#!/usr/bin/env python3
"""Fixed-target read-only evidence capture; no source code is executed.

The paper is CC BY-SA 4.0 and retains attribution in the temporary artifact.
Git graph comparisons are bounded; lack of a shared fetched ancestor is not
proof of independent origin. No API key or credential is exported.
"""
from __future__ import annotations
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.parse
import urllib.request

REPOS = [
    'MaxRobinsonTheGreat/EvolutionSimulator',
    'MaxRobinsonTheGreat/EvolutionSimulatorV2',
    'MaxRobinsonTheGreat/LifeEngine',
    'kolbytn/mindcraft',
    'mindcraft-bots/mindcraft',
    'mindcraft-ce/mindcraft-ce',
    'maxencefaldor/omni-epic',
]
PAPER = 'https://arxiv.org/pdf/2405.15568v3'


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


class CheckedRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, url):
        a, b = urllib.parse.urlsplit(req.full_url), urllib.parse.urlsplit(url)
        if b.scheme != 'https' or a.hostname != b.hostname:
            raise RuntimeError('CROSS_HOST_REDIRECT_REFUSED')
        return super().redirect_request(req, fp, code, msg, headers, url)


def get(url, limit=4_000_000):
    host = urllib.parse.urlsplit(url).hostname
    if host not in {'api.github.com', 'arxiv.org'}:
        raise RuntimeError('HOST_REFUSED')
    headers = {'User-Agent': 'ResearchLedger-Wave5/1.0'}
    if host == 'api.github.com' and os.environ.get('GITHUB_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['GITHUB_TOKEN']
        headers['Accept'] = 'application/vnd.github+json'
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.build_opener(CheckedRedirect()).open(req, timeout=90) as res:
        body = res.read(limit + 1)
        if len(body) > limit:
            raise RuntimeError('BODY_LIMIT')
        return body, {'requested_url': url, 'resolved_url': res.geturl(),
                      'http_status': res.status, 'sha256': sha(body),
                      'bytes': len(body), 'captured_at': now()}


def api(path):
    raw, receipt = get('https://api.github.com' + path)
    return json.loads(raw), receipt


def git(directory, *args, timeout=120):
    process = subprocess.run(['git', '-C', str(directory), *args],
        capture_output=True, text=True, timeout=timeout,
        env={**os.environ, 'GIT_TERMINAL_PROMPT': '0'})
    return process.returncode, process.stdout.strip()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output
    out.mkdir(parents=True, exist_ok=True)
    report = {'campaign_id': 'eg-nested-corpus-2026-09', 'wave': 5,
              'started_at': now(), 'repositories': [], 'paper': {},
              'comparisons': [], 'source_commit': os.environ.get('GITHUB_SHA')}
    try:
        body, receipt = get(PAPER, 35_000_000)
        if not body.startswith(b'%PDF-'):
            raise RuntimeError('NOT_PDF')
        (out / 'omni-epic-2405.15568v3.pdf').write_bytes(body)
        report['paper'] = {**receipt, 'state': 'CAPTURED',
            'license': 'CC-BY-SA-4.0',
            'attribution': 'Maxence Faldor, Jenny Zhang, Antoine Cully, Jeff Clune',
            'license_url': 'https://creativecommons.org/licenses/by-sa/4.0/',
            'arxiv_record': 'https://arxiv.org/abs/2405.15568v3'}
    except Exception as exc:
        report['paper'] = {'state': 'FAILED', 'error_class': type(exc).__name__}
    observed = {}
    for requested in REPOS:
        entry = {'requested_name': requested}
        try:
            meta, receipt = api('/repos/' + requested)
            full = meta['full_name']
            branch, branch_receipt = api('/repos/' + full + '/branches/' + urllib.parse.quote(meta['default_branch'], safe=''))
            entry.update({'state': 'CAPTURED', 'id': meta['id'], 'full_name': full,
                'fork': meta['fork'], 'parent': (meta.get('parent') or {}).get('full_name'),
                'source': (meta.get('source') or {}).get('full_name'),
                'created_at': meta['created_at'], 'head': branch['commit']['sha'],
                'default_branch': meta['default_branch'], 'response': receipt,
                'branch_response': branch_receipt})
            if full not in observed:
                observed[full] = entry
        except Exception as exc:
            entry.update({'state': 'FAILED', 'error_class': type(exc).__name__})
        report['repositories'].append(entry)
    graph_dir = out.parent / 'wave5-git-graph'
    graph_dir.mkdir(exist_ok=True)
    subprocess.run(['git', 'init', '--bare', str(graph_dir)], capture_output=True, check=True)
    selected = [n for n in observed if n != 'maxencefaldor/omni-epic']
    report['git_samples'] = {}
    for index, name in enumerate(selected):
        ref = 'refs/heads/evidence-' + str(index)
        head = observed[name]['head']
        try:
            code, _ = git(graph_dir, 'fetch', '--filter=blob:none', '--depth=256', '--no-tags',
                           'https://github.com/' + name + '.git', head + ':' + ref)
            if code:
                raise RuntimeError('FETCH_FAILED')
            code, listing = git(graph_dir, 'rev-list', ref)
            if code:
                raise RuntimeError('REV_LIST_FAILED')
            commits = sorted(set(listing.splitlines()))
            report['git_samples'][name] = {'head': head, 'ref': ref,
                'state': 'CAPTURED', 'depth_limit': 256,
                'commits': commits, 'sample_count': len(commits),
                'ordered_set_sha256': sha(('\n'.join(commits) + '\n').encode())}
        except Exception as exc:
            report['git_samples'][name] = {'state': 'FAILED', 'error_class': type(exc).__name__}
    for a, b in [('MaxRobinsonTheGreat/EvolutionSimulator', 'MaxRobinsonTheGreat/LifeEngine'),
                 ('mindcraft-bots/mindcraft', 'mindcraft-ce/mindcraft-ce')]:
        aa, bb = report['git_samples'].get(a, {}), report['git_samples'].get(b, {})
        result = {'a': a, 'b': b, 'scope': 'bounded fetched Git ancestry; not code behavior or authorship'}
        if aa.get('state') == bb.get('state') == 'CAPTURED':
            common = sorted(set(aa['commits']) & set(bb['commits']))
            result.update({'shared_sampled_commits': len(common), 'shared_examples': common[:8]})
            code, base = git(graph_dir, 'merge-base', '--all', aa['head'], bb['head'])
            result['merge_base_exit'] = code
            result['merge_bases'] = base.splitlines() if code == 0 else []
            result['conclusion'] = 'SHARED_GIT_HISTORY_CONFIRMED' if common else 'NO_SHARED_ANCESTOR_IN_BOUNDED_SAMPLE'
        else:
            result['conclusion'] = 'FETCH_INCOMPLETE'
        report['comparisons'].append(result)
    report['finished_at'] = now()
    (out / 'wave5-intake-receipts.json').write_text(json.dumps(report, indent=2) + '\n')
    (out / 'ATTRIBUTION.txt').write_text(
        'OMNI-EPIC: Open-endedness via Models of human Notions of Interestingness with Environments Programmed in Code.\n'
        'Maxence Faldor, Jenny Zhang, Antoine Cully, Jeff Clune. arXiv:2405.15568v3.\n'
        'Source: https://arxiv.org/pdf/2405.15568v3\nLicense: CC BY-SA 4.0 https://creativecommons.org/licenses/by-sa/4.0/\n'
        'PDF redistributed unchanged for source inspection; no endorsement implied.\n'
        'Repository receipts are point-in-time API metadata and bounded Git graph observations, not copied source code.\n')
    manifest = [{'path': p.name, 'sha256': sha(p.read_bytes())} for p in sorted(out.iterdir()) if p.is_file()]
    (out / 'SHA256-MANIFEST.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps({'paper': report['paper'].get('state'), 'repo_targets': len(report['repositories']),
                      'comparisons': report['comparisons']}, indent=2))


if __name__ == '__main__':
    main()
