import test from 'node:test';
import assert from 'node:assert/strict';
import { DatabaseSync } from 'node:sqlite';
import { readFileSync } from 'node:fs';
import worker, { hash } from './worker.mjs';

// Real SQLite exercises predicates, constraints, transactions and cascades.
function environment(max = 20) {
  const db = new DatabaseSync(':memory:');
  db.exec(readFileSync(new URL('./schema.sql', import.meta.url), 'utf8'));
  const prepare = sql => ({
    bind(...args) {
      const stmt = db.prepare(sql);
      return { first: async () => stmt.get(...args) || null,
        run: async () => ({ meta: { changes: Number(stmt.run(...args).changes) } }) };
    },
  });
  return { DB: { prepare, batch: async statements => {
    db.exec('BEGIN');
    try { const results = []; for (const s of statements) results.push(await s.run()); db.exec('COMMIT'); return results; }
    catch (error) { db.exec('ROLLBACK'); throw error; }
  } }, raw: db, ADMIN_TOKEN: 'admin'.repeat(16), OAUTH_CLIENT_ID: 'solar-client', OAUTH_CLIENT_SECRET: 'client-secret'.repeat(6),
    OAUTH_REDIRECT_URIS: JSON.stringify(['https://alexa.amazon.de/api/skill/link/example']), MAX_HOUSEHOLDS: String(max),
    LIMITER: { limit: async () => ({ success: true }) } };
}
function request(path, method = 'GET', token = null, input = null, form = false) {
  const headers = { 'CF-Connecting-IP': '192.0.2.1' };
  if (token) headers.Authorization = 'Bearer ' + token;
  if (input !== null) headers['Content-Type'] = form ? 'application/x-www-form-urlencoded' : 'application/json';
  return new Request('https://relay.example.test' + path, { method, headers,
    body: input === null ? null : form ? new URLSearchParams(input).toString() : JSON.stringify(input) });
}
async function invoke(env, path, method, token, input, form) {
  const response = await worker.fetch(request(path, method, token, input, form), env);
  return { status: response.status, value: await response.json() };
}
async function enroll(env) {
  const invitation = await invoke(env, '/admin/invites', 'POST', env.ADMIN_TOKEN, {});
  const enrolled = await invoke(env, '/v1/enroll', 'POST', null, { invite: invitation.value.invite, timezone: 'Europe/Berlin' });
  assert.equal(enrolled.status, 201);
  return { ...enrolled.value, invite: invitation.value.invite };
}
const live = power_w => ({ power_w, home_w: 600, energy_date: new Date().toISOString().slice(0, 10) });
async function link(env, account, options = {}) {
  const pair = await invoke(env, '/v1/pair', 'POST', account.write_token, {});
  const params = { client_id: env.OAUTH_CLIENT_ID, response_type: 'code', redirect_uri: JSON.parse(env.OAUTH_REDIRECT_URIS)[0], scope: 'solar:read', state: 'state-check', ...options, pair_code: pair.value.pair_code };
  const response = await worker.fetch(request('/oauth/authorize', 'POST', null, params, true), env);
  assert.equal(response.status, 302);
  const target = new URL(response.headers.get('Location'));
  assert.equal(target.searchParams.get('state'), params.state);
  const grant = { client_id: env.OAUTH_CLIENT_ID, client_secret: env.OAUTH_CLIENT_SECRET, grant_type: 'authorization_code', code: target.searchParams.get('code'), redirect_uri: params.redirect_uri };
  return { pair: pair.value, params, grant };
}

test('invites are one-use, capped, hashed, and do not grant read access', async () => {
  const env = environment(1), a = await enroll(env);
  assert.equal((await invoke(env, '/v1/enroll', 'POST', null, { invite: a.invite, timezone: 'UTC' })).status, 403);
  const invite = await invoke(env, '/admin/invites', 'POST', env.ADMIN_TOKEN, {});
  assert.equal((await invoke(env, '/v1/enroll', 'POST', null, { invite: invite.value.invite, timezone: 'UTC' })).status, 403);
  assert.equal((await invoke(env, '/v1/pv', 'GET', a.write_token)).status, 401);
  assert.notEqual(env.raw.prepare('SELECT write_hash FROM households').get().write_hash, a.write_token);
  assert.equal((await invoke(env, '/admin/invites', 'POST', a.write_token, {})).status, 401);
});

