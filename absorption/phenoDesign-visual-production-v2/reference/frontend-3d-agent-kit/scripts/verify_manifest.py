#!/usr/bin/env python3
"""Verify the shipped checksum manifest against local bytes; no network access.
A checksum detects edits relative to this manifest, not publisher authenticity.
"""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--root',type=Path,default=ROOT);a=ap.parse_args();root=a.root.resolve();lines=(root/'MANIFEST.sha256').read_text(encoding='utf-8').splitlines();fail=[];seen=set()
 for line in lines:
  digest,rel=line.split('  ',1);path=(root/rel).resolve()
  if not path.is_relative_to(root) or rel in seen:fail.append(rel+': unsafe/duplicate entry');continue
  seen.add(rel)
  if not path.is_file():fail.append(rel+': missing');continue
  if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:fail.append(rel+': changed')
 print(json.dumps(dict(status='FAIL' if fail else 'PASS',checked=len(lines),errors=fail,scope='Listed file integrity, not signer authenticity'),indent=2))
 if fail:raise SystemExit(1)
if __name__=='__main__':main()
