"use strict";
let catalog, selected, camera = "birdview";
const $ = id => document.getElementById(id);
const video = $("video");
const names = {expert:"专家示范",slow:"慢推对照",fast:"快推对照",demo:"调试演示",calibration:"速度校准"};
const reasons = {success:"成功",outside_target:"停在目标区外",no_collision:"未碰到 B",off_table:"物体离桌",timeout:"超时",second_strike:"重复击打",collision_before_release:"尚未分离就碰撞",direct_robot_b_contact:"机器人直接碰 B",nonfinite_state:"状态发散",physics_error:"物理异常"};
function listEpisodes() {
  const category = $("category").value, outcome = $("outcome").value;
  const rows = catalog.episodes.filter(e => (category === "all" || e.category === category) &&
    (outcome === "all" || (e.result.reason === "success" ? "success" : "failure") === outcome));
  $("episode-list").replaceChildren();
  for (const e of rows) {
    const button = document.createElement("button");button.className = "episode"+(selected?.id === e.id ? " selected" : "");button.type="button";
    const row = document.createElement("span");row.className="row";
    const label = document.createElement("span");label.textContent=`${String(e.episode.seed+1).padStart(2,"0")} · ${names[e.category]}`;
    const outcomeLabel = document.createElement("span");outcomeLabel.className=e.result.reason==="success"?"pass":"fail";outcomeLabel.textContent=e.result.reason==="success"?"成功":"失败";
    row.append(label,outcomeLabel);const detail=document.createElement("small");detail.textContent=`B ${e.episode.b_y.toFixed(2)} → 目标 ${e.episode.target_y.toFixed(2)} m`;
    button.append(row,detail);button.onclick=()=>selectEpisode(e);$("episode-list").append(button);
  }
  if (rows.length && !rows.some(e=>e.id===selected?.id)) selectEpisode(rows[0]);
  if (!rows.length) {const note=document.createElement("p");note.textContent="此筛选条件下没有回合。";$("episode-list").append(note);}
}
function selectEpisode(e) {
  selected=e;$("episode-id").textContent=e.id;
  $("episode-title").textContent=`布局 ${e.episode.seed+1} · ${names[e.category]}`;
  $("result").textContent=reasons[e.result.reason]||e.result.reason;$("result").className="badge"+(e.result.reason==="success"?"":" failed");
  $("b-init").textContent=e.episode.b_y.toFixed(2)+" m";$("goal").textContent=e.episode.target_y.toFixed(2)+" m";
  $("stroke").textContent=e.stroke_speed_m_per_s.toFixed(3)+" m/s";$("error").textContent=(e.result.target_error_m*100).toFixed(2)+" cm";
  $("events").replaceChildren();
  for (const [key,name] of [["release_time","分离确认"],["collision_time","首次碰撞"]]) if (e.result[key]!=null) {const span=document.createElement("span");span.textContent=`${name} ${e.result[key].toFixed(3)} s`;$("events").append(span);}
  const end=document.createElement("span");end.textContent=`结束 ${e.duration_s.toFixed(3)} s`;$("events").append(end);
  setCamera(camera,false);listEpisodes();draw();
}
function setCamera(name, preserve=true) {
  camera=name;const t=preserve?video.currentTime:0;const playing=!video.paused;
  video.src=selected.videos[name];video.onloadedmetadata=()=>{video.currentTime=Math.min(t,selected.duration_s);if(playing)video.play().catch(()=>{});draw();};
  for (const id of ["birdview","third_person_camera"]) $(id).setAttribute("aria-pressed",String(id===name));
}
function plot(id, arrays, min, max, label, goal) {
  const canvas=$(id), dpr=window.devicePixelRatio||1,w=canvas.clientWidth,h=Number(canvas.dataset.cssHeight||canvas.getAttribute("height"));
  canvas.dataset.cssHeight=String(h);
  if (canvas.width!==Math.round(w*dpr)||canvas.height!==Math.round(h*dpr)) {canvas.width=Math.round(w*dpr);canvas.height=Math.round(h*dpr);canvas.style.height=h+"px";}
  const ctx=canvas.getContext("2d");ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);
  const m={l:55,r:14,t:26,b:36},pw=w-m.l-m.r,ph=h-m.t-m.b;
  const x=t=>m.l+t/selected.duration_s*pw,y=v=>m.t+(max-v)/(max-min)*ph;
  ctx.font="10px -apple-system, sans-serif";ctx.fillStyle="#69747a";ctx.strokeStyle="#d9dedb";ctx.lineWidth=1;
  for(let i=0;i<=4;i++){const v=min+(max-min)*i/4;ctx.beginPath();ctx.moveTo(m.l,y(v));ctx.lineTo(w-m.r,y(v));ctx.stroke();ctx.fillText(v.toFixed(2),6,y(v)+3);}
  for(let i=0;i<=5;i++){const t=selected.duration_s*i/5;ctx.fillText(t.toFixed(1),x(t)-7,h-19);}
  ctx.fillText(label,6,12);ctx.fillText("仿真时间 (s)",Math.max(m.l,w/2-25),h-3);
  if(goal!=null){ctx.fillStyle="rgba(49,115,74,.07)";ctx.fillRect(m.l,y(goal+.05),pw,y(goal-.05)-y(goal+.05));ctx.strokeStyle="#31734a";ctx.setLineDash([5,4]);ctx.beginPath();ctx.moveTo(m.l,y(goal));ctx.lineTo(w-m.r,y(goal));ctx.stroke();ctx.setLineDash([]);}
  ["#d64e3d","#3766b9"].forEach((color,k)=>{ctx.strokeStyle=color;ctx.lineWidth=1.5;ctx.beginPath();arrays[k].forEach((v,i)=>{const px=x(selected.time[i]),py=y(v);i?ctx.lineTo(px,py):ctx.moveTo(px,py);});ctx.stroke();});
  for(const [key,name] of [["release_time","分离"],["collision_time","碰撞"]]){const t=selected.result[key];if(t==null)continue;ctx.strokeStyle="#919b9f";ctx.lineWidth=1;ctx.setLineDash([3,4]);ctx.beginPath();ctx.moveTo(x(t),m.t);ctx.lineTo(x(t),m.t+ph);ctx.stroke();ctx.setLineDash([]);ctx.fillStyle="#69747a";ctx.fillText(name,x(t)+4,m.t-7);}
  const now=Math.min(video.currentTime||0,selected.duration_s);ctx.strokeStyle="#253038";ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x(now),m.t);ctx.lineTo(x(now),m.t+ph);ctx.stroke();
  canvas.onclick=event=>{video.currentTime=Math.max(0,Math.min(selected.duration_s,(event.clientX-canvas.getBoundingClientRect().left-m.l)/pw*selected.duration_s));draw();};
}
function draw(){if(!selected)return;$("play-time").textContent=Math.min(video.currentTime||0,selected.duration_s).toFixed(2)+" s";
  plot("position",[selected.a_y,selected.b_y],-.8,.7,"y 位置 (m)",selected.episode.target_y);
  const vmax=Math.max(.2,...selected.a_speed,...selected.b_speed)*1.08;
  plot("velocity",[selected.a_speed,selected.b_speed],0,vmax,"线速度 (m/s)");
}
video.addEventListener("timeupdate",draw);video.addEventListener("seeked",draw);window.addEventListener("resize",draw);
$("category").onchange=listEpisodes;$("outcome").onchange=listEpisodes;
for(const id of ["birdview","third_person_camera"])$(id).onclick=()=>setCamera(id);
fetch("episodes.json",{cache:"no-cache"}).then(r=>{if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json();}).then(data=>{
  catalog=data;$("count").textContent=data.episodes.length;$("success").textContent=`${data.episodes.filter(e=>e.result.reason==="success").length} / ${data.episodes.length}`;
  if(!data.episodes.length)throw new Error("回合清单为空");selectEpisode(data.episodes.find(e=>e.category==="expert")||data.episodes[0]);
}).catch(err=>{$("load-error").textContent=" 回放加载失败："+err.message;});
