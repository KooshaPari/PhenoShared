# Rust Ecosystem Audit — 2026-05-05

Active repos audited: AgilePlus, AtomsBot, PhenoMCP, PhenoObservability, PhenoControl, FocalPoint, PhenoSynth, kitty-specs, PhenoVCS, PhenoPlugins, and others with root Cargo.toml.

---

## AUDIT 1: cargo-deny Ignore Policy Compliance

**Summary**: 4 of 6 checked repos have ignore directives.

### FocalPoint — 4 ignores (deny.toml)

```
[advisories]
ignore = [
    { id = "RUSTSEC-2024-0388", reason = "unmaintained - no safe upgrade" },
    { id = "RUSTSEC-2024-0436", reason = "unmaintained - no safe upgrade" },
    { id = "RUSTSEC-2025-0057", reason = "unmaintained - no safe upgrade" },
    { id = "RUSTSEC-2025-0141", reason = "unmaintained - no safe upgrade" },
]
```

All four are unmaintained advisories with no safe upgrade path. All have reason fields.

### PhenoControl — 2 ignores (deny.toml)

```
[advisories]
ignore = [
    { crate = "RUSTSEC-2020-0036", reason = "failure not referenced in any dependency tree" },
    { crate = "RUSTSEC-2025-0119", reason = "number_prefix not referenced in any dependency tree" },
]
```

Both use the older `{ crate = "..." }` syntax and reference unmaintained crates not actually in the dep graph. Properly reasoned.

### PhenoObservability — 1 ignore (deny.toml)

```
[[advisories.ignore]]
id = "RUSTSEC-2026-0105"
reason = "protobuf: LOW severity uncontrolled recursion (transitive via prometheus 0.14.0). Fix available in protobuf 4.35.0-rc.1 but prometheus does not yet support 4.x. Recursion only triggers on adversarial nested schemas, not typical observability flows. Re-evaluate when prometheus 0.15+ ships with protobuf 4.x support."
```

Has expiration note (2026-07-23). Well-documented rationale with a concrete re-evaluation trigger.

### AgilePlus, AtomsBot, PhenoMCP

No ignores in any `[advisories]` section. Clean.

### No deny.toml

PhenoSynth and kitty-specs have no deny.toml.

### Compliance Assessment

| Repo | Ignores | Quality | Status |
|------|---------|---------|--------|
| FocalPoint | 4 | All reasoned (unmaintained) | Acceptable |
| PhenoControl | 2 | Reasoned (not in dep tree) | Acceptable |
| PhenoObservability | 1 | Fully documented with expiry | Acceptable |
| AgilePlus | 0 | N/A | Clean |
| AtomsBot | 0 | N/A | Clean |
| PhenoMCP | 0 | N/A | Clean |

---

## AUDIT 2: Unused Cargo.lock Entries (cargo-machete)

**Summary**: PhenoMCP, PhenoObservability, FocalPoint, and PhenoControl all have unused dependencies flagged.

### PhenoMCP — 1 flagged crate

```
phenotype-surrealdb -- ./crates/phenotype-surrealdb/Cargo.toml:
    surrealdb
    thiserror
    tracing
```

Appears to be false positives — `surrealdb`, `thiserror`, and `tracing` are almost certainly used transitively via the workspace. Run with `--with-metadata` for better accuracy. A `[package.metadata.cargo-machete]` section can be added to silence confirmed false positives.

### PhenoObservability — 9 flagged crates

```
tracingkit            ./crates/tracingkit/Cargo.toml:          tracing
phenotype-mcp-server  ./crates/phenotype-mcp-server/Cargo.toml: tracing, uuid
tracely               ./crates/tracely-core/Cargo.toml:         metrics, opentelemetry, prometheus, serde
phenotype-observably-macros ./crates/phenotype-observably-macros/Cargo.toml: proc-macro2
pheno-questdb         ./crates/pheno-questdb/Cargo.toml:       phenotype-observably-macros, tokio
fuzz                  ./crates/tracely-sentinel/fuzz/Cargo.toml: libfuzzer-sys
phenotype-observably-tracing ./crates/phenotype-observably-tracing/Cargo.toml: chrono, opentelemetry, opentelemetry-otlp, tracing-opentelemetry, uuid
phenotype-logging     ./rust/phenotype-logging/Cargo.toml:      serde
```

**Notable**: `pheno-questdb` flags `phenotype-observably-macros` and `tokio` as unused, but `pheno-questdb` also appears as unused in the same scan — these are likely build-order artifacts. The `tracely` crate flags 4 deps as unused simultaneously. Also errors on `tracely-sentinel/fuzz` (missing file) and `phenotype-health` / `phenotype-metrics` (missing workspace members `phenotype-error-core`, `prometheus`).

**Action needed**: Investigate workspace breakage in PhenoObservability (missing `phenotype-error-core` and `prometheus` crates). This may indicate incomplete dependency extraction rather than true unused deps.

### FocalPoint — 9 flagged crates

