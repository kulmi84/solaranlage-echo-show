// Executes generated root expressions with real handler reply fixtures.
// This is not an Echo/APL runtime acceptance test.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const doc=JSON.parse(readFileSync(process.argv[2],'utf8'));
const replies=JSON.parse(readFileSync(process.argv[3],'utf8'));
const root=doc.mainTemplate.items[0];
const cached=process.argv[4]==='cached';
const state={Math,viewport:{width:310,height:440},elapsedTime:0,utcTime:1795340000000,displayState:'foreground',
 SolarLive:null,displaySnapshot:{sampleTime:0,stamp:''},layoutScale:1};
if(cached)state.displaySnapshot={sampleTime:123,stamp:'Originalzeit',solar:'100 W',home:'200 W',battery:'50 %'};
const context=vm.createContext(state),sent=[];
const evaluate=v=>typeof v==='string'&&v.startsWith('${')?vm.runInContext(v.slice(2,-1),context,{timeout:1000}):v;
for(const b of root.bind)if(b.name!=='displaySnapshot')state[b.name]=evaluate(b.value);
function commands(items){for(const c of items){
 if(c.when&&!evaluate(c.when))continue;
 if(c.type==='SetValue'){
  state[c.property]=evaluate(c.value);
  if(c.property==='snapshot')state.displaySnapshot=state.snapshot;
 }
 if(c.type==='Sequential')commands(c.commands);
 if(c.type==='SendEvent'){
  sent.push(state.elapsedTime);
  commands(cached?replies.failures[Math.min(sent.length-1,5)]:(sent.length<=6?replies.failures[sent.length-1]:replies.success));
 }
}}
function tick(t){state.elapsedTime=t;state.utcTime=1795340000000+t;for(const h of root.handleTick)if(evaluate(h.when))commands(h.commands);}
commands(root.onMount);
for(let t=0;t<=7200000;t+=1000){if(t%10000===0)state.wakePending=true;tick(t);}
if(cached){
 assert.equal(state.retryPaused,false);assert(sent.length>6);assert.equal(state.displaySnapshot.stamp,'Originalzeit');
 console.log(JSON.stringify({cachedValuesNeverPaused:true}));process.exit(0);
}
assert.deepEqual(sent,[0,60000,180000,420000,900000,1800000]);
assert.equal(state.retryPaused,true);assert.equal(state.linkPaused,false);
const stamp=root.items[0].item.items[4].items[0];
assert.equal(evaluate(stamp.text),'Keine Verbindung. Bitte Skill öffnen.');
assert(state.connectionKey);
// Neither a foreign wake nor a stale wake can restart the paused client.
state.connectionEnvelope={version:1,state:'retry',revision:1000};state.connectionEventKey='foreign';tick(7201000);
assert.equal(sent.length,6);
state.connectionEventKey=state.connectionKey;state.connectionEnvelope.revision=0;tick(7202000);
assert.equal(sent.length,6);
// Successful fullscreen publishes one scoped retry control; next probe verifies.
state.connectionEnvelope.revision=1000;tick(7203000);
assert.equal(sent.length,7);tick(7204000);
assert.equal(state.retryPaused,false);assert.equal(state.linkPaused,false);
assert.equal(state.retryFailures,0);assert.equal(state.retryDelayMs,60000);
const next=state.nextRefreshAt;
tick(next-1000);assert.equal(sent.length,7);
tick(next);assert.equal(sent.length,8);
assert.equal(state.snapshot.stamp,replies.success.find(c=>c.property==='snapshot').value.stamp);
console.log(JSON.stringify({attemptsBeforePause:6,pausedRequests:0,fullscreenWake:true,originalTime:true,resumedMinute:true}));
