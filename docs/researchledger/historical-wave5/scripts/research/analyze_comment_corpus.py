#!/usr/bin/env python3
"""Offline analysis of documented-API intake; no network or source execution.

Input is the private intake directory. Exports omit comment/description bodies.
Semantic review is recorded separately and is never inferred from parsing.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import html
import json
import math
from pathlib import Path
import platform
import re
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

STAMP = r'(?:\d{1,3}:)?\d{1,3}:[0-5]\d'
PREFIX = re.compile(r'^\s*(?:[-*]\s*)?(?:\((' + STAMP + r')\)|(' + STAMP + r'))\s*(?:[-–—|:]\s*)?(.+?)\s*$')
SUFFIX = re.compile(r'^\s*([^\n]+?):\s*(' + STAMP + r')(?:\s*[-–—]\s*' + STAMP + r')?\s*$')


def sha(value: str | bytes) -> str:
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def parse_stamp(value: str) -> int:
    values = list(map(int, value.split(':')))
    if len(values) == 3 and values[1] >= 60:
        raise ValueError('INVALID_MINUTES')
    result = 0
    for item in values:
        result = result * 60 + item
    return result


def markers(text: str, duration: int | None) -> dict:
    rows, issues = [], []
    for line_num, line in enumerate(text.splitlines(), 1):
        prefix, suffix = PREFIX.fullmatch(line), SUFFIX.fullmatch(line)
        if prefix:
            stamp, label, style = prefix[1] or prefix[2], prefix[3], 'timestamp_first'
        elif suffix:
            label, stamp, style = suffix[1], suffix[2], 'label_first'
        else:
            continue
        try:
            seconds = parse_stamp(stamp)
        except ValueError:
            issues.append({'line': line_num, 'reason': 'INVALID_TIMESTAMP'})
            continue
        if duration is not None and seconds >= duration:
            issues.append({'line': line_num, 'reason': 'AT_OR_AFTER_VIDEO_END', 'seconds': seconds})
            continue
        if rows and seconds <= rows[-1]['seconds']:
            issues.append({'line': line_num, 'reason': 'NONINCREASING_TIMESTAMP'})
        rows.append({'line': line_num, 'timestamp': stamp, 'seconds': seconds,
                     'label_sha256': sha(label), 'format': style})
    offsets = [r['seconds'] for r in rows]
    return {'markers': rows, 'issues': issues,
            'chapter_sequence_candidate': len(rows) >= 3 and offsets[0] == 0 and not issues,
            'interpretation': 'description timestamp markers, not confirmation of the player chapter UI'}


def canonical_url(value: str) -> str | None:
    value = html.unescape(value.strip()).rstrip('.,;!?')
    while value.endswith(')') and value.count(')') > value.count('('):
        value = value[:-1]
    p = urlsplit(value)
    if p.scheme.lower() not in {'http', 'https'} or not p.hostname or p.username or p.password:
        return None
    host = p.netloc.lower()
    if host.startswith('www.'):
        host = host[4:]
    query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not k.lower().startswith('utm_')]
    if host in {'youtu.be', 'youtube.com', 'm.youtube.com'}:
        vid = p.path.strip('/') if host == 'youtu.be' else dict(query).get('v')
        if not vid and p.path.startswith(('/shorts/', '/live/')):
            vid = p.path.split('/')[2]
        if vid and re.fullmatch(r'[A-Za-z0-9_-]{11}', vid):
            cid = dict(query).get('lc')
            return 'https://www.youtube.com/watch?v=' + vid + ('&lc=' + cid if cid else '')
    return urlunsplit((p.scheme.lower(), host, p.path or '/', urlencode(query), p.fragment))


def primitive_check() -> dict:
    errors = []
    points = [i / 100 for i in range(-4000, 4001)]
    for x in points:
        z = 2 * x
        sigmoid = 1 / (1 + math.exp(-z)) if z >= 0 else math.exp(z) / (1 + math.exp(z))
        errors.append(abs((math.tanh(x) + 1) / 2 - sigmoid))
    return {'experiment_id': 'EG-V3-PRIMITIVE-01', 'kind': 'numerical_identity_sanity_check',
            'identity': '(tanh(x)+1)/2 = sigmoid(2*x)', 'python': platform.python_version(),
            'number_of_points': len(points), 'interval': [-40, 40], 'step': 0.01,
            'maximum_absolute_error': max(errors), 'absolute_tolerance': 1e-14,
            'passed': max(errors) <= 1e-14,
            'not_established': ['optimizer ranking', 'training speed equivalence', 'generalization equivalence',
                                'LLM-agent benchmark performance'],
            'interpretation': 'The same function under input scaling; parameterization, conditioning and finite precision can still affect training.'}


def write(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--private-input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--gap-audit', type=Path)
    parser.add_argument('--source-archive-sha256')
    args = parser.parse_args()
    root, output = args.private_input, args.output
    captures = [json.loads(p.read_text()) for p in sorted((root / 'comments').glob('*.json'))]
    details_payload = json.loads((root / 'video-text-input.json').read_text())
    details = {v['video_id']: v for v in details_payload['videos']}
    oldroot = root / 'repository-inputs/emergent-garden'
    inventory = json.loads((oldroot / 'data/youtube-channel-inventory-v1.json').read_text())
    inv = {v['video_id']: v for v in inventory['videos']}
    if set(details) != set(inv):
        raise ValueError('DETAIL_INVENTORY_MISMATCH')
    coverage = json.loads((root / 'comment-coverage-v1.json').read_text())
    allcomments = [c for capture in captures for c in capture['comments']]
    if len({c['comment_id'] for c in allcomments}) != len(allcomments):
        raise ValueError('DUPLICATE_COMMENT_ID')
    if len(captures) != len(details):
        raise ValueError('CAPTURE_INVENTORY_MISMATCH')
    rows = []
    for row in coverage['videos']:
        r = dict(row)
        r['coverage_class'] = ('COUNT_RECONCILED_NO_PAGINATION_FAULT' if r['enumeration_complete'] and r['reported_count_matches_capture'] else
                              'COUNT_RECONCILED_AFTER_DEDUPLICATION' if r['count_stable'] and r['reported_count_matches_capture'] else
                              'COUNT_DISCREPANCY_UNRESOLVED')
        rows.append(r)
    gap = None
    if args.gap_audit:
        g = json.loads(args.gap_audit.read_text())
        sets = [set(r['id'] for r in c['records']) for c in g['captures']]
        if len(sets) != 3:
            raise ValueError('EXPECTED_THREE_AUDIT_PASSES')
        initial = {c['comment_id'] for c in allcomments if c['video_id'] == g['video_id']}
        gap = {'video_id': g['video_id'], 'reported_counts': g['reported_counts'], 'requests': g['api_requests'],
               'runs': [{'order': c['order'], 'returned_unique': len(s), 'new_ids_against_initial': len(s-initial),
                         'faults': c['summary']['faults']} for c, s in zip(g['captures'], sets)],
               'two_time_sets_identical': sets[0] == sets[2], 'relevance_subset_of_time': sets[1] <= sets[0],
               'root_cause': 'UNKNOWN', 'warning': 'Exhausting a ranked listing did not establish full count coverage.'}
    summary = {k: v for k, v in coverage.items() if k not in {'videos', 'description_chapter_candidates'}}
    summary.update({'analysis_version': '3.0.0', 'total_unique_comments': len(allcomments),
                    'coverage_classes': dict(Counter(r['coverage_class'] for r in rows)),
                    'source_hashes': {'private_input_archive_zip': args.source_archive_sha256} if args.source_archive_sha256 else {},
                    'count_discrepancy_audit': gap, 'videos': rows,
                    'interpretation': 'API-visible published text; count reconciliation is not an atomic snapshot or a semantic review of every comment.'})
    write(output / 'data/comment-coverage-analysis-v1.json', summary)
    marker_rows = []
    for vid, v in details.items():
        marker_rows.append({'video_id': vid, 'description_sha256': sha(v['description']),
                            **markers(v['description'], inv[vid].get('duration_seconds'))})
    marker_summary = {'videos': len(marker_rows), 'videos_with_markers': sum(bool(r['markers']) for r in marker_rows),
                      'markers': sum(len(r['markers']) for r in marker_rows),
                      'chapter_sequence_candidates': sum(r['chapter_sequence_candidate'] for r in marker_rows),
                      'videos_with_parse_issues': sum(bool(r['issues']) for r in marker_rows)}
    write(output / 'data/description-time-markers-v2.json', {'summary': marker_summary, 'videos': marker_rows})
    nodes, edges = {}, []

    def node(uri, kind, **attrs):
        nid = 'n-' + sha(uri)[:24]
        if nid not in nodes:
            nodes[nid] = {'id': nid, 'uri': uri, 'kind': kind, **attrs}
        if nodes[nid]['kind'] == 'linked_resource' and kind != 'linked_resource':
            nodes[nid]['kind'] = kind
        return nid

    channel = node('https://www.youtube.com/channel/UCwBhBDsqiQflTMLy2epbQVw', 'channel')
    for vid in inv:
        child = node('https://www.youtube.com/watch?v=' + vid, 'video')
        edges.append({'from': channel, 'to': child, 'relation': 'PUBLIC_UPLOAD_AT_CAPTURE'})
    direct = json.loads((oldroot / 'data/youtube-description-edges-v1.json').read_text())['edges']
    for e in direct:
        target_uri = canonical_url(e['original_url'])
        if not target_uri:
            continue
        edges.append({'from': node('https://www.youtube.com/watch?v=' + e['from_video_id'], 'video'),
                      'to': node(target_uri, 'linked_resource'), 'relation': 'DESCRIPTION_LINK',
                      'classifier_hint': e['edge_class'], 'original_url': e['original_url'],
                      'source_description_sha256': sha(details[e['from_video_id']]['description'])})
    comment_link_count = 0
    for c in allcomments:
        urls = sorted({u for raw in c['urls'] if (u := canonical_url(raw))})
        if not urls:
            continue
        source = node(c['source_url'], 'comment', text_sha256=c['text_sha256'], creator=c['creator'],
                      parent_comment_id=c['parent_id'], published_at=c['published_at'], updated_at=c['updated_at'])
        edges.append({'from': node('https://www.youtube.com/watch?v=' + c['video_id'], 'video'),
                      'to': source, 'relation': 'HAS_COMMENT_SOURCE'})
        for uri in urls:
            edges.append({'from': source, 'to': node(uri, 'linked_resource'),
                          'relation': 'CREATOR_LINK' if c['creator'] else 'AUDIENCE_LINK',
                          'trust': 'unreviewed_discovery_not_endorsement'})
            comment_link_count += 1
    frontier = json.loads((oldroot / 'data/direct-link-frontier-v1.json').read_text())
    aliases = []
    for row in frontier['expansions']['implementation_candidates']:
        repo = row.get('repository', {})
        if not repo.get('full_name'):
            continue
        src = canonical_url(row['canonical_url'])
        dest = 'https://github.com/' + repo['full_name']
        aliases.append({'discovered_url': row['canonical_url'], 'observed_full_name': repo['full_name'],
                        'head_sha': repo.get('head_sha'), 'readme_blob_sha': (repo.get('readme') or {}).get('blob_sha')})
        edges.append({'from': node(src, 'linked_resource'), 'to': node(dest, 'repository'),
                      'relation': 'RESOLVES_TO_AT_CAPTURE', 'revision': repo.get('head_sha')})
    gs = {'nodes': len(nodes), 'edges': len(edges), 'comment_url_edges': comment_link_count,
          'comment_link_target_urls': len({nodes[e['to']]['uri'] for e in edges if e['relation'] in {'AUDIENCE_LINK', 'CREATOR_LINK'}}),
          'priority_github_url_targets': len(aliases), 'observed_repository_identities': len({x['observed_full_name'].lower() for x in aliases})}
    if not all(e['from'] in nodes and e['to'] in nodes for e in edges):
        raise ValueError('DANGLING_GRAPH_EDGE')
    write(output / 'data/discovery-graph-v3.json', {'summary': gs, 'nodes': list(nodes.values()), 'edges': edges,
          'repository_aliases': aliases, 'limits': ['No automatic execution/fetch of comment URLs.',
          'Depth remains bounded; this is not a closed bibliography.', 'Alias resolution at capture does not prove historical code lineage.']})
    bycomment = {c['video_id']: [] for c in allcomments}
    for c in allcomments:
        bycomment[c['video_id']].append(c)
    bymarkers = {r['video_id']: r for r in marker_rows}
    index = []
    for vid, v in inv.items():
        index.append({'video_id': vid, 'title': v['title'], 'published_at': v.get('published_at'),
                      'source_url': v['canonical_url'], 'duration_seconds': v.get('duration_seconds'),
                      'description_present': bool(details[vid]['description']),
                      'description_time_markers': len(bymarkers[vid]['markers']),
                      'comments': len(bycomment.get(vid, [])), 'creator_comments': sum(c['creator'] for c in bycomment.get(vid, [])),
                      'transcript_state': 'FULL_TEXT_NOT_ACQUIRED',
                      'content_review_scope': 'description and comment metadata processed; semantic review recorded separately; no claim of watching full video'})
    write(output / 'data/per-video-evidence-index-v3.json', {'videos': index})
    write(output / 'data/primitive-verification-v1.json', primitive_check())
    print(json.dumps({'comments': len(allcomments), 'coverage_classes': summary['coverage_classes'],
                      'chapters': marker_summary, 'graph': gs, 'primitive': primitive_check()}, indent=2))


if __name__ == '__main__':
    main()
