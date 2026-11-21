import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {digest,register,remove,unlink,relink,read,publish,resolveStage,refreshRegistered,readVoice,fullscreenPublishProfile,storeFullscreenPublishProfile} from './worker.mjs';
const now=Date.parse('2026-11-16T15:00:00Z');

test('Fullscreen scheduled profile cannot change Live or an unrelated DEV package',()=>{
 const env={STAGE:'development',TEST_PACKAGE_ID:'Solaranlage1811',TEST_DATASTORE_NAMESPACE:'Solaranlage1811',
  WIDGET_PACKAGE_ID:'Solaranlage1711R2',DATASTORE_NAMESPACE:'Solaranlage1711',PUBLISH_MODE:'inline'};
 assert.equal(fullscreenPublishProfile(env),null);
 const enabled={...env,FULLSCREEN_DATASTORE_ENABLED:'true'};
 const selected=fullscreenPublishProfile(enabled);
 assert.equal(selected.WIDGET_PACKAGE_ID,'Solaranlage1811');
 assert.equal(selected.DATASTORE_NAMESPACE,'Solaranlage1811');
 assert.equal(selected.PUBLISH_MODE,'scheduled');
 assert.equal(enabled.PUBLISH_MODE,'inline');
 assert.equal(fullscreenPublishProfile({...enabled,STAGE:'live'}),null);
 assert.equal(fullscreenPublishProfile({...enabled,TEST_PACKAGE_ID:'Other'}),null);
});

test('One DEV snapshot delivers fullscreen and small values atomically; revocation still stops delivery',async()=>{
 const s=await setup();Object.assign(s.env,{WIDGET_PACKAGE_ID:'Solaranlage1811',DATASTORE_NAMESPACE:'Solaranlage1811',
  TEST_PACKAGE_ID:'Solaranlage1811',TEST_DATASTORE_NAMESPACE:'Solaranlage1811',PUBLISH_MODE:'inline',FULLSCREEN_DATASTORE_ENABLED:'true'});
 const initial=await(await register(s.request(),s.env,now,s.send)).json();
 assert.equal(initial.snapshot.solar,'100 W');
 assert.equal(initial.snapshot.fullscreen.live.live0v,'100 W');
 assert.equal(initial.snapshot.fullscreen.sampleTime,initial.snapshot.sampleTime);
 s.calls.length=0;
 const result=await publish(fullscreenPublishProfile(s.env),now,s.send);
 assert.equal(result.accepted,1);assert.equal(s.calls.length,1);
 const command=s.calls[0].commands;
 assert.equal(command.length,1);assert.equal(command[0].type,'PUT_OBJECT');
 assert.equal(command[0].namespace,'Solaranlage1811');
 assert.equal(command[0].content.solar,'100 W');
 assert.equal(command[0].content.fullscreen.live.live0v,'100 W');
 assert.equal(command[0].content.binding,initial.binding);
 s.calls.length=0;
 await unlink(s.request(),s.env,now+1000,s.send);
 s.calls.length=0;
 assert.equal((await publish(fullscreenPublishProfile(s.env),now+2000,s.send)).accepted,0);
 assert.equal(s.calls.length,0);
});
test('Store profile cannot alter the default DEV destination or bypass scope checks',()=>{
 const env={STAGE:'development',WIDGET_PACKAGE_ID:'Solaranlage1711R2',DATASTORE_NAMESPACE:'Solaranlage1711',LIVE_PACKAGE_ID:'SolarAccountImageBuild1211',LIVE_DATASTORE_NAMESPACE:'SolarAccountImagesV3'};
 const request=stage=>new Request('https://test/internal/register',{headers:{'X-Solar-Stage':stage}});
 const live=resolveStage(request('live'),env);
 assert.equal(live.STAGE,'live');assert.equal(live.WIDGET_PACKAGE_ID,'SolarAccountImageBuild1211');assert.equal(live.DATASTORE_NAMESPACE,'SolarAccountImagesV3');
 assert.equal(resolveStage(request('development'),env),env);
 assert.equal(env.WIDGET_PACKAGE_ID,'Solaranlage1711R2');
 assert.throws(()=>resolveStage(request('other'),env),{code:'wrong_scope'});
 assert.throws(()=>resolveStage(request('live'),{STAGE:'development'}),{code:'wrong_scope'});
});
async function setup(){
 const db=new DatabaseSync(':memory:');
 db.exec(readFileSync(new URL('../public-beta/schema.sql',import.meta.url),'utf8'));
 db.exec(readFileSync(new URL('./schema.sql',import.meta.url),'utf8'));
 const wrap=(sql,args=[])=>({bind(...a){return wrap(sql,a)},async first(){return db.prepare(sql).get(...args)},async all(){return {results:db.prepare(sql).all(...args)}},async run(){return {meta:{changes:Number(db.prepare(sql).run(...args).changes)}}}});
 const env={DB:{prepare:sql=>wrap(sql),async batch(items){db.exec('BEGIN');try{const out=[];for(const item of items)out.push(await item.run());db.exec('COMMIT');return out}catch(e){db.exec('ROLLBACK');throw e}}},REGISTRATION_SECRET:'r'.repeat(40),SUBJECT_HASH_KEY:'s'.repeat(40),STAGE:'development',WIDGET_PACKAGE_ID:'UNASSIGNED',DATASTORE_NAMESPACE:'UNASSIGNED',DATASTORE_KEY:'snapshot',PUBLISH_ENABLED:'true'};
 for(const [id,n,token] of [['a',100,'a'],['b',200,'b']]){
 db.prepare('INSERT INTO households(id,write_hash,timezone,created,live_at,live_json) VALUES(?,?,?,?,?,?)').run(id,'key-'+id,'Europe/Berlin',0,new Date(now).toISOString(),JSON.stringify({power_w:n,home_w:n+1,battery_soc:50}));
 db.prepare('INSERT INTO access_tokens VALUES(?,?,?)').run(await digest(token.repeat(64)),id,now/1000+3600);
 }
 const request=(owner='a',extra={},token=owner)=>new Request('https://test/internal/register',{method:'POST',headers:{'X-Solar-Registration':env.REGISTRATION_SECRET,Authorization:'Bearer '+token.repeat(64)},body:JSON.stringify({stage:env.STAGE,packageId:env.WIDGET_PACKAGE_ID,userId:'amzn1.ask.account.'+owner,deviceId:'amzn1.ask.device.'+owner,instanceId:'one',occurredAt:new Date(now).toISOString(),...extra})});
 const calls=[];const send=async(url,init)=>{if(url.includes('/auth/'))return Response.json({access_token:'synthetic'});const data=JSON.parse(init.body);calls.push(data);return Response.json({results:data.target.items.map(deviceId=>({deviceId,type:'SUCCESS'}))})};
 return {db,env,request,calls,send};
}

