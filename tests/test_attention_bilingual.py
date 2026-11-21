"""Native DOM bilingual rendering and scoped translation protection. Preview creates no records."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE=os.environ.get('THHT_TEST_BASE','http://127.0.0.1:8765').rstrip('/')
with sync_playwright() as pw:
 b=pw.chromium.launch(headless=True)
 for w,h in [(1440,1000),(390,844)]:
  ctx=b.new_context(viewport={'width':w,'height':h});p=ctx.new_page();p.goto(BASE+'/experiment.html?preview=1')
  p.evaluate('goToStep(3)')
  assert p.locator('#attnQuestion [lang="en"]').inner_text()=='What kind of fruit is wearing a wedding dress in the video?'
  assert p.locator('#attnQuestion [lang="zh-Hans"]').inner_text()=='视频中穿婚纱的是哪一种水果？'
  assert p.locator('#attnQuestion').get_attribute('translate')=='no'
  ens=p.locator('#objectOptions [lang="en"]').all_inner_texts();zhs=p.locator('#objectOptions [lang="zh-Hans"]').all_inner_texts()
  assert ens==['Banana','Tomato','Peach','Blueberry'];assert zhs==['香蕉','番茄','桃子','蓝莓']
  assert p.locator('#objectOptions .notranslate[translate="no"]').count()==4
  # Chinese line must be below its English line, not inline or duplicated English.
  for label in p.locator('#objectOptions label').all():
   en=label.locator('[lang="en"]').bounding_box();zh=label.locator('[lang="zh-Hans"]').bounding_box();assert zh['y']>en['y']
  assert p.evaluate("Object.values(STUDY_CONFIG.videos).every(v=>v.attentionCorrectOptionId==='tomato')")
  p.locator('section[data-step="3"]').screenshot(path=f'/workspace/thht/shots/bilingual-attention-{w}.png')
  ctx.close()
 b.close()
print('PASS desktop/mobile literal EN/ZH question and 4 option pairs on separate lines; scoped notranslate/lang attributes; tomato key unchanged')
