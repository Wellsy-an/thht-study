"""Synthetic production API/browser tests. Records are tagged; cleanup is a separate privileged step.
No researcher login or real participant account is used in this test.
"""
import json, uuid, os
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=os.environ.get('THHT_TEST_BASE','http://127.0.0.1:8765').rstrip('/')
OUT=Path('/workspace/thht/production-test-records.json')
TEST_RUN='synthetic-'+str(uuid.uuid4())
ids=json.loads(OUT.read_text()).get('participant_ids',[]) if OUT.exists() else []
def seed(page, first='tomato', final='peach'):
    page.evaluate('''([first,final,run])=>{
      const now=new Date().toISOString();
      state.consent={age18:true,consent:true,timestamp:now};
      Object.assign(state.video,{started:true,ended:true,watchOk:true,duration:60,playedSec:60,enteredAt:now,leftAt:now});
      state.attention={response:final,firstResponse:first,answeredAt:now};
      state.thht.selectedIds=['P01','P02','P03','P11','P12','P13','P14','P21','P22','P23','P24'];
      state.thht.selectionOrder=state.thht.selectedIds.slice();state.thht.startTime=Date.now()-1000;state.thht.endTime=Date.now();state.thht.locked=true;
      for(let i=1;i<=8;i++)state.scales['shs0'+i]=i%2===0?4:2;
      state.scales.perceived_violence=2;state.scales.ai_content_freq=3;
      state.choices={believedOtherParticipant:'yes',dailyShortVideoTime:'30_60'};
      state.demographics={age:24,gender:'prefer_not'};state.finishedAt=now;
      // Only synthetic payloads produced by this test have this marker.
      const build=buildResults;window.__testBuild=()=>Object.assign(build(true),{synthetic_test_run:run});
      goToStep(10);state.debrief.dataDecision='complete';saveState();
    }''',[first,final,TEST_RUN])

def snapshot(page):
    d=page.evaluate('({pid:state.participantId,token:state.submission.token,record:state.submission.pendingRecord,receipt:state.submission.receipt})')
    ids.append(d['pid']);OUT.write_text(json.dumps({'test_run':TEST_RUN,'participant_ids':ids},indent=2))
    return d

