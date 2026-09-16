#!/usr/bin/env python3
"""Audit candidate evaluator suite locks without fetching or executing anything.

The command reads bounded local YAML files, rejects links, duplicate keys, and
aliases, then reports structural validity separately from scoreability.  A
candidate lock is expected to be valid but blocked until every immutable suite,
runner, harness, verifier, and holdout identity is present.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, TypedDict

import yaml
from yaml.tokens import AliasToken, AnchorToken

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pheno.evidence.contracts import ContractError  # noqa: E402
from pheno.evidence.eval_contracts import (  # noqa: E402
    suite_lock_scoreability_reasons,
    suite_lock_sha256,
    validate_suite_lock,
)
from pheno.evidence.redaction import contains_secret  # noqa: E402

AUDIT_SCHEMA_VERSION = "pheno.eval.lock-audit.v1"
DEFAULT_MAX_INPUT_BYTES = 1024 * 1024
DEFAULT_LOCK_ROOT = ROOT / "config" / "eval_locks"


class LockAuditRow(TypedDict):
    """One row of the audit report (per-lock)."""

    source: str
    valid: bool
    scoreable: bool
    declared_scoreable: bool
    blocking_reasons: list[str]
    error: str


class LockAuditSummary(TypedDict):
    """Aggregate summary across all audited locks."""

    total: int
    valid: int
    scoreable: int
    blocked: int
    errors: int


class LockAuditReport(TypedDict):
    """Top-level audit report shape."""

    schema_version: str
    rows: list[LockAuditRow]
    summary: LockAuditSummary


class LockInputError(ValueError):
    """Raised for bounded local lock-input failures."""


class _StrictSafeLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects aliases and duplicate mapping keys."""

    def construct_mapping(self, node: Any, deep: bool = False) -> dict[Any, Any]:
        self.flatten_mapping(node)
        keys: set[Any] = set()
        for key_node, _value_node in node.value:
            key = self.construct_object(key_node, deep=False)
            try:
                duplicate = key in keys
            except TypeError as exc:
                raise LockInputError("YAML mapping keys must be scalar") from exc
            if duplicate:
                raise LockInputError(f"duplicate YAML mapping key {key!r} is forbidden")
            keys.add(key)
        return super().construct_mapping(node, deep=deep)


