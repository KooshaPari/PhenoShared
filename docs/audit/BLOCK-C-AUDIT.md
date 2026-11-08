# Block-C Audit — <REDACTED>/phenokits-commons

**Date:** 2026-06-17  
**Auditor:** ecosystem disposition wave (Lane C)  
**Charter:** [`phenotype-registry/docs/rationalization/boundary-shaping.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/boundary-shaping.md)  
**Absorption gate:** PhenoKits → phenokits-commons PR [#3](https://github.com/KooshaPari/phenokits-commons/pull/3) merged (100% path parity)

---

## Executive summary

| Signal | Finding |
|--------|---------|
| **Repo role** | Scaffold commons — governance templates, parameterized configs, per-repo test harnesses, polyglot reference libs |
| **Boundary lock** | **ACTIVE** after this audit — not a domain SDK warehouse |
| **PhenoKits absorption** | **COMPLETE** — `docs/absorption/PHENOKITS_GAP_PORT.md` |
| **PhenoProc governance port** | **COMPLETE** — `governance/phenoproc-*` from PR #3 |
| **Primary risk** | Legacy `libs/{go,typescript}` domain kits still co-located; README still describes retired python-sdk monorepo layout |
| **Recommended action** | Publish disposition + fleet bootstrap spec; relocate domain libs per table in `docs/boundary/DISPOSITION.md` |

---

## Baseline checks

| Check | Result | Notes |
|-------|--------|-------|
| PhenoKits path parity (excl. `.github/`, redirected `libs/python`) | **PASS** | 84 files in PR #3 |
| `governance/phenoproc-templates/` present | **PASS** | CI + Rust integration scaffolds |
| `governance/phenoproc-configs/` present | **PASS** | Per-language lint/format configs |
| Root `Cargo.toml` workspace members | **PASS (intentional empty)** | Virtual umbrella; no compiled crates at root |
| `HexaKit/` git submodule | **WARN** | Pointer only; shallow clones may not init — consumers should use `<REDACTED>/HexaKit` directly |
| `Tracera/` | **QUARANTINE** | Empty placeholder; row-level disposition in `worklogs/` |
| `README.md` accuracy | **FAIL** | Still documents `phenotype-python-sdk` / `phenotype-go-sdk` monorepo sections from pre-split era |
| Domain lib concentration | **WARN** | `libs/go/*` (7 pkgs), `libs/typescript/*` (3 pkgs) belong in language SDK repos |

---

## 12-category inventory (artifact taxonomy)

Aligned with `docs/RESTRUCTURING_PLAN.md` and root `Cargo.toml` comments.

| # | Category | Path | File density | Boundary verdict |
|---|----------|------|--------------|------------------|
| 1 | Templates | `templates/` | Medium | **Split** — test/CI scaffolds stay; project generators → HexaKit |
| 2 | Configs | `configs/` | High | **Keep** — parameterized copy-source |
| 3 | Libs | `libs/` | Medium | **Relocate** — SDK monorepos except polyglot `phenotype-id` |
| 4 | Secrets | `secrets/` | Stub | **Keep** — patterns only, no secret material |
| 5 | Governance | `governance/` | High | **Keep** — fleet bootstrap SSOT |
| 6 | Security | `security/` | Stub | **Keep** — scanning templates TBD |
| 7 | Observability | `observability/` | Stub | **Keep** — OTel bootstrap deferred (#4 in cross-project audit) |
| 8 | Documentation | `docs/` | High | **Keep** — absorption records + boundary docs |
| 9 | Scripts | `scripts/` | Low | **Keep** |
| 10 | Schemas | `schemas/` | Low | **Keep** — config param schemas |
| 11 | Policies | `policies/` | Stub | **Keep** — OPA/GitHub policy templates TBD |
| 12 | Credentials | `credentials/` | Stub | **Keep** — auth pattern docs only |

---

## Cross-repo boundary overlaps

| Concern | Also present in | Canonical owner | phenokits-commons role |
|---------|-----------------|-----------------|------------------------|
| Project `template-*` generators | HexaKit | **HexaKit** | Reference copies + hexagon doc kit only |
| Org reusable CI workflows | `<REDACTED>/.github` | **phenotype-org-governance** | Copy-source templates under `configs/cicd/` |
| Python domain kits | `phenotype-python-sdk` | **phenotype-python-sdk** | Redirect manifest in `libs/python/README.md` |
| Go domain kits | `phenotype-go-sdk` | **phenotype-go-sdk** | Relocate `libs/go/*` (except shared polyglot id) |
| Spec lifecycle (`agileplus specify`) | AgilePlus | **AgilePlus** | Consumes templates from `governance/phenoproc-*` |
| Boundary + DAG SSOT | phenotype-registry | **phenotype-registry** | Cited, not duplicated |

---

## Blockers resolved by PR #3

- [x] PhenoKits root validation tests → `tests/`
- [x] Polyglot `phenotype-id` → `libs/{go,python,typescript}/phenotype-id/`
- [x] Docsite + template Playwright harnesses → `docs/tests/`, `templates/*/docs/tests/`
- [x] Hexagon CI workflows → `hexagon/.github/workflows/`
- [x] Webapp template CI scaffold → `templates/webapp/.github/`
- [x] PhenoProc governance templates → `governance/phenoproc-*`

---

## Open items (post-audit execution)

| ID | Priority | Item | Owner doc |
|----|----------|------|-----------|
| BC-1 | P0 | Publish `docs/boundary/DISPOSITION.md` | This PR |
| BC-2 | P0 | Publish `governance/GOVERNANCE-TEMPLATE-FLEET-DEFAULTS.md` | This PR |
| BC-3 | P1 | Trim README to commons scope (remove SDK monorepo sections) | Follow-up PR |
| BC-4 | P1 | Relocate `libs/go/*` → `phenotype-go-sdk` | SDK repo PR |
| BC-5 | P1 | Relocate `libs/typescript/*` → `phenotype-ts-sdk` | SDK repo PR |
| BC-6 | P2 | Remove or document `HexaKit/` submodule (prefer direct dep) | Follow-up |
| BC-7 | NB | Tracera quarantine row disposition | `worklogs/` |

---

## Success criteria (Lane C acceptance)

1. `docs/boundary/DISPOSITION.md` on default branch with every top-level module assigned disposition + target owner
2. Fleet bootstrap spec documents `governance/phenoproc-*` as default copy-on-init source
3. PhenoKits archive can remain **KEEP_ARCHIVED** with 100% absorption evidence
