import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import worker, {SEED, boot, step, finalize} from './index.js';
import {isPalantirPosting} from './employer-policy.js';
import {readVerified} from './verified-api.js';
import {assessEligibility, isValidVerificationRecord, canonicalJobKey, REQUIRED_CHECKS} from './verification.js';
import {normalizeWhatnotObservation} from './ingestion.js';
import {ingestOfficialWhatnot} from './whatnot-import.js';
import {SQLiteD1} from './testing/sqlite-d1.mjs';

const DAY='2026-10-14', UUID='00000000-0000-4000-8000-000000000000';
const response=value=>Response.json(value);
async function database(t, boards=[]) {
  const db=new SQLiteD1();t.after(()=>db.close());await boot(db);
  await db.prepare('DELETE FROM board').run();
  for(const b of boards) await db.prepare('INSERT INTO board(id,ats,slug,company,tier,skip,last_day,last_ok,last_error) VALUES(?,?,?,?,?,?,?,?,?)')
    .bind(b.id,b.ats||'lever',b.slug||'innocent',b.company||'Example',b.tier||1,b.skip||0,b.day||null,b.ok??null,b.error||null).run();
  return db;
}
async function job(db, id, {board=1,title='Software Engineer',url='https://jobs.lever.co/innocent/'+UUID,
  source='board',status='open',detail=DAY}={}) {
  await db.prepare('INSERT INTO job(id,board_id,ext_id,title,location,loc_rank,url,first_seen,last_seen,status,detail_day,source) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)')
    .bind(id,board,'1',title,'Los Angeles, CA',3,url,DAY,DAY,status,detail,source).run();
}
async function get(db,path='/') {return (await worker.fetch(new Request('https://offline.test'+path),{JOBS:db})).json();}
function fetchMock(t, fn) {
  const calls=[];t.mock.method(globalThis,'fetch',async (url,options)=>{calls.push(String(url));return fn(String(url),options);});
  return calls;
}
async function verificationSchema(db) {
  const text=readFileSync(new URL('./migrations/0002-verification.sql',import.meta.url),'utf8');
  await db.batch(text.split(';').map(x=>x.trim()).filter(Boolean).map(x=>db.prepare(x)));
}
function eligibility(url, company='Example') {
  const stamp=new Date().toISOString(), evidence={};
  for(const field of REQUIRED_CHECKS) evidence[field]={status:'pass',sourceUrl:url,checkedAt:stamp,
    excerpt:'Employer confirms '+field,sourceSignature:'signature'};
  return {jobId:canonicalJobKey(url),company,officialUrl:url,sourceSignature:'signature',evidence};
}
async function verifiedRow(db, url, company) {
  const record=eligibility(url,company), stamp=new Date().toISOString();
  await db.prepare('INSERT INTO canonical_job(canonical_id,company,title,official_url,geography,first_seen,last_seen,content_signature,state) VALUES(?,?,?,?,?,?,?,?,?)')
    .bind(record.jobId,company,'Software Engineer',url,'la_metro',stamp,stamp,'signature','active_verified').run();
  await db.prepare('INSERT INTO job_verification(canonical_id,checked_at,source_signature,official_url,verification_status,evidence_json) VALUES(?,?,?,?,?,?)')
    .bind(record.jobId,stamp,'signature',url,'active_verified',JSON.stringify(record.evidence)).run();
}

