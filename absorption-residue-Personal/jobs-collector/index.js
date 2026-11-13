import {ingestOfficialWhatnot} from './whatnot-import.js';
import {readVerified} from './verified-api.js';
import {normalizeWhatnotObservation} from './ingestion.js';
import {isPalantirPosting, allowedBoardSql, allowedJobSql} from './employer-policy.js';
// Authored by Instinct. Job collector (Cloudflare Worker + D1, free tier).
// Stores and scores public ATS postings. It does NOT decide fit. Standing rules for the scoring notes:
//  - apply floor: posted base >= $110k; unknown comp is FLAGGED, never dropped
//  - YOE: 0-2 primary, 2-4 secondary; 5+ is a no unless the agent records a reasoned, experience-grounded exception (flag yoe_exception_review)
//  - LA first (within 40 mi of Santa Monica); SD/Chicago/Seattle/remote rank lower
//  - brand-leverage-or-stability test and final fit are agent judgment, not this Worker's
//  - excluded: Anduril, Silvus, Palantir. Dedupe vs Simplify/Gmail happens agent-side before anything is surfaced.
const EXCLUDE = /anduril|silvus|palantir/i;
const TITLE_OK = /software|\bsde\b|\bswe\b|developer|program manager|product manager|\btpm\b|backend|back-end|frontend|front-end|full.?stack|platform engineer|data engineer|ml engineer|machine learning engineer|applied ai/i;
const TITLE_NO = /sales|recruit|mechanical|electrical|manufactur|account exec|hardware|firmware|embedded|avionics|propulsion|rf |mechanism|pcb|facilities|finance|legal|counsel|marketing|support engineer|solutions engineer|field engineer|\bintern\b|director|vp |head of|clearance/i;
const TITLE_LEVEL_NO = /\b(?:staff|principal|distinguished)\b/i;
const PM_TITLE = /associate product manager|\bapm\b|product manager|technical program manager|\btpm\b|program manager|product analyst/i;
const PM_LEVEL_NO = /\b(?:senior|sr\.?|staff|principal|distinguished|lead|director|group|head of|vp)\b/i;
export const isDiscoveryTitle = title => PM_TITLE.test(title)
  ? !PM_LEVEL_NO.test(title) && !TITLE_NO.test(title)
  : TITLE_OK.test(title) && !TITLE_NO.test(title) && !TITLE_LEVEL_NO.test(title);
const LA = /los angeles|santa monica|culver|el segundo|burbank|pasadena|long beach|torrance|glendale|venice|playa|hollywood|beverly|marina del rey|hawthorne|\bla\b|, ca.*(90|91)\d{3}/i;
const BACKUP = /san diego|chicago|seattle|bellevue|remote|anywhere|united states|\bus\b/i;
const PER_FIRE_DETAILS = 8;
const laDay = () => new Date().toLocaleDateString('en-CA', { timeZone: 'America/Los_Angeles' });

export const SEED = [
  ['greenhouse','flexe','Flexe',2],['greenhouse','otter','Otter',2],['greenhouse','dragos','Dragos',2],['greenhouse','roo','Roo',2],['greenhouse','mediaalpha','MediaAlpha',2],['greenhouse','outpostspace','Outpost',2],['greenhouse','freeformfuturecorp','Freeform',2],['greenhouse','mcmaster-carr','McMaster-Carr',2],['greenhouse','drweng','DRW',2],['greenhouse','chicagotradingcampus','CTC',2],
  ['greenhouse','spacex','SpaceX',1],['greenhouse','riotgames','Riot Games',1],['greenhouse','scopely','Scopely',2],['greenhouse','ziprecruiter','ZipRecruiter',2],['greenhouse','goguardian','GoGuardian',2],
  ['lever','wealthfront','Wealthfront',2],['lever','integrate','Integrate',2],['lever','matchgroup','Match Group',2],
  ['ashby','plaid','Plaid',1],['ashby','havocai','Havoc AI',2],['ashby','vastai','Vast',2],['ashby','first-resonance','First Resonance',2],
];

export function parseComp(t) {
  const m = /\$\s?(\d{2,3})(?:,(\d{3}))?\s*(k)?\s*(?:-|–|—|to)\s*\$?\s*(\d{2,3})(?:,(\d{3}))?\s*(k)?/i.exec(t || '');
  if (!m) return [null, null];
  const v = (a, b, k) => b ? +a * 1000 + +b : (k || +a < 1000 && +a >= 50 && /k/i.test(m[0]) ? +a * 1000 : +a * 1000);
  const lo = v(m[1], m[2], m[3]), hi = v(m[4], m[5], m[6]);
  return lo >= 30000 && hi >= lo && hi < 1000000 ? [lo, hi] : [null, null];
}
export function parseYoe(t) {
  const re = /(\d{1,2})\s*\+?\s*(?:-\s*\d{1,2}\s*)?(?:or more\s*)?years?[^.]{0,60}?experience|experience[^.]{0,40}?(\d{1,2})\s*\+?\s*years?/ig;
  let m, best = null;
  while ((m = re.exec(t || ''))) { const n = +(m[1] || m[2]); if (n <= 20 && (best === null || n < best)) best = n; }
  return best;
}
export function locRank(loc, remote) {
  const l = loc || '';
  if (LA.test(l)) return 3;
  if (/remote/i.test(l) || remote) return 2; // Discovery only; never implies LA/California work eligibility
  if (BACKUP.test(l)) return 1;
  return 0;
}
export function score(j) {
  const flags = [];
  let s = j.loc_rank * 10;
  if (j.yoe_min == null) { flags.push('yoe_unknown'); s += 2; }
  else if (j.yoe_min <= 2) s += 5; else if (j.yoe_min <= 4) { s += 3; flags.push('yoe_2_4'); } else flags.push('yoe_exception_review');
  if (j.comp_max == null) flags.push('comp_unknown'); else if (j.comp_max >= 110000) s += 2;
  return { s, flags };
}

