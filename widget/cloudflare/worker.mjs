import {skillToken, push} from './push.mjs';
import {registry} from './registry.mjs';
import {publicAssets} from './assets.mjs';
import {widgetPrivacy} from './privacy.mjs';
const sha = async s => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s))), n => n.toString(16).padStart(2,'0')).join('');
const reply = (status, value) => Response.json(value, {status, headers:{'Cache-Control':'no-store'}});

// WIDGET_DB is separate from the production source. SOURCE_DB only executes SELECTs.
export async function register(request, env) {
  const registrations = registry(env);
  if (!env.REGISTER_KEY || await sha(request.headers.get('Authorization') || '') !== await sha('Bearer ' + env.REGISTER_KEY))
    return reply(401, {error:'unauthorized'});
  const raw = await request.text();
  if (raw.length > 8192) return reply(413, {error:'too_large'});
  let data;
  try { data = JSON.parse(raw); } catch { return reply(400,{error:'invalid_json'}); }
  if (!/^amzn1\.ask\.device\.[A-Za-z0-9_.-]{1,4000}$/.test(data.device || '') ||
      !/^amzn1\.ask\.account\.[A-Za-z0-9_.-]{1,4000}$/.test(data.user || ''))
    return reply(400,{error:'invalid_target'});
  const key = 'device:' + await sha(data.device);
  const old = await registrations.get(key);
  if (data.action === 'remove') {
    if (old && old.user === data.user) await registrations.delete(key);
    return reply(200,{ok:true});
  }
  if (data.action !== 'install' || !/^[a-f0-9]{64}$/.test(data.access || ''))
    return reply(400,{error:'invalid_registration'});
  const row = await env.SOURCE_DB.prepare('SELECT h.id,h.write_hash FROM households h JOIN access_tokens a ON h.id=a.tenant WHERE a.hash=? AND a.expires>? AND h.disabled=0')
    .bind(await sha(data.access), Math.floor(Date.now()/1000)).first();
  if (!row) return reply(401,{error:'account_unavailable'});
  await registrations.put(key, JSON.stringify({device:data.device,user:data.user,tenant:row.id,
    version:await sha(row.write_hash), installed:Date.now()}));
  return reply(200,{ok:true});
}

export async function updateAll(env) {
  const registrations = registry(env);
  let cursor, token;
  const counts = {accepted:0, failed:0, revoked:0};
  do {
    const page = await registrations.list({prefix:'device:', limit:100, ...(cursor ? {cursor} : {})});
    for (const key of page.keys) {
      const registration = await registrations.get(key.name);
      if (!registration) continue;
      if ((registration.nextAttempt || 0) > Date.now()) continue;
      try {
        const row = await env.SOURCE_DB.prepare('SELECT write_hash,timezone,live_at,live_json FROM households WHERE id=? AND disabled=0')
          .bind(registration.tenant).first();
        if (!row || await sha(row.write_hash) !== registration.version) {
          await registrations.delete(key.name); counts.revoked++; continue;
        }
        const demo=registration.tenant.startsWith('review-');
        if (!demo && (!row.live_json || row.live_json.length > 8192)) throw Error('no_live_values');
        if (!token) token = await skillToken(env);
        const values=demo ? {power_w:3200,home_w:1200,battery_soc:72,demo:true,received_at:new Date().toISOString(),timezone:'Europe/Berlin'} :
          {...JSON.parse(row.live_json),received_at:row.live_at,timezone:row.timezone};
        await push(token, registration.device, values);
        if (registration.failures || !registration.lastAcceptedAt || Date.now()-registration.lastAcceptedAt>300000) {
          delete registration.failures;
          delete registration.nextAttempt;
          delete registration.lastError;
          delete registration.errorClass;
          delete registration.errorDetail;
          registration.lastAcceptedAt=Date.now();
          registration.measurementAt=values.received_at;
          await registrations.put(key.name,JSON.stringify(registration));
        }
        counts.accepted++;
      } catch (error) {
        counts.failed++;
        registration.failures = Math.min((registration.failures || 0)+1,6);
        registration.nextAttempt = Date.now()+Math.min(3600000,60000*2**registration.failures);
        registration.lastError=/^((lwa|datastore)_\d{3}(:[A-Z_]{1,64})?|dispatch:[A-Z_]{1,64}|datastore_invalid_response)$/.test(error.message || '') ? error.message :
          error.message==='no_live_values' ? 'no_live_values' : 'temporary_error';
        registration.errorClass=['TypeError','RangeError','SyntaxError','Error','TimeoutError'].includes(error.name) ? error.name : 'Other';
        registration.errorDetail=String(error.message || '').replace(/[A-Za-z0-9_.-]{24,}/g,'[redacted]').slice(0,180);
        await registrations.put(key.name,JSON.stringify(registration));
      }
    }
    cursor = page.list_complete ? null : page.cursor;
  } while (cursor);
  // Counts only. Never log device IDs, household IDs, metrics, URLs, tokens or response bodies.
  console.log(JSON.stringify({event:'widget_push', ...counts}));
  return counts;
}

export default {
  async fetch(request, env, context) {
    const path = new URL(request.url).pathname;
    if (path==='/privacy' && ['GET','HEAD'].includes(request.method))
      return new Response(request.method==='HEAD'?null:widgetPrivacy,{headers:{'Content-Type':'text/html; charset=utf-8',
        'Cache-Control':'no-store','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'",
        'X-Content-Type-Options':'nosniff'}});
    if (publicAssets[path] && ['GET','HEAD'].includes(request.method))
      return new Response(request.method==='HEAD' ? null : Uint8Array.from(atob(publicAssets[path]),c=>c.charCodeAt(0)),
        {headers:{'Content-Type':'image/png','Cache-Control':'public, max-age=3600','X-Content-Type-Options':'nosniff'}});
    if (new URL(request.url).pathname !== '/registrations' || request.method !== 'POST') return reply(404,{error:'not_found'});
    try {
      const response = await register(request, env);
      if (response.status===200 && context) context.waitUntil(updateAll(env));
      return response;
    } catch { return reply(503,{error:'temporarily_unavailable'}); }
  },
  scheduled(event, env, context) { context.waitUntil(updateAll(env)); }
};