async function registeredLive(){
 const s=await setup();Object.assign(s.env,{STAGE:'live',WIDGET_PACKAGE_ID:'Published',LIVE_PACKAGE_ID:'Published'});
 await register(s.request(),s.env,now);
 s.refresh=(extra={},secret=s.env.REGISTRATION_SECRET)=>new Request('https://test/internal/refresh',{method:'POST',headers:{'X-Solar-Registration':secret},body:JSON.stringify({stage:'live',packageId:'Published',userId:'amzn1.ask.account.a',deviceId:'amzn1.ask.device.a',instanceId:'one',occurredAt:new Date(now).toISOString(),...extra})});
 return s;
}

test('Voice resolves the exact verified account/device after access-token expiry without re-registering',async()=>{
 const s=await registeredLive();Object.assign(s.env,{LIVE_DATASTORE_NAMESPACE:'SolarAccountImagesV3',TEST_PACKAGE_ID:'Solaranlage1811',TEST_DATASTORE_NAMESPACE:'Solaranlage1811',PUBLISH_MODE:'inline'});
 s.db.exec('UPDATE access_tokens SET expires=0');s.db.prepare('INSERT INTO refresh_tokens VALUES(?,?,?)').run('voice-refresh','a',now/1000+3600);
 const before=s.db.prepare('SELECT * FROM echo_value_devices').get();
 const response=await(await readVoice(s.refresh(),s.env,now,s.send)).json();
 assert.equal(response.resolvedStage,'live');assert.equal(response.resolvedPackageId,'Published');
 assert.equal(response.instanceId,'one');assert.equal(response.pv.home_w,101);assert.equal(response.snapshot.solar,'100 W');
 assert.equal(s.calls.length,1);assert.equal(s.calls[0].commands[0].namespace,'SolarAccountImagesV3');
 assert.deepEqual(s.db.prepare('SELECT * FROM echo_value_devices').get(),before);
});

test('Voice may use an active DEV association but does not reactivate the inactive Store association',async()=>{
 const s=await setup();Object.assign(s.env,{WIDGET_PACKAGE_ID:'Solaranlage1811',TEST_PACKAGE_ID:'Solaranlage1811',TEST_DATASTORE_NAMESPACE:'Solaranlage1811',DATASTORE_NAMESPACE:'Solaranlage1811',LIVE_PACKAGE_ID:'Published',LIVE_DATASTORE_NAMESPACE:'SolarAccountImagesV3'});
 await register(s.request(),s.env,now);const live={...s.env,STAGE:'live',WIDGET_PACKAGE_ID:'Published'};
 await register(s.request('a',{stage:'live',packageId:'Published'}),live,now);s.db.exec("UPDATE echo_value_devices SET active=0 WHERE stage='live'");
 const r=await(await readVoice(s.request('a',{stage:'live',packageId:'Published',instanceId:undefined}),live,now,s.send)).json();
 assert.equal(r.resolvedStage,'development');assert.equal(r.resolvedPackageId,'Solaranlage1811');
 assert.equal(s.db.prepare("SELECT active FROM echo_value_devices WHERE stage='live'").get().active,0);
});

test('Voice rejects an unknown or revoked device, a removed usage, a disabled household and rotated credentials',async()=>{
 for(const mutate of [s=>s.db.exec('UPDATE echo_value_devices SET active=0'),s=>remove(s.request(),s.env,now),s=>unlink(s.request(),s.env,now),s=>s.db.exec("UPDATE households SET disabled=1 WHERE id='a'"),s=>s.db.exec("UPDATE households SET write_hash='rotated' WHERE id='a'"),s=>s.db.exec('UPDATE access_tokens SET expires=0')]){
  const s=await registeredLive();s.env.LIVE_DATASTORE_NAMESPACE='SolarAccountImagesV3';await mutate(s);
  await assert.rejects(()=>readVoice(s.refresh(),s.env,now,s.send));assert.equal(s.calls.length,0);
 }
 for(const extra of [{userId:'amzn1.ask.account.b'},{deviceId:'amzn1.ask.device.b'},{stage:'development'},{packageId:'Other'}]){
  const s=await registeredLive();await assert.rejects(()=>readVoice(s.refresh(extra),s.env,now,s.send));assert.equal(s.calls.length,0);
 }
});

