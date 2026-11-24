#!/usr/bin/env python3
"""Offline fleet-readiness validation and interval simulation CLI.

The command reads policy or caller-supplied JSON and writes JSON to stdout. It
has no install, download, launch, SSH, remote-probe, or output-file operation.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pheno.evidence.redaction import contains_secret  # noqa: E402
from pheno.fleet_readiness import (  # noqa: E402
    REMOTE_TEMPLATE_PROFILES,
    FleetReadinessError,
    build_remote_capability_template,
    capability_readiness,
    load_policy,
    simulate_gtx1080_helper,
)

MAX_INPUT_BYTES = 1024 * 1024


def _reject_constant(value: str) -> None:
    raise FleetReadinessError(f"JSON contains non-finite constant {value}")


def _closed_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FleetReadinessError(f"JSON contains duplicate key {key!r}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        raise FleetReadinessError("input JSON must not be a symbolic link")
    try:
        with path.open("rb") as stream:
            metadata = os.fstat(stream.fileno())
            if not stat.S_ISREG(metadata.st_mode):
                raise FleetReadinessError("input JSON must be a regular file")
            if metadata.st_size > MAX_INPUT_BYTES:
                raise FleetReadinessError("input JSON exceeds the 1 MiB limit")
            payload = stream.read(MAX_INPUT_BYTES + 1)
    except FleetReadinessError:
        raise
    except OSError as exc:
        raise FleetReadinessError("input JSON cannot be read") from exc
    if len(payload) > MAX_INPUT_BYTES:
        raise FleetReadinessError("input JSON exceeds the 1 MiB limit")
    try:
        raw = payload.decode("utf-8")
        value = json.loads(
            raw,
            parse_constant=_reject_constant,
            object_pairs_hook=_closed_object,
        )
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise FleetReadinessError("input is not valid UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise FleetReadinessError("input JSON root must be an object")
    return value


def _dump(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
        allow_nan=False,
    )


def _safe_message(exc: BaseException) -> str:
    message = " ".join(str(exc).split())[:1000]
    if not message or contains_secret(message):
        return "input violates the fleet-readiness contract"
    return message


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Offline, read-only heterogeneous fleet readiness"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=ROOT / "config" / "fleet_readiness.yaml",
        help="local fleet-readiness policy",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("validate-policy", help="validate the fail-closed policy")

    capability = subparsers.add_parser(
        "validate-capability", help="validate a supplied capability JSON bundle"
    )
    capability.add_argument("input", type=Path)

    template = subparsers.add_parser(
        "template-remote",
        help="emit a deterministic, non-authorizing remote manifest template",
    )
    template.add_argument(
        "--device", choices=sorted(REMOTE_TEMPLATE_PROFILES), required=True
    )

    helper = subparsers.add_parser(
        "simulate-1080", help="evaluate explicit conservative interval inputs"
    )
    helper.add_argument("input", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        policy = load_policy(args.config)
        if args.command == "validate-policy":
            output = {
                "schema_version": policy["schema_version"],
                "valid": True,
                "all_mutation_and_install_gates_false": True,
            }
        elif args.command == "validate-capability":
            output = capability_readiness(load_json(args.input), policy)
        elif args.command == "template-remote":
            output = build_remote_capability_template(args.device, policy)
        elif args.command == "simulate-1080":
            output = simulate_gtx1080_helper(load_json(args.input), policy)
        else:  # pragma: no cover - argparse closes the command set
            parser.error("unknown command")
            return 2
    except (FleetReadinessError, OSError, UnicodeError, yaml.YAMLError) as exc:
        print(
            _dump(
                {
                    "error": {
                        "type": "fleet_readiness_validation_error",
                        "message": _safe_message(exc),
                    }
                }
            ),
            file=sys.stderr,
        )
        return 2
    print(_dump(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
