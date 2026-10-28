// Widget views use the same delegated account grant as the unchanged fullscreen.
import {open,getValues} from './sessions.mjs';
import {finalTilePng} from './dashboard.mjs';
import {transparentValuePng} from '../../experiments/widget-image/transparent-png.mjs';
import {statusPng} from '../../experiments/widget-image/status-png.mjs';

const headers={'Cache-Control':'no-store, max-age=0','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff'};
const sha=async value=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value))),n=>n.toString(16).padStart(2,'0')).join('');
export async function widgetImageRoute(request,env,upstream=fetch){
 const url=new URL(request.url),status=url.pathname==='/widget/status.png';
 if(!status&&url.pathname!=='/widget/value.png')return null;
 if(request.method!=='GET')return new Response('Not found',{status:404,headers});
 const col=url.searchParams.get('col');
 if(!status&&!['0','1','3'].includes(col))return new Response('Forbidden',{status:403,headers});
 let grant;try{grant=await open(url.searchParams.get('s')||'',env.DISPLAY_KEY);}catch{return new Response('Forbidden',{status:403,headers});}
 try{
  let row;
  if(typeof grant==='object'){
   // Exactly the authenticated grant's tenant, never a device/IP/latest-row guess.
   row=await env.DISPLAY_DB.prepare(`SELECT write_hash,live_at,timezone,
    json_extract(live_json,'$.power_w') AS power_w,
    json_extract(live_json,'$.home_w') AS home_w,
    json_extract(live_json,'$.battery_soc') AS battery_soc
    FROM households WHERE id=? AND disabled=0`).bind(grant.t).first();
   if(!row||await sha(row.write_hash)!==grant.r)return new Response('Forbidden',{status:403,headers});
  }else{
   // Existing legacy/reviewer grant: use the same authenticated relay as fullscreen.
   const values=await getValues(grant,upstream);
   row={...values,live_at:values.received_at,timezone:values.timezone||'UTC'};
  }
  if(!row.live_at)return new Response('No values',{status:503,headers});
  const png=status?await statusPng(row):await transparentValuePng(await finalTilePng({power_w:row.power_w,home_w:row.home_w,battery_soc:row.battery_soc,received_at:row.live_at},'live',{row:0,col:Number(col)}));
  return new Response(png,{headers:{...headers,'Content-Type':'image/png'}});
 }catch{return new Response('Image unavailable',{status:503,headers});}
}
