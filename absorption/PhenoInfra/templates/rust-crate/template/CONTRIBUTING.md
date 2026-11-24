# Contributing

Thank you for your interest in contributing to this crate!

## About

This crate is a **substrate** (per [ADR-023](../../docs/adr/2026-06-15/ADR-023-agent-effort-governance.md)).
The fleet's v8 governance applies to every new capability added here.

## When adding a new shared capability

Per [ADR-041](../../docs/adr/2026-06-18/ADR-041-predictive-dry.md) (predictive DRY), every new shared primitive must:

1. **Fill out `PREDICTIVE.md`** in the PR description, addressing the 4 ADR-041 criteria:
   - criterion-1: 1+ current consumer with working code (stable for ≥ 30 days)
   - criterion-2: 1+ predicted consumer (named, dated, scoped)
   - criterion-3: clean abstraction boundary (Port trait + MockAdapter, ≤ 5 methods)
   - criterion-4: bounded reversal cost (≤ 1 day to revert)
2. **Update `.predict.yaml`** in the repo root with the current + predicted consumers.
3. **Add a Port trait** (per ADR-038) for the new surface, plus a `MockAdapter` for tests.

The CI lint `predictive-dry-check.yml` will block the PR if any of the 4 criteria
is not addressed in the PR body.

## When promoting this crate to a new tier

Per [ADR-042](../../docs/adr/2026-06-18/ADR-042-substrate-graduation-path.md) (substrate graduation path), tier transitions are explicit and audited:

1. **Fill out `PROMOTION.md`** in the PR description, listing every gate of the
   from-tier → to-tier transition with evidence (link to a test, doc, file, etc.).
2. **Update `.framework-lint.yaml`** in the repo root with the new tier:
   - `tier: pheno-*-lib` (default)
   - `tier: phenotype-*-sdk` (after lib → SDK promotion)
   - `tier: phenotype-*-framework` (after SDK → framework promotion)
   - `tier: federated-service` (after framework → federated service promotion)
3. **Update `[package.metadata.phenotype].tier`** in `Cargo.toml` to match.
4. **Tier-skipping is forbidden** unless the skipped tier would have been empty
   (ADR-042 §4). Declare any skip in `PROMOTION.md`.

## Weekly cron

Per [ADR-044](../../docs/adr/2026-06-18/ADR-044-cron-deployment.md), the following
tools run weekly on the heavy-runner against this repo (and the rest of the fleet):

- **`pheno-framework-lint`** — checks tier compliance (L73). Reads `.framework-lint.yaml`
  if present, otherwise infers tier from the repo name.
- **`pheno-drift-detector`** — checks for app-substrate drift (L74). Reads
  `.drift-detector.yaml` overrides to suppress false positives.
- **`pheno-predict`** — checks for similar-code candidates against fleet baselines (L72).
  Reads `.predict.yaml` to know this crate's declared consumers.

A backup of these scans runs in GitHub Actions (`.github/workflows/predictive-dry-check.yml`).
The cron is the source of truth; CI is the safety net.

## Tier compliance

Per [ADR-045](../../docs/adr/2026-06-18/ADR-045-event-bus-substrate-consolidation.md) (substrate consolidation / tier compliance), this
crate's tier is audited by `pheno-framework-lint`. The latest report lives in
`findings/`. Open a fix PR if your tier is non-compliant.

## PR conventions

- Branch naming: `feat/`, `fix/`, `chore/`, `docs/`, `refactor/`.
- One logical change per PR.
- All PRs must pass `clippy`, `fmt`, `test`, and `predictive-dry-check`.
- Update `CHANGELOG.md` under `[Unreleased]`.
- Squash-merge with a conventional commit message.

## Commit message format

We follow conventional commits:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `style:` Formatting
- `refactor:` Code restructuring
- `test:` Tests
- `chore:` Maintenance

## Code review

All submissions require review. Please ensure:
- CI checks pass
- Code is documented
- Tests cover new functionality
- If a new tier is being introduced, `PROMOTION.md` is filled out
