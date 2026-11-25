import test from 'node:test';
import assert from 'node:assert/strict';
import {ingestOfficialWhatnot} from './whatnot-import.js';

const id='00000000-0000-4000-8000-000000000000';
const row={
  source:'whatnot-official',id,
  title:'Software Engineer, 2027 New Grad',
  official_url:'https://www.whatnot.com/careers/roles/'+id,
  locations:['New York, NY','San Francisco, CA','Los Angeles, CA','Seattle, WA']
};

function fakeDb(existing=null){
 const db={
  batches:[], statements:[],
  prepare(sql){
   const stmt={sql,args:[],
    bind(...args){this.args=args;db.statements.push(this);return this;},
    async first(){return existing;}
   };
   return stmt;
  },
  async batch(statements){db.batches.push(statements);return statements.map(()=>({success:true}));}
 };
 return db;
}
const ctx={whatnotBid:26,day:'2026-10-12',
  locRank:x=>x.includes('Los Angeles')?3:0,
  score:x=>({s:x.loc_rank*10,flags:['yoe_unknown','comp_unknown']})};

test('atomic official catalog source ingestion creates provenance and canonical identity',async()=>{
 const db=fakeDb();
 const result=await ingestOfficialWhatnot(db,row,ctx);
 assert.deepEqual(result,{added:1,dup:0,bad:0});
 assert.equal(db.batches.length,1);
 assert.equal(db.batches[0].length,3);
 const [canonical,source,legacy]=db.batches[0];
 assert.match(canonical.sql,/INSERT INTO canonical_job/);
 assert.equal(canonical.args[0],'ashby:whatnot:'+id);
 assert.equal(canonical.args[4],'la_metro');
 assert.equal(canonical.args[7],null);
 assert.equal(canonical.args[8],'discovered');
 assert.match(source.sql,/INSERT INTO canonical_source/);
 assert.equal(source.args[0],'whatnot-official');
 assert.equal(source.args[1],id);
 assert.match(source.args[7],/^[0-9a-f]{64}$/);
 assert.match(legacy.sql,/INSERT INTO job/);
 assert.equal(legacy.args[13],'whatnot-official');
 assert.equal(legacy.args[14],'catalog-listing-only');
});
test('cannot ingest invalid or unrelated catalog URLs',async()=>{
 const db=fakeDb();
 assert.deepEqual(await ingestOfficialWhatnot(db,{...row,official_url:'https://example.org/jobs/'+id},ctx),
  {added:0,dup:0,bad:1});
 assert.equal(db.batches.length,0);
});
test('a conflicting legacy URL does not overwrite another requisition',async()=>{
 const db=fakeDb({id:'different:job'});
 assert.deepEqual(await ingestOfficialWhatnot(db,row,ctx),{added:0,dup:1,bad:0});
 assert.equal(db.batches.length,0);
});