test('Voice rejects ambiguous cross-stage ownership instead of choosing a household',async()=>{
 const s=await registeredLive();Object.assign(s.env,{TEST_PACKAGE_ID:'Solaranlage1811',TEST_DATASTORE_NAMESPACE:'Solaranlage1811'});
 const dev={...s.env,STAGE:'development',WIDGET_PACKAGE_ID:'Solaranlage1811'};
 await register(s.request('b',{stage:'development',packageId:'Solaranlage1811',userId:'amzn1.ask.account.a',deviceId:'amzn1.ask.device.a'}),dev,now);
 await assert.rejects(()=>readVoice(s.refresh(),s.env,now,s.send),{code:'ambiguous_registration'});assert.equal(s.calls.length,0);
});

test('DEV tokenless minutes preserve the original atomic datastore delivery after access expiry',async()=>{
 const s=await setup();Object.assign(s.env,{WIDGET_PACKAGE_ID:'Solaranlage1811',TEST_PACKAGE_ID:'Solaranlage1811',DATASTORE_NAMESPACE:'Solaranlage1811'});
 await register(s.request(),s.env,now);s.env.PUBLISH_MODE='inline';
 s.db.exec('UPDATE access_tokens SET expires=0');
 const refresh=at=>new Request('https://test/internal/refresh',{method:'POST',headers:{'X-Solar-Registration':s.env.REGISTRATION_SECRET},body:JSON.stringify({stage:'development',packageId:'Solaranlage1811',userId:'amzn1.ask.account.a',deviceId:'amzn1.ask.device.a',instanceId:'one',occurredAt:new Date(at).toISOString(),trigger:'minute'})});
 for(let i=0;i<3;i++){
  const at=now+i*60000;s.db.prepare('UPDATE households SET live_at=?,live_json=? WHERE id=?').run(new Date(at).toISOString(),JSON.stringify({power_w:400+i,home_w:600+i,battery_soc:40+i}),'a');
  const response=await(await refreshRegistered(refresh(at),s.env,at,s.send)).json();
  assert.equal(response.delivery.accepted,1);assert.equal(s.calls.length,i+1);
  const sent=s.calls.at(-1);assert.deepEqual(sent.target.items,['amzn1.ask.device.a']);
  assert.equal(sent.commands.length,1);assert.equal(sent.commands[0].namespace,'Solaranlage1811');
  assert.deepEqual(sent.commands[0].content,response.snapshot);assert.equal(response.snapshot.sampleTime,at);
  assert.equal(response.snapshot.solar,(400+i)+' W');
 }
 const before=s.calls.length;s.db.exec("UPDATE households SET live_json='{}' WHERE id='a'");
 await assert.rejects(()=>refreshRegistered(refresh(now+180000),s.env,now+180000,s.send),{code:'snapshot_unavailable'});
 assert.equal(s.calls.length,before);
 await remove(s.request(),s.env,now);
 await assert.rejects(()=>refreshRegistered(refresh(now+180000),s.env,now+180000,s.send));assert.equal(s.calls.length,before);
});

test('DEV failed datastore delivery releases its lease and retries on the next regular minute',async()=>{
 const s=await setup();Object.assign(s.env,{WIDGET_PACKAGE_ID:'Solaranlage1811',TEST_PACKAGE_ID:'Solaranlage1811',DATASTORE_NAMESPACE:'Solaranlage1811'});
 await register(s.request(),s.env,now);s.env.PUBLISH_MODE='inline';
 const req=()=>new Request('https://test/internal/refresh',{method:'POST',headers:{'X-Solar-Registration':s.env.REGISTRATION_SECRET},body:JSON.stringify({stage:'development',packageId:'Solaranlage1811',userId:'amzn1.ask.account.a',deviceId:'amzn1.ask.device.a',instanceId:'one',occurredAt:new Date(now).toISOString()})});
 await assert.rejects(()=>refreshRegistered(req(),s.env,now,async(url,init)=>url.includes('/datastore/')?new Response('',{status:429}):s.send(url,init)),{code:'delivery_failed'});
 assert.equal(s.calls.length,0);assert.equal(s.db.prepare('SELECT COUNT(*) n FROM echo_value_locks').get().n,0);
 assert.equal((await(await refreshRegistered(req(),s.env,now,s.send)).json()).delivery.accepted,1);
});
test('DEV1811 tokenless refresh returns scoped fullscreen data and rejects changed ownership or removal',async()=>{
 const s=await setup();Object.assign(s.env,{WIDGET_PACKAGE_ID:'Solaranlage1811',TEST_PACKAGE_ID:'Solaranlage1811'});
 await register(s.request(),s.env,now);
 const refresh=extra=>new Request('https://test/internal/refresh',{method:'POST',headers:{'X-Solar-Registration':s.env.REGISTRATION_SECRET},body:JSON.stringify({stage:'development',packageId:'Solaranlage1811',userId:'amzn1.ask.account.a',deviceId:'amzn1.ask.device.a',instanceId:'one',occurredAt:new Date(now).toISOString(),...extra})});
 const r=await(await refreshRegistered(refresh(),s.env,now)).json();assert.equal(r.pv.power_w,100);assert.equal(r.snapshot.home,'101 W');
 s.db.exec('UPDATE access_tokens SET expires=0');
 assert.equal((await(await refreshRegistered(refresh(),s.env,now)).json()).pv.power_w,100);
 for(const extra of [{userId:'amzn1.ask.account.b'},{deviceId:'amzn1.ask.device.b'},{instanceId:'absent'},{packageId:'Other'},{stage:'live'}])await assert.rejects(()=>refreshRegistered(refresh(extra),s.env,now));
 await remove(s.request(),s.env,now);await assert.rejects(()=>refreshRegistered(refresh(),s.env,now));
 assert.equal(s.calls.length,0);
});
test('DEV association survives token rotation but stops immediately on unlink, disabled household or changed generation',async()=>{
 for(const mutate of [s=>unlink(s.request(),s.env,now),s=>s.db.exec("UPDATE households SET disabled=1 WHERE id='a'"),s=>s.db.exec("UPDATE households SET write_hash='rotated' WHERE id='a'")]){
  const s=await setup();Object.assign(s.env,{WIDGET_PACKAGE_ID:'Solaranlage1811',TEST_PACKAGE_ID:'Solaranlage1811'});await register(s.request(),s.env,now);
  const req=()=>new Request('https://test/internal/refresh',{method:'POST',headers:{'X-Solar-Registration':s.env.REGISTRATION_SECRET},body:JSON.stringify({stage:'development',packageId:'Solaranlage1811',userId:'amzn1.ask.account.a',deviceId:'amzn1.ask.device.a',instanceId:'one',occurredAt:new Date(now).toISOString()})});
  await mutate(s);await assert.rejects(()=>refreshRegistered(req(),s.env,now));
 }
});
test('Registered Live refresh returns four current values without OAuth or Amazon subrequests',async()=>{
 const s=await registeredLive();const before=s.db.prepare('SELECT updated_at FROM echo_value_devices').get().updated_at;
 for(let i=0;i<3;i++){
  const at=now+i*60000;s.db.prepare('UPDATE households SET live_at=?,live_json=? WHERE id=?').run(new Date(at).toISOString(),JSON.stringify({power_w:300+i,home_w:500+i,battery_soc:30+i}),'a');
  const r=await(await refreshRegistered(s.refresh({occurredAt:new Date(at).toISOString()}),s.env,at)).json();
  assert.equal(r.registered,true);assert.equal(r.refreshed,true);assert.equal(r.snapshot.solar,(300+i)+' W');assert.equal(r.snapshot.home,(500+i)+' W');assert.equal(r.snapshot.battery,(30+i)+' %');assert.equal(r.snapshot.sampleTime,at);assert.equal(r.snapshot.binding,r.binding);
 }
 assert.equal(s.calls.length,0);assert.equal(s.db.prepare('SELECT updated_at FROM echo_value_devices').get().updated_at,before);
});

