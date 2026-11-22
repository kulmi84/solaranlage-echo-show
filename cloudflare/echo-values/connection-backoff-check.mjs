// Executes the generated expression/command contract, not an Echo/APL runtime.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
const doc=JSON.parse(readFileSync(process.argv[2],'utf8'));
const root=doc.mainTemplate.items[0];
function run(withFailureReply){
 const state={Math,viewport:{width:310,height:440},elapsedTime:0,utcTime:1795340000000,displayState:'foreground',
  SolarLive:null,displaySnapshot:{sampleTime:0,stamp:''},layoutScale:1};
 const context=vm.createContext(state);
 const evaluate=v=>typeof v==='string'&&v.startsWith('${')?
  vm.runInContext(v.slice(2,-1),context,{timeout:1000}):v;
 for(const b of root.bind) if(b.name!=='displaySnapshot')state[b.name]=evaluate(b.value);
 const sent=[];
 function commands(items){for(const c of items){
  if(c.when&&!evaluate(c.when))continue;
  if(c.type==='SetValue')state[c.property]=evaluate(c.value);
  if(c.type==='SendEvent'){
   sent.push(state.elapsedTime);
   // Deliberately no snapshot, household or grant changes on an error.
   if(withFailureReply){state.requestPending=false;state.connectionStatus='Verbindung prüfen: Alexa-App';}
  }
 }}
 commands(root.onMount);
 for(let t=1000;t<=1800000;t+=1000){
  state.elapsedTime=t;state.utcTime=1795340000000+t;
  if(t%10000===0)state.wakePending=true;
  for(const tick of root.handleTick)if(evaluate(tick.when))commands(tick.commands);
 }
 assert.deepEqual(sent,[0,60000,180000,420000,900000,1800000]);
 // A newly received valid snapshot resumes 60 seconds, with no network event.
 state.displaySnapshot={sampleTime:1795341800000,stamp:'Originalzeit'};
 const before=sent.length;
 const recovery=root.handleTick.find(t=>t.when.includes('lastGoodSampleTime'));
 assert(evaluate(recovery.when));commands(recovery.commands);
 assert.equal(sent.length,before);assert.equal(state.retryDelayMs,60000);
 assert.equal(state.nextRefreshAt,state.elapsedTime+60000);
 assert.equal(state.connectionStatus,'');
 return sent;
}
console.log(JSON.stringify({missingReplies:run(false),explicitFailures:run(true),
 revealDidNotBypassBackoff:true,datastoreRecoveryReset:true}));
