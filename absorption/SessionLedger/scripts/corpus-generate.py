#!/usr/bin/env python3
"""
corpus-generate.py — production-scale OKF conformance fixture generator (W44-B6)

Wave-44 close-out for C08 L73 (production-scale corpus breadth).

Usage:
  python3 scripts/corpus-generate.py --out docs/reference/conformance/fixtures
  python3 scripts/corpus-generate.py --out docs/reference/conformance/fixtures --only aider-rust
  python3 scripts/corpus-generate.py --list

Generates a curated batch of fixtures that cover dimensions not yet exercised
by the 20 hand-vetted fixtures shipped in W43:

  - Additional agent sources (aider, opencode, continue, kiro, factory-droid-2)
  - Additional languages (rust, go, bash, yaml, sql)
  - Stress shapes (large entity count, deep relation graph, rapid-fire intent stream)
  - Edge cases (unicode intent label, embedded JSON label, multi-modal hint)
  - Failure-mode rejection shapes (malformed-truncated, missing-provenance, duplicate-id)

Every emitted fixture is a valid OKF 1.0 document per docs/reference/OKF-SPEC.md.
The conformance harness (tests/okf_roundtrip.rs) MUST continue to accept all
emitted fixtures. Output filename pattern: <slug>-<3-digit-id>.okf.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from pathlib import Path
from typing import Any, Iterable

OKF_VERSION = "1.0"

# ---------------------------------------------------------------------------
# Fixture library
# ---------------------------------------------------------------------------

# Dimensions still missing after W43 (20 hand-vetted fixtures):
#   - Sources: aider, opencode, continue, kiro, factory-droid-2
#   - Languages: rust, go, bash, yaml, sql
#   - Stress shapes: large entity count, deep relation graph, rapid-fire intent stream
#   - Edge cases: unicode intent label, embedded JSON label, multi-modal hint
#   - Failure-mode rejection shapes: malformed-truncated, missing-provenance, duplicate-id
#
# Each entry: (slug, id, builder_callable)

FIXTURE_SPECS: list[tuple[str, str, Any]] = [
    # --- Additional agent sources ---
    ("aider-rust-refactor",        "037", "build_aider_rust_refactor"),
    ("opencode-python-debugger",    "038", "build_opencode_python_debugger"),
    ("continue-go-microservice",    "039", "build_continue_go_microservice"),
    ("kiro-bash-ci-pipeline",      "040", "build_kiro_bash_ci_pipeline"),
    ("factory-droid-typescript",    "041", "build_factory_droid_typescript"),

    # --- Additional languages ---
    ("sql-migration-multi-intent",  "043", "build_sql_migration_multi_intent"),
    ("yaml-k8s-deployment",        "044", "build_yaml_k8s_deployment"),

    # --- Stress shapes ---
    ("large-entity-count-100",     "045", "build_large_entity_count"),
    ("deep-relation-graph-7",       "046", "build_deep_relation_graph"),
    ("rapid-fire-intent-stream-12", "047", "build_rapid_fire_intent_stream"),

    # --- Edge cases ---
    ("unicode-intent-label-cjk",    "048", "build_unicode_intent_label"),
    ("embedded-json-label",         "049", "build_embedded_json_label"),
    ("multi-modal-image-hint",      "050", "build_multi_modal_image_hint"),

    # --- Failure-mode rejection shapes ---
    # These are written but the harness should reject them; see FAILURE_FIXTURES.
    # They are NOT included in the default accepted-corpus run.
]


# Failure-mode fixtures (separate list so default run excludes them).
FAILURE_FIXTURES: list[tuple[str, str, Any]] = [
    ("malformed-truncated",         "E01", "build_malformed_truncated"),
    ("missing-provenance",          "E02", "build_missing_provenance"),
    ("duplicate-id",                "E03", "build_duplicate_id"),
]


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------

def _entity(eid: str, etype: str, label: str, properties: dict | None = None) -> dict:
    return {
        "id": eid,
        "type": etype,
        "label": label,
        "properties": properties if properties is not None else None,
    }


def _rel(src: str, tgt: str, rtype: str, prov: dict) -> dict:
    return {"source": src, "target": tgt, "type": rtype, "provenance": prov}


def _okf(source_id: str, corpus: str, entities: list, relations: list | None = None) -> dict:
    doc: dict[str, Any] = {
        "okf": OKF_VERSION,
        "source_id": source_id,
        "entities": entities,
        "provenance": {"corpus": corpus, "source_id": source_id},
    }
    if relations:
        doc["relations"] = relations
    return doc


def _prov(corpus: str, source_id: str) -> dict:
    return {"corpus": corpus, "source_id": source_id}


# ---------------------------------------------------------------------------
# Builders — accepted fixtures
# ---------------------------------------------------------------------------

def build_aider_rust_refactor() -> dict:
    sid = "aider-rust-refactor-037"
    p = _prov("aider", sid)
    return _okf(sid, "aider", [
        _entity("intent-0", "intent", "Refactor trait bounds to remove Box<dyn> indirection on LedgerStore", {"user_turn_count": 4}),
        _entity("acceptance-0", "acceptance", "cargo test -p sl-daemon --lib passes (no new warnings)", None),
        _entity("acceptance-1", "acceptance", "cargo clippy --workspace -- -D warnings green", None),
        _entity("constraint-0", "constraint", "keep public API stable; bump minor only on SemVer breaks", None),
        _entity("resource-0", "resource", "working-directory", {"cwd": "/home/dev/sl-daemon"}),
        _entity("criteria-0", "criteria", "trait-object removal must be measurable", {"watch_files": ["crates/sl-daemon/src/ledger.rs"], "skipped_by": []}),
        _entity("gate-0", "gate", "refactor-gate", {"ready": True, "scope_sized": True, "user_turns": 4, "total_token_estimate": 320}),
    ], [
        _rel("intent-0", "acceptance-0", "verified_by", p),
        _rel("intent-0", "acceptance-1", "verified_by", p),
        _rel("intent-0", "constraint-0", "bounded_by", p),
        _rel("intent-0", "resource-0", "grounds", p),
        _rel("intent-0", "criteria-0", "requires", p),
        _rel("intent-0", "gate-0", "asserts", p),
    ])


def build_opencode_python_debugger() -> dict:
    sid = "opencode-python-debugger-038"
    p = _prov("opencode", sid)
    return _okf(sid, "opencode", [
        _entity("intent-0", "intent", "Trace async iterator dropped-task warning in TaskDistributor", {"user_turn_count": 5}),
        _entity("acceptance-0", "acceptance", "pytest tests/test_distributor.py -k dropped_task passes", None),
        _entity("constraint-0", "constraint", "do not pull in new runtime deps; stdlib asyncio only", None),
        _entity("state-0", "state", "session-title", {"title": "Distributor dropped-task trace"}),
    ], [
        _rel("intent-0", "acceptance-0", "verified_by", p),
        _rel("intent-0", "constraint-0", "bounded_by", p),
        _rel("intent-0", "state-0", "grounds", p),
    ])


def build_continue_go_microservice() -> dict:
    sid = "continue-go-microservice-039"
    p = _prov("continue", sid)
    return _okf(sid, "continue", [
        _entity("intent-0", "intent", "Add /healthz/ready endpoint to the gateway", {"user_turn_count": 2}),
        _entity("intent-1", "intent", "Make readiness check respect circuit breaker state", {"user_turn_count": 3}),
        _entity("acceptance-0", "acceptance", "go test ./internal/gateway/... passes", None),
        _entity("acceptance-1", "acceptance", "k6 smoke script /healthz/ready returns 200 within 50ms", None),
        _entity("constraint-0", "constraint", "no new external HTTP client deps", None),
        _entity("gate-0", "gate", "ship-gate", {"ready": True, "scope_sized": True, "user_turns": 5, "total_token_estimate": 210}),
    ], [
        _rel("intent-0", "acceptance-0", "verified_by", p),
        _rel("intent-0", "constraint-0", "bounded_by", p),
        _rel("intent-1", "acceptance-1", "verified_by", p),
        _rel("intent-1", "intent-0", "grounds", p),
        _rel("intent-1", "gate-0", "asserts", p),
    ])


def build_kiro_bash_ci_pipeline() -> dict:
    sid = "kiro-bash-ci-pipeline-040"
    p = _prov("kiro", sid)
    return _okf(sid, "kiro", [
        _entity("intent-0", "intent", "Pin third-party GitHub Actions to commit SHAs in CI workflow", {"user_turn_count": 2}),
        _entity("acceptance-0", "acceptance", "renovate dry-run produces no diff for any pinned action", None),
        _entity("constraint-0", "constraint", "preserve workflow comments; no semantic changes to jobs", None),
        _entity("criteria-0", "criteria", "pinning scan runs on PRs touching .github/workflows", {"watch_files": [".github/workflows/"], "skipped_by": []}),
    ], [
        _rel("intent-0", "acceptance-0", "verified_by", p),
        _rel("intent-0", "constraint-0", "bounded_by", p),
        _rel("intent-0", "criteria-0", "requires", p),
    ])


def build_factory_droid_typescript() -> dict:
    sid = "factory-droid-typescript-041"
    p = _prov("factory-droid", sid)
    return _okf(sid, "factory-droid", [
        _entity("intent-0", "intent", "Replace ad-hoc fetch with retry-aware client for sl-viewer telemetry", {"user_turn_count": 4}),
        _entity("acceptance-0", "acceptance", "vitest run -t 'telemetry client' passes", None),
        _entity("acceptance-1", "acceptance", "tsc --noEmit clean", None),
        _entity("constraint-0", "constraint", "no new transitive deps; keep bundle size under +5KB", None),
    ], [
        _rel("intent-0", "acceptance-0", "verified_by", p),
        _rel("intent-0", "acceptance-1", "verified_by", p),
        _rel("intent-0", "constraint-0", "bounded_by", p),
    ])


def build_sql_migration_multi_intent() -> dict:
    sid = "sql-migration-multi-intent-043"
    p = _prov("forge", sid)
    return _okf(sid, "forge", [
        _entity("intent-0", "intent", "Add `applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()` to migration_log", {"user_turn_count": 2}),
        _entity("intent-1", "intent", "Backfill applied_at from session_start for legacy rows", {"user_turn_count": 3}),
        _entity("intent-2", "intent", "Document the migration in CHANGELOG (non-breaking)", {"user_turn_count": 1}),
        _entity("acceptance-0", "acceptance", "psql -c '\\d migration_log' shows new column", None),
        _entity("acceptance-1", "acceptance", "backfill SQL runs to completion on staging dump", None),
        _entity("constraint-0", "constraint", "ALTER TABLE must be ONLINE; no exclusive locks", None),
        _entity("constraint-1", "constraint", "do not change primary key shape", None),
    ], [
        _rel("intent-0", "acceptance-0", "verified_by", p),
        _rel("intent-0", "constraint-0", "bounded_by", p),
        _rel("intent-1", "acceptance-1", "verified_by", p),
        _rel("intent-1", "intent-0", "grounds", p),
        _rel("intent-1", "constraint-1", "bounded_by", p),
        _rel("intent-2", "intent-0", "grounds", p),
        _rel("intent-2", "intent-1", "grounds", p),
    ])


def build_yaml_k8s_deployment() -> dict:
    sid = "yaml-k8s-deployment-044"
    p = _prov("forge", sid)
    return _okf(sid, "forge", [
        _entity("intent-0", "intent", "Bump sl-daemon Deployment to 3 replicas with rollingUpdate maxUnavailable=0", {"user_turn_count": 3}),
        _entity("acceptance-0", "acceptance", "kubectl rollout status deployment/sl-daemon completes within 60s", None),
        _entity("constraint-0", "constraint", "preserve existing PodDisruptionBudget (minAvailable=2)", None),
        _entity("resource-0", "resource", "kustomize-overlay", {"cwd": "deploy/overlays/prod"}),
    ], [
        _rel("intent-0", "acceptance-0", "verified_by", p),
        _rel("intent-0", "constraint-0", "bounded_by", p),
        _rel("intent-0", "resource-0", "grounds", p),
    ])


def build_large_entity_count() -> dict:
    """100-entity fixture: stress entity-set serialisation."""
    sid = "large-entity-count-100-045"
    p = _prov("forge", sid)
    entities = [_entity(f"intent-{i}", "intent", f"step-{i} of a long refactor session", {"user_turn_count": 1, "token_estimate": 25 + i}) for i in range(40)]
    entities += [_entity(f"acceptance-{i}", "acceptance", f"verify step-{i}", None) for i in range(20)]
    entities += [_entity(f"constraint-{i}", "constraint", f"do not regress step-{i} perf", None) for i in range(20)]
    entities += [_entity(f"resource-0", "resource", "working-directory", {"cwd": "/srv/long-refactor"}),
                 _entity("gate-0", "gate", "completion-gate", {"ready": True, "scope_sized": True, "user_turns": 40, "total_token_estimate": 1234})]
    relations = [_rel(f"intent-{i}", f"acceptance-{i % 20}", "verified_by", p) for i in range(40)]
    relations += [_rel(f"intent-{i}", f"constraint-{i % 20}", "bounded_by", p) for i in range(40)]
    relations += [_rel("intent-39", "gate-0", "asserts", p)]
    return _okf(sid, "forge", entities, relations)


def build_deep_relation_graph() -> dict:
    """Deep chain of 7 relations across 8 entities."""
    sid = "deep-relation-graph-7-046"
    p = _prov("forge", sid)
    entities = [
        _entity("intent-0", "intent", "drive the 7-link relation chain to completion", {"user_turn_count": 1}),
        _entity("acceptance-0", "acceptance", "transitive closure computed in O(N)", None),
        _entity("constraint-0", "constraint", "no N+1 traversal; precompute adjacency once", None),
        _entity("resource-0", "resource", "graph-store", {"path": "src/domain/graph.rs"}),
        _entity("state-0", "state", "relation-depth-marker", {"depth": 7}),
        _entity("criteria-0", "criteria", "depth=7 chain resolves under 5ms p99", {"watch_files": ["src/domain/graph.rs"], "skipped_by": []}),
        _entity("criteria-1", "criteria", "adjacency cache invalidates on insert only", {"watch_files": ["src/domain/graph.rs"], "skipped_by": []}),
        _entity("gate-0", "gate", "graph-chain-gate", {"ready": True, "scope_sized": True, "user_turns": 1, "total_token_estimate": 90}),
    ]
    relations = [
        _rel("intent-0", "acceptance-0", "verified_by", p),
        _rel("intent-0", "constraint-0", "bounded_by", p),
        _rel("intent-0", "resource-0", "grounds", p),
        _rel("intent-0", "state-0", "grounds", p),
        _rel("intent-0", "criteria-0", "requires", p),
        _rel("intent-0", "criteria-1", "requires", p),
        _rel("intent-0", "gate-0", "asserts", p),
    ]
    return _okf(sid, "forge", entities, relations)


def build_rapid_fire_intent_stream() -> dict:
    """12 intents emitted in rapid succession, no acceptance/constraint yet."""
    sid = "rapid-fire-intent-stream-12-047"
    p = _prov("forge", sid)
    entities = [
        _entity(f"intent-{i}", "intent", f"quick intent #{i} (rapid-fire)", {"user_turn_count": 1, "phase": "stream", "seq": i})
        for i in range(12)
    ]
    relations = []
    return _okf(sid, "forge", entities, relations)


def build_unicode_intent_label() -> dict:
    """CJK unicode in label; sanity check for serializer round-trip."""
    sid = "unicode-intent-label-cjk-048"
    p = _prov("forge", sid)
    return _okf(sid, "forge", [
        _entity("intent-0", "intent", "在仪表板中添加暗模式支持", {"user_turn_count": 1, "locale": "zh-CN"}),
        _entity("acceptance-0", "acceptance", "tests pass; UI flips per prefers-color-scheme", None),
        _entity("constraint-0", "constraint", "use existing CSS variable layer; no new theme deps", None),
    ], [
        _rel("intent-0", "acceptance-0", "verified_by", p),
        _rel("intent-0", "constraint-0", "bounded_by", p),
    ])


def build_embedded_json_label() -> dict:
    """Label that contains a JSON snippet (must not break parser)."""
    sid = "embedded-json-label-049"
    p = _prov("forge", sid)
    json_label = 'parse {"kind":"runtime-error","stack":[...]} and surface'
    return _okf(sid, "forge", [
        _entity("intent-0", "intent", json_label, {"user_turn_count": 2}),
        _entity("acceptance-0", "acceptance", "error envelope renders inline; no XSS", None),
        _entity("constraint-0", "constraint", "escape HTML entities before rendering", None),
    ], [
        _rel("intent-0", "acceptance-0", "verified_by", p),
        _rel("intent-0", "constraint-0", "bounded_by", p),
    ])


def build_multi_modal_image_hint() -> dict:
    """Intent carries a multi-modal hint (image attachment metadata)."""
    sid = "multi-modal-image-hint-050"
    p = _prov("claude-code", sid)
    return _okf(sid, "claude-code", [
        _entity("intent-0", "intent", "Reproduce the bug from the screenshot attached above", {
            "user_turn_count": 1,
            "attachments": [{"kind": "image/png", "sha256": "0" * 64, "width": 1440, "height": 900}],
        }),
        _entity("acceptance-0", "acceptance", "step-by-step repro captured in test_repro.md", None),
        _entity("constraint-0", "constraint", "do not embed image bytes in OKF; reference by sha256", None),
    ], [
        _rel("intent-0", "acceptance-0", "verified_by", p),
        _rel("intent-0", "constraint-0", "bounded_by", p),
    ])


# ---------------------------------------------------------------------------
# Builders — failure-mode rejection fixtures
# ---------------------------------------------------------------------------

def build_malformed_truncated() -> dict:
    """Document is truncated mid-array; harness must reject."""
    # We deliberately write a syntactically invalid JSON document.
    # Stored as a string in the builder; the writer will dump it raw.
    return {"__raw_invalid_json__": '{\n  "okf": "1.0",\n  "source_id": "trunc-E01",\n  "entities": [\n    {"id": "intent-0", "type": "intent", "label": "truncated mid-array"'}


def build_missing_provenance() -> dict:
    """No top-level provenance; harness must reject."""
    return {
        "okf": OKF_VERSION,
        "source_id": "missing-prov-E02",
        "entities": [
            _entity("intent-0", "intent", "no provenance at top level", {"user_turn_count": 1}),
        ],
        # NB: no "provenance" key — invalid per OKF-SPEC §6
    }


def build_duplicate_id() -> dict:
    """Two entities with the same id; harness must reject."""
    sid = "duplicate-id-E03"
    return {
        "okf": OKF_VERSION,
        "source_id": sid,
        "entities": [
            _entity("intent-0", "intent", "first", None),
            _entity("intent-0", "intent", "second (duplicate id)", None),  # duplicate!
        ],
        "provenance": {"corpus": "forge", "source_id": sid},
    }


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def _write(path: Path, doc: Any, raw: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if raw:
        path.write_text(doc + "\n", encoding="utf-8")
    else:
        path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _emit(out_dir: Path, slug: str, fid: str, builder_name: str, accepted: bool) -> str:
    builder = globals()[builder_name]
    doc = builder()
    if accepted:
        fname = f"{slug}-{fid}.okf.json"
        _write(out_dir / fname, doc)
        return f"  + {fname}"
    else:
        fname = f"{slug}-{fid}.okf.json"
        if isinstance(doc, dict) and "__raw_invalid_json__" in doc:
            _write(out_dir / fname, doc["__raw_invalid_json__"], raw=True)
        else:
            _write(out_dir / fname, doc)
        return f"  ~ {fname}  (FAILURE-MODE; expected rejection by harness)"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate OKF conformance fixtures (Wave-44 B6).", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=textwrap.dedent(__doc__ or ""))
    ap.add_argument("--out", type=Path, default=Path("docs/reference/conformance/fixtures"), help="Output directory (default: %(default)s)")
    ap.add_argument("--only", default=None, help="Only emit the named slug (e.g. aider-rust-refactor).")
    ap.add_argument("--include-failures", action="store_true", help="Also emit failure-mode fixtures (E01–E03).")
    ap.add_argument("--list", action="store_true", help="Print the planned fixture set and exit.")
    args = ap.parse_args(argv)

    if args.list:
        print("Planned fixtures (default accepted run):")
        for slug, fid, name in FIXTURE_SPECS:
            print(f"  {slug}-{fid}  ({name})")
        if args.include_failures:
            print("\nFailure-mode fixtures:")
            for slug, fid, name in FAILURE_FIXTURES:
                print(f"  {slug}-{fid}  ({name})")
        return 0

    args.out.mkdir(parents=True, exist_ok=True)
    written = 0
    for slug, fid, name in FIXTURE_SPECS:
        if args.only and args.only not in slug:
            continue
        print(_emit(args.out, slug, fid, name, accepted=True))
        written += 1
    if args.include_failures:
        for slug, fid, name in FAILURE_FIXTURES:
            if args.only and args.only not in slug:
                continue
            print(_emit(args.out, slug, fid, name, accepted=False))
            written += 1
    print(f"\n{written} fixture(s) written to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
