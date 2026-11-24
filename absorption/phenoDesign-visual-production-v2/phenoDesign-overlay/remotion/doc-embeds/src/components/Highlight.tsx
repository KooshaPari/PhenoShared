/** Modified PR87 component: half-open intervals and a single finite click ripple. */
import React from 'react';
import {useCurrentFrame,useVideoConfig} from 'remotion';
import type {Highlight as H,CursorHighlight as C} from '../schema';
interface Scale {scaleX:number;scaleY:number;accent:string}
export const HighlightRect:React.FC<H&Scale>=({x,y,width,height,color,label,atSec,durationSec,style='pulse',scaleX,scaleY,accent})=>{
 const frame=useCurrentFrame(),{fps}=useVideoConfig(),rel=frame-Math.round(atSec*fps);
 if(rel<0||(durationSec!==undefined&&rel>=Math.max(1,Math.round(durationSec*fps))))return null;
 const stroke=color??accent,pulse=style==='pulse'?0.675+0.325*Math.sin(rel/fps*Math.PI*2):1;
 return <div style={{position:'absolute',left:x*scaleX,top:y*scaleY,width:width*scaleX,height:height*scaleY,boxSizing:'border-box',border:`4px solid ${stroke}`,borderRadius:6,opacity:pulse,pointerEvents:'none'}}>
 {label&&<div style={{position:'absolute',top:-34,left:0,background:stroke,color:'#0b0f14',fontSize:16,fontWeight:700,fontFamily:'Arial, sans-serif',padding:'3px 10px',borderRadius:5,whiteSpace:'nowrap'}}>{label}</div>}
 </div>;
};
export const Cursor:React.FC<C&Scale>=({x,y,atSec,kind='ripple',durationSec,color,scaleX,scaleY,accent})=>{
 const frame=useCurrentFrame(),{fps}=useVideoConfig(),rel=frame-Math.round(atSec*fps);
 const duration=durationSec??(kind==='ripple'?1:undefined);
 if(rel<0||(duration!==undefined&&rel>=Math.max(1,Math.round(duration*fps))))return null;
 const t=duration===undefined?0:Math.min(1,rel/Math.max(1,Math.round(duration*fps)-1));
 const size=kind==='ring'?28:16+74*t;
 return <div style={{position:'absolute',left:x*scaleX-size/2,top:y*scaleY-size/2,width:size,height:size,borderRadius:'50%',boxSizing:'border-box',border:`3px solid ${color??accent}`,opacity:kind==='ring'?1:0.9*(1-t),pointerEvents:'none'}}/>;
};
