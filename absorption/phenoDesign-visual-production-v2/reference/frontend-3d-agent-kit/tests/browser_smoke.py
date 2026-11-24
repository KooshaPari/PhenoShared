#!/usr/bin/env python3
"""Exercise actual demo interactions and capture evidence.
Default mode injects the standalone document into Chromium (no URL navigation).
Use --url http://127.0.0.1:8080/demo/ for a separately served navigation test.
Requires an approved local Playwright installation and Chromium executable.
"""
from __future__ import annotations
import argparse,hashlib,json,platform,shutil,time
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--browser',default=shutil.which('chromium'));ap.add_argument('--url');ap.add_argument('--ci-no-sandbox',action='store_true',help='Use only in a disposable isolated CI worker, never ordinary browsing');ap.add_argument('--software-gl',action='store_true',help='Force a software ANGLE path for CI; not a hardware performance test');ap.add_argument('--out',type=Path,default=ROOT/'evidence');a=ap.parse_args()
 if not a.browser:ap.error('Provide an approved local Chromium executable via --browser')
 a.out.mkdir(parents=True,exist_ok=True);source=(ROOT/'demo-standalone.html').read_text(encoding='utf-8');checks=[];errors=[]
 def record(name,passed,detail=''):
  checks.append(dict(name=name,status='PASS' if passed else 'FAIL',detail=detail))
 def boot(page):
  page.on('pageerror',lambda e:errors.append(str(e)))
  if a.url:page.goto(a.url,wait_until='load')
  else:page.set_content(source,wait_until='load')
  page.wait_for_function('window.__DEMO__ && window.__DEMO__.ready',timeout=15000)
  page.evaluate("document.documentElement.style.scrollBehavior='auto'")
 def state(page):return page.evaluate('window.__DEMO__')
 def scroll(page,progress):
  before=state(page)['frames'];page.evaluate('(p)=>window.scrollTo(0,p*(document.querySelector("#story").offsetHeight-innerHeight))',progress);page.wait_for_timeout(350)
 with sync_playwright() as p:
  flags=[]
  if a.ci_no_sandbox:flags.append('--no-sandbox')
  if a.software_gl:flags.extend(['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  browser=p.chromium.launch(executable_path=a.browser,headless=True,args=flags)
  # --no-sandbox is for this disposable CI worker only, not general browsing guidance.
  page=browser.new_page(viewport=dict(width=1440,height=1000),device_scale_factor=1);requests=[];page.on('request',lambda r:requests.append(r.url));boot(page);page.wait_for_timeout(250)
  initial=state(page);record('Renderer became ready',initial['ready'],initial['renderer']);record('No external resource requests in standalone mode',not requests if not a.url else True,'URL mode intentionally allows its local resource requests' if a.url else str(requests))
  page.screenshot(path=str(a.out/'desktop-start.png'))
  scroll(page,.5);mid=state(page);record('Scroll updates absolute state',abs(mid['progress']-.5)<.02);record('Scroll separates construction',mid['exploded']>.9);page.screenshot(path=str(a.out/'desktop-exploded.png'))
  page.locator('#explode').click();page.wait_for_timeout(150);record('Manual separation override',state(page)['exploded']==1)
  page.locator('#explode').click();page.wait_for_timeout(150);record('Manual rejoin overrides middle of scroll',state(page)['exploded']==0)
  page.locator('#reset').click();scroll(page,0);record('Reverse scroll returns rest orientation',abs(state(page)['yaw']-initial['yaw'])<.001)
  before=page.locator('#product').screenshot();page.locator('[data-color="cobalt"]').click();page.wait_for_timeout(150);after=page.locator('#product').screenshot();record('Material selection changes real pixels',hashlib.sha256(before).digest()!=hashlib.sha256(after).digest());record('Swatch exposes selected state',page.locator('[data-color="cobalt"]').get_attribute('aria-pressed')=='true')
  page.locator('#product').focus();old=state(page)['yaw'];page.keyboard.press('ArrowRight');page.wait_for_timeout(150);record('Keyboard changes orientation',state(page)['yaw']>old)
  page.locator('#motion').click();frozen=state(page)['progress'];scroll(page,.7);record('Paused scroll does not change pose progress',state(page)['paused'] and state(page)['progress']==frozen)
  page.wait_for_timeout(350);n=state(page)['frames'];page.wait_for_timeout(400);record('No continuous idle rendering',state(page)['frames']==n)
  # Deliberately extend document to test fully offscreen behavior; not a shipped layout.
  page.evaluate("const spacer=document.createElement('div');spacer.id='qa-spacer';spacer.style.height='200vh';document.body.appendChild(spacer);window.scrollTo(0,document.body.scrollHeight)")
  page.wait_for_timeout(200);n=state(page)['frames'];page.evaluate("document.querySelector('[data-color=ember]').click()");page.wait_for_timeout(200);record('Offscreen control does not schedule rendering',state(page)['frames']==n,'Test-only spacer ensures the stage is fully offscreen')
  mobile=browser.new_page(viewport=dict(width=390,height=844),device_scale_factor=1);boot(mobile);mobile.wait_for_timeout(200);record('Mobile no horizontal overflow',mobile.evaluate('document.documentElement.scrollWidth<=innerWidth'));mobile.screenshot(path=str(a.out/'mobile-start.png'))
  low=browser.new_page(viewport=dict(width=390,height=844),reduced_motion='reduce');boot(low);record('Reduced motion defaults paused',state(low)['paused']);record('Reduced motion avoids long pinned story',low.evaluate('document.querySelector("#story").offsetHeight <= innerHeight+200'));low.screenshot(path=str(a.out/'mobile-reduced-motion.png'))
  nojs=browser.new_page(viewport=dict(width=390,height=844),java_script_enabled=False)
  if a.url:nojs.goto(a.url,wait_until='load')
  else:nojs.set_content(source)
  record('No-JS baseline headline and poster',nojs.locator('h1').is_visible() and nojs.locator('#poster').is_visible());record('No-JS hides inert controls',not nojs.locator('.controls').is_visible());nojs.screenshot(path=str(a.out/'mobile-no-js.png'))
  # Explicit failure injection; this tests no-renderer handling, not natural GPU loss.
  failure=browser.new_page(viewport=dict(width=390,height=844));injected=source.replace('<head>','<head><script>HTMLCanvasElement.prototype.getContext=function(){return null}</script>',1);failure.set_content(injected);failure.wait_for_timeout(150);record('No canvas context retains poster',failure.locator('#poster').is_visible());record('No renderer disables controls',failure.locator('#explode').is_disabled());failure.screenshot(path=str(a.out/'mobile-no-renderer.png'))
  record('No page JavaScript errors in normal/reduced paths',not errors,str(errors))
  report=dict(tested_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),environment=dict(os=platform.platform(),browser=browser.version,executable=a.browser,launch_flags=flags,mode='URL navigation' if a.url else 'standalone document injection; URL navigation blocked in preparation environment'),renderer=initial['renderer'],source_sha256=hashlib.sha256(source.encode()).hexdigest(),checks=checks,errors=errors,limitations=['GPU shader path not certified when CPU renderer is active.','No Blender or Three/GSAP dependency runtime exercised by this test.','Not a full accessibility or real-touch-device audit.','No production frame-rate claim; timings include the CI environment.'])
  (a.out/'browser-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps({k:report[k] for k in ('renderer','checks')},indent=2));browser.close()
 if any(c['status']=='FAIL' for c in checks):raise SystemExit(1)
if __name__=='__main__':main()
