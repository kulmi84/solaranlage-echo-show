import test from 'node:test';import assert from 'node:assert/strict';import {writeFileSync} from 'node:fs';
import {seal,sealPayload,open,sessionRoute,getValues} from './sessions.mjs';import {cleanValues,dashboardPng,housePng,finalTilePng} from './dashboard.mjs';
import {delegateDisplay,DISPLAY_SECONDS} from './display-access.mjs';
const secret='a'.repeat(64),access='b'.repeat(64),env={DISPLAY_KEY:secret,SESSION_KEY:'c'.repeat(64)};
const sample={power_w:3400,pv_dc_w:3100,bkw_w:300,home_w:1250,grid_import_w:0,grid_export_w:2150,battery_soc:72,battery_charge_w:0,battery_discharge_w:0,today_pv_kwh:23.5,today_home_kwh:9.2,today_grid_import_kwh:1.2,today_grid_export_kwh:12.3,today_battery_charge_kwh:4.5,today_battery_discharge_kwh:2.3,energy_date:'2026-10-20',local_date:'2026-10-20',received_at:'2026-10-20T12:00:00Z',received_local:'14:00',history:{month_id:'2026-10',year_id:'2026',month_pv_kwh:740,month_home_kwh:212,month_grid_import_kwh:25,month_grid_export_kwh:430,month_battery_charge_kwh:80,month_battery_discharge_kwh:65,year_pv_kwh:8420,year_home_kwh:2510,year_grid_import_kwh:550,year_grid_export_kwh:5000,year_battery_charge_kwh:1520,year_battery_discharge_kwh:1390}};
const upstream=async(url,options)=>{assert.equal(url,'https://solaranlage-kontodienst.kulmi84.workers.dev/v1/pv');assert.equal(options.headers.Authorization,'Bearer '+access);assert.equal(options.redirect,'manual');return Response.json(sample);};

test('delegated display outlives OAuth expiry, stays read only and stops on revocation',async()=>{
 let linked=true,disabled=false,write='household-write-hash';const queries=[];
 const db={prepare(sql){assert.match(sql,/^SELECT /);queries.push(sql);return {bind(...args){return {async first(){
  if(sql.includes('JOIN access_tokens'))return linked?{id:'household-test',write_hash:write}:null;
  assert.equal(args[0],'household-test');return disabled?null:{write_hash:write,timezone:'Europe/Berlin',live_at:sample.received_at,live_json:JSON.stringify(sample),history_at:sample.received_at,history_json:JSON.stringify(sample.history)};
 }}}};}};
 const extended={...env,DISPLAY_DB:db};
 const created=await sessionRoute(new Request('https://test.test/image/session',{method:'POST',headers:{Authorization:'Bearer '+env.SESSION_KEY,'Content-Type':'application/json'},body:JSON.stringify({access_token:access})}),extended,upstream);
 const grant=await created.json();assert.equal(grant.expires_in,DISPLAY_SECONDS);
 const url=new URL(grant.base_url);const token=url.searchParams.get('s');const payload=await open(token,secret);
 assert.equal(payload.v,2);assert.equal(payload.t,'household-test');assert.equal(payload.a,undefined);
 assert.equal((await open(token,secret,Date.now()+2*3600_000)).t,'household-test');
 await assert.rejects(open(token,secret,Date.now()+24*3600_000));
 linked=false; // Original OAuth token no longer accepted; existing delegation survives.
 const image=()=>new Request(grant.base_url.replace('/dashboard.png','/tile.png')+'&row=0&col=1&layout=final');
 const noOAuth=async()=>{throw Error('should never reuse the expired OAuth token');};
 assert.equal((await sessionRoute(image(),extended,noOAuth)).status,200);
 disabled=true;assert.equal((await sessionRoute(image(),extended,noOAuth)).status,503);
 disabled=false;write='rotated-household-key';assert.equal((await sessionRoute(image(),extended,noOAuth)).status,503);
 await assert.rejects(delegateDisplay(db,access));
 const malformed=await sealPayload({...payload,e:payload.e+1},secret);await assert.rejects(open(malformed,secret));
 assert.ok(queries.every(sql=>!/(UPDATE|INSERT|DELETE|ALTER)/i.test(sql)));
});

