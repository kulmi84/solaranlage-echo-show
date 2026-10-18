const reply = (data, status = 200) => Response.json(data, {
  status, headers: { 'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff' }
});

async function authorized(request, secret) {
  if (!secret || secret.length < 32) return false;
  const supplied = request.headers.get('Authorization') || '';
  const digest = async s => new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(s)));
  const [a, b] = await Promise.all([digest(supplied), digest(`Bearer ${secret}`)]);
  let different = 0;
  for (let i = 0; i < a.length; i++) different |= a[i] ^ b[i];
  return different === 0;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (!['/pv', '/pv/history'].includes(url.pathname)) return reply({ error: 'not_found' }, 404);
    if (url.pathname === '/pv/history' && request.method !== 'POST') return reply({ error: 'method_not_allowed' }, 405);
    if (!['GET', 'POST'].includes(request.method)) return reply({ error: 'method_not_allowed' }, 405);
    const secret = request.method === 'POST' ? env.WRITE_TOKEN : env.READ_TOKEN;
    if (!await authorized(request, secret)) return reply({ error: 'unauthorized' }, 401);
    try {
      if (request.method === 'POST') {
        if (!request.headers.get('Content-Type')?.startsWith('application/json')) return reply({ error: 'json_required' }, 415);
        const body = await request.text();
        if (new TextEncoder().encode(body).length > 4096) return reply({ error: 'too_large' }, 413);
        let input;
        try { input = JSON.parse(body); } catch { return reply({ error: 'invalid_json' }, 400); }
        if (url.pathname === '/pv/history' || input?.kind === 'history') {
          if (!input || typeof input !== 'object' || typeof input.month_id !== 'string' || typeof input.year_id !== 'string' || !/^\d{4}-(0[1-9]|1[0-2])$/.test(input.month_id || '') || !/^\d{4}$/.test(input.year_id || '') || !input.month_id.startsWith(input.year_id + '-')) return reply({ error: 'invalid_period' }, 400);
          const history = { month_id: input.month_id, year_id: input.year_id };
          for (const prefix of ['month', 'year']) {
            for (const name of ['pv', 'home', 'grid_import', 'grid_export', 'battery_charge', 'battery_discharge']) {
              const key = `${prefix}_${name}_kwh`, value = input[key];
              if (value === undefined || value === null) { history[key] = null; continue; }
              if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 10000000) return reply({ error: 'invalid_history_metric' }, 400);
              history[key] = value;
            }
          }
          await env.DB.prepare('INSERT INTO solar_history (id, received_at, history_json) VALUES (1, ?, ?) ON CONFLICT(id) DO UPDATE SET received_at=excluded.received_at, history_json=excluded.history_json').bind(new Date().toISOString(), JSON.stringify(history)).run();
          return reply({ ok: true });
        }
        if (!input || typeof input.power_w !== 'number' || !Number.isFinite(input.power_w) || input.power_w < 0 || input.power_w > 10000000) {
          return reply({ error: 'invalid_power_w' }, 400);
        }
        const now = new Date().toISOString();
        const metrics = {};
        for (const key of ['pv_dc_w', 'bkw_w', 'home_w', 'grid_import_w', 'grid_export_w', 'battery_soc', 'battery_charge_w', 'battery_discharge_w', 'today_pv_kwh', 'today_home_kwh', 'today_grid_import_kwh', 'today_grid_export_kwh', 'today_battery_charge_kwh', 'today_battery_discharge_kwh']) {
          const value = input[key];
          if (value === undefined || value === null) { metrics[key] = null; continue; }
          if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > (key === 'battery_soc' ? 100 : 10000000)) return reply({ error: 'invalid_metric' }, 400);
          metrics[key] = value;
        }
        if (input.energy_date !== undefined && (typeof input.energy_date !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(input.energy_date))) return reply({ error: 'invalid_energy_date' }, 400);
        metrics.energy_date = input.energy_date ?? null;
        await env.DB.prepare('INSERT INTO pv (id, power_w, received_at, payload_json) VALUES (1, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET power_w=excluded.power_w, received_at=excluded.received_at, payload_json=excluded.payload_json').bind(input.power_w, now, JSON.stringify(metrics)).run();
        return reply({ ok: true, received_at: now });
      }
      const row = await env.DB.prepare('SELECT power_w, received_at, payload_json FROM pv WHERE id = 1').first();
      if (!row) return reply({ error: 'no_data' }, 404);
      const age = Math.max(0, Math.floor((Date.now() - Date.parse(row.received_at)) / 1000));
      const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Berlin', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
      const part = type => parts.find(p => p.type === type).value;
      const local_date = `${part('year')}-${part('month')}-${part('day')}`;
      const received_local = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Berlin', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(row.received_at));
      let history = null;
      try {
        const saved = await env.DB.prepare('SELECT received_at, history_json FROM solar_history WHERE id = 1').first();
        if (saved?.history_json) history = { ...JSON.parse(saved.history_json), received_at: saved.received_at };
      } catch { /* Old installations without the additive table keep working. */ }
      return reply({ ...JSON.parse(row.payload_json || '{}'), power_w: row.power_w, received_at: row.received_at, local_date, received_local, age_seconds: age, stale: age > 180, history });
    } catch {
      return reply({ error: 'storage_unavailable' }, 503);
    }
  }
};
