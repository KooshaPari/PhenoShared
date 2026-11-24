# SOTA — HexaKit (genesis layer)

> **Last researched:** 2026-06-17  
> **Methods:** Internal archive audits, rationalization plans, agent-session requirements, comparative template tooling

## Executive summary

| Dimension | Our choice | Confidence | Deep dive |
|-----------|------------|------------|-----------|
| Technical | Git-native template trees + OKF manifest | high | [docs/sota/technical.md](docs/sota/technical.md) |
| DX | `templates/genesis/` copy + extract-intent script | med | [docs/sota/dx.md](docs/sota/dx.md) |
| UX | N/A (developer infrastructure) | n/a | [docs/sota/ux.md](docs/sota/ux.md) |
| AX | Cursor manager → forge `-p` workers; session scrape | high | [docs/sota/ax.md](docs/sota/ax.md) |
| Security | Charter blocklist + review.md tiers | med | [docs/sota/security.md](docs/sota/security.md) |
| Ops | Template smoke scripts per language | med | [docs/sota/ops.md](docs/sota/ops.md) |
| Cost | Single genesis repo vs N Kit repos | high | [docs/sota/cost.md](docs/sota/cost.md) |

## Why this is optimal (for Phenotype)

Separating **genesis** (HexaKit) from **domain SDKs** (`phenotype-*-sdk`) minimizes duplicated governance while keeping optional installs for small modules. Alternatives like one mega-monorepo or dozens of `*Kit` archives failed on maintenance cost (see archive audit wave).

## Fork status

- **Is fork:** no

## Evolution triggers

- ~~Domain crate evictions (settly, Traceon, stashly, Metron)~~ → complete Waves 2–7
- Remaining `crates/*` infra stubs → role owners per `phenotype-registry` disposition index
- Backstage/Cortex adoption → re-evaluate OKF vs catalog UI

## Linkage

- [charter.md](charter.md) · [review.md](review.md) · [intent.md](intent.md)
- Prior monolithic research (v1): [docs/sota/archive-hexakit-research-v1.md](docs/sota/archive-hexakit-research-v1.md)
