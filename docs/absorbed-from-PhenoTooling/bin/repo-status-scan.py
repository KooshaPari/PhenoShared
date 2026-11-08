#!/usr/bin/env python3
# repo-status-scan.py
# ----------------------------------------------------------------------------
# Repository status scanner. Lists every repo under a given GitHub owner and
# reports visibility, archived state, default branch, last push, size, and
# counts of open issues / PRs. Output is a Markdown table (default) or CSV
# when --format csv is passed.
#
# Usage
#   python bin/repo-status-scan.py --owner KooshaPari [--format md|csv] [--include-archived] [--include-private]
#                                  [--out PATH] [--state open|closed|all] [--sort name|pushed|size]
#
# Exits 0 always; the script is a read-only observation tool.
# ----------------------------------------------------------------------------
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from typing import Any, Iterable


def gh_api(path: str, paginate: bool = True) -> Any:
    cmd = ["gh", "api", path]
    if paginate:
        cmd.append("--paginate")
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        sys.stderr.write(f"[repo-status-scan][ERROR] gh api {path} failed: {proc.stderr.strip()}\n")
        sys.exit(2)
    return json.loads(proc.stdout) if proc.stdout.strip() else []


def gather_repos(owner: str, include_archived: bool, include_private: bool) -> Iterable[dict]:
    repos = gh_api(f"/orgs/{owner}/repos?per_page=100&type=all")
    for r in repos:
        if r.get("archived") and not include_archived:
            continue
        if r.get("private") and not include_private:
            continue
        yield r


def render_markdown(repos: list[dict], sort: str) -> str:
    keys = ("nameWithOwner", "visibility", "archived", "default_branch", "pushed_at", "size_kb", "open_issues", "open_prs", "description")
    header = "| " + " | ".join(["nameWithOwner", "visibility", "archived", "default", "pushed_at", "size_kb", "issues", "prs", "description"]) + " |"
    sep = "|" + "|".join(["---"] * 9) + "|"

    rows = []
    for r in repos:
        row = {
            "nameWithOwner": r.get("full_name", "?"),
            "visibility": "private" if r.get("private") else "public",
            "archived": "yes" if r.get("archived") else "no",
            "default": r.get("default_branch", "?"),
            "pushed_at": (r.get("pushed_at") or "")[:10],
            "size_kb": r.get("size", 0),
            "open_issues": r.get("open_issues_count", 0),
            "open_prs": 0,  # filled in below
            "description": (r.get("description") or "").replace("|", "/")[:80],
        }
        rows.append(row)

    # PR counts require a second API call per repo; we lazily do that.
    for row in rows:
        prs = gh_api(f"/repos/{row['nameWithOwner']}/pulls?state=open&per_page=1", paginate=False)
        if isinstance(prs, list):
            row["open_prs"] = min(len(prs), 1) if prs else 0  # approximation; use total count from header if needed

    sort_key = {"name": lambda r: r["nameWithOwner"], "pushed": lambda r: r["pushed_at"], "size": lambda r: -r["size_kb"]}.get(sort, lambda r: r["nameWithOwner"])
    rows.sort(key=sort_key)

    lines = [f"# Repository status scan ({len(rows)} repos)", "", header, sep]
    for r in rows:
        lines.append("| " + " | ".join(str(r[k]) for k in keys) + " |")
    return "\n".join(lines) + "\n"


def render_csv(repos: list[dict]) -> str:
    buf = []
    writer = csv.writer(buf)
    writer.writerow(["nameWithOwner", "visibility", "archived", "default_branch", "pushed_at", "size_kb", "open_issues", "description"])
    for r in repos:
        writer.writerow([
            r.get("full_name", ""),
            "private" if r.get("private") else "public",
            "yes" if r.get("archived") else "no",
            r.get("default_branch", ""),
            (r.get("pushed_at") or "")[:10],
            r.get("size", 0),
            r.get("open_issues_count", 0),
            (r.get("description") or "")[:160],
        ])
    return "\n".join(buf) + "\n"


def main() -> int:
    p = argparse.ArgumentParser(description="Scan an org's repositories and emit a status table.")
    p.add_argument("--owner", required=True, help="GitHub owner/org to scan (e.g. KooshaPari)")
    p.add_argument("--format", choices=("md", "csv"), default="md")
    p.add_argument("--include-archived", action="store_true", help="include archived repos in the output")
    p.add_argument("--include-private", action="store_true", help="include private repos in the output")
    p.add_argument("--out", help="write to this path instead of stdout")
    p.add_argument("--sort", choices=("name", "pushed", "size"), default="name")
    args = p.parse_args()

    repos = list(gather_repos(args.owner, args.include_archived, args.include_private))
    body = render_markdown(repos, args.sort) if args.format == "md" else render_csv(repos)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(body)
    else:
        sys.stdout.write(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
