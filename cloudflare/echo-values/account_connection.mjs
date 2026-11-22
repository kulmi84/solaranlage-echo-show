// Installation observations are wake destinations, NEVER household authority.
// Only authenticated lifecycle/link events or a valid OAuth registration set state.
export const connectionScope = env => env.CONNECTION_STATUS_ENABLED === 'true' && ['live','development'].includes(env.STAGE)
  && env.WIDGET_PACKAGE_ID === 'SolarAccountImageBuild1211'
  && env.DATASTORE_NAMESPACE === 'SolarAccountImagesV3';
export const connectionClient = (data, env) => connectionScope(env) && data.connectionVersion === 2;

export async function observeConnection(db, env, data, who, occurred, hash) {
  const key = 'connection-' + await hash(JSON.stringify([env.STAGE, who, data.deviceId, data.instanceId, data.packageId]));
  // An explicit removal is not undone by a tokenless refresh.
  await db.prepare('INSERT INTO echo_value_widget_connections(stage,subject_hash,device_id,instance_id,package_id,control_key,active,seen_at,pending) VALUES(?,?,?,?,?,?,1,?,0) ON CONFLICT(stage,subject_hash,device_id,instance_id,package_id) DO NOTHING')
    .bind(env.STAGE, who, data.deviceId, data.instanceId, data.packageId, key, occurred).run();
  return db.prepare('SELECT * FROM echo_value_widget_connections WHERE stage=? AND subject_hash=? AND device_id=? AND instance_id=? AND package_id=?')
    .bind(env.STAGE, who, data.deviceId, data.instanceId, data.packageId).first();
}

export async function connectionState(db, env, who) {
  return db.prepare('SELECT * FROM echo_value_link_states WHERE stage=? AND subject_hash=?')
    .bind(env.STAGE, who).first();
}

export function connectionReply(observation, state) {
  if (!observation?.active) return null;
  return {key: observation.control_key, state: state?.status || 'unknown', revision: state?.occurred_at || 0};
}

export async function setConnectionState(db, env, who, status, occurred, row = null, source = 'event') {
  if (!connectionScope(env)) return;
  await db.batch([
    db.prepare('INSERT INTO echo_value_link_states(stage,subject_hash,status,occurred_at,household,generation,source) VALUES(?,?,?,?,?,?,?) ON CONFLICT(stage,subject_hash) DO UPDATE SET status=excluded.status,occurred_at=excluded.occurred_at,household=excluded.household,generation=excluded.generation,source=excluded.source WHERE excluded.occurred_at>echo_value_link_states.occurred_at OR (excluded.occurred_at=echo_value_link_states.occurred_at AND excluded.status=\'unlinked\')')
      .bind(env.STAGE, who, status, occurred, row?.id || null, row?.generation || null, source),
    db.prepare('UPDATE echo_value_widget_connections SET pending=1,attempt_at=0 WHERE stage=? AND subject_hash=? AND active=1 AND ?=1 AND EXISTS(SELECT 1 FROM echo_value_link_states s WHERE s.stage=? AND s.subject_hash=? AND s.status=? AND s.occurred_at=?)')
      .bind(env.STAGE, who, source === 'event' ? 1 : 0, env.STAGE, who, status, occurred)
  ]);
}

export async function removeConnections(db, env, data, who, occurred) {
  if (!connectionScope(env)) return;
  await db.prepare('UPDATE echo_value_widget_connections SET active=0,pending=0,seen_at=? WHERE stage=? AND subject_hash=? AND device_id=? AND package_id=? AND (?=1 OR instance_id=?) AND seen_at<=?')
    .bind(occurred, env.STAGE, who, data.deviceId, data.packageId, data.removeAll === true ? 1 : 0, data.instanceId || '', occurred).run();
}

// This is a fresh link-event authority plus a fresh authenticated widget event.
// It does not turn an old stored device/usage into a current authorization.
export async function linkedConnectionRow(db, env, who, occurred, hash, now) {
  const state = await connectionState(db, env, who);
  if (state?.status !== 'linked' || state.source !== 'event' || occurred < state.occurred_at) return null;
  const revoked = await db.prepare('SELECT revoked_at FROM echo_value_revocations WHERE stage=? AND subject_hash=?').bind(env.STAGE, who).first();
  if (revoked && state.occurred_at <= revoked.revoked_at) return null;
  const row = await db.prepare('SELECT h.* FROM households h WHERE h.id=? AND h.disabled=0 AND (EXISTS(SELECT 1 FROM access_tokens a WHERE a.tenant=h.id AND a.expires>?) OR EXISTS(SELECT 1 FROM refresh_tokens a WHERE a.tenant=h.id AND a.expires>?))')
    .bind(state.household, Math.floor(now/1000), Math.floor(now/1000)).first();
  return row && await hash(row.write_hash) === state.generation ? row : null;
}

export async function flushConnectionSignals(db, env, now, deliver) {
  if (!connectionScope(env) || env.PUBLISH_ENABLED !== 'true') return {accepted:0,failed:0};
  // Bounded outbox retries on the existing cron. No additional poll/household read.
  const rows = (await db.prepare('SELECT w.*,s.status,s.occurred_at FROM echo_value_widget_connections w JOIN echo_value_link_states s ON s.stage=w.stage AND s.subject_hash=w.subject_hash WHERE w.stage=? AND w.package_id=? AND w.active=1 AND w.pending=1 ORDER BY w.attempt_at,w.seen_at LIMIT 100')
    .bind(env.STAGE, env.WIDGET_PACKAGE_ID).all()).results;
  let accepted=0, failed=0;
  for (const row of rows) {
    try {
      await deliver(row.device_id, row.control_key, {version:1,state:row.status,revision:row.occurred_at});
      await db.prepare('UPDATE echo_value_widget_connections SET pending=0 WHERE stage=? AND subject_hash=? AND device_id=? AND instance_id=? AND package_id=? AND EXISTS(SELECT 1 FROM echo_value_link_states s WHERE s.stage=? AND s.subject_hash=? AND s.occurred_at=? AND s.status=?)')
        .bind(env.STAGE,row.subject_hash,row.device_id,row.instance_id,row.package_id,env.STAGE,row.subject_hash,row.occurred_at,row.status).run();
      accepted++;
    } catch {
      await db.prepare('UPDATE echo_value_widget_connections SET attempt_at=? WHERE stage=? AND subject_hash=? AND device_id=? AND instance_id=? AND package_id=?')
        .bind(now,env.STAGE,row.subject_hash,row.device_id,row.instance_id,row.package_id).run();
      failed++;
    }
  }
  return {accepted,failed};
}
