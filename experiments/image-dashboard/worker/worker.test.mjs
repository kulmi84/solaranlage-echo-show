import test from 'node:test';
import assert from 'node:assert/strict';
import {inflateSync} from 'node:zlib';
import worker,{clockPng} from './worker.mjs';
test('clock is a valid indexed PNG and changes with server time',async()=>{
  const a=await clockPng(new Date('2026-10-20T12:00:00Z'));
  const b=await clockPng(new Date('2026-10-20T12:00:10Z'));
  assert.deepEqual([...a.slice(0,8)],[137,80,78,71,13,10,26,10]);
  assert.notDeepEqual(a,b);
  let pos=8;const idat=[];
  while(pos<a.length){const size=new DataView(a.buffer,a.byteOffset+pos,4).getUint32(0);
    const type=new TextDecoder().decode(a.slice(pos+4,pos+8));
    if(type==='IDAT')idat.push(a.slice(pos+8,pos+8+size));pos+=size+12;}
  const raw=inflateSync(Buffer.concat(idat)); assert.equal(raw.length,855*160);
  assert.ok(raw.includes(1));
});
test('route serves only the test PNG with caching disabled',async()=>{
  const ok=await worker.fetch(new Request('https://example.test/clock.png?n=123'));
  assert.equal(ok.status,200);assert.equal(ok.headers.get('Content-Type'),'image/png');
  assert.match(ok.headers.get('Cache-Control'),/no-store/);
  assert.equal((await worker.fetch(new Request('https://example.test/pv'))).status,404);
  assert.equal((await worker.fetch(new Request('https://example.test/clock.png',{method:'POST'}))).status,404);
});
