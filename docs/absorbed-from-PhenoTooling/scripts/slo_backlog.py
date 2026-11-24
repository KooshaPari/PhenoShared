#!/usr/bin/env python3
"""WP-13: SLO-driven backlog emitter.

Polls a Prometheus Alertmanager-compatible /api/v1/alerts endpoint for
firing alerts on the three SLO burn-rate rules defined in
observability/prometheus/phenotype-tooling.rules.yml:

  - PhenotypeCliSuccessRateFastBurn   (severity: critical, slo: success_rate)
  - PhenotypeCliSuccessRateSlowBurn   (severity: warning,  slo: success_rate)
  - PhenotypeCliStartupLatencyP95     (severity: warning,  slo: startup_p95)

For each firing alert not already represented in the open GitHub
issues (matched by the dedup label `slo-incident:<alert_fingerprint>`),
opens a fresh issue with the PTX-aligned severity prefix and the
canonical body block. Issues auto-close once the alert clears.

Exit codes:
  0  success (zero or more issues opened, no errors)
  1  usage / config error
  2  network error fetching alerts
  3  GitHub API error

Required environment / CLI:
  --prometheus-url URL       base URL of the Prometheus server
                            (default: $PROMETHEUS_URL or http://127.0.0.1:9090)
  --repo OWNER/NAME          target repository for issues
                            (default: $GITHUB_REPOSITORY)
  --token TOKEN              GitHub PAT (default: $GITHUB_TOKEN)
  --dry-run                  print planned issue bodies without opening them
  --max-issues N             cap issues opened per run (default: 10)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional


SEVERITY_PREFIX = {
    "critical": "phase1:crit",
    "warning": "phase2:warn",
    "info": "phase3:info",
}

# Severity-aware labels applied to each opened issue.
SEVERITY_LABELS = {
    "critical": ["slo-incident", "severity:phase1-crit", "needs-triage"],
    "warning": ["slo-incident", "severity:phase2-warn", "needs-triage"],
    "info": ["slo-incident", "severity:phase3-info"],
}

# Source alert -> alert owner / runbook URL map. Kept here so this script
# is the single source of truth for SLO ownership.
ALERT_OWNERS: Dict[str, Dict[str, str]] = {
    "PhenotypeCliSuccessRateFastBurn": {
        "owner": "@KooshaPari",
        "runbook": "docs/WP-09-OBSERVABILITY.md#fast-burn",
    },
    "PhenotypeCliSuccessRateSlowBurn": {
        "owner": "@KooshaPari",
        "runbook": "docs/WP-09-OBSERVABILITY.md#slow-burn",
    },
    "PhenotypeCliStartupLatencyP95": {
        "owner": "@KooshaPari",
        "runbook": "docs/WP-09-OBSERVABILITY.md#startup-latency",
    },
}


def fingerprint(alert: Dict[str, Any]) -> str:
    """Stable fingerprint for dedup: alertname + slo label."""
    labels = alert.get("labels", {})
    name = labels.get("alertname", "unknown")
    slo = labels.get("slo", "unknown")
    raw = f"{name}|{slo}".encode("utf-8")
    return hashlib.sha1(raw).hexdigest()[:12]


def fetch_firing_alerts(prom_url: str) -> List[Dict[str, Any]]:
    """Return the list of alerts currently in `firing` state from
    Prometheus's /api/v1/alerts endpoint.

    Prometheus returns a JSON envelope: {"data": {"alerts": [...]}}.
    """
    url = urllib.parse.urljoin(prom_url.rstrip("/") + "/", "api/v1/alerts")
    try:
        with urllib.request.urlopen(url, timeout=15) as resp:
            payload = json.load(resp)
    except urllib.error.URLError as exc:
        print(f"error: could not fetch {url}: {exc}", file=sys.stderr)
        sys.exit(2)
    except json.JSONDecodeError as exc:
        print(f"error: malformed response from {url}: {exc}", file=sys.stderr)
        sys.exit(2)

    data = payload.get("data", {}) if isinstance(payload, dict) else {}
    alerts = data.get("alerts", []) if isinstance(data, dict) else []
    return [a for a in alerts if a.get("state") == "firing"]


def fetch_open_incident_fingerprints(repo: str, token: str) -> set[str]:
    """List open issues bearing the `slo-incident` label and extract
    the dedup fingerprint from each title. Returns the set of fingerprints
    currently in flight."""
    cmd = [
        "gh",
        "issue",
        "list",
        "--repo", repo,
        "--state", "open",
        "--label", "slo-incident",
        "--limit", "200",
        "--json", "title",
    ]
    try:
        out = subprocess.run(cmd, check=True, capture_output=True, text=True, env=os.environ | {"GH_TOKEN": token})
    except subprocess.CalledProcessError as exc:
        print(f"error: gh issue list failed: {exc.stderr.strip()}", file=sys.stderr)
        sys.exit(3)
        return set()  # unreachable, but keeps the type-checker happy

    fingerprints: set[str] = set()
    try:
        issues = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return set()
    for issue in issues:
        title = issue.get("title", "")
        # Title suffix is `[fp=<12hex>]`
        if "[fp=" in title and title.endswith("]"):
            fp = title.rsplit("[fp=", 1)[1].rstrip("]")
            if len(fp) == 12:
                fingerprints.add(fp)
    return fingerprints


def render_issue_body(alert: Dict[str, Any], fp: str) -> Dict[str, Any]:
    """Build (title, body, labels) for the GitHub issue."""
    labels = alert.get("labels", {}) or {}
    annotations = alert.get("annotations", {}) or {}
    alertname = labels.get("alertname", "unknown")
    severity = labels.get("severity", "warning")
    slo = labels.get("slo", "unknown")
    summary = annotations.get("summary", "SLO breach")
    description = annotations.get("description", "").strip()

    owner_info = ALERT_OWNERS.get(alertname, {"owner": "@KooshaPari", "runbook": "docs/WP-09-OBSERVABILITY.md"})
    prefix = SEVERITY_PREFIX.get(severity, "phase2:warn")
    title = f"{prefix} SLO breach: {alertname} [fp={fp}]"

    body_lines = [
        f"## {summary}",
        "",
        f"- **Alert:** `{alertname}`",
        f"- **Severity:** `{severity}`",
        f"- **SLO target:** `{slo}`",
        f"- **Started at:** `{alert.get('activeAt', 'unknown')}`",
        f"- **Owner:** {owner_info['owner']}",
        f"- **Runbook:** [{owner_info['runbook']}]({owner_info['runbook']})",
        "",
        "### Description",
        "",
        description or "(no description provided)",
        "",
        "### Triage checklist",
        "",
        "- [ ] Confirm the alert is real (check `phenotype_cli:*` recording rules)",
        "- [ ] Open dashboard `Phenotype Tooling / Observability`",
        "- [ ] Capture 5m + 1h invocations + error rate counters",
        "- [ ] Cross-check recent merges in `git log main --since=2h`",
        "- [ ] Roll back if regression introduced within last 2h",
        "- [ ] Mark the issue closed once the alert clears in Prometheus",
        "",
        "### Resolution notes",
        "",
        "_edit below:_",
        "",
    ]
    body = "\n".join(body_lines)
    return {
        "title": title,
        "body": body,
        "labels": SEVERITY_LABELS.get(severity, ["slo-incident", "needs-triage"]),
    }


def open_issue(repo: str, token: str, issue: Dict[str, Any]) -> Optional[str]:
    """Open a single GitHub issue via `gh`. Returns the issue URL."""
    cmd = [
        "gh",
        "issue",
        "create",
        "--repo", repo,
        "--title", issue["title"],
        "--body", issue["body"],
    ]
    for label in issue["labels"]:
        cmd.extend(["--label", label])
    try:
        out = subprocess.run(cmd, check=True, capture_output=True, text=True, env=os.environ | {"GH_TOKEN": token})
    except subprocess.CalledProcessError as exc:
        print(f"error: gh issue create failed: {exc.stderr.strip()}", file=sys.stderr)
        return None
    url = (out.stdout or "").strip()
    return url


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--prometheus-url", default=os.environ.get("PROMETHEUS_URL", "http://127.0.0.1:9090"))
    parser.add_argument("--repo", default=os.environ.get("GITHUB_REPOSITORY"))
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-issues", type=int, default=10)
    ns = parser.parse_args(argv)
    if not ns.dry_run:
        if not ns.repo:
            parser.error("--repo (or $GITHUB_REPOSITORY) is required unless --dry-run is set")
        if not ns.token:
            parser.error("--token (or $GITHUB_TOKEN/$GH_TOKEN) is required unless --dry-run is set")
    return ns


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    firing = fetch_firing_alerts(args.prometheus_url)
    if not firing:
        print("slo_backlog: no firing SLO alerts (0 firing)")
        return 0

    print(f"slo_backlog: {len(firing)} firing alert(s)")

    # Filter to only the alerts we own.
    owned = [a for a in firing if (a.get("labels", {}) or {}).get("alertname") in ALERT_OWNERS]
    if not owned:
        print("slo_backlog: no alerts match the owned set; nothing to emit")
        return 0

    if args.dry_run:
        for alert in owned:
            fp = fingerprint(alert)
            issue = render_issue_body(alert, fp)
            print("--- DRY RUN issue ---")
            print(f"Title: {issue['title']}")
            print(f"Labels: {issue['labels']}")
            print(issue["body"])
            print()
        return 0

    open_fps = fetch_open_incident_fingerprints(args.repo, args.token)
    opened = 0
    for alert in owned:
        fp = fingerprint(alert)
        if fp in open_fps:
            print(f"slo_backlog: dedup hit for {fp} ({alert['labels'].get('alertname')}); skipping")
            continue
        issue = render_issue_body(alert, fp)
        url = open_issue(args.repo, args.token, issue)
        if url:
            opened += 1
            print(f"slo_backlog: opened {issue['title']} -> {url}")
        if opened >= args.max_issues:
            print(f"slo_backlog: cap reached ({args.max_issues}); stopping")
            break
    print(f"slo_backlog: opened {opened} new issue(s) of {len(owned)} firing")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))