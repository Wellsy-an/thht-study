'use strict';
// Publishable key only. Access is enforced by database grants and RLS, not this UI.
const CONFIG = Object.freeze({ url: 'https://dhoelfaebggvzubxinxr.supabase.co', key: 'sb_publishable_cCqUEf5-mKanatsYMlrDyw_sD4VEA_R' });
const $ = id => document.getElementById(id);
const CONDITIONS = { fruit_violent: 'Violent / 暴力', fruit_nonviolent: 'Non-violent / 非暴力' };
const COLORS = ['#2f4a68','#7d9cc0','#b5bcc5','#59626d'];
const charts = {};
const ACCESS_KEY = 'thht_private_management_access';
const REFRESH_MS = 5000;
let timer, records = [], authorized = false, generation = 0, refreshing = false, rerun = false;
let managementToken = '';
// URL fragments are not sent to the web host or in HTTP referrers. Consume and
// clear the fragment before requesting any response data. Only the capability,
// never raw participant records, is remembered in this browser.
function readAccess(){
  const incomingToken = new URLSearchParams(location.hash.slice(1)).get('manage');
  if (location.hash) history.replaceState(null, '', location.pathname + location.search);
  try { managementToken = localStorage.getItem(ACCESS_KEY) || ''; } catch (_) {}
  if (incomingToken && /^[A-Za-z0-9_-]{64}$/.test(incomingToken)) {
    managementToken = incomingToken;
    try { localStorage.setItem(ACCESS_KEY, managementToken); } catch (_) {}
  }
}
const mean = xs => { const a = xs.filter(x => typeof x === 'number' && Number.isFinite(x)); return a.length ? Math.round(a.reduce((s,x)=>s+x,0)/a.length*1000)/1000 : null; };
// Build the chart day explicitly: locale date order varies across browser versions.
const day = s => new Date(new Date(s).getTime()+8*3600000).toISOString().slice(0,10);
const time = s => s ? new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(s))+' UTC+8' : '—';
const text = (id,s) => $(id).textContent = s;
function message(s,error=false){ text('message',s); $('message').className=error?'error':''; }
function filtered(){const c=$('condition').value,q=$('search').value.trim().toLowerCase();return records.filter(r=>(c==='all'||r.payload.condition===c)&&(!q||r.participant_id.toLowerCase().includes(q)));}
function chart(id,type,labels,datasets,extra={}) {
  charts[id] = new Chart($(id), {type,data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,animation:false,plugins:{legend:{display:true}},scales:type==='doughnut'?{}:{y:{beginAtZero:true}},...extra}});
}
let chartFailed = false;
function chartsUnavailable(){
  chartFailed=true;
  for(const id of Object.keys(charts)){
    try { charts[id].destroy(); } catch (_) {}
    delete charts[id];
  }
  $('chartError').hidden=false;$('chartLoading').hidden=true;$('charts').hidden=true;
}
function initCharts(){
  if(!authorized||!window.Chart||chartFailed||charts.daily)return;
  try {
  $('charts').hidden=false;

  Chart.defaults.font.family=getComputedStyle(document.body).fontFamily;
  const ds=(label,color=COLORS[0])=>({label,data:[],backgroundColor:color,borderColor:color});
  chart('daily','line',[],[{...ds('Daily / 每日'),tension:.2},{...ds('Cumulative / 累计',COLORS[1]),tension:.2}]);
  chart('thht','bar',Object.values(CONDITIONS),[ds('Help / 帮助'),ds('Hurt / 伤害',COLORS[1]),ds('Difference / 差异',COLORS[2])]);
  chart('ratings','bar',Object.values(CONDITIONS),[ds('SHS mean / 当前感受均分'),ds('Perceived violence / 感知暴力',COLORS[1])],{scales:{y:{min:0,max:5}}});
  chart('distribution','bar',Array.from({length:21},(_,i)=>i-10),[ds('Participants / 人数')]);
  chart('difficulty','doughnut',['Easy / 简单','Medium / 中等','Hard / 困难'],[{data:[],backgroundColor:COLORS.slice(0,3)}]);
  chart('attention','bar',Object.values(CONDITIONS),[ds('Pass / 通过'),ds('Fail / 未通过',COLORS[2])]);
  chart('belief','bar',['Yes / 是','No / 否','Not sure / 不确定'],[ds('Participants / 人数')]);
  chart('videoTime','bar',['<30min','30–60min','1–2h','2–3h','>3h'],[ds('Participants / 人数')]);
  $('chartLoading').hidden=true;$('chartError').hidden=true;
  } catch (_) { chartsUnavailable(); }
}
function loadChartLibrary(){
  // Charts are optional. A slow/failed library must never block authorization or records.
  const library=$('chartLibrary');
  library.addEventListener('load',()=>{initCharts();if(authorized)render();});
  library.addEventListener('error',chartsUnavailable);
  setTimeout(()=>{if(!window.Chart&&!chartFailed){$('chartLoading').hidden=true;$('chartError').hidden=false;}},12000);
  if(window.Chart)initCharts();
}

