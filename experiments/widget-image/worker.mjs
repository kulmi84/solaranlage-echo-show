import {finalTilePng} from '../../cloudflare/display/dashboard.mjs';
import {transparentValuePng} from './transparent-png.mjs';

const headers={'Cache-Control':'no-store, max-age=0','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'};
export const sha=async s=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s))),n=>n.toString(16).padStart(2,'0')).join('');
export function equal(a,b){if(typeof a!=='string'||typeof b!=='string'||a.length!==64||b.length!==64)return false;let diff=0;for(let i=0;i<64;i++)diff|=a.charCodeAt(i)^b.charCodeAt(i);return diff===0;}
export async function widgetImage(request,env){
 const url=new URL(request.url);
 if(request.method!=='GET'||url.pathname!=='/value.png')return new Response('Not found',{status:404,headers});
 const token=url.searchParams.get('k')||'',col=url.searchParams.get('col');
 if(!/^[a-f0-9]{64}$/.test(token)||!['0','1','3'].includes(col))return new Response('Forbidden',{status:403,headers});
 let grant;try{grant=JSON.parse(env.WIDGET_READ_GRANT||'');}catch{return new Response('Unavailable',{status:503,headers});}
 if(!equal(await sha(token),grant.tokenHash))return new Response('Forbidden',{status:403,headers});
 if(typeof grant.tenant!=='string'||grant.tenant.length>128||!grant.tenant||!/^[a-f0-9]{64}$/.test(grant.version||''))return new Response('Unavailable',{status:503,headers});
 try{
  // No token, OAuth, registration, history or sensor writes; only this one household.
  const row=await env.SOURCE_DB.prepare(`SELECT write_hash, live_at,
   json_extract(live_json,'$.power_w') AS power_w,
   json_extract(live_json,'$.home_w') AS home_w,
   json_extract(live_json,'$.battery_soc') AS battery_soc
   FROM households WHERE id=? AND disabled=0`).bind(grant.tenant).first();
  if(!row||!equal(await sha(row.write_hash),grant.version))return new Response('Forbidden',{status:403,headers});
  if(!row.live_at)return new Response('No values',{status:503,headers});
  const png=await transparentValuePng(await finalTilePng({power_w:row.power_w,home_w:row.home_w,battery_soc:row.battery_soc,received_at:row.live_at},'live',{row:0,col:Number(col)}));
  return new Response(png,{headers:{...headers,'Content-Type':'image/png'}});
 }catch{return new Response('Unavailable',{status:503,headers});}
}
export default {fetch:widgetImage};
