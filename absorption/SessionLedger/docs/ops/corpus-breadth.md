# Corpus breadth (C08 L73) — production-scale OKF conformance

**Wave-44 close-out lane B6.**  
**Owner:** machine.  
**Theme:** scale the OKF conformance corpus from hand-vetted 20 → 33+ (and
growing) via a deterministic generator; close C08 L73 _production-scale corpus
breadth_.

Companion: [`WAVE44_SCOPE.md`](../../WAVE44_SCOPE.md) (rank 6) and
[`WAVE44_PERT.md`](WAVE44_PERT.md) (lane B6).

## Rubric anchor

Pillar L73 — _Microbench + Macrobench + Load Test_. SCORECARD headline:
`C08 L73 | partial (deepened)` with the residual being production-scale corpus
breadth. Wave-43 added the load-macro PR gate (`load-macro-gate-hard.yml`,
`load-smoke.ps1 -RouteTier macro`); Wave-44 grows the _input_ corpus so the
gate has broad coverage to exercise.

## Strategy

The corpus must grow along three orthogonal axes:

| Axis                                     | Why                                                                                                                                                     |
| ---------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Source agent**                         | Each agent (forge, codex, claude-code, cursor, aider, opencode, continue, kiro, factory-droid) emits different shapes — round-trip must hold across all |
| **Shape (entities / relations / depth)** | Stress the parser, the indexer, and the distiller at realistic and adversarial sizes                                                                    |
| **Edge / failure modes**                 | Verify the parser **rejects** malformed input rather than silently accepting it                                                                         |

Generator ([`scripts/corpus-generate.py`](../../scripts/corpus-generate.py))
produces one fixture per (source × shape × edge) cell. Hand-vetted fixtures
remain canonical; generated fixtures are machine-expansion.

## Current corpus (post-W44-B6)

```
docs/reference/conformance/fixtures/
├── 20 hand-vetted fixtures (W43 hand-curated, OKF-EXAMPLES.md siblings)
└── 13 generated fixtures (W44-B6, scripts/corpus-generate.py)
    ├── aider-rust-refactor-037           7 entities  /  6 relations
    ├── opencode-python-debugger-038       4 entities  /  3 relations
    ├── continue-go-microservice-039      6 entities  /  5 relations
    ├── kiro-bash-ci-pipeline-040         4 entities  /  3 relations
    ├── factory-droid-typescript-041       4 entities  /  3 relations
    ├── sql-migration-multi-intent-043    7 entities  /  7 relations
    ├── yaml-k8s-deployment-044           4 entities  /  3 relations
    ├── large-entity-count-100-045       82 entities  / 81 relations (stress)
    ├── deep-relation-graph-7-046         8 entities  /  7 relations (chain)
    ├── rapid-fire-intent-stream-12-047  12 entities  /  0 relations (no verifiers)
    ├── unicode-intent-label-cjk-048      3 entities  /  2 relations (CJK round-trip)
    ├── embedded-json-label-049           3 entities  /  2 relations (label escaping)
    └── multi-modal-image-hint-050        3 entities  /  2 relations (sha256 attachment)

Total: 33 accepted fixtures.
```

Failure-mode fixtures (`malformed-truncated-E01`, `missing-provenance-E02`,
`duplicate-id-E03`) live in a separate scratch directory and are not part of
the accepted corpus run; the harness is expected to reject them.

## Generator API

```bash
# Default accepted batch (33 → +13 new)
python3 scripts/corpus-generate.py --out docs/reference/conformance/fixtures

# Single fixture
python3 scripts/corpus-generate.py --out docs/reference/conformance/fixtures --only aider-rust-refactor

# Include failure-mode fixtures (rejected by harness)
python3 scripts/corpus-generate.py --out /tmp/scratch --include-failures

# Plan list (dry run)
python3 scripts/corpus-generate.py --list
```

Every emitted fixture is a valid OKF 1.0 document per
[`docs/reference/OKF-SPEC.md`](../reference/OKF-SPEC.md).

## Test wiring

The conformance roundtrip test
([`tests/okf_roundtrip.rs`](../../tests/okf_roundtrip.rs)) MUST iterate every
`*.okf.json` under `docs/reference/conformance/fixtures/` and assert:

- JSON parses
- `okf == "1.0"`
- `entities[]` ids are unique
- every relation source/target id resolves to an entity
- top-level `provenance` is present and has both `corpus` and `source_id`

The failure-mode fixtures (E01–E03) live in a separate directory and are wired
via a **negative** test that asserts the harness rejects them.

## Acceptance (W44-B6 close)

- [x] Generator emits 13 new accepted fixtures covering 5 new sources + 3 stress shapes + 3 edges
- [x] All accepted fixtures parse as JSON and validate against OKF 1.0 shape
- [x] Failure-mode fixtures generated and isolated
- [x] Corpus README in `docs/reference/conformance/README.md` updated
- [ ] Roundtrip test wired to walk the full 33-fixture set
- [ ] Negative test wired for E01–E03

## Risk register

| Risk                                                                | Mitigation                                                                    |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| Generator emits a malformed OKF that round-trip accepts by accident | Strict shape assertions in test; CI red on any shape break                    |
| Corpus file count bloats PR diff                                    | New fixtures land in a single batched PR; subsequent additions are small      |
| Generator script breaks when OKF spec evolves (e.g. v1.1)           | Builder functions keyed by `OKF_VERSION`; bump in one place                   |
| Performance regression: large fixtures slow the round-trip suite    | Mark large fixtures with `@pytest.mark.slow` / `#[ignore]` and run in nightly |

## Carry-over to W45+ (if W44-B6 only partially closes L73)

- Per-source corpus: 1 fixture per (source × language × toolchain) — 36 cells
- Stress: 500-entity fixture, 50-deep relation chain, 100-intent rapid-fire
- Edge: emoji label, RTL label, base64 attachment, deeply nested `properties`
- Adversarial: cyclic relation graph (currently illegal per spec — confirm), contradictory `verified_by`/`bounded_by`