test('Inline Live refresh delivers one atomic object matching its response over three changing rounds',async()=>{
 const s=await registeredLive();s.env.PUBLISH_MODE='inline';s.env.DATASTORE_NAMESPACE='SolarAccountImagesV3';
 const updated=s.db.prepare('SELECT updated_at FROM echo_value_devices').get().updated_at;
 for(let i=0;i<3;i++){
  const at=now+i*60000;
  s.db.prepare('UPDATE households SET live_at=?,live_json=? WHERE id=?').run(new Date(at).toISOString(),JSON.stringify({power_w:300+i,home_w:500+i,battery_soc:30+i}),'a');
  const r=await(await refreshRegistered(s.refresh({occurredAt:new Date(at).toISOString(),trigger:'minute'}),s.env,at,s.send)).json();
  assert.equal(r.delivery.accepted,1);assert.equal(s.calls.length,i+1);
  const sent=s.calls.at(-1);assert.deepEqual(sent.target.items,['amzn1.ask.device.a']);
  assert.equal(sent.commands.length,1);assert.equal(sent.commands[0].type,'PUT_OBJECT');
  assert.equal(sent.commands[0].namespace,'SolarAccountImagesV3');assert.equal(sent.commands[0].key,'snapshot');
  assert.deepEqual(sent.commands[0].content,r.snapshot);assert.equal(r.snapshot.sampleTime,at);
  assert.equal(r.pv.power_w,300+i);assert.equal(r.pv.home_w,500+i);assert.equal(r.pv.battery_soc,30+i);
  assert.equal(r.snapshot.solar,(300+i)+' W');assert.equal(r.snapshot.home,(500+i)+' W');assert.equal(r.snapshot.battery,(30+i)+' %');
 }
 assert.equal(s.db.prepare('SELECT updated_at FROM echo_value_devices').get().updated_at,updated);
 s.db.exec("UPDATE households SET live_json='{}' WHERE id='a'");
 await assert.rejects(()=>refreshRegistered(s.refresh(),s.env,now,s.send),{code:'snapshot_unavailable'});
 assert.equal(s.calls.length,3);
});

test('Inline Live rejects inactive, removed, revoked, rotated and cross-scope bindings before any delivery',async()=>{
 for(const mutate of [s=>s.db.exec('UPDATE echo_value_devices SET active=0'),s=>remove(s.request(),s.env,now),s=>unlink(s.request(),s.env,now),s=>s.db.exec("UPDATE households SET disabled=1"),s=>s.db.exec("UPDATE households SET write_hash='rotated' WHERE id='a'"),s=>s.db.exec('UPDATE access_tokens SET expires=0')]){
  const s=await registeredLive();await mutate(s);s.env.PUBLISH_MODE='inline';
  await assert.rejects(()=>refreshRegistered(s.refresh(),s.env,now,s.send));assert.equal(s.calls.length,0);
 }
 for(const extra of [{userId:'amzn1.ask.account.b'},{deviceId:'amzn1.ask.device.b'},{instanceId:'other'},{packageId:'Other'},{stage:'development'}]){
  const s=await registeredLive();s.env.PUBLISH_MODE='inline';
  await assert.rejects(()=>refreshRegistered(s.refresh(extra),s.env,now,s.send));assert.equal(s.calls.length,0);
 }
});

