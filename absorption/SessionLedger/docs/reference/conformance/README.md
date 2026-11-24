# OKF Conformance Corpus

> **Companion to:** [`../OKF-SPEC.md`](../OKF-SPEC.md) (v1.0) and
> [`../OKF-EXAMPLES.md`](../OKF-EXAMPLES.md) (worked examples).
> **Purpose:** canonical, hand-vetted OKF documents that consumers (parsers,
> validators, renderers) can run through their own code to verify they
> handle every shape the spec promises.

---

## Layout

```
docs/reference/conformance/
├── README.md             ← this file
└── fixtures/
    ├── auth-fix-session-001.okf.json       ← example §2 (auth-fix, forge)
    ├── billing-session-003.okf.json        ← example §3 (billing, codex)
    ├── arm-ci-runner-007.okf.json          ← example §4 (ARM CI, claude-code)
    ├── minimal-session-042.okf.json        ← example §5 (minimal, forge)
    ├── multi-intent-088.okf.json           ← example §6 (multi-intent, forge)
    ├── empty-intent-002.okf.json           ← edge: blank intent label
    ├── cursor-refactor-011.okf.json        ← cursor corpus shape
    ├── blank-entities-099.okf.json         ← edge: empty entities[]
    ├── context-grounds-004.okf.json        ← explicit grounds relations
    ├── factory-delegate-015.okf.json     ← factory-droid delegated refactor
    ├── tool-evidence-021.okf.json          ← claude-code tool-output acceptance
    ├── codex-typescript-023.okf.json       ← codex TypeScript/npm toolchain acceptance
    ├── cursor-python-029.okf.json          ← cursor Python pytest tool evidence
    ├── forge-go-module-026.okf.json        ← forge Go module gRPC health probe
    ├── task-family-multiturn-031.okf.json  ← multi-turn discover/compress/verify family
    ├── task-family-token-budget-032.okf.json ← token-budget / metrics family
    ├── task-family-compress-resume-033.okf.json ← zstd compress → resume family
    ├── compress-token-proxy-034.okf.json   ← bytes_saved / rough_tokens_saved proxy
    ├── token-slice-budget-035.okf.json     ← per-slice CharCountTokenEstimator budget
    └── archive-gzip-resume-036.okf.json    ← gzip archive → resume / rehydrate family
```

Twenty fixtures total — five from worked examples in `OKF-EXAMPLES.md` plus
fifteen hand-vetted edge, corpus-expansion, cross-language, task-family, and
compression/token-oriented shapes. Example fixtures are the
**exact JSON shown in the examples doc** (verbatim, byte-for-byte except for
trailing whitespace). Anchored filenames are pinned in
[`docs/ops/eval-manifest.json`](../../ops/eval-manifest.json).

---

## What "conformance" means

A consumer (parser, validator, renderer) is conformant to OKF v1.0 if, for
every fixture in this corpus, it:

1. **Parses** the document without errors.
2. **Round-trips** it through `serde_json::from_str → to_string_pretty`
   producing a value-equal document (modulo property ordering).
3. **Validates** against the structural rules in `OKF-SPEC.md` §3-§6:
   - `okf` field equals `"1.0"`.
   - Every relation's `source` and `target` ids exist in `entities[]`.
   - Every entity `type` is in the v1.0 table (or treated as opaque).
   - Every relation `type` is in the v1.0 table (or treated as opaque).
   - Document-level `provenance.source_id` equals top-level `source_id`.
4. **Renders** the document with at least the canonical text fields
   (`label`, `source_id`, key relation `type`) shown to the user.

---

## Adding a new fixture

1. **Identify the gap.** Find a SessionLedger output shape that is NOT
   covered by the existing five fixtures. Likely candidates:
   - A new entity or relation type that the spec introduces (requires a
     minor-version bump first; see `OKF-SPEC.md` §13).
   - A corpus other than forge / codex / claude-code (e.g. cursor).
   - An edge case in the heuristic extractors (e.g. session where the
     intent extractor finds no goal).

2. **Add the source example** to `OKF-EXAMPLES.md`. The new section MUST:
   - Reference the source session.
   - Show the expected JSON shape.
   - Document any conformance subtleties (e.g. omitted relations, missing
     `properties`, multi-intent split).

3. **Commit the fixture** as `<source_id>.okf.json` under `fixtures/`.
   Filename MUST match the document's `source_id`. The file MUST be the
   exact bytes shown in the examples doc.