const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
export async function jfetch(url, { fetcher = fetch, wait = pause } = {}) {
  const backoff = [250, 750]; // Three total attempts, at most one second of backoff.
  for (let attempt = 0; ; attempt++) {
    let response;
    try {
      response = await fetcher(url, { headers: { accept: 'application/json', 'user-agent': 'job-collector/1.0' } });
    } catch (error) {
      // Rejections from fetch are transport failures, separate from HTTP/JSON errors.
      if (attempt === backoff.length) throw error;
      await wait(backoff[attempt]);
      continue;
    }
    if (!response.ok) {
      const error = Object.assign(new Error(`${response.status} ${url}`), { status: response.status });
      const retryable = response.status === 429 || (response.status >= 500 && response.status < 600);
      // Release unused response bodies before another request.
      await response.body?.cancel().catch(() => {});
      if (!retryable || attempt === backoff.length) throw error;
      await wait(backoff[attempt]);
      continue;
    }
    try {
      return await response.json();
    } catch (error) {
      // Invalid JSON is permanent for this request; a failed body transfer can recover.
      const retryable = error instanceof TypeError || error?.name === 'AbortError';
      if (!retryable || attempt === backoff.length) throw error;
      await wait(backoff[attempt]);
    }
  }
}
const strip = h => String(h || '').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ');


/**
 * Whatnot's public Ashby board API returns 404, but its employer careers catalog
 * serves role links and colocated location labels. Discovery only, never eligibility.
 */
