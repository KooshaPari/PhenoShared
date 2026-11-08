#!/usr/bin/env python3
"""Regenerate SECURITY_DEPS_LEDGER.md from `cargo audit` output + GitHub dependabot alerts."""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LEDGER_PATH = REPO_ROOT / "SECURITY_DEPS_LEDGER.md"

OPEN_BEGIN = "<!-- BEGIN ledger: open -->"
OPEN_END = "<!-- END ledger: open -->"
RES_BEGIN = "<!-- BEGIN ledger: resolved -->"
RES_END = "<!-- END ledger: resolved -->"
COUNTS_BEGIN = "<!-- BEGIN ledger: counts -->"
COUNTS_END = "<!-- END ledger: counts -->"

SEVERITY_TO_TIER = {
    "critical": "P0",
    "high": "P1",
    "moderate": "P2",
    "medium": "P2",
    "low": "P3",
}


def _normalize_severity(value: str | None) -> str:
    if not value:
        return "moderate"
    v = value.lower().strip()
    if v in SEVERITY_TO_TIER:
        return v
    return "moderate"


def _tier_for(sev: str) -> str:
    return SEVERITY_TO_TIER.get(sev, "P2")


def _render_entry(entry: dict[str, str | None]) -> str:
    lines = ["  -"]
    for key in (
        "advisory_id",
        "package",
        "severity",
        "reachable",
        "fix_version",
        "owner",
        "sla_tier",
        "status",
        "opened_at",
        "closed_at",
        "pr_url",
    ):
        val = entry.get(key)
        if val is None or val == "":
            continue
        lines.append(f"      {key}: {val}")
    return "\n".join(lines)


def _short_owner(obo: str | None) -> str:
    if not obo:
        return "@KooshaPari"
    obo = obo.strip()
    return obo if obo.startswith("@") else f"@{obo}"


def collect_from_cargo_audit() -> list[dict[str, str | None]]:
    try:
        out = subprocess.run(
            ["cargo", "audit", "--json"],
            capture_output=True,
            text=True,
            check=False,
            cwd=REPO_ROOT,
        )
    except FileNotFoundError:
        print("cargo-audit not installed; skipping cargo audit", file=sys.stderr)
        return []
    if out.returncode not in (0, 1):
        print(f"cargo audit returned {out.returncode}: {out.stderr[:200]}", file=sys.stderr)
        return []
    if not (out.stdout or "").strip():
        return []
    try:
        payload = json.loads(out.stdout)
    except json.JSONDecodeError:
        return []

    vulns = payload.get("vulnerabilities", {})
    entries: list[dict[str, str | None]] = []
    for name, list_or_meta in vulns.items():
        if isinstance(list_or_meta, list):
            for v in list_or_meta:
                entries.append(_cargo_to_entry(name, v))
        else:
            entries.append(_cargo_to_entry(name, list_or_meta))
    return entries


def collect_from_dependabot(token: str | None) -> list[dict[str, str | None]]:
    """Fetch open Dependabot alerts from GitHub and map them into RowEntry dicts.

    The Dependabot Alerts API schema:
        https://docs.github.com/en/rest/dependabot/alerts

    Real field shapes (per alert JSON object):
        - number: int (alert number, not the advisory)
        - ghsa_id: string (e.g. "GHSA-xxxx-yyyy-zzzz")
        - state: enum (open, fixed, dismissed, auto_dismissed)
        - severity: object { severity: "low"|"moderate"|"high"|"critical", score: float }
        - package: object { ecosystem: "cargo"|"npm"|"pip"|..., name: string }
        - dependency: object { package_url, scope, manifest_path, package_version }
        - advisory: object { ghsa_id, cve_id, summary, description, ... }
        - vulnerable_version_range: string
        - first_patched_version: object | null

    Returns: list of dicts compatible with RowEntry (advisory_id, package, severity,
             reachable, fix_version, owner, sla_tier, status, opened_at).

    Safe-by-default: returns [] on any error.
    """
    if not token:
        return []

    repo = os.environ.get("GITHUB_REPOSITORY", "KooshaPari/phenotype-tooling")
    url = f"https://api.github.com/repos/{repo}/dependabot/alerts?state=open&per_page=100"

    items: list[dict] = []
    max_pages = 5  # 5x100=500 alerts cap; current count is 100
    for _ in range(max_pages):
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
                resp_body = resp.read()
                link = resp.headers.get("Link", "")
        except Exception:  # pragma: no cover
            return []

        try:
            data = json.loads(resp_body.decode("utf-8"))
        except Exception:
            return []
        if not isinstance(data, list):
            return []
        items.extend(data)
        url = _next_link(link, url)
        if not url:
            break

    out: list[dict[str, str | None]] = []
    GHSA_RE = re.compile(r"^GHSA-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}$")

    for a in items:
        # Real schema (per https://docs.github.com/en/rest/dependabot/alerts):
        # - number                        : int alert number
        # - ghsa_id                       : NOT present at top level — comes from
        #                                   security_advisory.ghsa_id
        # - security_advisory.severity    : string ("low"|"medium"|"high"|"critical")
        # - security_vulnerability       : object with package, severity,
        #                                   vulnerable_version_range, first_patched_version
        # - dependency.package.ecosystem  : string ("rust"|"npm"|"pip")
        adv = a.get("security_advisory") or {}
        vuln = a.get("security_vulnerability") or {}

        ghsa = adv.get("ghsa_id")
        if not ghsa or not GHSA_RE.match(ghsa):
            # last-resort: skip malformed entries
            continue
        sev_raw = adv.get("severity") or vuln.get("severity")
        severity_norm = _normalize_severity(sev_raw)

        dep_pkg = (a.get("dependency") or {}).get("package") or {}
        ecosystem = (dep_pkg.get("ecosystem") or "").lower()
        # Normalize rust->cargo for ledger consistency
        if ecosystem == "rust":
            ecosystem = "cargo"
        dep_name = dep_pkg.get("name") or ""
        version = (a.get("dependency") or {}).get("package_version") or ""
        fpa = vuln.get("first_patched_version") or {}
        fix_version = fpa.get("identifier") if isinstance(fpa, dict) else None

        out.append(
            {
                "advisory_id": ghsa,
                "package": f"{ecosystem}:{dep_name}@{version}".strip("@") or f"{ecosystem}:{dep_name}",
                "severity": severity_norm,
                "reachable": "false",  # API does not expose reachability via this endpoint.
                "fix_version": fix_version or "N/A",
                "owner": _short_owner(None),
                "sla_tier": _tier_for(severity_norm),
                "status": a.get("state") or "open",
                "opened_at": (a.get("created_at") or "")[:10],
            }
        )
    return out


