import {connectionScope,connectionState} from './account_connection.mjs';
export const retryScope=env=>connectionScope(env) && env.CONNECTION_RETRY_PAUSE_ENABLED==='true';
export const retryClient=(data,env)=>retryScope(env) && data.connectionVersion===3;
const identity=(env,who,data)=>[env.STAGE,who,data.deviceId,data.instanceId,env.WIDGET_PACKAGE_ID];
const where='stage=? AND subject_hash=? AND device_id=? AND instance_id=? AND package_id=?';
const failureLimit=6;

async function currentRetry(db,env,who,data){
 return db.prepare('SELECT * FROM echo_value_widget_retries WHERE '+where).bind(...identity(env,who,data)).first();
}
export async function observeRetry(db,env,who,data){
 await db.prepare('INSERT INTO echo_value_widget_retries(stage,subject_hash,device_id,instance_id,package_id) VALUES(?,?,?,?,?) ON CONFLICT(stage,subject_hash,device_id,instance_id,package_id) DO NOTHING')
  .bind(...identity(env,who,data)).run();
}
export async function failedRetry(db,env,who,data,occurred,connection){
 // Duplicate/late deliveries cannot consume extra attempts. No account claim.
 await db.prepare('UPDATE echo_value_widget_retries SET failures=MIN(failures+1,?),last_attempt=? WHERE '+where+' AND last_attempt<?')
  .bind(failureLimit,occurred,...identity(env,who,data),occurred).run();
 const r=await currentRetry(db,env,who,data);
 return {...connection,revision:Math.max(connection.revision,r.resume_at),retryPaused:r.failures>=failureLimit,retryFailures:r.failures};
}
export async function verifiedRetry(db,env,who,data,connection){
 await db.prepare('UPDATE echo_value_widget_retries SET failures=0,pending=0 WHERE '+where).bind(...identity(env,who,data)).run();
 const r=await currentRetry(db,env,who,data);
 return {...connection,revision:Math.max(connection.revision,r?.resume_at||0),retryPaused:false,retryFailures:0};
}

async function sourceRow(db,env,who,deviceId,source,hash,now){
 const approved=(source.stage==='live' && source.packageId==='SolarAccountImageBuild1211' && source.packageId===env.LIVE_PACKAGE_ID)
  ||(source.stage==='development' && source.packageId==='Solaranlage1811' && source.packageId===env.TEST_PACKAGE_ID);
 if(!approved)return null;
 const row=await db.prepare('SELECT h.*,d.generation AS verified_generation,d.updated_at AS verified_at FROM echo_value_devices d JOIN echo_value_usages u ON u.stage=d.stage AND u.device_id=d.device_id AND u.subject_hash=d.subject_hash JOIN households h ON h.id=d.household WHERE d.stage=? AND d.subject_hash=? AND d.device_id=? AND d.active=1 AND u.package_id=? AND u.instance_id=? AND u.active=1 AND h.disabled=0 AND NOT EXISTS(SELECT 1 FROM echo_value_revocations r WHERE r.stage=d.stage AND r.subject_hash=d.subject_hash AND r.revoked_at>=d.updated_at) AND (EXISTS(SELECT 1 FROM access_tokens a WHERE a.tenant=h.id AND a.expires>?) OR EXISTS(SELECT 1 FROM refresh_tokens a WHERE a.tenant=h.id AND a.expires>?))')
  .bind(source.stage,who,deviceId,source.packageId,source.instanceId,Math.floor(now/1000),Math.floor(now/1000)).first();
 return row && row.id===source.household && row.verified_generation===source.generation && await hash(row.write_hash)===source.generation ? row : null;
}

