import assert from 'node:assert/strict';
import {inflateSync} from 'node:zlib';
import {widgetImage,sha} from './worker.mjs';
import {statusText} from './status-png.mjs';
const token='a'.repeat(64),write='b'.repeat(64),grant={tokenHash:await sha(token),tenant:'private-test',version:await sha(write)};
let reads=0,disabled=false,rotated=false,watts=721;
const env={WIDGET_READ_GRANT:JSON.stringify(grant),SOURCE_DB:{prepare(sql){assert.match(sql,/^SELECT/);assert.doesNotMatch(sql,/UPDATE|DELETE|INSERT|access_tokens/i);return {bind(id){assert.equal(id,'private-test');return {async first(){reads++;return disabled?null:{write_hash:rotated?'c'.repeat(64):write,live_at:new Date().toISOString(),power_w:19,home_w:watts,battery_soc:94};}};}};}}};
const req=(col='1',key=token)=>new Request('https://example.test/value.png?k='+key+'&col='+col);
assert.equal((await widgetImage(req('2'),env)).status,403);
assert.equal((await widgetImage(req('1','d'.repeat(64)),env)).status,403);assert.equal(reads,0);
const png=async()=>{const r=await widgetImage(req(),env);assert.equal(r.status,200);assert.equal(r.headers.get('Cache-Control'),'no-store, max-age=0');const b=new Uint8Array(await r.arrayBuffer());assert.equal(new DataView(b.buffer).getUint32(20),64);assert(new TextDecoder().decode(b).includes('tRNS'));return b;};
const before=await png();watts=811;assert.notDeepEqual(await png(),before);
// Advancing the clock does not invalidate this revocable widget handle.
const originalNow=Date.now;Date.now=()=>originalNow()+7*86400000;try{await png();}finally{Date.now=originalNow;}
for(const col of ['0','3'])assert.equal((await widgetImage(req(col),env)).status,200);
rotated=true;assert.equal((await widgetImage(req(),env)).status,403);rotated=false;
disabled=true;assert.equal((await widgetImage(req(),env)).status,403);
assert.equal((await widgetImage(new Request('https://example.test/internal/enroll'),env)).status,404);
disabled=false;
const time=Date.parse('2026-10-28T17:45:00Z');
assert.deepEqual(statusText({live_at:'2026-10-28T17:44:00Z',timezone:'Europe/Berlin'},time),{text:'Stand: 28.10.26, 18:44',stale:false});
assert.equal(statusText({live_at:'2026-10-28T17:30:00Z',timezone:'Europe/Berlin'},time).text,'Veraltet: 28.10.26, 18:30');
const status=await widgetImage(new Request('https://example.test/status.png?k='+token),env);assert.equal(status.status,200);const statusBytes=new Uint8Array(await status.arrayBuffer());assert.equal(new DataView(statusBytes.buffer).getUint32(16),789);assert.equal(new DataView(statusBytes.buffer).getUint32(20),84);assert.equal(statusBytes[25],6);
// Preserve full alpha coverage: the former coordinate downscale overwrote
// antialiased edges. The new line must remain RGBA with many distinct levels.
const chunks=[];for(let at=8;at+12<=statusBytes.length;){const length=new DataView(statusBytes.buffer).getUint32(at);if(new TextDecoder().decode(statusBytes.slice(at+4,at+8))==='IDAT')chunks.push(statusBytes.slice(at+8,at+8+length));at+=length+12;}
const raw=inflateSync(Buffer.concat(chunks)),levels=new Set();assert.equal(raw.length,84*(789*4+1));
for(let y=0;y<84;y++){assert.equal(raw[y*(789*4+1)],0);for(let x=0;x<789;x++)levels.add(raw[y*(789*4+1)+1+x*4+3]);}
assert(levels.has(0)&&levels.has(255)&&levels.size>30,'transparent background and smooth antialiased edges');
assert.equal((await widgetImage(new Request('https://example.test/status.png?k='+'d'.repeat(64)),env)).status,403);
console.log('PASS: transparent PNG, changing live values, 7-day access, three-column restriction, wrong-token rejection before DB, revocation and no public enrollment.');
