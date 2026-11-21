"""Offline synthetic dashboard UI/visualization tests; does not create Auth users or send email."""
import json
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8765/'
MOCK=r'''
let onAuth;
window.mockRows=[
{participant_id:'00000000-0000-4000-8000-000000000001',received_at:'2026-11-20T17:00:00Z',receipt_id:'receipt-one',payload:{participant_id:'00000000-0000-4000-8000-000000000001',finish_time:'2026-11-20T17:00:00Z',condition:'fruit_violent',completion_status:'complete',attention_pass:true,thht_easy_count:3,thht_medium_count:4,thht_hard_count:4,thht_help:2,thht_hurt:3,thht_difference:-1,shs_mean:2.5,perceived_violence:4,believed_other_participant:'yes',daily_short_video_time:'30_60',age:24}},
{participant_id:'00000000-0000-4000-8000-000000000002',received_at:'2026-11-21T10:00:00Z',receipt_id:'receipt-two',payload:{participant_id:'00000000-0000-4000-8000-000000000002',finish_time:'2026-11-21T10:00:00Z',condition:'fruit_nonviolent',completion_status:'complete',attention_pass:false,thht_easy_count:4,thht_medium_count:4,thht_hard_count:3,thht_help:3,thht_hurt:2,thht_difference:1,shs_mean:1.5,perceived_violence:1,believed_other_participant:'not_sure',daily_short_video_time:'1_2h',age:22}},
{participant_id:'00000000-0000-4000-8000-000000000003',received_at:'2026-11-21T10:10:00Z',receipt_id:'receipt-three',payload:{condition:'fruit_nonviolent',completion_status:'withdrawn_during_study'}}];
window.mockAllowed=true;window.mockLive=null;
window.supabase={createClient:()=>({
  rpc:async()=>({data:window.mockAllowed,error:null}),
  from:()=>({select(){return this},order(){return this},range:async(a,b)=>({data:window.mockRows.slice(a,b+1),error:null})}),
  channel:()=>({on(event,opts,callback){window.mockLive=callback;return this},subscribe(callback){setTimeout(()=>callback('SUBSCRIBED'),10);return this}}),
  removeChannel:async()=>{},
  auth:{onAuthStateChange(callback){onAuth=callback;setTimeout(()=>callback('INITIAL_SESSION',null),0)},signInWithPassword:async()=>{onAuth('SIGNED_IN',{user:{id:'test-only'}});return {error:null}},signOut:async()=>{onAuth('SIGNED_OUT',null);return {error:null}}}
})};
'''
with sync_playwright() as pw:
    b=pw.chromium.launch(headless=True)
    for viewport in [{'width':1440,'height':1000},{'width':390,'height':844}]:
        ctx=b.new_context(viewport=viewport,accept_downloads=True);p=ctx.new_page();errors=[]
        p.on('pageerror',lambda e:errors.append(str(e)))
        p.route('**/vendor/supabase.js',lambda route:route.fulfill(status=200,content_type='application/javascript',body=MOCK))
        p.goto(BASE);assert p.is_visible('#loginPanel');assert not p.is_visible('#workspace')
        # Tests call the mock Auth state callback, not a real sign-in or email address.
        p.evaluate("onAuth('SIGNED_IN',{user:{id:'test-only'}})")
        p.wait_for_selector('#rows tr');assert p.locator('#rows tr').count()==3
        assert p.inner_text('#kTotal')=='3' and p.inner_text('#kComplete')=='2' and p.inner_text('#kExit')=='1'
        assert p.inner_text('#kAttention')=='1/2 (50%)'
        assert p.evaluate('charts.thht.data.datasets[0].data')==[2,3]
        assert p.evaluate('charts.thht.data.datasets[1].data')==[3,2]
        assert p.evaluate('charts.thht.data.datasets[2].data')==[-1,1]
        assert p.evaluate('charts.daily.data.labels')==['2026-11-21'], 'Shanghai day conversion'
        assert p.evaluate('charts.daily.data.datasets[0].data')==[2]
        assert p.evaluate('Object.keys(charts).length')==8
        assert p.evaluate('document.documentElement.scrollWidth<=window.innerWidth'), 'no page-width overflow'
        p.locator('#rows tr button').first.click();assert 'receipt-one' in p.inner_text('#recordDetail')
        p.select_option('#condition','fruit_violent');assert p.locator('#rows tr').count()==1
        assert p.evaluate('charts.thht.data.datasets[0].data')==[2,None], 'empty group is null not zero'
        with p.expect_download() as down:p.click('#csv')
        path=down.value.path();csv=path.read_text(encoding='utf-8-sig')
        assert 'server_receipt_id' in csv and 'thht_difference' in csv and '000000000002' not in csv
        p.select_option('#condition','all')
        # A real INSERT event invokes the same refresh path; this tests the UI callback offline.
        p.evaluate("mockRows.push({...mockRows[0],participant_id:'00000000-0000-4000-8000-000000000004'});mockLive()")
        p.wait_for_function("document.querySelectorAll('#rows tr').length===4")
        p.screenshot(path=f'/workspace/thht/shots/production-dashboard-{viewport["width"]}.png',full_page=True)
        # Revoke authorization during an active session: records and table must disappear.
        p.evaluate('mockAllowed=false;loadRecords()');p.wait_for_function("document.querySelector('#workspace').hidden")
        assert p.locator('#rows tr').count()==0 and p.inner_text('#recordDetail')==''
        assert p.evaluate('records.length')==0
        p.click('#logout');p.wait_for_selector('#loginPanel')
        assert errors==[],errors
        ctx.close()
    b.close()
print('PASS dashboard desktop/mobile: login-only root, allowlist gating, 8 charts, v7 scores, UTC+8, null means, filter/export, INSERT refresh, revoke/logout clearing; synthetic mock transport only')
