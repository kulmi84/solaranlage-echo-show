import {readFileSync} from 'node:fs';
import vm from 'node:vm';
const doc=JSON.parse(readFileSync(process.argv[2],'utf8')),root=doc.mainTemplate.items[0];
const state=Object.fromEntries(root.bind.map(b=>[b.name,structuredClone(b.value)]));
Object.assign(state,{displayState:'foreground',utcTime:Date.now(),elapsedTime:0,FullscreenSnapshot:null});
const initial=JSON.stringify(state.fsLive),sent=[];
const evaluate=v=>typeof v==='string'&&v.startsWith('${')?vm.runInNewContext(v.slice(2,-1),state):structuredClone(v);
function run(){for(const tick of root.handleTick){if(tick.when&&!evaluate(tick.when))continue;for(const c of tick.commands){if(c.when&&!evaluate(c.when))continue;if(c.type==='SetValue')state[c.property]=evaluate(c.value);else if(c.type==='SendEvent')sent.push(c.arguments.map(evaluate));else throw Error('Unexpected command');}}}
for(let i=1;i<=3;i++){state.elapsedTime=i*60000;run();run();}
const threeRounds=sent.length===3,kept=JSON.stringify(state.fsLive)===initial;
state.displayState='hidden';state.elapsedTime=240000;run();const noHiddenRequest=sent.length===3;
state.displayState='foreground';state.fsWakeNetworkPending=true;run();run();const wakeOnce=sent.length===4;
const tick=root.handleTick[0],binding=tick.when.match(/FullscreenSnapshot\.binding == "([a-f0-9]+)"/)[1];
state.elapsedTime=300000;const sampleTime=state.fsSampleTime+60000;
state.FullscreenSnapshot={binding,sampleTime,fullscreen:{schema:1,sampleTime,live:{...state.fsLive,live1v:'999 W'},history:state.fsHistory}};
run();const noDuplicateAfterPush=sent.length===4&&state.fsLive.live1v==='999 W';
state.FullscreenSnapshot=null;state.currentPage=1;state.fsNextNetworkAt=state.elapsedTime+21600000;
state.elapsedTime+=60000;run();const historyNotEveryMinute=sent.length===4;
state.elapsedTime=state.fsNextNetworkAt;run();const historyDue=sent.length===5&&sent.at(-1)[2]===1;
const result={threeRounds,kept,noHiddenRequest,wakeOnce,noDuplicateAfterPush,historyNotEveryMinute,historyDue};
if(!Object.values(result).every(Boolean))throw Error(JSON.stringify(result));
console.log(JSON.stringify(result));
