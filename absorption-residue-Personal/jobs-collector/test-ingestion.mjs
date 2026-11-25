import test from 'node:test';
import assert from 'node:assert/strict';
import {normalizeWhatnotObservation} from './ingestion.js';
const id='00000000-0000-4000-8000-000000000000';
const good={source:'whatnot-official',id,title:'Software Engineer, 2027 New Grad',
 official_url:'https://www.whatnot.com/careers/roles/'+id,
 locations:['Los Angeles, CA','Seattle, WA','Los Angeles, CA']};
test('maps official catalog observation to stable canonical key',()=>{
 const x=normalizeWhatnotObservation(good);
 assert.equal(x.id,'ashby:whatnot:'+id);
 assert.equal(x.location,'Los Angeles, CA | Seattle, WA');
 assert.match(x.flags,/unverified/);
});
test('rejects forged or unrelated source and links',()=>{
 assert.equal(normalizeWhatnotObservation({...good,source:'github-list'}),null);
 assert.equal(normalizeWhatnotObservation({...good,official_url:'https://other.example/jobs/'+id}),null);
 assert.equal(normalizeWhatnotObservation({...good,id:'invalid'}),null);
});
test('rejects missing locations or untrusted title markup',()=>{
 assert.equal(normalizeWhatnotObservation({...good,locations:[]}),null);
 assert.equal(normalizeWhatnotObservation({...good,title:'<script>oops</script>'}),null);
});
