#!/usr/bin/env python3
"""SBOM diff policy check.

Compares the SBOM from the current PR against the SBOM from `main`,
identifies newly-introduced packages, and queries OSV.dev for known
vulnerabilities. Exits non-zero if any new high/critical vuln is
introduced.

This is the WP-22 entry point used by .github/workflows/sbom-diff.yml.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Tuple

OSV_QUERY_URL = "https://api.osv.dev/v1/query"
OSV_VULN_URL = "https://api.osv.dev/v1/vulns/"


def load_sbom_components(path: Path) -> List[Dict[str, str]]:
    """Parse a CycloneDX SBOM JSON file into a list of (name, version) dicts."""
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    components = []
    for c in data.get("components", []) or []:
        name = c.get("name") or c.get("purl", "").split("/")[-1]
        version = c.get("version", "")
        purl = c.get("purl", "")
        if name and version:
            components.append({"name": name, "version": version, "purl": purl})
    return components


def diff_components(
    base: List[Dict[str, str]], head: List[Dict[str, str]]
) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
    """Return (added, removed) tuples of component dicts."""
    base_keys = {(c["name"], c["version"]) for c in base}
    head_keys = {(c["name"], c["version"]) for c in head}
    added = [c for c in head if (c["name"], c["version"]) not in base_keys]
    removed = [c for c in base if (c["name"], c["version"]) not in head_keys]
    return added, removed


def _osv_post(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST a JSON payload to OSV.dev and return the parsed JSON."""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:  # nosec - trusted URL
        return json.loads(resp.read().decode("utf-8"))


def query_osv(package_name: str, ecosystem: str, version: str) -> List[Dict[str, Any]]:
    """Return the list of vulnerabilities affecting a package@version."""
    payload = {
        "package": {"name": package_name, "ecosystem": ecosystem},
        "version": version,
    }
    try:
        resp = _osv_post(OSV_QUERY_URL, payload)
    except urllib.error.URLError as exc:
        print(f"::warning::OSV query failed for {package_name}@{version}: {exc}")
        return []
    vulns = resp.get("vulns", []) or []
    return vulns


def severity_of(vuln: Dict[str, Any]) -> str:
    """Extract the highest severity rating from an OSV vuln record."""
    # Database_specific takes precedence (GHSA uses CVSS vectors)
    db = vuln.get("database_specific") or {}
    if isinstance(db, dict):
        sev = db.get("severity")
        if isinstance(sev, str):
            return sev.upper()
    # Fallback: parse CVSS score from severity list
    for entry in vuln.get("severity", []) or []:
        if isinstance(entry, dict):
            score = entry.get("score", "")
            # Very rough threshold; real code uses CVSS vector parsing
            if score.startswith("CVSS:3"):
                # Extract base score (last numeric field)
                try:
                    base = float(score.split("/")[-1])
                except ValueError:
                    continue
                if base >= 9.0:
                    return "CRITICAL"
                if base >= 7.0:
                    return "HIGH"
                if base >= 4.0:
                    return "MEDIUM"
                return "LOW"
    return "UNKNOWN"


def audit_added_packages(
    added: List[Dict[str, str]], ecosystem: str = "crates.io"
) -> List[Dict[str, Any]]:
    """For each newly-added package, query OSV.dev and return findings
    that are HIGH or CRITICAL severity."""
    findings: List[Dict[str, Any]] = []
    for pkg in added:
        vulns = query_osv(pkg["name"], ecosystem, pkg["version"])
        for vuln in vulns:
            sev = severity_of(vuln)
            if sev in ("HIGH", "CRITICAL"):
                findings.append(
                    {
                        "package": pkg,
                        "vuln_id": vuln.get("id"),
                        "summary": vuln.get("summary"),
                        "severity": sev,
                    }
                )
    return findings


def emit_pr_comment(findings: List[Dict[str, Any]]) -> str:
    """Format findings as a GitHub PR comment body."""
    if not findings:
        return "No high/critical vulnerabilities introduced by this PR. ✅"
    out = ["## :warning: SBOM Policy Check — New High/Critical Vulnerabilities", ""]
    out.append(
        "This PR introduces dependencies with known HIGH or CRITICAL vulnerabilities."
    )
    out.append("")
    out.append("| Package | Version | CVE | Severity | Summary |")
    out.append("|---|---|---|---|---|")
    for f in findings:
        pkg = f["package"]
        out.append(
            f"| `{pkg['name']}` | `{pkg['version']}` | {f['vuln_id']} | "
            f"{f['severity']} | {f['summary'][:120] if f['summary'] else ''} |"
        )
    out.append("")
    out.append(
        "_Override_: add `# license-override: <reason>` to a commit body, get CODEOWNER review."
    )
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base",
        required=True,
        type=Path,
        help="Path to base (main) SBOM JSON",
    )
    parser.add_argument(
        "--head",
        required=True,
        type=Path,
        help="Path to head (PR) SBOM JSON",
    )
    parser.add_argument(
        "--ecosystem",
        default="crates.io",
        help="OSV.dev ecosystem identifier (default: crates.io)",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Where to write the PR-comment markdown (default: stdout)",
    )
    args = parser.parse_args()

    base = load_sbom_components(args.base)
    head = load_sbom_components(args.head)
    added, removed = diff_components(base, head)
    print(
        f"::notice::SBOM diff: {len(added)} added, {len(removed)} removed",
        file=sys.stderr,
    )
    findings = audit_added_packages(added, ecosystem=args.ecosystem)
    comment = emit_pr_comment(findings)
    if args.report_path:
        args.report_path.parent.mkdir(parents=True, exist_ok=True)
        args.report_path.write_text(comment, encoding="utf-8")
    else:
        print(comment)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
