// Raster dashboard for the isolated beta; all numerical inputs are bounded.
import {smoothFont} from './smooth-font.mjs';
const basePalette=new Uint8Array([12,21,31,244,246,250,143,168,188,23,35,48,255,209,102,139,203,255,195,160,255,81,211,197,255,110,110]);
const colors=Array.from(basePalette),blend={};
for(let bg of [0,3])for(let fg=0;fg<9;fg++)for(let level=1;level<=7;level++){
 const index=colors.length/3;blend[bg+','+fg+','+level]=index;
 for(let channel=0;channel<3;channel++)colors.push(Math.round(basePalette[bg*3+channel]+(basePalette[fg*3+channel]-basePalette[bg*3+channel])*level/7));
}
const palette=new Uint8Array(colors),glyphCache=new Map();
function glyph(scale,char){const key=scale+char;if(!glyphCache.has(key)){const g=smoothFont[scale][char]||smoothFont[scale]['-'];glyphCache.set(key,[...g.slice(0,3),Uint8Array.from(atob(g[3]),c=>c.charCodeAt(0))]);}return glyphCache.get(key);}
const crcTable=Uint32Array.from({length:256},(_,n)=>{let c=n;for(let i=0;i<8;i++)c=(c&1)?0xedb88320^(c>>>1):c>>>1;return c>>>0;});
function chunk(type,data){const b=new Uint8Array(data.length+12),v=new DataView(b.buffer);v.setUint32(0,data.length);b.set(new TextEncoder().encode(type),4);b.set(data,8);let c=0xffffffff;for(let i=4;i<b.length-4;i++)c=crcTable[(c^b[i])&255]^(c>>>8);v.setUint32(b.length-4,(c^0xffffffff)>>>0);return b;}
export async function encodePng(width,height,pixels){
 const raw=new Uint8Array((width+1)*height);for(let y=0;y<height;y++)raw.set(pixels.subarray(y*width,(y+1)*width),y*(width+1)+1);
 const head=new Uint8Array(13),view=new DataView(head.buffer);view.setUint32(0,width);view.setUint32(4,height);head[8]=8;head[9]=3;
 const zipped=new Uint8Array(await new Response(new Blob([raw]).stream().pipeThrough(new CompressionStream('deflate'))).arrayBuffer());
 const pieces=[new Uint8Array([137,80,78,71,13,10,26,10]),chunk('IHDR',head),chunk('PLTE',palette),chunk('IDAT',zipped),chunk('IEND',new Uint8Array())];
 const out=new Uint8Array(pieces.reduce((n,p)=>n+p.length,0));let i=0;for(const p of pieces){out.set(p,i);i+=p.length;}return out;
}
export function cleanValues(data,now=Date.now()){
 const value=k=>typeof data[k]==='number'&&Number.isFinite(data[k])&&data[k]>=0&&data[k]<=(k==='battery_soc'?100:1e7)?data[k]:null;
 const live={};for(const k of ['power_w','pv_dc_w','bkw_w','home_w','grid_import_w','grid_export_w','battery_soc','battery_charge_w','battery_discharge_w'])live[k]=value(k);
 const day={};for(const k of ['pv','home','grid_import','grid_export','battery_charge','battery_discharge'])day[k]=data.energy_date&&data.energy_date===data.local_date?value('today_'+k+'_kwh'):null;
 const history={};for(const period of ['month','year'])for(const k of ['pv','home','grid_import','grid_export','battery_charge','battery_discharge']){
  const h=data.history,raw=h?.[period+'_'+k+'_kwh'],expected=String(data.local_date||'').slice(0,period==='month'?7:4);
  history[period+'_'+k]=expected&&h?.[period+'_id']===expected&&typeof raw==='number'&&Number.isFinite(raw)&&raw>=0&&raw<=1e7?raw:null;
 }
 const stamp=Date.parse(data.received_at),age=(now-stamp)/1000;
 return {live,day,history,stale:!Number.isFinite(age)||age>180||age< -60,received:/^\d\d:\d\d$/.test(data.received_local||'')?data.received_local:'--:--',date:/^\d{4}-\d\d-\d\d$/.test(data.local_date||'')?data.local_date:'---- -- --'};
}
const num=(v,d=2)=>v===null?'-':v.toFixed(d).replace('.',',');
const power=v=>v===null?'-':v>=1000?num(v/1000)+' kW':num(v,0)+' W';
const energy=v=>num(v)+' kWh';
export async function finalTilePng(data,page,tile,now=Date.now()){
 const v=cleanValues(data,now),footer=tile===null,width=footer?1150:263,height=footer?34:154;
 const bg=footer?0:3,pixels=new Uint8Array(width*height);pixels.fill(bg);
 function line(str,y,size,color){let pen=0;for(const ch of String(str)){const [w,h,advance,mask]=glyph(size,ch);for(let yy=0;yy<h;yy++)for(let xx=0;xx<w;xx++){const a=mask[yy*w+xx],px=pen+xx,py=y+yy;if(a&&px>=0&&px<width&&py>=0&&py<height)pixels[py*width+px]=blend[bg+','+color+','+a];}pen+=advance;}}
 if(footer){line((v.stale?'Veraltete Daten - Stand ':'Stand ')+v.received+' Uhr - Auto alle 60 s',0,8,v.stale?8:2);return encodePng(width,height,pixels);}
 const colors=[4,5,6,7];let main,details;
 if(page==='live'&&tile.row===0){const l=v.live;main=[power(l.power_w),power(l.home_w),power(l.grid_export_w),num(l.battery_soc,0)+' %'][tile.col];details=[['PV '+power(l.pv_dc_w),'BKW '+power(l.bkw_w)],['Verbrauch jetzt'],['Einspeisung','Bezug '+power(l.grid_import_w)],['Laden '+power(l.battery_charge_w),'Entladen '+power(l.battery_discharge_w)]][tile.col];}
 else{const h=page==='live'?v.day:v.history,prefix=page==='live'?'':(tile.row===0?'month_':'year_');
  const n=k=>h[prefix+k]===null?'-':(page==='live'?energy(h[prefix+k]):new Intl.NumberFormat('de-DE',{minimumFractionDigits:2,maximumFractionDigits:2}).format(h[prefix+k]));
  main=[n('pv'),n('home'),n('grid_export'),n('battery_charge')][tile.col];
  const unit=page==='history'?'kWh - ':'';
  details=[[unit+'Erzeugung'],[unit+'Verbrauch'],[unit+'Einspeisung','Bezug '+n('grid_import')+(page==='history'?' kWh':'')],[unit+'Geladen','Entladen '+n('battery_discharge')+(page==='history'?' kWh':'')]][tile.col];
 }
 line(main,0,page==='history'?7:6,colors[tile.col]);details.forEach((s,i)=>line(s,65+i*29,8,1));
 return encodePng(width,height,pixels);
}
export async function housePng(data,now=Date.now()){
 const width=480,height=130,pixels=new Uint8Array(width*height);pixels.fill(3);
 const v=cleanValues(data,now);
 function line(str,x,y,scale,color){let pen=x;for(const ch of str){const [w,h,advance,mask]=glyph(scale,ch);for(let yy=0;yy<h;yy++)for(let xx=0;xx<w;xx++){const a=mask[yy*w+xx],px=pen+xx,py=y+yy;if(a&&px>=0&&px<width&&py>=0&&py<height)pixels[py*width+px]=blend['3,'+color+','+a];}pen+=advance;}}
 line(v.stale?'-':power(v.live.home_w),16,8,5,5);
 line(v.stale?'Daten veraltet':'Stand '+v.received,16,85,2,v.stale?8:2);
 return encodePng(width,height,pixels);
}
export async function dashboardPng(data,page='live',now=Date.now(),tile=null){
 const width=1280,height=800,pixels=new Uint8Array(width*height),v=cleanValues(data,now);
 function rect(x,y,w,h,c){for(let yy=Math.max(0,y);yy<Math.min(height,y+h);yy++)pixels.fill(c,yy*width+Math.max(0,x),yy*width+Math.min(width,x+w));}
 function text(str,x,y,scale=3,c=1){
  str=String(str);let total=0;for(const ch of str)total+=glyph(scale,ch)[2];
  const factor=Math.min(1,(x>=950?width-x-20:((x-39)%311===0?274:width-x-24))/Math.max(total,1));
  let pen=x;for(const ch of str){const [w,h,advance,mask]=glyph(scale,ch);
   for(let yy=0;yy<h;yy++)for(let xx=0;xx<w;xx++){const level=mask[yy*w+xx];if(!level)continue;const px=Math.round(pen+xx*factor),py=y+yy;if(px<0||px>=width||py<0||py>=height)continue;const at=py*width+px,bg=pixels[at]===3?3:0;pixels[at]=blend[bg+','+c+','+level];}
   pen+=advance*factor;
  }
 }
 function card(i,y,label,main,details,c){const x=24+i*311;rect(x,y,299,235,3);text(label,x+15,y+17,3,2);text(main,x+15,y+66,main.length>9?4:5,c);for(let j=0;j<details.length;j++)text(details[j],x+15,y+125+j*32,2,2);}
 text('Solaranlage Test',24,19,5);text('Live-Bildbeta',950,32,2,2);
 const colors=[4,5,6,7],labels=['PV + BKW','Haus','Netz','Akku'];
 if(page==='live'){
  text('LIVE',24,86,3,2);const l=v.live;
  const mains=[power(l.power_w),power(l.home_w),power(l.grid_export_w),num(l.battery_soc,0)+' %'];
  const details=[['PV '+power(l.pv_dc_w),'BKW '+power(l.bkw_w)],['Verbrauch jetzt'],['Einspeisung','Bezug '+power(l.grid_import_w)],['Laden '+power(l.battery_charge_w),'Entladen '+power(l.battery_discharge_w)]];
  labels.forEach((label,i)=>card(i,125,label,mains[i],details[i],colors[i]));
  text('HEUTE - seit Mitternacht',24,402,3,2);const d=v.day;
  const daily=[energy(d.pv),energy(d.home),energy(d.grid_export),energy(d.battery_charge)];
  const dd=[['Erzeugung'],['Verbrauch'],['Einspeisung','Bezug '+energy(d.grid_import)],['Geladen','Entladen '+energy(d.battery_discharge)]];
  labels.forEach((label,i)=>card(i,442,label,daily[i],dd[i],colors[i]));
 }else{
  for(const [row,period]of ['month','year'].entries()){
   const y=row===0?125:442;text((period==='month'?'MONAT ':'JAHR ')+v.date.slice(0,period==='month'?7:4),24,y-39,3,2);
   const h=v.history,mains=[h[period+'_pv'],h[period+'_home'],h[period+'_grid_export'],h[period+'_battery_charge']].map(energy);
   const details=[['Erzeugung'],['Verbrauch'],['Einspeisung','Bezug '+energy(h[period+'_grid_import'])],['Geladen','Entladen '+energy(h[period+'_battery_discharge'])]];
   labels.forEach((label,i)=>card(i,y,label,mains[i],details[i],colors[i]));
  }
 }
 text((v.stale?'Veraltete Daten - ':'Stand ')+v.received+' - automatisch alle 60 s',24,725,3,v.stale?8:2);
 text('Bildbeta - Zugriff zeitlich begrenzt',24,770,2,2);
 if(tile){
  text(v.stale?'Veraltete Daten':'Stand '+v.received,39+tile.col*311,(tile.row===0?125:442)+202,2,v.stale?8:2);
  const x=24+tile.col*311+10,y=(tile.row===0?125:442)+56,w=279,h=170;
  const crop=new Uint8Array(w*h);for(let yy=0;yy<h;yy++)crop.set(pixels.subarray((y+yy)*width+x,(y+yy)*width+x+w),yy*w);
  return encodePng(w,h,crop);
 }
 return encodePng(width,height,pixels);
}

