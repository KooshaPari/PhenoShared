import {normalizeWhatnotObservation} from './ingestion.js';

function region(locations) {
  if (locations.includes('Los Angeles, CA')) return 'la_metro';
  if (locations.includes('San Francisco, CA')) return 'bay_area';
  if (locations.includes('Seattle, WA')) return 'seattle';
  if (locations.includes('New York, NY')) return 'nyc';
  return 'unapproved_or_unknown';
}
function signature(x) {
  return [x.title,x.location,x.url].join('\u001f');
}

export async function ingestOfficialWhatnot(db, row, ctx) {
  const x=normalizeWhatnotObservation(row);
  if (!x) return {added:0,dup:0,bad:1};
  const exists=await db.prepare('SELECT id FROM job WHERE id=? OR url=? LIMIT 1')
    .bind(x.id,x.url).first();
  if (exists && exists.id!==x.id) return {added:0,dup:1,bad:0};
  const lr=ctx.locRank(x.location,false);
  if (!lr) return {added:0,dup:0,bad:1};
  const sc=ctx.score({loc_rank:lr,yoe_min:null,comp_max:null});
  const observedAt=new Date().toISOString();
  const geo=region(row.locations);
  const encoded=new TextEncoder().encode(signature(x));
  const digest=await crypto.subtle.digest('SHA-256',encoded);
  const hash=Array.from(new Uint8Array(digest),v=>v.toString(16).padStart(2,'0')).join('');
  const statements=[
    db.prepare("INSERT INTO canonical_job(canonical_id,company,title,official_url,geography,first_seen,last_seen,content_signature,state) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(canonical_id) DO UPDATE SET company=excluded.company,title=excluded.title,official_url=excluded.official_url,geography=excluded.geography,last_seen=excluded.last_seen,content_signature=CASE WHEN canonical_job.title<>excluded.title OR canonical_job.geography<>excluded.geography OR canonical_job.official_url<>excluded.official_url THEN NULL ELSE canonical_job.content_signature END,state=CASE WHEN canonical_job.title<>excluded.title OR canonical_job.geography<>excluded.geography OR canonical_job.official_url<>excluded.official_url THEN 'review' ELSE canonical_job.state END")
      .bind(x.id,x.employer,x.title,x.url,geo,observedAt,observedAt,null,'discovered'),
    db.prepare("INSERT INTO canonical_source(source_kind,source_id,canonical_id,source_url,location,first_seen,last_seen,content_signature) VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source_kind,source_id) DO UPDATE SET canonical_id=excluded.canonical_id,source_url=excluded.source_url,location=excluded.location,last_seen=excluded.last_seen,content_signature=excluded.content_signature")
      .bind('whatnot-official',x.ext,x.id,x.url,x.location,observedAt,observedAt,hash),
    db.prepare("INSERT INTO job(id,board_id,ext_id,title,location,loc_rank,url,first_seen,last_seen,score,flags,detail_day,source,list,link_check) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET title=excluded.title,location=excluded.location,loc_rank=excluded.loc_rank,url=excluded.url,last_seen=excluded.last_seen,flags=excluded.flags,source=excluded.source,link_check=excluded.link_check")
      .bind(x.id,ctx.whatnotBid,x.ext,x.title,x.location,lr,x.url,ctx.day,ctx.day,sc.s,x.flags,ctx.day,x.source,'whatnot-official','catalog-listing-only')
  ];
  await db.batch(statements);
  return {added:1,dup:0,bad:0};
}
