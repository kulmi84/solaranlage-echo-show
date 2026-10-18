// Separate beta backend. No access to the production single-household tables.
const headers = { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff', 'Referrer-Policy': 'no-referrer' };
const reply = (value, status = 200) => Response.json(value, { status, headers });
const now = () => Math.floor(Date.now() / 1000);
const random = () => Array.from(crypto.getRandomValues(new Uint8Array(32)), v => v.toString(16).padStart(2, '0')).join('');
export const hash = async value => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(value))), v => v.toString(16).padStart(2, '0')).join('');
const bearer = request => (request.headers.get('Authorization') || '').replace(/^Bearer /, '');
const escaped = text => String(text).replace(/[&<>"']/g, x => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[x]));
async function equal(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') return false;
  const [x, y] = await Promise.all([hash(a), hash(b)]);
  let diff = 0;
  for (let i = 0; i < x.length; i++) diff |= x.charCodeAt(i) ^ y.charCodeAt(i);
  return diff === 0;
}
function failure(code, status = 400) { const e = new Error(code); e.status = status; throw e; }
async function body(request, form = false) {
  if (!(request.headers.get('Content-Type') || '').startsWith(form ? 'application/x-www-form-urlencoded' : 'application/json')) failure('content_type', 415);
  const reader = request.body?.getReader();
  let text = '', size = 0;
  const decoder = new TextDecoder();
  if (reader) while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    size += value.byteLength;
    if (size > 8192) { await reader.cancel(); failure('too_large', 413); }
    text += decoder.decode(value, { stream: true });
  }
  text += decoder.decode();
  if (form) return Object.fromEntries(new URLSearchParams(text));
  try { return JSON.parse(text); } catch { failure('invalid_json'); }
}
export function metrics(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) failure('invalid_data');
  const result = {};
  const keys = input.kind === 'history'
    ? ['month', 'year'].flatMap(p => ['pv', 'home', 'grid_import', 'grid_export', 'battery_charge', 'battery_discharge'].map(k => `${p}_${k}_kwh`))
    : ['power_w', 'pv_dc_w', 'bkw_w', 'home_w', 'grid_import_w', 'grid_export_w', 'battery_soc', 'battery_charge_w', 'battery_discharge_w',
       ...['pv', 'home', 'grid_import', 'grid_export', 'battery_charge', 'battery_discharge'].map(k => `today_${k}_kwh`)];
  for (const key of keys) {
    const v = input[key];
    if (v == null) result[key] = null;
    else if (typeof v !== 'number' || !Number.isFinite(v) || v < 0 || v > (key === 'battery_soc' ? 100 : 10000000)) failure('invalid_metric');
    else result[key] = v;
  }
  if (input.kind === 'history') {
    if (!/^\d{4}-(0[1-9]|1[0-2])$/.test(input.month_id || '') || !/^\d{4}$/.test(input.year_id || '') || !input.month_id.startsWith(input.year_id + '-')) failure('invalid_period');
    Object.assign(result, { month_id: input.month_id, year_id: input.year_id });
  } else {
    if (result.power_w === null || !/^\d{4}-\d{2}-\d{2}$/.test(input.energy_date || '')) failure('invalid_data');
    result.energy_date = input.energy_date;
  }
  return result;
}
async function writer(request, env) {
  const token = bearer(request);
  if (!/^[a-f0-9]{64}$/.test(token)) failure('unauthorized', 401);
  const row = await env.DB.prepare('SELECT * FROM households WHERE write_hash=? AND disabled=0').bind(await hash(token)).first();
  if (!row) failure('unauthorized', 401);
  return row;
}
function oauthContext(params, env) {
  let allowed;
  try { allowed = JSON.parse(env.OAUTH_REDIRECT_URIS || '[]'); } catch { failure('oauth_not_ready', 503); }
  if (!Array.isArray(allowed) || !allowed.length || !env.OAUTH_CLIENT_SECRET) failure('oauth_not_ready', 503);
  if (params.client_id !== env.OAUTH_CLIENT_ID) failure('invalid_oauth_client');
  if (!allowed.includes(params.redirect_uri)) failure('invalid_oauth_redirect');
  if (params.response_type !== 'code') failure('invalid_oauth_response_type');
  if (params.scope !== 'solar:read') failure('invalid_oauth_scope');
  // Alexa owns this opaque value. Preserve it verbatim, including long app states.
  if (!params.state || params.state.length > 4096) failure('invalid_oauth_state');
  if (params.code_challenge && (params.code_challenge_method !== 'S256' || !/^[A-Za-z0-9_-]{43}$/.test(params.code_challenge))) failure('invalid_pkce');
  return params;
}
async function tokens(tenant, env) {
  const access = random(), refresh = random();
  await env.DB.batch([
    env.DB.prepare('INSERT INTO access_tokens(hash,tenant,expires) VALUES(?,?,?)').bind(await hash(access), tenant, now() + 3600),
    env.DB.prepare('INSERT INTO refresh_tokens(hash,tenant,expires) VALUES(?,?,?)').bind(await hash(refresh), tenant, now() + 90 * 86400),
  ]);
  return reply({ access_token: access, refresh_token: refresh, token_type: 'Bearer', expires_in: 3600, scope: 'solar:read' });
}

