import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {digest,register,refreshRegistered,unlink,relink,remove,publish,readVoice} from './worker.mjs';
const now=Date.parse('2026-11-22T12:00:00Z');

test('Authenticated fullscreen verifies token household before reading existing binding',async()=>{
 const s=await setup();await register(s.req(now,'a'),s.env,now,s.send);
 const matching=await(await readVoice(s.req(now+1000,'a'),s.env,now+1000,s.send)).json();
 assert.equal(matching.registered,true);assert.equal(matching.pv.home_w,101);
 const before=s.calls.length;
 await assert.rejects(()=>readVoice(s.req(now+2000,'b'),s.env,now+2000,s.send),e=>e.code==='account_binding_mismatch');
 assert.equal(s.calls.length,before);
 await assert.rejects(()=>readVoice(s.req(now+2000,'c'),s.env,now+2000,s.send),e=>e.code==='unauthorized');
});

async function setup(){
 const db=new DatabaseSync(':memory:');
 for(const file of ['../public-beta/schema.sql','./schema.sql','./connection-schema.sql','./retry-schema.sql'])db.exec(readFileSync(new URL(file,import.meta.url),'utf8'));
 const wrap=(sql,args=[])=>({bind(...a){return wrap(sql,a)},async first(){return db.prepare(sql).get(...args)},async all(){return {results:db.prepare(sql).all(...args)}},async run(){return {meta:{changes:Number(db.prepare(sql).run(...args).changes)}}}});
 const env={DB:{prepare:sql=>wrap(sql),async batch(items){db.exec('BEGIN');try{const out=[];for(const item of items)out.push(await item.run());db.exec('COMMIT');return out}catch(e){db.exec('ROLLBACK');throw e}}},REGISTRATION_SECRET:'r'.repeat(40),SUBJECT_HASH_KEY:'s'.repeat(40),STAGE:'live',WIDGET_PACKAGE_ID:'SolarAccountImageBuild1211',LIVE_PACKAGE_ID:'SolarAccountImageBuild1211',DATASTORE_NAMESPACE:'SolarAccountImagesV3',DATASTORE_KEY:'snapshot',PUBLISH_ENABLED:'true',PUBLISH_MODE:'inline',CONNECTION_STATUS_ENABLED:'true',CONNECTION_RETRY_PAUSE_ENABLED:'true',TEST_PACKAGE_ID:'Solaranlage1811',TEST_DATASTORE_NAMESPACE:'Solaranlage1811',LIVE_DATASTORE_NAMESPACE:'SolarAccountImagesV3'};
 for(const [id,n] of [['a',100],['b',200]]){
  db.prepare('INSERT INTO households(id,write_hash,timezone,created,live_at,live_json) VALUES(?,?,?,?,?,?)').run(id,'key-'+id,'Europe/Berlin',0,new Date(now).toISOString(),JSON.stringify({power_w:n,home_w:n+1,battery_soc:50}));
  db.prepare('INSERT INTO access_tokens VALUES(?,?,?)').run(await digest(id.repeat(64)),id,now/1000+3600);
 }
 const req=(at,token=null,extra={})=>new Request('https://test/internal/refresh',{method:'POST',headers:{'X-Solar-Registration':env.REGISTRATION_SECRET,...(token?{Authorization:'Bearer '+token.repeat(64)}:{})},body:JSON.stringify({stage:env.STAGE,packageId:env.WIDGET_PACKAGE_ID,userId:'amzn1.ask.account.a',deviceId:'amzn1.ask.device.a',instanceId:'one',occurredAt:new Date(at).toISOString(),connectionVersion:3,...extra})});
 const calls=[];let failDelivery=false;
 const send=async(url,init)=>{if(url.includes('/auth/'))return Response.json({access_token:'synthetic'});const data=JSON.parse(init.body);calls.push(data);if(failDelivery)return Response.json({}, {status:503});return Response.json({results:data.target.items.map(deviceId=>({deviceId,type:'SUCCESS'}))})};
 return {db,env,req,calls,send,setFailure:v=>{failDelivery=v}};
}

async function failedSix(s){
 let last;
 for(const offset of [0,60000,180000,420000,900000,1800000]){
  last=await(await refreshRegistered(s.req(now+offset),s.env,now+offset,s.send)).json();
 }
 return last;
}
async function devAuthority(s){
 const env={...s.env,STAGE:'development',WIDGET_PACKAGE_ID:'Solaranlage1811',DATASTORE_NAMESPACE:'Solaranlage1811'};
 await register(s.req(now,'a',{stage:'development',packageId:'Solaranlage1811',connectionVersion:undefined}),env,now,s.send);
 return env;
}
const fullscreen=s=>s.req(now+1801000,null,{connectionVersion:undefined,instanceId:undefined,resumeWidgetRetries:true});

