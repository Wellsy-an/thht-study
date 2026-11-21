"""Offline regressions for the hosted-page blank-state failure paths. No real records/tokens."""
import hashlib,base64,re,secrets,json
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:8765/'
ROOT=Path(__file__).resolve().parents[1]
CHART=(ROOT/'vendor/chart.umd.min.js').read_text()
SAMPLE={'participant_id':'00000000-0000-4000-8000-000000000001','receipt_id':'synthetic-only','received_at':'2026-11-21T17:00:00Z','payload':{'participant_id':'00000000-0000-4000-8000-000000000001','condition':'fruit_violent','completion_status':'complete','finish_time':'2026-11-21T17:00:00Z','attention_pass':True,'thht_easy_count':3,'thht_medium_count':4,'thht_hard_count':4,'thht_help':2,'thht_hurt':3,'thht_difference':-1,'shs_mean':2.5,'perceived_violence':2,'age':24}}
html=(ROOT/'index.html').read_text();script=(ROOT/'dashboard.js').read_text()
assert html==(ROOT/'dashboard.html').read_text()
assert script in html and (ROOT/'dashboard.css').read_text() in html
assert "'sha256-"+base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()+"'" in html
assert 'src="dashboard.js"' not in html and 'href="dashboard.css"' not in html

def open_case(browser,mode,width=390):
 ctx=browser.new_context(viewport={'width':width,'height':844},accept_downloads=True)
 token=secrets.token_urlsafe(48);ctx.add_init_script("localStorage.setItem('thht_private_management_access',"+json.dumps(token)+")")
 if mode=='legacy':ctx.add_init_script("Object.defineProperty(AbortSignal,'timeout',{value:undefined});Array.prototype.at=undefined;String.prototype.replaceAll=undefined;window.AbortController=undefined;")
 if mode=='storage':ctx.add_init_script("Storage.prototype.getItem=function(){throw Error('denied')};Storage.prototype.setItem=function(){throw Error('denied')};")
 if mode=='history':ctx.add_init_script("history.replaceState=function(){throw Error('denied')}")
 if mode=='timeout':ctx.add_init_script("const nativeSetTimeout=window.setTimeout;window.setTimeout=function(f,n){return nativeSetTimeout(f,n===20000?200:n)};")
 p=ctx.new_page();errors=[];p.on('pageerror',lambda e:errors.append(type(e).__name__))
 state={'api':'ok','rows':[SAMPLE],'calls':0,'held':[]}
 def api(route):
  state['calls']+=1
  assert route.request.post_data_json['management_token']==token
  if state['api']=='fail':route.abort();return
  if state['api']=='hang':state['held'].append(route);return
  if state['api']=='invalid':route.fulfill(status=403,json={'message':'invalid'});return
  route.fulfill(status=200,json={'ok':True,'records':state['rows'],'refreshed_at':'2026-11-21T17:00:00Z'})
 p.route('**/rpc/read_dashboard',api)
 # These critical external assets may fail on the user's network; now no request is needed.
 p.route('**/dashboard.js',lambda route:route.abort());p.route('**/dashboard.css',lambda route:route.abort())
 if mode=='blocked-chart':p.route('**/vendor/chart.umd.min.js',lambda route:route.abort())
 if mode=='throwing-chart':p.route('**/vendor/chart.umd.min.js',lambda route:route.fulfill(content_type='text/javascript',body="window.Chart=function(){throw Error('synthetic canvas failure')};Chart.defaults={font:{}};"))
 if mode=='delayed-chart':p.route('**/vendor/chart.umd.min.js',lambda route:state['held'].append(route))
 if mode=='failed-api':state['api']='fail'
 if mode=='timeout':state['api']='hang'
 if mode=='empty':state['rows']=[]
 p.goto(BASE+('#manage='+token if mode in ('storage','history') else ''),wait_until='domcontentloaded')
 return ctx,p,state,errors

