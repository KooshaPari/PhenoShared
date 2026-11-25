#!/usr/bin/env python3
"""Compile a bounded vector scene into an Illustrator JSX job; does not launch Illustrator."""
import argparse,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def compile_job(job:dict,workspace:Path)->str:
 if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}',job.get('id','')):raise ValueError('Unsafe job id')
 for k in ('width','height'):
  if type(job.get(k)) is not int or not 16<=job[k]<=8192:raise ValueError('Bounded integer dimensions required')
 layers=job.get('layers')
 if not isinstance(layers,list) or not 1<=len(layers)<=100:raise ValueError('1..100 layers required')
 clean={'id':job['id'],'width':job['width'],'height':job['height'],'layers':[],'outputDirectory':str(workspace.resolve(strict=True))}
 for layer in layers:
  if not isinstance(layer.get('name'),str) or not 1<=len(layer['name'])<=200:raise ValueError('Layer name required')
  if not isinstance(layer.get('shapes'),list) or not 1<=len(layer['shapes'])<=1000:raise ValueError('Bounded shape list required')
  copied={'name':layer['name'],'shapes':[]}
  for s in layer['shapes']:
   if s.get('kind') not in ('ellipse','rect','path'):raise ValueError('Unsupported shape')
   out={k:s[k] for k in ('kind','name','fill','stroke','strokeWidth','points','closed','x','y','width','height') if k in s}
   if not isinstance(out.get('name'),str) or len(out['name'])>200:raise ValueError('Shape name required')
   for k in ('fill','stroke'):
    if k in s and not re.fullmatch(r'#[0-9a-fA-F]{6}',s[k]):raise ValueError('Six-digit hex required')
   if 'strokeWidth' in s and not 0<float(s['strokeWidth'])<=100:raise ValueError('Invalid stroke width')
   if s['kind']=='path':
    points=s.get('points')
    if not isinstance(points,list) or not 2<=len(points)<=10000:raise ValueError('Bounded point list required')
    for pt in points:
     if len(pt)!=2 or any(not isinstance(x,(int,float)) or not -8192<=x<=16384 for x in pt):raise ValueError('Invalid point')
   else:
    for k in ('x','y','width','height'):
     if not isinstance(s.get(k),(int,float)) or not 0<=s[k]<=8192:raise ValueError('Invalid shape bounds')
    if min(s['width'],s['height'])<=0:raise ValueError('Empty shape')
   copied['shapes'].append(out)
  clean['layers'].append(copied)
 template=(ROOT/'worker-recipes/adobe/illustrator/author.jsx.in').read_text()
 return template.replace('__JOB_JSON__',json.dumps(clean,ensure_ascii=True,allow_nan=False))
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('job',type=Path);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 try:
  if a.out.exists():raise ValueError('Output JSX already exists')
  a.out.write_text(compile_job(json.loads(a.job.read_text()),a.workspace))
 except (ValueError,OSError) as e:p.exit(1,f'{e}\n')
if __name__=='__main__':main()
