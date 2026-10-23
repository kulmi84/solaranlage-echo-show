import test from 'node:test';
import assert from 'node:assert/strict';
import {content, commands, skillToken, push} from './push.mjs';
const now = Date.parse('2026-10-23T12:00:00Z');
const data = {power_w: 2300, home_w: 1200, battery_soc: 72, received_at: '2026-10-23T11:59:00Z'};
test('real values with measurement timestamp and missing value placeholder', () => {
  const value = content(data, now);
  assert.equal(value.production, '2,3 kW');
  assert.equal(value.consumption, '1,2 kW');
  assert.equal(value.battery, '72 %');
  assert.match(value.stand, /13:59/);
  assert.equal(content({...data, home_w: null}, now).consumption, '—');
});
test('stale values remain visible with warning', () => {
  const value = content(data, now + 300000);
  assert.match(value.status, /VERALTET/);
  assert.equal(value.production, '2,3 kW');
});
test('future and invalid timestamps cannot look current', () => {
  for (const stamp of ['bad', '2027-01-01T00:00:00Z'])
    assert.throws(() => content({...data, received_at: stamp}, now));
});
test('each push targets one explicit device and only Solar/live', () => {
  const packet = commands('amzn1.ask.device.example', data, now);
  assert.deepEqual(packet.target, {type: 'DEVICES', items: ['amzn1.ask.device.example']});
  assert.equal(packet.commands[0].namespace, 'Solar');
  assert.equal(packet.commands[0].key, 'live');
  assert.throws(() => commands('', data, now));
});
test('LWA token is scoped to datastore at fixed Amazon endpoint', async () => {
  await skillToken({ALEXA_CLIENT_ID:'test-id', ALEXA_CLIENT_SECRET:'test-secret'}, async (url, init) => {
    assert.equal(url, 'https://api.amazon.com/auth/o2/token');
    assert.equal(init.body.get('scope'), 'alexa::datastore');
    assert.equal(init.redirect, 'manual');
    return Response.json({access_token:'test-token'});
  });
});
test('rejected updates are errors rather than reported success', async () => {
  await assert.rejects(push('test', 'amzn1.ask.device.example', data,
    async () => new Response('', {status:429})), /datastore_429/);
});
test('HTTP 200 without device delivery is not success', async()=>{
  await assert.rejects(push('test','amzn1.ask.device.example',data,
    async()=>Response.json({results:[{type:'DEVICE_UNAVAILABLE'}]})),/dispatch:DEVICE_UNAVAILABLE/);
});
test('only explicit device SUCCESS confirms delivery', async()=>{
  assert.equal(await push('test','amzn1.ask.device.example',data,
    async()=>Response.json({results:[{type:'SUCCESS'}]})),200);
});
test('default fetch retains the native Workers global receiver',async()=>{
  const original=globalThis.fetch;
  try {
    globalThis.fetch=function(url,init){
      assert.equal(this,globalThis);
      return Promise.resolve(Response.json(url.includes('/auth/') ? {access_token:'test'} : {results:[{type:'SUCCESS'}]}));
    };
    assert.equal(await skillToken({ALEXA_CLIENT_ID:'id',ALEXA_CLIENT_SECRET:'secret'}),'test');
    assert.equal(await push('test','amzn1.ask.device.example',data),200);
  } finally { globalThis.fetch=original; }
});
test('redirects are rejected without forwarding credentials',async()=>{
  await assert.rejects(skillToken({ALEXA_CLIENT_ID:'id',ALEXA_CLIENT_SECRET:'secret'},async(url,init)=>{
    assert.equal(init.redirect,'manual');
    return new Response(null,{status:302,headers:{Location:'https://example.invalid/'}});
  }),/lwa_302/);
});
test('certification fixture is always visibly labelled as demo',()=>{
  assert.equal(content({...data,demo:true},now).status,'DEMO · keine Live-Werte');
  assert.equal(content(data,now).status,'Live-Werte');
});
