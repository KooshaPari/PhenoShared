#!/usr/bin/env python3
"""Verify this package's delivered files. Hashes detect changed bytes, not producer authenticity."""
import argparse,hashlib
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);a=p.parse_args();root=a.root.resolve();count=0
for line in (root/'MANIFEST.sha256').read_text().splitlines():
 expected,rel=line.split('  ',1);path=root/rel
 if Path(rel).is_absolute() or '..' in Path(rel).parts or path.is_symlink():raise SystemExit(f'Unsafe manifest path: {rel}')
 if not path.is_file():raise SystemExit(f'Missing: {rel}')
 with path.open('rb') as f:actual=hashlib.file_digest(f,'sha256').hexdigest()
 if actual!=expected:raise SystemExit(f'Changed: {rel}')
 count+=1
print(f'{count} listed files match SHA-256. This is integrity, not source/host authentication.')
