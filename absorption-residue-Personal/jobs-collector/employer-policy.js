// Standing employer exclusion. Job descriptions mentioning a vendor are not employer evidence.
const PALANTIR = /palantir/i;
const COMPANY_FIELDS = ['company', 'company_name', 'companyName', 'employer', 'employer_name',
  'organization', 'organizationName', 'hiringOrganization'];
const ATS_PATHS = [
  ['jobs.lever.co', '/'], ['jobs.eu.lever.co', '/'], ['jobs.ashbyhq.com', '/'],
  ['boards.greenhouse.io', '/'], ['job-boards.greenhouse.io', '/'],
  ['boards-api.greenhouse.io', '/v1/boards/'], ['api.lever.co', '/v0/postings/'],
  ['api.ashbyhq.com', '/posting-api/job-board/']
];
function label(value) {
  if (typeof value === 'string') return PALANTIR.test(value);
  if (Array.isArray(value)) return value.some(label);
  return value && typeof value === 'object' && ['name', 'legalName', 'displayName'].some(key => label(value[key]));
}
function excludedUrl(raw) {
  try {
    const url = new URL(raw), host = url.hostname.toLowerCase();
    if (host === 'palantir.com' || host.endsWith('.palantir.com')) return true;
    if (host.endsWith('.myworkdayjobs.com') && PALANTIR.test(host.split('.')[0])) return true;
    const prefix = ATS_PATHS.find(([hostname, path]) => host === hostname && url.pathname.toLowerCase().startsWith(path))?.[1];
    return prefix != null && PALANTIR.test(decodeURIComponent(url.pathname.slice(prefix.length).split('/')[0]));
  } catch { return false; }
}
export function isPalantirPosting(row = {}, board = {}) {
  if (label(board.company) || label(board.slug) || COMPANY_FIELDS.some(key => label(row?.[key]))) return true;
  if (label(row?.categories?.company) || label(row?.categories?.employer)) return true;
  if (['url', 'official_url', 'officialUrl', 'absolute_url', 'hostedUrl', 'jobUrl', 'applyUrl'].some(key => excludedUrl(row?.[key]))) return true;
  if (['id', 'canonical_id', 'job_id', 'jobId'].some(key => /^(?:lever|greenhouse|ashby):[^:]*palantir[^:]*:/i.test(row?.[key] || ''))) return true;
  if (['id', 'job_id'].some(key => String(row?.[key] || '').startsWith('gh:') && excludedUrl(String(row[key]).slice(3)))) return true;
  return row?.source === 'github-list' && String(row.title || '').includes(' | ')
    && label(String(row.title).split(' | ')[0]);
}
const named = column => `instr(lower(coalesce(${column},'')),'palantir')>0`;
function urlPredicate(column) {
  const value = `lower(coalesce(${column},''))`;
  const authority = `substr(${value},9,instr(substr(${value},9)||'/','/')-1)`;
  const parts = [`${authority}='palantir.com'`, `${authority} LIKE '%.palantir.com'`,
    `(${authority} LIKE '%.myworkdayjobs.com' AND ${named(`substr(${authority},1,instr(${authority},'.')-1)`)})`];
  for (const [host, path] of ATS_PATHS) {
    const offset = ('https://' + host + path).length + 1;
    const rest = `substr(${value},${offset})`;
    parts.push(`(${value} LIKE 'https://${host}${path}%' AND ${named(`substr(${rest},1,instr(${rest}||'/','/')-1)`)})`);
  }
  return '(' + parts.join(' OR ') + ')';
}
// All identifiers below are fixed internal aliases, never request input.
export const allowedBoardSql = (alias = '') => {
  const prefix = alias ? alias + '.' : '';
  return `NOT (${named(prefix + 'company')} OR ${named(prefix + 'slug')})`;
};
export const allowedJobSql = (job = 'j', board = 'b') => `(${allowedBoardSql(board)}
  AND ${job}.status<>'excluded_employer' AND NOT ${urlPredicate(job + '.url')}
  AND NOT (${job}.source='github-list' AND instr(${job}.title,' | ')>0
    AND ${named(`substr(${job}.title,1,instr(${job}.title,' | ')-1)`)}))`;
export const allowedCanonicalSql = (alias = 'c') => `NOT (${named(alias + '.company')} OR ${urlPredicate(alias + '.official_url')})`;