test('Palantir is absent from the seed; fresh installations do not source it',async t=>{
  assert.ok(SEED.every(([,slug,company])=>!isPalantirPosting({company},{slug})));
  const db=new SQLiteD1();t.after(()=>db.close());await boot(db);
  assert.equal((await db.prepare("SELECT count(*) n FROM board WHERE lower(slug)='palantir'").first()).n,0);
});
test('existing Palantir boards are disabled idempotently without erasing history or owners',async t=>{
  const db=await database(t,[{id:1,slug:'palantir',company:'Legacy alias',day:'2026-10-13',ok:0,error:'keep history'},
    {id:2,ats:'greenhouse',slug:'alias',company:'PALANTIR Technologies'},
    {id:3,slug:'safe',company:'Example',skip:1,tier:3}]);
  await job(db,'lever:palantir:old');
  await job(db,'legacy-title',{board:3,source:'github-list',title:'Palantir | Staff Software Engineer',status:'excluded_title'});
  // boot() gates its exclusion scan to once per LA day via boot_meta; the
  // fixture boot already consumed today's pass, so reset the mark to exercise it.
  await db.prepare("DELETE FROM boot_meta WHERE k='exclusion_day'").run();
  await boot(db);await boot(db);
  const rows=(await db.prepare('SELECT id,company,tier,skip,last_day,last_ok,last_error FROM board ORDER BY id').all()).results;
  assert.deepEqual(rows[0],{id:1,company:'Legacy alias',tier:1,skip:1,last_day:'2026-10-13',last_ok:0,last_error:'keep history'});
  assert.equal(rows[1].skip,1);assert.equal(rows[2].tier,3);assert.equal(rows[2].skip,1);
  assert.equal((await db.prepare('SELECT status,first_seen FROM job').first()).status,'excluded_employer');
  assert.equal((await db.prepare('SELECT first_seen FROM job').first()).first_seen,DAY);
  assert.equal((await db.prepare("SELECT status FROM job WHERE id='legacy-title'").first()).status,'excluded_employer');
});
test('a persisted Palantir board cannot fetch or turn an empty eligible inventory healthy',async t=>{
  const db=await database(t,[{id:1,slug:'palantir',company:'Palantir'}]);
  const calls=fetchMock(t,()=>{throw new Error('excluded source must not fetch');});
  assert.equal(await step({JOBS:db},DAY),'done');assert.equal(calls.length,0);
  const run=await db.prepare('SELECT * FROM run').first();
  assert.equal(run.ok,0);assert.equal(run.boards_ok,0);assert.equal(run.boards_failed,0);
  assert.equal((await get(db,'/health')).health,'degraded');
});
test('company fields, object names and official ATS/domain identities are employer evidence',()=>{
  for(const row of [{company:'PaLaNtIr Technologies, Inc.'},{companyName:'Palantir'},
    {company:{name:'Palantir'}},{hiringOrganization:{legalName:'Palantir Technologies'}},
    {categories:{employer:'Palantir'}},{url:'https://jobs.lever.co/palantir/'+UUID},
    {url:'https://jobs.eu.lever.co/PALANTIR/'+UUID},{url:'https://jobs.ashbyhq.com/palantir/'+UUID},
    {url:'https://boards.greenhouse.io/palantir/jobs/123'},
    {url:'https://careers.palantir.com/jobs/123'},
    {url:'https://palantir.wd5.myworkdayjobs.com/en-US/Careers/job/Engineer_R123'},
    {url:'https://jobs.lever.co/pal%61ntir/'+UUID},
    {id:'lever:palantir:'+UUID}]) assert.equal(!!isPalantirPosting(row),true,JSON.stringify(row));
  for(const row of [{company:'Example',title:'Palantir integration engineer'},
    {url:'https://jobs.lever.co/innocent/'+UUID+'?ref=palantir.com'},
    {url:'https://notpalantir.com/jobs/123'}, {categories:{team:'Palantir connectors'}}]) {
    assert.equal(!!isPalantirPosting(row),false,JSON.stringify(row));
  }
});

