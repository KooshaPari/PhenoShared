import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp, mkdir, writeFile, readFile, symlink, rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {fitTransform,mapPoint,mapRect,frameWindow,activeAt,sceneFrames,sceneTimeline} from '../src/geometry.mjs';
import {validateEmbed,localAssetName,validateProductionJob,aggregateVerdict} from '../src/contracts.mjs';
import {containedFile,stageAsset,hashFile} from '../src/staging.mjs';
const spec=()=>({id:'canary',title:'Source geometry',width:800,height:800,fps:30,scenes:[{src:'image.png',holdSec:2,sourceWidth:1600,sourceHeight:900}]});
const job=()=>({id:'canary',medium:'vector',artifactKind:'concept',editableSources:['source.svg'],outputs:['preview.png'],acceptance:['Logo remains legible at 24px'],rights:{basis:'Original authored geometry'}});
test('cover crop centers without stretching',()=>{const t=fitTransform({sourceWidth:1600,sourceHeight:900,width:800,height:800}); assert.equal(t.scale,8/9); assert.equal(t.y,0); assert.ok(t.x<0); assert.deepEqual(mapPoint({x:800,y:450},t),{x:400,y:400});});
test('contain adds letterbox offset',()=>assert.deepEqual(fitTransform({sourceWidth:1600,sourceHeight:900,width:800,height:800,fit:'contain'}),{scale:0.5,x:0,y:175}));
test('zoom and annotation share crop transform',()=>{const t=fitTransform({sourceWidth:100,sourceHeight:100,width:400,height:200,zoom:2});assert.deepEqual(mapRect({x:25,y:25,width:50,height:50},t),{x:0,y:-100,width:400,height:400});});
for(const value of [0,-1,NaN,Infinity]) test(`reject geometry dimension ${value}`,()=>assert.throws(()=>fitTransform({sourceWidth:value,sourceHeight:1,width:1,height:1})));
test('reject nonfinite coordinates',()=>assert.throws(()=>mapPoint({x:NaN,y:0},{scale:1,x:0,y:0})));
test('reject invalid fit',()=>assert.throws(()=>fitTransform({sourceWidth:1,sourceHeight:1,width:1,height:1,fit:'stretch'})));
test('half-open annotation interval',()=>{const w=frameWindow(1,1,30); assert.equal(activeAt(29,w),false);assert.equal(activeAt(30,w),true);assert.equal(activeAt(59,w),true);assert.equal(activeAt(60,w),false);});
test('timeline contiguous with scene-local frame counts',()=>assert.deepEqual(sceneTimeline([{holdSec:2},{clipSec:3}],30),[{start:0,end:60,durationInFrames:60},{start:60,end:150,durationInFrames:90}]));
test('unspecified video duration rejected',()=>assert.throws(()=>sceneFrames({src:'v.mp4'},30)));
test('fractional fps not truncated',()=>assert.equal(sceneFrames({clipSec:10},29.97),300));
test('valid embed passes without mutation',()=>{const s=spec(),before=JSON.stringify(s);assert.equal(validateEmbed(s,{requireMetadata:true}),s);assert.equal(JSON.stringify(s),before);});
for(const [name,edit] of [
 ['empty scenes',s=>s.scenes=[]],['unsafe id',s=>s.id='../bad'],['missing title',s=>delete s.title],
 ['zero fps',s=>s.fps=0],['nonfinite width',s=>s.width=NaN],['fractional width',s=>s.width=320.5],
 ['missing duration',s=>delete s.scenes[0].holdSec],['overlong scene',s=>s.scenes[0].holdSec=4000],
 ['video hold',s=>s.scenes[0].src='video.mp4'],['bad fit',s=>s.scenes[0].fit='fill'],
 ['bad zoom',s=>s.scenes[0].zoom=[0,2]],['missing metadata',s=>delete s.scenes[0].sourceWidth],
 ['late callout',s=>s.scenes[0].callouts=[{text:'Late',atSec:2}]],
 ['offsource highlight',s=>s.scenes[0].highlights=[{x:1590,y:0,width:100,height:20,atSec:0}]],
 ['negative cursor',s=>s.scenes[0].cursors=[{x:-1,y:0,atSec:0}]],
 ['unknown image type',s=>s.scenes[0].src='unsafe.svg'],
 ['invalid accent',s=>s.accent='red;content:evil'],
]) test(`embed rejects ${name}`,()=>{const s=spec();edit(s);assert.throws(()=>validateEmbed(s,{requireMetadata:true}));});
for(const name of ['../escape.png','/abs.png','C:/abs.png','a\\b.png','https://x/y.png','a//b.png','a/./b.png','%2e%2e/a.png','a.png?x=1','a\0.png']) test(`reject asset path ${JSON.stringify(name)}`,()=>assert.throws(()=>localAssetName(name)));
test('allows portable spaced path',()=>assert.equal(localAssetName('refs/one view.png'),'refs/one view.png'));
test('job requires source and acceptance',()=>{assert.equal(validateProductionJob(job()).id,'canary'); const j=job();j.editableSources=[];assert.throws(()=>validateProductionJob(j));});
test('synthetic media cannot claim raw evidence',()=>{const j=job();j.artifactKind='evidence-master';j.generated=true;j.journeyRef='journey:1';assert.throws(()=>validateProductionJob(j));});
test('evidence needs journey association',()=>{const j=job();j.artifactKind='evidence-master';assert.throws(()=>validateProductionJob(j));});
test('empty assertion set not green',()=>assert.equal(aggregateVerdict([]),'INCONCLUSIVE'));
test('blocked assertions prevent PASS',()=>assert.equal(aggregateVerdict([{status:'PASS'},{status:'BLOCKED_ENV'}]),'BLOCKED_ENV'));
test('failure beats blocked',()=>assert.equal(aggregateVerdict([{status:'FAIL'},{status:'BLOCKED_ENV'}]),'FAIL'));
test('unknown verdict rejected',()=>assert.throws(()=>aggregateVerdict([{status:'verified'}])));
test('all asserted passes aggregate as reported PASS',()=>assert.equal(aggregateVerdict([{status:'PASS'}]),'PASS'));
async function fixture(fn){const root=await mkdtemp(join(tmpdir(),'pd-stage-'));try{await fn(root);}finally{await rm(root,{recursive:true,force:true});}}
test('same basenames do not overwrite distinct assets',()=>fixture(async root=>{await mkdir(join(root,'a'));await mkdir(join(root,'b'));await writeFile(join(root,'a','same.png'),'first');await writeFile(join(root,'b','same.png'),'second');const out=join(root,'stage');const a=await stageAsset(root,'a/same.png',out),b=await stageAsset(root,'b/same.png',out);assert.notEqual(a.name,b.name);assert.equal(await readFile(join(out,a.name),'utf8'),'first');}));
test('same bytes deduplicate safely',()=>fixture(async root=>{await writeFile(join(root,'a.png'),'same');const out=join(root,'stage');assert.deepEqual(await stageAsset(root,'a.png',out),await stageAsset(root,'a.png',out));}));
test('parallel distinct staging directories do not collide',()=>fixture(async root=>{await writeFile(join(root,'a.png'),'same');const [a,b]=await Promise.all([stageAsset(root,'a.png',join(root,'r1')),stageAsset(root,'a.png',join(root,'r2'))]);assert.equal(a.sha256,b.sha256);assert.equal(await hashFile(join(root,'r1',a.name)),a.sha256);}));
test('symlink asset rejected',()=>fixture(async root=>{await writeFile(join(root,'a.png'),'same');await symlink(join(root,'a.png'),join(root,'b.png'));await assert.rejects(containedFile(root,'b.png'));}));
test('symlink directory rejected',()=>fixture(async root=>{await mkdir(join(root,'a'));await writeFile(join(root,'a','a.png'),'same');await symlink(join(root,'a'),join(root,'b'),'dir');await assert.rejects(containedFile(root,'b/a.png'));}));
test('directory masquerading as file rejected',()=>fixture(async root=>{await mkdir(join(root,'a.png'));await assert.rejects(containedFile(root,'a.png'));}));
test('empty file rejected',()=>fixture(async root=>{await writeFile(join(root,'a.png'),'');await assert.rejects(stageAsset(root,'a.png',join(root,'stage')));}));
test('oversized file rejected',()=>fixture(async root=>{await writeFile(join(root,'a.png'),'123');await assert.rejects(stageAsset(root,'a.png',join(root,'stage'),{maxBytes:2}));}));
test('corrupt preexisting stage rejected',()=>fixture(async root=>{await writeFile(join(root,'a.png'),'source');const out=join(root,'stage');const a=await stageAsset(root,'a.png',out);await writeFile(join(out,a.name),'corrupt');await assert.rejects(stageAsset(root,'a.png',out));}));
