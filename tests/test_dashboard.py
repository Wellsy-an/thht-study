"""Offline synthetic UI/chart/capability-state tests; no production credentials or data used."""
import copy,secrets
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8765/'
def row(n,c,e,h,passed):
 pid='00000000-0000-4000-8000-'+str(n).zfill(12)
 return {'participant_id':pid,'received_at':'2026-11-20T17:00:00Z','receipt_id':'mock-receipt-'+str(n),'payload':{'participant_id':pid,'finish_time':'2026-11-20T17:00:00Z','condition':c,'completion_status':'complete','attention_pass':passed,'thht_easy_count':e,'thht_medium_count':11-e-h,'thht_hard_count':h,'thht_help':e-1,'thht_hurt':h-1,'thht_difference':e-h,'shs_mean':2.5,'perceived_violence':4,'believed_other_participant':'yes','daily_short_video_time':'30_60','age':24}}
with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True)
 for width,height in [(1440,1000),(390,844)]:
  rows=[row(1,'fruit_violent',3,4,True),row(2,'fruit_nonviolent',4,3,False),{'participant_id':'00000000-0000-4000-8000-000000000003','received_at':'2026-11-21T10:00:00Z','receipt_id':'three','payload':{'condition':'fruit_nonviolent','completion_status':'withdrawn_during_study'}}]
  state={'allowed':True};ctx=b.new_context(viewport={'width':width,'height':height},accept_downloads=True);p=ctx.new_page();errors=[]
  p.on('pageerror',lambda e:errors.append(type(e).__name__))
  def handler(route):
   if not state['allowed']:route.fulfill(status=403,json={'message':'Access unavailable'});return
   offset=route.request.post_data_json.get('page_offset',0)
   route.fulfill(status=200,json={'ok':True,'records':rows[offset:offset+500],'total_count':len(rows),'refreshed_at':'2026-11-21T10:00:00Z'})
  p.route('**/rpc/read_dashboard',handler)
  p.goto(BASE);assert p.is_visible('#accessPanel') and not p.is_visible('#workspace')
  assert p.locator('input[type="password"],input[type="email"]').count()==0
  # Random mock capability is accepted only by this offline stub, not the real API.
  p.evaluate("v=>localStorage.setItem('thht_private_management_access',v)",secrets.token_urlsafe(48));p.reload();p.wait_for_selector('#rows tr')
  assert p.locator('#rows tr').count()==3
  assert p.inner_text('#kTotal')=='3' and p.inner_text('#kComplete')=='2' and p.inner_text('#kExit')=='1'
  assert p.inner_text('#kAttention')=='1/2 (50%)'
  assert p.evaluate('charts.thht.data.datasets[0].data')==[2,3]
  assert p.evaluate('charts.thht.data.datasets[1].data')==[3,2]
  assert p.evaluate('charts.thht.data.datasets[2].data')==[-1,1]
  assert p.evaluate('charts.daily.data.labels')==['2026-11-21']
  assert p.evaluate('charts.daily.data.datasets[0].data')==[2]
  assert p.evaluate('Object.keys(charts).length')==8
  assert p.evaluate('document.documentElement.scrollWidth<=window.innerWidth')
  p.locator('#rows tr button').first.click();assert 'mock-receipt-1' in p.inner_text('#recordDetail')
  p.select_option('#condition','fruit_violent');assert p.locator('#rows tr').count()==1
  assert p.evaluate('charts.thht.data.datasets[0].data')==[2,None]
  with p.expect_download() as down:p.click('#csv')
  csv=down.value.path().read_text(encoding='utf-8-sig');assert 'server_receipt_id' in csv and 'thht_difference' in csv and '000000000002' not in csv
  p.select_option('#condition','all');rows.append(row(4,'fruit_violent',3,4,True))
  p.wait_for_function("()=>document.querySelectorAll('#rows tr').length===4",timeout=8000)
  state['allowed']=False;p.click('#refresh');p.wait_for_function("()=>document.querySelector('#workspace').hidden")
  assert p.locator('#rows tr').count()==0 and p.inner_text('#recordDetail')==''
  assert p.evaluate('records.length')==0 and p.evaluate('localStorage.getItem(ACCESS_KEY)') is None
  assert p.is_visible('#accessPanel');assert errors==[]
  ctx.close()
 b.close()
print('PASS synthetic desktop/mobile: no account UI, 8 charts, v7 scoring, UTC+8, null means, filtered export, polling refresh, invalid-access clearing')
