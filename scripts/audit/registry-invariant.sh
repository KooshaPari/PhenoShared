#!/usr/bin/env bash
#
# registry-invariant.sh - absorption-registry destination invariant checker.
#
# INVARIANT: a record may not claim to be absorbed unless the destination path it
# names exists in this repository.
#
# A destination that is a repo slug or free text is NOT a violation: this
# repository cannot see another repository, so it is reported as UNVERIFIABLE and
# never affects the exit code.  Only a path-shaped destination absent from this
# tree is a VIOLATION.  A gate that fires on correct data gets disabled.
#
# EXIT: 0 no VIOLATION; 1 at least one VIOLATION; 2 usage/harness error.
# SCOPE: projects/*.json (status=absorbed), docs/absorption/*/README.md,
# docs/ABSORPTION_INDEX.md, docs/absorbed-from/*/README.md,
# crates/ABSORPTION_MANIFEST.md.  Read-only; --self-test writes fixtures under
# $JCODE_SCRATCH_DIR only.

set -u

SELF="${BASH_SOURCE[0]}"
SELF_DIR="$(cd "$(dirname "$SELF")" && pwd)"
DEFAULT_ROOT="$(cd "$SELF_DIR/../.." && pwd)"

usage() {
  cat <<'USAGE'
Usage: scripts/audit/registry-invariant.sh [--self-test] [--root DIR]

  (no args)    check this repository; exit 1 if any VIOLATION
  --self-test  negative control (broken fixture must exit 1), positive control
               (clean fixture must exit 0), then the real repository
  --root DIR   check an alternate root (used by --self-test)
  -h, --help   this message

Lines: OK <src>:<line> path <p> exists | VIOLATION <src>:<line> absorbed-but-absent <p> | UNVERIFIABLE <src>:<line> destination is not a local path: <text>
SUMMARY files= projects_absorbed= claims= ok= violations= unverifiable= skipped_no_status=
USAGE
}

MODE="check"
ROOT_OVERRIDE=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --self-test) MODE="self-test"; shift ;;
    --root)      ROOT_OVERRIDE="${2:-}"; shift 2 ;;
    -h|--help)   usage; exit 0 ;;
    *)           echo "registry-invariant: unknown argument: $1" >&2; exit 2 ;;
  esac
done

