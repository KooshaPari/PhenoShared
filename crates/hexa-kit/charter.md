# Charter — HexaKit (phenotype-infrakit)

> **Boundary class:** genesis  
> **Lifecycle:** active  
> **Genesis template:** self — `templates/genesis/` v1.0.0

## Mission

Bootstrap Phenotype-org repositories with architectural templates, governance shells, and linked genesis documentation (intent, charter, review, SOTA, OKF) — **not** domain SDK libraries.

## Scope

### In scope

- `templates/` — language layers, quality gates, **genesis doc scaffolds**
- `hexakit new` / genesis init (planned CLI)
- `docs/genesis/` — fleet-wide documentation standard
- `crates/phenotype-compliance-scanner` — **pattern/schema compliance only** (not runtime linters)
- OKF manifests and LLM wiki chunk conventions
- Session-log intent extraction (`scripts/extract-intent-prompts.py`)

### Out of scope

| Boundary | Owner repo |
|----------|------------|
| Python domain kits (auth, MCP, testing, observability) | `phenotype-python-sdk` |
| Go platform modules (devhex, devenv) | `phenotype-go-sdk`, `phenotype-tooling` |
| Rust domain crates (settly, tracing, metrics, logging, cache) | **phenotype-config** (`settly`), **PhenoObservability** (`tracingkit`, `metrickit`, `logkit`), **phenoShared** (`stashly`) — evicted from workspace `exclude` |
| Static analysis runtime | `KodeVibe` |
| LLM validation | `kwality` |
| E2E journey harness | `phenotype-journeys` |

> **Transitional note (2026-06-17):** Waves 2–7 evicted settly, Traceon, stashly, Metron, agileplus from workspace members. Remaining `crates/*` are compliance-scanner + shared infra stubs only; new domain code must not land here.

## Governance artifacts

| Artifact | Path |
|----------|------|
| Intent | [intent.md](intent.md) |
| Review (Kilo Code Stand) | [review.md](review.md) |
| SOTA | [SOTA.md](SOTA.md) |
| OKF | [okf/manifest.okf.yaml](okf/manifest.okf.yaml) |
| Standard | [docs/genesis/STANDARD.md](docs/genesis/STANDARD.md) |

## Decision rights

| Action | Authority |
|--------|-----------|
| Merge to `main` | <REDACTED> + 1 reviewer |
| Agent-authored PR | Allowed per [review.md](review.md) |
| Scope expansion into domain SDKs | **Blocked** — requires charter amendment |

**Agent autonomy:** Level 2 — agents may edit templates/docs; domain crate additions need human approval.

## Dependencies

- Fleet registry: `phenotype-registry`
- Compliance schema consumer: optional per-repo
- Template consumers: all Phenotype repos on bootstrap

## Retirement

HexaKit is a **canonical genesis owner** — not a delete candidate. Domain absorption happens **out of** HexaKit into SDK workspaces.

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-06-16 | Genesis charter v1; crates marked transitional | agent |
| 2026-06-17 | Wave 7 genesis refresh — post-eviction canonical owners in out-of-scope table | agent |

## Attestation

This charter supersedes README claims that HexaKit is primarily a "46-crate infrakit." Genesis + transitional crates coexist until rust-sdk migration completes.
