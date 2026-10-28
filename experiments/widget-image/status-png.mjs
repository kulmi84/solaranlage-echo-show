import {encodePng} from '../../cloudflare/display/dashboard.mjs';
import {smoothFont} from '../../cloudflare/display/smooth-font.mjs';
import {transparentValuePng} from './transparent-png.mjs';

export function statusText(row,now=Date.now()){
 const stamp=Date.parse(row.live_at);if(!Number.isFinite(stamp))throw Error('timestamp');
 const parts=new Intl.DateTimeFormat('de-DE',{timeZone:row.timezone||'UTC',day:'2-digit',month:'2-digit',year:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).formatToParts(new Date(stamp));
 const p=type=>parts.find(part=>part.type===type).value;
 const stale=now-stamp>180000||stamp-now>60000;
 return {text:(stale?'Veraltet: ':'Stand: ')+`${p('day')}.${p('month')}.${p('year')}, ${p('hour')}:${p('minute')}`+(row.timezone?'':' UTC'),stale};
}
export async function statusPng(row){
 const {text,stale}=statusText(row),width=263,height=154,pixels=new Uint8Array(width*height);pixels.fill(3);
 const glyphs=[...text].map(c=>smoothFont[2][c]||smoothFont[2]['-']);
 const glyphScale=0.78;
 const total=glyphs.reduce((n,g)=>n+g[2],0),factor=Math.min(glyphScale,width/total);let pen=0;
 for(const [w,h,advance,encoded] of glyphs){const mask=Uint8Array.from(atob(encoded),c=>c.charCodeAt(0));for(let y=0;y<h&&y<22;y++)for(let x=0;x<w;x++){const a=mask[y*w+x],xx=Math.floor((pen+x)*factor),yy=Math.floor(y*glyphScale)+2;if(a&&xx<width&&yy<22)pixels[yy*width+xx]=9+63+(stale?8:2)*7+a-1;}pen+=advance;}
 return transparentValuePng(await encodePng(width,height,pixels),22);
}
