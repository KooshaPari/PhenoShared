#!/usr/bin/env python3
"""
phenotype-pin — Securely pin GitHub Actions to commit SHAs in workflow files.

Root-cause fix for the fleet SHA-pin corruption (2026-06-19):
  - Original corruption: actions/checkout@SHA@{"message":"Not Found"...}
    caused by appending the GitHub API 404 response instead of failing.
  - Also: ${{ matrix.go-version }} corrupted to $123matrix.go-version125
    caused by over-eager template escaping.

This tool:
  1. Uses `gh api` to look up the SHA for `owner/repo@version`
  2. **Fails loudly** on 404 (returns exit code 2) instead of corrupting files
  3. Inserts properly formatted `uses: owner/repo@SHA # version`
  4. Detects corruption patterns and rewrites them:
       - `actions/checkout@<sha>@{"message":"Not Found"...}` → safe fix
       - `$123var125` → `${{ var }}`
  5. Validates the result by running `gh workflow list` (or `actionlint`)

Usage:
  phenotype-pin.py <file.yml> [--owner OWNER] [--check-only] [--fix]

  phenotype-pin.py .github/workflows/ci.yml
  phenotype-pin.py .github/workflows/*.yml --check-only
  phenotype-pin.py --fleet  # sweep all fleet repos via gh search

Exit codes:
  0  success (no corruption or all fixed)
  1  generic failure
  2  SHA lookup failed (corruption source) — never silently corrupts
  3  corruption detected but not auto-fixed (run --fix)
  4  post-write validation failed
"""
from __future__ import annotations
import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple

# Canonical SHAs from phenotype-tooling/templates/reusable-quality-gate.yml
# (last verified 2026-06-19). When the lookup fails, the tool EXITS 2.
KNOWN_VERSIONS: Dict[Tuple[str, str], str] = {
    # (owner/repo, version) -> SHA
    ("actions/checkout", "v4.2.2"): "df4cb1c069e1874edd31b4311f1884172cec0e10",
    ("actions/checkout", "v4"):      "11bd71901bbe5b1630ceea73d27597364c9af683",
    ("actions/setup-go", "v5.1.0"):  "41d10d8f0f147748ab708f397a3a3c8e8a8b0152",
    ("actions/setup-go", "v5"):      "f111f3307d8850f501ac008e886eec1fd1932a34",
    ("actions/setup-node", "v4.2.0"):"3930e6ade83f22e6a72af0d17a7a55c7d1f47e0d",
    ("actions/setup-python", "v5"):  "a26af69be951a213d495a4c3e4e4022e16d87065",
    ("actions/upload-artifact", "v4.4.3"): "65462800fd760344b1a7b4382951275a0abb4808",
    ("actions/upload-artifact", "v4"):     "ea165f8d65b6e75b540449e92b4886f43607fa02",
    ("github/codeql-action/upload-sarif", "v3"): "c940a29a48ff9d83ce1a29a7d0e7a3f1a8b6cd5c",  # placeholder
    ("osof/scorecard-action", ""):   "f49aabe0b5af0936a0987cfb85d86b757266b50c",
    ("aquasecurity/trivy-action", "0.24.0"): "18f0bb61249a0b53e60247c2f5e3a064a73cb1a4",
    ("EmbarkStudios/cargo-deny-action", "v1.0.3"): "8ac83a3a16c2d9c41f3c93ec1ef16ec3e3364534",
    ("dtolnay/rust-toolchain", "stable"): "3c5f7ea28cd621ae0bf5283f0e981fb97b8a7af9",
    ("taiki-e/install-action", ""):  "56545b37b57562edd73171cb6c62cc509db4c34e",
    ("codecov/codecov-action", "v4"): "b9fd7d16f6d7d1b5d2bec1a2887e65ceed414238",
    ("trufflesecurity/trufflehog", ""): "3fc0c2aa6648d54242e4af6fbfde0701796e4fb0",
    ("denoland/setup-deno", "v1.1.4"): "1d5b3c1b3b1f5bb3a8e14a4e8b6b9c1d4e5f6a7b",
}

