import {test} from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {digest,register,refreshRegistered,unlink,relink,remove,publish} from './worker.mjs';
const now=Date.parse('2026-11-22T12:00:00Z');

async function setup(){
 const db=new DatabaseSync(':memory:');
 for(const file of ['../public-beta/schema.sql','./schema.sql','./connection-schema.sql'])db.exec(readFileSync(new URL(file,import.meta.url),'utf8'));
 const wrap=(sql,args=[])=>({bind(...a){return wrap(sql,a)},async first(){return db.prepare(sql).get(...args)},async all(){return {results:db.prepare(sql).all(...args)}},async run(){return {meta:{changes:Number(db.prepare(sql).run(...args).changes)}}}});
 const env={DB:{prepare:sql=>wrap(sql),async batch(items){db.exec('BEGIN');try{const out=[];for(const item of items)out.push(await item.run());db.exec('COMMIT');return out}catch(e){db.exec('ROLLBACK');throw e}}},REGISTRATION_SECRET:'r'.repeat(40),SUBJECT_HASH_KEY:'s'.repeat(40),STAGE:'live',WIDGET_PACKAGE_ID:'SolarAccountImageBuild1211',LIVE_PACKAGE_ID:'SolarAccountImageBuild1211',DATASTORE_NAMESPACE:'SolarAccountImagesV3',DATASTORE_KEY:'snapshot',PUBLISH_ENABLED:'true',PUBLISH_MODE:'inline',CONNECTION_STATUS_ENABLED:'true'};
 for(const [id,n] of [['a',100],['b',200]]){
  db.prepare('INSERT INTO households(id,write_hash,timezone,created,live_at,live_json) VALUES(?,?,?,?,?,?)').run(id,'key-'+id,'Europe/Berlin',0,new Date(now).toISOString(),JSON.stringify({power_w:n,home_w:n+1,battery_soc:50}));
  db.prepare('INSERT INTO access_tokens VALUES(?,?,?)').run(await digest(id.repeat(64)),id,now/1000+3600);
 }
 const req=(at,token=null,extra={})=>new Request('https://test/internal/refresh',{method:'POST',headers:{'X-Solar-Registration':env.REGISTRATION_SECRET,...(token?{Authorization:'Bearer '+token.repeat(64)}:{})},body:JSON.stringify({stage:env.STAGE,packageId:env.WIDGET_PACKAGE_ID,userId:'amzn1.ask.account.a',deviceId:'amzn1.ask.device.a',instanceId:'one',occurredAt:new Date(at).toISOString(),connectionVersion:2,...extra})});
 const calls=[];let failDelivery=false;
 const send=async(url,init)=>{if(url.includes('/auth/'))return Response.json({access_token:'synthetic'});const data=JSON.parse(init.body);calls.push(data);if(failDelivery)return Response.json({}, {status:503});return Response.json({results:data.target.items.map(deviceId=>({deviceId,type:'SUCCESS'}))})};
 return {db,env,req,calls,send,setFailure:v=>{failDelivery=v}};
}

test('Unknown/tokenless is not unlinked; unknown observation contains no household authority',async()=>{
 const s=await setup();await assert.rejects(()=>refreshRegistered(s.req(now),s.env,now,s.send),{code:'verified_registration_required'});
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM echo_value_link_states').get().n,0);
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM echo_value_devices').get().n,0);
 assert.equal(s.db.prepare('SELECT active FROM echo_value_widget_connections').get().active,1);
 assert.equal(s.calls.length,0);
});

test('Confirmed unlink stops; fresh account-link signal and fresh tokenless widget resume same household',async()=>{
 const s=await setup();await register(s.req(now,'a'),s.env,now,s.send);
 const before=s.db.prepare('SELECT * FROM echo_value_devices').get();
 await unlink(s.req(now+1000),s.env,now+1000,s.send);
 const stop=await(await refreshRegistered(s.req(now+2000),s.env,now+2000,s.send)).json();
 assert.equal(stop.registered,false);assert.equal(stop.connection.state,'unlinked');assert(!stop.snapshot);
 assert.equal(s.calls.at(-1).commands[0].content.state,'unlinked');
 assert.equal(s.db.prepare('SELECT active FROM echo_value_devices').get().active,0);
 s.calls.length=0;
 await relink(s.req(now+3000,'a'),s.env,now+3000,s.send);
 assert.equal(s.db.prepare('SELECT active FROM echo_value_devices').get().active,0,'signal cannot reactivate a binding');
 assert.equal(s.calls.length,1);assert.equal(s.calls[0].commands[0].content.state,'linked');
 assert.equal(s.calls[0].commands[0].content.solar,undefined,'wake carries no readings');
 const resumed=await(await refreshRegistered(s.req(now+4000),s.env,now+4000,s.send)).json();
 assert.equal(resumed.snapshot.solar,'100 W');assert.equal(resumed.connection.state,'linked');
 assert.equal(resumed.snapshot.sampleTime,now,'original measurement time is preserved');
 assert.equal(s.db.prepare('SELECT household FROM echo_value_devices').get().household,before.household);
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM echo_value_revocations').get().n,1,'revocation history is retained');
});

