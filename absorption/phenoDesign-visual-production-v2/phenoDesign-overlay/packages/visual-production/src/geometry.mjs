/** Source pixel -> viewport mapping. All media and source-space overlays share this transform. */
function positive(n, name) {
  if (!Number.isFinite(n) || n <= 0) throw new RangeError(`${name} must be finite and positive`);
  return n;
}
export function fitTransform({sourceWidth, sourceHeight, width, height, fit = 'cover', zoom = 1}) {
  for (const [name, val] of Object.entries({sourceWidth, sourceHeight, width, height, zoom})) positive(val, name);
  if (!['cover', 'contain'].includes(fit)) throw new TypeError('fit must be cover or contain');
  const scale = (fit === 'cover' ? Math.max : Math.min)(width/sourceWidth, height/sourceHeight) * zoom;
  return Object.freeze({scale, x: (width-sourceWidth*scale)/2, y: (height-sourceHeight*scale)/2});
}
export function mapPoint(point, transform) {
  if (!Number.isFinite(point.x) || !Number.isFinite(point.y)) throw new TypeError('Invalid point');
  return {x: point.x*transform.scale + transform.x, y: point.y*transform.scale + transform.y};
}
export function mapRect(rect, transform) {
  positive(rect.width, 'width'); positive(rect.height, 'height');
  return {...mapPoint(rect, transform), width: rect.width*transform.scale, height: rect.height*transform.scale};
}
export function frameWindow(atSec, durationSec, fps) {
  if (!Number.isFinite(atSec) || atSec < 0) throw new RangeError('atSec must be nonnegative');
  positive(durationSec, 'durationSec'); positive(fps, 'fps');
  const start = Math.round(atSec*fps);
  const end = start + Math.max(1, Math.round(durationSec*fps));
  return {start, end};
}
export function activeAt(frame, window) {
  return Number.isInteger(frame) && frame >= window.start && frame < window.end;
}
export function sceneFrames(scene, fps) {
  positive(fps, 'fps');
  const duration = scene.holdSec ?? scene.clipSec;
  positive(duration, 'scene duration');
  return Math.max(1, Math.round(duration*fps));
}
export function sceneTimeline(scenes, fps) {
  let end = 0;
  return scenes.map(scene => {
    const start = end;
    end += sceneFrames(scene, fps);
    return {start, end, durationInFrames: end-start};
  });
}
