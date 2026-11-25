/** Runtime validation; a TypeScript interface is not a validator. Fail closed before rendering. */
const HEX = /^#[0-9a-f]{6}$/i;
export const SAFE_ID = /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,95}$/;
export function fail(message) { throw new TypeError(message); }
function obj(v, name) { if (!v || typeof v !== 'object' || Array.isArray(v)) fail(`${name}: object required`); }
function text(v, name, max=4000) { if (typeof v !== 'string' || !v.trim() || v.length > max) fail(`${name}: nonempty bounded string required`); }
function number(v, name, min, max) { if (!Number.isFinite(v) || v < min || v > max) fail(`${name}: finite value ${min}..${max} required`); }
function list(v, name, max) { if (!Array.isArray(v) || v.length > max) fail(`${name}: bounded array required`); }
function color(v, name) { if (v !== undefined && !HEX.test(v)) fail(`${name}: six-digit hex required`); }
export function localAssetName(v) {
  text(v, 'asset path', 1000);
  // Portable local paths only. No remote URLs, Windows drives, escapes, encoded separators or traversal.
  if (/[:\\%?#\x00-\x1f]/.test(v) || v.startsWith('/') || v.split('/').some(x => !x || x==='.' || x==='..')) fail('Unsafe asset path');
  return v;
}
export function validateEmbed(input, {requireMetadata=false} = {}) {
  obj(input, 'embed');
  text(input.id, 'id', 96); if (!SAFE_ID.test(input.id)) fail('Unsafe id');
  text(input.title, 'title'); if (input.subtitle !== undefined) text(input.subtitle, 'subtitle');
  number(input.width ?? 1280, 'width', 2, 8192); number(input.height ?? 800, 'height', 2, 8192);
  if (!Number.isInteger(input.width ?? 1280) || !Number.isInteger(input.height ?? 800)) fail('Dimensions must be integers');
  number(input.fps ?? 30, 'fps', 1, 120); color(input.accent, 'accent');
  list(input.scenes, 'scenes', 500); if (!input.scenes.length) fail('At least one scene required');
  if (input.audioSrc !== undefined) localAssetName(input.audioSrc);
  let total = 0;
  input.scenes.forEach((s, index) => {
    obj(s, `scene ${index}`); localAssetName(s.src);
    const video = /\.(mp4|mov|webm|mkv)$/i.test(s.src);
    if (!video && !/\.(png|jpe?g|webp)$/i.test(s.src)) fail('Unsupported media extension; rasterize vectors explicitly');
    if (video && s.holdSec !== undefined) fail('Video uses clipSec, not holdSec');
    if (!video && s.clipSec !== undefined) fail('Still uses holdSec, not clipSec');
    const duration = video ? s.clipSec : s.holdSec;
    number(duration, 'explicit scene duration', 0.01, 3600); total += duration;
    if (total > 3600) fail('Embed exceeds one-hour safety budget');
    if (s.fit !== undefined && !['contain','cover'].includes(s.fit)) fail('Invalid fit');
    for (const key of ['sourceWidth','sourceHeight']) {
      if (requireMetadata || s[key] !== undefined) {
        number(s[key], key, 1, 32768); if (!Number.isInteger(s[key])) fail(`${key}: integer required`);
      }
    }
    if (s.zoom !== undefined) { list(s.zoom,'zoom',2); if(s.zoom.length!==2) fail('zoom pair required'); s.zoom.forEach(v=>number(v,'zoom',0.1,10)); }
    for (const key of ['callouts','highlights','cursors']) {
      if (s[key] === undefined) continue;
      list(s[key], key, 1000);
      s[key].forEach(a => {
        obj(a, key); number(a.atSec,'atSec',0,Math.max(0,duration-0.000001)); color(a.color,'annotation color');
        if (a.durationSec !== undefined) number(a.durationSec,'annotation duration',0.01,duration-a.atSec+0.000001);
        if(key==='callouts') {
          text(a.text,'callout text'); if(a.subText!==undefined) text(a.subText,'subText');
          if(a.anchor!==undefined && !['top-left','top-right','bottom-left','bottom-right'].includes(a.anchor)) fail('Invalid anchor');
        } else {
          number(a.x,'x',0,s.sourceWidth ?? 32768); number(a.y,'y',0,s.sourceHeight ?? 32768);
          if(key==='highlights') {
            number(a.width,'highlight width',0.01,32768); number(a.height,'highlight height',0.01,32768);
            if(requireMetadata && (a.x+a.width>s.sourceWidth || a.y+a.height>s.sourceHeight)) fail('Highlight outside source');
            if(a.style!==undefined && !['pulse','static'].includes(a.style)) fail('Invalid highlight style');
            if(a.label!==undefined) text(a.label,'highlight label');
          } else if(a.kind!==undefined && !['ring','ripple'].includes(a.kind)) fail('Invalid cursor kind');
        }
      });
    }
  });
  return input;
}
export function validateProductionJob(job) {
  obj(job,'job'); if (!SAFE_ID.test(job.id ?? '')) fail('Invalid job id');
  if (!['vector','raster','animation-2d','scene-3d','video','interactive','diagram','editorial','audio','spatial'].includes(job.medium)) fail('Unknown medium');
  if (!['concept','presentation','evidence-master'].includes(job.artifactKind)) fail('Unknown artifactKind');
  list(job.editableSources,'editableSources',500); if(!job.editableSources.length) fail('Editable source required');
  job.editableSources.forEach(localAssetName);
  list(job.outputs,'outputs',500); if(!job.outputs.length) fail('Output required'); job.outputs.forEach(localAssetName);
  list(job.acceptance,'acceptance',500); if(!job.acceptance.length) fail('Acceptance required'); job.acceptance.forEach(x=>text(x,'acceptance'));
  obj(job.rights,'rights'); text(job.rights.basis,'rights basis');
  if (job.artifactKind==='evidence-master') {
    text(job.journeyRef,'journeyRef');
    if (job.generated || job.retouch) fail('Generated/retouched imagery cannot be evidence-master');
  }
  return job;
}
/** Aggregate reported assertions, not independent proof. Bind receipts to your trusted existing verifier. */
export function aggregateVerdict(checks) {
  if (!Array.isArray(checks) || !checks.length) return 'INCONCLUSIVE';
  const states = new Set(checks.map(x=>x.status));
  const allowed = new Set(['PASS','FAIL','BLOCKED_ENV','BLOCKED_AUTH','INCONCLUSIVE','CANCELLED']);
  if([...states].some(s=>!allowed.has(s))) throw new TypeError('Unknown assertion status');
  for(const s of ['FAIL','CANCELLED','BLOCKED_AUTH','BLOCKED_ENV','INCONCLUSIVE']) if(states.has(s)) return s;
  return 'PASS';
}
