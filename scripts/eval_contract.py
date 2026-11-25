#!/usr/bin/env python3
"""Validate Pheno evaluator artifacts without executing or fetching anything.

This command intentionally accepts one bounded, regular JSON file and emits one
deterministic JSON result.  It has no network, model, runtime, dataset, or
subprocess integration.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pheno.evidence.atif import validate_atif_integrity  # noqa: E402
from pheno.evidence.contracts import ContractError  # noqa: E402
from pheno.evidence.redaction import contains_secret  # noqa: E402

DEFAULT_MAX_INPUT_BYTES = 16 * 1024 * 1024
OUTPUT_SCHEMA_VERSION = "pheno.eval.contract-cli.v1"


class CliInputError(ValueError):
    """Raised for bounded, user-correctable CLI input errors."""


class _JsonArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise CliInputError(message)


def _reject_constant(value: str) -> None:
    raise CliInputError(f"non-finite JSON number {value!r} is forbidden")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise CliInputError(f"duplicate JSON object key {key!r} is forbidden")
        result[key] = value
    return result


def load_json_file(path: Path, *, max_bytes: int) -> Any:
    """Load one strict, bounded UTF-8 JSON document from a regular file."""

    if max_bytes < 1:
        raise CliInputError("--max-input-bytes must be positive")
    if path.is_symlink():
        raise CliInputError("input must not be a symbolic link")
    try:
        with path.open("rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise CliInputError("input must be a regular file")
            if metadata.st_size > max_bytes:
                raise CliInputError(f"input exceeds the {max_bytes}-byte limit")
            # The bounded read protects against growth between fstat and read.
            raw = stream.read(max_bytes + 1)
    except CliInputError:
        raise
    except FileNotFoundError as exc:
        raise CliInputError("input file does not exist") from exc
    except IsADirectoryError as exc:
        raise CliInputError("input must be a regular file") from exc
    except OSError as exc:
        raise CliInputError("input file could not be read") from exc
    if len(raw) > max_bytes:
        raise CliInputError(f"input exceeds the {max_bytes}-byte limit")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CliInputError("input must be UTF-8 JSON") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise CliInputError(
            f"invalid JSON at line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc


def validate_atif(payload: Any) -> dict[str, Any]:
    summary = validate_atif_integrity(payload)
    return {
        "command": "validate-atif",
        "ok": True,
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "summary": summary.to_dict(),
        "validation_scope": "pheno_atif_integrity_overlay",
    }


def validate_trial(
    payload: Any,
    *,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    from pheno.evidence.trial_contracts import (
        trial_scoreability_reasons,
        trial_sha256,
        validate_trial_artifact_bundle,
        validate_trial_record,
    )

    validated = validate_trial_record(payload)
    record_reasons = sorted(trial_scoreability_reasons(validated))
    artifact_summary: dict[str, Any] | None = None
    artifact_bundle_verified = False
    effective_reasons = list(record_reasons)
    if artifact_root is None:
        effective_reasons.append("artifact bytes were not verified in this invocation")
    else:
        # The shared validator resolves and bounds the bundle.  Reject the
        # root link itself here as well so a CLI caller cannot silently select
        # a different directory through a mutable link.
        if artifact_root.is_symlink():
            raise ContractError("artifact_root must not be a symbolic link")
        artifact_summary = validate_trial_artifact_bundle(validated, artifact_root)
        artifact_bundle_verified = True
    return {
        "artifact_bundle_summary": artifact_summary,
        "artifact_bundle_verified": artifact_bundle_verified,
        "command": "validate-trial",
        "ok": True,
        "record_schema_version": validated["schema_version"],
        "record_scoreability_reasons": record_reasons,
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "scoreability_reasons": effective_reasons,
        "scoreable": artifact_bundle_verified and not record_reasons,
        "trial_sha256": trial_sha256(validated),
    }


def validate_aggregate(payload: Any) -> dict[str, Any]:
    from pheno.evidence.aggregate_contracts import (
        aggregate_sha256,
        validate_aggregate_record,
    )

    validated = validate_aggregate_record(payload)
    return {
        "aggregate_sha256": aggregate_sha256(validated),
        "command": "validate-aggregate",
        "ok": True,
        "record_schema_version": validated["schema_version"],
        "schema_version": OUTPUT_SCHEMA_VERSION,
    }


def validate_performance_block(payload: Any) -> dict[str, Any]:
    from pheno.evidence.performance_blocks import (
        performance_block_sha256,
        validate_performance_block_record,
    )

    validated = validate_performance_block_record(payload)
    return {
        "command": "validate-performance-block",
        "ok": True,
        "performance_block_sha256": performance_block_sha256(validated),
        "promotion_status": validated["promotion"]["status"],
        "record_schema_version": validated["schema_version"],
        "schema_version": OUTPUT_SCHEMA_VERSION,
    }


def validate_replay_stability(payload: Any) -> dict[str, Any]:
    from pheno.evidence.replay_stability import (
        replay_stability_sha256,
        validate_replay_stability_record,
    )

    validated = validate_replay_stability_record(payload)
    return {
        "block_id": validated["block_id"],
        "command": "validate-replay-stability",
        "mode": validated["mode"],
        "ok": True,
        "promotion_reason_codes": validated["promotion"]["reason_codes"],
        "promotion_status": validated["promotion"]["status"],
        "record_schema_version": validated["schema_version"],
        "replay_stability_sha256": replay_stability_sha256(validated),
        "schema_version": OUTPUT_SCHEMA_VERSION,
    }


def validate_telemetry(payload: Any) -> dict[str, Any]:
    from pheno.evidence.telemetry import (
        telemetry_bundle_sha256,
        validate_telemetry_bundle,
    )

    validated = validate_telemetry_bundle(payload)
    return {
        "command": "validate-telemetry",
        "memory_alignment_status": validated["summary"]["memory"]["alignment_status"],
        "ok": True,
        "quality_status": validated["quality"]["status"],
        "record_schema_version": validated["schema_version"],
        "schema_version": OUTPUT_SCHEMA_VERSION,
        "telemetry_bundle_sha256": telemetry_bundle_sha256(validated),
        "telemetry_id": validated["telemetry_id"],
    }


def _parser() -> argparse.ArgumentParser:
    parser = _JsonArgumentParser(
        description="Offline validation for Pheno evaluator JSON artifacts"
    )
    parser.add_argument(
        "--max-input-bytes",
        type=int,
        default=DEFAULT_MAX_INPUT_BYTES,
        help=f"maximum JSON input size (default: {DEFAULT_MAX_INPUT_BYTES})",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    for name in (
        "validate-atif",
        "validate-trial",
        "validate-aggregate",
        "validate-performance-block",
        "validate-replay-stability",
        "validate-telemetry",
    ):
        command = commands.add_parser(name)
        command.add_argument("input", type=Path)
        if name == "validate-trial":
            command.add_argument(
                "--artifact-root",
                type=Path,
                help=("verify every declared artifact byte beneath this directory"),
            )
    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return _parser().parse_args(argv)


def _emit(result: dict[str, Any], *, stream: Any | None = None) -> None:
    if stream is None:
        stream = sys.stdout
    print(
        json.dumps(
            result,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ),
        file=stream,
    )


def _safe_message(exc: BaseException) -> str:
    message = str(exc)
    if not message or contains_secret(message):
        return "input violates the evaluator contract"
    # Bound validator-controlled diagnostics and prevent multi-line output.
    return " ".join(message.split())[:1000]


def main(argv: list[str] | None = None) -> int:
    command: str | None = None
    try:
        args = parse_args(argv)
        command = args.command
        payload = load_json_file(args.input, max_bytes=args.max_input_bytes)
        validators: dict[str, Callable[[Any], dict[str, Any]]] = {
            "validate-atif": validate_atif,
            "validate-aggregate": validate_aggregate,
            "validate-performance-block": validate_performance_block,
            "validate-replay-stability": validate_replay_stability,
            "validate-telemetry": validate_telemetry,
        }
        if command == "validate-trial":
            result = validate_trial(payload, artifact_root=args.artifact_root)
        else:
            result = validators[command](payload)
        _emit(result)
        return 0
    except (CliInputError, ContractError, TypeError, ValueError) as exc:
        _emit(
            {
                "command": command,
                "error": {"kind": "input_or_contract", "message": _safe_message(exc)},
                "ok": False,
                "schema_version": OUTPUT_SCHEMA_VERSION,
            },
            stream=sys.stderr,
        )
        return 2
    except Exception:
        _emit(
            {
                "command": command,
                "error": {
                    "kind": "internal",
                    "message": "unexpected evaluator validation error",
                },
                "ok": False,
                "schema_version": OUTPUT_SCHEMA_VERSION,
            },
            stream=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
