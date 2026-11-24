#!/usr/bin/env python3
"""
Legacy Tooling Anti-Pattern Scanner
===================================

Self-contained scanner for the AppGen repository. Walks the repo, applies
the policy in `tools/legacy-enforcement/policy/rules.yaml`, and emits
JSON + Markdown reports.

Usage
-----
    python3 tools/legacy-enforcement/scanner/legacy_tooling_scanner.py \\
        --repo-root . \\
        --policy tools/legacy-enforcement/policy/rules.yaml \\
        --output-json legacy_tooling_report.json \\
        --output-md legacy_tooling_report.md \\
        [--report-only]

Exit codes
----------
    0  No critical or high findings (or `--report-only` is set).
    1  Critical or high findings present.
    2  Operational error (bad args, missing policy, unreadable file).

Design notes
------------
* Self-contained: depends only on the Python 3.10+ stdlib + PyYAML (which
  is preinstalled on all GitHub-hosted runners and can be installed in
  local dev via `pip install pyyaml`).
* Path normalization: POSIX-style for report `file` fields so output is
  portable across OSes and stable across runs.
* Findings are sorted by (severity_rank, file, line, rule_id) for
  deterministic output.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml  # PyYAML
except ImportError:  # pragma: no cover - surfaces a clean error in CI logs.
    sys.stderr.write(
        "error: PyYAML is required. Install with `pip install pyyaml`.\n"
    )
    raise

# ─── Severity ordering (lower number = more severe) ────────────────────────────
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}

# ─── Directories the scanner always skips ──────────────────────────────────────
DEFAULT_SKIP_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "out",
    ".next",
    ".cache",
    "coverage",
    "__pycache__",
    ".venv",
    "venv",
    "target",
    ".bun",
}

# ─── Binary / oversized file extensions we never scan ─────────────────────────
BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
    ".mp3", ".mp4", ".mov", ".wav", ".ogg", ".flac",
    ".ttf", ".otf", ".woff", ".woff2", ".eot",
    ".pyc", ".class", ".o", ".so", ".dll", ".dylib", ".exe",
}


@dataclass
class Finding:
    rule_id: str
    severity: str
    description: str
    file: str
    line: int
    match: str

    def to_dict(self) -> dict:
        d = asdict(self)
        # Trim long matches for readability.
        if len(d["match"]) > 200:
            d["match"] = d["match"][:197] + "..."
        return d


@dataclass
class ScanTotals:
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0

    def add(self, severity: str) -> None:
        sev = severity.lower()
        if sev in SEVERITY_RANK:
            setattr(self, sev, getattr(self, sev) + 1)

    def to_dict(self) -> dict:
        return {
            "critical": self.critical,
            "high": self.high,
            "medium": self.medium,
            "low": self.low,
        }

    @property
    def blocking(self) -> int:
        return self.critical + self.high


@dataclass
class ScanResult:
    policy_path: str
    repo_root: str
    files_scanned: int = 0
    findings: list[Finding] = field(default_factory=list)
    totals: ScanTotals = field(default_factory=ScanTotals)
    skipped_files: list[str] = field(default_factory=list)


# ─── Policy loader ─────────────────────────────────────────────────────────────
# We rely on PyYAML's safe loader. The policy is a small, hand-written file,
# so `safe_load` is more than sufficient and gives us the full feature set
# (block scalars, anchors, multiline strings) without us reinventing it.

class _PolicyLoader(yaml.SafeLoader):
    """SafeLoader subclass placeholder.

    We use ``SafeLoader`` directly which already refuses to construct
    arbitrary Python objects, so no extra constructor overrides are needed.
    Kept as a named subclass to make the intent explicit and to provide a
    single hook for future tightening (e.g. forbidding specific tags).
    """


def load_policy(path: Path) -> dict[str, Any]:
    """Parse the policy YAML file and return it as a nested dict."""
    if not path.exists():
        raise FileNotFoundError(f"Policy file not found: {path}")
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.load(fh, Loader=_PolicyLoader)
    if not isinstance(data, dict):
        raise ValueError(
            f"Policy root must be a mapping, got {type(data).__name__}"
        )
    return data


# ─── File discovery ────────────────────────────────────────────────────────────

def iter_files(repo_root: Path, skip_dirs: set[str]) -> Iterable[Path]:
    """Yield files under repo_root, skipping noisy directories."""
    for dirpath, dirnames, filenames in os.walk(repo_root):
        # In-place mutation prunes the walk.
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for name in filenames:
            yield Path(dirpath) / name


def matches_glob(rel_path: str, glob: str) -> bool:
    """Match `rel_path` against a glob (forward-slash normalized)."""
    rel = rel_path.replace(os.sep, "/")
    # fnmatch doesn't handle `**` recursively; emulate with a translation.
    # We support the patterns we actually use in rules.yaml.
    if glob.startswith("**/"):
        suffix = glob[3:]
        if "/" not in suffix:
            return fnmatch.fnmatch(rel, suffix) or fnmatch.fnmatch(rel, f"*/{suffix}")
        # Multi-segment `**` glob.
        regex = fnmatch.translate(glob)
        return re.match(regex, rel) is not None
    return fnmatch.fnmatch(rel, glob) or fnmatch.fnmatch(rel, f"**/{glob}")


def read_text(path: Path) -> str | None:
    """Read a file as text, returning None for binary or unreadable files."""
    suffix = path.suffix.lower()
    if suffix in BINARY_EXTENSIONS:
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    # Heuristic binary detection: NUL byte in first 8 KiB.
    if b"\x00" in data[:8192]:
        return None
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = data.decode("latin-1")
        except Exception:
            return None
    # Normalize CRLF / CR line endings to LF so regex `$` and line
    # accounting work the same on Windows-checked-out files.
    return text.replace("\r\n", "\n").replace("\r", "\n")


# ─── Rule application ──────────────────────────────────────────────────────────

def find_forbid_matches(text: str, patterns: list[str]) -> Iterable[tuple[int, str]]:
    for pat in patterns:
        try:
            regex = re.compile(pat, re.MULTILINE)
        except re.error as e:
            print(f"warning: invalid forbid regex {pat!r}: {e}", file=sys.stderr)
            continue
        for m in regex.finditer(text):
            line = text.count("\n", 0, m.start()) + 1
            yield line, m.group(0)


def apply_rule(
    rule: dict,
    files: list[tuple[Path, str, str]],
) -> list[Finding]:
    """Return findings produced by a single rule against a list of files.

    `files` is a list of (absolute_path, relative_posix_path, text) tuples.
    """
    rid = rule.get("id", "<unknown>")
    severity = rule.get("severity", "low")
    description = rule.get("description", "").strip()
    globs = rule.get("globs", []) or []
    excludes = rule.get("exclude", []) or []
    forbids = rule.get("forbid", []) or []
    requires = rule.get("require", []) or []

    findings: list[Finding] = []

    for abs_path, rel_path, text in files:
        if globs and not any(matches_glob(rel_path, g) for g in globs):
            continue
        if excludes and any(matches_glob(rel_path, g) for g in excludes):
            continue

        if forbids:
            for line, match in find_forbid_matches(text, forbids):
                findings.append(
                    Finding(
                        rule_id=rid,
                        severity=severity,
                        description=description,
                        file=rel_path,
                        line=line,
                        match=match,
                    )
                )

        if requires:
            present = any(
                re.search(pat, text, re.MULTILINE) is not None for pat in requires
            )
            if not present:
                findings.append(
                    Finding(
                        rule_id=rid,
                        severity=severity,
                        description=description + " [requirement missing]",
                        file=rel_path,
                        line=1,
                        match="<no matching line found>",
                    )
                )

    return findings


# ─── Top-level orchestration ───────────────────────────────────────────────────

def scan(repo_root: Path, policy: dict) -> ScanResult:
    skip_dirs = set(DEFAULT_SKIP_DIRS)
    result = ScanResult(
        policy_path=str(policy.get("_path", "")),
        repo_root=str(repo_root),
    )

    # First pass: collect candidate files.
    files: list[tuple[Path, str, str]] = []
    for abs_path in iter_files(repo_root, skip_dirs):
        rel_path = abs_path.relative_to(repo_root).as_posix()
        text = read_text(abs_path)
        if text is None:
            result.skipped_files.append(rel_path)
            continue
        files.append((abs_path, rel_path, text))
        result.files_scanned += 1

    rules = policy.get("rules", []) or []
    for rule in rules:
        if not isinstance(rule, dict):
            continue
        for finding in apply_rule(rule, files):
            result.findings.append(finding)
            result.totals.add(finding.severity)

    result.findings.sort(
        key=lambda f: (
            SEVERITY_RANK.get(f.severity, 99),
            f.file,
            f.line,
            f.rule_id,
        )
    )
    return result


def write_json_report(result: ScanResult, out_path: Path) -> None:
    payload = {
        "schema_version": 1,
        "policy_path": result.policy_path,
        "repo_root": result.repo_root,
        "files_scanned": result.files_scanned,
        "skipped_files": result.skipped_files,
        "totals": result.totals.to_dict(),
        "findings": [f.to_dict() for f in result.findings],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def write_markdown_report(result: ScanResult, out_path: Path) -> None:
    totals = result.totals
    lines: list[str] = []
    lines.append("# Legacy Tooling Anti-Pattern Scan Report")
    lines.append("")
    lines.append(f"- Repository: `{result.repo_root}`")
    lines.append(f"- Policy: `{result.policy_path}`")
    lines.append(f"- Files scanned: **{result.files_scanned}**")
    if result.skipped_files:
        lines.append(f"- Skipped (binary/unreadable): {len(result.skipped_files)}")
    lines.append("")

    lines.append("## Totals")
    lines.append("")
    lines.append("| Severity | Count |")
    lines.append("|----------|-------|")
    lines.append(f"| Critical | {totals.critical} |")
    lines.append(f"| High | {totals.high} |")
    lines.append(f"| Medium | {totals.medium} |")
    lines.append(f"| Low | {totals.low} |")
    lines.append("")

    if not result.findings:
        lines.append("## Findings")
        lines.append("")
        lines.append("_No findings._")
        lines.append("")
    else:
        lines.append("## Findings")
        lines.append("")
        lines.append("| Severity | Rule | File | Line | Description |")
        lines.append("|----------|------|------|------|-------------|")
        for f in result.findings:
            desc = f.description.replace("|", "\\|")
            lines.append(
                f"| {f.severity.upper()} | `{f.rule_id}` | `{f.file}` | {f.line} | {desc} |"
            )
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")


# ─── CLI ───────────────────────────────────────────────────────────────────────

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Scan a repo for legacy-tooling anti-patterns."
    )
    parser.add_argument("--repo-root", required=True, help="Path to scan.")
    parser.add_argument("--policy", required=True, help="Path to rules.yaml.")
    parser.add_argument("--output-json", required=True, help="JSON report path.")
    parser.add_argument("--output-md", required=True, help="Markdown report path.")
    parser.add_argument(
        "--report-only",
        action="store_true",
        help="Always exit 0 (WARN-mode advisory).",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    policy_path = Path(args.policy).resolve()

    if not repo_root.is_dir():
        print(f"error: repo-root not a directory: {repo_root}", file=sys.stderr)
        return 2

    try:
        policy = load_policy(policy_path)
    except (FileNotFoundError, ValueError) as e:
        print(f"error: failed to load policy: {e}", file=sys.stderr)
        return 2

    policy["_path"] = str(policy_path)
    result = scan(repo_root, policy)
    write_json_report(result, Path(args.output_json))
    write_markdown_report(result, Path(args.output_md))

    summary = (
        f"scanned={result.files_scanned} "
        f"critical={result.totals.critical} "
        f"high={result.totals.high} "
        f"medium={result.totals.medium} "
        f"low={result.totals.low}"
    )
    if args.report_only:
        print(f"legacy-tooling-scanner (WARN): {summary}")
        return 0
    if result.totals.blocking > 0:
        print(f"legacy-tooling-scanner: FAIL ({summary})", file=sys.stderr)
        return 1
    print(f"legacy-tooling-scanner: OK ({summary})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