test('diagnostics distinguish expired grants and upstream failures without secrets',async()=>{
 const logs=[],original=console.log;console.log=message=>logs.push(JSON.parse(message));
 try{
  const expired=await seal(access,secret,Date.now()-3601_000);
  assert.equal((await sessionRoute(new Request('https://test.test/tile.png?s='+expired+'&n=1600000&row=0&col=1'),env,upstream)).status,403);
  assert.equal(logs.at(-1).reason,'grant_expired');assert.ok(logs.at(-1).grant_age_s>=3600);
  const token=await seal(access,secret);
  assert.equal((await sessionRoute(new Request('https://test.test/tile.png?s='+token+'&n=1600000&row=0&col=1'),env,async()=>new Response('',{status:401}))).status,503);
  assert.equal(logs.at(-1).reason,'upstream_401');assert.equal(logs.at(-1).tick_ms,1600000);
  await sessionRoute(new Request('https://test.test/status.png?s='+token),env,async()=>{throw Error(access);});
  assert.equal(logs.at(-1).reason,'internal');
  const text=JSON.stringify(logs);for(const value of [access,secret,token,expired,env.SESSION_KEY,'https://'])assert.ok(!text.includes(value));
 }finally{console.log=original;}
});
test('encrypted grant hides bearer, authenticates changes and expires',async()=>{
 const stamp=Date.parse('2026-10-20T12:00:00Z'),token=await seal(access,secret,stamp);
 assert.ok(!token.includes(access));assert.equal(await open(token,secret,stamp),access);
 await assert.rejects(open(token,secret,stamp+3600_000));
 await assert.rejects(open(token.slice(0,25)+(token[25]==='A'?'B':'A')+token.slice(26),secret,stamp));
 await assert.rejects(open(token,'d'.repeat(64),stamp));await assert.rejects(open('x'.repeat(3000),secret,stamp));
});
test('anonymous image reads and session creation are denied',async()=>{
 assert.equal((await sessionRoute(new Request('https://test.test/house.png'),env)).status,403);
 assert.equal((await sessionRoute(new Request('https://test.test/dashboard.png'),env)).status,403);
 assert.equal((await sessionRoute(new Request('https://test.test/image/session',{method:'POST'}),env)).status,401);
});
test('small consumption image changes with readings and keeps existing grant protection',async()=>{
 const stamp=Date.parse(sample.received_at);
 const a=await housePng(sample,stamp),b=await housePng({...sample,home_w:876},stamp);
 assert.notDeepEqual(a,b);const view=new DataView(a.buffer,a.byteOffset,a.byteLength);
 assert.equal(view.getUint32(16),480);assert.equal(view.getUint32(20),130);
 writeFileSync(new URL('./preview-house.png',import.meta.url),a);
 const token=await seal(access,secret);
 assert.equal((await sessionRoute(new Request('https://test.test/house.png?s='+token),env,upstream)).status,200);
});
test('all sixteen value tiles render bounded PNGs and invalid coordinates are denied',async()=>{
 const stamp=Date.parse(sample.received_at),token=await seal(access,secret);
 for(const page of ['live','history'])for(let row=0;row<2;row++)for(let col=0;col<4;col++){
  const png=await dashboardPng(sample,page,stamp,{row,col}),v=new DataView(png.buffer,png.byteOffset,png.byteLength);
  assert.equal(v.getUint32(16),279);assert.equal(v.getUint32(20),170);
  if(page==='live'&&row===0&&col===1)writeFileSync(new URL('./preview-tile.png',import.meta.url),png);
 }
 const response=await sessionRoute(new Request('https://test.test/tile.png?s='+token+'&page=live&row=0&col=1'),env,upstream);
 assert.equal(response.status,200);
 assert.equal((await sessionRoute(new Request('https://test.test/tile.png?s='+token+'&row=0&col=9'),env,upstream)).status,404);
 assert.equal((await sessionRoute(new Request('https://test.test/tile.png?row=0&col=1'),env,upstream)).status,403);
});
test('final layout tiles omit per-tile timestamp and shared status changes with timestamp',async()=>{
 const stamp=Date.parse(sample.received_at),other={...sample,received_local:'14:01'};
 const tile={row:0,col:1};const a=await finalTilePng(sample,'live',tile,stamp);
 assert.deepEqual(a,await finalTilePng(other,'live',tile,stamp));
 assert.notDeepEqual(await finalTilePng(sample,'live',null,stamp),await finalTilePng(other,'live',null,stamp));
 assert.equal(new DataView(a.buffer,a.byteOffset).getUint32(16),263);
 writeFileSync(new URL('./preview-final-tile.png',import.meta.url),a);
 const token=await seal(access,secret);
 assert.equal((await sessionRoute(new Request('https://test.test/tile.png?s='+token+'&row=0&col=1&layout=final'),env,upstream)).status,200);
 assert.equal((await sessionRoute(new Request('https://test.test/status.png?s='+token),env,upstream)).status,200);
 assert.equal((await sessionRoute(new Request('https://test.test/status.png'),env,upstream)).status,403);
});
test('verified session creates only an opaque hour-limited read URL',async()=>{
 const request=new Request('https://test.test/image/session',{method:'POST',headers:{Authorization:'Bearer '+env.SESSION_KEY,'Content-Type':'application/json'},body:JSON.stringify({access_token:access,url:'https://attacker.invalid'})});
 const created=await sessionRoute(request,env,upstream);assert.equal(created.status,200);
 const data=await created.json();assert.equal(data.expires_in,3600);assert.ok(!data.base_url.includes(access));
 const result=await sessionRoute(new Request(data.base_url+'&page=live'),env,upstream);
 assert.equal(result.status,200);assert.equal(result.headers.get('Content-Type'),'image/png');assert.match(result.headers.get('Cache-Control'),/no-store/);
 const tampered=new URL(data.base_url);tampered.searchParams.set('page','admin');assert.equal((await sessionRoute(new Request(tampered),env,upstream)).status,404);
});
test('malformed/oversized creation and failed upstream do not mint grants',async()=>{
 const req=body=>new Request('https://test.test/image/session',{method:'POST',headers:{Authorization:'Bearer '+env.SESSION_KEY,'Content-Type':'application/json'},body});
 assert.equal((await sessionRoute(req('x'.repeat(1200)),env,upstream)).status,400);
 assert.equal((await sessionRoute(req('{'),env,upstream)).status,400);
 assert.equal((await sessionRoute(req(JSON.stringify({access_token:access})),env,async()=>new Response('',{status:401}))).status,400);
 await assert.rejects(getValues(access,async()=>new Response('x'.repeat(9000))));
});
test('invalid, stale and wrong-period values are never shown as fresh zero',()=>{
 const v=cleanValues({...sample,battery_soc:101,home_w:-1,today_pv_kwh:7,energy_date:'2026-10-19',history:{month_id:'2026-09',month_pv_kwh:44}},Date.parse('2026-10-20T12:04:00Z'));
 assert.equal(v.live.battery_soc,null);assert.equal(v.live.home_w,null);assert.equal(v.day.pv,null);assert.equal(v.history.month_pv,null);assert.equal(v.stale,true);
 assert.equal(cleanValues({...sample,home_w:0},Date.parse(sample.received_at)).live.home_w,0);
});
test('both dashboard views render valid different PNG snapshots',async()=>{
 const live=await dashboardPng(sample,'live',Date.parse(sample.received_at));const history=await dashboardPng(sample,'history',Date.parse(sample.received_at));
 assert.notDeepEqual(live,history);assert.equal(new DataView(live.buffer).getUint32(16),1280);assert.equal(new DataView(live.buffer).getUint32(20),800);
 writeFileSync(new URL('./preview-live.png',import.meta.url),live);writeFileSync(new URL('./preview-history.png',import.meta.url),history);
});

