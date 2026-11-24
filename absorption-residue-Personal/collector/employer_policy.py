"""Standing Palantir exclusion for this collector's intake and projections."""
import re
from urllib.parse import urlsplit, unquote

PALANTIR = re.compile('palantir', re.I)
COMPANY_FIELDS = ('company', 'company_name', 'companyName', 'employer', 'employer_name',
                  'organization', 'organizationName', 'hiringOrganization')
ATS_PATHS = (('jobs.lever.co', '/'), ('jobs.eu.lever.co', '/'), ('jobs.ashbyhq.com', '/'),
             ('boards.greenhouse.io', '/'), ('job-boards.greenhouse.io', '/'),
             ('boards-api.greenhouse.io', '/v1/boards/'), ('api.lever.co', '/v0/postings/'),
             ('api.ashbyhq.com', '/posting-api/job-board/'))


def excluded_name(value):
    if isinstance(value, str):
        return bool(PALANTIR.search(value))
    if isinstance(value, list):
        return any(excluded_name(item) for item in value)
    if isinstance(value, dict):
        return any(excluded_name(value.get(key)) for key in ('name', 'legalName', 'displayName'))
    return False


def excluded_url(raw):
    if not isinstance(raw, str):
        return False
    try:
        parts = urlsplit(raw)
        host = (parts.hostname or '').lower()
        if host == 'palantir.com' or host.endswith('.palantir.com'):
            return True
        if host.endswith('.myworkdayjobs.com') and excluded_name(host.split('.')[0]):
            return True
        for hostname, prefix in ATS_PATHS:
            if host == hostname and parts.path.lower().startswith(prefix):
                return excluded_name(unquote(parts.path[len(prefix):].split('/')[0]))
    except ValueError:
        pass
    return False


def excluded_posting(row=None, *, employer=None, slug=None):
    row = row if isinstance(row, dict) else {}
    if excluded_name(employer) or excluded_name(slug):
        return True
    if any(excluded_name(row.get(key)) for key in COMPANY_FIELDS):
        return True
    categories = row.get('categories') or {}
    if isinstance(categories, dict) and any(excluded_name(categories.get(key)) for key in ('company', 'employer')):
        return True
    return any(excluded_url(row.get(key)) for key in ('url', 'official_url', 'absolute_url', 'hostedUrl', 'jobUrl', 'applyUrl'))


def excluded_keys(conn):
    """Policy holds reuse observation history; legacy jobs-only exports remain readable."""
    if not conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='observations'").fetchone():
        return set()
    return {row[0] for row in conn.execute("SELECT DISTINCT job_key FROM observations WHERE change_type='employer_excluded'")}