test('full OAuth and refresh preserve household isolation and role boundaries', async () => {
  const env = environment(), a = await enroll(env), b = await enroll(env);
  assert.equal((await invoke(env, '/v1/pv', 'POST', a.write_token, live(123))).status, 200);
  assert.equal((await invoke(env, '/v1/pv', 'POST', b.write_token, live(987))).status, 200);
  const { grant } = await link(env, a);
  const issued = await invoke(env, '/oauth/token', 'POST', null, grant, true);
  assert.equal(issued.status, 200);
  assert.equal((await invoke(env, '/v1/pv', 'GET', issued.value.access_token)).value.power_w, 123);
  assert.equal((await invoke(env, '/v1/pv', 'POST', issued.value.access_token, live(1))).status, 401);
  assert.equal((await invoke(env, '/oauth/token', 'POST', null, grant, true)).status, 400);
  const refresh = { client_id: env.OAUTH_CLIENT_ID, client_secret: env.OAUTH_CLIENT_SECRET, grant_type: 'refresh_token', refresh_token: issued.value.refresh_token };
  const renewed = await invoke(env, '/oauth/token', 'POST', null, refresh, true);
  assert.equal(renewed.status, 200);
  assert.notEqual(renewed.value.refresh_token, issued.value.refresh_token);
  assert.equal((await invoke(env, '/oauth/token', 'POST', null, refresh, true)).status, 400);
  assert.equal((await invoke(env, '/v1/pv', 'GET', renewed.value.access_token)).value.power_w, 123);
});

test('redirects, clients, expired codes and PKCE are validated before granting access', async () => {
  const env = environment(), a = await enroll(env);
  const bad = new URLSearchParams({ client_id: env.OAUTH_CLIENT_ID, response_type: 'code', redirect_uri: 'https://evil.test', scope: 'solar:read', state: 'x' });
  assert.equal((await worker.fetch(request('/oauth/authorize?' + bad), env)).status, 400);
  const verifier = 'v'.repeat(43);
  const challenge = Buffer.from(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))).toString('base64url');
  const { grant } = await link(env, a, { code_challenge: challenge, code_challenge_method: 'S256' });
  assert.equal((await invoke(env, '/oauth/token', 'POST', null, { ...grant, client_secret: 'wrong', code_verifier: verifier }, true)).status, 401);
  assert.equal((await invoke(env, '/oauth/token', 'POST', null, { ...grant, code_verifier: 'x'.repeat(43) }, true)).status, 400);
  assert.equal((await invoke(env, '/oauth/token', 'POST', null, { ...grant, code_verifier: verifier }, true)).status, 200);
  const expired = await link(env, a);
  env.raw.prepare('UPDATE oauth_codes SET expires=0 WHERE hash=?').run(await hash(expired.grant.code));
  assert.equal((await invoke(env, '/oauth/token', 'POST', null, expired.grant, true)).status, 400);
});

test('pairing is expiring and one-use; deletion revokes data and all credentials', async () => {
  const env = environment(), a = await enroll(env);
  await invoke(env, '/v1/pv', 'POST', a.write_token, live(123));
  const { grant, params } = await link(env, a);
  assert.equal((await worker.fetch(request('/oauth/authorize', 'POST', null, params, true), env)).status, 403);
  const issued = await invoke(env, '/oauth/token', 'POST', null, grant, true);
  assert.equal((await invoke(env, '/v1/account', 'DELETE', a.write_token)).status, 200);
  assert.equal((await invoke(env, '/v1/pv', 'GET', issued.value.access_token)).status, 401);
  assert.equal(env.raw.prepare('SELECT COUNT(*) AS n FROM access_tokens').get().n, 0);
  assert.equal(env.raw.prepare('SELECT COUNT(*) AS n FROM refresh_tokens').get().n, 0);
});

