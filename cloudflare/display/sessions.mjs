import {dashboardPng,housePng,finalTilePng} from './dashboard.mjs';
import {delegateDisplay,displayValues,DISPLAY_SECONDS} from './display-access.mjs';
const relay='https://solaranlage-public-beta.kulmi84.workers.dev/v1/pv';
const aad=new TextEncoder().encode('solaranlage-image-test-v1');
const base64=b=>btoa(String.fromCharCode(...b)).replaceAll('+','-').replaceAll('/','_').replaceAll('=','');
function unbase64(s){if(!/^[\w-]+$/.test(s)||s.length>2048)throw Error('invalid');return Uint8Array.from(atob(s.replaceAll('-','+').replaceAll('_','/')),x=>x.charCodeAt(0));}
async function key(secret){if(!/^[a-f0-9]{64}$/.test(secret||''))throw Error('configuration');return crypto.subtle.importKey('raw',Uint8Array.from(secret.match(/../g),x=>parseInt(x,16)),'AES-GCM',false,['encrypt','decrypt']);}
export async function seal(access,secret,now=Date.now()){
 if(!/^[a-f0-9]{64}$/.test(access||''))throw Error('invalid');
 return sealPayload({a:access,e:Math.floor(now/1000)+3600},secret);
}
export async function sealPayload(payload,secret){
 const iv=crypto.getRandomValues(new Uint8Array(12)),plain=new TextEncoder().encode(JSON.stringify(payload));
 const cipher=new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv,additionalData:aad},await key(secret),plain));
 const all=new Uint8Array(iv.length+cipher.length);all.set(iv);all.set(cipher,12);return base64(all);
}
export async function open(token,secret,now=Date.now(),diagnostic=null){
 const bytes=unbase64(token),plain=await crypto.subtle.decrypt({name:'AES-GCM',iv:bytes.slice(0,12),additionalData:aad},await key(secret),bytes.slice(12));
 const value=JSON.parse(new TextDecoder().decode(plain)),seconds=Math.floor(now/1000);
 if(value.v===2){
  if(typeof value.t!=='string'||value.t.length>128||!value.t||!/^[a-f0-9]{64}$/.test(value.r||'')||!Number.isSafeInteger(value.i)||!Number.isSafeInteger(value.e)||value.i>seconds||value.e-value.i!==DISPLAY_SECONDS)throw Error('invalid');
  if(diagnostic){diagnostic.grant_age_s=seconds-value.i;diagnostic.grant_remaining_s=value.e-seconds;diagnostic.delegated=true;}
  if(value.e<=seconds)throw Error('expired');return value;
 }
 if(!/^[a-f0-9]{64}$/.test(value.a||'')||!Number.isSafeInteger(value.e)||value.e>seconds+3600)throw Error('invalid');
 if(diagnostic){diagnostic.grant_age_s=seconds-(value.e-3600);diagnostic.grant_remaining_s=value.e-seconds;}
 if(value.e<=seconds)throw Error('expired');return value.a;
}
async function equals(a,b){if(!a||!b)return false;const digest=async s=>new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(s)));const [x,y]=await Promise.all([digest(a),digest(b)]);let n=0;for(let i=0;i<x.length;i++)n|=x[i]^y[i];return n===0;}
async function boundedText(stream,limit){if(!stream)throw Error('invalid');const reader=stream.getReader(),decoder=new TextDecoder();let size=0,out='';while(true){const {done,value}=await reader.read();if(done)break;size+=value.byteLength;if(size>limit){await reader.cancel();throw Error('too_large');}out+=decoder.decode(value,{stream:true});}return out+decoder.decode();}
export async function getValues(access,upstream=fetch){
 const r=await upstream(relay,{headers:{Authorization:'Bearer '+access,Accept:'application/json'},redirect:'manual',signal:AbortSignal.timeout(5000)});
 if(!r.ok)throw Error('upstream_'+r.status);const raw=await boundedText(r.body,8192);const d=JSON.parse(raw);if(!d||typeof d!=='object'||Array.isArray(d))throw Error('upstream');return d;
}
async function routeImpl(request,env,upstream,diagnostic){
 const u=new URL(request.url),h={'Cache-Control':'no-store, max-age=0','X-Content-Type-Options':'nosniff','Referrer-Policy':'no-referrer'};
 if(u.pathname==='/image/session'){
  if(request.method!=='POST')return new Response('Not found',{status:404,headers:h});
  if(!(await equals(request.headers.get('Authorization'),'Bearer '+env.SESSION_KEY)))return new Response('Unauthorized',{status:401,headers:h});
  if(!env.SESSION_KEY||!env.DISPLAY_KEY)return new Response('Unavailable',{status:503,headers:h});
  try{
   if(!request.headers.get('Content-Type')?.startsWith('application/json'))throw Error('invalid');
   if(Number(request.headers.get('Content-Length'))>1024)throw Error('invalid');
   const raw=await boundedText(request.body,1024);const input=JSON.parse(raw);
   if(!/^[a-f0-9]{64}$/.test(input.access_token||''))throw Error('invalid');
   const values=await getValues(input.access_token,upstream);
   let payload=null;
   if(env.DISPLAY_DB){try{payload=await delegateDisplay(env.DISPLAY_DB,input.access_token);}catch(error){if(error.message!=='review_legacy')throw error;}}
   const token=payload?await sealPayload(payload,env.DISPLAY_KEY):await seal(input.access_token,env.DISPLAY_KEY);
   diagnostic.delegated=Boolean(payload);
   return Response.json({base_url:u.origin+'/dashboard.png?s='+token,expires_in:payload?DISPLAY_SECONDS:3600,local_date:/^\d{4}-\d\d-\d\d$/.test(values.local_date||'')?values.local_date:null},{headers:h});
  }catch(error){const detail=safeReason(error);diagnostic.reason=detail;return Response.json({error:'session_unavailable',detail},{status:400,headers:h});}
 }
 if(u.pathname==='/dashboard.png'||u.pathname==='/house.png'||u.pathname==='/tile.png'||u.pathname==='/status.png'){
  if(request.method!=='GET')return new Response('Not found',{status:404,headers:h});
  let access;try{access=await open(u.searchParams.get('s')||'',env.DISPLAY_KEY,Date.now(),diagnostic);}catch(error){diagnostic.reason=error.message==='expired'?'grant_expired':'grant_invalid';return new Response('Forbidden',{status:403,headers:h});}
  const page=u.searchParams.get('page')||'live';if(!['live','history'].includes(page))return new Response('Not found',{status:404,headers:h});
  let tile=null;if(u.pathname==='/tile.png'){const row=u.searchParams.get('row'),col=u.searchParams.get('col');if(!/^[01]$/.test(row||'')||!/^[0-3]$/.test(col||''))return new Response('Not found',{status:404,headers:h});tile={row:Number(row),col:Number(col)};}
  try{const values=typeof access==='object'?await displayValues(env.DISPLAY_DB,access):await getValues(access,upstream);const png=u.pathname==='/status.png'?finalTilePng(values,page,null):u.pathname==='/tile.png'&&u.searchParams.get('layout')==='final'?finalTilePng(values,page,tile):u.pathname==='/house.png'?housePng(values):dashboardPng(values,page,Date.now(),tile);return new Response(await png,{headers:{...h,'Content-Type':'image/png'}});}catch(error){diagnostic.reason=safeReason(error);return new Response('Image unavailable - reopen test skill',{status:503,headers:h});}
 }
 return null;
}

