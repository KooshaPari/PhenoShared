# Charter — {{PROJECT_NAME}}

> **Boundary class:** {{BOUNDARY_CLASS}}  
> **Lifecycle:** active  
> **Genesis template:** HexaKit `templates/genesis/` v1.0.0

## Mission

{{ONE_LINE_MISSION}}

## Scope

### In scope

- {{IN_SCOPE_ITEM_1}}
- {{IN_SCOPE_ITEM_2}}

### Out of scope

| Boundary | Owner repo |
|----------|------------|
| Domain SDKs (auth, telemetry, MCP, testing libs) | `phenotype-python-sdk`, `phenotype-go-sdk`, `phenotype-rust-sdk` (planned) |
| Static analysis runtime | `KodeVibe` |
| LLM validation | `kwality` |
| Application logic | product repos |

## Governance artifacts

| Artifact | Path |
|----------|------|
| Intent | [intent.md](intent.md) |
| Review (Kilo Code Stand) | [review.md](review.md) |
| SOTA | [SOTA.md](SOTA.md) |
| OKF manifest | [okf/manifest.okf.yaml](okf/manifest.okf.yaml) |

Specs: [HexaKit docs/genesis/STANDARD.md](https://github.com/KooshaPari/HexaKit/blob/main/docs/genesis/STANDARD.md)

## Decision rights

| Action | Authority |
|--------|-----------|
| Merge to `main` | {{MAINTAINER}} + 1 reviewer |
| Agent-authored PR | Allowed per [review.md](review.md) |
| Scope expansion | Charter amendment + intent synthesis update |

**Agent autonomy:** Level {{0-3}} — see [review.md](review.md#agent-roster)

## Dependencies

- Genesis bootstrap: HexaKit templates version `{{HEXAKIT_TEMPLATE_REF}}`
- {{ADDITIONAL_DEPS}}

## Retirement

If this repo is absorbed: require **100% boundary coverage** in a single canonical owner before delete. Update `phenotype-registry` and OKF manifest.

## Changelog

| Date | Change | Author |
|------|--------|--------|
| {{DATE}} | Initial charter from genesis template | — |

## Attestation

This charter supersedes informal README scope claims. On conflict, charter wins.
