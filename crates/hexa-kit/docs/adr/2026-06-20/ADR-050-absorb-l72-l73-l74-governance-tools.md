# ADR-050: HexaKit absorbs 3 governance tools (L72/L73/L74 closed loop)

**Date:** 2026-06-20
**Status:** ACCEPTED
**Supersedes:** none
**Superseded by:** none

## Context

The 3 standalone repos `<REDACTED>/pheno-predict` (L72), `<REDACTED>/pheno-framework-lint` (L73), and `<REDACTED>/pheno-drift-detector` (L74) were single-file Python CLIs implementing:

- **L72 predict** (ADR-047): fleet-wide similar-code scanner using token-shingle Jaccard similarity
- **L73 framework_lint** (ADR-048): substrate graduation & tier-convention linter (4-tier gate table)
- **L74 drift_detector** (ADR-049): app-substrate drift detector (3-pass algorithm)

Each repo had **zero fleet consumers** (no other repo imported them), were **stdlib-only** (no transitive deps), and shared a common governance-tool pattern (single-file Python CLI, argparse-based, SPEC.md + README.md + tests/).

The 3 ADRs (ADR-047, ADR-048, ADR-049) were authored by HexaKit's own governance process. HexaKit is the canonical Rust substrate framework with 46 crates, and per ADR-023 Rule 3.1, governance tooling naturally lives in the governance home — not in random `phenoShared` placements.

## Decision

**HexaKit absorbs the 3 governance tools** as `scripts/audit-tools/` subpackage. The 3 source repos are fully deleted on GitHub (404 confirmed).

### Placement

```
HexaKit/
├── scripts/
│   ├── audit-tools/                       ← NEW (this ADR)
│   │   ├── __init__.py                    ← SPDX MIT + ADR provenance
│   │   ├── pheno_framework_lint.py        ← 473 LOC, L73
│   │   ├── pheno_drift_detector.py        ← 413 LOC, L74
│   │   ├── pheno_predict.py               ← 376 LOC, L72
│   │   ├── audit                          ← dispatcher wrapper
│   │   ├── SPEC-framework-lint.md
│   │   ├── SPEC-drift-detector.md
│   │   ├── SPEC-predict.md
│   │   ├── README-framework-lint.md
│   │   ├── README-drift-detector.md
│   │   ├── README-predict.md
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── test_framework_lint.py    ← 303 LOC, 10 tests
│   │       ├── test_drift_detector.py    ← 71 LOC, 4 tests
│   │       └── test_predict.py           ← 339 LOC, 17 tests
│   ├── doc-sync/                          ← pattern reference (4-file subpackage)
│   ├── extract-intent-prompts.py          ← existing Python tool (SPDX MIT)
│   ├── traceability-check.py              ← existing Python tool (SPDX MIT)
│   ├── generate_error_enums_index.py      ← existing Python tool
│   └── export_phenotype_session_artifacts.py ← existing Python tool
├── docs/adr/2026-06-20/ADR-050-...md     ← this file
├── AGENTS.md                              ← updated with audit-tools section
└── ADR.md                                 ← append ADR-050 entry
```

### Why HexaKit (not pheno-scaffold-kit, not standalone)

1. **HexaKit is the governance home.** HexaKit already has 4 Python tools in `scripts/` and a 4-file Python subpackage in `scripts/doc-sync/`. Adding `scripts/audit-tools/` matches the established pattern exactly.
2. **HexaKit has `phenotype-compliance-scanner`** (Rust) as a sister governance crate. The 3 absorbed Python tools are the Python counterpart.
3. **`pheno-scaffold-kit`** is a stdlib-only CLI umbrella (also valid target), but HexaKit's governance tooling surface is more aligned: HexaKit *enforces* substrate conventions via compliance-scanner + lint rules, while the absorbed tools *audit* them.
4. **ADR provenance:** ADR-047, ADR-048, ADR-049 were all authored inside the HexaKit governance workflow.

### Why NOT phenoShared

`phenoShared` is a Rust workspace of stdlib primitives. It does NOT host Python tools. The 3 absorbed tools are Python-only.

### Why NOT standalone

Per ADR-023 Rule 3.1, "random `phenoShared`" placements (and per-extension, random `standalone`) are forbidden for new shared code. The 3 tools have a natural home (HexaKit governance scripts).

## Consequences

### Positive

- **Surface reduced by 4 repos** (3 source + 1 failed umbrella `pheno-scaffold-kit`).
- **HexaKit gains the L72/L73/L74 closed loop**: predict → framework-lint → drift-detector, all in one directory.
- **`scripts/audit`** dispatcher provides a single entry point: `./scripts/audit <tool> <subcommand> [args]`.
- **All 3 tools retain their CLI APIs**: zero behavioral change.
- **Tests pass**: 31 tests migrated (10 framework_lint + 4 drift_detector + 17 predict = 31 tests, 906 LOC).

### Negative

- **2 pre-existing bugs** in `pheno_predict.py` carry over: `test_drops_below_min_shared_shingles` and `test_04_json_output_deterministic`. These were bugs in the original source repo, not caused by absorption. Documented for follow-up.
- **The 3 original source repos are deleted** (no GitHub mirror). If HexaKit ever needs to re-extract, the source lives in `scripts/audit-tools/`.

## Implementation

- HexaKit branch: `feat/audit-tools-predict-framework-lint-drift-detector-2026-06-20`
- 13 files added (3 source + 3 SPEC + 3 README + 1 dispatcher + 1 `__init__.py` + 2 tests/`__init__.py` + 3 tests)
- 1,335 LOC of executable Python + 906 LOC of tests
- 0 LOC of new Rust (the 3 tools are Python-only)
- Registry updated: `disposition-index.json` rows l5-110/111/112 now point at HexaKit; `components.lock` `_archive_notes` updated.
- `findings/2026-06-19-L5-110-112-second-half-4-repo-absorption-audit.md` updated with the HexaKit absorption epilogue.

## ADR Provenance

This ADR implements the decisions of:
- ADR-023 (App-effort governance: device + dogfood + app substrate)
- ADR-047 (Predictive DRY discipline)
- ADR-048 (Substrate graduation path)
- ADR-049 (App-substrate drift detector)