# Analyzer: argv[1]=root, prints detail lines then one SUMMARY line.
run_analyzer() {
  python3 - "$1" <<'PYEOF'
import glob
import json
import os
import re
import sys

ROOT = os.path.abspath(sys.argv[1])

# First segments that mark a repo-relative path.
CONTENT_ROOTS = set("""
adapters agents apps bench contracts crates datasets demos deploy docs
examples hooks iac kernels libs migrations native packages perf platform
platforms plugins ports program prompts python references registry research
releases schemas scripts servers serving sites specs src state templates
tests tooling tools training vendor web work worklogs
""".split())

try:
    ROOT_ENTRIES = set(os.listdir(ROOT))
except OSError:
    ROOT_ENTRIES = set()

DEST_LABELS = {
    'target', 'target path', 'target paths', 'target repo', 'absorbed into',
    'absorbing repo', 'absorbing path', 'canonical path', 'canonical target',
    'canonical home', 'destination',
}
PATH_LABELS = {  # labels that name a filesystem path, even single-segment
    'target path', 'target paths', 'absorbing path', 'canonical path',
    'canonical target', 'canonical home', 'path',
}
DEST_HEADERS = {
    'target', 'target path', 'target paths', 'target repo', 'path',
    'target crate', 'absorbed into', 'destination',
}
JSON_FIELDS = (('absorbing_path', True), ('absorbed_into', False),
               ('absorbing_repo', False))

STATE = dict(files=0, claims=0, ok=0, violations=0, unverifiable=0,
             skipped_no_status=0, projects_absorbed=0)
EMITTED = set()


def emit(verdict, source, line, path, text=None):
    text = path if text is None else text
    key = (source, line, text)
    if key in EMITTED:
        return
    EMITTED.add(key)
    STATE['claims'] += 1
    if verdict == 'ok':
        STATE['ok'] += 1
        print('OK %s:%s path %s exists' % (source, line, path))
    elif verdict == 'violation':
        STATE['violations'] += 1
        print('VIOLATION %s:%s absorbed-but-absent %s' % (source, line, path))
    else:
        STATE['unverifiable'] += 1
        print('UNVERIFIABLE %s:%s destination is not a local path: %s'
              % (source, line, text))


def norm(p):
    p = p.strip()
    if p.startswith('<') and p.endswith('>'):
        p = p[1:-1]
    p = p.strip().strip('`').strip().strip('"').strip("'").strip()
    p = re.sub(r'^\./+', '', p)
    if p.endswith('/*'):
        p = p[:-2]
    return p.rstrip('/') if len(p) > 1 else p


def expand_braces(p):
    m = re.search(r'\{([^{}]*)\}', p)
    if not m:
        return [p]
    out = []
    for part in m.group(1).split(','):
        out.extend(expand_braces(p[:m.start()] + part.strip() + p[m.end():]))
    return out


def segments(p):
    return [s for s in p.split('/') if s not in ('', '.')]


def external_qualified(segs):
    """<repo-slug>/<content-root>/... reads as 'that repo, this path'."""
    return len(segs) >= 3 and segs[0] not in CONTENT_ROOTS and segs[1] in CONTENT_ROOTS


def path_shaped(segs):
    if not segs or not re.fullmatch(r'[A-Za-z0-9._*+@-]+', segs[0]):
        return False
    if len(segs) == 1:
        return segs[0] in CONTENT_ROOTS
    return segs[0] in CONTENT_ROOTS or segs[0] in ROOT_ENTRIES


def exists(relpath):
    if relpath in ('', '.'):
        return False
    # NOTE: no glob fallback here, deliberately. A wildcard must never decide a
    # verdict by accidental match: 'crates/pheno-data-*' globbed to the
    # unrelated surviving 'crates/pheno-data-from-phenoData' and reported OK,
    # hiding a genuinely absent destination. Metacharacters are handled
    # explicitly in resolve() instead.
    return os.path.exists(os.path.join(ROOT, relpath))


def resolve(value, strict=False):
    """Classify one destination value -> (ok|violation|unverifiable, display)."""
    p = norm(value)
    if not p:
        return ('skip', '')
    for cand in expand_braces(p):
        if exists(cand):
            return ('ok', cand)
    # A wildcard claim is never checkable as written. Glob it only to NAME what
    # it accidentally matched, never to grant OK: 'crates/pheno-data-*' matches
    # the unrelated 'crates/pheno-data-from-phenoData', which is not evidence
    # that the intended crates exist. (norm() has already stripped a trailing
    # '/*', so only interior wildcards reach here.)
    if re.search(r'[*?\[]', p):
        hits = sorted(os.path.relpath(h, ROOT) for h in glob.glob(os.path.join(ROOT, p)))
        if hits:
            return ('unverifiable', '%s (wildcard; matches only: %s)' % (p, ', '.join(hits)))
        segs = segments(p)
        if path_shaped(segs) and not external_qualified(segs):
            return ('violation', p)
        return ('unverifiable', p)
    segs = segments(expand_braces(p)[0])
    if external_qualified(segs):
        tail = '/'.join(segs[1:])
        if exists(tail):
            return ('ok', tail)
        return ('unverifiable', p)
    if strict or path_shaped(segs):
        return ('violation', p)
    return ('unverifiable', p)


def check(source, line, value, strict=False):
    tokens = [t.strip() for t in re.findall(r'`([^`]+)`', value)]
    tokens = [t for t in tokens if ('/' in t or (strict and t))]
    if not tokens:
        tokens = [value]
    for tok in tokens:
        verdict, display = resolve(tok, strict=strict)
        if verdict == 'skip':
            continue
        emit(verdict, source, line, display, text=tok.strip().strip('`'))


def read_lines(relpath):
    try:
        with open(os.path.join(ROOT, relpath), encoding='utf-8', errors='replace') as fh:
            return fh.read().splitlines()
    except OSError:
        return []


def unfenced(lines):
    """Lines with fenced code blocks replaced by None (verification transcripts)."""
    out, fence = [], False
    for line in lines:
        if line.lstrip().startswith('```'):
            fence = not fence
            out.append(None)
            continue
        out.append(None if fence else line)
    return out


def cells_of(line):
    s = line.strip()
    return None if not s.startswith('|') else [c.strip() for c in s.strip('|').split('|')]


def is_separator(cells):
    body = [c.replace(' ', '') for c in cells if c != '']
    return bool(body) and all(re.fullmatch(r':?-{2,}:?', c) for c in body)


# --- projects/*.json ---
def scan_projects():
    for full in sorted(glob.glob(os.path.join(ROOT, 'projects', '*.json'))):
        source = os.path.relpath(full, ROOT)
        STATE['files'] += 1
        try:
            with open(full, encoding='utf-8') as fh:
                data = json.load(fh)
        except (OSError, ValueError) as exc:
            emit('unverifiable', source, 0, '(unparseable: %s)' % exc)
            continue
        if not isinstance(data, dict):
            continue
        lines = read_lines(source)

        def line_of(key):
            for i, text in enumerate(lines, 1):
                if re.match(r'\s*"%s"\s*:' % re.escape(key), text):
                    return i
            return 0

        if 'status' not in data:
            # e.g. projects/phenotype-dag-core-rename-2026-09-01.json.
            # No status key means no absorption claim to verify -> counted, never
            # a violation.
            STATE['skipped_no_status'] += 1
            continue
        if data.get('status') != 'absorbed':
            continue
        STATE['projects_absorbed'] += 1
        claims = [(line_of(k), data[k], strict) for k, strict in JSON_FIELDS
                  if isinstance(data.get(k), str) and data[k].strip()]
        if not claims:
            emit('unverifiable', source, line_of('status'), '(none)',
                 text='(no destination field)')
            continue
        for line, value, strict in claims:
            check(source, line, value, strict=strict)


# --- docs/absorption/*/README.md ---
PROSE_MARKER = re.compile(
    r'into|→|->|canonical (?:in|at|owner)|lives? in|is at|retained at|target(?: is)?:?',
    re.I)
BOLD_FIELD = re.compile(
    r'^\s*(?:\*\*|__)?\s*(target paths|target path|target repo|target|absorbed into|'
    r'absorbing repo|absorbing path|canonical path|canonical target|canonical home)'
    r'\s*(?:\*\*|__)?\s*[:\-]\s*(.*)$', re.I)


def scan_absorption_readme(source):
    header, prev = None, None
    for i, line in enumerate(unfenced(read_lines(source)), 1):
        if line is None or not line.strip():
            header, prev = None, None
            continue
        cells = cells_of(line)
        if cells is not None:
            if is_separator(cells):
                header = prev
            else:
                first = cells[0].strip().strip('*').lower()
                if len(cells) >= 2 and first in DEST_LABELS:
                    check(source, i, cells[1], strict=first in PATH_LABELS)
                if header:
                    for j, head in enumerate(header):
                        key = head.strip().strip('*').lower()
                        if j < len(cells) and key in DEST_HEADERS:
                            check(source, i, cells[j], strict=key in PATH_LABELS)
                prev = cells
            continue
        header, prev = None, None
        s = line.strip()
        m = BOLD_FIELD.match(line)
        if m:
            label = m.group(1).lower()
            check(source, i, m.group(2), strict=label in PATH_LABELS)
            continue
        if s.startswith('#') and ('→' in s or '->' in s):
            check(source, i, re.split(r'→|->', s)[-1])
            continue
        if re.search(r'absorb|canonical|retention', s, re.I):
            marks = list(PROSE_MARKER.finditer(s))
            if marks:
                for tok in re.findall(r'`([^`]+)`', s[marks[-1].end():]):
                    if '/' in tok:
                        check(source, i, tok)


# --- relative markdown links ---
LINK_RE = re.compile(r'\]\(([^)]+)\)')


def scan_links(source):
    base = os.path.dirname(source)
    for i, line in enumerate(unfenced(read_lines(source)), 1):
        if line is None:
            continue
        for target in LINK_RE.findall(line):
            t = target.split('#')[0].strip()
            if not t or t.startswith(('http://', 'https://', 'mailto:', '#')):
                continue
            joined = os.path.normpath(os.path.join(base, t))
            if joined.startswith('..'):
                emit('unverifiable', source, i, t,
                     text='%s (link escapes repository)' % t)
            elif exists(joined):
                emit('ok', source, i, joined)
            else:
                emit('violation', source, i, joined)


# --- crates/ABSORPTION_MANIFEST.md ---
MANIFEST_MARKER = re.compile(r'canonical|absorb|target|retention|split target', re.I)


def scan_manifest(source):
    for i, line in enumerate(unfenced(read_lines(source)), 1):
        if line is None or not MANIFEST_MARKER.search(line):
            continue
        for tok in re.findall(r'`([^`]+)`', line):
            if '/' in tok and not tok.startswith(('http://', 'https://')):
                check(source, i, tok)


def main():
    scan_projects()
    patterns = [('docs/absorption/*/README.md', 'absorption'),
                ('docs/ABSORPTION_INDEX.md', 'links'),
                ('docs/absorbed-from/*/README.md', 'links'),
                ('crates/ABSORPTION_MANIFEST.md', 'manifest')]
    for pattern, kind in patterns:
        for full in sorted(glob.glob(os.path.join(ROOT, pattern))):
            STATE['files'] += 1
            source = os.path.relpath(full, ROOT)
            if kind == 'absorption':
                scan_absorption_readme(source)
            elif kind == 'manifest':
                scan_manifest(source)
            scan_links(source)
    print('SUMMARY files=%d projects_absorbed=%d claims=%d ok=%d violations=%d '
          'unverifiable=%d skipped_no_status=%d'
          % (STATE['files'], STATE['projects_absorbed'], STATE['claims'],
             STATE['ok'], STATE['violations'], STATE['unverifiable'],
             STATE['skipped_no_status']))


main()
PYEOF
}