function updateCharts(done){
  if(!charts.daily)return;
  const daily={}; for(const r of done){const d=day(r.finish_time);daily[d]=(daily[d]||0)+1;}
  const keys=Object.keys(daily).sort(); let days=[];
  if(keys.length){const first=new Date(keys[0]+'T00:00:00+08:00');const last=keys[keys.length-1];for(let d=first;day(d)<=last;d=new Date(d.getTime()+86400000))days.push(day(d));}
  charts.daily.data.labels=days;charts.daily.data.datasets[0].data=days.map(d=>daily[d]||0);let total=0;charts.daily.data.datasets[1].data=days.map(d=>total+=daily[d]||0);
  const grouped=Object.keys(CONDITIONS).map(c=>done.filter(r=>r.condition===c));
  ['thht_help','thht_hurt','thht_difference'].forEach((key,i)=>charts.thht.data.datasets[i].data=grouped.map(a=>mean(a.map(r=>r[key]))));
  ['shs_mean','perceived_violence'].forEach((key,i)=>charts.ratings.data.datasets[i].data=grouped.map(a=>mean(a.map(r=>r[key]))));
  charts.distribution.data.datasets[0].data=Array.from({length:21},(_,i)=>done.filter(r=>r.thht_difference===i-10).length);
  charts.difficulty.data.datasets[0].data=['thht_easy_count','thht_medium_count','thht_hard_count'].map(k=>done.reduce((s,r)=>s+(r[k]==null?0:r[k]),0));
  [true,false].forEach((v,i)=>charts.attention.data.datasets[i].data=grouped.map(a=>a.filter(r=>r.attention_pass===v).length));
  charts.belief.data.datasets[0].data=['yes','no','not_sure'].map(k=>done.filter(r=>r.believed_other_participant===k).length);
  charts.videoTime.data.datasets[0].data=['lt30','30_60','1_2h','2_3h','gt3h'].map(k=>done.filter(r=>r.daily_short_video_time===k).length);
  Object.values(charts).forEach(c=>c.update());
}
function render(){
  if(!authorized)return;
  const selected=filtered(),done=selected.map(r=>r.payload).filter(r=>r.completion_status==='complete');
  text('kTotal',selected.length);text('kComplete',done.length);text('kExit',selected.filter(r=>r.payload.completion_status==='withdrawn_during_study').length);
  const scored=done.filter(r=>typeof r.attention_pass==='boolean');const passed=scored.filter(r=>r.attention_pass).length;
  text('kAttention',scored.length?`${passed}/${scored.length} (${Math.round(passed/scored.length*100)}%)`:'—');
  try { updateCharts(done); } catch (_) { chartsUnavailable(); }
  $('rows').textContent='';
  for(const r of selected){
    const p=r.payload,tr=document.createElement('tr'),id=document.createElement('td'),button=document.createElement('button');
    button.type='button';button.textContent=r.participant_id;button.onclick=()=>{text('recordDetail',JSON.stringify(r,null,2));$('detail').open=true;};id.append(button);tr.append(id);
    const cells=[time(r.received_at),CONDITIONS[p.condition]||p.condition,p.completion_status==='complete'?'Complete / 完成':'Exit / 退出',p.attention_pass===true?'Pass / 通过':p.attention_pass===false?'Fail / 未通过':'—',p.completion_status==='complete'?`${p.thht_easy_count}/${p.thht_medium_count}/${p.thht_hard_count}`:'—',p.completion_status==='complete'?`${p.thht_help}/${p.thht_hurt}/${p.thht_difference}`:'—',p.shs_mean,p.perceived_violence,p.age];
    for(const value of cells){const td=document.createElement('td');td.textContent=value==null?'—':value;tr.append(td);}$('rows').append(tr);
  }
  text('rowCount',`${selected.length} / ${records.length} records / 份记录`);
}
function clearData(){
  records=[];authorized=false;generation++;if(timer)clearInterval(timer);timer=null;
  $('workspace').hidden=true;$('rows').textContent='';text('recordDetail','');text('connection','');
  for (const id of ['kTotal','kComplete','kExit']) text(id,'0'); text('kAttention','—'); text('rowCount','');
  try { for(const c of Object.values(charts)){for(const ds of c.data.datasets)ds.data=[];c.update();} } catch (_) { chartsUnavailable(); }
}
function forgetAccess(notice) {
  clearData(); managementToken = '';
  try { localStorage.removeItem(ACCESS_KEY); } catch (_) {}
  $('accessPanel').hidden=false; $('forget').hidden=true; $('retry').hidden=true;
  message(notice || 'Access forgotten on this browser. Reopen your private entry file to return. / 已清除此浏览器的管理权限；再次使用时请打开专属入口文件。');
}
async function dashboardRequest(offset){
  // AbortSignal.timeout is missing in several embedded/mobile browsers. Always
  // time out even there, and abort the request when AbortController is supported.
  const controller=typeof AbortController==='function'?new AbortController():null;
  let timeout;
  try {
    return await Promise.race([
      (async()=>{
        const options={method:'POST',headers:{'Content-Type':'application/json',apikey:CONFIG.key},
          body:JSON.stringify({management_token:managementToken,page_offset:offset}),
          cache:'no-store',credentials:'omit',referrerPolicy:'no-referrer'};
        if(controller)options.signal=controller.signal;
        const response=await fetch(CONFIG.url+'/rest/v1/rpc/read_dashboard',options);
        if(!response.ok)return {status:response.status,ok:false};
        return {status:response.status,ok:true,result:await response.json()};
      })(),
      new Promise((_,reject)=>{timeout=setTimeout(()=>{if(controller)controller.abort();reject(new Error('Refresh timed out'));},20000);})
    ]);
  } finally { clearTimeout(timeout); }
}
async function loadRecords(){
  if(!managementToken)return;
  if(refreshing){rerun=true;return;} refreshing=true;const gen=generation;
  try{
    const all=[];let offset=0;let refreshedAt=null;
    while(true){
      const response=await dashboardRequest(offset);
      if(gen!==generation)return;
      if(response.status===401||response.status===403){forgetAccess('This private entry is invalid or has been revoked. Reopen the current private entry file. / 此专属入口无效或已停用，请打开最新的专属入口文件。');return;}
      if(!response.ok)throw new Error('Refresh unavailable');
      const result=response.result;
      if(result.ok!==true||!Array.isArray(result.records))throw new Error('Invalid dashboard response');
      if(gen!==generation)return;
      all.push(...result.records);refreshedAt=result.refreshed_at;
      if(result.records.length<500)break;offset+=500;
    }
    if(gen!==generation)return;
    authorized=true;$('workspace').hidden=false;$('accessPanel').hidden=true;$('forget').hidden=false;
    records=Array.from(new Map(all.map(r=>[r.participant_id,r])).values());initCharts();render();
    $('emptyState').hidden=records.length!==0;
    $('retry').hidden=true;
    text('connection',`Auto-refresh every 5 seconds · Last confirmed refresh: ${time(refreshedAt || new Date())} / 每5秒自动刷新 · 最近确认刷新时间`);message('');
  }catch(e){if(gen===generation){
    $('retry').hidden=false;
    message(authorized?'Refresh failed; retrying automatically. Displayed records may be stale. / 刷新失败，将自动重试；显示的记录可能不是最新。':'Cannot reach the data service. Your access is kept; retrying automatically. Use Retry below. If this persists, open this website in Chrome, Edge or Safari instead of an in-app browser. / 暂时无法连接数据服务，管理权限已保留，正在自动重试。也可点击下方“重试”；若持续失败，请用 Chrome、Edge 或 Safari 打开，不要在聊天软件内打开。',true);
  }}
  finally{refreshing=false;if(rerun){rerun=false;loadRecords();}}
}
function exportRecords(format){
  if(!authorized)return;
  const a=filtered().map(r=>({...r.payload,server_received_at:r.received_at,server_receipt_id:r.receipt_id}));let content;
  if(format==='json')content=JSON.stringify(a,null,2);
  else{const columns=Array.from(new Set(a.flatMap(Object.keys))).sort();const cell=v=>{if(v==null)return '';let s=typeof v==='object'?JSON.stringify(v):String(v);if(/^[=+\-@\t\r]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';};content='\ufeff'+[columns.map(cell).join(','),...a.map(r=>columns.map(k=>cell(r[k])).join(','))].join('\r\n');}
  const url=URL.createObjectURL(new Blob([content],{type:format==='json'?'application/json':'text/csv;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download=`thht_${day(new Date())}.${format}`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function init(){
  readAccess();
  $('startupNotice').hidden=true;
  $('retry').onclick=loadRecords;
  loadChartLibrary();
  $('forget').onclick=()=>forgetAccess();
  $('refresh').onclick=loadRecords;$('condition').onchange=render;$('search').oninput=render;$('csv').onclick=()=>exportRecords('csv');$('json').onclick=()=>exportRecords('json');
  if(managementToken){
    $('accessPanel').hidden=true;$('forget').hidden=false;
    message('Opening your statistics panel… / 正在打开您的统计面板……');
    timer=setInterval(loadRecords,REFRESH_MS);loadRecords();
  }else{
    message('Open your private management entry file to view study data. No account is required. / 请打开专属管理入口文件查看研究数据，无需账号。');
  }
  window.addEventListener('storage',event=>{
    if(event.key===ACCESS_KEY&&managementToken&&event.newValue!==managementToken){
      clearData();managementToken='';$('accessPanel').hidden=false;$('forget').hidden=true;
      message('Management access changed in another tab. Reopen your private entry file. / 其他标签页已更改管理权限，请重新打开专属入口文件。');
    }
  });
}
try { init(); } catch (_) {
  $('startupNotice').hidden=false;
  message('This browser could not start the panel. Refresh, or open it in Chrome, Edge or Safari. No account is needed. / 此浏览器未能启动面板，请刷新，或用 Chrome、Edge、Safari 打开，无需账号。',true);
}
