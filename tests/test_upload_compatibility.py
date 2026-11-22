"""Offline upload contract regressions. All Supabase requests are mocked; no live writes."""
import copy,json,re
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8765/experiment.html'
UUID=re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',re.I)
SEED="""()=>{
 const now='2026-11-22T08:10:00.000Z';
 state.consent={age18:true,consent:true,timestamp:now};
 Object.assign(state.video,{started:true,ended:true,watchOk:true,duration:60,playedSec:60,enteredAt:now,leftAt:now});
 state.attention={response:'peach',firstResponse:'tomato',answeredAt:now};
 state.thht.selectedIds=['P01','P02','P03','P11','P12','P13','P14','P21','P22','P23','P24'];
 state.thht.selectionOrder=state.thht.selectedIds.slice();state.thht.startTime=1000;state.thht.endTime=2000;state.thht.locked=true;
 for(let i=1;i<=8;i++)state.scales['shs0'+i]=i%2===0?4:2;
 state.scales.perceived_violence=2;state.scales.ai_content_freq=3;
 state.choices={believedOtherParticipant:'yes',dailyShortVideoTime:'30_60'};
 state.demographics={age:24,gender:'prefer_not'};state.finishedAt=now;
 state.debrief.dataDecision='complete';goToStep(10);saveState();
}"""
def upload(p):
 return p.evaluate("async()=>{await submitResults(buildResults(true));showSubmissionStatus('complete');return {status:state.submission.status,code:state.submission.lastErrorCode,http:state.submission.lastHttpStatus,id:state.participantId}}")
def verify_backup(p,before):
 record=p.evaluate('state.lastRecord')
 for key,value in before.items():
  if key not in ('participant_id','submission_status'):assert record[key]==value,key
 assert 'submission_token' not in record and 'token' not in record
 assert p.is_visible('#resultsPanel')
 assert p.locator('#resultsJson').is_hidden()
 assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert p.inner_text('#uploadSupport').find(p.evaluate("state.participantId||'Unavailable'"))>=0
 assert p.evaluate("!document.body.innerText.includes(state.submission.token||'NO-ACTUAL-TOKEN')")
 return record

def case(browser,mode,width=390,preview=False):
 ctx=browser.new_context(viewport={'width':width,'height':844},accept_downloads=True)
 if mode in ('no_uuid','native_uuid_throws'):ctx.add_init_script("Object.defineProperty(Crypto.prototype,'randomUUID',{value:"+('undefined' if mode=='no_uuid' else "function(){throw Error('blocked')}")+",configurable:true})")
 if mode=='no_crypto':ctx.add_init_script("Object.defineProperty(Crypto.prototype,'randomUUID',{value:undefined,configurable:true});Object.defineProperty(Crypto.prototype,'getRandomValues',{value:undefined,configurable:true})")
 if mode=='no_fetch':ctx.add_init_script('window.fetch=undefined')
 if mode=='setup_error':ctx.add_init_script("Object.defineProperty(window,'fetch',{get(){throw Error('non-sensitive-test-detail')}})")
 if mode=='no_abort':ctx.add_init_script('window.AbortController=undefined')
 if mode=='abort_throws':ctx.add_init_script("window.AbortController=function(){throw Error('blocked')}")
 if mode in ('no_storage','no_storage_network'):ctx.add_init_script("Storage.prototype.getItem=function(){throw Error('blocked')};Storage.prototype.setItem=function(){throw Error('blocked')}")
 if mode in ('timeout','timeout_no_abort'):
  ctx.add_init_script("const realTimeout=window.setTimeout;window.setTimeout=(fn,ms)=>realTimeout(fn,ms===25000?100:ms)")
  if mode=='timeout_no_abort':ctx.add_init_script('window.AbortController=undefined')
 state={'mode':mode,'posts':[],'saved':{},'held':[]}
 def route_request(route):
  if not route.request.url.endswith('/rpc/submit_thht'):route.abort();return
  body=route.request.post_data_json;state['posts'].append(copy.deepcopy(body));pid=body['record']['participant_id']
  if state['mode'] in ('network','no_storage_network'):route.abort();return
  if state['mode'] in ('timeout','timeout_no_abort'):state['held'].append(route);return
  if state['mode']=='http':route.fulfill(status=400,json={'code':'22023','message':'mock validation failed'});return
  if state['mode']=='invalid_json':route.fulfill(status=200,content_type='application/json',body='not json');return
  if state['mode']=='missing_receipt':route.fulfill(status=200,json={'ok':True});return
  assert UUID.match(pid) or re.match(r'^[0-9a-f-]{36}$',pid,re.I)
  clean={k:v for k,v in body['record'].items() if k!='submission_status'}
  if pid not in state['saved']:
   state['saved'][pid]={'record':clean,'token':body['submission_token'],'receipt':{'ok':True,'participant_id':pid,'receipt_id':'00000000-0000-4000-8000-000000000099','received_at':'2026-11-22T08:11:00.123456+00:00'}}
  saved=state['saved'][pid]
  if saved['record']!=clean or saved['token']!=body['submission_token']:
   route.fulfill(status=400,json={'code':'22023','message':'Submission conflict'});return
  if state['mode']=='lost_receipt':route.abort();state['mode']='normal';return
  route.fulfill(status=200,json=saved['receipt'])
 ctx.route('https://*.supabase.co/**',route_request)
 p=ctx.new_page();errs=[];p.on('pageerror',lambda e:errs.append(type(e).__name__))
 p.goto(BASE+('?preview=1' if preview else ''));p.evaluate(SEED)
 return ctx,p,state,errs

