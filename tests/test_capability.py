"""Actual private API + launcher/browser integration. Never prints credentials.
Needs the private launcher created outside the repo; writes one tagged synthetic response.
Cleanup only the exact UUID in /workspace/thht-private/capability-tests-manifest.json.
"""
import os,json,time,uuid,re,sys,traceback
def private_error(kind,value,tb):
 print("FAIL private capability test (details suppressed to protect management link): "+kind.__name__+" at line "+str(traceback.extract_tb(tb)[-1].lineno),flush=True)
sys.excepthook=private_error
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=os.environ.get('THHT_TEST_BASE','http://127.0.0.1:8765').rstrip('/')
PRIVATE=Path('/workspace/thht-private')
TOKEN=json.loads((PRIVATE/'management-token.json').read_text())['management_token']
LAUNCHER=PRIVATE/'THHT-private-dashboard.html'
LOCAL=PRIVATE/'local-test-launcher.html'
source=LAUNCHER.read_text();LOCAL.write_text(source.replace('https://wellsy-an.github.io/thht-study/',BASE+'/'));os.chmod(LOCAL,0o600)
RUN='synthetic-capability-'+str(uuid.uuid4())
with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True)
 context=b.new_context();public=context.new_page();public.goto(BASE+'/');public.wait_for_selector('#accessPanel')
 assert not public.is_visible('#workspace') and public.locator('input[type="password"],input[type="email"]').count()==0
 assert public.locator('#rows tr').count()==0
 # API checks exercise real Supabase HTTPS through the browser, not mocked Auth or SQL claims.
 checks=public.evaluate('''async token=>{
  const origin=CONFIG.url+'/rest/v1',h={'Content-Type':'application/json',apikey:CONFIG.key};
  const read=await fetch(origin+'/rpc/read_dashboard',{method:'POST',headers:h,body:JSON.stringify({management_token:token,page_offset:0})});
  const result=await read.json();
  const empty=await fetch(origin+'/rpc/read_dashboard',{method:'POST',headers:h,body:JSON.stringify({management_token:'',page_offset:0})});
  const invalid=await fetch(origin+'/rpc/read_dashboard',{method:'POST',headers:h,body:JSON.stringify({management_token:token.slice(0,-1)+(token.endsWith('A')?'B':'A'),page_offset:0})});
  const direct=await fetch(origin+'/responses?select=*',{headers:h});
  const write=await fetch(origin+'/responses',{method:'POST',headers:h,body:JSON.stringify({participant_id:crypto.randomUUID(),payload:{}})});
  const misuse=await fetch(origin+'/rpc/read_dashboard',{method:'POST',headers:h,body:JSON.stringify({management_token:token,page_offset:0,record:{}})});
  return {read:read.status,ok:result.ok,empty:empty.status,invalid:invalid.status,direct:direct.status,write:write.status,misuse:misuse.status,baseline:result.total_count};
 }''',TOKEN)
 assert checks['read']==200 and checks['ok'] is True
 for k in ['empty','invalid','direct','write']:assert checks[k] in [401,403]
 assert checks['misuse']>=400
 print('PASS actual HTTPS valid capability read, no/invalid capability denial, direct-table read/write denial, no write-shaped capability RPC',flush=True)
 # Open the private attachment through file:// on desktop. Trigger anchor navigation without
 # putting a credential URL in a navigation API or error message.
 manager=context.new_page();manager.goto(LOCAL.as_uri());manager.evaluate("document.querySelector('#openPanel').click()")
 manager.wait_for_selector('#workspace',timeout=35000)
 assert manager.evaluate('location.hash')==''
 assert manager.evaluate("localStorage.getItem(ACCESS_KEY)") == TOKEN
 baseline=int(manager.inner_text('#kTotal'));before=int(manager.inner_text('#kComplete'))
 assert baseline==checks['baseline']
 assert manager.locator('input[type="password"],input[type="email"]').count()==0
 print('PASS file launcher → panel, fragment cleared, no account form, browser remembers capability',flush=True)
 # One clearly synthetic completed record through the unchanged participant upload implementation.
 participant_context=b.new_context();participant=participant_context.new_page();participant.goto(BASE+'/experiment.html')
 data=participant.evaluate('''async run=>{
   const now=new Date().toISOString();state.consent={age18:true,consent:true,timestamp:now};
   Object.assign(state.video,{started:true,ended:true,watchOk:true,duration:60,playedSec:60,enteredAt:now,leftAt:now});
   state.attention={response:'peach',firstResponse:'tomato',answeredAt:now};
   state.thht.selectedIds=['P01','P02','P03','P11','P12','P13','P14','P21','P22','P23','P24'];
   state.thht.selectionOrder=state.thht.selectedIds.slice();state.thht.startTime=Date.now()-1000;state.thht.endTime=Date.now();state.thht.locked=true;
   for(let i=1;i<=8;i++)state.scales['shs0'+i]=i%2===0?4:2;
   state.scales.perceived_violence=2;state.scales.ai_content_freq=3;state.choices={believedOtherParticipant:'yes',dailyShortVideoTime:'30_60'};
   state.demographics={age:24,gender:'prefer_not'};state.finishedAt=now;state.debrief.dataDecision='complete';
   const record=Object.assign(buildResults(true),{synthetic_test_run:run});
   await submitResults(record);return {id:state.participantId,status:state.submission.status};
 }''',RUN)
 assert data['status']=='uploaded'
 manifest=PRIVATE/'capability-tests-manifest.json';entries=json.loads(manifest.read_text()) if manifest.exists() else []
 entries.append({'participant_id':data['id'],'test_run':RUN});manifest.write_text(json.dumps(entries,indent=2));os.chmod(manifest,0o600)
 start=time.monotonic();manager.wait_for_function('id=>records.some(r=>r.participant_id===id)',arg=data['id'],timeout=16000)
 latency=time.monotonic()-start
 assert int(manager.inner_text('#kTotal'))==baseline+1 and int(manager.inner_text('#kComplete'))==before+1
 matched=manager.evaluate('id=>{const r=records.find(x=>x.participant_id===id);return {first:r.payload.attention_response,final:r.payload.attention_final_response,pass:r.payload.attention_pass};}',data['id'])
 assert matched=={'first':'tomato','final':'peach','pass':True}
 assert manager.evaluate('charts.daily.data.datasets[0].data.reduce((a,b)=>a+b,0)')==before+1
 assert '5' in manager.inner_text('#connection')
 assert manager.evaluate("Object.keys(localStorage).every(k=>!localStorage.getItem(k).includes('"+data['id']+"'))")
 print(f'PASS actual completed upload automatically updated rows/KPIs/line chart in {latency:.1f}s; no response cached in browser storage',flush=True)
 # Refresh plain root in same browser: remembered access, no form or file needed.
 manager.goto(BASE+'/');manager.wait_for_selector('#workspace',timeout=35000);assert manager.evaluate('location.hash')==''
 manager.click('#forget');assert manager.is_visible('#accessPanel') and not manager.is_visible('#workspace')
 assert manager.locator('#rows tr').count()==0 and manager.evaluate('records.length')==0
 assert manager.evaluate('localStorage.getItem(ACCESS_KEY)') is None
 print('PASS later plain-root open remembers access; forget clears token and rendered data',flush=True)
 # Mobile also opens the file-based launcher without login. No screenshots of real response rows.
 mobile=b.new_context(viewport={'width':390,'height':844},is_mobile=True,has_touch=True);m=mobile.new_page();m.goto(LOCAL.as_uri());m.evaluate("document.querySelector('#openPanel').click()")
 m.wait_for_selector('#workspace',timeout=35000);assert m.evaluate('location.hash')==''
 assert m.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
 assert m.locator('input[type="password"],input[type="email"]').count()==0
 print('PASS mobile file launcher and protected panel without account',flush=True)
 b.close()