test('independent history, bounded payloads, validation, and minute throttling', async () => {
  const env = environment(), a = await enroll(env);
  assert.equal((await invoke(env, '/v1/pv', 'POST', a.write_token, { ...live(1), battery_soc: 101 })).status, 400);
  assert.equal((await invoke(env, '/v1/pv', 'POST', a.write_token, live(123))).status, 200);
  assert.equal((await invoke(env, '/v1/pv', 'POST', a.write_token, live(987))).status, 429);
  assert.equal((await invoke(env, '/v1/pv', 'POST', a.write_token, { kind: 'history', month_id: '2026-10', year_id: '2026', month_pv_kwh: 12 })).status, 200);
  const { grant } = await link(env, a), issued = await invoke(env, '/oauth/token', 'POST', null, grant, true);
  const data = await invoke(env, '/v1/pv', 'GET', issued.value.access_token);
  assert.equal(data.value.power_w, 123); assert.equal(data.value.history.month_pv_kwh, 12);
  assert.equal((await invoke(env, '/v1/pv', 'POST', a.write_token, { ...live(1), extra: 'x'.repeat(9000) })).status, 413);
  env.LIMITER.limit = async () => ({ success: false });
  assert.equal((await invoke(env, '/v1/health', 'GET')).status, 429);
});

test('unconfigured OAuth and limiter fail closed; expiry cleanup retains valid tokens', async () => {
  const env = environment(); env.OAUTH_REDIRECT_URIS = '[]';
  assert.equal((await worker.fetch(request('/oauth/authorize'), env)).status, 503);
  delete env.LIMITER;
  assert.equal((await invoke(env, '/v1/health', 'GET')).status, 503);
});


test('Alexa long opaque states round-trip without loosening OAuth validation', async () => {
  const env = environment(), account = await enroll(env);
  const { grant } = await link(env, account, { state: 'a'.repeat(2048) });
  assert.equal((await invoke(env, '/oauth/token', 'POST', null, grant, true)).status, 200);
  const valid = { client_id: env.OAUTH_CLIENT_ID, redirect_uri: JSON.parse(env.OAUTH_REDIRECT_URIS)[0], response_type: 'code', scope: 'solar:read', state: 's' };
  for (const [key, value, error] of [
    ['client_id', 'wrong', 'invalid_oauth_client'],
    ['redirect_uri', 'https://evil.test', 'invalid_oauth_redirect'],
    ['scope', 'admin', 'invalid_oauth_scope'],
    ['response_type', 'token', 'invalid_oauth_response_type'],
    ['state', 'x'.repeat(4097), 'invalid_oauth_state'],
  ]) {
    const r = await invoke(env, '/oauth/authorize', 'POST', null, { ...valid, [key]: value }, true);
    assert.equal(r.status, 400); assert.equal(r.value.error, error);
  }
});


test('mobile pasted pairing codes accept whitespace and case, but remain one-use', async () => {
  const env = environment(), a = await enroll(env);
  const { params } = await link(env, a);
  const fresh = await invoke(env, '/v1/pair', 'POST', a.write_token, {});
  const code = fresh.value.pair_code;
  const pasted = '  ' + code.slice(0, 40).toUpperCase() + '\n' + code.slice(40) + '  ';
  const input = { ...params, pair_code: pasted };
  assert.equal((await worker.fetch(request('/oauth/authorize', 'POST', null, input, true), env)).status, 302);
  assert.equal((await worker.fetch(request('/oauth/authorize', 'POST', null, input, true), env)).status, 403);
});


