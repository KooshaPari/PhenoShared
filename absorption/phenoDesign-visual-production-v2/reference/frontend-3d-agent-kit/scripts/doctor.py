#!/usr/bin/env python3
"""Read-only local capability probe. No installs, model downloads or network calls."""
from __future__ import annotations
import argparse, json, platform, shutil, subprocess, sys
from pathlib import Path

def probe(name,args):
    path=shutil.which(name)
    if not path:return {'available':False}
    try:
        p=subprocess.run([path,*args],capture_output=True,text=True,timeout=12,check=False)
        return dict(available=True,path=path,returncode=p.returncode,version=(p.stdout or p.stderr).strip()[:1000])
    except (OSError,subprocess.TimeoutExpired) as e:return dict(available=True,path=path,error=str(e))
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path);a=ap.parse_args()
    report=dict(platform=platform.system(),machine=platform.machine(),python=sys.version.split()[0],tools={name:probe(name,args) for name,args in [('blender',['--version']),('node',['--version']),('npm',['--version']),('bun',['--version']),('uv',['--version']),('ffmpeg',['-version']),('nvidia-smi',['--query-gpu=name,memory.total,memory.free','--format=csv,noheader'])]},warning='Reported memory is a point-in-time observation, not a render reservation. Metal/CUDA capabilities require an actual workload test.')
    text=json.dumps(report,indent=2);print(text)
    if a.out:
        if a.out.exists():ap.error('Refusing existing report')
        a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(text,encoding='utf-8')
if __name__=='__main__':main()