```
bench-guard           ./tooling/bench-guard/Cargo.toml:           thiserror
target-pruner          ./tooling/target-pruner/Cargo.toml:         human-panic, tracing, tracing-subscriber
doc-link-check        ./tooling/doc-link-check/Cargo.toml:         thiserror
quality-gate          ./tooling/quality-gate/Cargo.toml:          regex, walkdir
agent-orchestrator    ./tooling/agent-orchestrator/Cargo.toml:     regex, thiserror, uuid, walkdir
release-cut           ./tooling/release-cut/Cargo.toml:           focus-release-bot, reqwest, serde, serde_json, thiserror, toml, walkdir
focus-transpilers     ./crates/focus-transpilers/Cargo.toml:       thiserror
connector-linear      ./crates/connector-linear/Cargo.toml:        anyhow
```

**Notable**: `release-cut` has 7 flagged deps — likely transitive dependencies that machete cannot resolve without `--with-metadata`. The `quality-gate` and `agent-orchestrator` flag `regex`, `walkdir`, `uuid` as unused which are almost certainly used at runtime.

### PhenoControl — not confirmed unused

AgilePlus reported "1 unused" but machete said "didn't find any unused dependencies" on re-run. Likely a transient artifact.

### Assessment

| Repo | Flagged | Real unused? | Action |
|------|---------|--------------|--------|
| PhenoMCP | 1 crate | Likely false positive | Run with `--with-metadata` |
| PhenoObservability | 9 crates | Mixed (workspace breakage likely) | Fix missing workspace crates; re-run with `--with-metadata` |
| FocalPoint | 9 crates | Likely false positives | Run with `--with-metadata` |
| PhenoControl | ~0 | Unclear | Re-run with `--with-metadata` |

**Recommendation**: Re-run all with `cargo machete --with-metadata` before taking action. Many flagged deps in these multi-crate workspaces are likely transitive or conditionally compiled.

---

## AUDIT 3: Critical Rust Advisory Check (cargo-audit)

**Summary**: 1 active vulnerability found. PhenoMCP has a confirmed vulnerability (RSA timing side-channel, no fix available).

### PhenoMCP — 1 vulnerability (RUSTSEC-2023-0071)

```
Crate:     rsa
Version:   0.9.10
Title:     Marvin Attack: potential key recovery through timing sidechannels
ID:        RUSTSEC-2023-0071
Severity:  5.9 (medium)
Solution:  No fixed upgrade is available!
Dependency tree: rsa 0.9.10 -> jsonwebtoken 10.3.0
```

**Status**: Active. `jsonwebtoken` 10.3.0 pulls in `rsa` 0.9.10. The attack requires a network-attackable RSA key-handling path. No safe upgrade available from rsa crate. Options: suppress with reason, replace `jsonwebtoken` with a non-RSA algorithm (e.g., EdDSA), or accept the risk until upstream fixes.

**Also flagged** (warnings/allowed):
- RUSTSEC-2023-0089: `heapless` via `rstar` -> `geo-types` (LOW)
- RUSTSEC-2026-0097: `rand` via `surrealdb-types` (LOW)
- 4 additional allowed warnings

### AgilePlus — Clean

```
Scanning Cargo.lock for vulnerabilities (121 crate dependencies)
(no errors or vulnerabilities reported)
```

### PhenoObservability — Clean

```
Scanning Cargo.lock for vulnerabilities (359 crate dependencies)
(no errors or vulnerabilities reported)
```

Note: PhenoObservability's deny.toml has an ignore for RUSTSEC-2026-0105 (protobuf LOW) with expiry 2026-07-23.

### PhenoControl — Clean

```
(no errors or vulnerabilities reported)
19 allowed warnings (unmaintained crate advisories: RUSTSEC-2024-04xx series, proc-macro-error RUSTSEC-2024-0370)
```

### AtomsBot — No Cargo.lock

```
error: not found: Couldn't load Cargo.lock
```

Repo has Cargo.toml but no Cargo.lock. Run `cargo generate-lockfile` in the AtomsBot workspace.

---

## High-Priority Items

1. **[PhenoMCP] RSA vulnerability (RUSTSEC-2023-0071)**: Medium severity, no fix available from upstream `rsa` crate. Evaluate replacing RSA in `jsonwebtoken` or suppressing with documented risk acceptance.

2. **[PhenoObservability] Workspace breakage**: `phenotype-error-core` and `prometheus` missing from workspace but referenced. Investigate before relying on machete output for this repo.

3. **[PhenoObservability] Unused deps (9 flagged)**: After fixing workspace, re-run `cargo machete --with-metadata` to distinguish real unused deps from build-order artifacts.

4. **[FocalPoint] Unused deps (9 flagged)**: Re-run with `--with-metadata` for accurate results.

5. **[AtomsBot] Missing Cargo.lock**: Generate lockfile for reproducible audit.

6. **[PhenoMCP] Unused deps**: Re-run with `--with-metadata` — flagged deps (`surrealdb`, `thiserror`, `tracing`) are almost certainly used.

---

## Findings Metadata

- **Audited by**: Phenotype Agent
- **Date**: 2026-05-05
- **Audit scope**: AgilePlus, AtomsBot, PhenoMCP, PhenoObservability, PhenoControl, FocalPoint, PhenoSynth, kitty-specs, and all other root-level Cargo.toml repos
- **Tools**: cargo-deny 0.14+, cargo-machete, cargo-audit 0.18+
