# ADR-006: Deployment Architecture

## Status

**Accepted** — 2026-05-25

## Author

KooshaPari

## Context

Phenotype web frontends need fast global delivery with zero-config preview deployments and branch-based promotion. Backend services and CI pipelines need reproducible, declarative build-and-test flows that run on every push. We want to avoid maintaining custom CI infrastructure while still having first-class support for Rust, TypeScript, and Docker workloads.

## Decision

We deploy all web frontends on **Vercel**, and run all build, test, lint, and release automation via **GitHub Actions**.

Vercel provides instant preview URLs per branch, edge-cached CDN delivery, and native support for the TanStack/Vite build outputs we produce. It integrates with GitHub PRs out of the box, meaning every PR gets a live preview without any manual deployment step. GitHub Actions is the CI layer for everything else: Rust compilation, cargo-deny, TruffleHog secret scanning, vitest runs, and release tagging. The combination keeps infrastructure cost near zero for the current scale while providing industry-standard DX.

## Consequences

### Positive
- PR preview deployments are automatic on Vercel; no staging environment to maintain
- GitHub Actions runners cover Rust, Node, and Docker workloads with standard marketplace actions
- Zero-config for most projects; Vercel auto-detects framework from package.json
- Free tier covers all current org projects

### Negative / Trade-offs
- Vercel vendor lock-in for frontend hosting; migrating would require re-configuring build pipelines
- GitHub Actions minutes are limited on free plans; large matrix builds may need optimisation
- Backend services (Rust, NATS, Postgres) are not on Vercel — container orchestration is a future decision

## References

- ADR-002 — Technology Stack (Vite/TanStack builds target Vercel)
- ADR-007 — Monitoring (Vercel Analytics feeds into PhenoObservability)

---

*Decision Date: 2026-05-25*
*Next Review: 2027-05-25*