export async function queueRetryResume(db,env,who,deviceId,occurred,source,hash,now){
 if(!retryScope(env))return false;
 const waiting=await db.prepare('SELECT 1 FROM echo_value_widget_retries r JOIN echo_value_widget_connections w ON w.stage=r.stage AND w.subject_hash=r.subject_hash AND w.device_id=r.device_id AND w.instance_id=r.instance_id AND w.package_id=r.package_id WHERE r.stage=? AND r.subject_hash=? AND r.device_id=? AND r.package_id=? AND r.failures>0 AND w.active=1 LIMIT 1')
  .bind(env.STAGE,who,deviceId,env.WIDGET_PACKAGE_ID).first();
 if(!waiting)return false;
 const state=await connectionState(db,env,who);
 if(state?.status==='unlinked' || (state && occurred<state.occurred_at))return;
 const authority=await sourceRow(db,env,who,deviceId,source,hash,now);
 if(!authority)return;
 const revoked=await db.prepare('SELECT revoked_at FROM echo_value_revocations WHERE stage=? AND subject_hash=?').bind(env.STAGE,who).first();
 if(revoked){
  const linkedAfter=state?.status==='linked' && state.occurred_at>revoked.revoked_at;
  const currentStore=source.stage===env.STAGE && source.packageId===env.WIDGET_PACKAGE_ID && authority.verified_at>revoked.revoked_at;
  if(occurred<=revoked.revoked_at || (!linkedAfter && !currentStore))return;
 }
 // Only opted-in, failed, still-installed instances on THIS exact device.
 const changed=await db.prepare('UPDATE echo_value_widget_retries SET resume_at=?,resume_household=?,resume_generation=?,source_stage=?,source_package=?,source_instance=?,failures=0,pending=1,attempt_at=0 WHERE stage=? AND subject_hash=? AND device_id=? AND package_id=? AND failures>0 AND resume_at<? AND EXISTS(SELECT 1 FROM echo_value_widget_connections w WHERE w.stage=echo_value_widget_retries.stage AND w.subject_hash=echo_value_widget_retries.subject_hash AND w.device_id=echo_value_widget_retries.device_id AND w.instance_id=echo_value_widget_retries.instance_id AND w.package_id=echo_value_widget_retries.package_id AND w.active=1 AND w.seen_at<=?)')
  .bind(occurred,authority.id,source.generation,source.stage,source.packageId,source.instanceId,env.STAGE,who,deviceId,env.WIDGET_PACKAGE_ID,occurred,occurred).run();
 return !!changed.meta.changes;
}

export async function retryAuthority(db,env,who,data,occurred,hash,now){
 if(!retryClient(data,env))return null;
 const r=await currentRetry(db,env,who,data);
 if(!r?.resume_at || occurred<r.resume_at)return null;
 const state=await connectionState(db,env,who);
 if(state?.status==='unlinked')return null;
 const revoked=await db.prepare('SELECT revoked_at FROM echo_value_revocations WHERE stage=? AND subject_hash=?').bind(env.STAGE,who).first();
 if(revoked && revoked.revoked_at>=r.resume_at)return null;
 return sourceRow(db,env,who,data.deviceId,{stage:r.source_stage,packageId:r.source_package,instanceId:r.source_instance,household:r.resume_household,generation:r.resume_generation},hash,now);
}

export async function flushRetrySignals(db,env,now,hash,deliver){
 if(!retryScope(env) || env.PUBLISH_ENABLED!=='true')return;
 const rows=(await db.prepare('SELECT r.*,w.control_key FROM echo_value_widget_retries r JOIN echo_value_widget_connections w ON w.stage=r.stage AND w.subject_hash=r.subject_hash AND w.device_id=r.device_id AND w.instance_id=r.instance_id AND w.package_id=r.package_id WHERE r.stage=? AND r.package_id=? AND r.pending=1 AND w.active=1 ORDER BY r.attempt_at,r.resume_at LIMIT 100')
  .bind(env.STAGE,env.WIDGET_PACKAGE_ID).all()).results;
 for(const r of rows){
  try{
   const data={connectionVersion:3,deviceId:r.device_id,instanceId:r.instance_id};
   if(await retryAuthority(db,env,r.subject_hash,data,Math.max(now,r.resume_at),hash,now)){
    await deliver(r.device_id,r.control_key,{version:1,state:'retry',revision:r.resume_at});
   }
   await db.prepare('UPDATE echo_value_widget_retries SET pending=0 WHERE '+where+' AND resume_at=?')
    .bind(...identity(env,r.subject_hash,data),r.resume_at).run();
  }catch{
   await db.prepare('UPDATE echo_value_widget_retries SET attempt_at=? WHERE '+where)
    .bind(now,...identity(env,r.subject_hash,{deviceId:r.device_id,instanceId:r.instance_id})).run();
  }
 }
}
