/** Modified PR87 component: crop, zoom and source-space overlays share one affine transform. */
import React from 'react';
import {AbsoluteFill,OffthreadVideo,Img,staticFile,useCurrentFrame,interpolate} from 'remotion';
import type {Scene} from '../schema';
import {Callout} from './Callout';
import {HighlightRect,Cursor} from './Highlight';
import {fitTransform} from '../../../../packages/visual-production/src/geometry.mjs';
interface Props {scene:Scene;width:number;height:number;accent:string;durationInFrames:number}
export const SceneView:React.FC<Props>=({scene,width,height,accent,durationInFrames})=>{
  const frame=useCurrentFrame();
  if(!scene.sourceWidth || !scene.sourceHeight) throw new Error('Scene must carry measured source dimensions; use the staging renderer');
  const sourceWidth=scene.sourceWidth,sourceHeight=scene.sourceHeight;
  const zoom=scene.zoom && durationInFrames>1 ? interpolate(frame,[0,durationInFrames-1],scene.zoom,{extrapolateLeft:'clamp',extrapolateRight:'clamp'}) : scene.zoom?.[0] ?? 1;
  const t=fitTransform({sourceWidth,sourceHeight,width,height,fit:scene.fit ?? 'cover',zoom});
  const style:React.CSSProperties={position:'absolute',width:sourceWidth,height:sourceHeight,left:0,top:0};
  return <AbsoluteFill style={{overflow:'hidden'}}>
    <div style={{...style,transformOrigin:'0 0',transform:`translate(${t.x}px,${t.y}px) scale(${t.scale})`}}>
      {/\.(mp4|mov|webm|mkv)$/i.test(scene.src)?<OffthreadVideo src={staticFile(scene.src)} style={style}/>:<Img src={staticFile(scene.src)} style={style}/>}
      {(scene.highlights??[]).map((h,i)=><HighlightRect key={`h${i}`} {...h} scaleX={1} scaleY={1} accent={accent}/>)}
      {(scene.cursors??[]).map((c,i)=><Cursor key={`c${i}`} {...c} scaleX={1} scaleY={1} accent={accent}/>)}
    </div>
    {(scene.callouts??[]).map((c,i)=><Callout key={`c${i}`} {...c} accent={accent}/>)}
  </AbsoluteFill>;
};
