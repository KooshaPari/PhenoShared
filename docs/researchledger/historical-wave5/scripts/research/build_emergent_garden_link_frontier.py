#!/usr/bin/env python3
"""Expand high-value outbound links from normalized Emergent Garden descriptions.

The pass expands only GitHub implementation candidates, arXiv primary-source
candidates, and creator-controlled web surfaces. Raw response bodies are never
committed; outputs retain metadata, hashes, short excerpts, and revision pins.
"""

from __future__ import annotations

import argparse
import base64
import collections
import datetime as dt
import hashlib
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable

CAMPAIGN_ID = "eg-nested-corpus-2026-09"
USER_AGENT = "ResearchLedger-EmergentGarden/1.0 (+https://github.com/KooshaPari/ResearchLedger)"
GITHUB_API = "https://api.github.com"
ARXIV_API = "https://export.arxiv.org/api/query"
MAX_BODY_BYTES = 2_000_000
HIGH_VALUE_CLASSES = {
    "IMPLEMENTATION_CANDIDATE",
    "PRIMARY_SOURCE_CANDIDATE",
    "AUTHOR_DIRECT",
}
TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)
HEADING_RE = re.compile(r"<h[1-3][^>]*>(.*?)</h[1-3]>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")
WHITESPACE_RE = re.compile(r"\s+")


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def clean_text(value: str) -> str:
    return WHITESPACE_RE.sub(" ", html.unescape(TAG_RE.sub(" ", value))).strip()


def bounded_excerpt(value: str, limit: int = 420) -> str:
    return clean_text(value)[:limit]


