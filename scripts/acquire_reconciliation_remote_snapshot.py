#!/usr/bin/env python3
"""Acquire a bounded, GET-only GitHub reconciliation snapshot.

On success the command writes exactly one canonical
``pheno.reconciliation.remote-snapshot.v1`` JSON document to stdout. It never
writes a file, invokes Git, changes remote state, or prints raw API/auth output.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any, BinaryIO

from scripts.acquire_snapshot_download import (  # noqa: F401
    API_HOST,
    API_VERSION,
    BRANCH_FILTER,
    BRANCH_PAGE_SIZE,
    COMPARE_FILTER,
    DEFAULT_ATTEMPTS,
    DEFAULT_BRANCH_FILTER,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_BRANCH_PAGE_REQUESTS,
    MAX_RESPONSE_BYTES,
    MAX_STDERR_BYTES,
    REPOSITORY_FILTER,
    REPOSITORY_RE,
    SHA_RE,
    CommandResult,
    CommandRunner,
    SnapshotError,
    SnapshotOptions,
    _bounded_reader,
    _canonical_bytes,
    _closed_object,
    _decode_json,
    _gh_environment,
    _GhClient,
    _Observation,
    _reject_constant,
    _require_exact_keys,
    _run_command,
    _valid_branch_name,
    _validate_sha,
)
from scripts.acquire_snapshot_verify import (  # noqa: F401
    _branch_page,
    _branches,
    _captured_at,
    _compare,
    _default_ref,
    _observe,
    _repository,
    _validate_options,
)

SCHEMA_VERSION = "pheno.reconciliation.remote-snapshot.v1"
ERROR_SCHEMA_VERSION = "pheno.reconciliation.remote-snapshot-error.v1"


def acquire_snapshot(
    options: SnapshotOptions,
    *,
    runner: CommandRunner = _run_command,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    options = _validate_options(options)
    client = _GhClient(
        runner=runner,
        timeout_seconds=options.timeout_seconds,
        attempts=options.attempts,
        sleeper=sleeper,
    )
    first = _observe(client, options.repository, options.expected_default_branch)
    first_branches = dict(first.branches)
    live_sha = first_branches[options.expected_default_branch]
    _compare(client, options.repository, options.base_sha, live_sha)
    second = _observe(client, options.repository, options.expected_default_branch)
    if first != second:
        raise SnapshotError(
            "REMOTE_NOT_QUIESCENT", "GitHub state moved during snapshot acquisition"
        )
    if options.expected_live_sha is not None and live_sha != options.expected_live_sha:
        raise SnapshotError(
            "REMOTE_LIVE_SHA_MISMATCH", "GitHub live tip differs from the expected pin"
        )
    if options.expected_branches and first.branches != options.expected_branches:
        raise SnapshotError(
            "REMOTE_BRANCH_SET_MISMATCH",
            "GitHub branch set differs from the exact expected set",
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "captured_at_utc": _captured_at(clock),
        "repository": dict(first.repository),
        "base_sha": options.base_sha,
        "local_sha": options.local_sha,
        "live_sha": live_sha,
        "branches": [{"name": name, "sha": sha} for name, sha in first.branches],
    }


def _parse_expected_branch(raw: str) -> tuple[str, str]:
    name, separator, sha = raw.rpartition("=")
    if not separator:
        raise SnapshotError(
            "ARGUMENT_BRANCH_SET_INVALID", "expected branch must be NAME=SHA"
        )
    return name, sha


class _SafeArgumentParser(argparse.ArgumentParser):
    def error(self, _message: str) -> None:
        raise SnapshotError(
            "ARGUMENT_INVALID", "command arguments violate the acquisition contract"
        )


def _parser() -> argparse.ArgumentParser:
    parser = _SafeArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--expected-default-branch", default="main")
    parser.add_argument("--base-sha", required=True)
    parser.add_argument("--local-sha", required=True)
    parser.add_argument("--expected-live-sha")
    parser.add_argument(
        "--expected-branch",
        action="append",
        type=_parse_expected_branch,
        default=[],
        metavar="NAME=SHA",
        help="optional exact branch-set guard; repeat for every branch",
    )
    parser.add_argument(
        "--timeout-seconds", type=float, default=DEFAULT_TIMEOUT_SECONDS
    )
    parser.add_argument("--attempts", type=int, default=DEFAULT_ATTEMPTS)
    return parser


def _error_document(exc: SnapshotError) -> dict[str, Any]:
    return {
        "error": {"code": exc.code, "message": exc.safe_message},
        "ok": False,
        "schema_version": ERROR_SCHEMA_VERSION,
    }


def main(
    argv: Sequence[str] | None = None,
    *,
    runner: CommandRunner = _run_command,
    sleeper: Callable[[float], None] = time.sleep,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    output: BinaryIO | None = None,
) -> int:
    stream = output if output is not None else sys.stdout.buffer
    try:
        namespace = _parser().parse_args(argv)
        snapshot = acquire_snapshot(
            SnapshotOptions(
                repository=namespace.repository,
                expected_default_branch=namespace.expected_default_branch,
                base_sha=namespace.base_sha,
                local_sha=namespace.local_sha,
                expected_live_sha=namespace.expected_live_sha,
                expected_branches=tuple(namespace.expected_branch),
                timeout_seconds=namespace.timeout_seconds,
                attempts=namespace.attempts,
            ),
            runner=runner,
            sleeper=sleeper,
            clock=clock,
        )
        stream.write(_canonical_bytes(snapshot) + b"\n")
        return 0
    except SnapshotError as exc:
        stream.write(_canonical_bytes(_error_document(exc)) + b"\n")
        return 2
    except Exception:
        error = SnapshotError(
            "ACQUISITION_FAILED", "a bounded snapshot acquisition check failed"
        )
        stream.write(_canonical_bytes(_error_document(error)) + b"\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
