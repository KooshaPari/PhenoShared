# L5-118 — pheno → HexaKit merge completion confirmation (2026-06-19)

**Scope:** v9 plan §1.2 Action 2 (ECOSYSTEM_MAP §6 P0) — "Merge pheno → HexaKit (remove 21 duplicate crate copies)"
**Status:** **MERGE COMPLETE PRE-v9** (3 prior waves: Phase 3, Phase 4 wave 5, Phase 4 wave 5b)
**Verdict:** **NO-OP for v9** — only ADR-057 + this confirmation note needed
**Full report:** `findings/2026-06-19-L5-118-EXECUTION-STATUS.md`

---

## 0. Premise correction (v9 plan §1.2 was based on stale state)

| v9 §1.2 premise | Reality (2026-06-19) |
|---|---|
| `<REDACTED>/pheno` is LIVE; "TO ARCHIVE post-migration" | `<REDACTED>/pheno` is **ALREADY ARCHIVED** (`gh api` returns `"archived": true`, last push `2026-06-19T08:12:10Z`) |
| "21 duplicate crate copies" need to be migrated | 19/22 pheno WS members are **already in HexaKit's `exclude` list** with explicit canonical owners; the 2 remaining (phenotype-error-macros, phenotype-port-traits) are intentional HexaKit scaffolds; 2 (agileplus-nats, phenotype-retry) are pheno-only and deferred to v10 |
| 3-5 absorbing PRs needed | 0 absorbing PRs needed — all 19 canonicalized duplicates are at `fsm: "done"` in the registry with PR references |

---

## 1. The 21 "duplicates" — actual categorization

| # | pheno crate | Canonical substrate | HexaKit status | Registry row | fsm | Terminal PR |
|---|---|---|---|---|---|---|
| 1 | `phenotype-async-traits` | phenotype-rust-sdk | exclude | id=3 | done | `phenotype-rust-sdk@cbf1ccf`, `HexaKit#278` |
| 2 | `phenotype-cache-adapter` | HexaKit (libs stub) | exclude | n/a (stub) | stub | `HexaKit#264` |
| 3 | `phenotype-casbin-wrapper` | Authvault | exclude | n/a | done | `Authvault` git pin wave 5b |
| 4 | `phenotype-contract` | TestingKit | exclude | id=10 | done | `TestingKit#9`, `HexaKit#271` |
| 5 | `phenotype-contracts` | phenotype-rust-sdk (generic) + role workspaces (slices) | exclude | id=11 | done | `HexaKit#264` + multi-tenant decompose (Authvault#88, Eventra#19#20, Agentora#92#93, ResilienceKit#2#3, phenotype-python-sdk#22#24#25, Pyron#61) |
| 6 | `phenotype-error-core` | phenotype-types | exclude | id=18 (shared with errors) | done | `phenotype-types#1`, `HexaKit#267` |
| 7 | `phenotype-error-macros` | **HexaKit scaffold** (intentional co-existence) | members | n/a | n/a | n/a |
| 8 | `phenotype-errors` | phenotype-types | exclude | id=18 | done | `phenotype-types#1`, `HexaKit#267` |
| 9 | `phenotype-event-sourcing` | Eventra | exclude | n/a | done | `Eventra#21` wave 5b |
| 10 | `phenotype-health` | ResilienceKit | exclude | id=22 | done | `HexaKit#261`, `HexaKit#278` |
| 11 | `phenotype-http-client-core` | phenotype-resilience | exclude | id=23 | done | `phenoShared#177` (wave D) |
| 12 | `phenotype-iter` | phenotype-types | exclude | n/a | done | `phenotype-types` wave 5b |
| 13 | `phenotype-policy-engine` | ResilienceKit | exclude | n/a | done | `ResilienceKit` wave 5b |
| 14 | `phenotype-port-traits` | **HexaKit scaffold** (intentional co-existence) | members | id=30 | done | `HexaKit#266` |
| 15 | `phenotype-state-machine` | ResilienceKit | exclude | n/a | done | `ResilienceKit` wave 5b |
| 16 | `phenotype-string` | phenotype-types | exclude | n/a | done | `phenotype-types` wave 5b |
| 17 | `phenotype-telemetry` | PhenoObservability | exclude | id=39 | done | `HexaKit#271` |
| 18 | `phenotype-test-infra` | TestingKit | exclude | id=40 | done | `TestingKit#7`, `HexaKit#264` |
| 19 | `phenotype-test-fixtures` | TestingKit | exclude | id=41 | done | `HexaKit#271` |
| 20 | `phenotype-time` | phenotype-types | exclude | n/a | done | `phenotype-types` wave 5b |
| 21 | `phenotype-validation` | phenotype-types | exclude | n/a | done | `phenotype-types` wave 5b |

**The 21 = 19 canonicalized + 2 scaffolds (intentional co-existence). All 19 canonicalized are `fsm: "done"`.**

### Pheno-only (NOT in HexaKit) — deferred to v10

- `agileplus-nats` (row 1) — AgilePlus workspace bridge, out of scope for pheno→HexaKit
- `phenotype-retry` (row 16 in pheno members) — no canonical owner declared; candidate for ResilienceKit in v10

---

## 2. The 3 waves that already completed the migration

1. **Phase 3 (2026-06-17 → 18)**: HexaKit `exclude` + git pin initial pass — see `docs/migrations/phase3-wave-ab-prune-2026-06-18.md`, `wave9/wave10/wave11/wave12/wave13-*.md`; PRs `HexaKit#264, #267, #271, #272`
2. **Phase 4 wave 5 (2026-06-19 07:49:45Z)**: config-core git pin + stub prune — `HexaKit#276`, see `docs/migrations/phase4-wave5-eviction-2026-06-19.md`
3. **Phase 4 wave 5b (2026-06-19 08:28:09Z)**: drain remaining 12 phenoShared git pins to terminal owners — `HexaKit#278`, see `docs/migrations/wave5-phenoshared-pin-drain-2026-06-19.md` ← **THE TERMINAL MIGRATION PR**

---

## 3. Verification

```bash
# Registry: all 19 canonicalized duplicates at fsm=done
$ grep -A 2 '"path": "crates/phenotype-' phenotype-registry/registry/disposition-index.json \
  | grep -E '"fsm"|"path"' | grep -B 1 '"done"' | wc -l
19

# HexaKit: 19 pheno crates in exclude with canonical owner comments
$ awk '/^exclude = \[/,/^\]/' HexaKit/Cargo.toml \
  | grep -E '"crates/phenotype-' | wc -l
19

# pheno: ALREADY ARCHIVED on GitHub
$ gh api /repos/<REDACTED>/pheno | jq -r '.archived'
true
```

---

## 4. Outstanding v9 work (deferred)

- **ADR-057** (recommended) — `docs/adr/2026-06-19/ADR-057-pheno-hexakit-merge-completion.md` — 1-page "merge COMPLETE" ADR that supersedes v9 §1.2 Action 2 narrative
- **Registry `repo-pheno` row** (optional, P3 cosmetic) — add a row for the pheno repo itself, not just the per-crate rows
- **2 pheno-only crates** (P3) — `agileplus-nats` and `phenotype-retry` deferred to v10

**Total v9 effort for Action 2: ~10 min orchestrator-direct** (vs the 120-180 min v9 plan §1.2 estimated).

---

**Author:** Orchestrator (L5-118)
**Cross-references:** `findings/2026-06-19-L5-118-EXECUTION-STATUS.md` (full report), ADR-014 (hexagonal ports), ADR-022 (Configra canonical), ADR-038 (L4 policy)
