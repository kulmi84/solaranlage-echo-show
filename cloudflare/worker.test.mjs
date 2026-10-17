import { test } from 'node:test';
import assert from 'node:assert/strict';
import worker from './worker.mjs';

const env = { READ_TOKEN: 'read-'.repeat(10), WRITE_TOKEN: 'write-'.repeat(10) };
let row;
env.DB = { prepare: () => ({ bind: (power, time, payload) => ({ run: async () => { row = { power_w: power, received_at: time, payload_json: payload }; } }), first: async () => row }) };
const request = (method, token, body) => new Request('https://example.test/pv', {
  method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
  ...(body === undefined ? {} : { body: JSON.stringify(body) })
});

test('read and write credentials cannot cross authorization boundaries', async () => {
  assert.equal((await worker.fetch(request('POST', env.READ_TOKEN, { power_w: 1 }), env)).status, 401);
  assert.equal((await worker.fetch(request('GET', env.WRITE_TOKEN), env)).status, 401);
});
test('missing data and invalid values are explicit; valid zero survives round trip', async () => {
  assert.equal((await worker.fetch(request('GET', env.READ_TOKEN), env)).status, 404);
  for (const power_w of [null, '2000', -1, 10000001]) {
    assert.equal((await worker.fetch(request('POST', env.WRITE_TOKEN, { power_w }), env)).status, 400);
  }
  assert.equal((await worker.fetch(request('POST', env.WRITE_TOKEN, { power_w: 0 }), env)).status, 200);
  const response = await worker.fetch(request('GET', env.READ_TOKEN), env);
  assert.equal(response.headers.get('cache-control'), 'no-store');
  const data = await response.json();
  assert.equal(data.power_w, 0);
  assert.equal(data.stale, false);
});
test('stale data is flagged and storage errors do not leak details', async () => {
  row.received_at = new Date(Date.now() - 240000).toISOString();
  assert.equal((await (await worker.fetch(request('GET', env.READ_TOKEN), env)).json()).stale, true);
  const broken = { ...env, DB: { prepare() { throw Error('secret connection details'); } } };
  const response = await worker.fetch(request('GET', env.READ_TOKEN), broken);
  assert.equal(response.status, 503);
  assert.deepEqual(await response.json(), { error: 'storage_unavailable' });
});

test('solar metrics preserve null and zero and reject invalid SOC', async () => {
  const data = { power_w: 2500, battery_soc: 100, grid_import_w: 0, home_w: null, today_pv_kwh: 18.2, energy_date: '2026-10-17' };
  assert.equal((await worker.fetch(request('POST', env.WRITE_TOKEN, data), env)).status, 200);
  const result = await (await worker.fetch(request('GET', env.READ_TOKEN), env)).json();
  assert.equal(result.battery_soc, 100); assert.equal(result.home_w, null); assert.equal(result.grid_import_w, 0);
  assert.equal(result.today_pv_kwh, 18.2);
  for (const value of [101, -1, '100']) assert.equal((await worker.fetch(request('POST', env.WRITE_TOKEN, {...data, battery_soc: value}), env)).status, 400);
});
