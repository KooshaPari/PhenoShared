#!/usr/bin/env python3
"""Pre-commit validator for WORKLOG.md files (ADR-015 / ADR-025).

Validates that WORKLOG.md files conform to the canonical v2.1 schema
(11-col lowercase with `device:` column at position 9). Accepts the
following legacy formats with a WARNING before 2026-06-22 and FAILs
on them after the cutover date:

  - v2.0 (10-col lowercase) — missing the `device` column
  - v1 (6-col capital) — `Date | Task ID | Layer | Action | Files | Notes`
  - v1+device (7-col capital + device) — pre-v2.1 hybrid used in
    pheno-config, pheno-context, pheno-otel, pheno-port-adapter

For NEW WORKLOG.md files (the file didn't exist before this commit),
the cutover is strict: only v2.1 is accepted at any time.

Exit codes:
  0 — file is canonical v2.1 (or not a worklog file)
  1 — file is legacy format; in WARN mode (pre-2026-06-22) this is
      reported but does not block the commit; in FAIL mode (post-cutover)
      it blocks the commit.

Usage:
    python3 validate_worklog.py <path>           # check one file
    python3 validate_worklog.py --strict <path>  # fail on legacy
    python3 validate_worklog.py --warn-only      # never fail
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add pheno-worklog-schema/src to path so we can import the validators.
_PWS = Path(__file__).resolve().parent / "src"
if str(_PWS) not in sys.path:
    sys.path.insert(0, str(_PWS))

from pheno_worklog_schema.schema import (  # noqa: E402
    CANONICAL_DEVICES,
    EXPECTED_COLUMNS,
    EXPECTED_COLUMNS_V20,
)
from migrate_v2_to_v2_1 import (  # noqa: E402
    detect_format,
    is_v21,
)

# 2026-06-22 is the ADR-025 v2.1 deprecation cutover date. After this
# date, legacy v2.0/v1/v1+device WORKLOG.md files are FAILs, not warns.
CUTOVER_DATE = "2026-06-22"

# Per ADR-023 / pheno-worklog-schema/schema.py, the device column
# accepts: macbook, heavy-runner, subagent, ci, "" (empty for legacy).
VALID_DEVICES = set(CANONICAL_DEVICES)


def _is_new_file(path: Path) -> bool:
    """True if the file is not tracked by git (i.e. it's new in this commit).

    We approximate "new file" by walking up from the file's location to
    find the nearest git toplevel, then running `git ls-files` from there.
    If we can't determine git state (e.g. running outside any git repo),
    we treat the file as existing (legacy) to avoid false positives.
    """
    try:
        import subprocess
        # Find the git toplevel by walking up from the file's directory.
        cur = path.resolve().parent if path.is_file() else path.resolve()
        git_toplevel = None
        for candidate in [cur, *cur.parents]:
            if (candidate / ".git").exists():
                git_toplevel = candidate
                break
        if git_toplevel is None:
            return False  # not in a git repo
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", str(path.resolve())],
            capture_output=True, text=True, timeout=5,
            cwd=str(git_toplevel),
        )
        # git ls-files --error-unmatch returns 0 if file is tracked.
        return result.returncode != 0
    except Exception:
        return False  # conservative: treat as existing


def validate(path: Path, strict: bool = False, warn_only: bool = False) -> int:
    """Validate a single WORKLOG.md file. Returns 0 on OK, 1 on FAIL."""
    if not path.exists():
        return 0  # file deleted; nothing to validate
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        print(f"  WARN: {path}: not UTF-8; skipping", file=sys.stderr)
        return 0

    fmt = detect_format(text)
    if fmt == "none":
        return 0  # not a recognized worklog file
    if fmt == "v21":
        return _validate_v21(path, text, warn_only=warn_only)
    # fmt is v20, v1, or v1p — legacy format
    return _validate_legacy(path, fmt, strict=strict, warn_only=warn_only)


def _validate_v21(path: Path, text: str, warn_only: bool = False) -> int:
    """Validate a canonical v2.1 WORKLOG.md file. Returns 0 on OK, 1 on FAIL.

    If `warn_only` is True, errors are reported but the function returns 0.
    """
    errors: list[str] = []
    rows = [l for l in text.splitlines()
            if l.strip().startswith("|") and "---" not in l]
    if len(rows) < 2:
        return 0  # only header, no data rows
    header_cells = [c.strip().lower()
                    for c in rows[0].strip("|").split("|")]
    if header_cells != [c.lower() for c in EXPECTED_COLUMNS]:
        # Header is lowercase-form-correct but case-different; that's OK
        errors.append(
            f"  v2.1 header case mismatch: {header_cells} (expected lowercase)"
        )
    for i, row in enumerate(rows[1:], start=1):
        cells = [c.strip() for c in row.strip("|").split("|")]
        if len(cells) != 11:
            errors.append(f"  row {i}: has {len(cells)} cells, expected 11")
            continue
        device = cells[9]
        if device not in VALID_DEVICES:
            errors.append(
                f"  row {i}: device {device!r} is not in CANONICAL_DEVICES "
                f"({sorted(VALID_DEVICES)})"
            )
    if errors:
        prefix = "WARN" if warn_only else "FAIL"
        print(f"{prefix}: {path} (canonical v2.1 but with errors):", file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        return 0 if warn_only else 1
    return 0


def _validate_legacy(path: Path, fmt: str, strict: bool, warn_only: bool) -> int:
    """Validate a legacy-format WORKLOG.md file. Returns 0 on WARN, 1 on FAIL."""
    is_new = _is_new_file(path)
    import datetime
    today = datetime.date.today().isoformat()
    post_cutover = today >= CUTOVER_DATE
    # Determine effective mode
    if warn_only:
        mode = "WARN"
    elif strict or is_new or post_cutover:
        mode = "FAIL"
    else:
        mode = "WARN"
    msg = (
        f"{mode}: {path} is in legacy format {fmt!r} "
        f"(expected canonical v2.1 11-col). "
        f"New file={is_new}, today={today}, cutover={CUTOVER_DATE}. "
        f"Run `python3 migrate_v2_to_v2_1.py {path}` to migrate."
    )
    print(msg, file=sys.stderr)
    return 0 if mode == "WARN" else 1


def main() -> int:
    p = argparse.ArgumentParser(
        description="Pre-commit validator for WORKLOG.md (ADR-015 / ADR-025).",
    )
    p.add_argument("paths", nargs="+", help="Paths to WORKLOG.md files to validate")
    p.add_argument("--strict", action="store_true",
                   help="Fail on legacy formats even before 2026-06-22")
    p.add_argument("--warn-only", action="store_true",
                   help="Never fail; warn only (for diagnostic runs)")
    args = p.parse_args()
    failed = 0
    for path_str in args.paths:
        path = Path(path_str)
        rc = validate(path, strict=args.strict, warn_only=args.warn_only)
        if rc != 0:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
