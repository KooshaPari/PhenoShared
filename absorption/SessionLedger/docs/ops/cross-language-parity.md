# Cross-language OKF fixture parity (SSOT)

Status: **C08 L75 expanded** — OKF conformance fixtures stay aligned across
programming-language shapes already present in the corpus (Python, TypeScript,
Go), plus a thin structural-invariant harness and a **language-agnostic OKF
adapter interface** with Python, TypeScript, and Go reference implementations that can
validate/emit non-Rust fixture paths. This is **fixture + structural + adapter
stub** evidence, not a multi-language runtime SDK and **not** Harbor / agent-eval.

Related: [`docs/EVAL_SCOPE.md`](../EVAL_SCOPE.md) (eval boundary),
[`docs/reference/conformance/README.md`](../reference/conformance/README.md)
(corpus layout), [`eval-manifest.json`](eval-manifest.json) (fixture anchors),
[`OKF-SPEC.md`](../reference/OKF-SPEC.md) (structural rules),
[`adapters/README.md`](../../adapters/README.md) (adapter interface).

## What "parity" means here

For each language row in the matrix below, SessionLedger maintains at least one
hand-vetted `.okf.json` fixture whose `source_id` (and filename stem) embeds a
stable **language tag**. Consumers that parse OKF in any host language should
be able to load these fixtures and apply the same conformance checks described
in the corpus README (parse → validate → round-trip).

Beyond tag presence, the SelfCheck **structural invariant harness** parses each
matrix fixture and asserts the same OKF v1.0 core invariants (version, ids,
required entity types, relation endpoints, provenance alignment). That is a
thin cross-language check over fixtures.

Wave-33 added a documented **adapter stub**: a language-agnostic
`load` / `validate` / `emit` contract plus a Python reference CLI. Wave-35 adds
a matching **Go** stdlib CLI beside Python; Wave-36 adds a **TypeScript** Node
stdlib CLI (still not a shipped SDK).

Parity does **not** require:

- Full native Python / TypeScript / Go SessionLedger ports or package releases
- Per-language agent harnesses or Harbor env providers
- Identical toolchains or acceptance-command strings across fixtures

## Parity matrix

| Language   | Tag (in `source_id`) | Anchor fixture                                                                                     | Corpus | Notes                              |
| ---------- | -------------------- | -------------------------------------------------------------------------------------------------- | ------ | ---------------------------------- |
| Python     | `python`             | [`cursor-python-029.okf.json`](../reference/conformance/fixtures/cursor-python-029.okf.json)       | cursor | pytest / mypy acceptance labels    |
| TypeScript | `typescript`         | [`codex-typescript-023.okf.json`](../reference/conformance/fixtures/codex-typescript-023.okf.json) | codex  | npm / eslint acceptance labels     |
| Go         | `go`                 | [`forge-go-module-026.okf.json`](../reference/conformance/fixtures/forge-go-module-026.okf.json)   | forge  | `go test` / gRPC health acceptance |

These three fixtures are also pinned in [`eval-manifest.json`](eval-manifest.json)
`fixture_anchors`. Additional languages may be appended later; do not remove
rows without a major corpus decision.

### Fixture language-tag rule

For every matrix row:

1. File exists under `docs/reference/conformance/fixtures/<source_id>.okf.json`.
2. Top-level JSON `source_id` equals the filename stem.
3. `source_id` contains the language **tag** substring from the matrix
   (case-sensitive: `python`, `typescript`, or `go`).
4. Document-level `provenance.source_id` matches top-level `source_id` when
   provenance is present (OKF v1.0 structural rule).

## Structural invariant harness

`scripts/cross-language-parity-check.ps1` compares OKF structural invariants
across the matrix fixtures (hermetic JSON parse; no language runtimes):

