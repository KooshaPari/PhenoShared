# Absorption index

Canonical index of archived repos absorbed or retired into the Phenotype platform layer. Each entry links to a disposition README under `docs/absorbed-from/<repo>/`.

## Wave G19 (2026-06-18)

Registry wave G19 stub absorption — owner repo: **phenotype-infra**. Registry ledger: `phenotype-registry` wave15 execution doc (`docs/operations/wave15-execution-2026-06-17.md`).

| Repo | Disposition | Absorption README | Worklog ref | Notes |
|------|-------------|-------------------|-------------|-------|
| [phenotype-hub](https://github.com/KooshaPari/phenotype-hub) | ABSORB | [docs/absorbed-from/phenotype-hub/README.md](absorbed-from/phenotype-hub/README.md) | L5-111 | Governance scaffold docs; canonical owner is this repo. P8 in `phenotype-registry/ECOSYSTEM_MAP.md` §6. |
| [vibeproxy-monitoring-unified](https://github.com/KooshaPari/vibeproxy-monitoring-unified) | RETIRE | [docs/absorbed-from/vibeproxy-monitoring-unified/README.md](absorbed-from/vibeproxy-monitoring-unified/README.md) | L5-111 | Empty stub; pointer to [cliproxyapi-plusplus VIBEPROXY_ABSORPTION](https://github.com/KooshaPari/cliproxyapi-plusplus/blob/main/docs/VIBEPROXY_ABSORPTION.md). P9 in `phenotype-registry/ECOSYSTEM_MAP.md` §6. |

## Sprawl consolidation wave (2026-09-27)

Repo-sprawl reduction wave — owner repo: **PhenoShared (phenoAI)**. Five standalone repos absorbed as plain copies under `absorption/<repo>/`, each with a `PROVENANCE.md`.

| Repo | Disposition | Absorption README | Worklog ref | Notes |
|------|-------------|-------------------|-------------|-------|
| [phenotype-canonicalization](https://github.com/KooshaPari/phenotype-canonicalization) | ABSORB | [docs/absorbed-from/phenotype-canonicalization/README.md](absorbed-from/phenotype-canonicalization/README.md) | SPR-01 | Agent-authored canonicalization docs/audit, 44 files. Source left unarchived pending operator confirmation. |
| [phenotype-cvp-audit-2026-09-14](https://github.com/KooshaPari/phenotype-cvp-audit-2026-09-14) | ABSORB | [docs/absorbed-from/phenotype-cvp-audit-2026-09-14/README.md](absorbed-from/phenotype-cvp-audit-2026-09-14/README.md) | SPR-02 | One-off dated CVP audit deliverable, 6 files. Source left unarchived pending operator confirmation. |
| [phenoDesign-visual-production-v2](https://github.com/KooshaPari/phenoDesign-visual-production-v2) | ABSORB | [docs/absorbed-from/phenoDesign-visual-production-v2/README.md](absorbed-from/phenoDesign-visual-production-v2/README.md) | SPR-03 | Distinct from the governed `phenoDesign` design-system repo. Source left unarchived pending operator confirmation. |
| [PhenoMLX-temp](https://github.com/KooshaPari/PhenoMLX-temp) | ABSORB | [docs/absorbed-from/PhenoMLX-temp/README.md](absorbed-from/PhenoMLX-temp/README.md) | SPR-04 | Temp snapshot; ~646 MB `.cargo-target/` excluded. Canonical source is live `KooshaPari/PhenoMLX`. GitHub repo `KooshaPari/PhenoMLX-temp` is archived. |
| [PhenoInfra](https://github.com/KooshaPari/PhenoInfra) | ABSORB | [docs/absorbed-from/PhenoInfra/README.md](absorbed-from/PhenoInfra/README.md) | SPR-05 | Compute/infra monorepo snapshot; not wired into root workspace. Source repo already archived. |

## Vendored-off-Go-tool disposition wave (2026-10-29)

Vendored-copy disposition pass for a Go tool absorbed outside the `absorption/` flow — owner repo: **PhenoShared (phenoAI)**. Entry recorded so the tree is permanently excluded from CI and from future module sweeps.

| Repo | Disposition | Absorption README | Worklog ref | Notes |
|------|-------------|-------------------|-------------|-------|
| [zz-merge-unk-hfscope](https://github.com/KooshaPari/zz-merge-unk-hfscope) | EXCLUDE | [docs/absorbed-from/hfscope/README.md](absorbed-from/hfscope/README.md) | HF-01 | Vendored at `hfscope/` (not `absorption/`); `PROVENANCE.md` declares absorption into PhenoMLX, yet the copy lives here. **Both upstreams deleted** (`KooshaPari/hfscope`, `KooshaPari/zz-merge-unk-hfscope` → "Repository not found"). Absorption incomplete: `cmd/` missing while `go.mod`/`Makefile` reference `cmd/hfscope` + `cmd/hfscope-token`, so `make build` is broken by construction; the `templ.Home` vet failure needs `templ generate` first (gitignored `**/*_templ.go`); 10 files not gofmt-clean. **Excluded from all CI.** Canonical is the external hfscope repo (currently deleted). |

## PhenoMCPServers delta completion wave (2026-11-10)

Closes the delta left by an earlier partial absorption of PhenoMCPServers into this repo — owner repo: **PhenoShared (phenoAI)**. Files land at their upstream relative paths; nothing was placed under `absorption/`.

| Repo | Disposition | Absorption README | Worklog ref | Notes |
|------|-------------|-------------------|-------------|-------|
| [PhenoMCPServers](https://github.com/KooshaPari/PhenoMCPServers) | ABSORB | [docs/absorbed-from/PhenoMCPServers/README.md](absorbed-from/PhenoMCPServers/README.md) | MCP-01 | Delta completion at source `8eb182b`. 46 files absorbed (2 schemas, 6 validators, 6 tests, 15 templates, 17 docs, 1 adapted CI workflow). Now 353/473 source files byte-identical here (45 of them added by this wave; the 46th landed as the adapted `phenomcp-catalog` workflow); 119 remaining diffs are the pre-existing `<REDACTED>` owner scrub plus monorepo adaptations. Source repo **left live and unarchived** pending operator decision — a prior audit recorded an unresolved `DECLARE_SPINE` recommendation. |

## Twelve-repo consolidation wave (2026-11-11)

Code and private data were separated before publication. Code lands here under `absorption/<repo>/`; withheld files went to the private `PhenoRegistry` under `repos/<repo>/`. Owner repo: **PhenoShared (phenoAI)**.

| Repo | Disposition | Absorption README | Worklog ref | Notes |
|------|-------------|-------------------|-------------|-------|
| `Authvault` (private source) | ABSORB | [docs/absorbed-from/Authvault/README.md](absorbed-from/Authvault/README.md) | MRG-01 | 322 code files. 11 dropped by root .gitignore (*.log, worklogs/). No private data. |
| `ResearchLedger` (private source) | ABSORB | [docs/absorbed-from/ResearchLedger/README.md](absorbed-from/ResearchLedger/README.md) | MRG-02 | 313 code files. 6 dropped by .gitignore. `linkedin-capture.json` withheld by ignore rule. |
| `SessionLedger` (private source) | ABSORB | [docs/absorbed-from/SessionLedger/README.md](absorbed-from/SessionLedger/README.md) | MRG-03 | 806 code files. 6 dropped by .gitignore (vendor/, audit_scorecard.json). |
| `cvp-fixture` (private source) | ABSORB | [docs/absorbed-from/cvp-fixture/README.md](absorbed-from/cvp-fixture/README.md) | MRG-04 | 17 code files, conformance fixtures. |
| `herdr-session-adapter` (private source) | ABSORB | [docs/absorbed-from/herdr-session-adapter/README.md](absorbed-from/herdr-session-adapter/README.md) | MRG-05 | 12 code files. |
| [kiro-adapters](https://github.com/KooshaPari/kiro-adapters) | ABSORB | [docs/absorbed-from/kiro-adapters/README.md](absorbed-from/kiro-adapters/README.md) | MRG-06 | 160 code files. 1 file withheld for a tailnet address; path held privately. |
| `netweave-3` (private source) | ABSORB | [docs/absorbed-from/netweave-3/README.md](absorbed-from/netweave-3/README.md) | MRG-07 | 30 code files. |
| `phenotype-router-spec` (private source) | ABSORB | [docs/absorbed-from/phenotype-router-spec/README.md](absorbed-from/phenotype-router-spec/README.md) | MRG-08 | 22 code files, A2A protocol schemas. |
| `rule30-research` (private source) | ABSORB | [docs/absorbed-from/rule30-research/README.md](absorbed-from/rule30-research/README.md) | MRG-09 | 6 code files. |
| `host-ops` (private source) | DATA_ONLY | private: `PhenoRegistry/repos/host-ops/` | MRG-10 | 107 files, all withheld. Host runbooks, tailnet addresses, Cloudflare zone id. No public copy. |
| `harness-ops` (private source) | DATA_ONLY | private: `PhenoRegistry/repos/harness-ops/` | MRG-11 | 65 files, all withheld. Agent-comms deploy scripts and wrangler config carrying the Cloudflare zone id. |
| `tailnet-smb-setup` (private source) | DATA_ONLY | private: `PhenoRegistry/repos/tailnet-smb-setup/` | MRG-12 | 21 files, all withheld. `research/lanes/credentials.md` and tailnet addressing. |

Selection policy: `host-ops`, `harness-ops` and `tailnet-smb-setup` moved wholly to the private registry because a per-file split would still publish host tooling, systemd unit names and runbook cadence. Every other repo was split per file on content. `argis-extensions` was deliberately excluded: its content already exists here at `crates/argis-extensions`.

## Worklog references

- **MRG-01..MRG-12** (2026-11-11): Twelve-repo consolidation. Content-based classifier over 3,526 files (tailnet CGNAT addresses, `.ts.net` hostnames, Cloudflare zone ids, credential filenames, key formats), with canonical test vectors whitelisted so they are not mistaken for secrets: W3C traceparent `4bf92f35`/`0af76519`, RFC 4231 HMAC KAT `b0344c61`, CGNAT bounds `100.64.0.0`/`100.64.0.1`, magic DNS `100.100.100.100`, placeholder `ghp_abcdefgh`. Result: 1,708 code files to `absorption/`, 194 data files to `PhenoRegistry/repos/`, 0 copy errors. A post-copy scan of the public absorption tree found no private identifiers; the only matches were the AWS documentation placeholder `AKIAIOSFODNN7EXAMPLE` and the fake token `ghp_abcdefgh...`, both in test fixtures.

- **PRE-EXISTING LEAK NOTED** (2026-11-11): the same Cloudflare zone id and the `tail2b570.ts.net` hostname are already committed in this public repo under `absorption/PhenoInfra/`: `docs/governance/oci-acquire-hook-chain.md`, `iac/landing-bootstrap/src/main.rs`, `iac/oci-post-acquire/src/main.rs`, `iac/scripts/install-windows-runner.ps1`, `iac/scripts/README-windows-runner.md`, `iac/scripts/README.md`, `iac/ansible/inventory.yml.example`, `docs/runbooks/windows-desktop-runner.md`. Also `absorption/resume-all/bin/tailscale-watch` (`100.96.0.0`). Not introduced by this wave and not removed by it; flagged for separate remediation.

- **MCP-01** (2026-11-10): PhenoMCPServers delta absorption — file-level diff found 353 identical, 46 missing, 119 diverged. Absorbed the 46 missing files verbatim, renamed and narrowed `.github/workflows/catalog.yml` to `phenomcp-catalog.yml`, and verified the validation pipeline in-tree (`validate_catalog`, `validate_fork_parents`, `validate_bundle_wiring` all OK; `validate_stale_patterns` and `check_driver_mcp_sync` advisory with exit 0; 29 passed / 2 pre-existing failures on the absorbed tests, 60 passed on the substrate + pheno-org suites). The 2 failures reproduce identically on a clean source clone, so they are upstream defects, not regressions.
- **HF-01** (2026-10-29): `hfscope` vendored-copy disposition — verified both declared upstreams deleted, confirmed `cmd/` absent, `make build` unbuildable, `templ generate` required before vet can pass, and 10 non-gofmt files. Recorded as EXCLUDE (not first-class) and excluded from all CI and module sweeps.

- **SPR-01..SPR-05** (2026-09-27): Repo-sprawl consolidation pass — five standalone repos assessed, absorbed as plain copies under `absorption/`, each given a `PROVENANCE.md` (source repo/commit/date/rationale) and a `docs/absorbed-from/<repo>/README.md` disposition README. Root Cargo workspace re-validated after absorption (`cargo metadata --no-deps` OK). Source repos to be archived after this wave.

- **L5-111** (2026-06-18): Trivial governance batch — verify P8 (phenotype-hub → phenotype-infra) and P9 (vibeproxy-monitoring-unified retirement) G19 absorption, add L5-### traceability to the index, and post a follow-up deprecation pointer on each archived source repo. See `phenotype-registry/ECOSYSTEM_MAP.md` §6 for the original P5/P8/P9 actions; this entry documents the G19 retrospective verification pass.

## Adding entries

When a future wave absorbs an archived repo into `phenotype-infra`:

1. Add `docs/absorbed-from/<repo>/README.md` with source URL, absorption date, disposition, and canonical mapping.
2. Append a row to the appropriate wave section in this file.
3. Add a `Worklog ref` column entry pointing to the L5-### tracking ID (or the wave/req_id used by the registry).
