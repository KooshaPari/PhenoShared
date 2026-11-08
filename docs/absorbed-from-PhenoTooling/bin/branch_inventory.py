#!/usr/bin/env python3
# branch_inventory.py
# ----------------------------------------------------------------------------
# Auto-derive the registry's audit candidate list from the GitHub public API.
#
# WHEN TO USE THIS vs. the manual script
# --------------------------------------
# Use `bin/branch_inventory.py` (this module):
#   * When you want a fresh, live snapshot of the org (e.g. weekly refresh).
#   * When a repo was just created or archived on GitHub and the local
#     disposition index is stale.
#   * When the orchestrator (`bin/absorption-justification.py
#     --refresh-inventory`) drives the audit pipeline.
#
# Keep the manual script (`phenotype-registry/_find_audit_candidates.py`):
#   * When you need a deterministic diff against a checked-in disposition
#     index for offline reproducibility.
#   * When you want to exercise a specific subset (the manual script has
#     a hard-coded `audited` set and a checked-in disposition index).
#
# Both write to the same `audit_candidates.json` path so downstream
# consumers don't need to know which source filled the file last.
#
# RATE-LIMIT BEHAVIOR
# -------------------
# Unauthenticated GitHub REST API: 60 requests/hour per source IP. We use
# `per_page=100` and follow the `Link: rel="next"` header to cover the
# whole org in a single call (~60 repos). A `.branch-inventory-cache.json`
# file in the working directory avoids re-fetching on repeat runs. On 403/429
# the per-repo `error` field carries the API message so the orchestrator
# can still proceed.
#
# CACHE TTL
# --------
# Default TTL is 1 hour (3600s). Override with `--cache-ttl <seconds>`.
# Pass `--no-cache` to always live-fetch.
#
# OUTPUT SCHEMA
# -------------
# Each entry is a JSON object:
#   { "name", "path", "default_branch", "pushed_at", "size_kb",
#     "archived_remote", "is_fork", "fork_parent", "private",
#     "description", "stargazers", "error" }
# Repos archived on GitHub are filtered out. Forks whose parent is NOT in
# the same org are filtered out (third-party mirrors).
# ----------------------------------------------------------------------------
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from typing import Any

API = "https://api.github.com"
UA = "phenotype-tooling/branch_inventory.py"
DEFAULT_ORG = "KooshaPari"
CACHE_FILE = ".branch-inventory-cache.json"
CACHE_TTL = 3600


class GHError(Exception):
    """Non-2xx response from the GitHub API."""


def _get(url: str) -> tuple[Any, dict]:
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": UA,
        "X-GitHub-Api-Version": "2022-11-28",
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8")), dict(r.getheaders())
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:300]
        except Exception:
            pass
        raise GHError(f"HTTP {e.code} for {url}: {body}")
    except urllib.error.URLError as e:
        raise GHError(f"URL error for {url}: {e.reason}")


def _next(headers: dict) -> str | None:
    link = headers.get("Link") or headers.get("link") or ""
    for part in link.split(","):
        if 'rel="next"' in part:
            url = part.split(";")[0].strip()
            if url.startswith("<") and url.endswith(">"):
                return url[1:-1]
    return None


def list_repos(org: str) -> list[dict]:
    url = f"{API}/orgs/{org}/repos?per_page=100&type=public"
    out: list[dict] = []
    for _ in range(20):  # 2000-repo cap, plenty for a single org
        data, hdr = _get(url)
        if not isinstance(data, list):
            raise GHError(f"expected array, got {type(data).__name__}")
        out.extend(data)
        nxt = _next(hdr)
        if not nxt:
            break
        url = nxt
    return out


def normalize(raw: dict, org: str) -> dict:
    owner = (raw.get("owner") or {}).get("login") or org
    name = raw.get("name") or "?"
    parent = raw.get("parent") or raw.get("source") or {}
    p_full = None
    if parent.get("name") and (parent.get("owner") or {}).get("login"):
        p_full = f"{parent['owner']['login']}/{parent['name']}"
    return {
        "name": name,
        "path": f"{owner}/{name}",
        "default_branch": raw.get("default_branch") or "main",
        "pushed_at": raw.get("pushed_at"),
        "size_kb": raw.get("size", 0) or 0,
        "archived_remote": bool(raw.get("archived", False)),
        "is_fork": bool(raw.get("fork", False)),
        "fork_parent": p_full,
        "private": bool(raw.get("private", False)),
        "description": raw.get("description") or "",
        "stargazers": raw.get("stargazers_count", 0) or 0,
        "error": None,
    }