def _load_lock(path: Path, *, max_bytes: int) -> Any:
    """Read + parse a lock YAML safely.

    Rejects:
      - Symbolic links (use the resolved regular file only)
      - Inputs > ``max_bytes`` (fail closed)
      - Duplicate keys (via the custom SafeLoader)

    Returns the parsed lock payload (or raises ``LockInputError``).
    """
    if max_bytes < 1:
        raise LockInputError("--max-input-bytes must be positive")
    if path.is_symlink():
        raise LockInputError("lock input must not be a symbolic link")
    try:
        with path.open("rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise LockInputError("lock input must be a regular file")
            if metadata.st_size > max_bytes:
                raise LockInputError(f"lock input exceeds the {max_bytes}-byte limit")
            raw = stream.read(max_bytes + 1)
    except LockInputError:
        raise
    except FileNotFoundError as exc:
        raise LockInputError("lock input does not exist") from exc
    except IsADirectoryError as exc:
        raise LockInputError("lock input must be a regular file") from exc
    except OSError as exc:
        raise LockInputError("lock input could not be read") from exc
    if len(raw) > max_bytes:
        raise LockInputError(f"lock input exceeds the {max_bytes}-byte limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LockInputError("lock input must be UTF-8 YAML") from exc
    try:
        if any(
            isinstance(token, (AliasToken, AnchorToken)) for token in yaml.scan(text)
        ):
            raise LockInputError("YAML aliases are forbidden")
        # bandit: aliases are rejected above via yaml.scan(); _StrictSafeLoader
        # is a SafeLoader derivative that rejects Python/object constructors.
        return yaml.load(text, Loader=_StrictSafeLoader)  # nosec B506
    except LockInputError:
        raise
    except yaml.YAMLError as exc:
        raise LockInputError("lock input is invalid YAML") from exc


def audit_lock(payload: Any, *, source: str) -> dict[str, Any]:
    """Validate a single parsed lock + return scoreability diagnostics.

    Returns a dict with:
      - ``blocking_reasons``: list of immutable-identity gaps (sorted)
      - ``declared_scoreable``: what the lock's integrity block claims
      - ``scoreable``: ``declared_scoreable and not blocking_reasons``
    """
    validated = validate_suite_lock(payload)
    reasons = sorted(suite_lock_scoreability_reasons(validated))
    declared_scoreable = validated["integrity"]["scoreable"]
    return {
        "blocking_reasons": reasons,
        "declared_scoreable": declared_scoreable,
        "evidence_complete": not reasons,
        "lock_sha256": suite_lock_sha256(validated),
        "scoreable": declared_scoreable and not reasons,
        "source": source,
        "suite_id": validated["suite_id"],
        "valid": True,
    }


def _safe_message(exc: BaseException) -> str:
    """Redact exception message to a safe 1000-char single-line string.

    Returns a generic message if the original is empty or contains a
    secret-like substring.
    """
    message = " ".join(str(exc).split())[:1000]
    if not message or contains_secret(message):
        return "lock input violates the evaluator contract"
    return message


def audit_paths(paths: list[Path], *, max_bytes: int) -> dict[str, Any]:
    """Audit a batch of lock paths.

    Returns a dict with ``rows`` (one entry per path) + ``summary``
    (counts of valid / scoreable / blocked).
    """
    rows: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for path in sorted(paths, key=lambda item: item.name.casefold()):
        source = path.name
        source_key = source.casefold()
        if source_key in seen_sources:
            rows.append(
                {
                    "error": "duplicate lock input basename",
                    "source": source,
                    "valid": False,
                }
            )
            continue
        seen_sources.add(source_key)
        try:
            rows.append(
                audit_lock(_load_lock(path, max_bytes=max_bytes), source=source)
            )
        except (ContractError, LockInputError, TypeError, ValueError) as exc:
            rows.append(
                {
                    "error": _safe_message(exc),
                    "source": source,
                    "valid": False,
                }
            )
    valid = [row for row in rows if row["valid"]]
    scoreable = [row for row in valid if row["scoreable"]]
    return {
        "all_scoreable": bool(rows) and len(scoreable) == len(rows),
        "counts": {
            "blocked": len(valid) - len(scoreable),
            "errors": len(rows) - len(valid),
            "inputs": len(rows),
            "scoreable": len(scoreable),
            "valid": len(valid),
        },
        "locks": rows,
        "metadata_only": True,
        "ok": bool(rows) and len(valid) == len(rows),
        "schema_version": AUDIT_SCHEMA_VERSION,
    }


def _parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the audit CLI.

    Args: positional lock paths, --max-input-bytes, --report-format
    (text|json), --strict (non-zero exit on blocking).
    """
    parser = argparse.ArgumentParser(
        description="Offline structural and scoreability audit for evaluator suite locks"
    )
    parser.add_argument("locks", nargs="*", type=Path)
    parser.add_argument(
        "--max-input-bytes",
        type=int,
        default=DEFAULT_MAX_INPUT_BYTES,
    )
    parser.add_argument(
        "--require-scoreable",
        action="store_true",
        help="exit 3 unless every lock is fully pinned and declared scoreable",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint: audit lock files and emit text or JSON report.

    Returns 0 on success; 2 on parse/input errors; 1 on
    --strict + blocking reasons.
    """
    args = _parser().parse_args(argv)
    paths = args.locks or sorted(DEFAULT_LOCK_ROOT.glob("*.yaml"))
    result = audit_paths(paths, max_bytes=args.max_input_bytes)
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    if not result["ok"]:
        return 2
    if args.require_scoreable and not result["all_scoreable"]:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