function safeReason(error){
 const message=error?.message||'';
 if(/^(upstream_[0-9]{3}|too_large|configuration|invalid|display_revoked)$/.test(message))return message;
 if(error?.name==='TimeoutError'||error?.name==='AbortError')return 'upstream_timeout';
 return 'internal';
}

// Observability persistence stays disabled: platform invocation metadata can include
// confidential query strings. A local tail collector retains only this allowlist.
export async function sessionRoute(request,env,upstream=fetch){
 const u=new URL(request.url),routes={'/image/session':'session','/tile.png':'tile','/status.png':'status','/house.png':'house','/dashboard.png':'dashboard'};
 const route=routes[u.pathname];if(!route)return null;
 const started=Date.now(),diagnostic={event:'DISPLAY_IMAGE_DIAG',at:new Date().toISOString(),route};
 const n=u.searchParams.get('n');if(/^\d{1,12}$/.test(n||''))diagnostic.tick_ms=Number(n);
 if(n==='initial')diagnostic.initial=true;
 const page=u.searchParams.get('page');if(['live','history'].includes(page))diagnostic.page=page;
 if(/^[01]$/.test(u.searchParams.get('row')||''))diagnostic.row=Number(u.searchParams.get('row'));
 if(/^[0-3]$/.test(u.searchParams.get('col')||''))diagnostic.col=Number(u.searchParams.get('col'));
 let response;
 try{response=await routeImpl(request,env,upstream,diagnostic);}
 catch{diagnostic.reason='internal';response=new Response('Image unavailable',{status:503,headers:{'Cache-Control':'no-store'}});}
 diagnostic.status=response.status;diagnostic.duration_ms=Date.now()-started;
 diagnostic.reason ||= response.ok?'ok':response.status===401?'session_unauthorized':response.status===404?'not_found':'rejected';
 console.log(JSON.stringify(diagnostic));return response;
}
