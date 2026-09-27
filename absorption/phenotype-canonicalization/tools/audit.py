#!/usr/bin/env python3
"""Read-only, commit-pinned manifest reconnaissance. NOT a compliance gate.

Reads Git objects, never executes repository commands or imports repository code.
Exit 0 means collection completed, 2 means collection/parsing is incomplete.
The report ALWAYS leaves product qualification NOT_EVALUATED.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
try:
    import tomllib
except ModuleNotFoundError:
    try:
        import tomli as tomllib
    except ModuleNotFoundError:
        print(
            "FATAL: Python 3.11+ or the 'tomli' package is required.\n"
            "  Install via: pip install tomli",
            file=sys.stderr,
        )
        raise SystemExit(2)
from pathlib import Path, PurePosixPath
from typing import Any

MAX_BLOB_BYTES = 2_000_000
HISTORY_PREFIXES = ('.archive/', 'archive/', 'historical/', 'audits/', '.work-audit/')
NONFIRST_PARTY_PARTS = {'node_modules', 'vendor', 'third_party', 'third-party'}


def command_segments(command: str) -> list[list[str]]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=';&|')
    lexer.whitespace_split = True
    segments: list[list[str]] = [[]]
    for token in lexer:
        if token and all(c in ';&|' for c in token):
            segments.append([])
        else:
            segments[-1].append(token)
    return [x for x in segments if x]


def repeated_projects(command: str) -> bool:
    for tokens in command_segments(command):
        if not any(re.fullmatch(r'(?:.*/)?ts(?:c|go)(?:\.cmd)?', x) for x in tokens):
            continue
        count = sum(x in ('-p', '--project') or x.startswith('--project=') for x in tokens)
        if count > 1:
            return True
    return False


def source_class(path: str) -> str:
    parts = PurePosixPath(path).parts
    if path.startswith(HISTORY_PREFIXES):
        return 'historical_by_default_path_rule'
    if any(x in NONFIRST_PARTY_PARTS for x in parts):
        return 'external_by_default_path_rule'
    if 'fixtures' in parts:
        return 'fixture_by_default_path_rule'
    return 'eligible_for_static_inspection_not_proven_active'


def inspect_blob(path: str, text: str) -> list[dict[str, Any]]:
    """Produce observations, not policy judgments. No dynamic alias/AST resolution."""
    findings: list[dict[str, Any]] = []
    def add(code: str, detail: str, **extra: Any) -> None:
        findings.append({'code':code, 'path':path, 'detail':detail,
                         'adjudication':'needs_profile_and_evidence', **extra})
    name = PurePosixPath(path).name
    if name == 'package.json':
        data = json.loads(text)
        if not isinstance(data, dict):
            raise ValueError('package.json must contain an object')
        scripts = data.get('scripts', {})
        if not isinstance(scripts, dict):
            raise ValueError('scripts must be an object')
        dependencies: dict[str, Any] = {}
        for field in ('dependencies', 'devDependencies', 'optionalDependencies'):
            value = data.get(field, {})
            if not isinstance(value, dict):
                raise ValueError(f'{field} must be an object')
            dependencies.update(value)
        for script, command in scripts.items():
            if not isinstance(command, str):
                raise ValueError(f'script {script!r} must be a string')
            if repeated_projects(command):
                add('TS_MULTIPLE_PROJECT_FLAGS', 'One compiler invocation repeats project selection.', script=script, command=command)
            if script in ('lint','lint:ts','lint:js','format','format:check'):
                if re.search(r'\b(?:eslint|biome|prettier)\b', command):
                    add('JS_NONCANONICAL_RUNNER_CANDIDATE', 'Live script names a non-default runner; rule/profile exception may apply.', script=script, command=command)
            if ('check' in script or script in ('lint','lint:stylelint','quality')) and not script.endswith(':fix'):
                if re.search(r'(?<!\S)--(?:fix|write)(?:\s|$)|\brun\s+\S+:fix\b', command):
                    add('CHECK_INVOKES_REPAIR', 'A check-like entry point directly invokes a repair.', script=script, command=command)
            if re.search(r'\boxfmt\b', command) and 'oxfmt' not in dependencies:
                add('FORMATTER_SOURCE_UNRESOLVED', 'oxfmt is not directly declared here; inspect ancestor workspace and resolved binary before calling this a defect.', script=script)
        ts = dependencies.get('typescript')
        if isinstance(ts,str) and re.match(r'^[~^<>=\s]*[0-6](?:\.|$)', ts):
            add('TS_LEGACY_DECLARATION', 'Declared TypeScript range is pre-native-7; determine CLI vs compiler-API role.', declared=ts)
        if data.get('packageManager') == 'bun':
            add('BUN_VERSION_UNDECLARED', 'packageManager says bun without an exact version; external pin remains unverified.')
        for dep, version in dependencies.items():
            if version in ('latest','*','next','canary'):
                add('FLOATING_DEPENDENCY_INPUT', 'Floating manifest input; a frozen lock may resolve it reproducibly. Verify that lock and update contract.', dependency=dep, declared=version)
            if isinstance(version,str) and '<REDACTED>' in version:
                add('DEPENDENCY_PLACEHOLDER', 'A visible placeholder appears in a dependency selector; resolve actual source without restoring secrets.', dependency=dep)
    elif name == 'pyproject.toml':
        data = tomllib.loads(text)
        required = data.get('project',{}).get('requires-python','')
        ruff = data.get('tool',{}).get('ruff',{})
        target = ruff.get('target-version')
        if isinstance(required,str) and re.search(r'>=\s*3\.14',required) and target in ('py310','py311','py312','py313'):
            add('PYTHON_LINT_TARGET_MISMATCH', 'Python minimum and explicit Ruff syntax target differ; determine intended compatibility.', requires_python=required, ruff_target=target)
        add('PYTHON_RUNTIME_NOT_PROVEN', 'Package metadata does not prove interpreter pin, free-threaded build, or post-import GIL state.')
    elif name == 'Cargo.toml':
        data = tomllib.loads(text)
        level = data.get('profile',{}).get('release',{}).get('opt-level')
        if level in ('s','z'):
            add('SIZE_ORIENTED_RELEASE_PROFILE', 'Size-oriented release setting observed; assess with workload measurements rather than assuming a slowdown.', opt_level=level)
    elif path.startswith('.github/workflows/') and name.endswith(('.yml','.yaml')):
        for line_number,line in enumerate(text.splitlines(),1):
            match = re.search(r'^\s*(?:-\s*)?uses:\s*[\'"]?([^\s\'"#]+)',line)
            if not match:
                continue
            target = match.group(1)
            if target.startswith(('./','docker://')) or '@' not in target:
                continue
            ref = target.rsplit('@',1)[1]
            if not re.fullmatch(r'[0-9a-fA-F]{40}',ref):
                add('WORKFLOW_MUTABLE_REF_CANDIDATE', 'Remote action/workflow reference is not a full commit SHA; resolve policy and provider accessibility.', line=line_number, target=target)
    return findings


def git(repo: Path, *args: str) -> bytes:
    result = subprocess.run(['git','-C',str(repo),*args],capture_output=True,timeout=30,check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode('utf-8','replace').strip() or f'git exited {result.returncode}')
    return result.stdout


def scan(repo: Path, ref: str = 'HEAD') -> dict[str, Any]:
    sha = git(repo,'rev-parse','--verify','--end-of-options',f'{ref}^{{commit}}').decode().strip()
    report: dict[str, Any] = {'schema_version':'0.1.0','source_commit':sha,
        'collector':'canonicalization-static-reference/0.1.0',
        'collector_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'qualification':'NOT_EVALUATED','coverage':'selected_git_manifests_only',
        'counts':{'tracked_entries':0,'inspected_files':0,'non_regular_entries':0,'excluded_by_default_path_rule':0},
        'observations':[], 'acquisition_errors':[], 'inspected_sources':[],
        'limits':['No dependency installation, runtime, complete shell/AST analysis, full branch history, hosted CI, or installed consumer verification.',
                  'Path classifications are overrideable reconnaissance defaults, not accepted lifecycle decisions.',
                  'No observations is not proof of compliance. Untracked and dirty worktree changes are intentionally outside the pinned commit.']}
    entries = git(repo,'ls-tree','-r','-z',sha).split(b'\0')
    for entry in entries:
        if not entry:
            continue
        report['counts']['tracked_entries'] += 1
        meta, raw_path = entry.split(b'\t',1)
        mode, kind, oid = meta.decode('ascii').split()
        path = raw_path.decode('utf-8','surrogateescape')
        if mode not in ('100644','100755') or kind != 'blob':
            report['counts']['non_regular_entries'] += 1
            continue
        if source_class(path) != 'eligible_for_static_inspection_not_proven_active':
            report['counts']['excluded_by_default_path_rule'] += 1
            continue
        if PurePosixPath(path).name not in ('package.json','pyproject.toml','Cargo.toml') and not (path.startswith('.github/workflows/') and path.endswith(('.yml','.yaml'))):
            continue
        try:
            size = int(git(repo,'cat-file','-s',oid))
            if size > MAX_BLOB_BYTES:
                raise ValueError(f'blob exceeds {MAX_BLOB_BYTES} bytes')
            text = git(repo,'cat-file','blob',oid).decode('utf-8')
            observations = inspect_blob(path,text)
            for observation in observations:
                observation.update(blob_sha=oid, source_commit=sha)
            report['observations'].extend(observations)
            report['inspected_sources'].append({'path':path,'blob_sha':oid})
            report['counts']['inspected_files'] += 1
        except (ValueError,UnicodeError,RuntimeError,subprocess.TimeoutExpired) as exc:
            report['acquisition_errors'].append({'path':path,'error':str(exc),'classification':'UNKNOWN_NOT_PASS'})
    report['collection_status'] = 'INCOMPLETE' if report['acquisition_errors'] else 'COMPLETED_STATIC_ONLY'
    return report


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--ref',default='HEAD')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    try:
        report=scan(args.repo.resolve(strict=True),args.ref)
    except (OSError,RuntimeError,subprocess.TimeoutExpired) as exc:
        print(json.dumps({'collection_status':'FAILED','qualification':'NOT_EVALUATED','error':str(exc)}),file=sys.stderr)
        return 2
    output=json.dumps(report,indent=2,ensure_ascii=True)+'\n'
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(output,encoding='utf-8')
    else:
        print(output,end='')
    return 2 if report['acquisition_errors'] else 0

if __name__ == '__main__':
    raise SystemExit(main())