# --self-test fixtures.  Every scanner is exercised and each fixture holds
# broken records plus healthy ones, so the control proves the checker
# discriminates instead of always failing.  The fenced block is a trap: if
# fenced verification transcripts were scanned, the control counts would change.
build_fixture() {
  local dir="$1" broken="$2"
  rm -rf "$dir"
  mkdir -p "$dir/projects" "$dir/crates/present-zzz" \
           "$dir/docs/absorption/zz-field" "$dir/docs/absorbed-from/zz-present"
  FIX_DIR="$dir" FIX_BROKEN="$broken" python3 - <<'PYEOF'
import json
import os

d = os.environ['FIX_DIR']
broken = os.environ['FIX_BROKEN'] == 'yes'
present = 'crates/present-zzz/'
files = {
    'projects/zz-negative-control.json': {
        'name': 'zz-negative-control', 'status': 'absorbed',
        'absorbing_path': 'crates/definitely-absent-zzz/' if broken else present,
        'absorbing_repo': 'some-other-org/some-other-repo'},
    'projects/zz-positive-control.json': {
        'name': 'zz-positive-control', 'status': 'absorbed',
        'absorbing_path': present},
    # repo slug + free text must stay UNVERIFIABLE, never VIOLATION
    'projects/zz-free-text.json': {
        'name': 'zz-free-text', 'status': 'absorbed',
        'absorbed_into': 'phenotype-tooling (crates/phench)'},
    # no status key at all -> counted as skipped_no_status
    'projects/zz-no-status.json': {'name': 'zz-no-status', 'path': 'repos/zz-no-status'},
}
files['docs/absorption/zz-field/README.md'] = (
    '# Absorption Record: zz-field\n\n| Field | Value |\n|-------|-------|\n'
    '| Source repo | `some-other-org/zz-field` |\n| Target path | `%s` |\n'
    '| Absorbed date | 2026-01-01 |\n\n'
    '```bash\n# fenced trap: absorbed into `crates/never-a-path-zzz/`\n```\n'
    % ('packages/absent-zzz/' if broken else present))
files['docs/absorbed-from/zz-present/README.md'] = (
    '# zz-present\n\n| Source path | Canonical surface |\n|-------------|-------------------|\n'
    '| `x.md` | [docs/](../../) |\n')
files['docs/ABSORPTION_INDEX.md'] = (
    '# Absorption index\n\n| Repo | Disposition | Absorption README |\n'
    '|------|-------------|-------------------|\n'
    '| [zz](https://example.invalid/zz) | ABSORB | [readme](%s) |\n'
    % ('absorbed-from/zz-missing/README.md' if broken else 'absorbed-from/zz-present/README.md'))
files['crates/ABSORPTION_MANIFEST.md'] = (
    '# Manifest\n\n`zz-crate` is canonical in `%s`.\n'
    % ('libs/absent-zzz/' if broken else present))
for rel, body in files.items():
    path = os.path.join(d, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(json.dumps(body, indent=2) + '\n' if isinstance(body, dict) else body)
PYEOF
}

run_check() {
  local root="$1" out summary
  out="$(run_analyzer "$root")" || {
    echo "registry-invariant: analyzer failed for $root" >&2; return 2; }
  summary="$(printf '%s\n' "$out" | grep '^SUMMARY ' | tail -1)"
  [ -n "$summary" ] || {
    echo "registry-invariant: analyzer produced no summary for $root" >&2; return 2; }
  printf '%s\n' "$out" | grep -v '^SUMMARY '
  printf '%s\n' "$summary"
}

count_violations() { printf '%s\n' "$1" | grep -c '^VIOLATION '; }
failed_control()   { printf '%s\n' "$1" | grep -q '^VIOLATION ' && echo 1 || echo 0; }

if [ "$MODE" = "check" ]; then
  root="${ROOT_OVERRIDE:-$DEFAULT_ROOT}"
  [ -d "$root" ] || { echo "registry-invariant: root not found: $root" >&2; exit 2; }
  out="$(run_check "$root")" || exit 2
  printf '%s\n' "$out"
  summary="$(printf '%s\n' "$out" | grep '^SUMMARY ' | tail -1)"
  violations="$(printf '%s\n' "$summary" | sed -n 's/.* violations=\([0-9]*\).*/\1/p')"
  echo "root=$root $summary"
  [ "${violations:-0}" -gt 0 ] && { echo "registry-invariant: FAIL ($violations violation(s))"; exit 1; }
  echo "registry-invariant: PASS (0 violations)"
  exit 0
fi

SCRATCH="${JCODE_SCRATCH_DIR:-}"
[ -n "$SCRATCH" ] || {
  echo "registry-invariant: JCODE_SCRATCH_DIR unset; refusing to write fixtures" >&2
  exit 2; }
FIX_BROKEN="$SCRATCH/registry-invariant-selftest/broken"
FIX_CLEAN="$SCRATCH/registry-invariant-selftest/clean"
echo "=== NEGATIVE CONTROL (fixture with deliberately absent destinations) ==="
build_fixture "$FIX_BROKEN" yes
echo "fixture=$FIX_BROKEN"
out_broken="$(run_check "$FIX_BROKEN")" || exit 2
printf '%s\n' "$out_broken"
broken_exit="$(failed_control "$out_broken")"
broken_count="$(count_violations "$out_broken")"
echo "observed_exit_code=$broken_exit expected_exit_code=1 | observed_violations=$broken_count expected_violations=4"

echo "=== POSITIVE CONTROL (same fixture, destinations made present) ==="
build_fixture "$FIX_CLEAN" no
echo "fixture=$FIX_CLEAN"
out_clean="$(run_check "$FIX_CLEAN")" || exit 2
printf '%s\n' "$out_clean"
clean_exit="$(failed_control "$out_clean")"
clean_count="$(count_violations "$out_clean")"
echo "observed_exit_code=$clean_exit expected_exit_code=0 | observed_violations=$clean_count expected_violations=0"

echo "=== REAL REPOSITORY (no fixture) ==="
echo "root=$DEFAULT_ROOT"
out_real="$(run_check "$DEFAULT_ROOT")" || exit 2
printf '%s\n' "$out_real"
real_exit="$(failed_control "$out_real")"
real_count="$(count_violations "$out_real")"
echo "observed_exit_code=$real_exit real_violations=$real_count"

echo "=== CONTROL VERDICT ==="
fail=0
[ "$broken_exit" -eq 1 ] || { echo "FAIL: negative control did not exit 1"; fail=1; }
[ "$broken_count" -eq 4 ] || { echo "FAIL: negative control saw $broken_count, expected 4"; fail=1; }
[ "$clean_exit" -eq 0 ] || { echo "FAIL: positive control did not exit 0"; fail=1; }
[ "$clean_count" -eq 0 ] || { echo "FAIL: positive control saw $clean_count, expected 0"; fail=1; }
[ "$fail" -eq 0 ] || { echo "SELF-TEST: FAIL"; exit 2; }
echo "SELF-TEST: PASS (negative control exited 1 with 4 violations; positive control exited 0)"
exit 0
