import test from 'node:test';
import assert from 'node:assert/strict';
import { environment } from './enrollment-fixture.mjs';
import worker, { hash } from './worker.mjs';

const setupKey = () => Array.from(crypto.getRandomValues(new Uint8Array(32)), n => n.toString(16).padStart(2, '0')).join('');
function request(path, { ip = '192.0.2.1', method = 'POST', body = {}, token, headers = {} } = {}) {
  const h = { 'Content-Type': 'application/json', ...headers };
  if (ip != null) h['CF-Connecting-IP'] = ip;
  if (token) h.Authorization = 'Bearer ' + token;
  return new Request('https://fixture.example' + path, { method, headers: h,
    body: ['GET', 'HEAD'].includes(method) ? null : JSON.stringify(body) });
}
async function call(env, path, options = {}) {
  const response = await worker.fetch(request(path, options), env);
  return { status: response.status, headers: response.headers, value: await response.json() };
}
const signup = (env, key = setupKey(), ip = '192.0.2.1') => call(env, '/v2/enroll',
  { ip, body: { installation_key: key, timezone: 'Europe/Berlin' } });
const count = env => env.raw.prepare('SELECT COUNT(*) AS n FROM households').get().n;

test('new route is opt-in; old database needs no new schema while disabled', async () => {
  const env = environment({ schema: false }); delete env.PUBLIC_ENROLLMENT_ENABLED;
  assert.equal((await signup(env)).status, 404);
  assert.equal(count(env), 0);
  assert.equal((await call(env, '/v1/health', { method: 'GET' })).status, 200);
  await worker.scheduled(null, env);
});

test('signup is separate from existing limiter and stores no raw IP or setup/writer secret', async () => {
  const env = environment(); env.LIMITER.limit = async () => { throw Error('legacy limiter must not be used'); };
  const key = setupKey(), result = await signup(env, key);
  assert.equal(result.status, 201);
  assert.match(result.value.write_token, /^[a-f0-9]{64}$/);
  const row = env.raw.prepare('SELECT * FROM households').get();
  assert.equal(row.write_hash, await hash(result.value.write_token));
  assert.notEqual(row.write_hash, result.value.write_token);
  const stored = JSON.stringify({ row, keys: env.raw.prepare('SELECT * FROM enrollment_keys').all(), limits: env.raw.prepare('SELECT * FROM enrollment_limits').all() });
  for (const secret of ['192.0.2.1', key, result.value.write_token]) assert.ok(!stored.includes(secret));
  assert.match(env.SIGNUP_LIMITER.calls[0].key, /^[a-f0-9]{64}$/);
  assert.equal(env.SIGNUP_LIMITER.calls[0].key, env.raw.prepare('SELECT subject FROM enrollment_limits').get().subject);
});

test('lost-response retries return the same account and do not consume another allowance', async () => {
  const env = environment(), key = setupKey();
  const first = await signup(env, key), retry = await signup(env, key, '192.0.2.99');
  assert.equal(first.status, 201); assert.equal(retry.status, 200);
  assert.deepEqual(retry.value, first.value); assert.equal(count(env), 1);
  assert.equal(env.raw.prepare('SELECT SUM(registrations) AS n FROM enrollment_limits').get().n, 2);
  env.MAX_HOUSEHOLDS = '1';
  assert.equal((await signup(env, key)).status, 200);
});

test('per-IP hourly limit rejects only new registrations; other IP remains usable', async () => {
  const env = environment();
  for (let n = 0; n < 3; n++) assert.equal((await signup(env)).status, 201);
  const denied = await signup(env);
  assert.equal(denied.status, 429); assert.equal(denied.value.error, 'registration_rate_limited');
  assert.ok(Number(denied.headers.get('Retry-After')) > 0);
  assert.equal((await signup(env, setupKey(), '192.0.2.2')).status, 201);
  assert.equal(count(env), 4);
});

