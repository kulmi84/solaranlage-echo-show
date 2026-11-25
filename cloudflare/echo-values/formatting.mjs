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



const store = "https://api.eu.amazonalexa.com/v1/datastore/commands";
const hex = bytes => Array.from(new Uint8Array(bytes), b => b.toString(16).padStart(2, "0")).join("");
const digest = async value => hex(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value)));

export function snapshot(row, now) {
  const data = JSON.parse(row.live_json);
  const at = Date.parse(row.live_at);
  if (!Number.isFinite(at) || at > now + 60000) throw Error("invalid_timestamp");
  const number = (value, maximum) => {
    if (!Number.isFinite(value) || value < 0 || value > maximum) throw Error("invalid_measurement");
    return value;
  };
  const formatted = (value, digits) => new Intl.NumberFormat("de-DE", {
    useGrouping: false, minimumFractionDigits: digits, maximumFractionDigits: digits,
    roundingMode: "halfExpand"
  }).format(value);
  const power = key => {
    const value = number(data[key], 10000000);
    return value >= 1000 ? formatted(value / 1000, 2) + " kW" : formatted(value, 0) + " W";
  };
  const parts = new Intl.DateTimeFormat("de-DE", {
    timeZone: row.timezone || "Europe/Berlin", day: "2-digit", month: "2-digit",
    year: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23"
  }).formatToParts(at);
  const part = key => parts.find(p => p.type === key).value;
  const stale = now - at > 180000;
  return {solar: power("power_w"), home: power("home_w"),
    battery: formatted(number(data.battery_soc, 100), 0) + " %",
    stamp: (stale ? "Veraltet: " : "Stand: ") + `${part("day")}.${part("month")}.${part("year")}, ${part("hour")}:${part("minute")}`,
    sampleTime: at, stale};
}

export async function sendSnapshot(env, now = Date.now(), send = fetch, observe = () => {}) {
  observe("configuration");
  const {device, household, generation} = JSON.parse(env.DEV_TARGET);
  if (!(typeof device === "string" && /^amzn1\.ask\.device\.[A-Za-z0-9_.-]+$/.test(device))
      || typeof household !== "string" || !household || !/^[a-f0-9]{64}$/.test(generation)) return "unregistered";
  observe("d1");
  const row = await env.SOURCE_DB.prepare(
    "SELECT write_hash,timezone,live_at,live_json FROM households WHERE id=? AND disabled=0"
  ).bind(household).first();
  if (!row || await digest(row.write_hash) !== generation) return "revoked";
  observe("format");
  const content = snapshot(row, now);
  observe("amazon_token");
  const token = await skillToken(env, send);
  observe("amazon_datastore");
  const response = await send(store, {
    method: "POST", redirect: "manual", signal: AbortSignal.timeout(5000),
    headers: {"Content-Type": "application/json", Authorization: "Bearer " + token},
    body: JSON.stringify({target: {type: "DEVICES", items: [device]}, commands: [
      {type: "PUT_OBJECT", namespace: "SolarDirectValuesDev", key: "snapshot", content}
    ]})
  });
  if (!response.ok) throw Error("datastore_" + response.status);
  const {results} = await response.json();
  if (results?.length !== 1 || results[0].deviceId !== device || results[0].type !== "SUCCESS")
    throw Error("datastore_not_confirmed");
  return "accepted";
}


export async function readLinkedSnapshot(request, env, now = Date.now(), observe = () => {}) {
  const reply = (body, status) => Response.json(body, {status, headers: {"Cache-Control": "no-store"}});
  if (new URL(request.url).pathname !== "/v1/pv") return reply({error: "not_found"}, 404);
  if (request.method !== "GET") return reply({error: "method_not_allowed"}, 405);
  const authorization = request.headers.get("Authorization") || "";
  if (!/^Bearer [a-f0-9]{64}$/.test(authorization)) return reply({error: "unauthorized"}, 401);
  const {household, generation} = JSON.parse(env.DEV_TARGET);
  if (typeof household !== "string" || !household || !/^[a-f0-9]{64}$/.test(generation))
    return reply({error: "unavailable"}, 503);
  observe("d1");
  const row = await env.SOURCE_DB.prepare(
    "SELECT h.write_hash,h.timezone,h.live_at,h.live_json,h.history_at,h.history_json FROM households h "
    + "JOIN access_tokens a ON h.id=a.tenant WHERE a.hash=? AND a.expires>? AND h.id=? AND h.disabled=0"
  ).bind(await digest(authorization.slice(7)), Math.floor(now / 1000), household).first();
  if (!row || await digest(row.write_hash) !== generation) return reply({error: "unauthorized"}, 401);
  if (!row.live_json) return reply({error: "no_data"}, 404);
  const data = JSON.parse(row.live_json);
  const parts = new Intl.DateTimeFormat("en-CA", {timeZone: row.timezone || "Europe/Berlin",
    year: "numeric", month: "2-digit", day: "2-digit"}).formatToParts(now);
  const part = key => parts.find(p => p.type === key).value;
  return reply({...data, received_at: row.live_at,
    local_date: part("year")+"-"+part("month")+"-"+part("day"),
    received_local: new Intl.DateTimeFormat("en-GB", {timeZone: row.timezone || "Europe/Berlin",
      hour: "2-digit", minute: "2-digit", hour12: false}).format(new Date(row.live_at)),
    history: row.history_json ? {...JSON.parse(row.history_json), received_at: row.history_at} : null
  }, 200);
}

export default {
  async fetch(request, env) {
    let queries = 0;
    let response;
    try {
      response = await readLinkedSnapshot(request, env, Date.now(), () => { queries++; });
    } catch {
      response = Response.json({error: "unavailable"}, {status: 503, headers: {"Cache-Control": "no-store"}});
    }
    console.log(JSON.stringify({event: "solar_dev_fullscreen_fetch", status: response.status,
      workerInvocations: 1, d1Queries: queries, internalWorkerRequests: 0, imageRequests: 0}));
    return response;
  },
  async scheduled(controller, env) {
    let phase = "start";
    const counts = {workerInvocations: 1, d1Queries: 0, amazonRequests: 0, internalWorkerRequests: 0, imageRequests: 0};
    const measuredSend = (url, init) => {
      const host = new URL(url).hostname;
      if (!["api.amazon.com", "api.eu.amazonalexa.com"].includes(host)) throw Error("unexpected_destination");
      counts.amazonRequests++;
      return globalThis.fetch(url, init);
    };
    try {
      const result = await sendSnapshot(env, controller.scheduledTime, measuredSend, value => { phase = value; if (value === "d1") counts.d1Queries++; });
      console.log(JSON.stringify({event: "solar_dev_text_push", result, ...counts}));
    } catch (error) {
      console.log(JSON.stringify({event: "solar_dev_text_push", result: "failed", phase, ...counts, reason: /^(lwa_\d{3}|datastore_\d{3}|datastore_not_confirmed|invalid_lwa_response|invalid_timestamp|invalid_measurement)$/.test(error?.message) ? error.message : error?.name === "TypeError" ? /redirect/i.test(error.message) ? "redirect_type_error" : /fetch|network|connection/i.test(error.message) ? "fetch_type_error" : "TypeError" : error?.name === "TimeoutError" ? "timeout" : "other"}));
    }
  }
};