test('Inline Live delivery failure returns no replacement snapshot and does not mutate registration',async()=>{
 const s=await registeredLive();s.env.PUBLISH_MODE='inline';const before=s.db.prepare('SELECT * FROM echo_value_devices').get();
 const send=async(url)=>url.includes('/auth/')?Response.json({access_token:'synthetic'}):Response.json({error:'unavailable'},{status:503});
 await assert.rejects(()=>refreshRegistered(s.refresh(),s.env,now,send),{code:'delivery_failed'});
 assert.deepEqual(s.db.prepare('SELECT * FROM echo_value_devices').get(),before);
});

test('Live keeps the verified association across access expiry while its refresh grant remains valid',async()=>{
 const s=await registeredLive();s.env.PUBLISH_MODE='inline';s.db.exec('UPDATE access_tokens SET expires=0');
 s.db.prepare('INSERT INTO refresh_tokens VALUES(?,?,?)').run('synthetic-refresh','a',now/1000+3600);
 const r=await(await refreshRegistered(s.refresh(),s.env,now,s.send)).json();
 assert.equal(r.delivery.accepted,1);assert.equal(r.snapshot.solar,'100 W');
 s.db.exec('UPDATE refresh_tokens SET expires=0');
 await assert.rejects(()=>refreshRegistered(s.refresh(),s.env,now,s.send),{code:'verified_registration_required'});
 assert.equal(s.calls.length,1);
});

test('A valid refresh grant cannot bypass unlink, removal or generation rotation',async()=>{
 for(const mutate of [s=>unlink(s.request(),s.env,now),s=>remove(s.request(),s.env,now),s=>s.db.exec("UPDATE households SET write_hash='rotated' WHERE id='a'")]){
  const s=await registeredLive();s.db.prepare('INSERT INTO refresh_tokens VALUES(?,?,?)').run('synthetic-refresh','a',now/1000+3600);
  await mutate(s);s.env.PUBLISH_MODE='inline';s.db.exec('UPDATE access_tokens SET expires=0');
  await assert.rejects(()=>refreshRegistered(s.refresh(),s.env,now,s.send));assert.equal(s.calls.length,0);
 }
});
test('Tokenless refresh never registers or reactivates unknown account/device/package usage',async()=>{
 for(const change of [{userId:'amzn1.ask.account.b'},{deviceId:'amzn1.ask.device.b'},{instanceId:'other'},{packageId:'Other'},{stage:'development'}]){
  const s=await registeredLive();await assert.rejects(()=>refreshRegistered(s.refresh(change),s.env,now));
  assert.equal(s.db.prepare('SELECT COUNT(*) AS n FROM echo_value_devices').get().n,1);
 }
});
test('Registered refresh rejects revocation, removal, disabled household, changed generation and expired grants',async()=>{
 for(const mutate of [s=>unlink(s.request(),s.env,now),s=>remove(s.request(),s.env,now),s=>s.db.exec("UPDATE households SET disabled=1 WHERE id='a'"),s=>s.db.exec("UPDATE households SET write_hash='rotated' WHERE id='a'"),s=>s.db.exec('UPDATE access_tokens SET expires=0')]){
  const s=await registeredLive();await mutate(s);await assert.rejects(()=>refreshRegistered(s.refresh(),s.env,now));
 }
});
test('Registered refresh cannot substitute a client-supplied household or skip internal authentication',async()=>{
 const s=await registeredLive();const r=await(await refreshRegistered(s.refresh({household:'b'}),s.env,now)).json();assert.equal(r.snapshot.solar,'100 W');
 await assert.rejects(()=>refreshRegistered(s.refresh({},'wrong'),s.env,now),{code:'unauthorized'});
});
test('Invalid registered readings preserve the last valid display by returning no snapshot',async()=>{
 const s=await registeredLive();s.db.exec("UPDATE households SET live_json='{}'");await assert.rejects(()=>refreshRegistered(s.refresh(),s.env,now),{code:'snapshot_unavailable'});
});
test('OAuth isolates household reads and rejects expired tokens',async()=>{const s=await setup();for(const [who,value] of [['a',100],['b',200]]){const r=await read(new Request('https://test/v1/pv?household=other',{headers:{Authorization:'Bearer '+who.repeat(64)}}),s.env,now);assert.equal((await r.json()).power_w,value)}s.db.exec('UPDATE access_tokens SET expires=0');await assert.rejects(()=>read(new Request('https://test/v1/pv',{headers:{Authorization:'Bearer '+'a'.repeat(64)}}),s.env,now),{code:'unauthorized'})});
test('Publishing keeps households in separate atomic snapshots',async()=>{const s=await setup();await register(s.request('a'),s.env,now);await register(s.request('b'),s.env,now);assert.equal((await publish(s.env,now,s.send)).accepted,2);assert.equal(s.calls.length,2);assert.deepEqual(s.calls.map(c=>c.commands[0].content.solar),['100 W','200 W']);assert.ok(s.calls.every(c=>c.target.items.length===1))});
test('Removing one instance retains another; unlink stops household delivery',async()=>{const s=await setup();await register(s.request(),s.env,now);await register(s.request('a',{instanceId:'two'}),s.env,now);await remove(s.request(),s.env,now);assert.equal((await publish(s.env,now,s.send)).accepted,1);await unlink(s.request(),s.env,now);assert.equal((await publish(s.env,now,s.send)).accepted,0);await assert.rejects(()=>register(s.request(),s.env,now),{code:'stale_event'})});
test('New owner replaces old ownership; stale registration cannot restore it',async()=>{const s=await setup();await register(s.request(),s.env,now);await register(s.request('b',{deviceId:'amzn1.ask.device.a',occurredAt:new Date(now+1000).toISOString()}),s.env,now+1000);await assert.rejects(()=>register(s.request(),s.env,now+1000),{code:'stale_event'});await publish(s.env,now+1000,s.send);assert.equal(s.calls[0].commands[0].content.solar,'200 W')});
test('Rotated access, disabled households and opt-out prevent publishing',async()=>{const s=await setup();await register(s.request(),s.env,now);s.db.exec("UPDATE households SET write_hash='rotated' WHERE id='a'");assert.equal((await publish(s.env,now,s.send)).accepted,0);await register(s.request(),s.env,now);s.db.exec("UPDATE households SET disabled=1 WHERE id='a'");assert.equal((await publish(s.env,now,s.send)).accepted,0);assert.equal((await publish({...s.env,PUBLISH_ENABLED:'false'},now,s.send)).enabled,false)});
test('Invalid measurement does not overwrite last valid datastore object',async()=>{const s=await setup();await register(s.request(),s.env,now);s.db.exec("UPDATE households SET live_json='{}'");assert.equal((await publish(s.env,now,s.send)).failed,1);assert.equal(s.calls.length,0)});