def _next_link(link_header: str, current_url: str) -> str | None:
    """Parse GitHub's RFC 5988 `Link` header, return next page URL or None."""
    if not link_header:
        return None
    for part in link_header.split(","):
        pieces = part.split(";")
        if len(pieces) != 2:
            continue
        if 'rel="next"' in pieces[1]:
            url = pieces[0].strip().lstrip("<").rstrip(">")
            return url
    return None


def _cargo_to_entry(name: str, v: dict) -> dict[str, str | None]:
    sev = _normalize_severity(v.get("severity") or v.get("alert", {}).get("severity"))
    fix_versions = v.get("versions", {}).get("patched") or []
    fix_version = ",".join(fix_versions) if fix_versions else "N/A"
    return {
        "advisory_id": v.get("id") or v.get("advisory", {}).get("id"),
        "package": f"{name}:{v.get('package', {}).get('version', '')}",
        "severity": sev,
        "reachable": str(bool(v.get("informational") is None)).lower(),
        "fix_version": fix_version,
        "owner": _short_owner(None),
        "sla_tier": _tier_for(sev),
        "status": "open",
        "opened_at": _dt.date.today().isoformat(),
    }


def render_ledger(ledger: Path, open_entries: list[dict[str, str | None]], resolved: list[dict[str, str | None]]) -> None:
    text = ledger.read_text(encoding="utf-8") if ledger.exists() else ""
    open_block = "\n".join(_render_entry(e) for e in open_entries) or "(none)"
    res_block = "\n".join(_render_entry(e) for e in resolved) or "(none)"

    # Open block
    if OPEN_BEGIN in text and OPEN_END in text:
        text = re.sub(
            re.escape(OPEN_BEGIN) + r".*?" + re.escape(OPEN_END),
            f"{OPEN_BEGIN}\n{open_block}\n{OPEN_END}",
            text,
            count=1,
            flags=re.DOTALL,
        )
    else:
        text += f"\n\n{OPEN_BEGIN}\n{open_block}\n{OPEN_END}"

    # Resolved block
    if RES_BEGIN in text and RES_END in text:
        text = re.sub(
            re.escape(RES_BEGIN) + r".*?" + re.escape(RES_END),
            f"{RES_BEGIN}\n{res_block}\n{RES_END}",
            text,
            count=1,
            flags=re.DOTALL,
        )
    else:
        text += f"\n\n{RES_BEGIN}\n{res_block}\n{RES_END}"

    # Counts block (live summary)
    counts_lines = [
        "| tier | open | description | SLA (Phase 3) |",
        "|---|---|---|---|",
        f"| P0 | {sum(1 for e in open_entries if e.get('sla_tier') == 'P0')} | critical severity | 7d |",
        f"| P1 | {sum(1 for e in open_entries if e.get('sla_tier') == 'P1')} | high severity | 14d |",
        f"| P2 | {sum(1 for e in open_entries if e.get('sla_tier') == 'P2')} | medium/moderate severity | 30d |",
        f"| P3 | {sum(1 for e in open_entries if e.get('sla_tier') == 'P3')} | low severity | 90d |",
        "",
        f"Total open: {len(open_entries)}",
    ]
    counts_block = "\n".join(counts_lines)
    if COUNTS_BEGIN in text and COUNTS_END in text:
        text = re.sub(
            re.escape(COUNTS_BEGIN) + r".*?" + re.escape(COUNTS_END),
            f"{COUNTS_BEGIN}\n{counts_block}\n{COUNTS_END}",
            text,
            count=1,
            flags=re.DOTALL,
        )
    else:
        text += f"\n\n{COUNTS_BEGIN}\n{counts_block}\n{COUNTS_END}"

    ledger.write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Regenerate SECURITY_DEPS_LEDGER.md")
    ap.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"), help="GitHub PAT for Dependabot API")
    args = ap.parse_args()

    open_entries = collect_from_cargo_audit()
    open_entries.extend(collect_from_dependabot(args.token))
    if not open_entries:
        # Render an empty-but-honest ledger on a clean audit so the ledger never
        # drifts; downstream consumers see "no entries" instead of stale data.
        render_ledger(LEDGER_PATH, [], [])
        print(f"ledger: {LEDGER_PATH} (no alerts)")
        return 0

    render_ledger(LEDGER_PATH, open_entries, [])
    print(f"ledger: {LEDGER_PATH} ({len(open_entries)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
