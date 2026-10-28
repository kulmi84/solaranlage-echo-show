const SIGNATURE=new Uint8Array([137,80,78,71,13,10,26,10]);
const BASE=[12,21,31,244,246,250,143,168,188,23,35,48,255,209,102,139,203,255,195,160,255,81,211,197,255,110,110];
const crcTable=Uint32Array.from({length:256},(_,n)=>{let c=n;for(let i=0;i<8;i++)c=c&1?0xedb88320^(c>>>1):c>>>1;return c>>>0;});
function chunk(type,data){const b=new Uint8Array(data.length+12),v=new DataView(b.buffer);v.setUint32(0,data.length);b.set(new TextEncoder().encode(type),4);b.set(data,8);let c=0xffffffff;for(let i=4;i<b.length-4;i++)c=crcTable[(c^b[i])&255]^(c>>>8);v.setUint32(b.length-4,(c^0xffffffff)>>>0);return b;}
function join(parts){const b=new Uint8Array(parts.reduce((n,p)=>n+p.length,0));let at=0;for(const p of parts){b.set(p,at);at+=p.length;}return b;}
async function bounded(stream,max){const r=stream.getReader(),parts=[];let length=0;while(true){const x=await r.read();if(x.done)break;length+=x.value.length;if(length>max){await r.cancel();throw Error('size');}parts.push(x.value);}return join(parts);}
export async function transparentValuePng(input,height=64){
 if(!Number.isInteger(height)||height<1||height>154)throw Error('height');
 if(input.length>262144||!SIGNATURE.every((n,i)=>input[i]===n))throw Error('png');
 let at=8,head,palette;const ids=[];
 while(at+12<=input.length){const v=new DataView(input.buffer,input.byteOffset+at),len=v.getUint32(0);if(len>262144||at+12+len>input.length)throw Error('chunk');const type=new TextDecoder().decode(input.subarray(at+4,at+8)),data=input.slice(at+8,at+8+len);if(type==='IHDR')head=data;else if(type==='PLTE')palette=data;else if(type==='IDAT')ids.push(data);at+=12+len;if(type==='IEND')break;}
 if(!head||head.length!==13||!palette||palette.length!==405||!ids.length)throw Error('format');
 const view=new DataView(head.buffer);if(view.getUint32(0)!==263||view.getUint32(4)!==154||head[8]!==8||head[9]!==3||head[12]!==0)throw Error('format');
 if(!BASE.every((x,i)=>palette[i]===x))throw Error('palette');
 const raw=await bounded(new Blob([join(ids)]).stream().pipeThrough(new DecompressionStream('deflate')),264*154);
 if(raw.length!==264*154)throw Error('pixels');
 for(let y=0;y<154;y++)if(raw[y*264]!==0)throw Error('filter');
 const alpha=new Uint8Array(135);alpha.fill(255);alpha[0]=0;alpha[3]=0;
 for(let bg=0;bg<2;bg++)for(let fg=0;fg<9;fg++)for(let level=1;level<=7;level++){
  const index=9+bg*63+fg*7+level-1;
  palette.set(BASE.slice(fg*3,fg*3+3),index*3);alpha[index]=(fg===0||fg===3)?0:Math.round(level*255/7);
 }
 view.setUint32(4,height);
 const zipped=new Uint8Array(await new Response(new Blob([raw.slice(0,264*height)]).stream().pipeThrough(new CompressionStream('deflate'))).arrayBuffer());
 return join([SIGNATURE,chunk('IHDR',head),chunk('PLTE',palette),chunk('tRNS',alpha),chunk('IDAT',zipped),chunk('IEND',new Uint8Array())]);
}