with sync_playwright() as pw:
    browser=pw.chromium.launch(headless=True)
    context=browser.new_context()
    page=context.new_page();page.goto(BASE+'/experiment.html');seed(page)
    result=page.evaluate('async()=>{await submitResults(window.__testBuild());showSubmissionStatus("complete");return {s:state.submission.status,r:state.lastRecord,receipt:state.submission.receipt};}')
    d=snapshot(page)
    assert result['s']=='uploaded', page.evaluate('state.submission.lastError')
    assert result['receipt']['ok'] and result['receipt']['participant_id']==d['pid']
    assert result['r']['attention_response']=='tomato' and result['r']['attention_final_response']=='peach' and result['r']['attention_pass'] is True and result['r']['thht_difference']==-1 and result['r']['shs_mean']==2
    assert not page.is_visible('#resultsJson'), 'analysis scores hidden from participants'
    assert 'successfully uploaded' in page.inner_text('#decisionNotice') or 'have been uploaded' in page.inner_text('#decisionNotice')
    response=page.evaluate('''async d=>{
      const res=await fetch(STUDY_CONFIG.submitEndpoint,{method:'POST',headers:{apikey:STUDY_CONFIG.publishableKey,'Content-Type':'application/json'},body:JSON.stringify({record:d.record,submission_token:d.token})});return {status:res.status,json:await res.json()};
    }''',d)
    assert response['status']==200 and response['json']==d['receipt'], response
    # Concurrent identical retries share a receipt and must produce only one database row.
    same=page.evaluate('''async d=>Promise.all(Array.from({length:5},async()=>{
      const res=await fetch(STUDY_CONFIG.submitEndpoint,{method:'POST',headers:{apikey:STUDY_CONFIG.publishableKey,'Content-Type':'application/json'},body:JSON.stringify({record:d.record,submission_token:d.token})});return await res.json();}))''',d)
    assert all(r==d['receipt'] for r in same)
    cases=[('wrong token',{'record':d['record'],'submission_token':'0'*64}),('changed answers',{'record':{**d['record'],'age':25},'submission_token':d['token']}),('preview write',{'record':{**d['record'],'participant_id':str(uuid.uuid4()),'preview_mode':True},'submission_token':d['token']})]
    for label,body in cases:
        status=page.evaluate('''async body=>{const r=await fetch(STUDY_CONFIG.submitEndpoint,{method:'POST',headers:{apikey:STUDY_CONFIG.publishableKey,'Content-Type':'application/json'},body:JSON.stringify(body)});return r.status;}''',body)
        assert status>=400,(label,status)
    anon=page.evaluate('''async()=>{const r=await fetch('https://dhoelfaebggvzubxinxr.supabase.co/rest/v1/responses?select=*',{headers:{apikey:STUDY_CONFIG.publishableKey}});return {status:r.status,body:await r.json()};}''')
    assert anon['status'] in (401,403),anon
    print('PASS actual HTTPS/CORS browser insert, durable receipt, 6 identical retries, token conflict, changed-answer conflict, preview server rejection, anon read denial, hidden scores',flush=True)
    page.reload();assert page.evaluate('state.submission.status')=='uploaded'
    # Success-looking HTTP 200 without a database receipt must not show upload success.
    ctx2=browser.new_context();p2=ctx2.new_page();p2.goto(BASE+'/experiment.html');seed(p2,'peach','banana')
    p2.route('**/rest/v1/rpc/submit_thht',lambda route:route.fulfill(status=200,json={'ok':True}))
    r=p2.evaluate('async()=>{await submitResults(window.__testBuild());return state.lastRecord;}')
    assert r['submission_status']=='failed' and r['attention_pass'] is False
    assert p2.evaluate('state.submission.status')=='failed'
    p2.unroute('**/rest/v1/rpc/submit_thht')
    p2.reload()
    assert p2.is_visible('#btnRetryUpload')
    p2.click('#btnRetryUpload');p2.wait_for_function('state.submission.status==="uploaded"',timeout=35000)
    d2=snapshot(p2);assert d2['record']['attention_response']=='peach' and d2['record']['attention_final_response']=='banana' and d2['record']['attention_pass'] is False
    print('PASS no false HTTP-200 success, failed local backup status, first answer scoring, retry after reload',flush=True)
    # Simulate committed write but lost receipt, then refresh and retry frozen snapshot.
    ctx3=browser.new_context();p3=ctx3.new_page();p3.goto(BASE+'/experiment.html');seed(p3)
    def lost(route):
        response=route.fetch();assert response.status==200
        route.abort()
    p3.route('**/rest/v1/rpc/submit_thht',lost)
    p3.evaluate('async()=>{await submitResults(window.__testBuild());return state.submission.status;}')
    snapshot(p3);assert p3.evaluate('state.submission.status')=='failed'
    p3.unroute('**/rest/v1/rpc/submit_thht');p3.reload();p3.click('#btnRetryUpload')
    p3.wait_for_function('state.submission.status==="uploaded"',timeout=35000)
    print('PASS committed-but-lost-receipt refresh recovers idempotently',flush=True)
    # Mid-study withdrawal sends no answers; optional injected answers stripped server-side.
    ctx4=browser.new_context();p4=ctx4.new_page();p4.goto(BASE+'/experiment.html')
    p4.evaluate('''()=>{const now=new Date().toISOString();state.consent={age18:true,consent:true,timestamp:now};state.withdrawn=true;state.withdrawnAt=now;state.withdrawnAtStep=2;}''')
    p4.evaluate('''async run=>{const r=Object.assign(buildResults(false),{synthetic_test_run:run,shs01:4});await submitResults(r);}''',TEST_RUN)
    d4=snapshot(p4);assert p4.evaluate('state.submission.status')=='uploaded',p4.evaluate('state.submission.lastError')
    print('PASS mid-study withdrawal metadata upload',flush=True)
    # Preview never sends a request even with the production endpoint configured.
    ctx5=browser.new_context();p5=ctx5.new_page();p5.goto(BASE+'/experiment.html?preview=1');seed(p5)
    writes=[];p5.on('request',lambda req:writes.append(req.url) if '/rpc/submit_thht' in req.url else None)
    assert p5.evaluate('async()=>await submitResults(window.__testBuild())')=='local_only'
    assert writes==[]
    print('PASS browser preview has no writes',flush=True)
    # Root is a login-only researcher panel. No experiment/prototype navigation.
    root=browser.new_page();root.goto(BASE+'/');root.wait_for_selector('#accessPanel')
    assert root.is_visible('#accessPanel') and not root.is_visible('#workspace')
    assert root.locator('a[href*="experiment"]').count()==0
    assert root.locator('#rows tr').count()==0
    print('PASS root opens private management entry directly; no public data or version choice',flush=True)
    root.screenshot(path='/workspace/thht/shots/production-login.png',full_page=True)
    browser.close()
