#!/usr/bin/env node
/** Replacement for PR87 render.mjs. Modified for isolated staging and explicit media contracts.
 * Prepared against 6c99a15337505b55f46a9f576465db5e4053b416. Runtime requires on-device qualification.
 * No package acquisition, arbitrary shell strings, shared public deletion, or publication.
 */
import {readFile,mkdir,mkdtemp,writeFile,stat} from 'node:fs/promises';
import {dirname,resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {validateEmbed} from '../../../packages/visual-production/src/contracts.mjs';
import {stageAsset,hashFile} from '../../../packages/visual-production/src/staging.mjs';
import {probeMedia,primaryVideo,decodeMedia} from '../../../packages/visual-production/src/probe-media.mjs';
const ROOT=resolve(dirname(fileURLToPath(import.meta.url)),'..');
function options(argv){
  const opts={format:'mp4'};
  for(let i=0;i<argv.length;i++){
    if(argv[i]==='--help'){console.log('node bin/render.mjs --annotations relative-or-absolute.json --out output-dir --format mp4|gif|both\nRequires installed aligned Remotion dependencies, FFmpeg/FFprobe and DOC_EMBEDS_BROWSER. Outputs are presentation derivatives, not raw evidence.');process.exit(0);}
    const key=argv[i].replace(/^--/,'');
    if(!['annotations','out','format'].includes(key)||!argv[i+1]||argv[i+1].startsWith('--')) throw new Error(`Unknown/missing option: ${argv[i]}`);
    opts[key]=argv[++i];
  }
  if(!opts.annotations||!['mp4','gif','both'].includes(opts.format)) throw new Error('Valid --annotations and --format required');
  return opts;
}
let runDir;
async function main(){
  const opts=options(process.argv.slice(2));
  const specPath=resolve(opts.annotations),specDir=dirname(specPath);
  if((await stat(specPath)).size>2*1024*1024) throw new Error('Spec exceeds 2 MiB');
  const original=JSON.parse(await readFile(specPath,'utf8'));
  validateEmbed(original);
  const spec=structuredClone(original),out=resolve(opts.out ?? join(specDir,'out'));
  await mkdir(out,{recursive:true});
  runDir=await mkdtemp(join(out,`${spec.id}-`));
  const publicDir=join(runDir,'public'); await mkdir(publicDir);
  const assets=[],seen=new Set(); let totalBytes=0;
  async function stage(name){
    const asset=await stageAsset(specDir,name,publicDir);
    if(!seen.has(asset.sha256)){totalBytes+=asset.bytes;seen.add(asset.sha256);}
    if(totalBytes>1024*1024*1024) throw new Error('Total staging budget exceeds 1 GiB');
    assets.push(asset);return asset;
  }
  for(const scene of spec.scenes){
    const item=await stage(scene.src),meta=probeMedia(join(publicDir,item.name)),stream=primaryVideo(meta);
    for(const [field,actual] of [['sourceWidth',stream.width],['sourceHeight',stream.height]]){
      if(scene[field]!==undefined && scene[field]!==actual) throw new Error(`${scene.src}: ${field} disagrees with decoded metadata`);
      scene[field]=actual;
    }
    if(scene.clipSec!==undefined){
      const duration=Number(stream.duration ?? meta.format?.duration);
      if(!Number.isFinite(duration)||scene.clipSec>duration+1/(spec.fps ?? 30)) throw new Error('Clip exceeds source duration or duration unavailable');
    }
    scene.src=item.name;
  }
  if(spec.audioSrc){
    if(!/\.(wav|mp3|m4a|ogg|flac|aac)$/i.test(spec.audioSrc)) throw new Error('Unsupported audio extension');
    const item=await stage(spec.audioSrc),meta=probeMedia(join(publicDir,item.name));
    if(!meta.streams?.some(s=>s.codec_type==='audio')) throw new Error('Audio asset has no audio stream');
    spec.audioSrc=item.name;
  }
  validateEmbed(spec,{requireMetadata:true});
  await writeFile(join(runDir,'staged-props.json'),JSON.stringify(spec,null,2));
  await writeFile(join(runDir,'staging-receipt.json'),JSON.stringify({inputSpecSha256:await hashFile(specPath),assets},null,2));
  const browser=process.env.DOC_EMBEDS_BROWSER;
  if(!browser || !(await stat(browser).catch(()=>null))?.isFile()) throw Object.assign(new Error('Set DOC_EMBEDS_BROWSER to an installed, qualified browser executable; no download is attempted'),{blocked:true});
  let bundler,renderer;
  try{bundler=await import('@remotion/bundler');renderer=await import('@remotion/renderer');}
  catch(e){throw Object.assign(new Error(`Install an aligned, licensed Remotion toolchain in this workspace first: ${e.message}`),{blocked:true});}
  // Canary isolation intentionally builds per run. Promote a source+lock keyed immutable bundle cache for throughput.
  // Remotion SSR does not automatically honor remotion.config.ts; reviewed overrides belong here explicitly.
  const serveUrl=await bundler.bundle({entryPoint:join(ROOT,'src/index.tsx'),rootDir:ROOT,publicDir,outDir:join(runDir,'bundle')});
  const composition=await renderer.selectComposition({serveUrl,id:'DocEmbed',inputProps:spec,browserExecutable:browser});
  const outputs=[];
  for(const fmt of opts.format==='both'?['mp4','gif']:[opts.format]){
    const output=join(runDir,`${spec.id}.${fmt}`);
    if(fmt==='mp4' && (composition.width%2 || composition.height%2)) throw new Error('H.264 yuv420p delivery requires even output dimensions');
    await renderer.renderMedia({composition,serveUrl,inputProps:spec,outputLocation:output,browserExecutable:browser,
      codec:fmt==='mp4'?'h264':'gif',concurrency:1,timeoutInMilliseconds:30000,
      ...(fmt==='mp4'?{pixelFormat:'yuv420p'}:{everyNthFrame:1,numberOfGifLoops:1})});
    decodeMedia(output);
    const meta=probeMedia(output),video=primaryVideo(meta);
    if(video.width!==composition.width||video.height!==composition.height) throw new Error('Rendered dimensions mismatch');
    const duration=Number(meta.format?.duration ?? video.duration),expected=composition.durationInFrames/composition.fps;
    if(!Number.isFinite(duration)||Math.abs(duration-expected)>Math.max(0.12,2/composition.fps)) throw new Error('Rendered duration mismatch');
    outputs.push({path:output,sha256:await hashFile(output),metadata:meta,decode:'PASS'});
  }
  await writeFile(join(runDir,'render-receipt.json'),JSON.stringify({artifactKind:'presentation',integrity:'PASS',visualReview:'INCONCLUSIVE',consumerJourney:'INCONCLUSIVE',outputs},null,2));
  console.log(JSON.stringify({runDir,exportIntegrity:'PASS',endToEndVerdict:'INCONCLUSIVE',outputs:outputs.map(x=>x.path)}));
}
main().catch(async error=>{
  const receipt={status:error.blocked?'BLOCKED_ENV':'FAIL',message:error.message,runDir};
  if(runDir) await writeFile(join(runDir,'failure.json'),JSON.stringify(receipt,null,2)).catch(()=>{});
  console.error(JSON.stringify(receipt));process.exitCode=error.blocked?2:1;
});
