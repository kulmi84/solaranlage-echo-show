// Contract check for generated APL expressions in their documented scopes.
// This is not an APL runtime or an Echo device test.
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const document=JSON.parse(readFileSync(process.argv[2],'utf8'));
const root=document.mainTemplate.items[0],tick=root.handleTick[0];
const state=Object.fromEntries(root.bind.map(x=>[x.name,structuredClone(x.value)]));
Object.assign(state,{displayState:'foreground',utcTime:Date.now(),elapsedTime:0});
const binding=tick.when.match(/FullscreenSnapshot\.binding == "([a-f0-9]+)"/)[1];
const evaluate=value=>typeof value==='string'&&value.startsWith('${')
 ? vm.runInNewContext(value.slice(2,-1),state,{timeout:100}) : structuredClone(value);
function run(snapshot) {
 state.FullscreenSnapshot=snapshot;
 if(!evaluate(tick.when))return false;
 for(const c of tick.commands){
  if(c.type!=='SetValue'||c.componentId!=='solarRoot')throw Error('Unexpected side effect');
  if(!c.when||evaluate(c.when))state[c.property]=evaluate(c.value);
 }
 return true;
}
const values=[];
for(let i=1;i<=3;i++){
 state.elapsedTime=i*60000;
 const sampleTime=state.fsSampleTime+60000;
 const next={binding,sampleTime,fullscreen:{schema:1,sampleTime,
  live:{...structuredClone(state.fsLive),live1v:`${600+i} W`},history:structuredClone(state.fsHistory)}};
 if(!run(next))throw Error('A valid live DataBinding update was ignored');
 values.push(state.fsLive.live1v);
}
const kept=JSON.stringify(state.fsLive),old=state.fsSampleTime-1;
const oldData={binding,sampleTime:old,fullscreen:{schema:1,sampleTime:old,live:state.fsLive,history:state.fsHistory}};
const rejectedOlderSample=!run(oldData)&&JSON.stringify(state.fsLive)===kept;
const rejectedOtherHouseholdBinding=!run({...oldData,binding:'d'.repeat(64),sampleTime:state.fsSampleTime,
 fullscreen:{...oldData.fullscreen,sampleTime:state.fsSampleTime}})&&JSON.stringify(state.fsLive)===kept;
const retainedAfterMissingData=!run(null)&&JSON.stringify(state.fsLive)===kept;
console.log(JSON.stringify({successiveHomeValues:values,rejectedOlderSample,
 rejectedOtherHouseholdBinding,retainedAfterMissingData}));
