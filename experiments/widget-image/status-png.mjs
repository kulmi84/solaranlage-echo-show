import {statusFont} from './status-font.mjs';

export function statusText(row,now=Date.now()){
 const stamp=Date.parse(row.live_at);if(!Number.isFinite(stamp))throw Error('timestamp');
 const parts=new Intl.DateTimeFormat('de-DE',{timeZone:row.timezone||'UTC',day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(stamp));
 const p=type=>parts.find(part=>part.type===type).value;
 const stale=now-stamp>180000||stamp-now>60000;
 return {text:(stale?'Veraltet: ':'Stand: ')+`${p('day')}.${p('month')}.${p('year')}, ${p('hour')}:${p('minute')}`+(row.timezone?'':' UTC'),stale};
}
export async function statusPng(row){
 const {text,stale}=statusText(row),width=789,height=84;
 const raw=new Uint8Array((width*4+1)*height),color=stale?[255,110,110]:[255,209,102];let pen=0;
 // Native-resolution antialiasing: never squash glyph coordinates or overwrite
 // multiple source pixels into one destination pixel, which damaged the edges.
 for(const c of text){const [w,h,advance,encoded]=statusFont[c];const mask=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));
  for(let y=0;y<h;y++)for(let x=0;x<w&&pen+x<width;x++){const alpha=mask[y*w+x];if(!alpha)continue;const at=y*(width*4+1)+1+(pen+x)*4;raw.set(color,at);raw[at+3]=Math.max(raw[at+3],alpha);}pen+=advance;}
 const head=new Uint8Array(13),view=new DataView(head.buffer);view.setUint32(0,width);view.setUint32(4,height);head[8]=8;head[9]=6;
 const compressed=new Uint8Array(await new Response(new Blob([raw]).stream().pipeThrough(new CompressionStream('deflate'))).arrayBuffer());
 return join([new Uint8Array([137,80,78,71,13,10,26,10]),chunk('IHDR',head),chunk('IDAT',compressed),chunk('IEND',new Uint8Array())]);
}
const crcTable=Uint32Array.from({length:256},(_,n)=>{let c=n;for(let i=0;i<8;i++)c=c&1?0xedb88320^(c>>>1):c>>>1;return c>>>0;});
function chunk(type,data){const out=new Uint8Array(data.length+12),view=new DataView(out.buffer);view.setUint32(0,data.length);out.set(new TextEncoder().encode(type),4);out.set(data,8);let crc=0xffffffff;for(let i=4;i<out.length-4;i++)crc=crcTable[(crc^out[i])&255]^(crc>>>8);view.setUint32(out.length-4,(crc^0xffffffff)>>>0);return out;}
function join(parts){const out=new Uint8Array(parts.reduce((n,p)=>n+p.length,0));let at=0;for(const p of parts){out.set(p,at);at+=p.length;}return out;}