export function parseWhatnotCareers(html) {
  const rx = /<a\b[^>]*\bhref=["']\/careers\/roles\/([0-9a-f-]{36})["'][^>]*>([\s\S]*?)<\/a>/gi;
  const anchors = [...String(html).matchAll(rx)];
  const found = new Map();
  const places = /\b(?:Los Angeles,\s*CA|San Francisco,\s*CA|Seattle,\s*WA|New York,\s*NY|Phoenix,\s*AZ|London,\s*UK|Dublin,\s*Ireland|Berlin,\s*Germany|Kraków,\s*Poland)\b/gi;
  for (const m of anchors) {
    const id = m[1].toLowerCase();
    const title = strip(m[2]).trim();
    if (found.has(id) || !title || /^(?:view job|apply now)$/i.test(title)) continue;
    const start = m.index;
    let end = Math.min(String(html).length, start + 4000);
    for (const n of anchors) {
      if (n.index > start && n[1].toLowerCase() !== id) {
        end = Math.min(end, n.index);
        break;
      }
    }
    const local = [...html.slice(start, end).matchAll(places)].map(x => x[0]);
    const locs = [...new Set(local)];
    found.set(id, { ext: id, title, loc: locs.join(' · '),
      url: 'https://www.whatnot.com/careers/roles/' + id,
      text: '', remote: false });
  }
  if (found.size < 20) throw new Error('Whatnot official catalog changed: too few linked roles');
  return [...found.values()];
}

/** Ashby hosted-page GraphQL fallback for orgs whose public posting API returns 404. Discovery only. */
export function mapAshbyHosted(slug, data) {
  const postings = data && data.data && data.data.jobBoard && data.data.jobBoard.jobPostings;
  if (!Array.isArray(postings)) throw new Error('Ashby hosted board returned no postings for ' + slug);
  const rows = postings.map(x => ({ ext: x.id, title: x.title, loc: x.locationName || '',
    excludedEmployer: !!isPalantirPosting(x, {slug}),
    url: `https://jobs.ashbyhq.com/${slug}/${x.id}`, text: x.compensationTierSummary || '',
    remote: /remote/i.test(String(x.workplaceType || '')) }));
  if (isPalantirPosting(data.data.jobBoard, {slug})) rows.excludedBoard = true;
  return rows;
}

async function listAshbyHosted(slug) {
  const query = 'query ApiJobBoardWithTeams($organizationHostedJobsPageName: String!) { jobBoard: jobBoardWithTeams(organizationHostedJobsPageName: $organizationHostedJobsPageName) { jobPostings { id title locationName workplaceType employmentType compensationTierSummary } } }';
  const r = await fetch('https://jobs.ashbyhq.com/api/non-user-graphql?op=ApiJobBoardWithTeams', {
    method: 'POST',
    headers: { 'content-type': 'application/json', accept: 'application/json', 'user-agent': 'job-collector/1.0' },
    body: JSON.stringify({ operationName: 'ApiJobBoardWithTeams', variables: { organizationHostedJobsPageName: slug }, query })
  });
  if (!r.ok) throw new Error(`${r.status} ashby hosted ${slug}`);
  return mapAshbyHosted(slug, await r.json());
}

async function listBoard(b) {
  if (b.ats === 'whatnot-careers') {
    const r = await fetch('https://www.whatnot.com/careers/discover', {
      headers: {accept:'text/html', 'user-agent':'job-cockpit-public-careers/0.1 (read-only)'}
    });
    if (!r.ok) throw new Error('Whatnot careers returned HTTP ' + r.status);
    return parseWhatnotCareers(await r.text());
  }
  if (b.ats === 'greenhouse') {
    const j = await jfetch(`https://boards-api.greenhouse.io/v1/boards/${b.slug}/jobs`);
    const rows = j.jobs.map(x => ({ ext: String(x.id), title: x.title, loc: x.location && x.location.name, url: x.absolute_url, needsDetail: true,
      excludedEmployer: !!isPalantirPosting(x, b) }));
    if (isPalantirPosting(j, b)) rows.excludedBoard = true;
    return rows;
  }
  if (b.ats === 'lever') {
    const j = await jfetch(`https://api.lever.co/v0/postings/${b.slug}?mode=json`);
    return j.map(x => ({ ext: x.id, title: x.text, loc: x.categories && x.categories.location, url: x.hostedUrl, text: x.descriptionPlain, remote: x.workplaceType === 'remote',
      excludedEmployer: !!isPalantirPosting(x, b) }));
  }
  let j;
  try {
    j = await jfetch(`https://api.ashbyhq.com/posting-api/job-board/${b.slug}?includeCompensation=true`);
  } catch (e) {
    // Some orgs (Whatnot) disable the public posting API but keep the hosted board; fall back to its page GraphQL.
    if (e.status !== 404) throw e;
    return listAshbyHosted(b.slug);
  }
  const rows = j.jobs.map(x => ({ ext: x.id, title: x.title, loc: x.location, url: x.jobUrl, text: (x.descriptionPlain || '') + ' ' + ((x.compensation && x.compensation.compensationTierSummary) || ''), remote: x.isRemote,
    excludedEmployer: !!isPalantirPosting(x, b) }));
  if (isPalantirPosting(j, b)) rows.excludedBoard = true;
  return rows;
}

export async function boot(db) {
  const have = await db.prepare("SELECT name FROM sqlite_master WHERE name='board'").first();
  if (!have) {
    const ddl = SCHEMA.split(';').map(s => s.trim()).filter(Boolean).map(s => db.prepare(s));
    await db.batch(ddl);
    await db.batch(SEED.map(([a, s, c, t]) => db.prepare('INSERT OR IGNORE INTO board(ats,slug,company,tier) VALUES(?,?,?,?)').bind(a, s, c, t)));
  }
  // Seed removal does not retire persisted boards. Preserve rows/history, disable sourcing.
  await db.prepare(`UPDATE board SET skip=1 WHERE skip=0 AND NOT (${allowedBoardSql()})`).run();
  // The exclusion pass scans every open job (~6.3k rows_read per call) and boot()
  // runs on every /ingest POST + cron fire, which burned millions of D1 read ops
  // in hours. Run it at most once per LA day; ingest rejects excluded employers
  // per row already.
  await db.prepare("CREATE TABLE IF NOT EXISTS boot_meta(k TEXT PRIMARY KEY, v TEXT)").run();
  const day = laDay();
  const mark = await db.prepare("SELECT v FROM boot_meta WHERE k='exclusion_day'").first();
  if (!mark || mark.v !== day) {
    const rows = (await db.prepare("SELECT j.id,j.title,j.url,j.source,b.company,b.slug FROM job j JOIN board b ON b.id=j.board_id WHERE j.status IN ('open','below_floor','needs_closure_check','excluded_title')").all()).results;
    const blocked = rows.filter(row => isPalantirPosting(row, row));
    for (let i=0; i<blocked.length; i+=40) await db.batch(blocked.slice(i,i+40)
      .map(row => db.prepare("UPDATE job SET status='excluded_employer' WHERE id=?").bind(row.id)));
    await db.prepare("INSERT INTO boot_meta(k,v) VALUES('exclusion_day',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v").bind(day).run();
  }
}
const SCHEMA = `CREATE TABLE IF NOT EXISTS board(id INTEGER PRIMARY KEY, ats TEXT NOT NULL, slug TEXT NOT NULL, company TEXT NOT NULL, tier INTEGER DEFAULT 2, skip INTEGER DEFAULT 0, last_day TEXT, last_ok INTEGER, last_error TEXT, UNIQUE(ats,slug));
CREATE TABLE IF NOT EXISTS job(id TEXT PRIMARY KEY, board_id INTEGER NOT NULL, ext_id TEXT, title TEXT, location TEXT, loc_rank INTEGER, comp_min INTEGER, comp_max INTEGER, yoe_min INTEGER, url TEXT, first_seen TEXT, last_seen TEXT, status TEXT DEFAULT 'open', score INTEGER, apply_rank INTEGER, flags TEXT, detail_day TEXT, source TEXT DEFAULT 'board', list TEXT, link_check TEXT);
CREATE INDEX IF NOT EXISTS job_seen ON job(last_seen, status);
CREATE INDEX IF NOT EXISTS job_board ON job(board_id);
CREATE TABLE IF NOT EXISTS job_event(job_id TEXT, day TEXT, change TEXT);
CREATE INDEX IF NOT EXISTS ev_day ON job_event(day);
CREATE TABLE IF NOT EXISTS alert(day TEXT, level TEXT, job_id TEXT, reason TEXT);
CREATE TABLE IF NOT EXISTS run(day TEXT PRIMARY KEY, ok INTEGER, error TEXT, boards_ok INTEGER, boards_failed INTEGER, jobs_new INTEGER, jobs_closed INTEGER, candidates INTEGER, finished_at TEXT);
`;

export async function step(env, day = laDay()) {
  const db = env.JOBS;
  await boot(db);
  // Error-only rows record an interrupted step, not completion of the daily sweep.
  const done = await db.prepare('SELECT day FROM run WHERE day=? AND boards_ok IS NOT NULL').bind(day).first();
  if (done) return 'idle';
  let b = await db.prepare(`SELECT * FROM board WHERE skip=0 AND ${allowedBoardSql()} AND (last_day IS NULL OR last_day<>?) ORDER BY tier, id LIMIT 1`).bind(day).first();
  let retry = false;
  if (!b) {
    b = await db.prepare(`SELECT * FROM board WHERE skip=0 AND ${allowedBoardSql()} AND last_day=? AND last_ok=0 AND (last_error IS NULL OR substr(last_error,1,9)<>'retry:v1:') ORDER BY tier,id LIMIT 1`).bind(day).first();
    if (b) {
      // Claim the single board retry before I/O. Concurrent steps cannot claim it again.
      const claimed = await db.prepare("UPDATE board SET last_ok=NULL,last_error='retry:v1: in progress' WHERE id=? AND skip=0 AND last_day=? AND last_ok=0 AND (last_error IS NULL OR substr(last_error,1,9)<>'retry:v1:')").bind(b.id, day).run();
      if (!claimed.meta.changes) return 'busy';
      retry = true;
    }
  }
  if (b) {
    // A late duplicate first attempt must not overwrite a claimed/completed retry.
    const outcomeWhere = retry
      ? "id=? AND last_day=? AND last_ok IS NULL AND last_error='retry:v1: in progress'"
      : 'id=? AND (last_day IS NULL OR last_day<>?)';
    try {
      if (EXCLUDE.test(b.company)) throw new Error('excluded');
      const items = await listBoard(b), stmts = [];
      if (items.excludedBoard) {
        await db.batch([
          db.prepare('UPDATE board SET skip=1 WHERE id=?').bind(b.id),
          db.prepare("UPDATE job SET status='excluded_employer' WHERE board_id=? AND status IN ('open','below_floor','needs_closure_check','excluded_title')").bind(b.id)
        ]);
        return 'board excluded ' + b.slug;
      }
      const excludedIds = new Set((await db.prepare("SELECT id FROM job WHERE board_id=? AND status='excluded_employer'").bind(b.id).all()).results.map(row=>row.id));
      let kept = 0;
      for (const x of items) {
        const id = b.ats + ':' + b.slug + ':' + x.ext;
        if (excludedIds.has(id) || x.excludedEmployer || isPalantirPosting(x, b)) {
          stmts.push(db.prepare("UPDATE job SET status='excluded_employer' WHERE id=?").bind(id));
          continue;
        }
        if (!isDiscoveryTitle(x.title)) {
          // Preserve history, but withdraw previously collected roles that changed level.
          if (TITLE_LEVEL_NO.test(x.title)) stmts.push(db.prepare("UPDATE job SET title=?,status='excluded_title' WHERE id=?")
            .bind(x.title, b.ats + ':' + b.slug + ':' + x.ext));
          continue;
        }
        const lr = locRank(x.loc, x.remote); if (!lr) continue;
        const [lo, hi] = parseComp(x.text), yoe = x.text ? parseYoe(x.text) : null;
        if (hi != null && hi < 110000) continue;
        const sc = score({ loc_rank: lr, yoe_min: yoe, comp_max: hi });
        kept++;
        stmts.push(db.prepare(`INSERT INTO job(id,board_id,ext_id,title,location,loc_rank,comp_min,comp_max,yoe_min,url,first_seen,last_seen,score,flags,detail_day) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
          ON CONFLICT(id) DO UPDATE SET title=excluded.title,location=excluded.location,last_seen=excluded.last_seen,status='open',url=excluded.url,
          comp_min=COALESCE(excluded.comp_min,comp_min),comp_max=COALESCE(excluded.comp_max,comp_max),yoe_min=COALESCE(excluded.yoe_min,yoe_min)`)
          .bind(id, b.id, x.ext, x.title, x.loc || '', lr, lo, hi, yoe, x.url, day, day, sc.s, sc.flags.join(','), x.needsDetail ? null : day));
      }
      for (let i = 0; i < stmts.length; i += 40) await db.batch(stmts.slice(i, i + 40));
      await db.prepare('UPDATE board SET last_day=?,last_ok=1,last_error=NULL WHERE ' + outcomeWhere).bind(day, b.id, day).run();
      return `board ${b.slug} kept ${kept}/${items.length}`;
    } catch (e) {
      // Prefix first failures too: an upstream message beginning with retry: is data.
      const error = (retry ? 'retry:v1: ' : 'attempt: ') + String(e.message || e);
      await db.prepare('UPDATE board SET last_day=?,last_ok=0,last_error=? WHERE ' + outcomeWhere).bind(day, error.slice(0, 200), b.id, day).run();
      return 'board error ' + b.slug;
    }
  }
  // detail phase (greenhouse only): comp + YOE from the posting body
  const jobs = (await db.prepare(`SELECT j.id,j.ext_id,b.slug,j.loc_rank,j.title,j.url,j.source,b.company FROM job j JOIN board b ON b.id=j.board_id WHERE j.last_seen=? AND j.detail_day IS NULL AND b.ats='greenhouse' AND ${allowedJobSql()} LIMIT ?`).bind(day, PER_FIRE_DETAILS).all()).results.filter(row=>!isPalantirPosting(row,row));
  if (jobs.length) {
    for (const j of jobs) {
      try {
        const d = await jfetch(`https://boards-api.greenhouse.io/v1/boards/${j.slug}/jobs/${j.ext_id}`);
        const t = strip(d.content), [lo, hi] = parseComp(t), yoe = parseYoe(t), sc = score({ loc_rank: j.loc_rank, yoe_min: yoe, comp_max: hi });
        await db.prepare('UPDATE job SET comp_min=?,comp_max=?,yoe_min=?,score=?,flags=?,detail_day=?,status=CASE WHEN ? IS NOT NULL AND ?<110000 THEN \'below_floor\' ELSE status END WHERE id=?').bind(lo, hi, yoe, sc.s, sc.flags.join(','), day, hi, hi, j.id).run();
      } catch (e) { await db.prepare('UPDATE job SET detail_day=?,flags=flags||\',detail_failed\' WHERE id=?').bind(day, j.id).run(); }
    }
    return 'details ' + jobs.length;
  }
  return await finalize(db, day) ? 'done' : 'busy';
}

export async function finalize(db, day) {
  // Each statement has the same gate. The batch commits all effects + completion
  // together; a concurrent finalizer observes completion and performs no writes.
  const ready = `NOT EXISTS(SELECT 1 FROM run WHERE day=? AND boards_ok IS NOT NULL)
    AND NOT EXISTS(SELECT 1 FROM board WHERE skip=0 AND ${allowedBoardSql()} AND
      (last_day IS NULL OR last_day<>? OR last_ok IS NULL OR
       (last_ok=0 AND (last_error IS NULL OR substr(last_error,1,9)<>'retry:v1:'))))
    AND NOT EXISTS(SELECT 1 FROM job j JOIN board b ON b.id=j.board_id
      WHERE j.last_seen=? AND j.detail_day IS NULL AND b.ats='greenhouse' AND ${allowedJobSql()})`;
  // SQLite GLOB character classes mirror the ASCII word boundaries in TITLE_LEVEL_NO.
  const excludedLevel = ['staff', 'principal', 'distinguished']
    .map(word => `(' '||lower(coalesce(title,''))||' ') GLOB '*[^a-z0-9_]${word}[^a-z0-9_]*'`).join(' OR ');
  const statements = [
    db.prepare(`UPDATE job SET status='excluded_title' WHERE source='board' AND status='open' AND (${excludedLevel}) AND ${ready}`).bind(day, day, day),
    db.prepare(`UPDATE job SET status='stale' WHERE source='github-list' AND status='open' AND last_seen<date(?,'-14 day') AND ${ready}`).bind(day, day, day, day),
    db.prepare(`UPDATE job SET status='needs_closure_check' WHERE status='open' AND last_seen<? AND board_id IN (SELECT id FROM board WHERE last_day=? AND last_ok=1) AND ${ready}`).bind(day, day, day, day, day),
    db.prepare(`INSERT INTO job_event(job_id,day,change) SELECT j.id,j.first_seen,'new' FROM job j JOIN board b ON b.id=j.board_id WHERE j.first_seen=? AND j.status='open' AND ${allowedJobSql()} AND NOT EXISTS(SELECT 1 FROM job_event e WHERE e.job_id=j.id AND e.change='new') AND ${ready}`).bind(day, day, day, day),
    db.prepare(`INSERT INTO alert(day,level,job_id,reason) SELECT ?,'priority',j.id,'Disney posting' FROM job j JOIN board b ON b.id=j.board_id WHERE j.first_seen=? AND j.status='open' AND b.company LIKE '%Disney%'
      AND ${allowedJobSql()} AND EXISTS(SELECT 1 FROM run WHERE day<>? AND boards_ok IS NOT NULL)
      AND NOT EXISTS(SELECT 1 FROM alert a WHERE a.day=? AND a.job_id=j.id AND a.reason='Disney posting') AND ${ready}`).bind(day, day, day, day, day, day, day),
    db.prepare(`INSERT INTO alert(day,level,job_id,reason) SELECT ?,'priority',j.id,'new tier-1 role, LA, yoe<=4 or unknown' FROM job j JOIN board b ON b.id=j.board_id WHERE j.first_seen=? AND j.status='open' AND b.tier=1 AND j.loc_rank=3 AND (j.yoe_min IS NULL OR j.yoe_min<=4)
      AND ${allowedJobSql()} AND EXISTS(SELECT 1 FROM run WHERE day<>? AND boards_ok IS NOT NULL)
      AND NOT EXISTS(SELECT 1 FROM alert a WHERE a.day=? AND a.job_id=j.id AND a.reason='new tier-1 role, LA, yoe<=4 or unknown') AND ${ready}`).bind(day, day, day, day, day, day, day),
    db.prepare(`INSERT INTO run(day,ok,error,boards_ok,boards_failed,jobs_new,jobs_closed,candidates,finished_at)
      SELECT ?,CASE WHEN count(*)>0 AND sum(last_day=? AND last_ok=1)=count(*) THEN 1 ELSE 0 END,
        CASE WHEN count(*)=0 THEN 'no active boards' WHEN sum(last_ok=0)>0 THEN sum(last_ok=0)||' board(s) failed' ELSE NULL END,
        coalesce(sum(last_ok=1),0),coalesce(sum(last_ok=0),0),
        (SELECT count(*) FROM job j JOIN board b ON b.id=j.board_id WHERE j.first_seen=? AND ${allowedJobSql()}),
        (SELECT count(*) FROM job j JOIN board b ON b.id=j.board_id WHERE j.status='closed' AND j.last_seen<? AND j.last_seen>=date(?,'-1 day') AND ${allowedJobSql()}),
        (SELECT count(*) FROM job j JOIN board b ON b.id=j.board_id WHERE j.last_seen=? AND j.status='open' AND ${allowedJobSql()}),?
      FROM board WHERE skip=0 AND ${allowedBoardSql()} HAVING ${ready}
      ON CONFLICT(day) DO UPDATE SET ok=excluded.ok,error=excluded.error,boards_ok=excluded.boards_ok,
        boards_failed=excluded.boards_failed,jobs_new=excluded.jobs_new,jobs_closed=excluded.jobs_closed,
        candidates=excluded.candidates,finished_at=excluded.finished_at WHERE run.boards_ok IS NULL`)
      .bind(day, day, day, day, day, day, new Date().toISOString(), day, day, day)
  ];
  const results = await db.batch(statements);
  return results.at(-1).meta.changes > 0;
}

export async function recordStepError(db, day, error) {
  // UPSERT preserves the row and its counters. Completed sweeps win either race order.
  await db.prepare(`INSERT INTO run(day,ok,error,finished_at) VALUES(?,0,?,?)
    ON CONFLICT(day) DO UPDATE SET ok=0,error=excluded.error,finished_at=excluded.finished_at
    WHERE run.boards_ok IS NULL`).bind(day, String(error.message || error).slice(0, 300), new Date().toISOString()).run();
}


// Only the first /ingest of each LA day in an isolate pays for boot()'s DDL +
// board sweep; the cron path still boots on every fire. Running the full boot
// per POST is what tipped the Worker over its resource limits (Error 1102)
// under sweep load.
let ingestBootDay = null;

async function ingest(req, env) {
  try {
    return await ingestImpl(req, env);
  } catch (e) {
    // Surface the failing layer instead of an opaque runtime termination.
    return new Response('ingest error: ' + (e && e.message ? e.message : e), { status: 500 });
  }
}

async function ingestImpl(req, env) {
  const auth = req.headers.get('authorization') || '';
  const want = 'Bearer ' + (env.INGEST_TOKEN || '');
  let diff = auth.length ^ want.length;
  for (let i = 0; i < Math.min(auth.length, want.length); i++) diff |= auth.charCodeAt(i) ^ want.charCodeAt(i);
  if (!env.INGEST_TOKEN || diff !== 0) return new Response('unauthorized', { status: 401 });
  const body = await req.json().catch(() => null);
  if (!body || !Array.isArray(body.rows) || body.rows.length > 100) return new Response('bad request', { status: 400 });
  const db = env.JOBS, day = laDay();
  if (ingestBootDay !== day) { await boot(db); ingestBootDay = day; }
  if (body.rows.some(r=>r?.source==='whatnot-official' && !isPalantirPosting(r))) {
    const sourceTable=await db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='canonical_source'").first();
    const canonicalTable=await db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='canonical_job'").first();
    if (!sourceTable || !canonicalTable) return new Response('verification schema not deployed', {status:503});
  }
  // aggregator rows hang off a pseudo-board so the schema stays one shape
  await db.prepare("INSERT OR IGNORE INTO board(ats,slug,company,tier,skip) VALUES('github-list','aggregator','(aggregator)',3,1)").run();
  const bid = (await db.prepare("SELECT id FROM board WHERE ats='github-list'").first()).id;
  // Official career-catalog observations have an independent provenance identity.
  await db.prepare("INSERT OR IGNORE INTO board(ats,slug,company,tier,skip) VALUES('whatnot-official','whatnot-careers','Whatnot',1,1)").run();
  const whatnotBid = (await db.prepare("SELECT id FROM board WHERE ats='whatnot-official'").first()).id;
  let added = 0, upd = 0, dup = 0, bad = 0, whatnotImported = 0, whatnotRejected = 0;
  // One batched url pre-check per request instead of a per-row lookup
  // (job.url is indexed via job_url, but the IN-list still reads fewer rows).
  const listUrls = [...new Set(body.rows.filter((r) => r && r.source === 'github-list' && r.url).map((r) => String(r.url)))];
  const urlOwners = new Map();
  if (listUrls.length) {
    const ph = listUrls.map(() => '?').join(',');
    for (const r of (await db.prepare(`SELECT id,url FROM job WHERE url IN (${ph})`).bind(...listUrls).all()).results) urlOwners.set(r.url, r.id);
  }
  const stmts = [];
  const stmtKind = []; // 'add' | 'upd', parallel to stmts, for accounting after each batch commits
  for (const r of body.rows) {
    if (isPalantirPosting(r)) { bad++; continue; }
    if (r?.source === 'whatnot-official') {
      const result=await ingestOfficialWhatnot(db,r,{whatnotBid,day,locRank,score});
      added+=result.added;dup+=result.dup;bad+=result.bad;
      whatnotImported+=result.added;
      whatnotRejected+=result.bad;
      continue;
    }
    if (!r || r.source !== 'github-list' || !r.url || !r.title || !r.company || EXCLUDE.test(r.company)) { bad++; continue; }
    const haveId = urlOwners.get(String(r.url));
    const have = haveId ? { id: haveId } : null;
    const id = 'gh:' + r.url;
    const sc = score({ loc_rank: r.loc_rank | 0, yoe_min: null, comp_max: null });
    const flags = [...sc.flags, 'aggregator', r.link_check === 'ok' ? '' : 'link_unverified'].filter(Boolean).join(',');
    if (have && have.id !== id) { dup++; continue; }
    stmts.push(db.prepare(`INSERT INTO job(id,board_id,ext_id,title,location,loc_rank,url,first_seen,last_seen,score,flags,detail_day,source,list,link_check) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(id) DO UPDATE SET title=excluded.title,last_seen=excluded.last_seen,status='open',link_check=excluded.link_check,flags=excluded.flags`)
      .bind(id, bid, id, (String(r.company).slice(0, 60) + ' | ' + String(r.title)).slice(0, 200), String(r.location || '').slice(0, 200), r.loc_rank | 0, r.url, day, day, sc.s, flags, day, 'github-list', String(r.list || '').slice(0, 80), String(r.link_check || '').slice(0, 40)));
    stmtKind.push(have ? 'upd' : 'add');
  }
  // One D1 round trip per chunk instead of one per row: a 25-row ingest drops
  // from ~25 sequential writes (~5-7s wall) to a single batch, shrinking the
  // window in which the Worker can be terminated for resource use.
  for (let i = 0; i < stmts.length; i += 25) {
    await db.batch(stmts.slice(i, i + 25));
    for (const k of stmtKind.slice(i, i + 25)) { if (k === 'upd') upd++; else added++; }
  }
  if (whatnotImported || whatnotRejected) {
    const table=await db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='source_checkpoint'").first();
    if (table) {
      await db.prepare("INSERT INTO source_checkpoint(source_kind,last_attempt,last_success,last_error,records_count) VALUES('whatnot-official',datetime('now'),CASE WHEN ?=0 THEN datetime('now') ELSE NULL END,CASE WHEN ?=0 THEN NULL ELSE 'invalid source entries' END,?) ON CONFLICT(source_kind) DO UPDATE SET last_attempt=excluded.last_attempt,last_success=COALESCE(excluded.last_success,source_checkpoint.last_success),last_error=excluded.last_error,records_count=excluded.records_count")
        .bind(whatnotRejected,whatnotRejected,whatnotImported).run();
    }
  }
  return new Response(JSON.stringify({ added, upd, dup, bad }), { headers: { 'content-type': 'application/json' } });
}

const J = o => new Response(JSON.stringify(o), { headers: { 'content-type': 'application/json' } });

async function handleVerified(req, env, db) {
  const auth = req.headers.get('authorization') || '';
  const expected = 'Bearer ' + (env.INGEST_TOKEN || '');
  let diff = auth.length ^ expected.length;
  for (let i=0; i<Math.min(auth.length,expected.length); i++)
    diff |= auth.charCodeAt(i) ^ expected.charCodeAt(i);
  if (!env.INGEST_TOKEN || diff !== 0) return new Response('unauthorized',{status:401});
  const report=await readVerified(db);
  return new Response(JSON.stringify(report), {
    status:report.schema_ready?200:503,
    headers:{'content-type':'application/json','cache-control':'no-store'}
  });
}

async function handleCandidates(db) {
  const rows=(await db.prepare(`SELECT j.id,b.company,j.title,j.location,j.comp_min,j.comp_max,j.yoe_min,j.url,j.first_seen,j.score,j.apply_rank,j.flags,j.source,j.list,j.link_check FROM job j JOIN board b ON b.id=j.board_id WHERE j.status='open' AND ${allowedJobSql()} ORDER BY (j.apply_rank IS NULL) ASC, j.apply_rank ASC, j.score DESC LIMIT 100`).all()).results.filter(row=>!isPalantirPosting(row));
  return J(rows.map(j => ({...j, verification_status:'unverified', location_eligible:null, graduation_eligible:null})));
}

function healthVerdict(latest, latestFinalized, boards, ageHours) {
  const stale = ageHours === null || !Number.isFinite(ageHours) || ageHours < 0 || ageHours > 36;
  if (stale) return 'stale';
  const boardHealthy = boards.total > 0 && boards.last_success === boards.total && !boards.last_failure && !boards.never_checked;
  const finalizedHealthy = latestFinalized?.ok === 1 && Number.isInteger(latestFinalized.boards_ok)
    && latestFinalized.boards_ok > 0 && latestFinalized.boards_failed === 0;
  return finalizedHealthy && latest?.ok===1 && boardHealthy ? 'ok' : 'degraded';
}

async function handleHealth(db) {
  const latest = await db.prepare('SELECT day,ok,boards_ok,boards_failed,candidates,finished_at,error FROM run ORDER BY day DESC LIMIT 1').first();
  const finalizedRuns = (await db.prepare('SELECT day,ok,boards_ok,boards_failed,candidates,finished_at,error FROM run WHERE boards_ok IS NOT NULL ORDER BY day DESC LIMIT 2').all()).results;
  const counts = await db.prepare(`SELECT COUNT(*) total, SUM(CASE WHEN j.status='open' THEN 1 ELSE 0 END) open_records, SUM(CASE WHEN j.status='open' AND j.loc_rank=3 THEN 1 ELSE 0 END) la_ranked, SUM(CASE WHEN j.status='needs_closure_check' THEN 1 ELSE 0 END) closure_review, SUM(CASE WHEN j.source='github-list' THEN 1 ELSE 0 END) index_records FROM job j JOIN board b ON b.id=j.board_id WHERE ${allowedJobSql()}`).first();
  const boards = await db.prepare(`SELECT COUNT(*) total, SUM(CASE WHEN last_ok=1 THEN 1 ELSE 0 END) last_success, SUM(CASE WHEN last_ok=0 THEN 1 ELSE 0 END) last_failure, SUM(CASE WHEN last_day IS NULL THEN 1 ELSE 0 END) never_checked FROM board WHERE skip=0 AND ${allowedBoardSql()}`).first();
  const sourceTable=await db.prepare("SELECT name FROM sqlite_master WHERE type='table' AND name='source_checkpoint'").first();
  const whatnotFallback=sourceTable ? await db.prepare("SELECT source_kind,last_attempt,last_success,last_error,records_count FROM source_checkpoint WHERE source_kind='whatnot-official'").first() : null;
  const latestFinalized = finalizedRuns[0] || null;
  const ageHours = latestFinalized?.finished_at ? (Date.now() - Date.parse(latestFinalized.finished_at)) / 3600000 : null;
  return J({ service:'job-collector', checked_at:new Date().toISOString(),
    health:healthVerdict(latest, latestFinalized, boards, ageHours),
    latest_run:latest, age_hours:ageHours === null?null:Math.round(ageHours*10)/10,
    latest_finalized_run:latestFinalized, finalized_runs:finalizedRuns,
    run_identity_scheme:'la-day-v1', stale_after_hours:36,
    counts, boards, whatnot_fallback:whatnotFallback, strict_verified_la: null,
    warning:'Collected/open/LA-ranked records are NOT verified applicant-eligible jobs. Strict verified LA count is not implemented.' });
}

async function handleReview(db) {
  const rows=(await db.prepare(`SELECT j.id,b.company,j.title,j.location,j.comp_min,j.comp_max,j.yoe_min,j.url,j.first_seen,j.score,j.flags,j.source,j.link_check FROM job j JOIN board b ON b.id=j.board_id WHERE j.status='open' AND j.loc_rank=3 AND ${allowedJobSql()} ORDER BY j.score DESC LIMIT 200`).all()).results.filter(row=>!isPalantirPosting(row));
  return J({ kind:'unverified_la_review_queue', count:rows.length, truncated:rows.length===200,
    warning:'LA rank is approximate; Irvine, remote California eligibility, graduation and YOE require independent verification.',
    candidates:rows.map(j=>({...j,verification_status:'unverified',graduation_eligible:null,location_eligible:null})) });
}

async function handleDefault(db) {
  const run = await db.prepare('SELECT * FROM run ORDER BY day DESC LIMIT 1').first().catch(() => null);
  const alerts = run ? (await db.prepare('SELECT a.*,j.title,j.url,j.source,j.status AS job_status,b.company,b.slug FROM alert a LEFT JOIN job j ON j.id=a.job_id LEFT JOIN board b ON b.id=j.board_id WHERE a.day=?').bind(run.day).all()).results
    .filter(row=>row.job_status!=='excluded_employer' && !isPalantirPosting(row,row)).map(({day,level,job_id,reason})=>({day,level,job_id,reason})) : [];
  return J({ run, alerts });
}

export default {
  async scheduled(event, env, ctx) {
    const day = laDay(); // Keep errors attached to the same run across LA midnight.
    ctx.waitUntil(step(env, day).catch(e => recordStepError(env.JOBS, day, e).catch(() => {})));
  },
  // Public read-only JSON (public job postings only; no personal data).
  async fetch(req, env) {
    const u = new URL(req.url), db = env.JOBS;
    if (u.pathname === '/ingest' && req.method === 'POST') return ingest(req, env);
    if (u.pathname === '/verified' && req.method === 'GET') return handleVerified(req, env, db);
    if (u.pathname === '/candidates') return handleCandidates(db);
    if (u.pathname === '/health') return handleHealth(db);
    if (u.pathname === '/review') return handleReview(db);
    if (u.pathname === '/boards') return J((await db.prepare(`SELECT ats,slug,company,last_day,last_ok,last_error FROM board WHERE ${allowedBoardSql()}`).all()).results);
    return handleDefault(db);
  },
};
