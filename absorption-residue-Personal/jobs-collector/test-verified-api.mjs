import test from 'node:test';
import assert from 'node:assert/strict';
import {readVerified} from './verified-api.js';
function mock(rows,has=true){return {prepare(){return {first:async()=>has?{name:'job_verification'}:null,all:async()=>({results:rows})};}};}
test('missing schema is unknown, not 0',async()=>{const x=await readVerified(mock([],false));assert.equal(x.verified_eligible_la,null)});
test('no evidence yields zero counted matches',async()=>{const x=await readVerified(mock([]));assert.equal(x.verified_eligible_la,0)});
test('truncated evidence does not report a false number',async()=>{const x=await readVerified(mock(Array(501).fill({})));assert.equal(x.verified_eligible_la,null)});
