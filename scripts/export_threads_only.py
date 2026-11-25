#!/usr/bin/env python3
"""Export GitHub discussion threads for selected repositories into the private
registry, without bundling, verifying completeness, or authorising deletion.

This is additive only: it reads threads from each source repository and stores
them in PhenoRegistry under repos/<repo>/threads/. It never deletes or modifies
source repositories.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts import prepare_deletion


def gh_contents(path: str) -> tuple[bool, object]:
    """Read back a registry contents path; returns (ok, parsed_json_or_error)."""
    code, body = prepare_deletion.gh_api(path)
    if code != 0:
        return False, body
    try:
        return True, json.loads(body)
    except Exception as exc:
        return False, f"unparseable response: {exc}: {body[:200]}"


def export_repo_threads(owner: str, registry: str, repo: str) -> dict:
    result = {
        "repo": repo,
        "issues": 0,
        "pulls": 0,
        "comments": 0,
        "stored": [],
        "store_errors": [],
        "registry_holds": False,
        "registry_detail": "",
    }

    try:
        ok, threads = prepare_deletion.export_threads(owner, repo)
    except Exception as exc:
        result["store_errors"].append(f"thread export failed: {exc}")
        threads = {"issues": [], "pulls": [], "comments": []}
        ok = False
    if not ok and not result["store_errors"]:
        result["store_errors"].append("thread export failed")
        threads = {"issues": [], "pulls": [], "comments": []}

    issues = threads.get("issues") or []
    pulls = threads.get("pulls") or []
    comments = threads.get("comments") or []
    result["issues"] = len(issues)
    result["pulls"] = len(pulls)
    result["comments"] = len(comments)

    # Store each non-empty dataset under threads/ for explicit read-back path.
    for name, data in (
        ("issues.json", issues),
        ("pulls.json", pulls),
        ("issue-comments.json", comments),
    ):
        if not data:
            continue
        try:
            stored_ok, ref = prepare_deletion.store_file(
                registry, owner, repo, "threads", name, json.dumps(data, indent=1).encode()
            )
        except Exception as exc:
            stored_ok, ref = False, f"exception: {exc}"
        if stored_ok:
            result["stored"].append(f"{name}@{ref}")
        else:
            result["store_errors"].append(f"{name}: {ref}")

    # Read back the registry contents after export (required confirmation).
    path = f"repos/{owner}/{registry}/contents/repos/{repo}/threads"
    try:
        ok_rb, body = gh_contents(path)
    except Exception as exc:
        ok_rb, body = False, f"read-back exception: {exc}"
    if ok_rb and isinstance(body, list):
        names = sorted(item.get("name", "") for item in body if isinstance(item, dict))
        result["registry_holds"] = True
        result["registry_detail"] = ", ".join(n for n in names if n) or "(empty dir)"
    else:
        result["registry_holds"] = False
        if result["issues"] == 0 and result["pulls"] == 0 and result["comments"] == 0 and not result["store_errors"]:
            result["registry_detail"] = "no threads to store"
        else:
            detail = body if isinstance(body, str) else json.dumps(body)[:200]
            result["registry_detail"] = str(detail)[:200]

    return result


def print_table(rows: list[dict]) -> None:
    headers = ["Repository", "Issues", "Pulls", "Comments", "Registry holds output", "Detail"]
    table_rows = []
    for r in rows:
        holds = "yes" if r["registry_holds"] else "no"
        detail = r["registry_detail"] or ""
        if r["store_errors"]:
            err = "; ".join(r["store_errors"])
            detail = f"{detail} | store errors: {err}" if detail else f"store errors: {err}"
        table_rows.append([
            r["repo"],
            str(r["issues"]),
            str(r["pulls"]),
            str(r["comments"]),
            holds,
            detail,
        ])

    widths = [len(h) for h in headers]
    for row in table_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt(row: list[str]) -> str:
        return " | ".join(cell.ljust(widths[i]) for i, cell in enumerate(row))

    sep = "-+-".join("-" * w for w in widths)
    print(fmt(headers))
    print(sep)
    for row in table_rows:
        print(fmt(row))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("repos", nargs="+", help="Repository names to export threads for")
    ap.add_argument("--owner", default=prepare_deletion.DEFAULT_OWNER)
    ap.add_argument("--registry", default=prepare_deletion.DEFAULT_REGISTRY)
    ap.add_argument("--json-out", help="Optional path to write machine-readable results")
    args = ap.parse_args()

    rows = []
    for repo in args.repos:
        print(f"== {repo}", flush=True)
        try:
            row = export_repo_threads(args.owner, args.registry, repo)
        except Exception as exc:
            row = {
                "repo": repo,
                "issues": 0,
                "pulls": 0,
                "comments": 0,
                "stored": [],
                "store_errors": [f"unexpected error: {exc}"],
                "registry_holds": False,
                "registry_detail": "skipped due to error",
            }
        rows.append(row)
        print(
            f"   threads  {row['issues']} issues, {row['pulls']} pulls, {row['comments']} comments; "
            f"registry={'yes' if row['registry_holds'] else 'no'} ({row['registry_detail']})",
            flush=True,
        )
        if row["store_errors"]:
            for err in row["store_errors"]:
                print(f"   warning  {err}", flush=True)

    print()
    print_table(rows)

    totals = {
        "repos": len(rows),
        "issues": sum(r["issues"] for r in rows),
        "pulls": sum(r["pulls"] for r in rows),
        "comments": sum(r["comments"] for r in rows),
        "threads_total": sum(r["issues"] + r["pulls"] + r["comments"] for r in rows),
        "registry_confirmed": sum(1 for r in rows if r["registry_holds"]),
        "repos_with_store_errors": sum(1 for r in rows if r["store_errors"]),
    }
    print()
    print(
        "TOTALS: {repos} repos, {issues} issues, {pulls} pulls, {comments} comments, "
        "{threads_total} threads preserved; registry confirmed for {registry_confirmed} repos; "
        "{repos_with_store_errors} repos with store errors".format(**totals)
    )

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as fh:
            json.dump({"rows": rows, "totals": totals}, fh, indent=2)
        print(f"JSON results written to {args.json_out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
