// Isolated beta. Clock is public; dashboards require expiring encrypted read grants.
import {sessionRoute} from './sessions.mjs';
const digits = {
  '0':['111','101','101','101','111'], '1':['010','110','010','010','111'],
  '2':['111','001','111','100','111'], '3':['111','001','111','001','111'],
  '4':['101','101','111','001','001'], '5':['111','100','111','001','111'],
  '6':['111','100','111','101','111'], '7':['111','001','010','010','010'],
  '8':['111','101','111','101','111'], '9':['111','101','111','001','111'],
  ':':['000','010','000','010','000'], ' ':['000','000','000','000','000']
};
const crcTable = Uint32Array.from({length:256},(_,n)=>{
  let c=n; for(let k=0;k<8;k++) c=(c&1)?0xedb88320^(c>>>1):c>>>1; return c>>>0;
});
function chunk(type,data) {
  const out=new Uint8Array(data.length+12), view=new DataView(out.buffer);
  view.setUint32(0,data.length); out.set(new TextEncoder().encode(type),4);out.set(data,8);
  let crc=0xffffffff;for(let i=4;i<out.length-4;i++) crc=crcTable[(crc^out[i])&255]^(crc>>>8);
  view.setUint32(out.length-4,(crc^0xffffffff)>>>0); return out;
}
export async function clockPng(date=new Date()) {
  const width=854,height=160,scale=24,raw=new Uint8Array((width+1)*height);
  const text=date.toISOString().slice(11,19), x0=Math.floor((width-text.length*4*scale+scale)/2),y0=20;
  for(let i=0;i<text.length;i++) for(let y=0;y<5;y++) for(let x=0;x<3;x++) {
    if(digits[text[i]][y][x]!=='1') continue;
    for(let dy=0;dy<scale;dy++) for(let dx=0;dx<scale;dx++) {
      const xx=x0+(i*4+x)*scale+dx, yy=y0+y*scale+dy;
      if(xx>=0 && xx<width && yy<height) raw[yy*(width+1)+1+xx]=1;
    }
  }
  const header=new Uint8Array(13),dv=new DataView(header.buffer);
  dv.setUint32(0,width);dv.setUint32(4,height);header[8]=8;header[9]=3;
  const compressed=new Uint8Array(await new Response(new Blob([raw]).stream().pipeThrough(new CompressionStream('deflate'))).arrayBuffer());
  const pieces=[new Uint8Array([137,80,78,71,13,10,26,10]),chunk('IHDR',header),
    chunk('PLTE',new Uint8Array([12,21,31,255,209,102])),chunk('IDAT',compressed),chunk('IEND',new Uint8Array())];
  const out=new Uint8Array(pieces.reduce((n,p)=>n+p.length,0));let offset=0;
  for(const p of pieces){out.set(p,offset);offset+=p.length;} return out;
}
export default {
  async fetch(request,env={}) {
    const routed=await sessionRoute(request,env);
    if(routed)return routed;
    const url=new URL(request.url);
    if(url.pathname!=='/clock.png' || !['GET','HEAD'].includes(request.method)) return new Response('Not found',{status:404});
    const headers={'Content-Type':'image/png','Cache-Control':'no-store, max-age=0',
      'X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'};
    return new Response(request.method==='HEAD'?null:await clockPng(),{headers});
  }
};
