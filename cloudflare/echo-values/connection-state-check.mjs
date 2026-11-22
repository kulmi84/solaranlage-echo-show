// Generated APL expressions + actual handler commands, not an Echo runtime.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const doc=JSON.parse(readFileSync(process.argv[2],'utf8'));
const fixture=JSON.parse(readFileSync(process.argv[3],'utf8'));
const root=doc.mainTemplate.items[0];
const state={Math,viewport:{width:310,height:440},elapsedTime:0,utcTime:1795340000000,displayState:'foreground',
 SolarLive:null,displaySnapshot:{sampleTime:123,stamp:'Originalzeit'},layoutScale:1};
const context=vm.createContext(state), sent=[], watches=[];
const evaluate=v=>typeof v==='string'&&v.startsWith('${')?vm.runInContext(v.slice(2,-1),context,{timeout:1000}):v;
for(const b of root.bind)if(b.name!=='displaySnapshot')state[b.name]=evaluate(b.value);
function commands(items){for(const c of items){
 if(c.when&&!evaluate(c.when))continue;
 if(c.type==='SetValue')state[c.property]=evaluate(c.value);
 if(c.type==='Sequential')commands(c.commands);
 if(c.type==='SendEvent')sent.push(state.elapsedTime);
 if(c.type==='DataStore:WatchObject')watches.push(evaluate(c.key));
}}
function tick(at){state.elapsedTime=at;state.utcTime=1795340000000+at;for(const t of root.handleTick)if(evaluate(t.when))commands(t.commands);}
commands(root.onMount);
commands(fixture.stop);tick(0);
assert.equal(state.linkPaused,true);
assert.equal(state.connectionStatus,'Bitte Konto in der Alexa-App verknüpfen');
const before=sent.length;
for(let t=1000;t<=3600000;t+=1000){state.wakePending=true;tick(t);}
assert.equal(sent.length,before,'no refresh/reveal request during confirmed pause');
assert(watches.includes(state.connectionKey));
const savedRevision=state.connectionRevision;
// A stale or foreign control cannot resume this instance.
state.connectionEventKey='connection-'+'f'.repeat(64);
state.connectionEnvelope={version:1,state:'linked',revision:savedRevision+1000};tick(3601000);
assert.equal(state.linkPaused,true);
state.connectionEventKey=state.connectionKey;
state.connectionEnvelope={version:1,state:'linked',revision:savedRevision-1};tick(3602000);
assert.equal(state.linkPaused,true);
// Even an asynchronously arriving old/new snapshot cannot unpause by itself.
state.displaySnapshot={sampleTime:999,stamp:'Originalzeit'};tick(3603000);
assert.equal(state.linkPaused,true);assert.equal(sent.length,before);
state.connectionEnvelope={version:1,state:'linked',revision:savedRevision+1000};tick(3604000);
assert.equal(state.linkPaused,false);assert.equal(state.linkResumePending,true);
assert.equal(sent.length,before+1,'one fresh identity verification after matching signal');
commands(fixture.success);tick(3604000);
assert.equal(state.linkResumePending,false);
assert.equal(state.retryDelayMs,60000);
// The response and live expression now point at the same original measurement.
state.displaySnapshot=state.snapshot;tick(3605000);
const deadline=state.nextRefreshAt;
tick(deadline-1000);assert.equal(sent.length,before+1);
tick(deadline);assert.equal(sent.length,before+2,'60-second schedule resumes');
assert.equal(state.snapshot.stamp,fixture.success.find(c=>c.property==='snapshot').value.stamp);
console.log(JSON.stringify({pausedRequests:0,scopedWake:true,staleWakeRejected:true,originalTimestamp:true,resumedMinute:true}));
