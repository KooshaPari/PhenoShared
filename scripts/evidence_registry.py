#!/usr/bin/env python3
"""Plan, run, and validate metadata-only evidence discovery.

Remote discovery requires the explicit ``--allow-metadata-network`` flag.
There is no model download or shortlist-mutation command in this CLI.
"""

from __future__ import annotations

import argparse
import json
import os  # noqa: F401  - re-exported for tests that patch ``os.environ``
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Re-export for monkey-patching from tests (test_evidence_registry.py
# uses ``patch.object(evidence_registry_cli, "MetadataClient", ...)``
# to inject a fake transport).
from pheno.evidence.adapters import (  # noqa: E402, F401
    ArxivAdapter,
    GitHubAdapter,
    HuggingFaceAdapter,
    LocalCorpusAdapter,
    ModelScopeAdapter,
    RedditAdapter,
)
from pheno.evidence.adapters.base import MetadataClient  # noqa: E402, F401
from pheno.evidence.store import RegistryStore  # noqa: E402 - repo-local CLI bootstrap
from pheno.evidence.tournament import (  # noqa: E402 - repo-local CLI bootstrap
    build_candidate_review,
    validate_tournament,
)

# Re-export from sub-module for backward compatibility.
from scripts.evidence_registry_discover import (  # noqa: E402, F401
    ALL_SOURCES,
    REMOTE_SOURCES,
    _attempt_operation,
    _fail_operation,
    _new_operation,
    _operation_id,
    _safe_error,
    _skip_operation,
    discover,
)
from scripts.evidence_registry_export import persist_page  # noqa: E402, F401
from scripts.evidence_registry_queries import (  # noqa: E402, F401
    load_config,
    plan,
    resolve_state_root,
    selected_sources,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Pheno metadata-only evidence registry"
    )
    parser.add_argument(
        "--config", type=Path, default=ROOT / "config" / "evidence_registry.yaml"
    )
    parser.add_argument("--root", type=Path)
    parser.add_argument(
        "--tournament",
        type=Path,
        default=ROOT / "config" / "heterogeneous_tournament.yaml",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "discover"):
        command = sub.add_parser(name)
        command.add_argument("--source", action="append", default=[])
        command.add_argument("--max-queries", type=int)
        if name == "discover":
            command.add_argument("--allow-metadata-network", action="store_true")
            command.add_argument("--resolve-only", action="store_true")
    sub.add_parser("validate")
    sub.add_parser("index")
    review = sub.add_parser("review")
    review.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(args.config.resolve())
    root = resolve_state_root(config, args.root)
    store = RegistryStore(
        root,
        max_snapshot_bytes=int(
            config["policy"].get("max_response_bytes", 8 * 1024 * 1024)
        ),
    )
    if args.command == "validate":
        result = store.validate()
    elif args.command == "index":
        result = {
            "schema_version": "pheno.evidence.index.v1",
            "primary": store.latest_subject_records(),
            "anecdotes": store.latest_anecdotes(),
        }
    elif args.command == "review":
        tournament = yaml.safe_load(
            args.tournament.resolve().read_text(encoding="utf-8")
        )
        validate_tournament(tournament)
        result = build_candidate_review(tournament, store.latest_records())
        if args.output is not None:
            output = args.output.resolve()
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    else:
        sources = selected_sources(config, args.source)
        if args.max_queries is not None and args.max_queries < 1:
            raise ValueError("--max-queries must be positive")
        if args.command == "plan":
            result = plan(config, sources, args.max_queries)
        else:
            result = discover(
                config,
                sources,
                store,
                max_queries=args.max_queries,
                allow_metadata_network=args.allow_metadata_network,
                resolve_only=args.resolve_only,
            )
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok", True) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"evidence registry error: {exc}", file=sys.stderr)
        raise SystemExit(2)
