import test from 'node:test';
import assert from 'node:assert/strict';
import {register, updateAll} from './worker.mjs';

function environment(row = {id:'household-test',write_hash:'original'}) {
  const entries = new Map(), queries = [];
  return {REGISTER_KEY:'test-key', entries, queries,
    SOURCE_DB:{prepare(sql) { queries.push(sql); return {bind() {return {first:async()=>row};}};}},
    REGISTRATIONS:{get:async key=>entries.has(key)?JSON.parse(entries.get(key)):null,
      put:async(key,value)=>entries.set(key,value), delete:async key=>entries.delete(key),
      list:async()=>({keys:[...entries.keys()].map(name=>({name})),list_complete:true})}};
}
function request(data, key='test-key') {
  return new Request('https://example.invalid/registrations',{method:'POST',
    headers:{Authorization:'Bearer '+key},body:JSON.stringify(data)});
}
const target = {action:'install',device:'amzn1.ask.device.testing',user:'amzn1.ask.account.testing',access:'a'.repeat(64)};
test('registration rejects caller without the dedicated secret before database access', async()=>{
  const env=environment();
  assert.equal((await register(request(target,'wrong'),env)).status,401);
  assert.equal(env.queries.length,0);
});
test('registration validates existing account; source DB is only read; access token is not persisted',async()=>{
  const env=environment();
  assert.equal((await register(request(target),env)).status,200);
  assert.equal(env.entries.size,1);
  assert.ok(env.queries.every(query=>query.startsWith('SELECT ')));
  assert.ok(![...env.entries.values()].join('').includes(target.access));
});
test('invalid or disabled account cannot register',async()=>{
  const env=environment(null);
  assert.equal((await register(request(target),env)).status,401);
  assert.equal(env.entries.size,0);
});
test('an authenticated certification account registers without accessing a real household',async()=>{
  const env=environment({id:'review-certification-demo',write_hash:'synthetic'});
  assert.equal((await register(request(target),env)).status,200);
  assert.equal(JSON.parse([...env.entries.values()][0]).tenant,'review-certification-demo');
});
test('only the same skill user can remove the device registration',async()=>{
  const env=environment();
  await register(request(target),env);
  await register(request({...target,action:'remove',user:'amzn1.ask.account.other'}),env);
  assert.equal(env.entries.size,1);
  await register(request({...target,action:'remove'}),env);
  assert.equal(env.entries.size,0);
});
test('revoked source household removes registration without contacting Amazon',async()=>{
  const env=environment(null);
  env.entries.set('device:test',JSON.stringify({tenant:'test',device:target.device,version:'old'}));
  const counts=await updateAll(env);
  assert.equal(counts.revoked,1);
  assert.equal(counts.accepted,0);
  assert.equal(env.entries.size,0);
});
