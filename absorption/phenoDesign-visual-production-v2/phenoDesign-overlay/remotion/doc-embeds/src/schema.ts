/** Compatible expansion of the PR87 EmbedSpec. Runtime validation lives in visual-production/contracts.mjs.
 * Source provenance: KooshaPari/PhenoDesign PR87; this file modified September 15, 2026.
 */
export interface Callout {text:string;subText?:string;color?:string;atSec:number;durationSec?:number;anchor?:'top-left'|'top-right'|'bottom-left'|'bottom-right'}
export interface Highlight {x:number;y:number;width:number;height:number;color?:string;label?:string;atSec:number;durationSec?:number;style?:'pulse'|'static'}
export interface CursorHighlight {x:number;y:number;atSec:number;kind?:'ripple'|'ring';color?:string;durationSec?:number}
export interface Scene {
  src:string; holdSec?:number; clipSec?:number;
  /** Measured source pixel dimensions. Never substitute output dimensions. */
  sourceWidth?:number; sourceHeight?:number; fit?:'cover'|'contain'; zoom?:[number,number];
  callouts?:Callout[];highlights?:Highlight[];cursors?:CursorHighlight[];
}
export interface EmbedSpec {id:string;title:string;subtitle?:string;width?:number;height?:number;fps?:number;accent?:string;audioSrc?:string;scenes:Scene[]}
export const DEFAULTS={width:1280,height:800,fps:30,accent:'#34d399'} as const;