with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True)
 for width in (390,1440):
  for mode in ('blocked-chart','throwing-chart','legacy','storage','failed-api','empty','delayed-chart'):
   ctx,p,state,errors=open_case(b,mode,width)
   if mode=='failed-api':
    p.wait_for_selector('#retry');assert '无法连接数据服务' in p.inner_text('#message')
    assert not p.is_visible('#workspace') and not p.is_visible('#accessPanel')
    p.screenshot(path=f'/workspace/thht/shots/dashboard-retry-{width}.png',full_page=True)
    state['api']='ok';p.click('#retry')
   p.wait_for_selector('#workspace')
   assert p.inner_text('#kTotal')==('0' if mode=='empty' else '1')
   assert p.evaluate('location.hash')==''
   assert not p.is_visible('#startupNotice') and not p.is_visible('#retry')
   assert p.locator('input[type="password"],input[type="email"]').count()==0
   if mode=='empty':
    assert p.is_visible('#emptyState');assert p.locator('#rows tr').count()==0
    p.wait_for_function('()=>Object.keys(charts).length===8')
    p.screenshot(path=f'/workspace/thht/shots/dashboard-empty-{width}.png',full_page=width==1440)
   elif mode in ('blocked-chart','throwing-chart'):
    p.wait_for_selector('#chartError');assert p.locator('#rows tr').count()==1
    with p.expect_download() as down:p.click('#csv')
    assert 'synthetic-only' in down.value.path().read_text(encoding='utf-8-sig')
   else:
    if mode=='delayed-chart':
     assert p.locator('#rows tr').count()==1 and p.is_visible('#chartLoading')
     assert len(state['held'])==1
     state['held'].pop().fulfill(content_type='text/javascript',body=CHART)
    p.wait_for_function('()=>Object.keys(charts).length===8')
    assert p.evaluate('charts.daily.data.labels')==['2026-11-22']
    # Chart rendering failure must not prevent records or exports on later refreshes.
    p.evaluate("()=>{charts.daily.update=function(){throw Error('synthetic chart update failure')}}")
    p.click('#refresh');p.wait_for_selector('#chartError')
    assert p.locator('#rows tr').count()==1
   assert errors==[],(mode,errors)
   assert p.evaluate('document.documentElement.scrollWidth<=innerWidth')
   if mode!='storage':
    state['api']='invalid';p.click('#refresh');p.wait_for_selector('#accessPanel')
    assert not p.is_visible('#workspace') and p.locator('#rows tr').count()==0
    assert p.evaluate('localStorage.getItem(ACCESS_KEY)') is None
   ctx.close()
   print(f'PASS {width}px {mode}',flush=True)
 # A browser that denies History API access gets visible guidance without requesting data.
 ctx,p,state,errors=open_case(b,'history')
 assert p.is_visible('#startupNotice') and '此浏览器未能启动面板' in p.inner_text('#message')
 assert not p.is_visible('#workspace') and state['calls']==0 and errors==[];ctx.close()
 print('PASS startup exception renders guidance without reading protected records',flush=True)
 # Test timed-out fetch, not just an immediately failed connection. No production waits/writes.
 ctx,p,state,errors=open_case(b,'timeout');p.wait_for_selector('#retry')
 assert '无法连接数据服务' in p.inner_text('#message')
 for held in state['held']:
  try:held.abort()
  except Exception:pass  # The client may have already aborted this synthetic hung request.
 state['held'].clear()
 state['api']='ok';p.click('#retry');p.wait_for_selector('#workspace');assert errors==[]
 p.unroute_all(behavior='ignoreErrors');ctx.close()
 print('PASS request timeout surfaces recovery and retry succeeds',flush=True)
 ctx=b.new_context(java_script_enabled=False,viewport={'width':390,'height':844});p=ctx.new_page()
 p.goto(BASE);assert p.is_visible('#startupNotice') and '请启用 JavaScript' in p.inner_text('body')
 assert not p.is_visible('#workspace');p.screenshot(path='/workspace/thht/shots/dashboard-no-javascript.png',full_page=True);ctx.close()
 b.close()
print('PASS self-contained assets + CSP hash, desktop/mobile fallback, delayed/broken charts, legacy APIs, storage denial, network failure/retry, timeout, explicit empty state and JS-disabled guidance')