test('link form CSP permits only configured Amazon redirect origins', async () => {
  const env = environment();
  const q = new URLSearchParams({ client_id: env.OAUTH_CLIENT_ID, response_type: 'code', scope: 'solar:read', state: 'test-state', redirect_uri: JSON.parse(env.OAUTH_REDIRECT_URIS)[0] });
  const response = await worker.fetch(request('/oauth/authorize?' + q), env);
  assert.equal(response.status, 200);
  const csp = response.headers.get('Content-Security-Policy');
  assert.ok(csp.includes("form-action 'self' https://alexa.amazon.de;"));
  assert.ok(csp.includes("default-src 'none'"));
  assert.ok(!csp.includes('*'));
});

test('public information is readable without credentials or a database and never exposes configuration', async () => {
  for (const path of ['/', '/privacy', '/contact']) {
    const response = await worker.fetch(request(path), {});
    assert.equal(response.status, 200);
    assert.match(response.headers.get('Content-Type'), /text\/html/);
    const html = await response.text();
    assert.ok(html.includes('support@dorisundmarcin.de'));
    assert.ok(!html.includes('ADMIN_TOKEN'));
    assert.ok(response.headers.get('Content-Security-Policy').includes("frame-ancestors 'none'"));
  }
  assert.equal((await worker.fetch(request('/privacy','HEAD'), {})).status, 200);
});

test('review credentials link only a separate synthetic household and expire closed', async () => {
  const env = environment(), real = await enroll(env);
  const secret = 'ab'.repeat(32);
  Object.assign(env, { REVIEW_TENANT_ID: 'review-certification-20261019', REVIEW_KEY_HASH: await hash(secret), REVIEW_EXPIRES: String(Math.floor(Date.now()/1000)+86400) });
  env.raw.prepare('INSERT INTO households(id,write_hash,timezone,created) VALUES(?,?,?,?)').run(env.REVIEW_TENANT_ID, await hash('unknown-writer'), 'Europe/Berlin', 1);
  assert.equal((await worker.fetch(request('/review'), env)).status, 200);
  assert.equal((await invoke(env, '/review','POST',null,{review_key:'ff'.repeat(32)},true)).status, 401);
  const form = await worker.fetch(request('/review','POST',null,{review_key:secret},true),env);
  assert.equal(form.status,200);
  const code = (await form.text()).match(/<pre>([a-f0-9]{64})<\/pre>/)[1];
  const params={client_id:env.OAUTH_CLIENT_ID,response_type:'code',redirect_uri:JSON.parse(env.OAUTH_REDIRECT_URIS)[0],scope:'solar:read',state:'demo-test',pair_code:code};
  const redirect=await worker.fetch(request('/oauth/authorize','POST',null,params,true),env);
  const authcode=new URL(redirect.headers.get('Location')).searchParams.get('code');
  const grant=await invoke(env,'/oauth/token','POST',null,{client_id:env.OAUTH_CLIENT_ID,client_secret:env.OAUTH_CLIENT_SECRET,grant_type:'authorization_code',code:authcode,redirect_uri:params.redirect_uri},true);
  assert.equal(grant.status,200);
  const measurement=await invoke(env,'/v1/pv','GET',grant.value.access_token);
  assert.equal(measurement.value.power_w,3200);
  assert.equal(measurement.value.home_w,1200);
  assert.equal(measurement.value.history.month_home_kwh,200);
  assert.equal((await invoke(env,'/v1/pv','POST',grant.value.access_token,live(5))).status,401);
  assert.equal(env.raw.prepare('SELECT live_json FROM households WHERE id=?').get(real.tenant_id).live_json,null);
  env.REVIEW_EXPIRES='1';
  assert.equal((await invoke(env,'/review')).status,404);
  assert.equal((await invoke(env,'/v1/pv','GET',grant.value.access_token)).status,401);
});

test('review mode cannot target normal customer identifiers and is disabled without complete configuration', async () => {
  const env=environment();
  assert.equal((await invoke(env,'/review')).status,404);
  Object.assign(env,{REVIEW_TENANT_ID:crypto.randomUUID(),REVIEW_KEY_HASH:await hash('ab'.repeat(32)),REVIEW_EXPIRES:String(Math.floor(Date.now()/1000)+86400)});
  assert.equal((await invoke(env,'/review')).status,404);
});