test('Link after unknown observation automatically supplies a fresh authorized instance',async()=>{
 const s=await setup();await assert.rejects(()=>refreshRegistered(s.req(now),s.env,now,s.send));
 await relink(s.req(now+1000,'b'),s.env,now+1000,s.send);
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM echo_value_devices').get().n,0);
 const result=await(await refreshRegistered(s.req(now+2000),s.env,now+2000,s.send)).json();
 assert.equal(result.snapshot.solar,'200 W');assert.equal(s.db.prepare('SELECT household FROM echo_value_devices').get().household,'b');
});

test('Delayed unlink/relink and stale widget events cannot reverse latest lifecycle decision',async()=>{
 const s=await setup();await register(s.req(now,'a'),s.env,now,s.send);
 await unlink(s.req(now+3000),s.env,now+3000,s.send);
 await relink(s.req(now+2000,'a'),s.env,now+4000,s.send);
 const result=await(await refreshRegistered(s.req(now+5000),s.env,now+5000,s.send)).json();
 assert.equal(result.connection.state,'unlinked');
 await assert.rejects(()=>refreshRegistered(s.req(now+1000),s.env,now+5000,s.send),{code:'stale_event'});
 await relink(s.req(now+6000,'a'),s.env,now+6000,s.send);
 await unlink(s.req(now+3000),s.env,now+7000,s.send);
 const resumed=await(await refreshRegistered(s.req(now+8000),s.env,now+8000,s.send)).json();
 assert.equal(resumed.connection.state,'linked');assert.equal(resumed.snapshot.solar,'100 W');
});

test('Removed instance and wrong account cannot use restart authority',async()=>{
 const s=await setup();await register(s.req(now,'a'),s.env,now,s.send);
 await remove(s.req(now+1000),s.env,now+1000);
 await relink(s.req(now+2000,'a'),s.env,now+2000,s.send);
 await assert.rejects(()=>refreshRegistered(s.req(now+3000),s.env,now+3000,s.send),{code:'stale_event'});
 await assert.rejects(()=>refreshRegistered(s.req(now+3000,null,{userId:'amzn1.ask.account.other'}),s.env,now+3000,s.send),{code:'verified_registration_required'});
 assert.equal(s.db.prepare('SELECT active FROM echo_value_usages').get().active,0);
});

test('Expired access alone remains linked; grant loss, disable and rotation cannot authorize restart',async()=>{
 for(const mutate of [s=>s.db.exec('UPDATE access_tokens SET expires=0'),s=>s.db.exec('UPDATE households SET disabled=1'),s=>s.db.exec("UPDATE households SET write_hash='rotated' WHERE id='a'")]){
  const s=await setup();await register(s.req(now,'a'),s.env,now,s.send);await unlink(s.req(now+1000),s.env,now+1000,s.send);
  await relink(s.req(now+2000,'a'),s.env,now+2000,s.send);mutate(s);
  await assert.rejects(()=>refreshRegistered(s.req(now+3000),s.env,now+3000,s.send));
 }
 const s=await setup();await register(s.req(now,'a'),s.env,now,s.send);
 s.db.exec('UPDATE access_tokens SET expires=0');s.db.prepare('INSERT INTO refresh_tokens VALUES(?,?,?)').run('refresh','a',now/1000+3600);
 const current=await(await refreshRegistered(s.req(now+1000),s.env,now+1000,s.send)).json();
 assert.equal(current.connection.state,'linked');assert.equal(current.snapshot.solar,'100 W');
});

test('Failed wake is retained and retried by existing cron; different stage and legacy stay untouched',async()=>{
 const s=await setup();await register(s.req(now,'a'),s.env,now,s.send);await unlink(s.req(now+1000),s.env,now+1000,s.send);
 s.setFailure(true);await relink(s.req(now+2000,'a'),s.env,now+2000,s.send);
 assert.equal(s.db.prepare('SELECT pending FROM echo_value_widget_connections').get().pending,1);
 s.setFailure(false);s.calls.length=0;
 await publish({...s.env,PUBLISH_MODE:'scheduled'},now+3000,s.send);
 assert.equal(s.calls.length,1);assert.equal(s.calls[0].commands[0].content.state,'linked');
 assert.equal(s.db.prepare('SELECT pending FROM echo_value_widget_connections').get().pending,0);
 assert.equal(s.db.prepare('SELECT active FROM echo_value_devices').get().active,0);
 const legacy=await setup();await register(legacy.req(now,'a',{connectionVersion:undefined}),legacy.env,now,legacy.send);
 assert.equal(legacy.db.prepare('SELECT COUNT(*) n FROM echo_value_widget_connections').get().n,0);
});

