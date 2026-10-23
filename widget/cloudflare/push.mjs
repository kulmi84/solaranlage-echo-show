// Separate widget publisher. No Home Assistant writes or production relay changes.
export function content(data, now = Date.now()) {
  const number = (value, unit, factor = 1, limit = 10000000) =>
    typeof value === 'number' && Number.isFinite(value) && value >= 0 && value <= limit
      ? (value / factor).toLocaleString('de-DE', {maximumFractionDigits: factor === 1000 ? 2 : 0}) + ' ' + unit : '—';
  const power = value => typeof value === 'number' && value >= 1000 ? number(value, 'kW', 1000) : number(value, 'W');
  const stamp = Date.parse(data.received_at);
  if (!Number.isFinite(stamp) || stamp > now + 60000) throw Error('invalid_timestamp');
  return {production: power(data.power_w), consumption: power(data.home_w),
    battery: number(data.battery_soc, '%', 1, 100),
    status: data.demo === true ? 'DEMO · keine Live-Werte' : now - stamp > 180000 ? 'VERALTET · letzter Empfang' : 'Live-Werte',
    stand: 'Stand: ' + new Intl.DateTimeFormat('de-DE', {timeZone: data.timezone || 'Europe/Berlin',
      dateStyle: 'short', timeStyle: 'short'}).format(new Date(stamp))};
}

export function commands(device, data, now) {
  if (typeof device !== 'string' || !device.startsWith('amzn1.ask.device.')) throw Error('invalid_device');
  return {target: {type: 'DEVICES', items: [device]}, commands: [
    {type: 'PUT_OBJECT', namespace: 'Solar', key: 'live', content: content(data, now)}]};
}

export async function skillToken(env, send = (url, init) => globalThis.fetch(url, init)) {
  const response = await send('https://api.amazon.com/auth/o2/token', {
    method: 'POST', redirect: 'manual', signal: AbortSignal.timeout(8000),
    headers: {'Content-Type': 'application/x-www-form-urlencoded'},
    body: new URLSearchParams({grant_type: 'client_credentials', client_id: env.ALEXA_CLIENT_ID,
      client_secret: env.ALEXA_CLIENT_SECRET, scope: 'alexa::datastore'})});
  if (!response.ok) throw Error('lwa_' + response.status);
  const result = await response.json();
  if (typeof result.access_token !== 'string' || !result.access_token) throw Error('invalid_lwa_response');
  return result.access_token;
}

export async function push(token, device, data, send = (url, init) => globalThis.fetch(url, init)) {
  const response = await send('https://api.eu.amazonalexa.com/v1/datastore/commands', {
    method: 'POST', redirect: 'manual', signal: AbortSignal.timeout(8000),
    headers: {'Content-Type': 'application/json', Authorization: 'Bearer ' + token},
    body: JSON.stringify(commands(device, data))});
  if (!response.ok) {
    let detail;
    try { detail=await response.json(); } catch {}
    const code=detail?.type || detail?.code;
    throw Error('datastore_' + response.status + (/^[A-Z_]{1,64}$/.test(code || '') ? ':'+code : ''));
  }
  const result=await response.json();
  if (!Array.isArray(result.results) || result.results.length!==1) throw Error('datastore_invalid_response');
  if (result.results[0].type!=='SUCCESS') {
    const type=result.results[0].type;
    throw Error(/^[A-Z_]{1,64}$/.test(type || '') ? 'dispatch:'+type : 'datastore_invalid_response');
  }
  return response.status;
}
