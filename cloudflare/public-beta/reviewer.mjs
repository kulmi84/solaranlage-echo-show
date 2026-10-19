// Optional, time-limited certification household. Never targets a normal UUID household.
export function reviewerEnabled(env) {
  const expires = Number(env.REVIEW_EXPIRES);
  return /^review-[a-z0-9-]{8,80}$/.test(env.REVIEW_TENANT_ID || '') &&
    /^[a-f0-9]{64}$/.test(env.REVIEW_KEY_HASH || '') && Number.isSafeInteger(expires) &&
    expires > Math.floor(Date.now() / 1000);
}
export function demoValues() {
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Europe/Berlin', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date());
  const part = name => parts.find(p => p.type === name).value;
  const energy_date = `${part('year')}-${part('month')}-${part('day')}`;
  const live = { power_w: 3200, pv_dc_w: 2800, bkw_w: 400, home_w: 1200,
    grid_import_w: 0, grid_export_w: 1500, battery_soc: 72, battery_charge_w: 500, battery_discharge_w: 0,
    energy_date, today_pv_kwh: 18, today_home_kwh: 10, today_grid_import_kwh: 1,
    today_grid_export_kwh: 7, today_battery_charge_kwh: 4, today_battery_discharge_kwh: 2 };
  const history = { month_id: energy_date.slice(0,7), year_id: part('year') };
  for (const [period, factor] of [['month', 20], ['year', 150]]) for (const [key,value] of Object.entries(live)) {
    if (key.startsWith('today_')) history[period + key.slice(5)] = value * factor;
  }
  return { live, history };
}
export async function reviewerRoute(request, env, helpers) {
  if (new URL(request.url).pathname !== '/review') return null;
  const { headers, body, hash, equal, random, now, failure } = helpers;
  if (!reviewerEnabled(env)) failure('not_found', 404);
  const html = content => new Response(`<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Solaranlage certification demo</title><h1>Solaranlage certification demo</h1><p>Isolated synthetic household. No access to customer measurements.</p>${content}<p><a href="/privacy">Privacy</a> · <a href="/contact">Contact</a></p></html>`, { headers: { ...headers, 'Content-Type':'text/html; charset=utf-8', 'Content-Security-Policy':"default-src 'none'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'" } });
  if (request.method === 'GET') return html('<form method="post" action="/review"><label>Reviewer key <input type="password" name="review_key" required maxlength="64" autocomplete="off" autocapitalize="none" spellcheck="false"></label><button type="submit">Generate one-time linking code</button></form>');
  if (request.method !== 'POST') failure('method_not_allowed', 405);
  const input = await body(request, true);
  if (!/^[a-f0-9]{64}$/.test(input.review_key || '') || !await equal(await hash(input.review_key), env.REVIEW_KEY_HASH)) failure('unauthorized', 401);
  const account = await env.DB.prepare('SELECT id FROM households WHERE id=? AND disabled=0').bind(env.REVIEW_TENANT_ID).first();
  if (!account) failure('review_not_ready', 503);
  const code = random();
  await env.DB.prepare('INSERT INTO pair_codes(hash,tenant,expires) VALUES(?,?,?)').bind(await hash(code), account.id, now() + 600).run();
  return html(`<p>Copy this one-time code into the skill's account-linking form in the Alexa app. It is valid for ten minutes and grants read access only to synthetic demo measurements.</p><pre>${code}</pre><p>You can generate a fresh code here for each test.</p>`);
}
