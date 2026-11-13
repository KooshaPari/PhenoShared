import {test} from 'node:test';
import assert from 'node:assert/strict';
// @ts-ignore
import {onRequest} from '../functions/api/asks/[[path]].js';
const req=(q='',method='GET')=>new Request('https://x/api/asks/'+q,{method});
test('asks returns explicitly labeled private snapshot when data unavailable',async()=>{
 const absent=await onRequest({request:req(),env:{},params:{}}); assert.equal(absent.status,200);assert.equal((await absent.json()).source_mode,'snapshot');
 const db={prepare:()=>{throw Error('quota');}};
 const r=await onRequest({request:req(),env:{COCKPIT_DB:db},params:{}});
 assert.equal(r.status,200);const d=await r.json();assert.equal(d.source_mode,'snapshot');assert.ok(d.snapshot_captured_at);assert.equal(d.asks.length,50);assert.equal(r.headers.get('cache-control'),'private, no-store');
});
test('asks uses one bounded indexed query, keyset pagination and allowlisted DTO',async()=>{
 let queries=0;const db={prepare:(sql:string)=>{queries++;assert.match(sql,/reviewed=1 AND id>\?/);assert.match(sql,/LIMIT 51/);return{bind:(n:number)=>{assert.equal(n,50);return{all:async()=>({results:Array.from({length:51},(_,i)=>({id:i+51,original_text:'<script>x</script>',interpretation:'ask',reported_state:'DONE',verified_state:'needs_reconciliation',internal_owner:'CANARY'}))})};}};}};
 const r=await onRequest({request:req('?after=50'),env:{COCKPIT_DB:db},params:{}});const d=await r.json();
 assert.equal(queries,1);assert.equal(d.asks.length,50);assert.equal(d.next_after,100);assert.ok(!JSON.stringify(d).includes('CANARY'));assert.equal(r.headers.get('cache-control'),'private, no-store');
});
test('asks blocks write, invalid cursor and unknown path',async()=>{
 assert.equal((await onRequest({request:req('','POST'),env:{},params:{}})).status,405);
 assert.equal((await onRequest({request:req('?after=1%20OR%201'),env:{COCKPIT_DB:{}},params:{}})).status,400);
 assert.equal((await onRequest({request:req(),env:{},params:{path:['bad']}})).status,404);
});

test('snapshot fallback completes all114 unique asks with7 explicitly missing originals',async()=>{
 let after=0,all=[];
 do{const r=await onRequest({request:req('?after='+after),env:{},params:{}});const d=await r.json();all.push(...d.asks);after=d.next_after;}while(after!==null);
 assert.equal(all.length,114);assert.equal(new Set(all.map(x=>x.id)).size,114);assert.equal(all.filter(x=>!x.original_text).length,7);
 assert.equal(all.filter(x=>x.verified_state==='Pending review').length,114);
 assert.ok(all.every(x=>!('source_notes' in x)&&!('owner_todo_or_agent' in x)));
});
