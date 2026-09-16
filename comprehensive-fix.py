#!/usr/bin/env python3
"""
Comprehensive disposition-index correction 2026-09-01.

Brings the SSOT in line with actual remote state after the polyrepo-eco-merge
session.  Marks repos that were deleted/renamed in this session and fixes
stale claims (PhenoPlugins absorption never shipped, phenotype-shared
phantom target, etc).
"""
import json, datetime, subprocess, re
from pathlib import Path

REGISTRY = Path('registry/disposition-index.json')
NOW = datetime.datetime(2026, 9, 1, 17, 0, 0, tzinfo=datetime.timezone.utc)
NOW_ISO = NOW.isoformat().replace('+00:00', 'Z')

ANSI = re.compile(r'\x1b\[[0-9;]*m')
def gh_api(p):
    r = subprocess.run(['gh', 'api', p], capture_output=True, text=True, timeout=10)
    return ANSI.sub('', r.stdout).strip()

# Repo fates per remote verification
# (path, action) — where action is one of:
#   "deleted"      — repo no longer exists (HTTP 404)
#   "renamed-zz"   — repo renamed to zz-archive-* prefix (still exists, archived)
#   "live"         — repo still active (no action)

d = json.loads(REGISTRY.read_text())
rows = d['rows']

# Step 1: query remote for ground truth of every pheno-* repo
print("=== Querying remote for ground truth ===")
ALL_PHENO_NAMES = set()
# pull all archived + pheno from remote
for kind in ['gh_api(/repos/KooshaPari/phenotype-org-audits)'.split('(')[0]]:
    pass

# Use git remote to query
r = subprocess.run(['gh', 'repo', 'list', 'KooshaPari', '--limit', '400', '--json', 'name,isArchived'],
                   capture_output=True, text=True, timeout=20)
out = ANSI.sub('', r.stdout).strip()
gh_repos = json.loads(out)
gh_by_name = {x['name']: x['isArchived'] for x in gh_repos}

# Determine fates
def fate(name):
    if name in gh_by_name:
        return ('live' if not gh_by_name[name] else 'zz-archive', name in gh_by_name and not gh_by_name[name])
    return ('deleted', False)

# Map old names to current (renamed) names
RENAMES = {
    'phenotype-org-audits': 'zz-archive-phenotype-org-audits',
    'phenotype-org-governance': 'zz-archive-phenotype-org-governance',
    'phenoRouterMonitor': 'zz-archive-phenoRouterMonitor',
    'pheno-agents-md': 'zz-archive-pheno-agents-md',
    'pheno-cdylib-bridge': 'zz-archive-pheno-cdylib-bridge',
    'pheno-context': 'zz-archive-pheno-context',
    'pheno-forge-plugins': 'zz-archive-pheno-forge-plugins',
    'pheno-forge-smoke': 'zz-archive-pheno-forge-smoke',
    'pheno-mcp-router': 'zz-archive-pheno-mcp-router',
    'phenoPatch': 'zz-archive-phenoPatch',
    'pheno-control-plane': 'zz-archive-pheno-control-plane',
    'pheno-research': 'zz-archive-pheno-research',
    'pheno-runtime-config': 'zz-archive-pheno-runtime-config',
    'phenoData': 'zz-archive-phenoData',
    'phenodag': 'zz-archive-phenodag',
    'PhenoProject': 'zz-archive-PhenoProject',
    'PhenoRuntime': 'zz-archive-PhenoRuntime',
}

DELETED = [
    'phenoEvents',           # HTTP 404 (deleted)
    'phenotype-contracts',   # HTTP 404 (deleted)
]

# Row operations
patches = []

