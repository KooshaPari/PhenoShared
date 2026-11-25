import test from 'node:test';
import assert from 'node:assert/strict';
import {
 canonicalJobKey,normalizeOfficialUrl,assessEligibility,isValidVerificationRecord,
 REQUIRED_CHECKS
} from './verification.js';

const stamp='2026-10-12T19:30:00Z',hash='abc123';
function record(overrides={}) {
 const fields={};
 for (const f of REQUIRED_CHECKS) fields[f]={
  status:'pass',sourceUrl:'https://jobs.ashbyhq.com/whatnot/00000000-0000-4000-8000-000000000000',
  checkedAt:stamp,excerpt:'Employer page confirms '+f,sourceSignature:hash
 };
 return {jobId:'whatnot:role1',
  officialUrl:'https://www.whatnot.com/careers/roles/00000000-0000-4000-8000-000000000000',
  sourceSignature:hash,evidence:fields,...overrides};
}
test('canonical identity unifies official Whatnot/Ashby URLs',()=>{
 const a='https://www.whatnot.com/careers/roles/AAAAAAAA-BBBB-CCCC-DDDD-EEEEEEEEEEEE?utm_source=search';
 const b='https://jobs.ashbyhq.com/whatnot/00000000-0000-4000-8000-000000000000/application';
 assert.equal(canonicalJobKey(a),canonicalJobKey(b));
});
test('Greenhouse index and official posting normalize tracking query',()=>{
 const a='https://boards.greenhouse.io/ziprecruiter/jobs/8127108?gh_jid=8127108';
 const b='https://job-boards.greenhouse.io/ziprecruiter/jobs/8127108';
 assert.equal(canonicalJobKey(a),canonicalJobKey(b));
});
test('different requisitions are never deduplicated by identical title',()=>{
 assert.notEqual(canonicalJobKey('https://jobs.ashbyhq.com/whatnot/00000000-0000-4000-8000-000000000000'),
 canonicalJobKey('https://jobs.ashbyhq.com/whatnot/00000000-0000-4000-8000-000000000000'));
});
test('tracking URLs, unsupported URLs are rejected or normalized',()=>{
 assert.equal(normalizeOfficialUrl('http://example.com/job'),null);
 assert.equal(normalizeOfficialUrl('https://example.com/job?utm_source=github#apply'),'https://example.com/job');
});
test('all independently sourced checks can yield a verified result',()=>{
 assert.equal(assessEligibility(record(),stamp).status,'active_verified');
 assert.equal(isValidVerificationRecord(record(),stamp),true);
});
test('salary undisclosed from employer is not invented',()=>{
 const r=record();
 r.evidence.compensation.status='undisclosed';
 assert.equal(assessEligibility(r,stamp).status,'active_verified');
});
test('a single unknown field blocks promotion',()=>{
 const r=record();delete r.evidence.graduation;
 assert.equal(assessEligibility(r,stamp).status,'needs_review');
});
test('conditional location blocks promotion',()=>{
 const r=record();r.evidence.location.status='conditional';
 assert.equal(assessEligibility(r,stamp).status,'needs_review');
});
test('a definitive fail remains ineligible',()=>{
 const r=record();r.evidence.experience.status='fail';
 assert.equal(assessEligibility(r,stamp).status,'ineligible');
});
test('stale evidence cannot stay verified',()=>{
 const r=record();
 assert.equal(assessEligibility(r,'2026-10-18T19:30:00Z').status,'needs_review');
});
test('changed source signature revokes a previously valid check',()=>{
 const r=record({sourceSignature:'new-html-version'});
 assert.equal(assessEligibility(r,stamp).status,'needs_review');
});
test('missing official citations or excerpts cannot pass',()=>{
 const r=record();r.evidence.authorization.sourceUrl='';
 assert.equal(assessEligibility(r,stamp).status,'needs_review');
});
