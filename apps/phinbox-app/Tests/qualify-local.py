#!/usr/bin/env python3
"""Actual candidate CLI + daemon + Swift transport, synthetic isolated state only."""
import argparse,hashlib,json,os,subprocess,time,urllib.request,urllib.error
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--cli',type=Path,required=True);p.add_argument('--swift-tests',type=Path,required=True);p.add_argument('--evidence',type=Path,required=True);a=p.parse_args()
app=Path(__file__).resolve().parents[1];root=a.evidence/'queue';root.mkdir(parents=True,exist_ok=True)
env=dict(os.environ)
for key in ['PHINBOX_INBOX_DIR','PHINBOX_PORT','PHINBOX_NOTIFY_NATIVE','PHINBOX_AUTO_OPEN_BROWSER','PHINBOX_IMESSAGE_TARGET','PHINBOX_EMAIL_TARGET','PHINBOX_WEBHOOK_URL','PHINBOX_NOTIFY']:env.pop(key,None)
log=(a.evidence/'daemon.log').open('w')
child=subprocess.Popen([str(a.cli),'--inbox-dir',str(root),'daemon','--port','0','--no-tray'],stdout=log,stderr=subprocess.STDOUT,env=env)
def cli(*args):return json.loads(subprocess.check_output([str(a.cli),'--inbox-dir',str(root),*args],env=env,text=True))
def post(rid,body):
 req=urllib.request.Request(endpoint+'/inbox/'+rid+'/answer',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
 try:
  with urllib.request.urlopen(req,timeout=5) as response:return response.status
 except urllib.error.HTTPError as e:return e.code
try:
 for _ in range(100):
  if (root/'daemon.lock').exists():break
  if child.poll() is not None:raise RuntimeError('candidate daemon exited')
  time.sleep(.05)
 lock=json.loads((root/'daemon.lock').read_text());endpoint='http://127.0.0.1:'+str(lock['port'])
 assert lock['port']!=7117
 spec={'title':'Synthetic native approval','question':'This exercises candidate state only.','field':{'kind':'boolean','label':'Confirm','default':True},'buttons':{'cancel':'Decline','confirm':'Record','default_is_cancel':True,'defer_label':'Later'},'details':{'command':'synthetic-command','reason':'candidate-only','items':[{'kind':'file','path':'synthetic-file','action':'read'}],'effects':['synthetic-effect']},'timeout_secs':600}
 for rid in ['native-confirm','native-cancel','native-defer','web-details']:
  cli('ask','--async','--from-json',json.dumps(spec|{'request_id':rid}))
 html=urllib.request.urlopen(endpoint+'/inbox/web-details',timeout=5).read().decode()
 assert all(s in html for s in ['synthetic-command','synthetic-file','synthetic-effect','name=defer','formnovalidate','Decline'])
 swift=subprocess.check_output([str(a.swift_tests),str(app/'Tests/fixtures/rust-schema.json'),endpoint,str(root)],text=True,env=env,timeout=30)
 assert post('native-confirm',{'confirm':'ok','value':'false'})==409
 assert not (root/'answered/native-defer.json').exists()
 cli('answer','--request-id','native-defer','--boolean','false')
 waited=cli('wait','--request-id','native-defer')
 assert 'false' in json.dumps(waited)
 integer=spec|{'request_id':'integer-bounds','field':{'kind':'integer','label':'Count','min':1,'max':5,'default':2}}
 cli('ask','--async','--from-json',json.dumps(integer))
 assert post('integer-bounds',{'confirm':'ok','value':'99'})==400
 assert post('integer-bounds',{'confirm':'ok','value':'3'})==200
 notes=spec|{'request_id':'cancel-required-notes','notes':{'label':'Reason','required':True}}
 cli('ask','--async','--from-json',json.dumps(notes))
 assert post('cancel-required-notes',{'cancel':'1'})==200
 expiry=spec|{'request_id':'expired','timeout_secs':1}
 cli('ask','--async','--from-json',json.dumps(expiry));time.sleep(1.2)
 assert post('expired',{'confirm':'ok','value':'true'})==410
 assert not (root/'answered/expired.json').exists()
 receipt={'record_class':'EXECUTED_PRODUCT_CANDIDATE','scope':'synthetic isolated local CLI/daemon/web/Swift transport','root':str(root),'endpoint':endpoint,'pid':child.pid,'binary_sha256':hashlib.sha256(a.cli.read_bytes()).hexdigest(),'checks':['native typed true','native cancellation','native durable defer then CLI answer/wait','alternate root and ephemeral port','rich web details/custom buttons/defer','duplicate answer409','integer bounds400/valid200','cancel bypasses required notes','authoritative expiry410'],'swift_stdout':swift.strip(),'shared_state_modified':False,'gui_exercised':False,'user_accepted':None}
 (a.evidence/'local-journey.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
finally:
 child.terminate()
 try:child.wait(timeout=5)
 except subprocess.TimeoutExpired:child.kill();child.wait(timeout=5)
 log.close()
