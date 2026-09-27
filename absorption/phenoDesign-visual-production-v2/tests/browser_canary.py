#!/usr/bin/env python3
"""Real isolated browser exercise of the SVG canary. Not a Remotion/Adobe/GPU qualification."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
checks=[]
HTML=(ROOT/'examples/vector-prop/index.html').read_text()
def check(name,condition):
 checks.append({'name':name,'status':'PASS' if condition else 'FAIL'})
 if not condition:raise AssertionError(name)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=os.environ.get('PD_CHROMIUM','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
 try:
  context=browser.new_context(viewport={'width':1280,'height':960},reduced_motion='no-preference')
  page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.set_content(HTML,wait_until="load");page.get_by_role('heading',name='A vector with a real input contract.').wait_for()
  check('initial state text',page.locator('#value').inner_text()=='50%')
  check('initial state geometry',page.locator('#needle').get_attribute('data-value')=='50')
  page.locator('#intensity').focus();page.keyboard.press('ArrowRight')
  check('native keyboard input',page.locator('#value').inner_text()=='51%')
  page.locator('#intensity').fill('100')
  check('upper bound state',page.locator('#needle').get_attribute('data-value')=='100')
  check('geometry rotation updated','135deg' in page.locator('#needle').get_attribute('style'))
  page.locator('#intensity').fill('0')
  check('reverse input',page.locator('#value').inner_text()=='0%')
  page.get_by_role('button',name='Copper',exact=True).click()
  check('material control state',page.locator('#copper').get_attribute('aria-pressed')=='true')
  check('material changes SVG bytes',page.locator('#accent').get_attribute('stroke')=='#a74e29')
  page.get_by_role('button',name='Disable interpolation').click()
  check('pause/interpolation control',page.locator('body').evaluate('(e)=>e.classList.contains("motion-off")'))
  page.get_by_role('button',name='Reset',exact=True).click()
  check('reset',page.locator('#value').inner_text()=='50%' and page.locator('#teal').get_attribute('aria-pressed')=='true')
  for _ in range(100):
   settled=page.locator('#needle').evaluate('(e)=>{const m=new DOMMatrix(getComputedStyle(e).transform);return Math.abs(m.a-1)<0.0001&&Math.abs(m.b)<0.0001}')
   if settled:break
   page.wait_for_timeout(20)
  check('settled geometry matches value',page.locator('#needle').evaluate('(e)=>Math.abs(new DOMMatrix(getComputedStyle(e).transform).a-1)<0.0001'))
  page.screenshot(path=str(ROOT/'evidence/vector-desktop.png'),full_page=True)
  check('no uncaught browser errors',not errors)
  context.close()
  context=browser.new_context(viewport={'width':390,'height':844},reduced_motion='reduce',is_mobile=True,has_touch=True)
  page=context.new_page();page.set_content(HTML,wait_until="load")
  check('reduced motion recognized','Reduced motion' in page.locator('#mode').inner_text())
  check('reduced motion interpolation disabled',page.locator('#needle').evaluate('(e)=>getComputedStyle(e).transitionDuration')=='0s')
  check('no mobile horizontal overflow',page.evaluate('document.documentElement.scrollWidth <= innerWidth'))
  page.screenshot(path=str(ROOT/'evidence/vector-mobile.png'),full_page=True)
  context.close()
  context=browser.new_context(viewport={'width':390,'height':844},java_script_enabled=False)
  page=context.new_page();page.set_content(HTML,wait_until="load")
  check('no-script fallback present',page.locator('noscript').inner_text().startswith('Static preview.'))
  check('no-script illustration remains',page.locator('svg').is_visible())
  page.screenshot(path=str(ROOT/'evidence/vector-no-js.png'),full_page=True)
  context.close()
 finally:
  browser.close()
(ROOT/'evidence/browser-checks.json').write_text(json.dumps({'target':'standalone SVG canary loaded with set_content; navigation is blocked by browser environment policy','browser':'Chromium, installed executable','checks':checks,'not_covered':['Remotion runtime','native Adobe','Blender','physical mobile hardware','screen reader user evaluation']},indent=2)+'\n')
print(f'{len(checks)} browser checks passed')
