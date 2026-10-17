#!/usr/bin/env python3
"""Build actual native source outside unrelated workspace resolution. No install/launch."""
import json,os,subprocess,tempfile,tomllib,argparse
from pathlib import Path
parser=argparse.ArgumentParser()
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--tray',action='store_true')
args=parser.parse_args()
app=Path(__file__).resolve().parent
root=app.parents[1]
crate=root/'crates/phinbox'
pkg=tomllib.loads((crate/'Cargo.toml').read_text())
ws=tomllib.loads((root/'Cargo.toml').read_text())
def lit(v):
    if isinstance(v,dict):return '{ '+', '.join(json.dumps(k)+' = '+lit(x) for k,x in v.items())+' }'
    if isinstance(v,list):return '['+', '.join(lit(x) for x in v)+']'
    if isinstance(v,bool):return str(v).lower()
    return json.dumps(v)
def deps(table):
    out=[]
    for name,value in table.items():
        if name=='phenotype-tooling-observability':continue
        if isinstance(value,dict) and value.get('workspace'):
            shared=ws['workspace']['dependencies'][name]
            base=dict(shared) if isinstance(shared,dict) else {'version':shared}
            override={k:v for k,v in value.items() if k!='workspace'}
            features=sorted(set(base.get('features',[]))|set(override.pop('features',[])))
            base.update(override)
            if features:base['features']=features
            value=base
        if isinstance(value,dict) and 'path' in value:
            value=dict(value);value['path']=str((root/value['path']).resolve())
        out.append(json.dumps(name)+' = '+lit(value))
    return out
args.output.mkdir(parents=True,exist_ok=True)
manifest_dir=args.output/'harness';manifest_dir.mkdir(exist_ok=True)
features=dict(pkg['features']);features['observability']=[]
lines=['[package]','name="phinbox"','version='+lit(pkg['package']['version']),'edition="2021"',
       '[lib]','path='+lit(str(crate/'src/lib.rs')),'[features]']
lines += [json.dumps(k)+' = '+lit(v) for k,v in features.items()]
lines += ['[dependencies]',*deps(pkg['dependencies']),'[dev-dependencies]',*deps(pkg['dev-dependencies'])]
for binary in pkg['bin']:
    lines+=['[[bin]]','name='+lit(binary['name']),'path='+lit(str(crate/binary['path']))]
    if 'required-features' in binary:lines+=['required-features='+lit(binary['required-features'])]
for test in sorted((crate/'tests').glob('native_*.rs')):
    lines+=['[[test]]','name='+lit(test.stem),'path='+lit(str(test))]
manifest=manifest_dir/'Cargo.toml';manifest.write_text('\n'.join(lines)+'\n')
env=dict(os.environ,CARGO_BUILD_JOBS='1',SDKROOT='/Library/Developer/CommandLineTools/SDKs/MacOSX26.sdk',MACOSX_DEPLOYMENT_TARGET='15.0')
env.setdefault('CARGO_TARGET_DIR',str(Path.home()/'.cache/phinbox-native-target'))
cmd=['cargo','build','--manifest-path',str(manifest),'--no-default-features','--bin','phinbox']
if args.tray:cmd += ['--features','mcp,tray-native','--bin','phinbox-app']
print('Building actual native source:',manifest,flush=True)
subprocess.run(cmd,env=env,check=True)
print('Built binaries:',str(Path(env['CARGO_TARGET_DIR'])/'debug'),flush=True)