test('Six unknown registrations pause, persist across remount and never claim an unlinked account',async()=>{
 const s=await setup();const result=await failedSix(s);
 assert.equal(result.registered,false);assert.equal(result.connection.state,'unknown');
 assert.equal(result.connection.retryPaused,true);assert.equal(result.connection.retryFailures,6);
 assert.equal(result.snapshot,undefined);assert.equal(s.calls.length,0);
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM echo_value_devices').get().n,0);
 const remount=await(await refreshRegistered(s.req(now+1800500),s.env,now+1800500,s.send)).json();
 assert.equal(remount.connection.retryPaused,true);assert.equal(remount.connection.retryFailures,6);
});

test('Duplicate and reordered requests do not exhaust the registration budget',async()=>{
 const s=await setup();
 for(let i=0;i<7;i++)await refreshRegistered(s.req(now+1000),s.env,now+2000,s.send);
 await refreshRegistered(s.req(now),s.env,now+2000,s.send);
 assert.equal(s.db.prepare('SELECT failures FROM echo_value_widget_retries').get().failures,1);
});

test('Fresh linked event resumes paused exact widget without fullscreen or old-binding restoration',async()=>{
 const s=await setup();await failedSix(s);
 await relink(s.req(now+1801000,'a'),s.env,now+1801000,s.send);
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM echo_value_devices').get().n,0);
 const result=await(await refreshRegistered(s.req(now+1802000),s.env,now+1802000,s.send)).json();
 assert.equal(result.registered,true);assert.equal(result.connection.retryPaused,false);
 assert.equal(result.connection.retryFailures,0);assert.equal(result.snapshot.solar,'100 W');
});

test('Successful fullscreen wakes only failed opted-in instances; fresh widget proof then supplies Store values',async()=>{
 const s=await setup();await devAuthority(s);await failedSix(s);s.calls.length=0;
 const before=s.db.prepare("SELECT * FROM echo_value_devices WHERE stage='development'").get();
 const answer=await(await readVoice(fullscreen(s),s.env,now+1801000,s.send)).json();
 assert.equal(answer.resolvedStage,'development');assert.equal(answer.snapshot.solar,'100 W');
 const signal=s.calls.flatMap(c=>c.commands).find(c=>c.content.state==='retry');
 assert(signal);assert.equal(signal.content.solar,undefined);
 assert.equal(s.db.prepare("SELECT COUNT(*) n FROM echo_value_devices WHERE stage='live'").get().n,0,'wake alone is not registration');
 const fresh=await(await refreshRegistered(s.req(now+1802000),s.env,now+1802000,s.send)).json();
 assert.equal(fresh.registered,true);assert.equal(fresh.connection.retryPaused,false);assert.equal(fresh.snapshot.solar,'100 W');
 assert.deepEqual(s.db.prepare("SELECT * FROM echo_value_devices WHERE stage='development'").get(),before);
 for(let round=1;round<=3;round++){
  const at=now+1802000+round*60000;
  s.db.prepare('UPDATE households SET live_at=?,live_json=? WHERE id=?').run(new Date(at).toISOString(),JSON.stringify({power_w:100+round,home_w:500+round,battery_soc:50+round}),'a');
  const result=await(await refreshRegistered(s.req(at),s.env,at,s.send)).json();
  assert.equal(result.snapshot.solar,(100+round)+' W');assert.equal(result.snapshot.sampleTime,at);
  assert.equal(result.connection.retryFailures,0);
 }
});

test('Fullscreen timer, other account, failed authority and removed source cannot authorize a restart',async()=>{
 const s=await setup();const dev=await devAuthority(s);await failedSix(s);
 const timer=s.req(now+1801000,null,{connectionVersion:undefined,instanceId:undefined});
 await readVoice(timer,s.env,now+1801000,s.send);
 assert.equal(s.db.prepare('SELECT resume_at FROM echo_value_widget_retries').get().resume_at,0);
 await assert.rejects(()=>readVoice(s.req(now+1801000,null,{userId:'amzn1.ask.account.other',resumeWidgetRetries:true}),s.env,now+1801000,s.send));
 await readVoice(fullscreen(s),s.env,now+1801000,s.send);
 await remove(s.req(now+1801500,null,{stage:'development',packageId:'Solaranlage1811'}),dev,now+1801500);
 const denied=await(await refreshRegistered(s.req(now+1802000),s.env,now+1802000,s.send)).json();
 assert.equal(denied.registered,false);assert.equal(s.db.prepare("SELECT COUNT(*) n FROM echo_value_devices WHERE stage='live'").get().n,0);
});