test('Live and development registrations on the same Echo stay separate',async()=>{const s=await setup();await register(s.request(),s.env,now);const live={...s.env,STAGE:'live',WIDGET_PACKAGE_ID:'LiveCandidate',DATASTORE_NAMESPACE:'SolarValuesLive'};await register(s.request('b',{stage:'live',packageId:'LiveCandidate',deviceId:'amzn1.ask.device.a'}),live,now);await publish(s.env,now,s.send);await publish(live,now,s.send);assert.deepEqual(s.calls.map(c=>c.commands[0].content.solar),['100 W','200 W']);assert.deepEqual(s.calls.map(c=>c.commands[0].namespace),['UNASSIGNED','SolarValuesLive'])});
test('More than twenty devices use bounded Amazon batches',async()=>{const s=await setup();for(let i=0;i<21;i++)await register(s.request('a',{deviceId:'amzn1.ask.device.a'+i}),s.env,now);assert.equal((await publish(s.env,now,s.send)).accepted,21);assert.deepEqual(s.calls.map(c=>c.target.items.length),[20,1])});
test('Unlink between validation and transaction cannot reactivate registration',async()=>{const s=await setup();const original=s.env.DB.batch;let injected=false;s.env.DB.batch=async items=>{if(!injected){injected=true;s.db.prepare('INSERT INTO echo_value_revocations(stage,subject_hash,revoked_at) VALUES(?,?,?)').run('development',await (async()=>{const key=await crypto.subtle.importKey('raw',new TextEncoder().encode(s.env.SUBJECT_HASH_KEY),{name:'HMAC',hash:'SHA-256'},false,['sign']);return Buffer.from(await crypto.subtle.sign('HMAC',key,new TextEncoder().encode('amzn1.ask.account.a'))).toString('hex')})(),now)}return original(items)};await assert.rejects(()=>register(s.request(),s.env,now),{code:'stale_event'});assert.equal((await publish(s.env,now,s.send)).accepted,0)});

test('Pending Amazon delivery blocks removal; acknowledged removal prevents later writes',async()=>{const s=await setup();await register(s.request(),s.env,now);let resume,entered;const ready=new Promise(r=>entered=r),gate=new Promise(r=>resume=r);const sending=publish(s.env,now,async(url,init)=>{if(url.includes('/datastore/')){entered();await gate;}return s.send(url,init)});await ready;await assert.rejects(()=>remove(s.request(),s.env,now),{code:'delivery_busy'});resume();await sending;await remove(s.request(),s.env,now);assert.equal((await publish(s.env,now,s.send)).accepted,0)});
test('Amazon failure releases lease and preserves old object for next-minute retry',async()=>{const s=await setup();await register(s.request(),s.env,now);assert.equal((await publish(s.env,now,async(url,init)=>url.includes('/datastore/')?new Response('',{status:429}):s.send(url,init))).failed,1);assert.equal((await publish(s.env,now,s.send)).accepted,1)});

test('Removed instance cannot be resurrected by identical old event',async()=>{const s=await setup();await register(s.request(),s.env,now);await remove(s.request(),s.env,now);await assert.rejects(()=>register(s.request(),s.env,now),{code:'stale_event'});assert.equal((await publish(s.env,now,s.send)).accepted,0)});
test('Pagination rotates over more than one hundred registrations',async()=>{const s=await setup();for(let i=0;i<101;i++)await register(s.request('a',{deviceId:'amzn1.ask.device.a'+String(i).padStart(3,'0')}),s.env,now);await publish(s.env,now,s.send);await publish(s.env,now,s.send);assert.equal(new Set(s.calls.flatMap(c=>c.target.items)).size,101)});
test('Expired leases recover after a crashed runner; active leases block',async()=>{const s=await setup();s.db.prepare('INSERT INTO echo_value_locks VALUES(?,?,?)').run('development','old',Date.now()+60000);await assert.rejects(()=>register(s.request(),s.env,now),{code:'delivery_busy'});s.db.exec('UPDATE echo_value_locks SET expires=0');assert.equal((await register(s.request(),s.env,now)).status,200)});

test('Account re-link moves registered devices with a new display binding',async()=>{const s=await setup();const first=await (await register(s.request(),s.env,now)).json();await publish(s.env,now,s.send);assert.equal(s.calls[0].commands[0].content.binding,first.binding);await relink(s.request('a',{occurredAt:new Date(now+1000).toISOString()},'b'),s.env,now+1000);await publish(s.env,now+1000,s.send);const latest=s.calls[1].commands[0].content;assert.equal(latest.solar,'200 W');assert.notEqual(latest.binding,first.binding)});

