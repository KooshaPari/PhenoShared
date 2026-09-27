#!/usr/bin/env python3
"""Dry-run by default. Start a bounded, fresh Blender process to build the trainer.
This is process hygiene, NOT an OS sandbox. Grant no sensitive home/network access.
"""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def command(binary: str, output: Path, threads: int, render: bool) -> list[str]:
    cmd=[binary,'--background','--factory-startup','--disable-autoexec','--threads',str(threads),'--python-exit-code','1','--python',str(ROOT/'blender/build_product.py'),'--','--output',str(output)]
    if render:cmd.append('--render')
    return cmd

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--blender',default=shutil.which('blender'));ap.add_argument('--output',type=Path,default=ROOT/'build/trainer-v1');ap.add_argument('--threads',type=int,default=4);ap.add_argument('--timeout',type=int,default=600);ap.add_argument('--render',action='store_true');ap.add_argument('--run',action='store_true');a=ap.parse_args()
    if not 1<=a.threads<=16 or not 10<=a.timeout<=3600:ap.error('threads must be 1..16; timeout 10..3600 seconds')
    output=a.output.resolve();cmd=command(a.blender or '<ABSOLUTE_BLENDER_EXECUTABLE>',output,a.threads,a.render)
    print(json.dumps(dict(mode='RUN' if a.run else 'DRY_RUN',argv=cmd,timeout_seconds=a.timeout),indent=2))
    if not a.run:return
    if not a.blender or not Path(a.blender).is_file():ap.error('Blender executable missing. Provide --blender with an absolute executable path.')
    if output.exists():ap.error('Refusing existing output directory. Pick a fresh job directory.')
    output.parent.mkdir(parents=True,exist_ok=True);log=output.with_suffix('.log')
    if log.exists():ap.error('Refusing existing log: '+str(log))
    with tempfile.TemporaryDirectory(prefix='fd3d-blender-') as home:
        allowed=('PATH','SYSTEMROOT','WINDIR','TEMP','TMP','TMPDIR','LANG','LC_ALL','LD_LIBRARY_PATH')
        env={k:os.environ[k] for k in allowed if k in os.environ}
        env.update(HOME=home,USERPROFILE=home,BLENDER_USER_CONFIG=str(Path(home)/'config'),BLENDER_USER_SCRIPTS=str(Path(home)/'scripts'),OMP_NUM_THREADS=str(a.threads))
        with log.open('x',encoding='utf-8') as f:
            try:r=subprocess.run(cmd,cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=a.timeout,check=False)
            except subprocess.TimeoutExpired:print(json.dumps(dict(status='TIMEOUT',log=str(log))));raise SystemExit(124)
        print(json.dumps(dict(status='PROCESS_EXIT',returncode=r.returncode,log=str(log),output=str(output))))
        raise SystemExit(r.returncode)
if __name__=='__main__':main()