test('A failed old-snapshot clear still persists the explicit unlink for the next status reply',async()=>{
 const s=await setup();await register(s.req(now,'a'),s.env,now,s.send);
 s.setFailure(true);await assert.rejects(()=>unlink(s.req(now+1000),s.env,now+1000,s.send));
 const result=await(await refreshRegistered(s.req(now+2000),s.env,now+2000,s.send)).json();
 assert.equal(result.connection.state,'unlinked');assert.equal(result.registered,false);
 assert.equal(s.db.prepare('SELECT pending FROM echo_value_widget_connections').get().pending,1);
});

test('Status and wake keys are isolated by exact device, instance, account and stage',async()=>{
 const s=await setup();await register(s.req(now,'a'),s.env,now,s.send);
 await register(s.req(now+1000,'a',{instanceId:'two'}),s.env,now+1000,s.send);
 await register(s.req(now+1000,'b',{userId:'amzn1.ask.account.b',deviceId:'amzn1.ask.device.b'}),s.env,now+1000,s.send);
 s.calls.length=0;await unlink(s.req(now+2000),s.env,now+2000,s.send);
 const signals=s.calls.flatMap(x=>x.commands.map(c=>({target:x.target.items,c}))).filter(x=>x.c.key.startsWith('connection-'));
 assert.equal(signals.length,2);assert.notEqual(signals[0].c.key,signals[1].c.key);
 assert(signals.every(x=>x.target.length===1 && x.target[0]==='amzn1.ask.device.a'));
 const other=await(await refreshRegistered(s.req(now+3000,null,{userId:'amzn1.ask.account.b',deviceId:'amzn1.ask.device.b'}),s.env,now+3000,s.send)).json();
 assert.equal(other.connection.state,'linked');assert.equal(other.snapshot.solar,'200 W');
 const dev={...s.env,STAGE:'development',WIDGET_PACKAGE_ID:'Solaranlage1811',TEST_PACKAGE_ID:'Solaranlage1811',DATASTORE_NAMESPACE:'Solaranlage1811'};
 await register(s.req(now+4000,'a',{stage:'development',packageId:'Solaranlage1811'}),dev,now+4000,s.send);
 assert.equal(s.db.prepare("SELECT COUNT(*) n FROM echo_value_link_states WHERE stage='development'").get().n,0);
});

test('Disabled feature performs no status writes and protocol v1 retains old response shape',async()=>{
 const s=await setup();s.env.CONNECTION_STATUS_ENABLED='false';
 const legacy=await(await register(s.req(now,'a'),s.env,now,s.send)).json();
 assert(!legacy.connection);
 await unlink(s.req(now+1000),s.env,now+1000,s.send);
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM echo_value_link_states').get().n,0);
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM echo_value_widget_connections').get().n,0);
 const enabled=await setup();const v1=await(await register(enabled.req(now,'a',{connectionVersion:1}),enabled.env,now,enabled.send)).json();
 assert(!v1.connection);
});

test('A paused active observer is not expired before a later genuine relink',async()=>{
 const s=await setup();await register(s.req(now,'a'),s.env,now,s.send);await unlink(s.req(now+1000),s.env,now+1000,s.send);
 const later=now+40*86400000;
 await publish({...s.env,PUBLISH_MODE:'scheduled'},later,s.send);
 assert.equal(s.db.prepare('SELECT COUNT(*) n FROM echo_value_widget_connections').get().n,1);
 s.db.exec('UPDATE access_tokens SET expires=9999999999');s.calls.length=0;
 await relink(s.req(later,'a'),s.env,later,s.send);
 assert.equal(s.calls[0].commands[0].content.state,'linked');
});

test('Late removal wins over a later tokenless observation; no per-minute observer writes',async()=>{
 const s=await setup();await register(s.req(now,'a'),s.env,now,s.send);
 const before=s.db.prepare('SELECT * FROM echo_value_widget_connections').get();
 await refreshRegistered(s.req(now+3000),s.env,now+3000,s.send);
 assert.deepEqual(s.db.prepare('SELECT * FROM echo_value_widget_connections').get(),before);
 await remove(s.req(now+1000),s.env,now+4000);
 await relink(s.req(now+5000,'a'),s.env,now+5000,s.send);
 await assert.rejects(()=>refreshRegistered(s.req(now+6000),s.env,now+6000,s.send),{code:'stale_event'});
});