with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True)
 for width in (390,1440):
  for mode in ('normal','no_uuid','native_uuid_throws','no_abort','abort_throws','no_storage','no_storage_network','no_crypto','no_fetch','setup_error','network','http','missing_receipt','invalid_json','timeout','timeout_no_abort'):
   ctx,p,st,errs=case(b,mode,width);before=p.evaluate('buildResults(true)');token=p.evaluate('state.submission.token||null');result=upload(p)
   expected={'no_crypto':'UP_BROWSER','no_fetch':'UP_BROWSER','setup_error':'UP_SETUP','network':'UP_NETWORK','no_storage_network':'UP_NETWORK','http':'UP_HTTP','missing_receipt':'UP_RECEIPT','invalid_json':'UP_RECEIPT','timeout':'UP_TIMEOUT','timeout_no_abort':'UP_TIMEOUT'}.get(mode)
   if expected:
    assert result['status']=='failed' and result['code']==expected,(mode,result)
    assert expected in p.inner_text('#uploadDiagnostic')
    assert '尚未确认上传成功' in p.inner_text('#decisionNotice')
   else:
    assert result['status']=='uploaded',(mode,result)
    assert UUID.match(result['id']);assert len(st['saved'])==1
   verify_backup(p,before)
   with p.expect_download() as download:p.click('#btnDownload')
   backup=json.loads(download.value.path().read_text());assert backup==p.evaluate('state.lastRecord')
   with p.expect_download() as download:p.click('#btnDownloadCsv')
   csv=download.value.path().read_text();assert 'shs01' in csv and 'selected_puzzle_ids' in csv
   if token:assert token not in json.dumps(backup) and token not in csv
   if mode=='no_crypto':
    assert p.evaluate('state.participantId') is None and len(st['posts'])==0
    p.reload();assert p.evaluate('state.demographics.age')==24 and p.evaluate('state.participantId') is None
   for held in st['held']:
    try:held.abort()
    except Exception:pass
   p.unroute_all(behavior='ignoreErrors');ctx.unroute_all(behavior='ignoreErrors');ctx.close()
   assert errs==[],(mode,errs)
   print('PASS',width,mode,flush=True)
 # Narrow legacy migration: preserve answers, condition and original token; migrate once only.
 for mode in ('legacy','valid_existing','accepted_legacy','legacy_receipt','legacy_last_accepted','mismatch','lost_token','unknown_invalid'):
  ctx,p,st,errs=case(b,'normal')
  p.evaluate("mode=>{const old=mode==='valid_existing'?'01234567-89ab-4cde-8fab-0123456789ab':mode==='unknown_invalid'?'unrecognized-invalid-id':'anon-legacy123';state.participantId=old;state.submission.pendingRecord=buildResults(true);state.lastRecord=buildResults(true);if(mode==='accepted_legacy')state.submission.status='uploaded';if(mode==='legacy_receipt')state.submission.receipt={receipt_id:'prior-acceptance'};if(mode==='legacy_last_accepted')state.lastRecord.submission_status='uploaded';if(mode==='mismatch')state.submission.pendingRecord.participant_id='01234567-89ab-4cde-8fab-0123456789ab';if(mode==='lost_token')delete state.submission.token;saveState();}",mode)
  if mode=='lost_token':
   p.reload();assert p.evaluate('state.submission.token||null') is None
  before=p.evaluate('buildResults(true)');old=p.evaluate('state.participantId');token=p.evaluate('state.submission.token||null')
  result=upload(p)
  if mode=='legacy':
   assert UUID.match(result['id']) and result['id']!=old
   assert p.evaluate('state.submission.originalParticipantId')==old
   assert st['posts'][0]['submission_token']==token
   verify_backup(p,before)
   new=result['id'];p.reload();assert p.evaluate('state.participantId')==new
   upload(p);assert len(st['saved'])==1 and len(st['posts'])==1
  elif mode=='valid_existing':assert result['id']==old and result['status']=='uploaded'
  else:
   assert result['id']==old and not st['posts']
   assert result['status']==('uploaded' if mode=='accepted_legacy' else 'failed')
   if mode!='accepted_legacy':assert result['code']=='UP_IDENTITY'
  assert errs==[];ctx.close();print('PASS',mode,flush=True)
 # A committed write with lost acknowledgement must retry frozen answers/token, not create another row.
 ctx,p,st,errs=case(b,'lost_receipt');before=p.evaluate('buildResults(true)');first=upload(p)
 assert first['status']=='failed' and first['code']=='UP_NETWORK' and len(st['saved'])==1
 snapshot=copy.deepcopy(st['posts'][0]);p.reload()
 # A later mutable UI/state change must NOT alter the pending submitted payload.
 p.evaluate("()=>{state.reloadCount+=3;state.scales.shs01=5;}")
 second=upload(p);assert second['status']=='uploaded' and len(st['saved'])==1
 assert st['posts'][0]==st['posts'][1] and st['posts'][1]==snapshot
 assert p.evaluate('state.lastRecord.shs01')==before['shs01']
 for _ in range(3):upload(p)
 assert len(st['posts'])==2;ctx.close();print('PASS lost receipt/reload/frozen snapshot/one stored row',flush=True)
 # An invalid/missing receipt after HTTP 200 also recovers with the same identity and snapshot.
 ctx,p,st,errs=case(b,'missing_receipt');before=p.evaluate('buildResults(true)');first=upload(p);pid=first['id'];body=copy.deepcopy(st['posts'][0])
 st['mode']='normal';second=upload(p);assert second['status']=='uploaded' and second['id']==pid
 assert st['posts'][1]==body and len(st['saved'])==1;ctx.close();print('PASS invalid receipt retry stable',flush=True)
 # A late response after a no-AbortController timeout must not change failed status or duplicate the next retry.
 ctx,p,st,errs=case(b,'timeout_no_abort');result=upload(p);assert result['code']=='UP_TIMEOUT'
 body=copy.deepcopy(st['posts'][0]);pid=body['record']['participant_id']
 receipt={'ok':True,'participant_id':pid,'receipt_id':'00000000-0000-4000-8000-000000000099','received_at':'2026-11-22T08:11:00Z'}
 st['saved'][pid]={'record':{k:v for k,v in body['record'].items() if k!='submission_status'},'token':body['submission_token'],'receipt':receipt}
 st['held'].pop().fulfill(status=200,json=receipt)
 p.evaluate('()=>Promise.resolve()');assert p.evaluate('state.submission.status')=='failed'
 st['mode']='normal';result=upload(p);assert result['status']=='uploaded' and len(st['saved'])==1 and st['posts'][1]==body
 ctx.close();print('PASS late timeout acknowledgement remains duplicate-safe',flush=True)
 # Preview is always local, including if secure crypto is unavailable.
 for mode in ('normal','no_crypto'):
  ctx,p,st,errs=case(b,mode,preview=True);result=upload(p)
  assert result['status']=='local_only' and not st['posts'];assert errs==[];ctx.close()
 print('PASS preview never contacts production',flush=True)
 b.close()
print('PASS all offline upload compatibility, backup, identity and idempotency tests')
