# Visual production integration primitives

Dependency-free, private workspace package for phenoDesign. The browser entry exports only pure contracts and geometry; file staging is a separate Node-only entry. It does not create a new asset registry, scheduler, graphics SDK, evidence ledger or autonomous agent orchestrator.

Run `node --test test/*.test.mjs` here. See the parent kit's `docs/REPOSITORY-INTEGRATION.md` and `docs/E2E-CONTRACT.md` for adoption, architecture and verification limits.

`aggregateVerdict` combines reported statuses. It does not independently establish that the underlying operations happened. Hashes establish byte identity, not trusted provenance.
