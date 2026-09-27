#!/usr/bin/env python3
"""Inspect actual video bytes and decode them. This is NOT a perceptual or product verifier."""
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

def run(args:list[str],timeout:int=120)->str:
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout,check=False)
 if p.returncode:raise ValueError(f'{args[0]} failed: {p.stderr[-3000:]}')
 return p.stdout

def audit(path:Path,*,width:int|None=None,height:int|None=None,duration:float|None=None,audio:bool|None=None)->dict:
 path=path.resolve(strict=True)
 metadata=json.loads(run(['ffprobe','-v','error','-protocol_whitelist','file,pipe','-show_streams','-show_format','-of','json',str(path)],30))
 v=next((s for s in metadata.get('streams',[]) if s.get('codec_type')=='video'),None)
 if not v:raise ValueError('No video/image stream')
 if width is not None and width!=v['width']:raise ValueError('Width mismatch')
 if height is not None and height!=v['height']:raise ValueError('Height mismatch')
 actual=float(metadata.get('format',{}).get('duration',v.get('duration','nan')))
 if duration is not None and not(abs(actual-duration)<=.12):raise ValueError('Duration mismatch')
 has_audio=any(s.get('codec_type')=='audio' for s in metadata['streams'])
 if audio is not None and has_audio!=audio:raise ValueError('Audio presence mismatch')
 run(['ffmpeg','-v','error','-xerror','-nostdin','-protocol_whitelist','file,pipe','-i',str(path),'-f','null','-'])
 with path.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
 return {'path':str(path),'sha256':digest,'bytes':path.stat().st_size,'metadata':metadata,'checks':{'decode':'PASS','requestedMetadata':'PASS'},'visualReview':'INCONCLUSIVE','consumerJourney':'INCONCLUSIVE'}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('file',type=Path);p.add_argument('--width',type=int);p.add_argument('--height',type=int);p.add_argument('--duration',type=float);p.add_argument('--audio',choices=['present','absent']);p.add_argument('--output',type=Path)
 a=p.parse_args()
 try:r=audit(a.file,width=a.width,height=a.height,duration=a.duration,audio=None if a.audio is None else a.audio=='present')
 except (ValueError,OSError,subprocess.TimeoutExpired) as e:p.exit(1,f'{e}\n')
 text=json.dumps(r,indent=2)+'\n'
 if a.output:a.output.write_text(text)
 else:print(text)
if __name__=='__main__':main()