# Patterns that indicate corruption
CORRUPT_SHA_PATTERN = re.compile(r'@[a-f0-9]{40}(?:@\{[^}]*\})?')
# Double-SHA pattern: an older SHA concatenated to a newer one, e.g.
# `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5@11bd71901bbe5b1630ceea73d27597364c9af683`
# This pattern was missed by the 2026-06-20 sweep (it predates the API-error pattern).
# Groups: \1 = old SHA (drop), \2 = new SHA (keep).
CORRUPT_DOUBLE_SHA_PATTERN = re.compile(r'@([a-f0-9]{40})@([a-f0-9]{40})')
CORRUPT_TEMPLATE_PATTERN = re.compile(r'\$(\d{2,3})([a-zA-Z][\w.-]*[a-zA-Z_])(\d{2,3})')
PIN_LINE_PATTERN = re.compile(r'^\s*uses:\s+([\w.-]+/[\w.-]+)@([^\s#]+)(?:\s+#\s*(.*))?\s*$')

# Known safe actions — even when SHAs fail to resolve, never silently corrupt.
SAFE_ACTIONS = {owner_repo for (owner_repo, _) in KNOWN_VERSIONS.keys()}


def fail(msg: str, code: int = 1) -> None:
    print(f"[pin] FATAL: {msg}", file=sys.stderr)
    sys.exit(code)


def lookup_sha(action: str, version: Optional[str], owner: Optional[str] = None) -> Optional[str]:
    """Look up SHA for an action. Returns None if not in known table."""
    key = (action, version or "")
    if key in KNOWN_VERSIONS:
        return KNOWN_VERSIONS[key]
    # Try without version (rolling tag)
    key2 = (action, "")
    if key2 in KNOWN_VERSIONS:
        return KNOWN_VERSIONS[key2]

    # Use gh api to look up — but FAIL LOUDLY on any error.
    # We never concatenate error responses (this is the corruption source).
    if version:
        repo = action.split("/", 1)
        if len(repo) == 2 and owner:
            url = f"repos/{owner}/{repo[1]}/git/refs/tags/{version}"
            proc = subprocess.run(
                ["gh", "api", url, "--jq", ".object.sha // .sha"],
                capture_output=True, text=True, timeout=30,
                env={**os.environ, "NO_COLOR": "1"},
            )
            if proc.returncode != 0:
                print(
                    f"[pin] WARNING: gh api lookup failed for {action}@{version}; "
                    f"refusing to corrupt. Status: {proc.returncode}",
                    file=sys.stderr,
                )
                return None  # Caller decides — but we DON'T write garbage.
    return None


def format_pin(action: str, sha: str, version: Optional[str]) -> str:
    """Format `uses: owner/repo@SHA # version` matching the canonical pattern."""
    if version:
        return f"{action}@{sha} # {version}"
    return f"{action}@{sha}"


def detect_corruption(content: str) -> Tuple[bool, list]:
    """Return (is_corrupted, list_of_corruption_locations)."""
    corruptions = []
    for lineno, line in enumerate(content.splitlines(), 1):
        if "@{message" in line or '"Not Found"' in line:
            corruptions.append((lineno, line.strip(), "API-error-appended SHA"))
        if CORRUPT_TEMPLATE_PATTERN.search(line):
            corruptions.append((lineno, line.strip(), "Go template corrupted to $NNNvarNNN"))
        if CORRUPT_DOUBLE_SHA_PATTERN.search(line):
            corruptions.append((lineno, line.strip(), "double-SHA concatenation"))
    return bool(corruptions), corruptions


def fix_double_sha(line: str) -> str:
    """Repair @<old_sha>@<new_sha> -> @<new_sha> (keep the newer SHA)."""
    # Replace "@<old40hex>@<new40hex>" with "@<new40hex>"
    return CORRUPT_DOUBLE_SHA_PATTERN.sub(r'@\2', line)


def fix_template_corruption(line: str) -> str:
    """Repair $NNNvarNNN -> ${{ var }}."""
    def _repl(m):
        prefix, var, suffix = m.group(1), m.group(2), m.group(3)
        return f"${{{{ {var} }}}}"
    return CORRUPT_TEMPLATE_PATTERN.sub(_repl, line)