test('Explicit Store unlink is never overridden by a successful DEV-backed fullscreen',async()=>{
 const s=await setup();await devAuthority(s);await failedSix(s);
 await unlink(s.req(now+1800500),s.env,now+1800500,s.send);
 await readVoice(fullscreen(s),s.env,now+1801000,s.send);
 assert.equal(s.db.prepare('SELECT resume_at FROM echo_value_widget_retries').get().resume_at,0);
 const result=await(await refreshRegistered(s.req(now+1802000),s.env,now+1802000,s.send)).json();
 assert.equal(result.connection.state,'unlinked');assert.equal(result.registered,false);
});

test('Failed control delivery cannot break fullscreen; existing cron retries and delivers the wake',async()=>{
 const s=await setup();await devAuthority(s);await failedSix(s);
 // Fail only Store wake, not the existing DEV data delivery.
 const send=async(url,init)=>{
  if(!url.includes('/auth/')){const c=JSON.parse(init.body);if(c.commands.some(x=>x.content.state==='retry'))return Response.json({}, {status:503});}
  return s.send(url,init);
 };
 const answer=await(await readVoice(fullscreen(s),s.env,now+1801000,send)).json();
 assert.equal(answer.snapshot.solar,'100 W');assert.equal(s.db.prepare('SELECT pending FROM echo_value_widget_retries').get().pending,1);
 s.calls.length=0;await publish({...s.env,PUBLISH_MODE:'scheduled'},now+1802000,s.send);
 assert(s.calls.flatMap(c=>c.commands).some(x=>x.content.state==='retry'));
 assert.equal(s.db.prepare('SELECT pending FROM echo_value_widget_retries').get().pending,0);
});

test('Healthy registration and temporary data failure do not consume the pause budget',async()=>{
 const s=await setup();await register(s.req(now,'a'),s.env,now,s.send);
 for(let n=1;n<=7;n++){
  const reply=await(await refreshRegistered(s.req(now+n*60000),s.env,now+n*60000,s.send)).json();
  assert.equal(reply.connection.retryPaused,false);assert.equal(reply.connection.retryFailures,0);
 }
 s.db.exec("UPDATE households SET live_json=NULL WHERE id='a'");
 await assert.rejects(()=>refreshRegistered(s.req(now+500000),s.env,now+500000,s.send),{code:'snapshot_unavailable'});
 assert.equal(s.db.prepare('SELECT failures FROM echo_value_widget_retries').get().failures,0);
});

test('Successful token-backed Store fullscreen also wakes and preserves its original response',async()=>{
 const s=await setup();await failedSix(s);s.calls.length=0;
 const opened=await(await register(s.req(now+1801000,'a',{connectionVersion:undefined,resumeWidgetRetries:true}),s.env,now+1801000,s.send)).json();
 assert.equal(opened.snapshot.solar,'100 W');assert(!opened.connection);
 assert(s.calls.flatMap(c=>c.commands).some(x=>x.content.state==='retry'));
 const refreshed=await(await refreshRegistered(s.req(now+1802000),s.env,now+1802000,s.send)).json();
 assert.equal(refreshed.registered,true);assert.equal(refreshed.connection.retryPaused,false);
});

test('Grant loss, source rotation and disabled source invalidate a queued fullscreen authority',async()=>{
 for(const change of [s=>s.db.exec('UPDATE access_tokens SET expires=0'),s=>s.db.exec("UPDATE households SET write_hash='changed' WHERE id='a'"),s=>s.db.exec("UPDATE households SET disabled=1 WHERE id='a'")]){
  const s=await setup();await devAuthority(s);await failedSix(s);await readVoice(fullscreen(s),s.env,now+1801000,s.send);change(s);
  const result=await(await refreshRegistered(s.req(now+1802000),s.env,now+1802000,s.send)).json();
  assert.equal(result.registered,false);assert.equal(s.db.prepare("SELECT COUNT(*) n FROM echo_value_devices WHERE stage='live'").get().n,0);
 }
});

test('A removed failed instance cannot be resumed by fullscreen or a new tokenless probe',async()=>{
 const s=await setup();await devAuthority(s);await failedSix(s);
 await remove(s.req(now+1800500),s.env,now+1800500);
 await readVoice(fullscreen(s),s.env,now+1801000,s.send);
 assert.equal(s.db.prepare('SELECT resume_at FROM echo_value_widget_retries').get().resume_at,0);
 await assert.rejects(()=>refreshRegistered(s.req(now+1802000),s.env,now+1802000,s.send),{code:'stale_event'});
});

test('Protocol2 remains on bounded retries and does not acquire protocol3 state',async()=>{
 const s=await setup();
 await assert.rejects(()=>refreshRegistered(s.req(now,null,{connectionVersion:2}),s.env,now,s.send),{code:'verified_registration_required'});
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM echo_value_widget_retries').get().n,0);
});