def request_bytes(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    max_bytes: int = MAX_BODY_BYTES,
) -> tuple[bytes, dict[str, Any]]:
    merged_headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, application/atom+xml, text/html;q=0.9, */*;q=0.8",
    }
    if headers:
        merged_headers.update(headers)
    request = urllib.request.Request(url, headers=merged_headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read(max_bytes + 1)
        truncated = len(body) > max_bytes
        if truncated:
            body = body[:max_bytes]
        metadata = {
            "requested_url": url,
            "final_url": response.geturl(),
            "http_status": response.status,
            "content_type": response.headers.get_content_type(),
            "content_length_header": response.headers.get("Content-Length"),
            "captured_byte_count": len(body),
            "capture_truncated": truncated,
            "etag": response.headers.get("ETag"),
            "last_modified": response.headers.get("Last-Modified"),
        }
        return body, metadata


def request_json(url: str, *, headers: dict[str, str] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    body, metadata = request_bytes(url, headers=headers)
    return json.loads(body.decode("utf-8")), {**metadata, "response_sha256": sha256_bytes(body)}


def chunks(values: list[str], size: int) -> Iterable[list[str]]:
    for index in range(0, len(values), size):
        yield values[index : index + size]


def parse_repo_url(url: str) -> tuple[str, str] | None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.netloc.lower() not in {"github.com", "www.github.com"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        return None
    return parts[0], parts[1].removesuffix(".git")


def github_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def github_get(path: str) -> tuple[dict[str, Any], dict[str, Any]]:
    return request_json(f"{GITHUB_API}{path}", headers=github_headers())


def decode_github_content(payload: dict[str, Any]) -> str | None:
    if payload.get("encoding") != "base64" or not payload.get("content"):
        return None
    try:
        return base64.b64decode(payload["content"], validate=False).decode("utf-8", errors="replace")
    except (ValueError, UnicodeDecodeError):
        return None


def expand_github(target: dict[str, Any]) -> dict[str, Any]:
    parsed = parse_repo_url(target["canonical_url"])
    if not parsed:
        return {**target, "expansion_state": "INVALID_REPOSITORY_URL"}
    owner, repo = parsed
    full_name = f"{owner}/{repo}"
    result: dict[str, Any] = {**target, "repository_full_name": full_name, "expansion_state": "FAILED"}
    try:
        repository, repository_response = github_get(f"/repos/{owner}/{repo}")
        default_branch = repository.get("default_branch") or "main"
        branch, branch_response = github_get(
            f"/repos/{owner}/{repo}/branches/{urllib.parse.quote(default_branch, safe='')}"
        )
        readme_metadata: dict[str, Any] | None = None
        readme_error: str | None = None
        try:
            readme, readme_response = github_get(
                f"/repos/{owner}/{repo}/readme?ref={urllib.parse.quote(default_branch, safe='')}"
            )
            readme_text = decode_github_content(readme)
            readme_metadata = {
                "path": readme.get("path"),
                "blob_sha": readme.get("sha"),
                "size": readme.get("size"),
                "response_sha256": readme_response.get("response_sha256"),
                "content_sha256": sha256_text(readme_text) if readme_text is not None else None,
                "excerpt": bounded_excerpt(readme_text or "", 500),
                "headings": [
                    clean_text(line)
                    for line in (readme_text or "").splitlines()
                    if line.lstrip().startswith("#")
                ][:20],
            }
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
            readme_error = f"{type(error).__name__}: {error}"

        license_payload = repository.get("license") or {}
        parent_payload = repository.get("parent") or {}
        source_payload = repository.get("source") or {}
        result.update(
            {
                "expansion_state": "EXPANDED",
                "repository": {
                    "full_name": repository.get("full_name") or full_name,
                    "html_url": repository.get("html_url"),
                    "description": repository.get("description"),
                    "fork": bool(repository.get("fork")),
                    "archived": bool(repository.get("archived")),
                    "disabled": bool(repository.get("disabled")),
                    "visibility": repository.get("visibility"),
                    "default_branch": default_branch,
                    "head_sha": ((branch.get("commit") or {}).get("sha")),
                    "head_commit_url": ((branch.get("commit") or {}).get("html_url")),
                    "created_at": repository.get("created_at"),
                    "updated_at": repository.get("updated_at"),
                    "pushed_at": repository.get("pushed_at"),
                    "size_kib": repository.get("size"),
                    "primary_language": repository.get("language"),
                    "topics": sorted(repository.get("topics") or []),
                    "license_spdx": license_payload.get("spdx_id"),
                    "open_issues_count": repository.get("open_issues_count"),
                    "parent_full_name": parent_payload.get("full_name"),
                    "source_full_name": source_payload.get("full_name"),
                    "repository_response_sha256": repository_response.get("response_sha256"),
                    "branch_response_sha256": branch_response.get("response_sha256"),
                    "readme": readme_metadata,
                    "readme_error": readme_error,
                },
            }
        )
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as error:
        result["error"] = f"{type(error).__name__}: {error}"
    return result


def arxiv_id_from_url(url: str) -> str | None:
    parsed = urllib.parse.urlsplit(url)
    if parsed.netloc.lower() not in {"arxiv.org", "www.arxiv.org"}:
        return None
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2 or parts[0] not in {"abs", "pdf", "html"}:
        return None
    return parts[1].removesuffix(".pdf")


def parse_arxiv_entries(body: bytes) -> dict[str, dict[str, Any]]:
    root = ET.fromstring(body)
    namespaces = {
        "atom": "http://www.w3.org/2005/Atom",
        "arxiv": "http://arxiv.org/schemas/atom",
    }
    results: dict[str, dict[str, Any]] = {}
    for entry in root.findall("atom:entry", namespaces):
        versioned_id = (entry.findtext("atom:id", default="", namespaces=namespaces) or "").rstrip("/").split("/")[-1]
        base_id = re.sub(r"v\d+$", "", versioned_id)
        title = clean_text(entry.findtext("atom:title", default="", namespaces=namespaces))
        summary = clean_text(entry.findtext("atom:summary", default="", namespaces=namespaces))
        primary = entry.find("arxiv:primary_category", namespaces)
        results[base_id] = {
            "arxiv_id": base_id,
            "versioned_id": versioned_id,
            "title": title,
            "abstract_sha256": sha256_text(summary),
            "abstract_excerpt": summary[:700],
            "authors": [
                clean_text(author.findtext("atom:name", default="", namespaces=namespaces))
                for author in entry.findall("atom:author", namespaces)
            ],
            "published_at": entry.findtext("atom:published", default=None, namespaces=namespaces),
            "updated_at": entry.findtext("atom:updated", default=None, namespaces=namespaces),
            "categories": sorted(
                {
                    category.attrib.get("term", "")
                    for category in entry.findall("atom:category", namespaces)
                    if category.attrib.get("term")
                }
            ),
            "primary_category": primary.attrib.get("term") if primary is not None else None,
            "comment": clean_text(entry.findtext("arxiv:comment", default="", namespaces=namespaces)),
            "journal_reference": clean_text(entry.findtext("arxiv:journal_ref", default="", namespaces=namespaces)),
            "doi": clean_text(entry.findtext("arxiv:doi", default="", namespaces=namespaces)),
            "links": {
                link.attrib.get("title") or link.attrib.get("rel") or "link": link.attrib.get("href")
                for link in entry.findall("atom:link", namespaces)
                if link.attrib.get("href")
            },
        }
    return results


def expand_arxiv(targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    valid_ids = [value for value in (arxiv_id_from_url(target["canonical_url"]) for target in targets) if value]
    if not valid_ids:
        return [{**target, "expansion_state": "INVALID_ARXIV_URL"} for target in targets]
    records: dict[str, dict[str, Any]] = {}
    response_metadata: dict[str, Any] = {}
    error_text: str | None = None
    try:
        url = f"{ARXIV_API}?{urllib.parse.urlencode({'id_list': ','.join(valid_ids), 'max_results': len(valid_ids)})}"
        body, response_metadata = request_bytes(url, headers={"Accept": "application/atom+xml"})
        response_metadata["response_sha256"] = sha256_bytes(body)
        records = parse_arxiv_entries(body)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError, ET.ParseError) as error:
        error_text = f"{type(error).__name__}: {error}"

    results: list[dict[str, Any]] = []
    for target in targets:
        arxiv_id = arxiv_id_from_url(target["canonical_url"])
        paper = records.get(arxiv_id or "")
        if paper:
            results.append(
                {
                    **target,
                    "expansion_state": "EXPANDED",
                    "paper": paper,
                    "provider_response": response_metadata,
                }
            )
        else:
            results.append(
                {
                    **target,
                    "expansion_state": "FAILED",
                    "arxiv_id": arxiv_id,
                    "error": error_text or "arXiv API returned no matching entry",
                }
            )
    return results


def expand_web(target: dict[str, Any]) -> dict[str, Any]:
    result = {**target, "expansion_state": "FAILED"}
    try:
        body, metadata = request_bytes(target["canonical_url"])
        text = body.decode("utf-8", errors="replace")
        title_match = TITLE_RE.search(text)
        result.update(
            {
                "expansion_state": "EXPANDED",
                "capture": {
                    **metadata,
                    "response_sha256": sha256_bytes(body),
                    "page_title": clean_text(title_match.group(1)) if title_match else None,
                    "headings": [clean_text(match) for match in HEADING_RE.findall(text)][:20],
                    "text_excerpt": bounded_excerpt(text, 500),
                },
            }
        )
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError) as error:
        result["error"] = f"{type(error).__name__}: {error}"
    return result


def grouped_targets(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for edge in edges:
        edge_class = edge.get("edge_class")
        canonical_url = edge.get("canonical_url")
        if edge_class not in HIGH_VALUE_CLASSES or not canonical_url:
            continue
        key = (edge_class, canonical_url)
        target = grouped.setdefault(
            key,
            {
                "edge_class": edge_class,
                "canonical_url": canonical_url,
                "domain": edge.get("domain"),
                "occurrence_count": 0,
                "source_videos": [],
            },
        )
        target["occurrence_count"] += 1
        source = {
            "video_id": edge.get("from_video_id"),
            "title": edge.get("from_title"),
            "published_at": edge.get("from_published_at"),
        }
        if source not in target["source_videos"]:
            target["source_videos"].append(source)
    results = list(grouped.values())
    for target in results:
        target["source_videos"].sort(
            key=lambda row: ((row.get("published_at") or ""), row.get("video_id") or ""),
            reverse=True,
        )
    return sorted(results, key=lambda row: (row["edge_class"], row["canonical_url"]))


def markdown_escape(value: Any) -> str:
    return str(value if value not in (None, "") else "—").replace("|", "\\|").replace("\n", " ")


def source_video_labels(target: dict[str, Any]) -> str:
    return "; ".join(
        source.get("title") or source.get("video_id") or "unknown"
        for source in target.get("source_videos") or []
    )


def build_report(frontier: dict[str, Any]) -> str:
    summary = frontier["summary"]
    lines = [
        "# Emergent Garden Direct-Link Expansion — Wave 2",
        "",
        f"**Campaign:** `{CAMPAIGN_ID}`  ",
        f"**Generated:** {frontier['generated_at']}  ",
        f"**Input ledger SHA-256:** `{frontier['input']['sha256']}`  ",
        f"**Input inventory complete:** **{'yes' if frontier['input']['inventory_complete'] else 'no'}**  ",
        "**G3 direct-graph scope:** recent-window high-value links only",
        "",
        "## Verdict",
        "",
        "The official Atom-feed window exposes a useful direct graph even though the complete channel inventory is blocked. This pass resolves unique implementation candidates through the GitHub REST API, primary papers through arXiv, and creator-controlled pages through bounded HTTP captures. It does not upgrade the recent-window sample into a complete channel graph.",
        "",
        "## Coverage",
        "",
        "| Measure | Count |",
        "|---|---:|",
        f"| Description edges in input ledger | {summary['input_edges']} |",
        f"| Unique targets in input ledger | {summary['input_unique_targets']} |",
        f"| Unique high-value targets | {summary['high_value_unique_targets']} |",
        f"| Unique implementation repositories | {summary['implementation_targets']} |",
        f"| Unique primary papers | {summary['paper_targets']} |",
        f"| Unique creator-controlled pages | {summary['author_direct_targets']} |",
        f"| Expanded successfully | {summary['expanded']} |",
        f"| Expansion failures | {summary['failed']} |",
        "",
        "## Direct implementation repositories",
        "",
        "| Repository | Source video(s) | Head | README evidence | State |",
        "|---|---|---|---|---|",
    ]
    for item in frontier["expansions"]["implementation_candidates"]:
        repository = item.get("repository") or {}
        readme = repository.get("readme") or {}
        name = repository.get("full_name") or item.get("repository_full_name") or item["canonical_url"]
        url = repository.get("html_url") or item["canonical_url"]
        head = repository.get("head_sha") or "—"
        readme_evidence = readme.get("content_sha256") or readme.get("blob_sha") or "—"
        lines.append(
            f"| [{markdown_escape(name)}]({url}) | {markdown_escape(source_video_labels(item))} | "
            f"`{markdown_escape(head[:12])}` | `{markdown_escape(readme_evidence[:20])}` | "
            f"{markdown_escape(item.get('expansion_state'))} |"
        )

    lines.extend(
        [
            "",
            "## Primary papers",
            "",
            "| Paper | Source video(s) | Version | Primary category | State |",
            "|---|---|---|---|---|",
        ]
    )
    for item in frontier["expansions"]["primary_sources"]:
        paper = item.get("paper") or {}
        title = paper.get("title") or paper.get("arxiv_id") or item["canonical_url"]
        lines.append(
            f"| [{markdown_escape(title)}]({item['canonical_url']}) | {markdown_escape(source_video_labels(item))} | "
            f"`{markdown_escape(paper.get('versioned_id'))}` | {markdown_escape(paper.get('primary_category'))} | "
            f"{markdown_escape(item.get('expansion_state'))} |"
        )

    lines.extend(
        [
            "",
            "## Creator-controlled surfaces",
            "",
            "| Surface | Source video(s) | HTTP | Response hash | State |",
            "|---|---|---:|---|---|",
        ]
    )
    for item in frontier["expansions"]["author_direct"]:
        capture = item.get("capture") or {}
        label = capture.get("page_title") or item["canonical_url"]
        response_hash = capture.get("response_sha256") or "—"
        lines.append(
            f"| [{markdown_escape(label)}]({item['canonical_url']}) | {markdown_escape(source_video_labels(item))} | "
            f"{markdown_escape(capture.get('http_status'))} | `{markdown_escape(response_hash[:20])}` | "
            f"{markdown_escape(item.get('expansion_state'))} |"
        )

    lines.extend(
        [
            "",
            "## Mechanism-level implications",
            "",
            "1. **Foreground execution is a distinct system constraint.** The Age of Empires chain contains both the strategy-generating repository and a screen-capture game runner. A benchmark that tests only strategy text misses resolution, focus, timing, UI-state, and destructive file-write hazards.",
            "2. **Shared-artifact swarms need ownership and merge controls.** The Slopcity surface explicitly gives multiple agents responsibility for a shared hub while also asking them to render, inspect, critique, and revise their own work. That is a useful adversarial case for same-file contention and orphan prevention, not evidence that unbounded parallelism wins.",
            "3. **Embodied planning depends on a separate actuator substrate.** Baritone is a Minecraft pathfinder, while Mindcraft supplies language-agent planning and task structure. Conflating the planner with the actuator hides stale-state, path-execution, and recovery failures.",
            "4. **Open-ended search still requires an evaluator.** The directly linked ASAL and Darwin Gödel Machine papers use learned or benchmark-grounded evaluation rather than treating novelty alone as success.",
            "5. **Fast representations can change the feasible search regime.** The instant neural graphics primitive paper is implementation context for accelerating repeated evaluation; it does not by itself validate recursive self-improvement.",
            "",
            "## Competing interpretations",
            "",
            "- A linked repository may be historical context, an external dependency, a runner, or the creator's implementation; the graph preserves those possibilities instead of collapsing every GitHub edge into authorship.",
            "- A reachable creator page can identify an artifact while still failing to establish its source repository or revision history.",
            "- README claims and paper abstracts describe intended systems and reported results; they are not independent reproductions.",
            "- Failure to capture a page can reflect anti-bot controls, TLS, redirects, or transient network errors rather than absence.",
            "",
            "## Gate transition",
            "",
            "This bounded pass advances the recent-window portion of `G3_DIRECT_GRAPH` to a reproducible expanded state. The campaign-level gate remains partial because `G1_INVENTORY` is blocked and older descriptions have not been enumerated. No additional product-repository fanout is authorized by this report alone.",
            "",
        ]
    )
    return "\n".join(lines)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="docs/corpora/emergent-garden")
    parser.add_argument("--delay-ms", type=int, default=100)
    args = parser.parse_args()
    root = Path(args.root)
    source_path = root / "data" / "youtube-description-edges-v1.json"
    source_bytes = source_path.read_bytes()
    source = json.loads(source_bytes.decode("utf-8"))
    targets = grouped_targets(source.get("edges") or [])

    implementations = [target for target in targets if target["edge_class"] == "IMPLEMENTATION_CANDIDATE"]
    papers = [target for target in targets if target["edge_class"] == "PRIMARY_SOURCE_CANDIDATE"]
    author_direct = [target for target in targets if target["edge_class"] == "AUTHOR_DIRECT"]

    expanded_implementations: list[dict[str, Any]] = []
    for target in implementations:
        expanded_implementations.append(expand_github(target))
        if args.delay_ms:
            time.sleep(args.delay_ms / 1000)

    expanded_papers = expand_arxiv(papers)

    expanded_author_direct: list[dict[str, Any]] = []
    for target in author_direct:
        expanded_author_direct.append(expand_web(target))
        if args.delay_ms:
            time.sleep(args.delay_ms / 1000)

    all_expansions = [*expanded_implementations, *expanded_papers, *expanded_author_direct]
    state_counts = collections.Counter(item.get("expansion_state") for item in all_expansions)
    generated_at = now_utc()
    frontier = {
        "schema_version": "1.0",
        "campaign_id": CAMPAIGN_ID,
        "generated_at": generated_at,
        "input": {
            "path": str(source_path),
            "sha256": sha256_bytes(source_bytes),
            "generated_at": source.get("generated_at"),
            "provider": source.get("provider"),
            "inventory_complete": bool(source.get("inventory_complete")),
        },
        "summary": {
            "input_edges": int((source.get("summary") or {}).get("edges", len(source.get("edges") or []))),
            "input_unique_targets": int((source.get("summary") or {}).get("unique_targets", 0)),
            "high_value_unique_targets": len(targets),
            "implementation_targets": len(implementations),
            "paper_targets": len(papers),
            "author_direct_targets": len(author_direct),
            "expanded": state_counts.get("EXPANDED", 0),
            "failed": len(all_expansions) - state_counts.get("EXPANDED", 0),
            "state_counts": dict(sorted(state_counts.items())),
        },
        "expansions": {
            "implementation_candidates": expanded_implementations,
            "primary_sources": expanded_papers,
            "author_direct": expanded_author_direct,
        },
        "limits": [
            "Input descriptions cover only the official Atom recent window because G1 is blocked.",
            "Repository and web metadata are point-in-time captures, not reproduction results.",
            "README excerpts and abstracts are publication-safe summaries, not full mirrored documents.",
            "Creator-controlled page reachability does not prove source-repository lineage.",
            "Only high-value direct edges are expanded; broader context and social links remain unexpanded.",
        ],
    }

    write_json(root / "data" / "direct-link-frontier-v1.json", frontier)
    report_path = root / "research" / "DIRECT-LINK-EXPANSION-WAVE-2.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(build_report(frontier), encoding="utf-8")
    print(json.dumps(frontier["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
