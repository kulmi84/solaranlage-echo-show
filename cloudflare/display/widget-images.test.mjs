import assert from 'node:assert/strict';
import {widgetImageRoute} from './widget-images.mjs';
import {sealPayload,sessionRoute} from './sessions.mjs';
const before={fetch:async(request,env)=>await sessionRoute(request,env)||new Response('Not found',{status:404})};
import after from './worker.mjs';
const secret='a'.repeat(64),writeA='b'.repeat(64),writeB='c'.repeat(64);
const hash=async s=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s))),n=>n.toString(16).padStart(2,'0')).join('');
let reads=0,disabled=false,rotated=false;
const now=Math.floor(Date.now()/1000);
const grant=async(t,w,i=now)=>sealPayload({v:2,t,r:await hash(w),i,e:i+86400},secret);
const a=await grant('house-a',writeA),b=await grant('house-b',writeB);
const env={DISPLAY_KEY:secret,DISPLAY_DB:{prepare(sql){assert.match(sql,/^SELECT /);assert.doesNotMatch(sql,/INSERT|UPDATE|DELETE/);return {bind(tenant){assert(['house-a','house-b'].includes(tenant));return {async first(){reads++;if(disabled)return null;const sample={power_w:tenant==='house-a'?2100:5100,home_w:tenant==='house-a'?600:1200,battery_soc:tenant==='house-a'?22:88,received_at:new Date().toISOString()};return {write_hash:rotated?'revoked':tenant==='house-a'?writeA:writeB,timezone:'Europe/Berlin',live_at:sample.received_at,live_json:JSON.stringify(sample),history_json:null,...sample};}};}};}}};
const request=(token,path='/widget/value.png',col='1')=>new Request('https://display.test'+path+'?s='+token+'&col='+col);
const png=async token=>{const r=await widgetImageRoute(request(token),env);assert.equal(r.status,200);assert.equal(r.headers.get('Cache-Control'),'no-store, max-age=0');return new Uint8Array(await r.arrayBuffer());};
assert.notDeepEqual(await png(a),await png(b),'accounts must have different values');
assert.equal((await widgetImageRoute(request('tampered'),env)).status,403);const count=reads;
assert.equal((await widgetImageRoute(request(a,'/widget/value.png','2'),env)).status,403);assert.equal(reads,count);
const expired=await grant('house-a',writeA,now-86401);assert.equal((await widgetImageRoute(request(expired),env)).status,403);assert.equal(reads,count);
assert.equal((await widgetImageRoute(request(a,'/widget/status.png'),env)).status,200);
rotated=true;assert.equal((await widgetImageRoute(request(a),env)).status,403);rotated=false;
disabled=true;assert.equal((await widgetImageRoute(request(a),env)).status,403);disabled=false;
assert.equal(await widgetImageRoute(new Request('https://display.test/tile.png'),env),null);
// Existing fullscreen requests remain byte-identical through the new entrypoint.
for(const path of ['/tile.png?s='+a+'&page=live&row=0&col=1&layout=final','/status.png?s='+a,'/not-a-route']){
 const request=new Request('https://display.test'+path);const old=await before.fetch(request,env),current=await after.fetch(request,env);
 assert.equal(current.status,old.status);assert.deepEqual([...current.headers],[...old.headers]);assert.deepEqual(new Uint8Array(await current.arrayBuffer()),new Uint8Array(await old.arrayBuffer()));
}
console.log('PASS: two-account isolation, expiry, tamper rejection, restricted columns, revocation, status, unchanged fullscreen responses.');
