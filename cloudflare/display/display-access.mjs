// Beta-only delegated reads. These are deliberately SELECT-only statements.
// No production relay code, token lifetimes, database schema or rows are changed.
const digest=async value=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(value))),v=>v.toString(16).padStart(2,'0')).join('');
export const DISPLAY_SECONDS=86400;
export async function delegateDisplay(db,access){
 const row=await db.prepare('SELECT h.id,h.write_hash FROM households h JOIN access_tokens a ON h.id=a.tenant WHERE a.hash=? AND a.expires>? AND h.disabled=0').bind(await digest(access),Math.floor(Date.now()/1000)).first();
 if(!row)throw Error('upstream_401');
 if(row.id.startsWith('review-'))throw Error('review_legacy');
 const now=Math.floor(Date.now()/1000);
 return {v:2,t:row.id,r:await digest(row.write_hash),i:now,e:now+DISPLAY_SECONDS};
}
export async function displayValues(db,grant){
 const row=await db.prepare('SELECT write_hash,timezone,live_at,live_json,history_at,history_json FROM households WHERE id=? AND disabled=0').bind(grant.t).first();
 if(!row||await digest(row.write_hash)!==grant.r)throw Error('display_revoked');
 if(!row.live_json)throw Error('upstream_404');
 if(row.live_json.length>8192||(row.history_json||'').length>8192)throw Error('too_large');
 const parts=new Intl.DateTimeFormat('en-CA',{timeZone:row.timezone,year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(new Date());
 const part=type=>parts.find(p=>p.type===type).value;
 return {...JSON.parse(row.live_json),received_at:row.live_at,
  local_date:`${part('year')}-${part('month')}-${part('day')}`,
  received_local:new Intl.DateTimeFormat('en-GB',{timeZone:row.timezone,hour:'2-digit',minute:'2-digit',hour12:false}).format(new Date(row.live_at)),
  history:row.history_json?{...JSON.parse(row.history_json),received_at:row.history_at}:null};
}
