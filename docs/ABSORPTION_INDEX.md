# Absorption index

Canonical index of archived repos absorbed or retired into the Phenotype platform layer. Each entry links to a disposition README under `docs/absorbed-from/<repo>/`.

## Wave G19 (2026-06-18)

Registry wave G19 stub absorption — owner repo: **phenotype-infra**. Registry ledger: `phenotype-registry` wave15 execution doc (`docs/operations/wave15-execution-2026-06-17.md`).

| Repo | Disposition | Absorption README | Worklog ref | Notes |
|------|-------------|-------------------|-------------|-------|
| [phenotype-hub](https://github.com/KooshaPari/phenotype-hub) | ABSORB | [docs/absorbed-from/phenotype-hub/README.md](absorbed-from/phenotype-hub/README.md) | L5-111 | Governance scaffold docs; canonical owner is this repo. P8 in `phenotype-registry/ECOSYSTEM_MAP.md` §6. |
| [vibeproxy-monitoring-unified](https://github.com/KooshaPari/vibeproxy-monitoring-unified) | RETIRE | [docs/absorbed-from/vibeproxy-monitoring-unified/README.md](absorbed-from/vibeproxy-monitoring-unified/README.md) | L5-111 | Empty stub; pointer to [cliproxyapi-plusplus VIBEPROXY_ABSORPTION](https://github.com/KooshaPari/cliproxyapi-plusplus/blob/main/docs/VIBEPROXY_ABSORPTION.md). P9 in `phenotype-registry/ECOSYSTEM_MAP.md` §6. |

## Worklog references

- **L5-111** (this turn, 2026-06-18): Trivial governance batch — verify P8 (phenotype-hub → phenotype-infra) and P9 (vibeproxy-monitoring-unified retirement) G19 absorption, add L5-### traceability to the index, and post a follow-up deprecation pointer on each archived source repo. See `phenotype-registry/ECOSYSTEM_MAP.md` §6 for the original P5/P8/P9 actions; this entry documents the G19 retrospective verification pass.

## Adding entries

When a future wave absorbs an archived repo into `phenotype-infra`:

1. Add `docs/absorbed-from/<repo>/README.md` with source URL, absorption date, disposition, and canonical mapping.
2. Append a row to the appropriate wave section in this file.
3. Add a `Worklog ref` column entry pointing to the L5-### tracking ID (or the wave/req_id used by the registry).
