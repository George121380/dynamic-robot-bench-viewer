'use strict';
const $=id=>document.getElementById(id), base='data-browser-v1/';
const video=$('video'), scene=$('scene');
let manifest, episodes=[], filtered=[], current, series, windowData, bounds, sequence=0, frame=-1, split='all', videoUrl;
const colors={tool:'#b96343',cube:'#347ba5',goal:'#5b9663',input:'#5d5ca4',past:'#8d9892',future:'#c57828'};
const actionNames=['TCP Δx','TCP Δy','TCP Δz','TCP Δrx','TCP Δry','TCP Δrz','夹爪'];
const actionColors=['#397f78','#476fa5','#b16a49','#397f78','#476fa5','#b16a49','#414c48'];
const path=(e,name)=>`${base}episodes/${e.id}/${name}`;
function option(value,text){const o=document.createElement('option');o.value=value;o.textContent=text;return o;}
function episodeLabel(e){return `${e.split==='train'?'训练':'验证'} ${e.id.slice(-4)} · ${e.tool} · ${(e.steps/20).toFixed(1)}s`;}
function filteredByContext(includeTool=true){return episodes.filter(e=>(split==='all'||e.split===split)&&(!includeTool||$('toolFilter').value==='all'||e.tool===$('toolFilter').value)&&($('directionFilter').value==='all'||e.direction===Number($('directionFilter').value)));}
function applyFilters(preferred){
  filtered=filteredByContext();$('episodeSelect').replaceChildren(...filtered.map(e=>option(e.id,episodeLabel(e))));
  $('filterCount').textContent=`当前 ${filtered.length} 条 / 全部 250 条`;
  const target=filtered.find(e=>e.id===preferred)||filtered[0];
  gallery();document.querySelector('.viewer').classList.toggle('empty',!target);$('sampleDetails').hidden=!target;
  if(target)loadEpisode(target);else{++sequence;video.pause();current=null;error('这个筛选组合没有样本，请调整工具或方向。');}
}
function gallery(){
  const context=filteredByContext(false);$('toolGallery').replaceChildren();
  for(const [toolIndex,tool] of [...new Set(episodes.map(e=>e.tool))].sort().entries()){
    const rows=context.filter(e=>e.tool===tool),e=rows.find(row=>row.direction===toolIndex)||rows[0]||episodes.find(e=>e.tool===tool);
    const button=document.createElement('button');button.className='tool-card';button.dataset.tool=tool;button.disabled=!rows.length;
    const image=document.createElement('img');image.src=path(e,'poster.jpg');image.alt=`${tool} 正式样本首次接触画面`;image.loading='lazy';
    const text=document.createElement('div'),strong=document.createElement('strong'),small=document.createElement('small');strong.textContent=tool;small.textContent=`${rows.length} 条符合当前筛选`;
    text.append(strong,small);button.append(image,text);button.onclick=()=>{$('toolFilter').value=tool;applyFilters(e.id);};$('toolGallery').append(button);
  }
}
function error(message){$('loadError').textContent=message;$('loadError').hidden=false;}
async function checkedFetch(url,type='json'){const r=await fetch(url);if(!r.ok)throw new Error(`${r.status} ${url}`);return type==='json'?r.json():type==='blob'?r.blob():r.arrayBuffer();}
async function loadEpisode(e){
  if(!e)return;
  const ticket=++sequence;video.pause();$('loadError').hidden=true;$('episodeSelect').value=e.id;
  $('episodeTitle').textContent=`${e.tool} · ${e.split==='train'?'训练':'验证'}样本 ${e.id.slice(-4)}`;
  $('episodeSplit').textContent=`${e.id}  /  方向 ${e.direction*45}°–${(e.direction+1)*45}°  /  ${(e.steps/20).toFixed(1)} 秒`;
  try{
    const [buffer,window,videoBlob]=await Promise.all([checkedFetch(path(e,'series.f32'),'buffer'),checkedFetch(path(e,'window.json')),checkedFetch(path(e,'rollout.mp4'),'blob')]);
    if(ticket!==sequence)return;
    if(buffer.byteLength!==(e.steps+1)*49*4)throw new Error('轨迹文件长度不匹配');
    current=e;series=new Float32Array(buffer);windowData=window;bounds=sceneBounds();frame=-1;
    $('scrubber').max=e.steps;$('strip').src=path(e,'strip.jpg');
    $('stripCaption').textContent=`初始 ${e.poster_ticks[0]/20}s → 首次接触 ${(e.poster_ticks[1]/20).toFixed(2)}s → 最后训练帧 ${(e.poster_ticks[2]/20).toFixed(2)}s`;
    $('downloadVideo').href=path(e,'rollout.mp4');$('downloadVideo').download=e.id+'.mp4';
    $('downloadWindow').href=path(e,'window.json');$('downloadWindow').download=e.id+'-window.json';
    $('windowImage').src=path(e,'window.png');$('windowTitle').textContent=`第 ${window.tick} 帧 · ${window.seconds.toFixed(2)}s 的真实训练窗口`;
    $('showLabels').checked=false;
    document.querySelectorAll('.tool-card').forEach(b=>b.classList.toggle('active',b.dataset.tool===e.tool));
    const url=new URL(location.href);url.searchParams.set('episode',e.id);history.replaceState(null,'',url);
    const start=Math.max(0,e.contact_tick-30);
    video.onloadedmetadata=()=>{if(ticket!==sequence)return;video.currentTime=start/20;video.playbackRate=Number($('speed').value);video.play().catch(()=>{});};
    // A complete local Blob keeps frame seeking reliable even on a static server without HTTP Range.
    const previousUrl=videoUrl;videoUrl=URL.createObjectURL(videoBlob);
    video.poster=path(e,'poster.jpg');video.src=videoUrl;video.load();if(previousUrl)URL.revokeObjectURL(previousUrl);render(start,true);
  }catch(err){if(ticket===sequence)error('回放加载失败，请刷新重试。'+err.message);}
}
function raster(canvas){const width=canvas.clientWidth,height=canvas.clientHeight;if(!width||!height)return null;const ratio=Math.min(devicePixelRatio||1,2);if(canvas.width!==Math.round(width*ratio)||canvas.height!==Math.round(height*ratio)){canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);}const ctx=canvas.getContext('2d');ctx.setTransform(ratio,0,0,ratio,0,0);ctx.clearRect(0,0,width,height);return {ctx,width,height};}
function transform(point,t,entity){const o=t*49+entity*12,[x,y,z]=point;return [x*series[o]+y*series[o+3]+z*series[o+6]+series[o+9],x*series[o+1]+y*series[o+4]+z*series[o+7]+series[o+10],x*series[o+2]+y*series[o+5]+z*series[o+8]+series[o+11]];}
function corners(box){const result=[];for(const x of [-1,1])for(const y of [-1,1])for(const z of [-1,1])result.push([box.center[0]+x*box.half[0],box.center[1]+y*box.half[1],box.center[2]+z*box.half[2]]);return result;}
function sceneBounds(){let xmin=Infinity,xmax=-Infinity,ymin=Infinity,ymax=-Infinity;const add=p=>{xmin=Math.min(xmin,p[0]);xmax=Math.max(xmax,p[0]);ymin=Math.min(ymin,p[1]);ymax=Math.max(ymax,p[1]);};const verts=current.tool_geometry.boxes.flatMap(corners);for(let t=0;t<=current.steps;t+=1){for(const p of verts)add(transform(p,t,0));const o=t*49+21;add([series[o]-.03,series[o+1]-.03]);add([series[o]+.03,series[o+1]+.03]);}add([current.goal[0]-current.goal_radius,current.goal[1]-current.goal_radius]);add([current.goal[0]+current.goal_radius,current.goal[1]+current.goal_radius]);const span=Math.max(xmax-xmin,ymax-ymin,.45)+.10;return {x:(xmin+xmax)/2,y:(ymin+ymax)/2,span};}
function hull(points){const sorted=points.map(p=>[p[0],p[1]]).sort((a,b)=>a[0]-b[0]||a[1]-b[1]);const cross=(o,a,b)=>(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0]);let lower=[],upper=[];for(const p of sorted){while(lower.length>=2&&cross(lower.at(-2),lower.at(-1),p)<=0)lower.pop();lower.push(p);}for(const p of sorted.slice().reverse()){while(upper.length>=2&&cross(upper.at(-2),upper.at(-1),p)<=0)upper.pop();upper.push(p);}lower.pop();upper.pop();return lower.concat(upper);}
function worldCanvas(canvas,t,{history=true,window=false}={}){
  const r=raster(canvas);if(!r||!current)return;const {ctx:c,width:w,height:h}=r;
  const size=Math.min(w-70,h-65),scale=size/bounds.span,cx=w/2,cy=h/2-2;
  const map=p=>[cx+(p[0]-bounds.x)*scale,cy-(p[1]-bounds.y)*scale];
  const line=(pts,color,width=1,dash=[])=>{if(!pts.length)return;c.beginPath();pts.forEach((p,i)=>{const [x,y]=map(p);i?c.lineTo(x,y):c.moveTo(x,y);});c.strokeStyle=color;c.lineWidth=width;c.setLineDash(dash);c.stroke();c.setLineDash([]);};
  const dot=(p,color,radius=3)=>{const [x,y]=map(p);c.beginPath();c.arc(x,y,radius,0,Math.PI*2);c.fillStyle=color;c.fill();};
  const step=bounds.span>.95?.2:.1,loX=bounds.x-bounds.span/2,hiX=bounds.x+bounds.span/2,loY=bounds.y-bounds.span/2,hiY=bounds.y+bounds.span/2;
  c.font='10px system-ui';c.textAlign='center';c.fillStyle='#7c8981';
  for(let x=Math.ceil(loX/step)*step;x<=hiX;x+=step){line([[x,loY],[x,hiY]],'#e3e9e2');const p=map([x,loY]);c.fillStyle='#7c8981';c.fillText(x.toFixed(1),p[0],p[1]+17);}
  for(let y=Math.ceil(loY/step)*step;y<=hiY;y+=step){line([[loX,y],[hiX,y]],'#e3e9e2');const p=map([loX,y]);c.fillStyle='#7c8981';c.textAlign='right';c.fillText(y.toFixed(1),p[0]-7,p[1]+3);}
  c.textAlign='right';c.fillText('x (m)',w-12,h-12);c.textAlign='left';c.fillText('y (m)',12,16);
  const g=map(current.goal);c.beginPath();c.arc(g[0],g[1],current.goal_radius*scale,0,Math.PI*2);c.fillStyle='#5b966315';c.fill();c.strokeStyle=colors.goal;c.lineWidth=2;c.stroke();c.fillStyle=colors.goal;c.textAlign='center';c.font='11px system-ui';c.fillText('目标区',g[0],g[1]+current.goal_radius*scale+14);
  if(history){for(const entity of [0,1]){const pts=[];for(let f=0;f<=t;f+=2){const o=f*49+entity*12+9;pts.push([series[o],series[o+1]]);}line(pts,entity?'#347ba55c':'#b9634345',1.8);}}
  for(const entity of [0,1]){const boxes=entity?[{center:[0,0,0],half:[current.cube_half,current.cube_half,current.cube_half]}]:current.tool_geometry.boxes;c.fillStyle=entity?colors.cube:colors.tool;c.globalAlpha=window?.30:1;for(const box of boxes){const pts=hull(corners(box).map(p=>transform(p,t,entity))).map(map);c.beginPath();pts.forEach((p,i)=>i?c.lineTo(...p):c.moveTo(...p));c.closePath();c.fill();}c.globalAlpha=1;}
  if(window){
    const o=windowData.observation,tr=windowData.target;
    for(let i=0;i<o.track_xyz.length;i++){const pts=o.track_xyz[i].filter((_,j)=>o.track_valid[i][j]);line(pts,colors.input,2.2);if(pts.length)dot(pts.at(-1),colors.input,3);}
    for(const p of tr.query_xyz)dot(p,'#444d48',2);
    if($('showLabels').checked){for(const prefix of ['past','future'])for(let q=0;q<tr.query_xyz.length;q++){const anchor=tr.query_xyz[q],pts=tr[prefix+'_displacement'][q].flatMap((d,i)=>tr[prefix+'_valid'][q][i]?[d.map((x,k)=>x+anchor[k])]:[]);if(prefix==='past')pts.push(anchor);else pts.unshift(anchor);line(pts,colors[prefix],1.5,prefix==='past'?[3,4]:[5,3]);}}
    c.fillStyle=colors.input;c.textAlign='left';c.font='11px system-ui';c.fillText('紫色实线：8条观测历史；深色点：16个当前查询锚点',12,h-10);
  }else{const o=t*49+21,dist=Math.hypot(series[o]-current.goal[0],series[o+1]-current.goal[1]);c.font='12px system-ui';c.textAlign='left';c.fillStyle='#41524a';c.fillText(`方块距目标中心 ${(dist*100).toFixed(1)} cm`,15,h-12);}
}
function plotActions(t){const r=raster($('actionPlot'));if(!r||!current)return;const {ctx:c,width:w,height:h}=r,L=42,R=16,T=16,B=28,W=w-L-R,H=h-T-B;c.font='10px system-ui';c.textAlign='right';for(const v of [-1,0,1]){const y=T+(1-v)*H/2;c.strokeStyle='#e1e7e1';c.beginPath();c.moveTo(L,y);c.lineTo(w-R,y);c.stroke();c.fillStyle='#748078';c.fillText(String(v),L-7,y+3);}for(let i=0;i<=4;i++){const x=L+W*i/4;c.textAlign='center';c.fillText((current.steps/20*i/4).toFixed(1)+'s',x,h-9);}for(let k=0;k<7;k++){c.beginPath();const step=Math.max(1,Math.floor(current.steps/W));for(let i=0;i<current.steps;i+=step){const x=L+W*i/current.steps,y=T+(1-series[i*49+42+k])*H/2;i?c.lineTo(x,y):c.moveTo(x,y);}c.strokeStyle=actionColors[k];c.lineWidth=k===6?1.6:1;c.globalAlpha=.8;c.setLineDash(k>=3&&k<6?[4,3]:[]);c.stroke();}c.globalAlpha=1;c.setLineDash([]);const x=L+W*t/current.steps;c.beginPath();c.moveTo(x,T);c.lineTo(x,h-B);c.strokeStyle='#151e18';c.lineWidth=1.5;c.stroke();}
function stateTable(t){$('stateTime').textContent=`第 ${t} 帧 · ${(t/20).toFixed(2)}s`;const data=series.subarray(t*49+24,t*49+42);$('stateTable').querySelector('tbody').innerHTML=['位置 q','速度 q̇'].map((name,row)=>'<tr><th>'+name+'</th>'+Array.from(data.subarray(row*9,row*9+9),n=>`<td>${n.toFixed(4)}</td>`).join('')+'</tr>').join('');}
function render(t,force=false){if(!current)return;t=Math.min(current.steps,Math.max(0,t));if(t===frame&&!force)return;frame=t;$('scrubber').value=t;$('clock').textContent=`${(t/20).toFixed(2)} / ${(current.steps/20).toFixed(2)} s`;$('frameInfo').textContent=`第 ${t} / ${current.steps} 帧${t===current.steps?' · 终止帧，无下一动作':''}`;worldCanvas(scene,t);if($('sampleDetails').open){worldCanvas($('windowScene'),windowData.tick,{history:false,window:true});plotActions(t);stateTable(t);}}
function seek(t,play=false){if(!current)return;video.currentTime=Math.min(current.steps,Math.max(0,t))/20;render(Math.round(t),true);if(play)video.play().catch(()=>{});else video.pause();}
$('play').onclick=()=>video.paused?video.play().catch(()=>{}):video.pause();video.onplay=()=>$('play').textContent='暂停';video.onpause=()=>$('play').textContent='播放';
$('speed').onchange=()=>video.playbackRate=Number($('speed').value);$('scrubber').oninput=()=>seek(Number($('scrubber').value));
$('jumpStart').onclick=()=>seek(0,true);$('jumpGrasp').onclick=()=>seek(current.grasp_tick);$('jumpContact').onclick=()=>seek(current.contact_tick);$('jumpEnd').onclick=()=>seek(current.steps);$('jumpWindow').onclick=()=>{seek(current.window_tick);$('video').scrollIntoView({behavior:'smooth',block:'center'});};
$('episodeSelect').onchange=()=>loadEpisode(filtered.find(e=>e.id===$('episodeSelect').value));
$('previous').onclick=()=>{const i=filtered.findIndex(e=>e.id===current?.id);loadEpisode(filtered[(i-1+filtered.length)%filtered.length]);};$('next').onclick=()=>{const i=filtered.findIndex(e=>e.id===current?.id);loadEpisode(filtered[(i+1)%filtered.length]);};$('random').onclick=()=>loadEpisode(filtered[Math.floor(Math.random()*filtered.length)]);
$('toolFilter').onchange=()=>applyFilters();$('directionFilter').onchange=()=>applyFilters();
for(const button of document.querySelectorAll('[data-split]'))button.onclick=()=>{split=button.dataset.split;document.querySelectorAll('[data-split]').forEach(b=>b.classList.toggle('active',b===button));applyFilters();};
$('sampleDetails').ontoggle=()=>render(frame,true);$('showLabels').onchange=()=>render(frame,true);
$('actionPlot').onclick=ev=>{const box=ev.currentTarget.getBoundingClientRect();seek(Math.round((ev.clientX-box.left-42)/(box.width-58)*current.steps));};
new ResizeObserver(()=>render(frame,true)).observe(scene);
for(let i=0;i<7;i++){const span=document.createElement('span'),bar=document.createElement('i');bar.style.background=actionColors[i];if(i>=3&&i<6)bar.style.opacity=.5;span.append(bar,document.createTextNode(actionNames[i]));$('actionLegend').append(span);}
function animate(){if(current&&!video.seeking&&video.readyState>=2)render(Math.floor(video.currentTime*20+1e-5));requestAnimationFrame(animate);}requestAnimationFrame(animate);
(async()=>{try{manifest=await checkedFetch(base+'manifest.json');episodes=manifest.episodes;if(episodes.length!==250)throw new Error('正式数据索引数量异常');for(const tool of [...new Set(episodes.map(e=>e.tool))].sort())$('toolFilter').append(option(tool,tool));for(let i=0;i<8;i++)$('directionFilter').append(option(i,`${i*45}°–${(i+1)*45}°`));$('sourceIdentity').textContent=`冻结数据 · ${manifest.source_commit.slice(0,7)}`;const requested=new URL(location.href).searchParams.get('episode'),defaultEpisode=episodes.find(e=>e.split==='train'&&e.tool==='J-00');applyFilters(episodes.some(e=>e.id===requested)?requested:defaultEpisode.id);}catch(err){error('数据索引加载失败：'+err.message);}})();