for(const ats of ['greenhouse','lever','ashby','ashby-hosted']) test(`${ats} rejects Palantir returned by another board and retires its cached role`,async t=>{
  const boardAts=ats==='ashby-hosted'?'ashby':ats;
  const db=await database(t,[{id:1,ats:boardAts}]);
  const badId=boardAts+':innocent:1';await job(db,badId);
  const rows=[{id:1,title:'Software Engineer',text:'Software Engineer',company:{name:'Palantir'},
    location:{name:'Los Angeles, CA'},absolute_url:'https://job-boards.greenhouse.io/innocent/jobs/1',
    hostedUrl:'https://jobs.lever.co/innocent/1',jobUrl:'https://jobs.ashbyhq.com/innocent/1',locationName:'Los Angeles, CA'},
    {id:2,title:'Software Engineer',text:'Software Engineer',company:'Example',location:{name:'Los Angeles, CA'},
    absolute_url:'https://job-boards.greenhouse.io/innocent/jobs/2',hostedUrl:'https://jobs.lever.co/innocent/2',
    jobUrl:'https://jobs.ashbyhq.com/innocent/2',locationName:'Los Angeles, CA'}];
  const calls=fetchMock(t,url=>{
    if(ats==='ashby-hosted'&&url.includes('posting-api'))return new Response('{}',{status:404});
    if(ats==='ashby-hosted')return response({data:{jobBoard:{jobPostings:rows}}});
    if(url.endsWith('/jobs/2'))return response({content:'2 years experience. $120k - $150k'});
    if(ats==='greenhouse')return response({jobs:rows});
    const postings=rows.map(x=>({...x,location:'Los Angeles, CA',categories:{location:'Los Angeles, CA'}}));
    return response(ats==='lever'?postings:{jobs:postings});
  });
  assert.equal(await step({JOBS:db},DAY),'board innocent kept 1/2');
  if(ats==='greenhouse')assert.equal(await step({JOBS:db},DAY),'details 1');
  assert.equal(await step({JOBS:db},DAY),'done');
  assert.equal((await db.prepare('SELECT status FROM job WHERE id=?').bind(badId).first()).status,'excluded_employer');
  const open=(await get(db,'/candidates'));assert.equal(open.length,1);assert.equal(open[0].id,boardAts+':innocent:2');
  assert.ok(calls.every(url=>!url.endsWith('/jobs/1')));
  const run=await db.prepare('SELECT * FROM run').first();assert.equal(run.ok,1);assert.equal(run.boards_failed,0);
});
test('board-level Palantir metadata retires an incorrectly labeled source',async t=>{
  const db=await database(t,[{id:1,ats:'greenhouse'}]);await job(db,'greenhouse:innocent:old');
  const calls=fetchMock(t,()=>response({company:'Palantir',jobs:[]}));
  assert.equal(await step({JOBS:db},DAY),'board excluded innocent');
  assert.equal(await step({JOBS:db},DAY),'done');assert.equal(calls.length,1);
  assert.equal((await db.prepare('SELECT skip FROM board').first()).skip,1);
  assert.equal((await db.prepare('SELECT ok FROM run').first()).ok,0);
});
test('a quarantined role cannot reopen when a later feed omits employer metadata',async t=>{
  const db=await database(t,[{id:1}]);await job(db,'lever:innocent:1',{status:'excluded_employer'});
  fetchMock(t,()=>response([{id:1,text:'Software Engineer',categories:{location:'Los Angeles, CA'},
    hostedUrl:'https://jobs.lever.co/innocent/1'}]));
  assert.equal(await step({JOBS:db},DAY),'board innocent kept 0/1');
  assert.equal((await db.prepare('SELECT status FROM job').first()).status,'excluded_employer');
});
test('Palantir detail requests are suppressed even under an unrelated board',async t=>{
  const db=await database(t,[{id:1,ats:'greenhouse',day:DAY,ok:1}]);
  await job(db,'greenhouse:innocent:1',{url:'https://jobs.lever.co/palantir/'+UUID,detail:null});
  const calls=fetchMock(t,()=>{throw new Error('excluded detail must not fetch');});
  // Reset the once-per-day exclusion mark so step()'s boot rescans (see boot_meta gate).
  await db.prepare("DELETE FROM boot_meta WHERE k='exclusion_day'").run();
  assert.equal(await step({JOBS:db},DAY),'done');assert.equal(calls.length,0);
  assert.equal((await db.prepare('SELECT status FROM job').first()).status,'excluded_employer');
});
test('authenticated ingestion rejects company/URL/alternate-source bypasses before staging',async t=>{
  const db=await database(t);
  const rows=[{source:'github-list',company:'PALANTIR',title:'Software Engineer',url:'https://example.test/job'},
    {source:'github-list',company:'Example',title:'Software Engineer',url:'https://jobs.lever.co/palantir/'+UUID},
    {source:'whatnot-official',company:'Palantir',id:UUID,title:'Software Engineer',
      official_url:'https://www.whatnot.com/careers/roles/'+UUID,locations:['Los Angeles, CA']},
    {source:'github-list',company:'Example',title:'Software Engineer',url:'https://jobs.lever.co/innocent/'+UUID,loc_rank:3}];
  const req=new Request('https://offline.test/ingest',{method:'POST',headers:{authorization:'Bearer unit-test-only'},body:JSON.stringify({rows})});
  const result=await worker.fetch(req,{JOBS:db,INGEST_TOKEN:'unit-test-only'});
  assert.equal(result.status,200);assert.deepEqual(await result.json(),{added:1,upd:0,dup:0,bad:3});
  assert.equal((await db.prepare('SELECT count(*) n FROM job').first()).n,1);
});
test('official Whatnot normalization and its direct importer reject conflicting Palantir metadata',async()=>{
  const row={source:'whatnot-official',id:UUID,title:'Software Engineer',company:'Palantir',
    official_url:'https://www.whatnot.com/careers/roles/'+UUID,locations:['Los Angeles, CA']};
  assert.equal(normalizeWhatnotObservation(row),null);
  assert.deepEqual(await ingestOfficialWhatnot({prepare(){throw new Error('must reject before DB access');}},row,{}),{added:0,dup:0,bad:1});
});
test('read-only candidates, review, boards and alerts hide existing Palantir without deleting audit data',async t=>{
  const db=await database(t,[{id:1,slug:'palantir',company:'Palantir'},{id:2,slug:'innocent',company:'Example'}]);
  await job(db,'lever:palantir:old');await job(db,'good',{board:2});
  await job(db,'legacy',{board:2,source:'github-list',title:'Palantir Technologies | Software Engineer'});
  await db.prepare('INSERT INTO run(day,ok,boards_ok,boards_failed,finished_at) VALUES(?,0,1,1,?)').bind(DAY,new Date().toISOString()).run();
  for(const id of ['lever:palantir:old','good','legacy','gh:https://jobs.lever.co/palantir/orphan']) {
    await db.prepare('INSERT INTO alert(day,level,job_id,reason) VALUES(?,?,?,?)').bind(DAY,'priority',id,'historical').run();
  }
  assert.deepEqual((await get(db,'/candidates')).map(x=>x.id),['good']);
  assert.deepEqual((await get(db,'/review')).candidates.map(x=>x.id),['good']);
  assert.deepEqual((await get(db,'/boards')).map(x=>x.slug),['innocent']);
  assert.deepEqual((await get(db)).alerts.map(x=>x.job_id),['good']);
  assert.equal((await db.prepare('SELECT count(*) n FROM alert').first()).n,4);
  assert.equal((await db.prepare("SELECT status FROM job WHERE id='lever:palantir:old'").first()).status,'open');
  assert.equal((await get(db,'/health')).latest_run.boards_failed,1);
});
test('new priority alerts, events and run counts omit excluded cached and aggregator jobs',async t=>{
  const db=await database(t,[{id:1,slug:'palantir',company:'Palantir',day:DAY,ok:0},{id:2,day:DAY,ok:1}]);
  await job(db,'lever:palantir:old');await job(db,'good',{board:2});
  await job(db,'legacy',{board:2,source:'github-list',title:'Palantir | Software Engineer'});
  await db.prepare('INSERT INTO run(day,ok,boards_ok) VALUES(?,1,1)').bind('2026-10-13').run();
  assert.equal(await finalize(db,DAY),true);
  assert.deepEqual((await db.prepare('SELECT job_id FROM alert').all()).results,[{job_id:'good'}]);
  assert.deepEqual((await db.prepare('SELECT job_id FROM job_event').all()).results,[{job_id:'good'}]);
  const run=await db.prepare('SELECT * FROM run WHERE day=?').bind(DAY).first();
  assert.equal(run.ok,1);assert.equal(run.boards_ok,1);assert.equal(run.boards_failed,0);assert.equal(run.candidates,1);
});
test('Palantir cannot become application eligible even with six passing evidence checks',()=>{
  for(const record of [eligibility('https://jobs.lever.co/palantir/'+UUID),
    eligibility('https://jobs.lever.co/innocent/'+UUID,'Palantir Technologies')]) {
    assert.equal(assessEligibility(record).status,'ineligible');assert.equal(isValidVerificationRecord(record),false);
  }
  assert.equal(assessEligibility(eligibility('https://jobs.lever.co/innocent/'+UUID)).status,'active_verified');
});
test('verified projection excludes Palantir and quarantined identities while retaining canonical history',async t=>{
  const db=await database(t,[{id:1}]);await verificationSchema(db);
  await verifiedRow(db,'https://jobs.lever.co/palantir/'+UUID,'Palantir');
  await verifiedRow(db,'https://jobs.lever.co/innocent/'+UUID,'Example');
  let result=await readVerified(db);assert.equal(result.total_verified,1);assert.equal(result.jobs[0].company,'Example');
  await job(db,canonicalJobKey('https://jobs.lever.co/innocent/'+UUID),{status:'excluded_employer'});
  result=await readVerified(db);assert.equal(result.total_verified,0);
  assert.equal((await db.prepare('SELECT count(*) n FROM canonical_job').first()).n,2);
});
test('canonical-only verification schemas retain the allowed employer projection',async t=>{
  const db=new SQLiteD1();t.after(()=>db.close());await verificationSchema(db);
  await verifiedRow(db,'https://jobs.lever.co/innocent/'+UUID,'Example');
  await verifiedRow(db,'https://jobs.lever.co/palantir/'+UUID,'Palantir');
  assert.equal((await readVerified(db)).total_verified,1);
});
test('excluded canonical rows cannot consume the verified counting window',async t=>{
  const db=await database(t);await verificationSchema(db);
  const statements=[];
  for(let i=0;i<501;i++) {
    const id='lever:palantir:'+i,url='https://jobs.lever.co/palantir/'+i,stamp=new Date().toISOString();
    statements.push(db.prepare('INSERT INTO canonical_job(canonical_id,company,title,official_url,first_seen,last_seen) VALUES(?,?,?,?,?,?)')
      .bind(id,'Palantir','Software Engineer',url,stamp,stamp));
    statements.push(db.prepare('INSERT INTO job_verification(canonical_id,checked_at,source_signature,official_url,verification_status,evidence_json) VALUES(?,?,?,?,?,?)')
      .bind(id,stamp,'signature',url,'active_verified','{}'));
  }
  for(let i=0;i<statements.length;i+=40)await db.batch(statements.slice(i,i+40));
  await verifiedRow(db,'https://jobs.lever.co/innocent/'+UUID,'Example');
  const result=await readVerified(db);assert.equal(result.total_verified,1);assert.equal(result.truncated,undefined);
});
