import {spawnSync} from 'node:child_process';
export function checkedProcess(executable,args,{timeout=120000,maxBuffer=4*1024*1024}={}) {
  const r=spawnSync(executable,args,{shell:false,encoding:'utf8',timeout,maxBuffer,windowsHide:true});
  if(r.error) throw new Error(`Tool invocation failed: ${r.error.message}`);
  if(r.status!==0) throw new Error(`${executable} failed (${r.status}): ${r.stderr.slice(-4000)}`);
  return r.stdout;
}
export function probeMedia(file) {
  return JSON.parse(checkedProcess(process.env.FFPROBE ?? 'ffprobe',[
    '-v','error','-protocol_whitelist','file,pipe','-show_streams','-show_format','-of','json',file,
  ],{timeout:30000}));
}
export function primaryVideo(metadata) {
  const stream=metadata.streams?.find(s=>s.codec_type==='video');
  if(!stream || !Number.isInteger(stream.width) || !Number.isInteger(stream.height)) throw new Error('No measurable video/image stream');
  const rotation=stream.side_data_list?.find(s=>s.rotation!==undefined)?.rotation ?? stream.tags?.rotate ?? 0;
  if(Number(rotation)!==0 || (stream.sample_aspect_ratio && !['1:1','0:1','N/A'].includes(stream.sample_aspect_ratio))) {
    throw new Error('Normalize rotation and non-square pixel aspect explicitly before annotation');
  }
  return stream;
}
export function decodeMedia(file) {
  checkedProcess(process.env.FFMPEG ?? 'ffmpeg',[
    '-v','error','-xerror','-nostdin','-protocol_whitelist','file,pipe','-i',file,'-f','null','-',
  ]);
}
