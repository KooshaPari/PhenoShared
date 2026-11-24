import test from 'node:test';
import assert from 'node:assert/strict';
import worker, {boot} from './index.js';
import {SQLiteD1} from './testing/sqlite-d1.mjs';

const UUID='00000000-0000-4000-8000-000000000000';
const TOKEN='unit-test-only';
async function database(t, boards=[]) {
  const db=new SQLiteD1();t.after(()=>db.close());await boot(db);
  await db.prepare('DELETE FROM board').run();
  for(const b of boards) await db.prepare('INSERT INTO board(id,ats,slug,company,tier,skip,last_day,last_ok,last_error) VALUES(?,?,?,?,?,?,?,?,?)')
    .bind(b.id,b.ats||'lever',b.slug||'innocent',b.company||'Example',b.tier||1,b.skip||0,b.day||null,b.ok??null,b.error||null).run();
  return db;
}
const row=(n,over={})=>({source:'github-list',company:'Example',title:'Software Engineer',
  url:'https://jobs.example.test/'+n+'/'+UUID,loc_rank:3,list:'unit-test',link_check:'unverified',...over});
async function ingest(db,rows) {
  return worker.fetch(new Request('https://offline.test/ingest',{method:'POST',
    headers:{authorization:'Bearer '+TOKEN},body:JSON.stringify({rows})}),{JOBS:db,INGEST_TOKEN:TOKEN});
}

test('ingest batches row upserts and stays idempotent across replays',async t=>{
  const db=await database(t);
  const rows=[row(1),row(2),row(3),{source:'github-list',company:'Example',title:'',url:''}];
  const first=await ingest(db,rows);
  assert.equal(first.status,200);
  assert.deepEqual(await first.json(),{added:3,upd:0,dup:0,bad:1});
  assert.equal((await db.prepare("SELECT count(*) n FROM job WHERE source='github-list'").first()).n,3);
  const replay=await ingest(db,rows);
  assert.equal(replay.status,200);
  assert.deepEqual(await replay.json(),{added:0,upd:3,dup:0,bad:1});
  assert.equal((await db.prepare("SELECT count(*) n FROM job WHERE source='github-list'").first()).n,3);
});

test('ingest rejects a different owner id for a known url as dup',async t=>{
  const db=await database(t);
  await db.prepare("INSERT INTO job(id,board_id,ext_id,title,url,first_seen,last_seen,status,source) VALUES('lever:example:1',1,'1','Engineer',?,'2026-10-20','2026-10-20','open','board')")
    .bind('https://jobs.example.test/1/'+UUID).run();
  const result=await ingest(db,[row(1)]);
  assert.equal(result.status,200);
  assert.deepEqual(await result.json(),{added:0,upd:0,dup:1,bad:0});
});

test('employer exclusion scan runs at most once per day via boot_meta',async t=>{
  const db=await database(t,[{id:1,slug:'palantir',company:'Palantir'}]);
  // The fixture's boot already consumed today's scan. A new Palantir row
  // inserted afterwards must survive a same-day boot (gate holds).
  await db.prepare("INSERT INTO job(id,board_id,ext_id,title,url,first_seen,last_seen,status,source) VALUES('lever:palantir:1',1,'1','Palantir | Engineer','https://jobs.lever.co/palantir/"+UUID+"','2026-10-20','2026-10-20','open','board')").run();
  await boot(db);
  assert.equal((await db.prepare("SELECT status FROM job WHERE id='lever:palantir:1'").first()).status,'open');
  // A new day (mark cleared) rescans and excludes.
  await db.prepare("DELETE FROM boot_meta WHERE k='exclusion_day'").run();
  await boot(db);
  assert.equal((await db.prepare("SELECT status FROM job WHERE id='lever:palantir:1'").first()).status,'excluded_employer');
});

test('ingest surfaces internal errors as 500 with the error name',async t=>{
  const db=await database(t);
  await db.close();
  const result=await ingest(db,[row(1)]);
  assert.equal(result.status,500);
  assert.match(await result.text(),/^ingest error: /);
});
