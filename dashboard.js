'use strict';
// Publishable key only. Access is enforced by database grants and RLS, not this UI.
const CONFIG = Object.freeze({ url: 'https://dhoelfaebggvzubxinxr.supabase.co', key: 'sb_publishable_cCqUEf5-mKanatsYMlrDyw_sD4VEA_R' });
const $ = id => document.getElementById(id);
const CONDITIONS = { fruit_violent: 'Violent / 暴力', fruit_nonviolent: 'Non-violent / 非暴力' };
const COLORS = ['#2f4a68','#7d9cc0','#b5bcc5','#59626d'];
const charts = {};
let client, channel, timer, records = [], authorized = false, generation = 0, refreshing = false, rerun = false;
const mean = xs => { const a = xs.filter(x => typeof x === 'number' && Number.isFinite(x)); return a.length ? Math.round(a.reduce((s,x)=>s+x,0)/a.length*1000)/1000 : null; };
const day = s => new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date(s));
const time = s => s ? new Intl.DateTimeFormat('en-GB',{timeZone:'Asia/Shanghai',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date(s))+' UTC+8' : '—';
const text = (id,s) => $(id).textContent = s;
function message(s,error=false){ text('message',s); $('message').className=error?'error':''; }
function filtered(){const c=$('condition').value,q=$('search').value.trim().toLowerCase();return records.filter(r=>(c==='all'||r.payload.condition===c)&&(!q||r.participant_id.toLowerCase().includes(q)));}
function chart(id,type,labels,datasets,extra={}) {
  charts[id] = new Chart($(id), {type,data:{labels,datasets},options:{responsive:true,maintainAspectRatio:false,animation:false,plugins:{legend:{display:true}},scales:type==='doughnut'?{}:{y:{beginAtZero:true}},...extra}});
}
function initCharts(){
  if(!window.Chart){$('chartError').hidden=false;$('charts').hidden=true;return;}
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
}
function updateCharts(done){
  if(!charts.daily)return;
  const daily={}; for(const r of done){const d=day(r.finish_time);daily[d]=(daily[d]||0)+1;}
  const keys=Object.keys(daily).sort(); let days=[];
  if(keys.length){const first=new Date(keys[0]+'T00:00:00+08:00');const last=keys.at(-1);for(let d=first;day(d)<=last;d=new Date(d.getTime()+86400000))days.push(day(d));}
  charts.daily.data.labels=days;charts.daily.data.datasets[0].data=days.map(d=>daily[d]||0);let total=0;charts.daily.data.datasets[1].data=days.map(d=>total+=daily[d]||0);
  const grouped=Object.keys(CONDITIONS).map(c=>done.filter(r=>r.condition===c));
  ['thht_help','thht_hurt','thht_difference'].forEach((key,i)=>charts.thht.data.datasets[i].data=grouped.map(a=>mean(a.map(r=>r[key]))));
  ['shs_mean','perceived_violence'].forEach((key,i)=>charts.ratings.data.datasets[i].data=grouped.map(a=>mean(a.map(r=>r[key]))));
  charts.distribution.data.datasets[0].data=Array.from({length:21},(_,i)=>done.filter(r=>r.thht_difference===i-10).length);
  charts.difficulty.data.datasets[0].data=['thht_easy_count','thht_medium_count','thht_hard_count'].map(k=>done.reduce((s,r)=>s+(r[k]??0),0));
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
  updateCharts(done); $('rows').replaceChildren();
  for(const r of selected){
    const p=r.payload,tr=document.createElement('tr'),id=document.createElement('td'),button=document.createElement('button');
    button.type='button';button.textContent=r.participant_id;button.onclick=()=>{text('recordDetail',JSON.stringify(r,null,2));$('detail').open=true;};id.append(button);tr.append(id);
    const cells=[time(r.received_at),CONDITIONS[p.condition]||p.condition,p.completion_status==='complete'?'Complete / 完成':'Exit / 退出',p.attention_pass===true?'Pass / 通过':p.attention_pass===false?'Fail / 未通过':'—',p.completion_status==='complete'?`${p.thht_easy_count}/${p.thht_medium_count}/${p.thht_hard_count}`:'—',p.completion_status==='complete'?`${p.thht_help}/${p.thht_hurt}/${p.thht_difference}`:'—',p.shs_mean,p.perceived_violence,p.age];
    for(const value of cells){const td=document.createElement('td');td.textContent=value??'—';tr.append(td);}$('rows').append(tr);
  }
  text('rowCount',`${selected.length} / ${records.length} records / 份记录`);
}
function clearData(){
  records=[];authorized=false;generation++;if(timer)clearInterval(timer);timer=null;
  if(channel){client.removeChannel(channel);channel=null;}
  $('workspace').hidden=true;$('rows').replaceChildren();text('recordDetail','');text('connection','');
  for (const id of ['kTotal','kComplete','kExit']) text(id,'0'); text('kAttention','—'); text('rowCount','');
  for(const c of Object.values(charts)){for(const ds of c.data.datasets)ds.data=[];c.update();}
}
async function loadRecords(){
  if(!authorized)return;
  if(refreshing){rerun=true;return;} refreshing=true;const gen=generation;
  try{
    const access=await client.rpc('researcher_access');
    if(gen!==generation)return;
    if(access.error||access.data!==true){clearData();message('This account is not authorized to read study data. / 此账号未获研究数据读取权限。',true);return;}
    const all=[];let offset=0;
    while(true){const {data,error}=await client.from('responses').select('participant_id,received_at,receipt_id,payload').order('received_at',{ascending:false}).order('participant_id').range(offset,offset+499);
      if(error)throw error;if(gen!==generation)return;all.push(...data);if(data.length<500)break;offset+=500;
    }
    if(gen!==generation)return;
    records=Array.from(new Map(all.map(r=>[r.participant_id,r])).values());render();
    text('connection',`Last confirmed refresh: ${time(new Date())} / 最近确认刷新时间`);message('');
  }catch(e){if(gen===generation)message('Refresh failed; the displayed records may be stale. / 刷新失败；显示的记录可能不是最新。',true);}
  finally{refreshing=false;if(rerun){rerun=false;loadRecords();}}
}
async function sessionChanged(session){
  clearData();const gen=generation;$('logout').hidden=!session;$('loginPanel').hidden=!!session;
  if(!session){message('Sign in to view live study data. / 登录后查看实时研究数据。');return;}
  message('Checking researcher authorization… / 正在验证研究者权限……');
  const {data,error}=await client.rpc('researcher_access');if(gen!==generation)return;
  if(error||data!==true){message('Signed in, but this account is not authorized. Ask the project owner to add this account UUID to the researcher allowlist. / 已登录，但此账号尚未授权。请项目所有者将此账号 UUID 加入研究者名单。',true);return;}
  authorized=true;$('workspace').hidden=false;
  channel=client.channel('researcher-responses').on('postgres_changes',{event:'INSERT',schema:'public',table:'responses'},()=>loadRecords()).subscribe(status=>{
    if(gen!==generation)return;
    if(status==='SUBSCRIBED')loadRecords();
    else if(status==='CHANNEL_ERROR'||status==='TIMED_OUT')message('Realtime disconnected; automatic refresh continues every 15 seconds. / 实时连接中断；仍每15秒自动刷新。',true);
  });
  await loadRecords();if(gen===generation&&authorized)timer=setInterval(loadRecords,15000);
}
function exportRecords(format){
  if(!authorized)return;
  const a=filtered().map(r=>({...r.payload,server_received_at:r.received_at,server_receipt_id:r.receipt_id}));let content;
  if(format==='json')content=JSON.stringify(a,null,2);
  else{const columns=Array.from(new Set(a.flatMap(Object.keys))).sort();const cell=v=>{if(v==null)return '';let s=typeof v==='object'?JSON.stringify(v):String(v);if(/^[=+\-@\t\r]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};content='\ufeff'+[columns.map(cell).join(','),...a.map(r=>columns.map(k=>cell(r[k])).join(','))].join('\r\n');}
  const url=URL.createObjectURL(new Blob([content],{type:format==='json'?'application/json':'text/csv;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download=`thht_${day(new Date())}.${format}`;link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
function init(){
  initCharts();if(!window.supabase){message('Login service could not load. Reload this page. / 登录服务未能加载，请刷新页面。',true);return;}
  client=supabase.createClient(CONFIG.url,CONFIG.key,{auth:{storageKey:'thht_researcher_auth',detectSessionInUrl:false}});
  $('loginForm').onsubmit=async e=>{e.preventDefault();$('loginButton').disabled=true;message('Signing in… / 正在登录……');try{const {error}=await client.auth.signInWithPassword({email:$('email').value.trim(),password:$('password').value});if(error)message('Sign-in failed. Check the account and password, or contact the project owner. / 登录失败，请检查账号密码或联系项目所有者。',true);}finally{$('password').value='';$('loginButton').disabled=false;}};
  $('logout').onclick=async()=>{clearData();await client.auth.signOut({scope:'local'});};
  $('refresh').onclick=loadRecords;$('condition').onchange=render;$('search').oninput=render;$('csv').onclick=()=>exportRecords('csv');$('json').onclick=()=>exportRecords('json');
  // Schedule outside the auth callback to avoid a supabase-js auth lock deadlock.
  client.auth.onAuthStateChange((event,session)=>{if(event!=='TOKEN_REFRESHED')setTimeout(()=>sessionChanged(session),0);});
}
init();