test('parallel requests cannot exceed IP allowance, create duplicates or overfill capacity', async () => {
  const env = environment();
  const replies = await Promise.all(Array.from({ length: 8 }, () => signup(env)));
  assert.equal(replies.filter(r => r.status === 201).length, 3); assert.equal(count(env), 3);
  const repeated = environment(), key = setupKey();
  const same = await Promise.all(Array.from({ length: 5 }, () => signup(repeated, key)));
  assert.ok(same.every(r => [200, 201].includes(r.status)));
  assert.equal(new Set(same.map(r => r.value.tenant_id)).size, 1); assert.equal(count(repeated), 1);
  const capped = environment(); capped.MAX_HOUSEHOLDS = '2';
  const cappedReplies = await Promise.all(Array.from({ length: 6 }, (_, n) => signup(capped, setupKey(), '192.0.2.' + (n + 1))));
  assert.equal(cappedReplies.filter(r => r.status === 201).length, 2); assert.equal(count(capped), 2);
  assert.ok(cappedReplies.filter(r => r.status !== 201).every(r => r.value.error === 'registration_full'));
});

test('daily quota survives a new hour and resets after the UTC day changes', async t => {
  let current = Date.UTC(2026, 9, 31, 12, 0, 0);
  t.mock.method(Date, 'now', () => current);
  const env = environment(); env.ENROLLMENT_HOURLY_LIMIT = '1'; env.ENROLLMENT_DAILY_LIMIT = '2';
  assert.equal((await signup(env)).status, 201);
  current += 3600_000; assert.equal((await signup(env)).status, 201);
  current += 3600_000; assert.equal((await signup(env)).status, 429);
  current = Date.UTC(2026, 10, 1, 1, 0, 0); assert.equal((await signup(env)).status, 201);
  await worker.scheduled(null, env);
  assert.equal(env.raw.prepare('SELECT COUNT(*) AS n FROM enrollment_limits WHERE expires<=?').get(current / 1000).n, 0);
});

test('deleted account cannot be resurrected through retry; fresh setup works and old token is denied', async () => {
  const env = environment(), key = setupKey(), first = await signup(env, key);
  assert.equal((await call(env, '/v1/account', { method: 'DELETE', token: first.value.write_token })).status, 200);
  assert.equal((await signup(env, key)).status, 410); assert.equal(count(env), 0);
  const fresh = await signup(env); assert.equal(fresh.status, 201);
  assert.notEqual(fresh.value.write_token, first.value.write_token);
  assert.equal((await call(env, '/v1/pair', { token: first.value.write_token })).status, 401);
  assert.equal((await call(env, '/v1/pair', { token: fresh.value.write_token })).status, 200);
});

test('forged forwarding headers, invalid data and missing prerequisites cannot create accounts', async () => {
  const env = environment();
  assert.equal((await call(env, '/v2/enroll', { ip: null, headers: { 'X-Forwarded-For': '192.0.2.1' }, body: { installation_key: setupKey(), timezone: 'UTC' } })).status, 400);
  for (const ip of ['bad-ip', '999.1.1.1', '192.0.2.1,192.0.2.2']) assert.equal((await signup(env, setupKey(), ip)).status, 400);
  assert.equal((await signup(env, 'invalid')).status, 400);
  assert.equal((await call(env, '/v2/enroll', { body: { installation_key: [setupKey()], timezone: 'UTC' } })).status, 400);
  assert.equal((await call(env, '/v2/enroll', { body: { installation_key: setupKey(), timezone: 'invalid/timezone' } })).status, 400);
  env.REGISTRATION_KEY = ''; assert.equal((await signup(env)).status, 503);
  assert.equal(count(env), 0);
  const noSchema = environment({ schema: false }); assert.equal((await signup(noSchema)).status, 503);
  assert.equal((await call(noSchema, '/v1/health', { method: 'GET' })).status, 200);
});

test('IPv6 spelling is normalized, short-term limiter fails closed and limits are bounded', async () => {
  const env = environment(); env.ENROLLMENT_HOURLY_LIMIT = '1';
  assert.equal((await signup(env, setupKey(), '2001:db8::1')).status, 201);
  assert.equal((await signup(env, setupKey(), '2001:0db8:0000:0000:0000:0000:0000:0001')).status, 429);
  env.SIGNUP_LIMITER.limit = async () => ({ success: false });
  assert.equal((await signup(env, setupKey(), '192.0.2.9')).status, 429);
  const bad = environment(); bad.ENROLLMENT_HOURLY_LIMIT = '1000'; assert.equal((await signup(bad)).status, 503);
});

