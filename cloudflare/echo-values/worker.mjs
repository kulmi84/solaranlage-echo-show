// Prepared migration candidate. No automatic deployment or household backfill.
import {snapshot, skillToken} from '../../experiments/direct-values-dev/worker.mjs';

const utf8 = value => new TextEncoder().encode(value);
export const digest = async value => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',utf8(value))),b=>b.toString(16).padStart(2,'0')).join('');
const reply = (data,status=200) => Response.json(data,{status,headers:{'Cache-Control':'no-store'}});
const fail = (status,code) => {throw Object.assign(Error(code),{status,code});};
async function internal(request,env) {
  if (typeof env.REGISTRATION_SECRET!=='string' || env.REGISTRATION_SECRET.length<32) fail(503,'not_configured');
  const actual=await digest(request.headers.get('X-Solar-Registration')||'');
  const expected=await digest(env.REGISTRATION_SECRET);
  let diff=0; for(let i=0;i<actual.length;i++) diff|=actual.charCodeAt(i)^expected.charCodeAt(i);
  if(diff) fail(401,'unauthorized');
}
async function body(request) {
  const reader=request.body?.getReader(); if(!reader) fail(400,'invalid_body');
  let size=0;const chunks=[];
  while(true){const part=await reader.read();if(part.done)break;size+=part.value.length;
    if(size>8192){await reader.cancel();fail(413,'too_large');}chunks.push(part.value);}
  const bytes=new Uint8Array(size);let at=0;for(const c of chunks){bytes.set(c,at);at+=c.length;}
  try{return JSON.parse(new TextDecoder().decode(bytes));}catch{fail(400,'invalid_body');}
}
function scope(data,env,now) {
  if(!['live','development'].includes(env.STAGE) || !env.WIDGET_PACKAGE_ID || (typeof env.SUBJECT_HASH_KEY!=='string' || env.SUBJECT_HASH_KEY.length<32)) fail(503,'not_configured');
  if(data.stage!==env.STAGE || data.packageId!==env.WIDGET_PACKAGE_ID) fail(403,'wrong_scope');
  if(typeof data.userId!=='string'||!/^amzn1\.ask\.account\.[A-Za-z0-9_.-]{1,400}$/.test(data.userId))fail(400,'invalid_user');
  const occurred=Date.parse(data.occurredAt);
  if(!Number.isFinite(occurred)||occurred>now+60000||occurred<now-300000)fail(400,'invalid_event_time');
  return occurred;
}
async function subject(user,env) {
  const key=await crypto.subtle.importKey('raw',utf8(env.SUBJECT_HASH_KEY),{name:'HMAC',hash:'SHA-256'},false,['sign']);
  return Array.from(new Uint8Array(await crypto.subtle.sign('HMAC',key,utf8(user))),b=>b.toString(16).padStart(2,'0')).join('');
}
function device(data,requireInstance=true) {
  if(typeof data.deviceId!=='string'||!/^amzn1\.ask\.device\.[A-Za-z0-9_.-]{1,500}$/.test(data.deviceId))fail(400,'invalid_device');
  if(requireInstance && (typeof data.instanceId!=='string'||!data.instanceId||data.instanceId.length>500))fail(400,'instance_required');
}
export async function linked(request,env,now) {
  const auth=request.headers.get('Authorization')||'';
  if(!/^Bearer [a-f0-9]{64}$/.test(auth))fail(401,'unauthorized');
  const row=await env.DB.prepare('SELECT h.* FROM households h JOIN access_tokens a ON h.id=a.tenant WHERE a.hash=? AND a.expires>? AND h.disabled=0')
    .bind(await digest(auth.slice(7)),Math.floor(now/1000)).first();
  if(!row)fail(401,'unauthorized');
  return row;
}
async function registerUnlocked(request,env,now=Date.now()) {
  await internal(request,env);const data=await body(request),occurred=scope(data,env,now);device(data);
  const row=await linked(request,env,now),who=await subject(data.userId,env),generation=await digest(row.write_hash);
  const revoked=await env.DB.prepare('SELECT revoked_at FROM echo_value_revocations WHERE stage=? AND subject_hash=?').bind(env.STAGE,who).first();
  if(revoked && occurred<=revoked.revoked_at)fail(409,'stale_event');
  const results=await env.DB.batch([
    env.DB.prepare('INSERT INTO echo_value_devices(stage,device_id,subject_hash,household,generation,active,updated_at) SELECT ?,?,?,?,?,1,? WHERE NOT EXISTS(SELECT 1 FROM echo_value_revocations WHERE stage=? AND subject_hash=? AND revoked_at>=?) ON CONFLICT(stage,device_id) DO UPDATE SET subject_hash=excluded.subject_hash,household=excluded.household,generation=excluded.generation,active=1,updated_at=excluded.updated_at WHERE excluded.updated_at>=echo_value_devices.updated_at').bind(env.STAGE,data.deviceId,who,row.id,generation,occurred,env.STAGE,who,occurred),
    env.DB.prepare('DELETE FROM echo_value_usages WHERE stage=? AND device_id=? AND subject_hash<>? AND EXISTS(SELECT 1 FROM echo_value_devices d WHERE d.stage=? AND d.device_id=? AND d.subject_hash=? AND d.updated_at=?)').bind(env.STAGE,data.deviceId,who,env.STAGE,data.deviceId,who,occurred),
    env.DB.prepare('INSERT INTO echo_value_usages(stage,device_id,instance_id,package_id,subject_hash,active,updated_at) SELECT ?,?,?,?,?,1,? WHERE EXISTS(SELECT 1 FROM echo_value_devices WHERE stage=? AND device_id=? AND subject_hash=? AND updated_at=?) ON CONFLICT(stage,device_id,instance_id) DO UPDATE SET package_id=excluded.package_id,subject_hash=excluded.subject_hash,active=1,updated_at=excluded.updated_at WHERE excluded.updated_at>echo_value_usages.updated_at OR (excluded.updated_at=echo_value_usages.updated_at AND echo_value_usages.active=1)').bind(env.STAGE,data.deviceId,data.instanceId,data.packageId,who,occurred,env.STAGE,data.deviceId,who,occurred)
  ]);
  if(!results[0].meta.changes||!results[2].meta.changes)fail(409,'stale_event');
  let initial;try{initial={...snapshot(row,now),binding:await digest(JSON.stringify([env.STAGE,who,row.id,generation]))};}catch{}
  return reply({registered:true,binding:await digest(JSON.stringify([env.STAGE,who,row.id,generation])),...(initial?{snapshot:initial}:{})});
}
async function removeUnlocked(request,env,now=Date.now()) {
  await internal(request,env);const data=await body(request),occurred=scope(data,env,now);device(data,data.removeAll!==true);
  const who=await subject(data.userId,env);
  await env.DB.prepare('UPDATE echo_value_usages SET active=0,updated_at=? WHERE stage=? AND device_id=? AND package_id=? AND (?=1 OR instance_id=?) AND subject_hash=? AND updated_at<=?')
    .bind(occurred,env.STAGE,data.deviceId,env.WIDGET_PACKAGE_ID,data.removeAll===true?1:0,data.instanceId||'',who,occurred).run();
  return reply({removed:true});
}
async function unlinkUnlocked(request,env,now=Date.now()) {
  await internal(request,env);const data=await body(request),occurred=scope(data,env,now);
  const who=await subject(data.userId,env);
  await env.DB.batch([
    env.DB.prepare('INSERT INTO echo_value_revocations(stage,subject_hash,revoked_at) VALUES(?,?,?) ON CONFLICT(stage,subject_hash) DO UPDATE SET revoked_at=MAX(revoked_at,excluded.revoked_at)').bind(env.STAGE,who,occurred),
    env.DB.prepare('UPDATE echo_value_devices SET active=0,updated_at=? WHERE stage=? AND subject_hash=? AND updated_at<=?').bind(occurred,env.STAGE,who,occurred),
    env.DB.prepare('UPDATE echo_value_usages SET active=0,updated_at=? WHERE stage=? AND subject_hash=? AND updated_at<=?').bind(occurred,env.STAGE,who,occurred)
  ]);
  return reply({unlinked:true});
}
async function relinkUnlocked(request,env,now){
 await internal(request,env);const data=await body(request),occurred=scope(data,env,now);
 const row=await linked(request,env,now),who=await subject(data.userId,env),generation=await digest(row.write_hash);
 await env.DB.prepare('UPDATE echo_value_devices SET household=?,generation=?,updated_at=? WHERE stage=? AND subject_hash=? AND active=1 AND updated_at<=? AND NOT EXISTS(SELECT 1 FROM echo_value_revocations r WHERE r.stage=? AND r.subject_hash=? AND r.revoked_at>=?)').bind(row.id,generation,occurred,env.STAGE,who,occurred,env.STAGE,who,occurred).run();
 return reply({relinked:true});
}
export async function read(request,env,now=Date.now()) {
  const row=await linked(request,env,now);if(!row.live_json)fail(404,'no_data');
  const parts=new Intl.DateTimeFormat('en-CA',{timeZone:row.timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(now);
  const part=key=>parts.find(p=>p.type===key).value;
  return reply({...JSON.parse(row.live_json),received_at:row.live_at,local_date:part('year')+'-'+part('month')+'-'+part('day'),
    received_local:new Intl.DateTimeFormat('en-GB',{timeZone:row.timezone,hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(row.live_at)),
    history:row.history_json?{...JSON.parse(row.history_json),received_at:row.history_at}:null});
}
async function publishUnlocked(env,now=Date.now(),send=(url,init)=>globalThis.fetch(url,init)) {
  if(env.PUBLISH_ENABLED!=='true')return {enabled:false,accepted:0,failed:0,households:0};
  if(!env.WIDGET_PACKAGE_ID||!env.DATASTORE_NAMESPACE||!env.DATASTORE_KEY||!['live','development'].includes(env.STAGE))fail(503,'not_configured');
  const cursor=await env.DB.prepare('SELECT device_id FROM echo_value_publish_cursor WHERE stage=?').bind(env.STAGE).first();
  const started=Date.now();
  const {results}=await env.DB.prepare('SELECT d.device_id,d.household,d.subject_hash,d.updated_at,d.generation,h.write_hash,h.timezone,h.live_at,h.live_json FROM echo_value_devices d JOIN households h ON h.id=d.household WHERE d.stage=? AND d.active=1 AND h.disabled=0 AND EXISTS(SELECT 1 FROM echo_value_usages u WHERE u.stage=d.stage AND u.device_id=d.device_id AND u.subject_hash=d.subject_hash AND u.active=1 AND u.package_id=?) ORDER BY CASE WHEN d.device_id>? THEN 0 ELSE 1 END,d.device_id LIMIT 100').bind(env.STAGE,env.WIDGET_PACKAGE_ID,cursor?.device_id||'').all();
  const groups=new Map();let failed=0;
  for(const row of results){if(await digest(row.write_hash)!==row.generation)continue;
    const groupKey=JSON.stringify([row.household,row.subject_hash]);
    if(!groups.has(groupKey))groups.set(groupKey,{row,devices:[]});
    groups.get(groupKey).devices.push(row);}
  if(!groups.size)return {enabled:true,accepted:0,failed:0,households:0};
  const token=await skillToken(env,async(url,init)=>{const response=await send(url,init);if(!response.ok)return response;return Response.json(await boundedResponse(response));});let accepted=0;
  for(const {row,devices} of groups.values()){
    let content;try{content={...snapshot(row,now),binding:await digest(JSON.stringify([env.STAGE,row.subject_hash,row.household,row.generation]))};}catch{failed+=devices.length;continue;}
    for(let at=0;at<devices.length;at+=20){
      if(Date.now()-started>40000)break;
      const selected=devices.slice(at,at+20),targets=[];
      // The stage lease blocks concurrent adapter mutations. Re-read ownership and
      // household generation as a second guard before crossing the Amazon boundary.
      const freshRows=(await env.DB.prepare('SELECT d.device_id,d.subject_hash,d.household,d.generation,d.updated_at,h.write_hash,h.disabled FROM echo_value_devices d JOIN households h ON h.id=d.household WHERE d.stage=? AND d.device_id IN ('+selected.map(()=>'?').join(',')+') AND d.active=1 AND EXISTS(SELECT 1 FROM echo_value_usages u WHERE u.stage=d.stage AND u.device_id=d.device_id AND u.active=1 AND u.subject_hash=d.subject_hash AND u.package_id=?)').bind(env.STAGE,...selected.map(r=>r.device_id),env.WIDGET_PACKAGE_ID).all()).results;
      for(const expected of selected){
        const fresh=freshRows.find(r=>r.device_id===expected.device_id);
        if(fresh && !fresh.disabled && fresh.subject_hash===expected.subject_hash && fresh.household===expected.household && fresh.updated_at===expected.updated_at && fresh.generation===expected.generation && fresh.generation===await digest(fresh.write_hash))targets.push(expected.device_id);
      }
      if(!targets.length)continue;
      try{
        const response=await send('https://api.eu.amazonalexa.com/v1/datastore/commands',{method:'POST',redirect:'manual',signal:AbortSignal.timeout(5000),
          headers:{'Content-Type':'application/json',Authorization:'Bearer '+token},
          body:JSON.stringify({target:{type:'DEVICES',items:targets},commands:[{type:'PUT_OBJECT',namespace:env.DATASTORE_NAMESPACE,key:env.DATASTORE_KEY,content}]})});
        if(!response.ok)throw Error('delivery_failed');
        const body=await boundedResponse(response);
        const ok=new Set((body.results||[]).filter(r=>targets.includes(r.deviceId)&&r.type==='SUCCESS').map(r=>r.deviceId));
        accepted+=ok.size;failed+=targets.length-ok.size;
      }catch{failed+=targets.length;}
    }
  }
  if(results.length)await env.DB.prepare('INSERT INTO echo_value_publish_cursor(stage,device_id) VALUES(?,?) ON CONFLICT(stage) DO UPDATE SET device_id=excluded.device_id').bind(env.STAGE,results[results.length-1].device_id).run();
  return {enabled:true,accepted,failed,households:groups.size,selected:results.length};
}
// A finite lease serializes all mutations and outbound writes for this stage.
// No retry inside a cron run: failures retain the previous object; next minute retries.
async function boundedResponse(response){
 const reader=response.body?.getReader();if(!reader)throw Error('empty_response');
 let size=0;const chunks=[];
 while(true){const r=await reader.read();if(r.done)break;size+=r.value.length;if(size>65536){await reader.cancel();throw Error('response_too_large');}chunks.push(r.value);}
 const bytes=new Uint8Array(size);let at=0;for(const c of chunks){bytes.set(c,at);at+=c.length;}
 return JSON.parse(new TextDecoder().decode(bytes));
}
async function locked(env,action){
 const owner=crypto.randomUUID(),clock=Date.now();
 const result=await env.DB.prepare('INSERT INTO echo_value_locks(stage,owner,expires) VALUES(?,?,?) ON CONFLICT(stage) DO UPDATE SET owner=excluded.owner,expires=excluded.expires WHERE echo_value_locks.expires<?').bind(env.STAGE,owner,clock+180000,clock).run();
 if(!result.meta.changes)fail(503,'delivery_busy');
 const guarded=async(url,init)=>{
   const lease=await env.DB.prepare('SELECT owner,expires FROM echo_value_locks WHERE stage=?').bind(env.STAGE).first();
   if(!lease||lease.owner!==owner||lease.expires<Date.now()+30000)throw Error('lease_expired');
   return env.__send(url,init);
 };
 try{return await action(guarded);}finally{await env.DB.prepare('DELETE FROM echo_value_locks WHERE stage=? AND owner=?').bind(env.STAGE,owner).run();}
}
export async function register(request,env,now=Date.now()){
 await internal(request,env);return locked(env,()=>registerUnlocked(request,env,now));
}
export async function remove(request,env,now=Date.now()){
 await internal(request,env);return locked(env,()=>removeUnlocked(request,env,now));
}
export async function unlink(request,env,now=Date.now()){
 await internal(request,env);return locked(env,()=>unlinkUnlocked(request,env,now));
}
export async function relink(request,env,now=Date.now()){
 await internal(request,env);return locked(env,()=>relinkUnlocked(request,env,now));
}
export async function publish(env,now=Date.now(),send=(url,init)=>globalThis.fetch(url,init)){
 if(env.PUBLISH_ENABLED!=='true')return {enabled:false,accepted:0,failed:0,households:0};
 return locked({...env,__send:send},guarded=>publishUnlocked(env,now,guarded));
}
export default {
  async fetch(request,env){
    try{
      const path=new URL(request.url).pathname;
      if(path==='/v1/pv'&&request.method==='GET')return await read(request,env);
      if(path==='/internal/register'&&request.method==='POST')return await register(request,env);
      if(path==='/internal/remove'&&request.method==='POST')return await remove(request,env);
      if(path==='/internal/unlink'&&request.method==='POST')return await unlink(request,env);
      if(path==='/internal/relink'&&request.method==='POST')return await relink(request,env);
      return reply({error:'not_found'},404);
    }catch(error){return reply({error:error.code||'unavailable'},error.status||503);}
  },
  async scheduled(controller,env){
    try{console.log(JSON.stringify({event:'echo_values_publish',...await publish(env,controller.scheduledTime)}));}
    catch{console.log(JSON.stringify({event:'echo_values_publish',result:'failed'}));}
  }
};
