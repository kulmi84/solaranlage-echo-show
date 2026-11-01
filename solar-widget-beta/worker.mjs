const reply = (body, status = 200) => Response.json(body, {status, headers: {'Cache-Control': 'no-store'}});
const keys = ['power_w', 'home_w', 'battery_soc', 'today_pv_kwh', 'today_grid_export_kwh'];

async function authorized(request, token) {
  if (!token || token.length < 32) return false;
  const digest = value => crypto.subtle.digest('SHA-256', new TextEncoder().encode(value));
  const a = new Uint8Array(await digest(request.headers.get('Authorization') || ''));
  const b = new Uint8Array(await digest(`Bearer ${token}`));
  return a.reduce((difference, value, i) => difference | (value ^ b[i]), 0) === 0;
}

async function boundedJson(request) {
  const reader = request.body?.getReader();
  if (!reader) throw new Error('empty');
  const chunks = [];
  let length = 0;
  while (true) {
    const {value, done} = await reader.read();
    if (done) break;
    length += value.length;
    if (length > 4096) { await reader.cancel(); throw new Error('size'); }
    chunks.push(value);
  }
  const bytes = new Uint8Array(length);
  let offset = 0;
  for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
  return JSON.parse(new TextDecoder().decode(bytes));
}

export function contentFor(row, now = Date.now()) {
  const values = row ? JSON.parse(row.payload) : {};
  const stale = !row || now - Date.parse(row.received_at) > 180000;
  const format = (key, unit) => values[key] == null ? '—' : `${new Intl.NumberFormat('de-DE', {maximumFractionDigits: 2}).format(values[key])} ${unit}`;
  const today = new Intl.DateTimeFormat('sv-SE', {timeZone: 'Europe/Berlin'}).format(new Date(now));
  return {
    production: format('power_w', 'W'), consumption: format('home_w', 'W'),
    battery: format('battery_soc', '%'),
    today: values.energy_date === today ? format('today_pv_kwh', 'kWh') : '—',
    export: values.energy_date === today ? format('today_grid_export_kwh', 'kWh') : '—',
    status: !row ? 'Noch keine Messwerte' : stale ? 'VERALTET · letzter Empfang:' : 'Letzter Empfang:',
    received: row?.received_at || '—'
  };
}

export async function push(env, send = fetch) {
  for (const name of ['BETA_CLIENT_ID', 'BETA_CLIENT_SECRET', 'BETA_USER_ID']) {
    if (!env[name]) throw new Error('beta_configuration_missing');
  }
  const row = await env.BETA_DB.prepare('SELECT payload, received_at FROM beta_snapshot WHERE id=1').first();
  const tokenResponse = await send('https://api.amazon.com/auth/o2/token', {
    method: 'POST', signal: AbortSignal.timeout(10000),
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: new URLSearchParams({grant_type: 'client_credentials', client_id: env.BETA_CLIENT_ID,
      client_secret: env.BETA_CLIENT_SECRET, scope: 'alexa::datastore'})
  });
  if (!tokenResponse.ok) throw new Error('beta_token_failed');
  const {access_token} = await tokenResponse.json();
  if (!access_token) throw new Error('beta_token_missing');
  const response = await send('https://api.eu.amazonalexa.com/v1/datastore/commands', {
    method: 'POST', signal: AbortSignal.timeout(10000),
    headers: {'Content-Type': 'application/json', Authorization: `Bearer ${access_token}`},
    body: JSON.stringify({commands: [{type: 'PUT_OBJECT', namespace: 'MeineSolaranlageBeta',
      key: 'live', content: contentFor(row)}], target: {type: 'USER', item: env.BETA_USER_ID}})
  });
  if (!response.ok) throw new Error('beta_push_failed');
  const result = await response.json();
  // HTTP 200 alone does not prove delivery. The next cron retries current data.
  if (!Array.isArray(result.results) || !result.results.length || result.results.some(item => item.type !== 'SUCCESS')) {
    throw new Error('beta_delivery_not_confirmed');
  }
  return {delivered: result.results.length};
}

export default {
  async fetch(request, env) {
    const path = new URL(request.url).pathname;
    if (!['/values', '/push'].includes(path)) return reply({error: 'not_found'}, 404);
    if (request.method !== 'POST') return reply({error: 'method_not_allowed'}, 405);
    if (!await authorized(request, path === '/push' ? env.BETA_ADMIN_TOKEN : env.BETA_WRITE_TOKEN)) return reply({error: 'unauthorized'}, 401);
    try {
      if (path === '/push') return reply(await push(env));
      if (!request.headers.get('Content-Type')?.startsWith('application/json')) return reply({error: 'json_required'}, 415);
      let input;
      try { input = await boundedJson(request); } catch { return reply({error: 'invalid_or_oversize_json'}, 400); }
      if (!input || typeof input !== 'object' || Array.isArray(input)) return reply({error: 'invalid_values'}, 400);
      const values = {};
      for (const key of keys) {
        const value = input[key] ?? null;
        if (value !== null && (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > (key === 'battery_soc' ? 100 : 10000000))) return reply({error: 'invalid_values'}, 400);
        values[key] = value;
      }
      if (input.energy_date != null && !/^\d{4}-\d{2}-\d{2}$/.test(input.energy_date)) return reply({error: 'invalid_date'}, 400);
      values.energy_date = input.energy_date ?? null;
      const received = new Date().toISOString();
      await env.BETA_DB.prepare('INSERT INTO beta_snapshot(id,payload,received_at) VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload, received_at=excluded.received_at').bind(JSON.stringify(values), received).run();
      return reply({stored: true, received_at: received});
    } catch { return reply({error: 'beta_service_unavailable'}, 503); }
  },
  async scheduled(_event, env) {
    try { await push(env); } catch (error) {
      console.error(JSON.stringify({event: 'beta_push_failed', reason: error.message.startsWith('beta_') ? error.message : 'service_unavailable'}));
      throw new Error('BETA push unsuccessful');
    }
  }
};
