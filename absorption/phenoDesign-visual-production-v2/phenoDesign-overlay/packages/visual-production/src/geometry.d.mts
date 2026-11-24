export type Transform={scale:number;x:number;y:number};
export function fitTransform(input:{sourceWidth:number;sourceHeight:number;width:number;height:number;fit?:'cover'|'contain';zoom?:number}):Transform;
export function mapPoint(point:{x:number;y:number},transform:Transform):{x:number;y:number};
export function mapRect(rect:{x:number;y:number;width:number;height:number},transform:Transform):{x:number;y:number;width:number;height:number};
export function frameWindow(atSec:number,durationSec:number,fps:number):{start:number;end:number};
export function activeAt(frame:number,window:{start:number;end:number}):boolean;
export function sceneFrames(scene:{holdSec?:number;clipSec?:number},fps:number):number;
export function sceneTimeline(scenes:{holdSec?:number;clipSec?:number}[],fps:number):{start:number;end:number;durationInFrames:number}[];
