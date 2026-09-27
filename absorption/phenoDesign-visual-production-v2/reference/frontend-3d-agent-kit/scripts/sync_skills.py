#!/usr/bin/env python3
"""Copy selected ORIGINAL kit skills to a project. Dry-run; conflicts refuse writes.
No deletes, config mutations, symlink traversal, user-global installs or AGENTS overwrite.
The complete kit stays at its source path; copied instructions point back to that root.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def plan(project:Path,harness:str,names:list[str]):
    dest=project/('.agents/skills' if harness=='codex' else '.forge/skills')
    if not project.is_dir():raise ValueError('Project directory must already exist')
    for parent in (project,*dest.parents):
        if parent.is_symlink():raise ValueError('Symlink destination ancestor refused')
        if parent.exists() and not parent.is_dir():raise ValueError('Destination ancestor is not a directory')
    if dest.is_symlink():raise ValueError('Symlink destination refused')
    ops=[]
    for name in names:
        if '/' in name or '\\' in name or name in ('.','..'):raise ValueError('Invalid skill name')
        source=ROOT/'skills'/name/'SKILL.md'
        if not source.is_file() or source.is_symlink():raise ValueError('Unknown original skill: '+name)
        target=dest/name/'SKILL.md'
        for p in (target.parent,target):
            if p.is_symlink():raise ValueError('Symlink destination refused')
        data=source.read_text(encoding='utf-8').replace('{{KIT_ROOT}}',str(ROOT))
        status='IDENTICAL' if target.is_file() and target.read_text(encoding='utf-8')==data else 'CONFLICT' if target.exists() else 'CREATE'
        ops.append(dict(source=str(source),destination=str(target),status=status,data=data))
    return ops

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--project',type=Path,required=True);ap.add_argument('--harness',choices=['codex','forge'],required=True);ap.add_argument('--skills',nargs='+');ap.add_argument('--apply',action='store_true');a=ap.parse_args()
    names=a.skills or sorted(p.name for p in (ROOT/'skills').iterdir() if (p/'SKILL.md').is_file())
    try:ops=plan(a.project.absolute(),a.harness,names)
    except ValueError as e:ap.error(str(e))
    print(json.dumps([{k:v for k,v in op.items() if k!='data'} for op in ops],indent=2))
    if any(x['status']=='CONFLICT' for x in ops):raise SystemExit('Conflicts found. No files written; reconcile manually.')
    if not a.apply:return
    for op in ops:
        if op['status']=='CREATE':
            p=Path(op['destination']);p.parent.mkdir(parents=True,exist_ok=True)
            with p.open('x',encoding='utf-8') as f:f.write(op['data'])
    print('Applied. Verify discovery in your installed harness/fork. Keep the kit source directory available.')
if __name__=='__main__':main()
