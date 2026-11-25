# Charter — Authvault

> **Boundary class:** sdk-domain  
> **Role:** connect  
> **Lifecycle:** active  
> **Genesis template:** HexaKit `templates/genesis/` v1.0.0

## Mission

Hexagonal auth framework (OAuth2, JWT, RBAC/ABAC) for the connect role.

## Scope

### In scope

- Rust auth domain crates and adapters
- Security/session/token audit surfaces

### Out of scope

| Boundary | Owner repo |
|----------|------------|
| Python auth-kit edge | `phenotype-python-sdk` |
| Application product auth UX | `product repos` |

## Governance artifacts

| Artifact | Path |
|----------|------|
| Intent | [intent.md](intent.md) |
| Review | [review.md](review.md) |
| SOTA | [SOTA.md](SOTA.md) |
| OKF | [okf/manifest.okf.yaml](okf/manifest.okf.yaml) |

Authority: [phenotype-registry DOMAIN_ROLES](https://github.com/KooshaPari/phenotype-registry/blob/main/DOMAIN_ROLES.md)

## Decision rights

| Action | Authority |
|--------|-----------|
| Merge to `main` | KooshaPari + 1 reviewer |

## Changelog

| Date | Change |
|------|--------|
| 2026-06-17 | Genesis rollout Wave 4 |