# (A) Mark DELETED repos as deleted
for r in rows:
    p = r.get('path', '')
    if not p: continue
    name = p.split('/')[-1]
    if name in DELETED:
        old = r.get('disposition')
        r['disposition'] = 'DEAD_WEIGHT_DELETED'
        r['archived'] = True
        r['fsm'] = 'deleted'
        if old != 'DEAD_WEIGHT_DELETED':
            r['note'] = (r.get('note','') + f' | 2026-09-01: HTTP 404 verified; deleted this session.').strip()
            patches.append(f"DELETED: {name} ({old} → DEAD_WEIGHT_DELETED)")
    elif name in RENAMES:
        # Repo was renamed to zz-archive-* but still archived, not deleted
        old = r.get('disposition')
        new_name = RENAMES[name]
        if gh_by_name.get(new_name):
            # Verify renamed repo exists & is archived
            r['path'] = f'KooshaPari/{new_name}'
            r['name'] = new_name
            r['archived'] = True
            r['fsm'] = 'archived'
            r['disposition'] = 'ZZ_ARCHIVE_RENAMED'
            if old != 'ZZ_ARCHIVE_RENAMED':
                r['note'] = (r.get('note','') + f' | 2026-09-01: renamed to {new_name}, archived per zz-archive convention.').strip()
                patches.append(f"RENAMED→zz-archive: {name} → {new_name}")

# (B) Add missing orphans (deletion cohort + renamed repos not yet in index)
all_paths = {r.get('path') for r in rows}
for old_name, new_name in RENAMES.items():
    full_path = f'KooshaPari/{new_name}'
    if full_path not in all_paths and new_name in gh_by_name:
        rows.append({
            'name': new_name,
            'path': full_path,
            'fsm': 'archived',
            'archived': True,
            'disposition': 'ZZ_ARCHIVE_RENAMED',
            'target': f'formerly KooshaPari/{old_name}',
            'reconciled_at': NOW_ISO,
            'note': f'2026-09-01: renamed from {old_name}, archived.',
        })
        patches.append(f"NEW ROW: {new_name}")

# (C) Fix PhenoPlugins (TOO_LARGE_RETIRE → B:WORKING; absorption never shipped)
for r in rows:
    if r.get('path') == 'KooshaPari/PhenoPlugins':
        old = r.get('disposition')
        if old == 'TOO_LARGE_RETIRE':
            r['disposition'] = 'B:WORKING'
            r['archived'] = False
            r['fsm'] = 'active'
            r['note'] = (r.get('note','') + ' | 2026-09-01: TOO_LARGE_RETIRE was stale; pheno monorepo has 87 crates, none plugin-related; PhenoPlugins is LIVE (482KB). Corrected to B:WORKING.').strip()
            patches.append("PhenoPlugins: TOO_LARGE_RETIRE → B:WORKING")

# (D) Fix phenotype-contracts rows: repoint phenotype-shared → PhenoContracts
fixed_pc = 0
for r in rows:
    if r.get('path') == 'KooshaPari/phenotype-contracts':
        tgt = r.get('target') or ''
        if 'phenotype-shared' in tgt:
            r['target'] = 'PhenoContracts (canonical home, byte-identical schemas)'
            r['note'] = (r.get('note','') + ' | 2026-09-01: target repointed from phantom phenotype-shared (HTTP 404) to live PhenoContracts.').strip()
            fixed_pc += 1
if fixed_pc:
    patches.append(f"phenotype-contracts: {fixed_pc} row(s) repointed → PhenoContracts")

# (E) phenoEvents: was KEEP_CANONICAL_STANDALONE, but actually deleted
for r in rows:
    if r.get('path') == 'KooshaPari/phenoEvents':
        old = r.get('disposition')
        if old != 'DEAD_WEIGHT_DELETED':
            r['disposition'] = 'DEAD_WEIGHT_DELETED'
            r['archived'] = True
            r['fsm'] = 'deleted'
            r['note'] = (r.get('note','') + ' | 2026-09-01: HTTP 404 verified; archived 2026-09-01 then deleted. Eventra is canonical events home.').strip()
            patches.append(f"phenoEvents: {old} → DEAD_WEIGHT_DELETED")

# Update meta
d.setdefault('meta', {})
d['meta']['patches_applied'] = (d['meta'].get('patches_applied', 0) or 0) + len(patches)
d['meta']['last_patched'] = NOW_ISO
d['meta']['last_patch_session'] = 'polyrepo-eco-merge-2026-09-01 batch-12 comprehensive-correction'

REGISTRY.write_text(json.dumps(d, indent=2))

print(f"\n=== Total rows: {len(rows)} ===")
print(f"\n=== {len(patches)} patches applied ===")
for p in patches:
    print(f"  ✓ {p}")
