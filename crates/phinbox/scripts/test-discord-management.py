#!/usr/bin/env python3
"""Focused actual-source library/CLI tests, Python3.11+; no live Discord calls."""
import json, os, platform, subprocess, tempfile, tomllib
from pathlib import Path
crate = Path(__file__).resolve().parents[1]
root = crate.parents[1]
pkg = tomllib.loads((crate / 'Cargo.toml').read_text())
ws = tomllib.loads((root / 'Cargo.toml').read_text())
def lit(v):
    if isinstance(v, dict): return '{ ' + ', '.join(json.dumps(k)+' = '+lit(x) for k,x in v.items())+' }'
    if isinstance(v, list): return '['+', '.join(lit(x) for x in v)+']'
    if isinstance(v, bool): return str(v).lower()
    return json.dumps(v)
def deps(table):
    out=[]
    for name, value in table.items():
        if isinstance(value,dict) and value.get('optional'): continue
        if isinstance(value,dict) and value.get('workspace'):
            shared=ws['workspace']['dependencies'][name]
            base=dict(shared) if isinstance(shared,dict) else {'version':shared}
            override={k:v for k,v in value.items() if k!='workspace'}
            features=sorted(set(base.get('features',[]))|set(override.pop('features',[])))
            base.update(override)
            if features: base['features']=features
            if 'path' in base: base['path']=str((root/base['path']).resolve())
            value=base
        elif isinstance(value,dict) and 'path' in value:
            value=dict(value);value['path']=str((crate/value['path']).resolve())
        out.append(json.dumps(name)+' = '+lit(value))
    return out
scratch=Path(tempfile.mkdtemp(prefix='phinbox-discord-focused-'))
lines=['[package]','name="phinbox"','version='+lit(pkg['package']['version']),'edition="2021"',
       '[lib]','path='+lit(str(crate/'src/lib.rs')),'[features]','default=[]','mcp=[]','tray-native=[]','observability=[]',
       '[dependencies]',*deps(pkg['dependencies']),'[dev-dependencies]',*deps(pkg['dev-dependencies'])]
tests=sorted((crate/'tests').glob('discord_*.rs'))
for test in tests: lines+=['[[test]]','name='+lit(test.stem),'path='+lit(str(test))]
lines+=['[[bin]]','name="phinbox"','path='+lit(str(crate/'src/cli/mod.rs'))]
manifest=scratch/'Cargo.toml';manifest.write_text('\n'.join(lines)+'\n')
env=dict(os.environ,CARGO_BUILD_JOBS='1')
env.setdefault('CARGO_TARGET_DIR',str(Path.home()/'.cache/phinbox-discord-target'))
if platform.system()=='Darwin':
    sdk='/Library/Developer/CommandLineTools/SDKs/MacOSX26.sdk'
    if not Path(sdk).is_dir(): raise SystemExit('Required MacOSX26 SDK unavailable')
    env.update(SDKROOT=sdk,MACOSX_DEPLOYMENT_TARGET='15.0')
print('Focused actual-source harness:',manifest,flush=True)
subprocess.run(['cargo','check','--manifest-path',str(manifest),'--bin','phinbox'],env=env,check=True)
args=['cargo','test','--manifest-path',str(manifest)]
for test in tests: args+=['--test',test.stem]
subprocess.run(args,env=env,check=True)
