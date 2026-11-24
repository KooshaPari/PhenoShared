#!/usr/bin/env python3
"""Non-destructive local phenoDesign integration. Dry-run by default; never commits, merges or pushes."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, tempfile
from datetime import datetime, timezone
from pathlib import Path

PACK=Path(__file__).resolve().parents[1]
EXPECTED={
 'remotion/doc-embeds/bin/render.mjs':'1c0956e6a59203a2c1c42c424e377c0a3d8a88d2',
 'remotion/doc-embeds/src/schema.ts':'4c076a8c5c474f78644e806f681abb6ea515a0a3',
 'remotion/doc-embeds/src/components/SceneView.tsx':'77add7b263e409bc42f632d48134e9473778cbc7',
 'remotion/doc-embeds/src/DocEmbed.tsx':'e674f812dcf3d4e35b295feedb0509e6a5c4a9e3',
 'remotion/doc-embeds/src/components/Highlight.tsx':'327d4363c0056992e806c53ceff946398774acc1',
 'package.json':'de801285b0c70f43023f6984ca880b19c3fcc812',
 'remotion/doc-embeds/package.json':'6d0d70c3f89395adaada162a90bb5e633ed681a0',
}
def git_blob(data:bytes)->str:
 return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
def safe_target(root:Path,rel:str)->Path:
 p=Path(rel)
 if p.is_absolute() or '..' in p.parts or not p.parts: raise ValueError(f'Unsafe target: {rel}')
 target=root/p
 cur=root
 for part in p.parts:
  cur=cur/part
  if cur.is_symlink(): raise ValueError(f'Refusing symlink: {cur}')
 return target

def plan(repo:Path,pack:Path=PACK)->dict[str,bytes]:
 if not repo.is_dir(): raise ValueError('Repository directory does not exist')
 required=['remotion/doc-embeds/src/index.tsx','remotion/doc-embeds/src/components/Callout.tsx','packages/playwright-record/src/recorder.ts']
 for name in required:
  if not safe_target(repo,name).is_file(): raise ValueError(f'Migration prerequisite missing: {name}. Reconcile PR87 first; do not recreate absent packages from this overlay.')
 desired={}
 for src in sorted((pack/'phenoDesign-overlay').rglob('*')):
  if src.is_symlink(): raise ValueError(f'Pack symlink rejected: {src}')
  if src.is_file(): desired[src.relative_to(pack/'phenoDesign-overlay').as_posix()]=src.read_bytes()
 # Install original skills under one canonical repository directory, not two drifting harness copies.
 roots=[pack/'skills',pack/'reference/frontend-3d-agent-kit/skills',pack/'reference/frontend-3d-agent-kit/upstream/anthropic']
 for root in roots:
  if not root.exists(): continue
  for src in sorted(root.rglob('*')):
   if src.is_symlink(): raise ValueError('Skill source symlink rejected')
   if src.is_file():
    rel='skills/'+src.relative_to(root).as_posix()
    if rel in desired and desired[rel]!=src.read_bytes(): raise ValueError(f'Duplicate skill: {rel}')
    data=src.read_bytes()
    if src.name=='SKILL.md' and root==pack/'reference/frontend-3d-agent-kit/skills':
     data=data.replace(b'{{KIT_ROOT}}',str((pack/'reference/frontend-3d-agent-kit').resolve()).encode())
    desired[rel]=data
 for root,prefix in [(pack/'docs','docs/visual-production'),(pack/'resources','docs/visual-production/resources')]:
  for src in sorted(root.rglob('*')):
   if src.is_file() and not src.is_symlink(): desired[prefix+'/'+src.relative_to(root).as_posix()]=src.read_bytes()
 # Metadata adjustments preserve all other fields. A second run is idempotent.
 for name in ['package.json','remotion/doc-embeds/package.json']:
  path=safe_target(repo,name); raw=path.read_bytes(); obj=json.loads(raw)
  if name=='package.json':
   spaces=obj.get('workspaces',[])
   if not isinstance(spaces,list): raise ValueError('Reconcile non-array workspace layout manually')
   if 'remotion/*' not in spaces: spaces.append('remotion/*')
   obj['workspaces']=spaces
  else:
   deps=obj.setdefault('dependencies',{})
   if 'remotion' not in deps: raise ValueError('Remotion dependency missing')
   deps.setdefault('@remotion/bundler',deps['remotion'])
  target=(json.dumps(obj,indent=2,ensure_ascii=False)+'\n').encode()
  if target!=raw:
   # Allow formatting-only/idempotent content from this installer; reject unknown semantic input.
   if git_blob(raw)!=EXPECTED[name]:
    if json.loads(raw)!=obj: raise ValueError(f'Metadata drift: {name}; review and merge intentionally')
   desired[name]=target
 for name,data in desired.items():
  dest=safe_target(repo,name)
  if name in EXPECTED and not dest.exists(): raise ValueError(f'Expected source missing: {name}')
  if dest.exists():
   if not dest.is_file(): raise ValueError(f'Target not a regular file: {name}')
   old=dest.read_bytes()
   if old!=data and git_blob(old)!=EXPECTED.get(name): raise ValueError(f'Conflict/drift, no files changed: {name}')
 return desired

def apply(repo:Path,desired:dict[str,bytes],*,enabled:bool=False)->dict:
 changed=[name for name,data in desired.items() if not safe_target(repo,name).exists() or safe_target(repo,name).read_bytes()!=data]
 report={'mode':'apply' if enabled else 'dry-run','changed':changed,'unchanged':len(desired)-len(changed),'no_remote_actions':True}
 if not enabled or not changed:return report
 # Caller must prevent concurrent writers. Preflight drift and symlinks are checked again here.
 before={}
 for name in changed:
  p=safe_target(repo,name);before[name]=p.read_bytes() if p.exists() else None
  if before[name] is not None and before[name]!=desired[name] and git_blob(before[name])!=EXPECTED.get(name):
   raise ValueError(f'Conflict or modification after planning: {name}')
 stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
 backup=Path(tempfile.mkdtemp(prefix=f'phenoDesign-before-{stamp}-',dir=repo.parent))
 for name,data in before.items():
  if data is not None:
   p=backup/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
 journal={'created':[n for n,x in before.items() if x is None],'replaced':[n for n,x in before.items() if x is not None]}
 (backup/'JOURNAL.json').write_text(json.dumps(journal,indent=2)+'\n')
 written=[]
 try:
  for name in changed:
   p=safe_target(repo,name)
   current=p.read_bytes() if p.exists() else None
   if current!=before[name]: raise ValueError(f'Concurrent modification: {name}')
   p.parent.mkdir(parents=True,exist_ok=True)
   fd,tmp=tempfile.mkstemp(prefix='.pd-stage-',dir=p.parent)
   try:
    with os.fdopen(fd,'wb') as stream:stream.write(desired[name])
    os.replace(tmp,p)
   finally:
    if os.path.exists(tmp):os.unlink(tmp)
   written.append(name)
 except BaseException:
  for name in reversed(written):
   p=repo/name
   if before[name] is None:p.unlink(missing_ok=True)
   else:p.write_bytes(before[name])
  raise
 report['backup']=str(backup)
 return report

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--apply',action='store_true')
 a=p.parse_args()
 if a.repo.is_symlink():p.error('Repository symlink not accepted')
 repo=a.repo.resolve()
 try:print(json.dumps(apply(repo,plan(repo),enabled=a.apply),indent=2))
 except (ValueError,OSError,json.JSONDecodeError) as exc:p.exit(1,f'{exc}\n')
if __name__=='__main__':main()
