"use strict";
const $ = id => document.getElementById(id);
const videos = [$('head-video'), $('left-video'), $('right-video')];
const colors = {left:'#087c76',right:'#b66e35',grid:'#dfe5e1',text:'#677573',command:'#8c8f99'};
const kinds = {initial:'初始',change:'变速',stop:'停止',reverse:'反向',resume:'恢复'};
let catalog, sources, episode, data, frame = 0, playing = false, generation = 0, sourceMode = "official";
const cache = new Map();
const fmt = (n,d=3) => Number(n).toFixed(d);

function showError(error) { $('error').hidden=false; $('error').textContent='读取轨迹失败：'+error.message; }
function stop() { playing=false; videos.forEach(v=>v.pause()); $('play').textContent='播放'; $('play').setAttribute('aria-label','播放轨迹'); $('play').setAttribute('aria-pressed','false'); }
function drawBase(id, xlo, xhi, ylo, yhi, xlabel, ylabel) {
  const canvas=$(id), box=canvas.getBoundingClientRect(), width=Math.max(200,box.width);
  const height=Number(canvas.dataset.logicalHeight||(canvas.dataset.logicalHeight=canvas.getAttribute('height')));
  const dpr=window.devicePixelRatio||1;
  canvas.width=width*dpr; canvas.height=height*dpr; canvas.style.height=height+'px';
  const c=canvas.getContext('2d'); c.scale(dpr,dpr);
  const pad={l:49,r:17,t:14,b:35}, w=width-pad.l-pad.r,h=height-pad.t-pad.b;
  if(xhi===xlo)xhi=xlo+1; if(yhi===ylo)yhi=ylo+1;
  const X=x=>pad.l+(x-xlo)/(xhi-xlo)*w, Y=y=>pad.t+(yhi-y)/(yhi-ylo)*h;
  c.font='12px -apple-system,sans-serif'; c.lineWidth=1; c.strokeStyle=colors.grid; c.fillStyle=colors.text;
  for(let i=0;i<5;i++){const y=ylo+(yhi-ylo)*i/4;c.beginPath();c.moveTo(pad.l,Y(y));c.lineTo(width-pad.r,Y(y));c.stroke();c.textAlign='right';c.fillText(fmt(y,2),pad.l-8,Y(y)+3);}
  for(let i=0;i<5;i++){const x=xlo+(xhi-xlo)*i/4;c.textAlign='center';c.fillText(fmt(x,1),X(x),height-19);}
  c.textAlign='left';c.fillText(ylabel,pad.l,9);c.textAlign='right';c.fillText(xlabel,width-pad.r,height-3);
  return {c,X,Y,width,height,pad,xlo,xhi};
}
function line(plot, points, color, dashed=false) {
  const {c,X,Y}=plot;c.strokeStyle=color;c.lineWidth=1.7;c.setLineDash(dashed?[4,3]:[]);c.beginPath();
  points.forEach((p,i)=>i?c.lineTo(X(p[0]),Y(p[1])):c.moveTo(X(p[0]),Y(p[1])));c.stroke();c.setLineDash([]);
}
function marker(plot,x,y,color) {const {c,X,Y}=plot;c.fillStyle=color;c.beginPath();c.arc(X(x),Y(y),4.5,0,Math.PI*2);c.fill();c.strokeStyle='#fff';c.lineWidth=1.5;c.stroke();}
function timeCursor(plot) {const {c,X,pad,height}=plot;c.strokeStyle='#263d39';c.lineWidth=1;c.beginPath();c.moveTo(X(data.timestamp[frame]),pad.t);c.lineTo(X(data.timestamp[frame]),height-pad.b);c.stroke();}
function drawSpeed() {
  const max=Math.max(.15,...data.speed.map(Math.abs))*1.15;
  const p=drawBase('speed-chart',0,episode.seconds,-max,max,'仿真时间（s）','速度（m/s）');
  line(p,[[0,0],[episode.seconds,0]],colors.command,true);
  const points=[];data.speed.forEach((v,i)=>{if(i)points.push([data.timestamp[i],data.speed[i-1]]);points.push([data.timestamp[i],v]);});
  line(p,points,colors.left);timeCursor(p);marker(p,data.timestamp[frame],data.speed[frame],colors.left);
}
function drawPose(id,axis) {
  const both=[...data.left_ee,...data.right_ee];
  let xmin=Math.min(...both.map(p=>p[0])),xmax=Math.max(...both.map(p=>p[0]));
  let ymin=Math.min(...both.map(p=>p[axis])),ymax=Math.max(...both.map(p=>p[axis]));
  const dx=Math.max(xmax-xmin,.2)*.1,dy=Math.max(ymax-ymin,.1)*.16;
  const p=drawBase(id,xmin-dx,xmax+dx,ymin-dy,ymax+dy,(episode.source==='official'?'场景':'世界')+' X（m）',(episode.source==='official'?'场景':'世界')+(axis===1?' Y（m）':' Z（m）'));
  for(const [arm,color] of [['left',colors.left],['right',colors.right]]){
    const points=data[arm+'_ee'];line(p,points.map(x=>[x[0],x[axis]]),color);
    marker(p,points[frame][0],points[frame][axis],color);
  }
}
function drawJoint() {
  if(!$('joint-chart').getBoundingClientRect().width)return;
  const j=Number($('joint-select').value),a=data.state.map(x=>x[j]),b=data.action.map(x=>x[j]);
  let low=Math.min(...a,...b),high=Math.max(...a,...b); const padding=Math.max(high-low,.1)*.15;
  const unit=(j===6||j===13)?'归一化开度':'角度（rad）';
  const p=drawBase('joint-chart',0,episode.seconds,low-padding,high+padding,'仿真时间（s）',unit);
  line(p,b.map((v,i)=>[data.timestamp[i],v]),colors.command,true);line(p,a.map((v,i)=>[data.timestamp[i],v]),colors.left);timeCursor(p);
  $('joint-caption').textContent=`当前状态 ${fmt(a[frame],4)} · 当前动作 ${fmt(b[frame],4)}。关节为 rad；夹爪为归一化开度（0 闭合、1 张开）。观测在动作之前记录。`;
}
function draw() { if(!data)return;if(data.speed)drawSpeed();drawPose('xy-chart',1);drawPose('xz-chart',2);drawJoint(); }
function updateReadouts() {
  $('scrub').value=frame;$('clock').textContent=`${fmt(data.timestamp[frame],2)} / ${fmt(episode.seconds,2)} s`;
  $('speed-readout').textContent=data.speed?`${data.speed[frame]>=0?'+':''}${fmt(data.speed[frame])} m/s`:'官方未记录';
  $('frame-readout').textContent=`${frame+1} / ${episode.frames}`;
  const t=data.timestamp[frame];const event=[...(episode.events||[])].reverse().find(e=>e.time<=t+1e-7);
  $('event-readout').textContent=event?(kinds[event.kind]||event.kind):'官方原始条件';
  document.querySelectorAll('.event-chip').forEach(x=>x.classList.toggle('active',Number(x.dataset.time)===event?.time));
  draw();
}
function seek(newFrame) {stop();frame=Math.max(0,Math.min(episode.frames-1,newFrame));const t=data.timestamp[frame];videos.forEach(v=>{if(v.readyState>0)v.currentTime=t;});updateReadouts();}
async function selectEpisode(id) {
  stop();const token=++generation;episode=catalog.episodes.find(e=>e.id===id);data=null;frame=0;
  document.querySelectorAll('.episode-button').forEach(b=>b.classList.toggle('active',b.dataset.id===id));
  const official=episode.source==='official';
  const reference=episode.expert_style==='reference';
  $('intro-note').textContent=official?'官方原始示范：对照左右臂选择和抓取姿态。原始 HDF5 未记录速度读数。':'记住第一个物体，再抓取随后出现的同类物体。传送带速度以仿真时钟变化。';
  $('episode-kicker').textContent=official?`OFFICIAL · ${episode.id}`:`L${episode.level} · LAYOUT ${episode.layout_id} · SEED ${episode.seed}`;
  $('episode-title').textContent=official?`官方 Demo ${Number(episode.id.split('_')[1])}`:`尝试 ${String(episode.attempt+1).padStart(2,'0')} · ${['','随机固定速度','随机停止与恢复','随机变速 / 停止 / 反向'][episode.level]}`;
  $('result-badge').textContent=official?'官方训练示范':(episode.success?'抓取成功':'失败记录');$('result-badge').classList.toggle('failure',!official&&!episode.success);
  const reason={ik_unreachable:'IK 不可达',timeout_before_grasp:'超时，目标未完成抓取',target_not_yet_reachable:'目标未进入可达区域',grasp_did_not_lift_target:'夹持后未抬起目标',unconfirmed_grasp_lift:'原奖励触发抬升，但未确认抓取；排除训练'}[episode.failure_reason]||episode.failure_reason;
  $('episode-meta').textContent=official?`${episode.frames} 帧 · ${fmt(episode.seconds,2)} 秒 · ${episode.fps} Hz · 左臂累计关节变化 ${fmt(episode.left_joint_travel_rad,2)} rad · 右臂 ${fmt(episode.right_joint_travel_rad,2)} rad`:`${episode.frames} 帧 · ${fmt(episode.seconds,2)} 仿真秒 · 初始速度 ${fmt(episode.initial_speed)} m/s · 范围 ${fmt(episode.min_speed)} 至 ${fmt(episode.max_speed)} m/s${episode.target_category?' · 目标 '+episode.target_category:''}${reason?' · '+reason:''}`;
  $('xy-title').textContent=`俯视 · ${official?'场景':'世界'}坐标 X–Y`;$('xz-title').textContent=`侧视 · ${official?'场景':'世界'}坐标 X–Z`;
  $('speed-panel').hidden=official;$('events-panel').hidden=official;$('input-readout').textContent=official?'原始数据无速度字段':'可独立开关';
  $('aside-note').textContent=official?'官方 Hugging Face 原始视频及 HDF5 数值。原始编号 0–99 全部保留。':'新版随机选择官方接近和抬起路径，适配当前物体与速度，分别使用左右臂。成功沿用原任务抬升条件，失败也保留。';
  $('format-note').textContent=official?`视频为官方原始 preview_video 文件，逐个校验 SHA-256；数值来自同版本 HDF5。官方未提供逐帧传送带速度读数，不推算或补写。数据集版本 ${episode.dataset_revision.slice(0,12)}。`:'网页视频为 480×360 的 H.264 预览；训练数据保留三路 640×480 RGB。速度始终记录，评估时默认关闭模型输入，可使用 --include-speed 开启。此处展示脚本专家轨迹。';
  videos.forEach((v,i)=>{const camera=['cam_head','cam_left_wrist','cam_right_wrist'][i];v.src=episode.videos[camera].url;v.poster=episode.videos[camera].poster;v.playbackRate=Number($('rate').value);v.load();});
  $('scrub').max=episode.frames-1;$('scrub').value=0;
  $('events').replaceChildren(...(episode.events||[]).map(e=>{const b=document.createElement('button');b.className='event-chip';b.dataset.time=e.time;b.textContent=`${fmt(e.time,2)} s · ${kinds[e.kind]||e.kind}  ${fmt(e.speed)} m/s`;b.onclick=()=>seek(Math.min(episode.frames-1,Math.ceil(e.time*(episode.fps||25))));return b;}));
  $('source-caption').textContent=official?`来源：RoboDojo-Benchmark/RoboDojo · ${episode.id} · 原始 HDF5 数值，不平滑轨迹。 `:`来源：${catalog.task} / ${episode.id} · 所有曲线直接读取本回合 HDF5，不平滑轨迹。`;
  if(official){const a=document.createElement('a');a.href=episode.source_url;a.textContent='查看官方原始文件';a.target='_blank';a.rel='noopener';$('source-caption').append(a);}
  $('motion-panel').hidden=official||!reference;
  if(reference){
    const plans=episode.expert?.plans||[];
    $('motion-description').textContent=plans.map(p=>`${p.arm==='left'?'左':'右'}臂 · 计划工具倾角 ${fmt(p.planned_tilt_deg,1)}° · ${p.prepare_seconds?`准备 ${fmt(p.prepare_seconds,1)} s · `:''}接近 ${fmt(p.approach_seconds,1)} s · ${fmt(p.start_time,2)} s 开始`).join('；');
    $('motion-references').replaceChildren(...plans.map(p=>{const b=document.createElement('button');b.className='event-chip';b.textContent=`对照官方 Demo ${Number(p.reference_episode.split('_')[1])}`;b.onclick=()=>changeSource('official',p.reference_episode).catch(showError);return b;}));
  }
  if(!cache.has(id)){const response=await fetch(episode.data_url);if(!response.ok)throw new Error(response.statusText);cache.set(id,await response.json());}
  if(token!==generation)return;data=cache.get(id);updateReadouts();
  history.replaceState(null,'','#'+encodeURIComponent(id));
}
function renderList() {
  const level=$('level-filter').value,result=$('result-filter').value,arm=$('arm-filter').value,style=$('style-filter').value;
  const armMatch=e=>arm==='all'||(arm==='left'&&e.left_joint_travel_rad>.1&&e.right_joint_travel_rad<=.1)||(arm==='right'&&e.right_joint_travel_rad>.1&&e.left_joint_travel_rad<=.1)||(arm==='both'&&e.left_joint_travel_rad>.1&&e.right_joint_travel_rad>.1);
  const rows=catalog.episodes.filter(e=>e.source==='official'?armMatch(e):((level==='all'||e.level===Number(level))&&(result==='all'||e.success===(result==='success'))&&armMatch(e)&&(style==='all'||(e.expert_style||'vertical')===style)));
  $('episodes').replaceChildren(...rows.map(e=>{const b=document.createElement('button');b.className='episode-button'+(episode?.id===e.id?' active':'');b.dataset.id=e.id;
    const img=document.createElement('img');img.src=e.thumbnail;img.alt='回合终帧预览';img.loading='lazy';
    const text=document.createElement('span'),strong=document.createElement('strong'),small=document.createElement('small');
    strong.textContent=e.source==='official'?`官方 Demo ${String(Number(e.id.split('_')[1])).padStart(3,'0')}`:`L${e.level} · 尝试 ${String(e.attempt+1).padStart(2,'0')} · ${e.success?'成功':'失败'}`;small.textContent=e.source==='official'?`${fmt(e.seconds,1)} s · 原始三路视频`:`${fmt(e.initial_speed)} m/s · 布局 ${e.layout_id} · ${fmt(e.seconds,1)} s`;text.append(strong,small);b.append(img,text);b.onclick=()=>selectEpisode(e.id).catch(showError);return b;}));
  document.querySelector('.workspace').hidden=!rows.length;
  if(!rows.length){const empty=document.createElement('p');empty.className='aside-note';empty.textContent='该筛选下没有轨迹';$('episodes').append(empty);}
  $('episode-count').textContent=`${rows.length} / ${catalog.episodes.length} 条`;
  if(episode&&rows.length&&!rows.some(e=>e.id===episode.id))selectEpisode(rows[0].id).catch(showError);
}
async function changeSource(mode,id) {
  stop();sourceMode=mode;catalog=sources[mode];episode=null;data=null;
  $('arm-filter').value='all';$('level-filter').value='all';$('result-filter').value='all';
  $('show-official').classList.toggle('active',mode==='official');$('show-scripted').classList.toggle('active',mode==='scripted');
  $('show-official').setAttribute('aria-pressed',mode==='official');$('show-scripted').setAttribute('aria-pressed',mode==='scripted');
  $('arm-filter-label').hidden=false;$('style-filter-label').hidden=mode==='official';
  if(mode==='scripted')$('style-filter').value=catalog.episodes.some(e=>e.expert_style==='reference')?'reference':'all';
  if(id&&mode==='scripted')$('style-filter').value=catalog.episodes.find(e=>e.id===id)?.expert_style||'vertical';
  $('level-filter').disabled=mode==='official';$('result-filter').disabled=mode==='official';
  renderList();const candidates=catalog.episodes.filter(e=>mode==='official'||$('style-filter').value==='all'||(e.expert_style||'vertical')===$('style-filter').value);const first=candidates.find(e=>e.id===id)||candidates.find(e=>e.success)||candidates[0];
  if(first)await selectEpisode(first.id);
}
async function init() {
  const response=await fetch('episodes.json',{cache:'no-store'});if(!response.ok)throw new Error(response.statusText);
  const scripted=await response.json();scripted.episodes.forEach(e=>e.source='scripted');
  const officialResponse=await fetch('official/catalog.json');const official=officialResponse.ok?await officialResponse.json():{episodes:[]};
  sources={scripted,official};catalog=scripted;
  $('official-count').textContent=`${official.episodes.length} 条`;$('show-official').disabled=!official.episodes.length;
  const newRows=scripted.episodes.filter(e=>e.expert_style==='reference');
  $('collection-status').textContent=newRows.length?`新版 ${newRows.filter(e=>e.success).length} 条成功 · ${newRows.filter(e=>!e.success).length} 条失败记录`:'旧版垂直抓取快照';
  $('counts').replaceChildren(...[1,2,3].map(l=>{const count=(newRows.length?newRows:scripted.episodes).filter(e=>e.level===l&&e.success).length,target=scripted.pilot_targets[l];const el=document.createElement('div');el.innerHTML=`<div class="count-label">L${l} ${newRows.length?'新版':'旧版'}成功</div><div class="count-value">${count}<small> / ${target}</small></div><div class="count-bar"><i style="width:${Math.min(100,count/target*100)}%"></i></div>`;return el;}));
  [...new Set(scripted.episodes.map(e=>e.level))].sort().forEach(l=>{const o=document.createElement('option');o.value=l;o.textContent='L'+l;$('level-filter').append(o);});
  $('built-at').textContent=`脚本快照 ${new Date(scripted.built_at).toLocaleString('zh-CN',{timeZone:'UTC'})} UTC · 官方 ${official.revision?.slice(0,12)||'未加载'}`;
  for(let j=0;j<14;j++){const o=document.createElement('option');o.value=j;const k=j%7;o.textContent=`${j<7?'左':'右'}臂 ${k===6?'夹爪':'关节 '+(k+1)}`;$('joint-select').append(o);}
  const comparisonResponse=await fetch('comparison.json',{cache:'no-store'});if(comparisonResponse.ok){const comparison=await comparisonResponse.json();$('comparison-text').textContent=comparison.description;$('comparison').hidden=false;}
  const hash=decodeURIComponent(location.hash.slice(1))||(newRows.length?scripted.default_episode:'');const isOfficial=official.episodes.some(e=>e.id===hash);
  await changeSource(isOfficial||(!hash&&!newRows.length&&official.episodes.length)?'official':'scripted',hash);
}
$('show-official').onclick=()=>changeSource('official').catch(showError);$('show-scripted').onclick=()=>changeSource('scripted').catch(showError);
$('arm-filter').onchange=renderList;$('level-filter').onchange=renderList;$('result-filter').onchange=renderList;$('joint-select').onchange=drawJoint;
$('style-filter').onchange=renderList;
$('scrub').oninput=()=>data&&seek(Number($('scrub').value));$('previous').onclick=()=>data&&seek(frame-1);$('next').onclick=()=>data&&seek(frame+1);
$('rate').onchange=()=>videos.forEach(v=>v.playbackRate=Number($('rate').value));
$('play').onclick=async()=>{if(!data)return;if(playing){stop();return;}if(frame===episode.frames-1)seek(0);try{await Promise.all(videos.map(v=>v.play()));playing=true;$('play').textContent='暂停';$('play').setAttribute('aria-label','暂停轨迹');$('play').setAttribute('aria-pressed','true');}catch(e){stop();showError(e);}};
videos[0].addEventListener('ended',stop);
videos.forEach(v=>v.addEventListener('loadedmetadata',()=>{if(data)v.currentTime=data.timestamp[frame];}));
$('speed-chart').onclick=e=>{if(!data)return;const box=e.currentTarget.getBoundingClientRect();const ratio=Math.max(0,Math.min(1,(e.clientX-box.left-49)/(box.width-66)));seek(Math.round(ratio*episode.seconds*(episode.fps||25)));};
document.querySelector('details').addEventListener('toggle',drawJoint);
window.addEventListener('resize',draw);
function tick(){if(playing&&data){const next=Math.min(episode.frames-1,Math.floor((videos[0].currentTime+1e-5)*(episode.fps||25)));if(next!==frame){frame=next;videos.slice(1).forEach(v=>{if(Math.abs(v.currentTime-videos[0].currentTime)>.10)v.currentTime=videos[0].currentTime;});updateReadouts();}}requestAnimationFrame(tick);}tick();
init().catch(showError);