test('Removal notification without instance deactivates all matching package usages',async()=>{const s=await setup();await register(s.request(),s.env,now);await register(s.request('a',{instanceId:'two'}),s.env,now);await remove(s.request('a',{instanceId:null,removeAll:true}),s.env,now);assert.equal((await publish(s.env,now,s.send)).accepted,0)});


test('Three synthetic minute rounds publish changing atomic values with bounded calls',async()=>{
 const s=await setup();await register(s.request(),s.env,now);
 let d1=0,http=0;const original=s.env.DB.prepare;
 s.env.DB.prepare=(...args)=>{const q=original(...args);const track=x=>({bind(...a){return track(x.bind(...a))},async first(){d1++;return x.first()},async all(){d1++;return x.all()},async run(){d1++;return x.run()}});return track(q)};
 const evidence=[];
 for(let round=0;round<3;round++){
  const at=now+round*60000;
  s.db.prepare('UPDATE households SET live_at=?,live_json=? WHERE id=?').run(new Date(at).toISOString(),JSON.stringify({power_w:100+round,home_w:500+round,battery_soc:50+round}),'a');
  const beforeD1=d1,beforeHttp=http;
  const result=await publish(s.env,at,async(...args)=>{http++;return s.send(...args)});
  const content=s.calls.at(-1).commands[0].content;
  assert.equal(result.accepted,1);assert.equal(result.failed,0);
  assert.equal(content.sampleTime,at);assert.equal(content.solar,(100+round)+' W');assert.equal(content.home,(500+round)+' W');assert.equal(content.battery,(50+round)+' %');
  assert.equal(s.calls.at(-1).commands.length,1);
  evidence.push({round:round+1,d1:d1-beforeD1,amazonHttp:http-beforeHttp});
 }
 assert.deepEqual(evidence,[1,2,3].map(round=>({round,d1:8,amazonHttp:2})));
 console.log('SYNTHETIC_MINUTE_ROUNDS '+JSON.stringify(evidence));
});

test('Stale measurements retain their original timestamp and become visibly stale',async()=>{
 const s=await setup();await register(s.request(),s.env,now);
 await publish(s.env,now,s.send);const first=s.calls.at(-1).commands[0].content;
 await publish(s.env,now+300000,s.send);const last=s.calls.at(-1).commands[0].content;
 assert.equal(last.sampleTime,first.sampleTime);assert.equal(last.stale,true);
 assert.equal(last.stamp.replace(/^Veraltet: /,''),first.stamp.replace(/^Stand: /,''));
});

test('Client-supplied household cannot override the linked account',async()=>{
 const s=await setup();await register(s.request('a',{household:'b'}),s.env,now);
 await publish(s.env,now,s.send);assert.equal(s.calls[0].commands[0].content.solar,'100 W');
});


test('Inline mode delivers three changing rounds without a second cron delivery',async()=>{
 const s=await setup();s.env.PUBLISH_MODE='inline';
 for(let i=0;i<3;i++){
  const at=now+i*60000;s.db.prepare('UPDATE households SET live_at=?,live_json=? WHERE id=?').run(new Date(at).toISOString(),JSON.stringify({power_w:300+i,home_w:600+i,battery_soc:20+i}),'a');
  const response=await (await register(s.request('a',{occurredAt:new Date(at).toISOString()}),s.env,at,s.send)).json();
  assert.equal(response.delivery.accepted,1);assert.equal(response.snapshot.sampleTime,at);
  assert.equal(s.calls.length,i+1);assert.equal(s.calls.at(-1).commands.length,1);
  assert.equal(s.calls.at(-1).commands[0].content.solar,(300+i)+' W');
  const count=s.calls.length;assert.equal((await publish(s.env,at,s.send)).reason,'inline_mode');assert.equal(s.calls.length,count);
 }
});

test('Inline relink clears old display before delivering the new household',async()=>{
 const s=await setup();s.env.PUBLISH_MODE='inline';await register(s.request(),s.env,now,s.send);
 await relink(s.request('a',{occurredAt:new Date(now+1000).toISOString()},'b'),s.env,now+1000,s.send);
 const commands=s.calls.at(-1).commands;assert.equal(commands.length,2);
 assert.equal(commands[0].content.stamp,'');assert.equal(commands[0].content.sampleTime,0);
 assert.equal(commands[1].content.solar,'200 W');assert.equal(s.db.prepare('SELECT household FROM echo_value_devices').get().household,'b');
});

test('Relink without valid new measurements clears instead of retaining old household',async()=>{
 const s=await setup();s.env.PUBLISH_MODE='inline';await register(s.request(),s.env,now,s.send);s.db.exec("UPDATE households SET live_json='{}' WHERE id='b'");
 await relink(s.request('a',{occurredAt:new Date(now+1000).toISOString()},'b'),s.env,now+1000,s.send);
 assert.equal(s.calls.at(-1).commands.length,1);assert.equal(s.calls.at(-1).commands[0].content.sampleTime,0);assert.equal(s.calls.at(-1).commands[0].content.stamp,'');
});

test('Failed relink clear remains retryable and does not commit new ownership',async()=>{
 const s=await setup();s.env.PUBLISH_MODE='inline';await register(s.request(),s.env,now,s.send);s.db.exec("UPDATE households SET live_json='{}' WHERE id='b'");
 const failure=(url,init)=>url.includes('/datastore/')?new Response('',{status:503}):s.send(url,init);
 await assert.rejects(()=>relink(s.request('a',{occurredAt:new Date(now+1000).toISOString()},'b'),s.env,now+1000,failure),{code:'delivery_failed'});
 assert.equal(s.db.prepare('SELECT household FROM echo_value_devices').get().household,'a');
 await register(s.request('a',{occurredAt:new Date(now+2000).toISOString()},'b'),s.env,now+2000,s.send);
 assert.equal(s.calls.at(-1).commands[0].content.sampleTime,0);assert.equal(s.db.prepare('SELECT household FROM echo_value_devices').get().household,'b');
});

