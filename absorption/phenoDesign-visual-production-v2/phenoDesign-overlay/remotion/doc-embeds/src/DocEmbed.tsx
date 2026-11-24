/** Modified PR87 composition: explicit durations and per-scene metadata, preserving existing caption presentation. */
import React from 'react';
import {AbsoluteFill,Audio,Sequence,Series,staticFile,useVideoConfig} from 'remotion';
import type {EmbedSpec,Scene} from './schema';
import {DEFAULTS} from './schema';
import {SceneView} from './components/SceneView';
import {sceneFrames as frames} from '../../../packages/visual-production/src/geometry.mjs';
export function sceneFrames(scene:Scene,fps:number):number {return frames(scene,fps);}
export function totalFrames(spec:EmbedSpec):number {return spec.scenes.reduce((sum,s)=>sum+sceneFrames(s,spec.fps??DEFAULTS.fps),0);}
export const DocEmbed:React.FC<EmbedSpec>=(spec)=>{
  const {fps,width,height}=useVideoConfig();const accent=spec.accent??DEFAULTS.accent;
  return <AbsoluteFill style={{background:'#0b0f14'}}>
    <Series>{spec.scenes.map((scene,i)=><Series.Sequence key={i} durationInFrames={sceneFrames(scene,fps)}>
      <SceneView scene={scene} width={width} height={height} accent={accent} durationInFrames={sceneFrames(scene,fps)}/>
    </Series.Sequence>)}</Series>
    {spec.audioSrc&&<Sequence from={0}><Audio src={staticFile(spec.audioSrc)}/></Sequence>}
    <div style={{position:'absolute',bottom:0,left:0,right:0,height:56,background:'linear-gradient(0deg, rgba(0,0,0,0.85), rgba(0,0,0,0))',display:'flex',alignItems:'center',padding:'0 28px',gap:14,fontFamily:'Arial, sans-serif'}}>
      <div style={{width:10,height:10,borderRadius:'50%',background:accent}}/>
      <span style={{color:'white',fontSize:22,fontWeight:700}}>{spec.title}</span>
      {spec.subtitle&&<span style={{color:'rgba(255,255,255,0.65)',fontSize:16}}>{spec.subtitle}</span>}
    </div>
  </AbsoluteFill>;
};
