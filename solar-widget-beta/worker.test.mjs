import test from 'node:test';
import assert from 'node:assert/strict';
import worker, {contentFor, push} from './worker.mjs';

test('missing, stale and previous-day values stay recognizable', () => {
  assert.equal(contentFor(null).production, '—');
  const row = {payload: JSON.stringify({power_w: 0, battery_soc: 0, today_pv_kwh: 9, energy_date: '2026-10-31'}), received_at: '2026-11-01T10:00:00Z'};
  const value = contentFor(row, Date.parse('2026-11-01T10:04:00Z'));
  assert.equal(value.production, '0 W');
  assert.equal(value.battery, '0 %');
  assert.equal(value.today, '—');
  assert.match(value.status, /VERALTET/);
});

test('unauthorized requests never touch the database', async () => {
  const response = await worker.fetch(new Request('https://beta.test/values', {method: 'POST'}), {});
  assert.equal(response.status, 401);
});

test('invalid metrics and oversized uploads never write', async () => {
  const token = 'x'.repeat(32);
  for (const payload of [{battery_soc: 101}, {power_w: -1}, {home_w: true}, {padding: 'x'.repeat(5000)}]) {
    const response = await worker.fetch(new Request('https://beta.test/values', {method: 'POST', headers: {Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'}, body: JSON.stringify(payload)}), {BETA_WRITE_TOKEN: token});
    assert.equal(response.status, 400);
  }
});

test('uploads use exclusively the BETA database', async () => {
  let saved;
  const token = 'x'.repeat(32);
  const env = {BETA_WRITE_TOKEN: token, BETA_DB: {prepare(sql) {
    assert.match(sql, /beta_snapshot/);
    return {bind(...args) { saved = args; return {async run() {}}; }};
  }}};
  const response = await worker.fetch(new Request('https://beta.test/values', {method: 'POST', headers: {Authorization: `Bearer ${token}`, 'Content-Type': 'application/json'}, body: '{"power_w":123}'}), env);
  assert.equal(response.status, 200);
  assert.equal(JSON.parse(saved[0]).power_w, 123);
});

test('push uses BETA credentials, target and native PUT_OBJECT; checks delivery', async () => {
  const env = {BETA_CLIENT_ID: 'beta-client', BETA_CLIENT_SECRET: 'beta-secret', BETA_USER_ID: 'beta-user',
    BETA_DB: {prepare: () => ({first: async () => null})}};
  for (const resultType of ['SUCCESS', 'DEVICE_UNAVAILABLE']) {
    let calls = 0;
    const send = async (url, options) => {
      calls++;
      if (calls === 1) {
        assert.equal(options.body.get('scope'), 'alexa::datastore');
        assert.equal(options.body.get('client_id'), 'beta-client');
        return Response.json({access_token: 'beta-access'});
      }
      assert.equal(url, 'https://api.eu.amazonalexa.com/v1/datastore/commands');
      const payload = JSON.parse(options.body);
      assert.deepEqual(payload.target, {type: 'USER', item: 'beta-user'});
      assert.equal(payload.commands[0].namespace, 'MeineSolaranlageBeta');
      assert.equal(payload.commands[0].type, 'PUT_OBJECT');
      assert.equal(payload.attemptDeliveryUntil, undefined);
      return Response.json({results: [{type: resultType}]});
    };
    if (resultType === 'SUCCESS') assert.equal((await push(env, send)).delivered, 1);
    else await assert.rejects(push(env, send), /delivery_not_confirmed/);
  }
});
