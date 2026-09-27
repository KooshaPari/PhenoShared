#!/usr/bin/env python3
"""Bounded local capability probe. Does not install tools, launch GUI apps, or claim a native worker is usable."""
import json, platform, shutil, subprocess, sys
from pathlib import Path
TOOLS={'node':['--version'],'bun':['--version'],'python':['--version'],'blender':['--version'],'ffmpeg':['-version'],'ffprobe':['-version'],'inkscape':['--version'],'magick':['-version'],'rive':['--version']}
result={'platform':platform.platform(),'python':sys.version,'cli':{},'adobe':{'installation':'USER_REPORTED','session':'UNQUALIFIED','hostAutomation':'NOT_EXECUTED'}}
for name,args in TOOLS.items():
 exe=shutil.which(name)
 if not exe:result['cli'][name]={'status':'NOT_FOUND'};continue
 try:
  p=subprocess.run([exe,*args],capture_output=True,text=True,timeout=8)
  result['cli'][name]={'path':exe,'exit':p.returncode,'output':(p.stdout+p.stderr)[:1600],'status':'VERSION_PROBED' if p.returncode==0 else 'PROBE_FAILED'}
 except (OSError,subprocess.TimeoutExpired) as e:result['cli'][name]={'status':'PROBE_FAILED','message':str(e)}
print(json.dumps(result,indent=2))