| Invariant              | Rule                                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------ |
| Dialect                | Top-level `okf` is `"1.0"` on every row                                                                      |
| Identity               | `source_id` equals filename stem; `provenance.source_id` matches                                             |
| Entities               | Non-empty; unique `id`; each entity has `type` + non-empty `label`                                           |
| Shared core types      | Every row includes `intent`, `acceptance`, `constraint`, `resource`, `state`, `gate`                         |
| Relations              | Non-empty; `source`/`target` resolve to entity ids; type ∈ v1.0 set; relation `provenance.source_id` matches |
| Cross-lang fingerprint | Sorted shared-core type set is identical across Python / TypeScript / Go                                     |

Optional entity types (e.g. TypeScript `criteria`) may differ per language row;
only the shared core fingerprint must match. This harness is the Wave-32
expansion beyond fixture-tag SSOT toward consumer-facing structural parity.

## Native language adapter stub

Language-agnostic contract (see [`adapters/README.md`](../../adapters/README.md)):

| Operation       | Role                                                  |
| --------------- | ----------------------------------------------------- |
| `load(path)`    | Read UTF-8 OKF JSON                                   |
| `validate(doc)` | Enforce the same v1.0 structural rules as the harness |
| `emit(doc)`     | Pretty-print validated OKF JSON                       |

Reference implementations (stdlib only):

| Path                                                                             | CLI                                                       |
| -------------------------------------------------------------------------------- | --------------------------------------------------------- |
| [`adapters/python/okf_adapter.py`](../../adapters/python/okf_adapter.py)         | `validate` / `emit` against a fixture path                |
| [`adapters/typescript/okf_adapter.ts`](../../adapters/typescript/okf_adapter.ts) | `validate` / `emit` via `node --experimental-strip-types` |
| [`adapters/go/main.go`](../../adapters/go/main.go)                               | `validate` / `emit` against a fixture path (`go run .`)   |

SelfCheck always verifies Python, TypeScript, and Go adapter sources and runs the
Python adapter against `cursor-python-029.okf.json`. When Node ≥22 is installed
it also runs the TypeScript adapter against `codex-typescript-023.okf.json`;
when `go` is installed it runs the Go adapter against `forge-go-module-026.okf.json`;
otherwise TypeScript/Go execute steps are explicit skips while hermetic doc/source
anchors still pass.

## Explicit non-goals

| Item                                      | Status           | Rationale                                                  |
| ----------------------------------------- | ---------------- | ---------------------------------------------------------- |
| Harbor / Portage / Terminal-Bench         | **N/A**          | Product boundary — see [`EVAL_SCOPE.md`](../EVAL_SCOPE.md) |
| Multi-env agent scoring                   | **N/A**          | SessionLedger is ingest → distill → OKF → view             |
| Shipping language SDKs / package releases | **out of scope** | Adapter stub + fixture/SSOT evidence only                  |

## Done gates

| Gate                            | Status   | Command                                              |
| ------------------------------- | -------- | ---------------------------------------------------- |
| Cross-language parity SelfCheck | **done** | `scripts/cross-language-parity-check.ps1 -SelfCheck` |

## Machine verification (SelfCheck)

Hermetic doc + fixture path + structural harness + Python/Go/TypeScript adapter stub check
(no daemon, no network, no cargo; uses host `python`/`python3` stdlib; optional
host `go` and Node ≥22 `--experimental-strip-types`):

```powershell
pwsh ./scripts/cross-language-parity-check.ps1 -SelfCheck
```

`-SelfCheck` asserts this page keeps the parity matrix, language-tag rule,
structural invariant harness section, native language adapter stub section,
EVAL_SCOPE / Harbor N/A boundary, that each matrix fixture exists with a
matching `source_id` language tag, that the structural harness finds an
identical shared-core fingerprint across rows, that the Python reference
adapter validates and emits the Python fixture, and that Go and TypeScript adapter
sources exist (with runtime `go run` / Node when available). `tests/cross_language_parity.rs`
wraps the same command for optional `cargo test` proof.

CI: [`.github/workflows/eval-compression.yml`](../../.github/workflows/eval-compression.yml)
runs the SelfCheck on PR/push (blocking, hermetic).
