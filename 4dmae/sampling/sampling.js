'use strict';
const $=id=>document.getElementById(id);
const colors={c:'#2167ae',target:'#c03639',other:'#b37616',removed:'#8a418f'};
const visible=category=>$('show-'+category).checked;
let data,current,epoch,frame=15,playing=false,last=0,images=new Map(),hits={};
const nameTarget=n=>({1:'cube',2:'tool',3:'gripper'}[n]||'none');
const fmt=n=>Number(n).toFixed(4);
const distance=(a,b)=>Math.sqrt(a.reduce((s,v,i)=>s+(v-b[i])**2,0));
function image(path){
  if(!path)return null;
  if(!images.has(path)){const im=new Image();im.src='data/'+path;im.onload=()=>draw();im.onerror=()=>{$('time-note').textContent='Could not load image: '+path;};images.set(path,im);}
  return images.get(path);
}
function transform(){
  const z=Number($('zoom').value);let center=[64,64];
  if(z>1){const q=epoch.scene.query.filter((_,i)=>epoch.scene.target_mask[i]).map(p=>p[15]);center=[0,1].map(k=>q.reduce((s,p)=>s+p[k],0)/q.length);}
  return {z,center,point:p=>[(p[0]-center[0])*5*z+320,(p[1]-center[1])*5*z+320]};
}
function base(id,grid=false){
  const ctx=$(id).getContext('2d'),t=transform();ctx.clearRect(0,0,640,640);ctx.fillStyle='#f7f7f7';ctx.fillRect(0,0,640,640);
  let path=current.frames[$('rgb-replay').checked?frame:15];
  const im=image(path);
  if(im&&im.complete&&im.naturalWidth){ctx.imageSmoothingEnabled=true;const o=t.point([0,0]);ctx.drawImage(im,o[0],o[1],640*t.z,640*t.z);}
  else if(!path){ctx.fillStyle='#777';ctx.textAlign='center';ctx.font='20px Arial';ctx.fillText('Before episode start',320,320);}
  if(grid&&$('grid').checked){ctx.save();ctx.strokeStyle='rgba(255,255,255,.62)';ctx.lineWidth=1;for(let i=1;i<6;i++){const p=t.point([i*128/6,0]),q=t.point([i*128/6,128]);ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...q);ctx.stroke();}for(let j=1;j<4;j++){const p=t.point([0,j*32]),q=t.point([128,j*32]);ctx.beginPath();ctx.moveTo(...p);ctx.lineTo(...q);ctx.stroke();}ctx.restore();}
  hits[id]=[];return {ctx,t};
}
function marker(ctx,p,color,shape='circle',radius=5){
  ctx.save();ctx.fillStyle=color;ctx.strokeStyle='white';ctx.lineWidth=1.7;ctx.beginPath();
  if(shape==='triangle'){ctx.moveTo(p[0],p[1]-radius-1);ctx.lineTo(p[0]+radius+1,p[1]+radius);ctx.lineTo(p[0]-radius-1,p[1]+radius);ctx.closePath();}
  else ctx.arc(p[0],p[1],radius,0,Math.PI*2);
  ctx.fill();ctx.stroke();ctx.restore();
}
function trace(ctx,track,t,end,color,valid=null,dash=false){
  ctx.save();ctx.strokeStyle=color;ctx.lineWidth=2.2;ctx.setLineDash(dash?[5,3]:[]);ctx.beginPath();let started=false;
  for(let i=0;i<=end;i++){if(valid&&!valid[i]){started=false;continue;}const p=t.point(track[i]);if(!started){ctx.moveTo(...p);started=true;}else ctx.lineTo(...p);}
  ctx.stroke();ctx.restore();
}
function paintB1(){
  const {ctx,t}=base('b1'),end=$('future').checked?Math.max(0,frame-15):0;
  current.b1.query.forEach((track,i)=>{const category=i<32?'target':'other';if(!visible(category))return;const color=colors[category];if(end)trace(ctx,track,t,end,color,null,true);const p=t.point(track[end]);marker(ctx,p,color,'triangle',3.7);hits.b1.push({p,type:'B1 Q',i,body:current.b1.objects[i],xyz:current.b1.query_xyz[i][end],delta:distance(current.b1.query_xyz[i][0],current.b1.query_xyz[i][end])});});
}
function paintB5(mode){
  const {ctx,t}=base(mode,true),v=epoch[mode],cf=Math.min(frame,15),qf=$('future').checked?frame:15;
  v.condition.forEach((track,i)=>{
    const refill=mode==='holdout'&&!epoch.scene.c_pixel.includes(v.c_pixel[i]);
    if(!visible(refill?'refill':'c'))return;
    trace(ctx,track,t,cf,colors.c,v.valid);
    if(!v.valid[cf])return;
    const p=t.point(track[cf]);marker(ctx,p,colors.c);
    if(refill){ctx.save();ctx.strokeStyle=colors.c;ctx.lineWidth=2;ctx.beginPath();ctx.arc(...p,9,0,Math.PI*2);ctx.stroke();ctx.restore();}
    hits[mode].push({p,type:refill?'C (refilled)':'C',i,body:v.c_bodies[i],pixel:v.c_pixel[i],xyz:v.condition_xyz[i][cf],delta:distance(v.condition_xyz[i][15],v.condition_xyz[i][cf])});
  });
  v.query.forEach((track,i)=>{
    const category=v.target_mask[i]?'target':'other';
    if(!visible(category))return;
    const color=colors[category];
    if($('future').checked)trace(ctx,track,t,qf,color,v.valid,true);
    if($('future').checked&&!v.valid[qf])return;
    const p=t.point(track[qf]);marker(ctx,p,color,'triangle');
    hits[mode].push({p,type:v.target_mask[i]?'Q (target)':'Q (other)',i,body:v.q_bodies[i],pixel:v.q_pixel[i],xyz:v.query_xyz[i][qf],delta:distance(v.query_xyz[i][15],v.query_xyz[i][qf])});
  });
  if(mode==='holdout'&&cf===15&&visible('removed')){
    epoch.scene.condition.forEach((track,i)=>{if(v.c_pixel.includes(epoch.scene.c_pixel[i]))return;const p=t.point(track[15]);ctx.save();ctx.strokeStyle=colors.removed;ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(p[0]-7,p[1]-7);ctx.lineTo(p[0]+7,p[1]+7);ctx.moveTo(p[0]-7,p[1]+7);ctx.lineTo(p[0]+7,p[1]-7);ctx.stroke();ctx.restore();});
  }
}
function paintPool(){
  const {ctx,t}=base('pool',true),p=current.pool;
  p.xy.forEach((xy,i)=>{if(!visible(p.global_pool[i]?'global':'supplemental'))return;const pos=t.point(xy);if(p.global_pool[i])marker(ctx,pos,colors.c,'circle',2.5);else{ctx.save();ctx.strokeStyle=colors.other;ctx.lineWidth=1.8;ctx.beginPath();ctx.arc(...pos,3.2,0,Math.PI*2);ctx.stroke();ctx.restore();}hits.pool.push({p:pos,type:p.global_pool[i]?'Global candidate':'Supplemental candidate',i,body:p.bodies[i],pixel:p.pixel[i]});});
  const n=p.global_pool.filter(Boolean).length;$('pool-caption').textContent=`Stored pool: ${n} global + ${p.xy.length-n} supplemental = ${p.xy.length} distinct visible pixels`;
}
function draw(){
  if(!current)return;
  paintB1();paintB5('scene');paintB5('holdout');paintPool();
  $('time').textContent=`t = ${((frame-15)/20).toFixed(2)} s`;$('time-slider').value=frame;
  const valid=epoch.scene.valid.slice(0,Math.min(frame,15)+1).filter(Boolean).length;
  $('time-note').textContent=`${$('rgb-replay').checked?'RGB replay is reference only.':'Current RGB is fixed.'} C: ${valid}/16 valid history positions up to this time; frozen after t = 0. ${$('future').checked?'Dashed Q paths are ground-truth labels, never model predictions.':'Q markers show the current anchors.'}`;
}
function update(){
  current=data.cases[Number($('sample').value)];epoch=current.epochs[Number($('epoch').value)];
  $('sample-caption').textContent=`Train episode ${String(current.episode).padStart(4,'0')} · tick ${current.tick} · window ${current.index} · target: ${nameTarget(epoch.scene.target)} · ${current.slot===null?'episode-start example':`first-batch slot ${current.slot+1}`} · sampling epoch ${epoch.epoch}`;
  const removed=epoch.holdout.removed;
  $('holdout-caption').textContent=removed?`${removed} target C replaced · same 12 Q`:'0 C replaced · identical to scene';
  const bg=epoch.scene.c_bodies.filter(n=>!n.startsWith('panda_')&&!['cube','l_shape_tool'].includes(n)).length;
  $('scene-caption').textContent=`12 C + 12 Q · ${bg} background C · ${epoch.scene.scene_hits_target} target C`;
  $('point-detail').textContent='Select a marker to inspect its body, material identity and world coordinates.';
  const table=document.createElement('table');table.innerHTML='<thead><tr><th>Point</th><th>Body</th><th>512px pixel ID</th></tr></thead>';const body=document.createElement('tbody');
  for(const role of ['c','q'])epoch.scene[role+'_pixel'].forEach((p,i)=>{const row=document.createElement('tr');[role.toUpperCase()+i,epoch.scene[role+'_bodies'][i],String(p)].forEach(v=>{const td=document.createElement('td');td.textContent=v;row.append(td);});body.append(row);});table.append(body);$('point-table').replaceChildren(table);
  document.querySelectorAll('.slot').forEach(e=>e.classList.toggle('active',Number(e.dataset.slot)===current.slot));
  current.frames.forEach(image);draw();
}
function detail(ev){
  const id=ev.currentTarget.id,r=ev.currentTarget.getBoundingClientRect();const p=[(ev.clientX-r.left)*640/r.width,(ev.clientY-r.top)*640/r.height];
  const near=(hits[id]||[]).map(h=>({...h,d:Math.hypot(h.p[0]-p[0],h.p[1]-p[1])})).sort((a,b)=>a.d-b.d)[0];
  if(!near||near.d>20){$('point-detail').textContent='Select a visible marker; use 2× or 4× zoom for small objects.';return;}
  $('point-detail').textContent=`${near.type} ${near.i} · ${near.body}${near.pixel===undefined?'':` · pixel ID ${near.pixel} (512 × 512)`}${near.xyz?` · world xyz [${near.xyz.map(fmt).join(', ')}] m · displacement from t0 ${(near.delta*1000).toFixed(2)} mm`:''}`;
}
function setPlaying(value){playing=value;last=0;$('play').textContent=value?'Pause':'Play';if(value)requestAnimationFrame(animate);}
function animate(now){if(!playing)return;if(!last)last=now;if(now-last>=100){last=now;frame++;if(frame>30){frame=30;setPlaying(false);}draw();}if(playing)requestAnimationFrame(animate);}
function downloadFigure(){
  setPlaying(false);draw();const canvas=document.createElement('canvas');canvas.width=2020;canvas.height=860;
  const c=canvas.getContext('2d');c.fillStyle='white';c.fillRect(0,0,2020,860);c.textAlign='center';c.fillStyle='#333';c.font='28px Arial';c.fillText('B1 / B5 — Training Point Sampling',1010,38);
  c.font='19px Arial';c.fillText(`Train episode ${current.episode} · tick ${current.tick} · epoch ${epoch.epoch} · target ${nameTarget(epoch.scene.target)} · t = ${((frame-15)/20).toFixed(2)} s`,1010,70);
  ['b1','scene','holdout'].forEach((id,i)=>{const x=30+i*660;c.font='23px Arial';c.fillText(['B1 · 64 fixed Q','B5 scene · 12 C + 12 Q',`B5 holdout · ${epoch.holdout.removed} C replaced`][i],x+320,112);c.drawImage($(id),x,130,640,640);});
  c.font='19px Arial';const shown=[['c','Original C',colors.c],['target','Target Q / B1 cube',colors.target],['other','Other Q / B1 tool',colors.other],['removed','Removed C',colors.removed],['refill','Refilled C',colors.c]].filter(([key])=>visible(key));
  shown.forEach(([,label,color],i)=>{c.fillStyle=color;c.fillText(label,30+(i+.5)*1960/shown.length,805);});
  if(!shown.length){c.fillStyle='#555';c.fillText('All point categories hidden',1010,805);}
  c.fillStyle='#555';c.font='17px Arial';c.fillText(`Current-visible B5 anchors; oracle histories. ${$('future').checked?'Dashed Q paths: ground-truth labels only.':'Q shown at current anchors.'} B1 8cfd8df · B5 b537131`,1010,839);
  const a=$('export-link');a.hidden=false;a.download=`training-points-ep${current.episode}-t${current.tick}-epoch${epoch.epoch}.png`;a.href=canvas.toDataURL('image/png');a.click();
}
async function init(){
  const response=await fetch('data/samples.json');if(!response.ok)throw new Error('Sample data HTTP '+response.status);data=await response.json();
  data.cases.forEach((c,i)=>{const option=document.createElement('option');option.value=i;option.textContent=`Episode ${String(c.episode).padStart(4,'0')} / tick ${c.tick}${c.early_history?' · early history':''}`;$('sample').append(option);});
  const firstChanged=data.cases.findIndex(c=>c.epochs[0].holdout.removed>0);$('sample').value=firstChanged>=0?firstChanged:0;
  const counts=[['Background',10.3064],['Arm',1.0906],['Cube / tool / gripper',.6030]];
  counts.forEach(([name,n])=>{const row=document.createElement('div');row.className='coverage-row';const label=document.createElement('span');label.textContent=name;const track=document.createElement('div');track.className='coverage-track';const fill=document.createElement('div');fill.className='coverage-fill';fill.style.width=(n/12*100)+'%';track.append(fill);const value=document.createElement('span');value.textContent=n.toFixed(2);row.append(label,track,value);$('coverage').append(row);});const scale=document.createElement('p');scale.className='caption';scale.textContent='Bar scale: 0–12 condition points';$('coverage').append(scale);
  for(let rank=0;rank<8;rank++){const col=document.createElement('div');col.className='rank';const title=document.createElement('div');title.className='rank-title';title.textContent='Rank '+rank;col.append(title);data.batch.filter(b=>b.rank===rank).forEach(b=>{const idx=data.cases.findIndex(c=>c.slot===b.slot);const cell=document.createElement(idx>=0?'button':'div');cell.className='slot '+b.mode+(idx>=0?' exported':'');cell.dataset.slot=b.slot;cell.textContent=`${b.slot+1} ${b.mode==='scene'?'S':'H'}`;cell.title=`Episode ${b.episode}, tick ${b.tick}, window ${b.index}`;if(idx>=0)cell.onclick=()=>{$('sample').value=idx;update();$('samples').scrollIntoView({behavior:'smooth'});};col.append(cell);});$('batch').append(col);}
  $('provenance').textContent=`Export: ${data.exported_at} · scene manifest ${data.b5_manifest_sha256.slice(0,16)}… · oracle manifest ${data.b1_manifest_sha256.slice(0,16)}…`;
  ['sample','epoch'].forEach(id=>$(id).onchange=()=>{setPlaying(false);update();});['zoom','future','rgb-replay','grid'].forEach(id=>$(id).onchange=draw);
  document.querySelectorAll('.point-filters input').forEach(input=>{input.onchange=()=>{$('point-detail').textContent='Select a visible marker to inspect its body, material identity and world coordinates.';$('export-link').hidden=true;draw();};});
  $('time-slider').oninput=e=>{setPlaying(false);frame=Number(e.target.value);draw();};['play','restart','anchor','download'].forEach(id=>$(id).disabled=false);
  $('play').onclick=()=>{if(frame===30)frame=0;setPlaying(!playing);draw();};$('restart').onclick=()=>{setPlaying(false);frame=0;draw();};
  $('anchor').onclick=()=>{setPlaying(false);frame=15;draw();};$('download').onclick=downloadFigure;
  ['b1','scene','holdout','pool'].forEach(id=>$(id).onclick=detail);update();
}
init().catch(e=>{$('sample-caption').textContent='Unable to load the production sample export. '+e.message;console.error(e);});
