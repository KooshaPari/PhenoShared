#!/usr/bin/env python3
"""Copy canonical repo skills to a chosen harness layout. Dry-run; conflicts fail; no AGENTS.md edits."""
import argparse,json,shutil
from pathlib import Path
from apply_overlay import safe_target

def activate(repo:Path,harness:str,enabled:bool=False)->dict:
 canonical=repo/'skills';prefix='.agents/skills' if harness=='codex' else '.forge/skills'
 if canonical.is_symlink() or not canonical.is_dir():raise ValueError('Canonical skills directory missing or symlinked')
 files=[]
 for skill in sorted(canonical.iterdir()):
  if not skill.is_dir() or not (skill/'SKILL.md').is_file():continue
  if skill.is_symlink():raise ValueError('Symlink skill rejected')
  for src in sorted(skill.rglob('*')):
   if src.is_symlink():raise ValueError('Symlink file rejected')
   if src.is_file():
    target=safe_target(repo,prefix+'/'+src.relative_to(canonical).as_posix())
    if target.exists() and (not target.is_file() or target.read_bytes()!=src.read_bytes()):raise ValueError(f'Conflict: {target}')
    if not target.exists():files.append((src,target))
 if enabled:
  for src,target in files:
   target.parent.mkdir(parents=True,exist_ok=True)
   with target.open('xb') as f:f.write(src.read_bytes())
 return {'mode':'apply' if enabled else 'dry-run','harness':harness,'copyCount':len(files),'targets':[str(p.relative_to(repo)) for _,p in files]}
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--harness',choices=['codex','forge'],required=True);p.add_argument('--apply',action='store_true');a=p.parse_args()
 try:print(json.dumps(activate(a.repo.resolve(strict=True),a.harness,a.apply),indent=2))
 except (OSError,ValueError) as e:p.exit(1,str(e)+'\n')
if __name__=='__main__':main()