def filter_candidates(repos: list[dict], org: str) -> list[dict]:
    """Drop archived repos and out-of-org forks."""
    out = []
    for r in repos:
        if r["archived_remote"]:
            continue
        if r["is_fork"]:
            p_owner = (r["fork_parent"] or "").split("/")[0]
            if p_owner.lower() != org.lower():
                continue
        out.append(r)
    return out


def load_cache(path: str, ttl: int) -> dict | None:
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        if (time.time() - float(d.get("fetched_at", 0))) > ttl:
            return None
        return d
    except (OSError, ValueError, json.JSONDecodeError):
        return None


def save_cache(path: str, org: str, repos: list[dict]) -> None:
    if not path:
        return
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump({
                "fetched_at": time.time(),
                "org": org,
                "count": len(repos),
                "repos": repos,
            }, f, indent=2)
            f.write("\n")
    except OSError as e:
        sys.stderr.write(f"[branch_inventory][WARN] cache write failed: {e}\n")


def build(org: str, use_cache: bool, cache_path: str, ttl: int,
          dry_run: bool) -> list[dict]:
    if use_cache and not dry_run:
        c = load_cache(cache_path, ttl)
        if c and c.get("org") == org:
            sys.stderr.write(
                f"[branch_inventory] cache hit: {cache_path} "
                f"(age={int(time.time() - c['fetched_at'])}s, "
                f"count={c.get('count', 0)})\n"
            )
            return c.get("repos", [])
    if dry_run:
        sys.stderr.write(
            f"[branch_inventory][DRY-RUN] would GET {API}/orgs/{org}/repos\n"
        )
        return [{
            "name": "<dry-run>",
            "path": f"{org}/<dry-run>",
            "default_branch": "main",
            "pushed_at": None,
            "size_kb": 0,
            "archived_remote": False,
            "is_fork": False,
            "fork_parent": None,
            "private": False,
            "description": "dry-run placeholder; no API call was made",
            "stargazers": 0,
            "error": None,
        }]
    try:
        raw = list_repos(org)
    except GHError as e:
        sys.stderr.write(f"[branch_inventory][ERROR] {e}\n")
        return [{
            "name": "<api-error>",
            "path": f"{org}/<api-error>",
            "default_branch": "main",
            "pushed_at": None,
            "size_kb": 0,
            "archived_remote": False,
            "is_fork": False,
            "fork_parent": None,
            "private": False,
            "description": "",
            "stargazers": 0,
            "error": str(e),
        }]
    norm = [normalize(r, org) for r in raw]
    cands = filter_candidates(norm, org)
    save_cache(cache_path, org, cands)
    return cands


def write(out: str, repos: list[dict]) -> str:
    if out == "-":
        sys.stdout.write(json.dumps(repos, indent=2))
        sys.stdout.write("\n")
        return "-"
    parent = os.path.dirname(os.path.abspath(out))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(repos, f, indent=2)
        f.write("\n")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Auto-derive audit candidates from the GitHub API."
    )
    p.add_argument("--org", default=DEFAULT_ORG,
                   help=f"GitHub org (default: {DEFAULT_ORG})")
    p.add_argument("--out", default="-", help="output path (default: stdout)")
    p.add_argument("--dry-run", action="store_true",
                   help="skip API call, emit a placeholder row")
    p.add_argument("--no-cache", dest="use_cache", action="store_false",
                   help="always live-fetch")
    p.add_argument("--cache-path", default=CACHE_FILE,
                   help=f"cache file (default: {CACHE_FILE})")
    p.add_argument("--cache-ttl", type=int, default=CACHE_TTL,
                   help=f"cache TTL seconds (default: {CACHE_TTL})")
    args = p.parse_args(argv)

    repos = build(
        org=args.org,
        use_cache=args.use_cache,
        cache_path=args.cache_path,
        ttl=args.cache_ttl,
        dry_run=args.dry_run,
    )
    written = write(args.out, repos)
    where = "stdout" if written == "-" else written
    sys.stderr.write(f"[branch_inventory] wrote {len(repos)} candidate(s) to {where}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())