test('Delayed disable event clears data and stops delivery, while stale events cannot restore it',async()=>{
 const s=await setup();s.env.PUBLISH_MODE='inline';await register(s.request(),s.env,now,s.send);
 await unlink(s.request('a',{occurredAt:new Date(now+1000).toISOString()}),s.env,now+600000,s.send);
 assert.equal(s.db.prepare('SELECT active FROM echo_value_devices').get().active,0);assert.equal(s.calls.at(-1).commands[0].content.sampleTime,0);
 await assert.rejects(()=>register(s.request('a',{occurredAt:new Date(now+500).toISOString()}),s.env,now+500,s.send),{code:'stale_event'});
});

test('Inline delivery failure releases its lease and succeeds on the next regular request',async()=>{
 const s=await setup();s.env.PUBLISH_MODE='inline';const fail=(url,init)=>url.includes('/datastore/')?new Response('',{status:429}):s.send(url,init);
 await assert.rejects(()=>register(s.request(),s.env,now,fail),{code:'delivery_failed'});
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM echo_value_locks').get().n,0);
 const response=await (await register(s.request('a',{occurredAt:new Date(now+60000).toISOString()}),s.env,now+60000,s.send)).json();assert.equal(response.delivery.accepted,1);
});

test('Approved separate DEV package resolves to its own namespace without replacing the old DEV',()=>{
 const env={STAGE:'development',WIDGET_PACKAGE_ID:'Solaranlage1711R2',DATASTORE_NAMESPACE:'Solaranlage1711',TEST_PACKAGE_ID:'Solaranlage1811',TEST_DATASTORE_NAMESPACE:'Solaranlage1811'};
 const req=pkg=>new Request('https://test/internal/register',{headers:{'X-Solar-Stage':'development','X-Solar-Package':pkg}});
 const target=resolveStage(req('Solaranlage1811'),env);
 assert.equal(target.WIDGET_PACKAGE_ID,'Solaranlage1811');assert.equal(target.DATASTORE_NAMESPACE,'Solaranlage1811');
 assert.equal(resolveStage(req('Solaranlage1711R2'),env),env);
 assert.throws(()=>resolveStage(req('unapproved'),env),{code:'wrong_scope'});
});

test('Store development and live adapter scopes resolve the Store namespace, while DEV1811 stays separate',()=>{
 const env={STAGE:'development',WIDGET_PACKAGE_ID:'Solaranlage1711R2',DATASTORE_NAMESPACE:'Solaranlage1711',TEST_PACKAGE_ID:'Solaranlage1811',TEST_DATASTORE_NAMESPACE:'Solaranlage1811',LIVE_PACKAGE_ID:'SolarAccountImageBuild1211',LIVE_DATASTORE_NAMESPACE:'SolarAccountImagesV3'};
 const req=(stage,pkg)=>new Request('https://test/internal/register',{headers:{'X-Solar-Stage':stage,'X-Solar-Package':pkg}});
 for(const stage of ['development','live']){const scoped=resolveStage(req(stage,'SolarAccountImageBuild1211'),env);assert.equal(scoped.STAGE,stage);assert.equal(scoped.WIDGET_PACKAGE_ID,'SolarAccountImageBuild1211');assert.equal(scoped.DATASTORE_NAMESPACE,'SolarAccountImagesV3');}
 assert.equal(resolveStage(req('development','Solaranlage1811'),env).DATASTORE_NAMESPACE,'Solaranlage1811');
 assert.throws(()=>resolveStage(req('certification','SolarAccountImageBuild1211'),env),{code:'wrong_scope'});
});




test('Store fullscreen uses separate explicit scope and retains DEV profile',async()=>{
 const s=await setup();Object.assign(s.env,{STAGE:'live',WIDGET_PACKAGE_ID:'SolarAccountImageBuild1211',DATASTORE_NAMESPACE:'SolarAccountImagesV3',LIVE_PACKAGE_ID:'SolarAccountImageBuild1211',LIVE_DATASTORE_NAMESPACE:'SolarAccountImagesV3',TEST_PACKAGE_ID:'Solaranlage1811',TEST_DATASTORE_NAMESPACE:'Solaranlage1811',FULLSCREEN_DATASTORE_ENABLED:'true',FULLSCREEN_STORE_ENABLED:'true',PUBLISH_MODE:'inline'});
 const result=await(await register(s.request(),s.env,now,s.send)).json();
 assert.equal(result.snapshot.fullscreen.live.live0v,'100 W');
 assert.equal(result.snapshot.fullscreen.sampleTime,result.snapshot.sampleTime);
 const profile=storeFullscreenPublishProfile(s.env);assert.equal(profile.STAGE,'live');
 assert.equal(profile.DATASTORE_NAMESPACE,'SolarAccountImagesV3');
 assert.equal(s.env.PUBLISH_MODE,'inline');
 s.calls.length=0;assert.equal((await publish(profile,now,s.send)).accepted,1);
 assert.equal(s.calls[0].commands[0].namespace,'SolarAccountImagesV3');
 assert.equal(storeFullscreenPublishProfile({...s.env,FULLSCREEN_STORE_ENABLED:'false'}),null);
 assert.equal(storeFullscreenPublishProfile({...s.env,LIVE_PACKAGE_ID:'Other'}),null);
});
