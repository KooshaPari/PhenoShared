# Phenotype Org Audits -- Spine INDEX

> Spine role locked 2026-07-05. Master index of the audit/inventory spine.

## Spines tracked

| Spine | Role | Repo |
|---|---|---|
| `phenotype-org-audits` | audit / inventory spine (this repo) | github.com/<REDACTED>/phenotype-org-audits |
| `phenotype-apps` | apps catalog spine (meta-portfolio, 324+ entries) | github.com/<REDACTED>/phenotype-apps |
| `substrate` | dispatch spine (3 drivers x 6 engines) | github.com/<REDACTED>/substrate |
| `AgilePlus` | control plane spine (cockpit) | github.com/<REDACTED>/AgilePlus |
| `Tracera` | trace spine | github.com/<REDACTED>/Tracera |
| `pheno` | workspace umbrella | github.com/<REDACTED>/pheno |
| `phenotype-infra` | infra workspace | github.com/<REDACTED>/phenotype-infra |

## Recent pillars (active, in audit cycle)

The 100+ pillar org-audit template (L0..L122) is the live scoring framework
(see `feat(audit): rebuild v38 100+ pillar org audit template (#73)`).

## Cross-repo consolidations (in flight or planned)

- `consolidation/config-consolidation-plan-2026-06-29` branch -- Configra + Conft
  + pheno-runtime-config consolidation (separate branch).
- Phenodag absorption (P20-P28 pillars) -- absorbed into Tracera + AgilePlus.
- Authvault -> AuthKit (D1) -- Authvault archived 2026-07-05, AuthKit is canonical.

## Archives

- Authvault: archived 2026-07-05 per D1.
- AtomsBot / GDK / Kaskman: strict-pause banners in `phenotype-apps/`.

## Out-of-scope (other teams)

- OmniRoute rewrite plan: `docs/sessions/20260705-omniroute-backend-rewrite/`.
- BytePort Surface 100% plan: owned by the BytePort team.
- Compute layer (PhenoCompose 55/100, nanovms 52/100) lift: flagged R-A.

## Open questions for the sponsor

See `docs/sessions/2026-07-05-polyrepo-portfolio-strategy/00_MASTER_SYNTHESIS.md`.
