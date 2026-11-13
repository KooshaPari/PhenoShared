/**
 * Deterministic eligibility evidence gate; collected jobs are unverified by default.
 * No title/search-index/HTTP-200 evidence automatically promotes a requisition.
 */
import {isPalantirPosting} from './employer-policy.js';
export const REQUIRED_CHECKS = Object.freeze([
 'official_active','location','experience','graduation','authorization','compensation'
]);
const MAX_EVIDENCE_AGE_HOURS = 72;
const http = value => /^https:\/\/[^/?#\s]+/i.test(String(value || ''));

export function normalizeOfficialUrl(value) {
 if (!http(value)) return null;
 try {
  const u = new URL(value);
  u.hash = ''; u.search = ''; u.hostname = u.hostname.toLowerCase();
  u.pathname = u.pathname.replace(/\/+$/, '') || '/';
  return u.toString();
 } catch { return null; }
}
/* Never deduplicate based on company name + title. */
export function canonicalJobKey(value) {
 const url = normalizeOfficialUrl(value);
 if (!url) return null;
 const u = new URL(url);
 let m;
 if (/(?:^|\.)greenhouse\.io$/.test(u.hostname)) {
  m = u.pathname.match(/^\/([^/]+)\/jobs\/(\d+)$/i);
  if (m) return 'greenhouse:' + m[1].toLowerCase() + ':' + m[2];
 }
 if (u.hostname === 'jobs.ashbyhq.com') {
  m = u.pathname.match(/^\/([^/]+)\/([0-9a-f-]{36})(?:\/application)?$/i);
  if (m) return 'ashby:' + m[1].toLowerCase() + ':' + m[2].toLowerCase();
 }
 if (u.hostname === 'www.whatnot.com' || u.hostname === 'whatnot.com') {
  m = u.pathname.match(/^\/careers\/roles\/([0-9a-f-]{36})$/i);
  if (m) return 'ashby:whatnot:' + m[1].toLowerCase();
 }
 if (u.hostname === 'jobs.lever.co' || u.hostname === 'jobs.eu.lever.co') {
  m = u.pathname.match(/^\/([^/]+)\/([0-9a-f-]{36})$/i);
  if (m) return 'lever:' + m[1].toLowerCase() + ':' + m[2].toLowerCase();
 }
 if (/\.myworkdayjobs\.com$/.test(u.hostname)) {
  m = u.pathname.match(/[_\/](R\d+(?:-\d+)?)$/i);
  if (m) return 'workday:' + u.hostname + ':' + m[1].toLowerCase();
 }
 return 'url:' + url;
}

function normalizedCheck(evidence, field, signature, nowMs) {
 const check = evidence?.[field];
 if (!check || typeof check !== 'object') return {status:'unknown', reason:field+': no evidence'};
 const allowed = field === 'compensation' ?
  ['pass','fail','unknown','conditional','undisclosed'] :
  ['pass','fail','unknown','conditional'];
 if (!allowed.includes(check.status)) return {status:'unknown',reason:field+': invalid status'};
 if (!http(check.sourceUrl)) return {status:'unknown',reason:field+': missing official source URL'};
 if (!check.checkedAt || !Number.isFinite(Date.parse(check.checkedAt))) {
  return {status:'unknown',reason:field+': missing check time'};
 }
 const ageHours = (nowMs - Date.parse(check.checkedAt))/3600000;
 if (!Number.isFinite(ageHours) || ageHours < -0.0833 || ageHours > MAX_EVIDENCE_AGE_HOURS) {
  return {status:'unknown',reason:field+': stale or future evidence'};
 }
 if (!check.excerpt || typeof check.excerpt !== 'string' || !check.excerpt.trim()) {
  return {status:'unknown',reason:field+': employer-page excerpt missing'};
 }
 if (!signature || check.sourceSignature !== signature) {
  return {status:'unknown',reason:field+': source version changed'};
 }
 return {status:check.status,reason:check.status === 'undisclosed'?'official salary undisclosed':null};
}
export function assessEligibility(record,now=new Date().toISOString()) {
 const {officialUrl,sourceSignature,evidence}=record;
 if (isPalantirPosting(record)) return {status:'ineligible',fields:{},reasons:['Employer excluded by standing rule']};
 const nowMs=Date.parse(now);
 if (!normalizeOfficialUrl(officialUrl) || !Number.isFinite(nowMs)) {
  return {status:'needs_review',fields:{},reasons:['Invalid official URL or check time']};
 }
 const fields={},reasons=[];
 let failed=false,pending=false;
 for(const field of REQUIRED_CHECKS) {
  const check=normalizedCheck(evidence,field,sourceSignature,nowMs);
  fields[field]=check.status;
  if(check.status==='fail') failed=true;
  else if(check.status!=='pass' && !(field==='compensation'&&check.status==='undisclosed')) pending=true;
  if(check.reason) reasons.push(check.reason);
 }
 return {status:failed?'ineligible':pending?'needs_review':'active_verified',fields,reasons};
}
export function isValidVerificationRecord(rec,now=new Date().toISOString()) {
 if(!rec || typeof rec!=='object' || typeof rec.jobId!=='string' || !rec.jobId) return false;
 if(!canonicalJobKey(rec.officialUrl) || !rec.sourceSignature) return false;
 return assessEligibility(rec,now).status==='active_verified';
}
