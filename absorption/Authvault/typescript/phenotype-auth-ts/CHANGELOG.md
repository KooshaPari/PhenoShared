# Changelog

All notable changes to this project will be documented in this file.

## 📚 Documentation
- Docs: add real spec docs (PRD, FR, ADR) (#5)

* docs: add PRD.md

* docs: add FUNCTIONAL_REQUIREMENTS.md

* docs: add ADR.md (`3e195bc`)
- Docs: add VitePress docsite with Mermaid support (#4)

* docs: add VitePress docsite with Mermaid support

* chore: add bun lockfile for docs dependencies

---------

Co-authored-by: Claude Code <claude@anthropic.com> (`8de1ff9`)
- Docs: add real ADR.md and PRD.md from TypeScript source analysis (#3)

ADR: 6 decisions covering hexagonal architecture, ESM modules, OAuth2
error hierarchy, Vitest, TTL expiry, and ISP port segregation.
PRD: 5 epics covering domain model, error types, port interfaces,
reference adapters, and package distribution.

Co-authored-by: Claude Code <claude@anthropic.com> (`b8fdad3`)
- Docs: add CLAUDE.md with development guidelines (`5183d71`)
## ✨ Features
- Feat: finalize phenotype-auth-ts auth ports and adapters (`65c334d`)
- Feat: comprehensive xDD test suite with BDD/TDD/contract tests

xDD Methodologies Applied:
- TDD: Red-green-refactor test cycle
- BDD: Given-When-Then scenario format
- CDD: Contract tests for port interfaces
- DDD: Domain models with error handling
- Property-Based: Invariant tests

Tests:
- TokenProvider contract tests
- TokenStore contract tests
- TokenVerifier contract tests
- Authentication flow BDD scenarios
- Property-based claim validation

Structure:
- src/domain/ - Domain models and errors
- src/ports/ - Port interfaces
- src/adapters/ - Adapter implementations
- tests/ - Contract and BDD tests (`5a1f91c`)
## 🔨 Other
- Chore(ci): adopt phenotype-tooling quality-gate + fr-coverage (`7ea90c3`)
- Chore: add Taskfile.yml with standard tasks (#2)

Co-authored-by: Claude Code <claude@anthropic.com> (`8e4be3d`)
- Chore: add ARCHIVED.md marker (`51ff73c`)
- Chore: add governance files (`dbdc512`)
- Chore: add architecture decision record

ADR-001: TypeScript auth patterns architecture

xDD: TDD, BDD, DDD, CDD, SOLID (`dc0f7d7`)
- Initial commit: phenotype-auth-ts with OAuth2/OIDC patterns

xDD Methodologies:
- TDD: Jest unit tests
- BDD: Given-When-Then scenarios
- DDD: Auth domain models
- CDD: Token verification contracts

ADR:
- adr/ADR-001-architecture.md (`67c2db2`)