test('existing invited accounts, stored measurements and OAuth refresh survive blocked signup', async () => {
  const env = environment();
  const invite = await call(env, '/admin/invites', { token: env.ADMIN_TOKEN });
  const old = await call(env, '/v1/enroll', { body: { invite: invite.value.invite, timezone: 'UTC' } });
  const live = { power_w: 123, home_w: 456, energy_date: new Date().toISOString().slice(0, 10) };
  assert.equal((await call(env, '/v1/pv', { token: old.value.write_token, body: live })).status, 200);
  const before = env.raw.prepare('SELECT * FROM households WHERE id=?').get(old.value.tenant_id);
  const pair = await call(env, '/v1/pair', { token: old.value.write_token }); assert.equal(pair.status, 200);
  const params = { client_id: env.OAUTH_CLIENT_ID, redirect_uri: JSON.parse(env.OAUTH_REDIRECT_URIS)[0], response_type: 'code', scope: 'solar:read', state: 'fixture', pair_code: pair.value.pair_code };
  const redirect = await worker.fetch(new Request('https://fixture.example/oauth/authorize', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'CF-Connecting-IP': '192.0.2.1' }, body: new URLSearchParams(params) }), env);
  assert.equal(redirect.status, 302);
  const tokenRequest = body => worker.fetch(new Request('https://fixture.example/oauth/token', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded', 'CF-Connecting-IP': '192.0.2.1' }, body: new URLSearchParams(body) }), env);
  const oauth = await (await tokenRequest({ client_id: env.OAUTH_CLIENT_ID, client_secret: env.OAUTH_CLIENT_SECRET, grant_type: 'authorization_code', code: new URL(redirect.headers.get('Location')).searchParams.get('code'), redirect_uri: params.redirect_uri })).json();
  env.MAX_HOUSEHOLDS = '1'; env.SIGNUP_LIMITER.limit = async () => ({ success: false });
  assert.equal((await signup(env)).status, 429);
  const refresh = await tokenRequest({ client_id: env.OAUTH_CLIENT_ID, client_secret: env.OAUTH_CLIENT_SECRET, grant_type: 'refresh_token', refresh_token: oauth.refresh_token });
  assert.equal(refresh.status, 200); const renewed = await refresh.json();
  assert.equal((await call(env, '/v1/pv', { method: 'GET', token: renewed.access_token })).value.power_w, 123);
  assert.deepEqual(env.raw.prepare('SELECT * FROM households WHERE id=?').get(old.value.tenant_id), before);
  assert.equal(count(env), 1);
});

test('failed quota write rolls back the entire new account and retry record', async () => {
  const env = environment();
  env.raw.exec("CREATE TRIGGER reject_quota BEFORE INSERT ON enrollment_limits BEGIN SELECT RAISE(ABORT,'fixture-storage-failure'); END");
  const key = setupKey(), result = await signup(env, key);
  assert.equal(result.status, 503); assert.equal(result.value.error, 'registration_unavailable');
  assert.equal(count(env), 0);
  assert.equal(env.raw.prepare('SELECT COUNT(*) AS n FROM enrollment_keys').get().n, 0);
  assert.ok(!JSON.stringify(result.value).includes(key));
  assert.ok(!JSON.stringify(result.value).includes('fixture-storage-failure'));
  env.raw.exec('DROP TRIGGER reject_quota');
  assert.equal((await signup(env, key)).status, 201);
});

test('capability discovery changes only the new setup path; existing health contract stays exact', async () => {
  const env = environment({ schema: false }); env.PUBLIC_ENROLLMENT_ENABLED = 'false';
  assert.deepEqual((await call(env, '/v2/enrollment', { method: 'GET' })).value, { mode: 'invitation' });
  env.PUBLIC_ENROLLMENT_ENABLED = 'true';
  assert.deepEqual((await call(env, '/v2/enrollment', { method: 'GET' })).value, { mode: 'automatic' });
  assert.deepEqual((await call(env, '/v1/health', { method: 'GET' })).value, { ok: true, api: 1 });
  assert.equal(count(env), 0);
});
