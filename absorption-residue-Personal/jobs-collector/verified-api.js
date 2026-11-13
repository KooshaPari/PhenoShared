import {assessEligibility, canonicalJobKey} from './verification.js';
import {isPalantirPosting, allowedCanonicalSql} from './employer-policy.js';

/**
 * Read-only private verified-list projection from D1.
 * Returns unknown (NOT zero) if the migration is absent or results are capped.
 */
export async function readVerified(db, now=new Date().toISOString()) {
  const table=await db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='job_verification'").first();
  if(!table) return {schema_ready:false, verified_eligible_la:null, total_verified:null,
    jobs:[], warning:'verification migration has not been applied'};
  const legacy=await db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='job'").first();
  const legacyGuard=legacy ? "AND NOT EXISTS(SELECT 1 FROM job j WHERE (j.id=c.canonical_id OR j.url=c.official_url) AND j.status='excluded_employer')" : '';
  const rows=(await db.prepare(`SELECT c.canonical_id,c.company,c.title,c.official_url,c.geography,c.state,c.content_signature,v.checked_at,v.source_signature,v.evidence_json FROM canonical_job c INNER JOIN job_verification v ON v.canonical_id=c.canonical_id WHERE ${allowedCanonicalSql()}
    ${legacyGuard}
    ORDER BY v.checked_at DESC LIMIT 501`).all()).results || [];
  if(rows.length>500) return {schema_ready:true, verified_eligible_la:null,total_verified:null,
    jobs:[],truncated:true,warning:'Evidence rows exceed verified counting window'};
  const accepted=[];
  for(const row of rows) {
    if(isPalantirPosting(row))continue;
    if(row.state==='closed'||row.state==='stale'||!row.content_signature||
       canonicalJobKey(row.official_url)!==row.canonical_id||
       row.source_signature!==row.content_signature)continue;
    let evidence;
    try{evidence=JSON.parse(row.evidence_json);}catch{continue;}
    const result=assessEligibility({officialUrl:row.official_url,
      sourceSignature:row.content_signature,evidence},now);
    if(result.status!=='active_verified')continue;
    accepted.push({canonical_id:row.canonical_id,company:row.company,title:row.title,
      official_url:row.official_url,region:row.geography,checked_at:row.checked_at,
      base_compensation:evidence.compensation?.status==='undisclosed'?
        'undisclosed':(evidence.compensation?.baseRange||null)});
  }
  return {schema_ready:true,verified_eligible_la:accepted.filter(x=>x.region==='la_metro').length,
    total_verified:accepted.length,jobs:accepted,
    warning:'Only current, source-version-matched six-field evidence records are counted'};
}
