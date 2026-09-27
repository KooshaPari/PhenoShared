#!/usr/bin/env python3
"""Build a standalone, offline HTML from this kit's local demo sources."""
import base64
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def main():
 d=ROOT/'demo';s=(d/'index.html').read_text(encoding='utf-8')
 s=s.replace('<link rel="stylesheet" href="style.css">','<style>'+(d/'style.css').read_text(encoding='utf-8')+'</style>')
 s=s.replace('src="poster.svg"','src="data:image/svg+xml;base64,'+base64.b64encode((d/'poster.svg').read_bytes()).decode()+'"')
 for f in ('mesh-data.js','software-viewer.js','viewer.js'):
  s=s.replace(f'<script src="{f}"></script>','<script>'+(d/f).read_text(encoding='utf-8')+'</script>')
 s=s.replace('href="../START-HERE.md"','href="START-HERE.md"')
 (ROOT/'demo-standalone.html').write_text(s,encoding='utf-8')
 print('Wrote demo-standalone.html')
if __name__=='__main__':main()