export default {
  async fetch(request, env) {
    try {
      const url = new URL(request.url), path = url.pathname, method = request.method;
      if (url.protocol !== 'https:') return reply({ error: 'https_required' }, 400);
      if (!env.LIMITER) return reply({ error: 'limiter_not_ready' }, 503);
      const limit = await env.LIMITER.limit({ key: request.headers.get('CF-Connecting-IP') || 'unknown' });
      if (!limit.success) return reply({ error: 'rate_limited' }, 429);
      if (path === '/v1/health' && method === 'GET') return reply({ ok: true, api: 1 });
      if (path === '/admin/invites' && method === 'POST') {
        if (!env.ADMIN_TOKEN || env.ADMIN_TOKEN.length < 32 || !await equal(bearer(request), env.ADMIN_TOKEN)) failure('unauthorized', 401);
        const invite = random();
        await env.DB.prepare('INSERT INTO invites(hash,expires) VALUES(?,?)').bind(await hash(invite), now() + 7 * 86400).run();
        return reply({ invite, expires_in: 7 * 86400 }, 201);
      }
      if (path === '/v1/enroll' && method === 'POST') {
        const input = await body(request);
        if (!/^[a-f0-9]{64}$/.test(input?.invite || '')) failure('invalid_invite', 403);
        try { new Intl.DateTimeFormat('en', { timeZone: input.timezone }).format(); } catch { failure('invalid_timezone'); }
        if (typeof input.timezone !== 'string' || input.timezone.length > 80) failure('invalid_timezone');
        const id = crypto.randomUUID(), write = random(), invitation = await hash(input.invite);
        const max = Math.min(20, Math.max(1, Number.parseInt(env.MAX_HOUSEHOLDS || '20', 10) || 20));
        const result = await env.DB.batch([
          env.DB.prepare('INSERT INTO households(id,write_hash,timezone,created) SELECT ?,?,?,? WHERE EXISTS(SELECT 1 FROM invites WHERE hash=? AND used=0 AND expires>?) AND (SELECT COUNT(*) FROM households) < ?').bind(id, await hash(write), input.timezone, now(), invitation, now(), max),
          env.DB.prepare('UPDATE invites SET used=1 WHERE hash=? AND EXISTS(SELECT 1 FROM households WHERE id=?)').bind(invitation, id),
        ]);
        if (!result[0].meta.changes) failure('invalid_invite_or_full', 403);
        return reply({ tenant_id: id, write_token: write }, 201);
      }
      if (path === '/v1/pair' && method === 'POST') {
        const row = await writer(request, env), code = random();
        await env.DB.batch([
          env.DB.prepare('DELETE FROM pair_codes WHERE tenant=?').bind(row.id),
          env.DB.prepare('INSERT INTO pair_codes(hash,tenant,expires) VALUES(?,?,?)').bind(await hash(code), row.id, now() + 600),
        ]);
        return reply({ pair_code: code, expires_in: 600 });
      }
      if (path === '/v1/account' && method === 'DELETE') {
        const row = await writer(request, env);
        await env.DB.prepare('DELETE FROM households WHERE id=?').bind(row.id).run();
        return reply({ ok: true });
      }
      if (path === '/v1/pv' && method === 'POST') {
        const row = await writer(request, env), input = await body(request), value = metrics(input);
        const history = input.kind === 'history', column = history ? 'history' : 'live';
        const previous = Date.parse(row[column + '_at'] || '') || 0;
        if (Date.now() - previous < (history ? 30000 : 45000)) failure('rate_limited', 429);
        // Include previous timestamp in the predicate so parallel uploads cannot bypass throttling.
        const result = await env.DB.prepare(`UPDATE households SET ${column}_json=?,${column}_at=? WHERE id=? AND ${column}_at IS ?`).bind(JSON.stringify(value), new Date().toISOString(), row.id, row[column + '_at'] ?? null).run();
        if (!result.meta.changes) failure('rate_limited', 429);
        return reply({ ok: true });
      }
      if (path === '/v1/pv' && method === 'GET') {
        const token = bearer(request);
        if (!/^[a-f0-9]{64}$/.test(token)) failure('unauthorized', 401);
        const row = await env.DB.prepare('SELECT h.* FROM households h JOIN access_tokens a ON h.id=a.tenant WHERE a.hash=? AND a.expires>? AND h.disabled=0').bind(await hash(token), now()).first();
        if (!row) failure('unauthorized', 401);
        if (!row.live_json) failure('no_data', 404);
        const parts = new Intl.DateTimeFormat('en-CA', { timeZone: row.timezone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
        const part = type => parts.find(p => p.type === type).value;
        return reply({ ...JSON.parse(row.live_json), received_at: row.live_at,
          local_date: `${part('year')}-${part('month')}-${part('day')}`,
          received_local: new Intl.DateTimeFormat('en-GB', { timeZone: row.timezone, hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(row.live_at)),
          history: row.history_json ? { ...JSON.parse(row.history_json), received_at: row.history_at } : null });
      }
      if (path === '/oauth/authorize' && ['GET', 'POST'].includes(method)) {
        const params = oauthContext(method === 'GET' ? Object.fromEntries(url.searchParams) : await body(request, true), env);
        if (method === 'GET') {
          // form-action also applies to the POST redirect in browsers such as Safari.
          const formTargets = [...new Set(JSON.parse(env.OAUTH_REDIRECT_URIS).map(uri => new URL(uri).origin))].join(' ');
          const hidden = Object.entries(params).filter(([key]) => ['client_id', 'redirect_uri', 'response_type', 'scope', 'state', 'code_challenge', 'code_challenge_method'].includes(key)).map(([key, value]) => `<input type="hidden" name="${escaped(key)}" value="${escaped(value)}">`).join('');
          return new Response(`<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Solaranlage verbinden</title><h1>Solaranlage mit Alexa verbinden</h1><p>Öffne in Home Assistant die Optionen von Solaranlage Echo Show → Alexa verbinden. Kopiere den kurzlebigen Code hierher.</p><p>Damit erlaubst du Alexa, die ausgewählten Solar-, Verbrauchs-, Netz- und Akkuwerte deiner Anlage abzurufen.</p><form method="post" action="/oauth/authorize">${hidden}<label>Verbindungscode <input name="pair_code" type="password" autocomplete="off" required maxlength="256" autocapitalize="none" spellcheck="false"></label><button type="submit">Meine Anlage verbinden</button></form></html>`, { headers: { ...headers, 'Content-Type': 'text/html; charset=utf-8', 'Content-Security-Policy': `default-src 'none'; form-action 'self' ${formTargets}; frame-ancestors 'none'; base-uri 'none'` } });
        }
        // Mobile text selection can include visual line breaks or spaces.
        const pairCode = String(params.pair_code || '').replace(/\s/g, '').toLowerCase();
        if (!/^[a-f0-9]{64}$/.test(pairCode)) failure('invalid_pair_code', 403);
        const paired = await env.DB.prepare('UPDATE pair_codes SET used=1 WHERE hash=? AND used=0 AND expires>? RETURNING tenant').bind(await hash(pairCode), now()).first();
        if (!paired) failure('invalid_pair_code', 403);
        const code = random();
        await env.DB.prepare('INSERT INTO oauth_codes(hash,tenant,client,redirect,challenge,expires) VALUES(?,?,?,?,?,?)').bind(await hash(code), paired.tenant, params.client_id, params.redirect_uri, params.code_challenge || null, now() + 300).run();
        const target = new URL(params.redirect_uri); target.searchParams.set('code', code); target.searchParams.set('state', params.state);
        return new Response(null, { status: 302, headers: { ...headers, Location: target.toString() } });
      }
      if (path === '/oauth/token' && method === 'POST') {
        const input = await body(request, true);
        let id = input.client_id, secret = input.client_secret;
        if ((request.headers.get('Authorization') || '').startsWith('Basic ')) {
          const decoded = atob(request.headers.get('Authorization').slice(6)), split = decoded.indexOf(':');
          id = decoded.slice(0, split); secret = decoded.slice(split + 1);
        }
        if (!env.OAUTH_CLIENT_SECRET || id !== env.OAUTH_CLIENT_ID || !await equal(secret, env.OAUTH_CLIENT_SECRET)) failure('invalid_client', 401);
        if (input.grant_type === 'authorization_code') {
          const row = await env.DB.prepare('SELECT * FROM oauth_codes WHERE hash=? AND used=0 AND expires>?').bind(await hash(input.code || ''), now()).first();
          if (!row || row.client !== id || row.redirect !== input.redirect_uri) failure('invalid_grant');
          if (row.challenge) {
            if (!/^[A-Za-z0-9._~-]{43,128}$/.test(input.code_verifier || '')) failure('invalid_grant');
            const digest = new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(input.code_verifier)));
            const challenge = btoa(String.fromCharCode(...digest)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
            if (!await equal(challenge, row.challenge)) failure('invalid_grant');
          }
          const consumed = await env.DB.prepare('UPDATE oauth_codes SET used=1 WHERE hash=? AND used=0 RETURNING tenant').bind(row.hash).first();
          if (!consumed) failure('invalid_grant');
          return tokens(consumed.tenant, env);
        }
        if (input.grant_type === 'refresh_token') {
          const consumed = await env.DB.prepare('DELETE FROM refresh_tokens WHERE hash=? AND expires>? RETURNING tenant').bind(await hash(input.refresh_token || ''), now()).first();
          if (!consumed) failure('invalid_grant');
          return tokens(consumed.tenant, env);
        }
        failure('unsupported_grant_type');
      }
      return reply({ error: 'not_found' }, 404);
    } catch (error) { return reply({ error: error.status ? error.message : 'service_unavailable' }, error.status || 503); }
  },
  async scheduled(_event, env) {
    await env.DB.batch(['pair_codes', 'oauth_codes', 'access_tokens', 'refresh_tokens', 'invites'].map(table => env.DB.prepare(`DELETE FROM ${table} WHERE expires<?`).bind(now())));
  }
};