4. **Add a conformance test** to `session-ledger/tests/conformance.rs`
   (or whichever crate owns conformance). The test loads the fixture,
   round-trips it, and asserts structural validity. Name the test after
   the fixture stem (e.g. `conformance::billing_session_003`).

5. **Bump the fixture count** in this README's "Layout" block above and
   in `OKF-SPEC.md` §14 ("Concrete Examples").

---

## Running the corpus

```sh
# Inside the session-ledger workspace
cargo test -p session-ledger --features okf-conformance -- conformance
```

(The `okf-conformance` feature is a placeholder; SessionLedger does not yet
gate this in `Cargo.toml`. Adding the feature flag is tracked under the
spec conformance milestone — see `CHANGELOG.md`.)

For consumers in other languages, the simplest harness is:

```rust
// pseudo-code
let raw = std::fs::read_to_string("fixtures/auth-fix-session-001.okf.json")?;
let doc: OkfDocument = serde_json::from_str(&raw)?;

// Validate
assert_eq!(doc.okf, "1.0");
for r in &doc.relations {
    assert!(doc.entities.iter().any(|e| e.id == r.source));
    assert!(doc.entities.iter().any(|e| e.id == r.target));
}
assert_eq!(doc.provenance.source_id, doc.source_id);

// Round-trip
let round = serde_json::to_string_pretty(&doc)?;
let parsed: OkfDocument = serde_json::from_str(&round)?;
assert_eq!(doc, parsed);
```

Equivalent TypeScript / Python / Go consumers should perform the same three
steps.

---

## Stability guarantee

The corpus is **append-only**:

- Existing fixtures are NEVER edited in place (only deleted if a major
  version bump makes them obsolete).
- New fixtures ONLY add to the corpus; they never replace or invalidate
  older ones.
- Fixture filenames are stable identifiers — downstream consumers can pin
  to a specific filename forever.

A fixture MAY be **deprecated** (renamed `*.deprecated.okf.json`) when a
newer example supersedes it, but the old file remains in git history and
is referenced from the examples doc.

---

_End of OKF Conformance Corpus README._

---

## Wave-44-B6 generator-produced fixtures (W44 close-out, C08 L73)

The 13 fixtures below were generated by [`scripts/corpus-generate.py`](../../scripts/corpus-generate.py)
as part of the Wave-44 close-out lane B6 (production-scale corpus breadth).
They exercise dimensions not covered by the 20 hand-vetted fixtures above:

| Fixture                                    | Source        | Stress / coverage                                       |
| ------------------------------------------ | ------------- | ------------------------------------------------------- |
| `aider-rust-refactor-037.okf.json`         | aider         | rust refactor; trait-bound removal with 6-relation gate |
| `opencode-python-debugger-038.okf.json`    | opencode      | async iterator trace; stdlib-only constraint            |
| `continue-go-microservice-039.okf.json`    | continue      | /healthz/ready + circuit breaker (5-relation chain)     |
| `kiro-bash-ci-pipeline-040.okf.json`       | kiro          | GitHub Actions commit-SHA pinning                       |
| `factory-droid-typescript-041.okf.json`    | factory-droid | retry-aware telemetry client with bundle-size cap       |
| `sql-migration-multi-intent-043.okf.json`  | forge         | 3-intent ALTER TABLE migration w/ ONLINE constraint     |
| `yaml-k8s-deployment-044.okf.json`         | forge         | rollingUpdate maxUnavailable=0 under PDB                |
| `large-entity-count-100-045.okf.json`      | forge         | 82 entities / 81 relations (stress)                     |
| `deep-relation-graph-7-046.okf.json`       | forge         | 8 entities / 7-relation deep chain (transitive closure) |
| `rapid-fire-intent-stream-12-047.okf.json` | forge         | 12 intents, no verifiers (open-loop stream)             |
| `unicode-intent-label-cjk-048.okf.json`    | forge         | CJK unicode label; zh-CN locale hint                    |
| `embedded-json-label-049.okf.json`         | forge         | JSON-snippet inside label (XSS / escape verification)   |
| `multi-modal-image-hint-050.okf.json`      | claude-code   | sha256 image attachment (no embedded bytes)             |

Total corpus (post-W44-B6): 33 accepted fixtures.

Regenerate via:

```bash
python3 scripts/corpus-generate.py --out docs/reference/conformance/fixtures
```

See [`docs/ops/corpus-breadth.md`](../../docs/ops/corpus-breadth.md) for the
strategy doc, failure-mode fixtures (E01–E03), and the test wiring plan.