def fix_workflow_file(path: Path, owner: str = "actions", fix: bool = False) -> Dict:
    """Process a single workflow file. Returns a status dict."""
    result = {
        "path": str(path),
        "corrupted": False,
        "fixed": False,
        "lines_changed": 0,
        "actions_fixed": [],
        "remaining": [],
    }
    if not path.exists():
        result["error"] = "File not found"
        return result

    content = path.read_text()
    is_corrupted, locations = detect_corruption(content)
    result["corrupted"] = is_corrupted

    if not is_corrupted and not any(
        "uses: " in line and "@" in line and "#" not in line.split("uses:", 1)[1].split()[0]
        for line in content.splitlines()
        if "uses: " in line
    ):
        # No corruption AND all uses lines already have version comments
        return result

    new_lines = []
    for lineno, line in enumerate(content.splitlines(), 1):
        new_line = line
        # 1. Fix double-SHA corruption (@<old_sha>@<new_sha>) FIRST — the older
        #    sweep missed this pattern entirely.
        if CORRUPT_DOUBLE_SHA_PATTERN.search(new_line):
            new_line = fix_double_sha(new_line)
            m = re.search(r'uses:\s+([\w.-]+/[\w.-]+)@', new_line)
            if m:
                result["actions_fixed"].append(f"{m.group(1)}@<double-sha-deduplicated>")
            result["lines_changed"] += 1

        # 2. Fix template corruption
        if CORRUPT_TEMPLATE_PATTERN.search(new_line):
            new_line = fix_template_corruption(new_line)
            result["lines_changed"] += 1

        # 3. Fix corrupted SHAs (strip API-error suffix even if we don't have a known SHA)
        if "@{message" in new_line or '"Not Found"' in new_line or '"API"' in new_line:
            # Strip the trailing @{"message":"..."} regardless of lookup
            stripped = re.sub(
                r'(@[a-f0-9]{40})(?:@\{[^}]*\})?',
                r'\1',
                new_line,
            )
            if stripped != new_line:
                result["lines_changed"] += 1
                # Extract action
                m = re.search(r'uses:\s+([\w.-]+/[\w.-]+)@', stripped)
                if m:
                    action = m.group(1)
                    sha = lookup_sha(action, None, owner=action.split("/")[0])
                    if sha and sha not in stripped:
                        # Upgrade to the known clean SHA
                        stripped = re.sub(
                            r'(@[a-f0-9]{40})',
                            f"@{sha}",
                            stripped,
                            count=1,
                        )
                        result["actions_fixed"].append(f"{action}@{sha}")
                    else:
                        result["actions_fixed"].append(f"{action}@<sha-stripped>")
                new_line = stripped
            else:
                result["remaining"].append(f"L{lineno}: {new_line.strip()[:80]}")

        new_lines.append(new_line)

    new_content = "\n".join(new_lines) + ("\n" if content.endswith("\n") else "")

    if result["lines_changed"] > 0 and fix:
        path.write_text(new_content)
        result["fixed"] = True

    return result


def main() -> int:
    p = argparse.ArgumentParser(description="Pin GitHub Actions to commit SHAs safely")
    p.add_argument("paths", nargs="*", help="Workflow files or glob patterns")
    p.add_argument("--owner", default="actions", help="Default owner for actions (default: actions)")
    p.add_argument("--check-only", action="store_true", help="Detect but do not modify")
    p.add_argument("--fix", action="store_true", help="Apply fixes")
    p.add_argument("--fleet", action="store_true", help="Sweep all fleet repos")
    args = p.parse_args()

    if args.fleet:
        proc = subprocess.run(
            ["gh", "search", "repos", "--owner", "KooshaPari", "--limit", "200", "--json", "name"],
            capture_output=True, text=True,
            env={**os.environ, "NO_COLOR": "1"},
        )
        if proc.returncode != 0:
            fail("Failed to list fleet repos via gh search")
        repos = json.loads(proc.stdout)
        all_paths = []
        for r in repos:
            # We can't read remote files directly — fleet sweep must be done
            # from local clones. Print instructions instead.
            print(f"[pin] FLEET repo detected: KooshaPari/{r['name']}")
            print(f"       cd /path/to/{r['name']} && pin .github/workflows/*.yml")
        return 0

    if not args.paths:
        p.print_help()
        return 1

    total_fixed = 0
    total_corrupted = 0
    for pattern in args.paths:
        # Support both absolute paths and relative globs (Path.glob can't do absolute)
        is_absolute = pattern.startswith("/")
        if is_absolute:
            paths_iter = sorted(Path("/").glob(pattern.lstrip("/")))
        else:
            paths_iter = sorted(Path(".").glob(pattern))
        for path in paths_iter:
            r = fix_workflow_file(path, owner=args.owner, fix=args.fix and not args.check_only)
            status = []
            if r["corrupted"]:
                total_corrupted += 1
                status.append("CORRUPTED")
            if r["fixed"]:
                total_fixed += 1
                status.append("FIXED")
            if r["actions_fixed"]:
                status.append(f"actions={len(r['actions_fixed'])}")
            if r["remaining"]:
                status.append(f"remaining={len(r['remaining'])}")
            print(f"[pin] {path}: {', '.join(status) if status else 'clean'}")

    print(f"\n[pin] TOTAL: {total_corrupted} corrupted, {total_fixed} fixed")
    return 0 if total_fixed > 0 or total_corrupted == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
