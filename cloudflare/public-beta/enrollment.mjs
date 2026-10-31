// Parallel, opt-in enrollment. Existing invitation, upload and OAuth routes stay intact.
const encoder = new TextEncoder();
const messages = {
  registration_not_ready: 'Die automatische Einrichtung ist noch nicht verfügbar.',
  registration_invalid: 'Die Einrichtungsanfrage ist ungültig. Bitte erneut versuchen.',
  registration_ip_unavailable: 'Die Verbindung konnte nicht geprüft werden. Bitte später erneut versuchen.',
  registration_rate_limited: 'Zu viele Einrichtungsversuche. Bitte später erneut versuchen.',
  registration_full: 'Der Dienst ist derzeit ausgelastet. Bestehende Zugänge laufen weiter.',
  registration_revoked: 'Diese Einrichtung wurde gelöscht oder gesperrt. Bitte eine neue Einrichtung starten.',
  registration_unavailable: 'Die Einrichtung ist vorübergehend nicht möglich. Bitte später erneut versuchen.',
};

async function keyed(secret, value) {
  const key = await crypto.subtle.importKey('raw', encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' }, false, ['sign']);
  return Array.from(new Uint8Array(await crypto.subtle.sign('HMAC', key, encoder.encode(value))),
    n => n.toString(16).padStart(2, '0')).join('');
}

function sourceIP(request) {
  // Only the Cloudflare-provided client address, never caller-supplied forwarding headers.
  const raw = request.headers.get('CF-Connecting-IP');
  if (!raw || raw.length > 45) return null;
  if (/^(0|[1-9]\d{0,2})(\.(0|[1-9]\d{0,2})){3}$/.test(raw))
    return raw.split('.').every(n => Number(n) <= 255) ? raw : null;
  if (!raw.includes(':') || !/^[0-9a-f:.]+$/i.test(raw)) return null;
  try { return new URL('http://[' + raw + ']').hostname.slice(1, -1); }
  catch { return null; }
}

function setting(value, fallback, ceiling) {
  if (value == null) return fallback;
  if (!/^[1-9]\d*$/.test(String(value))) return null;
  const number = Number(value);
  return Number.isSafeInteger(number) && number <= ceiling ? number : null;
}

export async function publicEnrollment(request, env, helpers) {
  const respond = (code, status, retry = null) => Response.json(
    messages[code] ? { error: code, message: messages[code] } : { error: code },
    { status, headers: { ...helpers.headers, ...(retry ? { 'Retry-After': String(retry) } : {}) } });
  if (env.PUBLIC_ENROLLMENT_ENABLED !== 'true') return respond('not_found', 404);
  if (request.method !== 'POST') return respond('method_not_allowed', 405);
  const hourly = setting(env.ENROLLMENT_HOURLY_LIMIT, 3, 10);
  const daily = setting(env.ENROLLMENT_DAILY_LIMIT, 10, 30);
  const capacity = setting(env.MAX_HOUSEHOLDS, 20, 20);
  if (!hourly || !daily || !capacity || !env.SIGNUP_LIMITER || !env.DB
      || typeof env.REGISTRATION_KEY !== 'string' || env.REGISTRATION_KEY.length < 32)
    return respond('registration_not_ready', 503);
  const ip = sourceIP(request);
  if (!ip) return respond('registration_ip_unavailable', 400);
  try {
    const subject = await keyed(env.REGISTRATION_KEY, 'enrollment-ip:v1:' + ip);
    const burst = await env.SIGNUP_LIMITER.limit({ key: subject });
    if (!burst.success) return respond('registration_rate_limited', 429, 60);
    const input = await helpers.body(request);
    if (!input || typeof input !== 'object' || Array.isArray(input)
        || typeof input.installation_key !== 'string'
        || !/^[a-f0-9]{64}$/.test(input.installation_key || '')
        || typeof input.timezone !== 'string' || input.timezone.length > 80)
      return respond('registration_invalid', 400);
    try { new Intl.DateTimeFormat('en', { timeZone: input.timezone }).format(); }
    catch { return respond('registration_invalid', 400); }
    // HA generates and retains this random setup key before its first request.
    // Derivation makes a lost response retryable; only hashes enter the database.
    const keyHash = await helpers.hash(input.installation_key);
    const write = await keyed(env.REGISTRATION_KEY, 'enrollment-writer:v1:' + input.installation_key);
    const writeHash = await helpers.hash(write);
    const lookup = () => env.DB.prepare(
      'SELECT k.tenant,h.write_hash,h.disabled FROM enrollment_keys k LEFT JOIN households h ON h.id=k.tenant WHERE k.key_hash=?'
    ).bind(keyHash).first();
    const recover = row => {
      if (!row) return null;
      if (!row.tenant || row.disabled) return respond('registration_revoked', 410);
      // A changed server derivation key cannot silently replace an existing writer.
      if (row.write_hash !== writeHash) return respond('registration_unavailable', 503);
      return Response.json({ tenant_id: row.tenant, write_token: write },
        { status: 200, headers: helpers.headers });
    };
    const previous = recover(await lookup());
    if (previous) return previous;
    const now = helpers.now(), hour = Math.floor(now / 3600) * 3600, day = Math.floor(now / 86400) * 86400;
    const id = crypto.randomUUID();
    // One transactional batch: predicate, account, retry record and quota updates.
    // No allowance is consumed for a failed insert or an idempotent retry.
    const result = await env.DB.batch([
      env.DB.prepare(`INSERT INTO households(id,write_hash,timezone,created)
        SELECT ?,?,?,? WHERE NOT EXISTS(SELECT 1 FROM enrollment_keys WHERE key_hash=?)
        AND NOT EXISTS(SELECT 1 FROM households WHERE write_hash=?)
        AND (SELECT COUNT(*) FROM households) < ?
        AND COALESCE((SELECT registrations FROM enrollment_limits WHERE kind='hour' AND subject=? AND period_start=?),0) < ?
        AND COALESCE((SELECT registrations FROM enrollment_limits WHERE kind='day' AND subject=? AND period_start=?),0) < ?`)
        .bind(id, writeHash, input.timezone, now, keyHash, writeHash, capacity, subject, hour, hourly, subject, day, daily),
      env.DB.prepare('INSERT INTO enrollment_keys(key_hash,tenant,created) SELECT ?,?,? WHERE EXISTS(SELECT 1 FROM households WHERE id=?)')
        .bind(keyHash, id, now, id),
      ...[['hour', hour, hour + 3600], ['day', day, day + 86400]].map(([kind, period, expires]) =>
        env.DB.prepare(`INSERT INTO enrollment_limits(kind,subject,period_start,registrations,expires)
          SELECT ?,?,?,1,? WHERE EXISTS(SELECT 1 FROM households WHERE id=?)
          ON CONFLICT(kind,subject,period_start) DO UPDATE SET registrations=registrations+1`)
          .bind(kind, subject, period, expires, id)),
      env.DB.prepare('DELETE FROM enrollment_limits WHERE expires<=?').bind(now),
    ]);
    if (result[0].meta.changes) return Response.json({ tenant_id: id, write_token: write },
      { status: 201, headers: helpers.headers });
    const raced = recover(await lookup());
    if (raced) return raced;
    const total = await env.DB.prepare('SELECT COUNT(*) AS total FROM households').bind().first();
    if (total.total >= capacity) return respond('registration_full', 503, 3600);
    const used = await env.DB.prepare('SELECT kind,registrations FROM enrollment_limits WHERE subject=? AND ((kind=\'hour\' AND period_start=?) OR (kind=\'day\' AND period_start=?))')
      .bind(subject, hour, day).all();
    if (used.results.some(r => r.kind === 'day' && r.registrations >= daily))
      return respond('registration_rate_limited', 429, day + 86400 - now);
    if (used.results.some(r => r.kind === 'hour' && r.registrations >= hourly))
      return respond('registration_rate_limited', 429, hour + 3600 - now);
    return respond('registration_unavailable', 503, 60);
  } catch (error) {
    // Keep raw IP, body, keys, tokens and SQL details out of responses/logs.
    if ([400, 413, 415].includes(error?.status)) return respond('registration_invalid', error.status);
    return respond('registration_unavailable', 503, 60);
  }
}

export async function cleanupEnrollmentLimits(env, timestamp) {
  if (env.PUBLIC_ENROLLMENT_ENABLED === 'true')
    await env.DB.prepare('DELETE FROM enrollment_limits WHERE expires<=?').bind(timestamp).run();
}
