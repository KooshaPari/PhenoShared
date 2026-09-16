# Journey-Traceability Adoption Catalog

**Snapshot date:** 2026-06-05
**Canonical standard:** [phenotype-infra `journey-traceability-standard.md`](https://raw.githubusercontent.com/KooshaPari/phenotype-infra/main/docs/governance/journey-traceability-standard.md)
**Originating PR:** [phenodocs#168](https://github.com/KooshaPari/phenodocs/pull/168)

This page tracks, repo-by-repo, which Phenotype-org repositories have adopted the
**spec → code → test → journey → gate** traceability pattern. The columns are:

- `journey-traceability.md?` — does the repo ship a `docs/operations/journey-traceability.md` guide?
- `manifests/README.md?` — does the repo ship a `docs/journeys/manifests/` directory (per-journey manifests)?
- `journey pages count` — number of journey pages under `docs/journeys/` (excluding the manifests directory)
- `CI gate?` — is there a GitHub Actions workflow that verifies journey/manifest coverage (e.g. `journey-gate.yml`, `journey-verify.yml`)?

A repo is considered **fully adopted** when all four columns are `yes` (or a positive count).

## Adoption Table

| Repo | journey-traceability.md? | manifests/README.md? | journey pages count | CI gate? |
| --- | --- | --- | --- | --- |
| phenodocs | yes | yes | 1 | yes |
| hwLedger | yes | yes | 0 | no |
| PhenoHandbook | yes | yes | 0 | no |
| phenotype-journeys | yes | no | 0 | yes |
| OmniRoute | yes | no | 0 | no |
| FocalPoint | yes | yes | 0 | yes |
| Parpoura | yes | yes | 0 | no |
| PhenoMCP | yes | yes | 0 | no |
| PhenoProc | yes | yes | 0 | no |
| PhenoForge | no | no | 5 | no |
| HeliosCLI | yes | yes | 0 | yes |
| helios-router | no | no | 0 | no |
| heliosscope | — (repo not found locally) | — | — | — |
| heliosApp | yes | yes | 0 | yes |
| AgilePlus | yes | no | 0 | no |
| Civis | no | no | 0 | no |
| Paginary | yes | yes | 0 | no |
| heliosLab | yes | yes | 4 | no |
| PhenoPlugins | yes | yes | 0 | no |
| phenoForge | no | no | 5 | no |
| PhenoProject | yes | yes | 0 | no |
| phenotype-tooling | yes | yes | 0 | no |
| thegent-maif | — (repo not found locally) | — | — | — |
| BytePort | yes | yes | 0 | no |
| Sidekick | yes | yes | 0 | no |
| GDK | yes | yes | 0 | no |
| PhenoAgent | yes | yes | 0 | yes |

## Roll-up Summary

- **Repos surveyed:** 27 (2 not present locally: `heliosscope`, `thegent-maif`)
- **Fully adopted (all 4 columns green):** 1 — `phenodocs`
- **Manifests in place, gate in place:** 5 — `FocalPoint`, `HeliosCLI`, `heliosApp`, `phenotype-journeys` (gate without manifests), `PhenoAgent`
- **Missing journey-traceability.md:** `PhenoForge`, `helios-router`, `Civis`, `phenoForge`
- **Highest journey-page counts:** `PhenoForge` and `phenoForge` (5 pages each), `heliosLab` (4 pages), `phenodocs` (1 page)

## Notes on Method

- Detection is filesystem-based against `/Users/kooshapari/CodeProjects/Phenotype/repos/`.
- "CI gate" is detected by the presence of a workflow filename matching `journey-gate*.yml` or `journey-verify*.yml` under `.github/workflows/`. Per Phenotype's GitHub Actions billing constraint, these workflows will not execute on remote CI, but the files are recorded as evidence of intent.
- Counts exclude the `manifests/` directory; `README.md` index pages at the `docs/journeys/` root are not counted.
- This catalog is a point-in-time snapshot. To refresh, regenerate from a clean checkout of the `Phenotype/repos/` tree.

## Related Standards

- **Standard:** https://raw.githubusercontent.com/KooshaPari/phenotype-infra/main/docs/governance/journey-traceability-standard.md
- **Reference PR:** https://github.com/KooshaPari/phenodocs/pull/168
- **Internal pointer:** `docs/operations/journey-traceability.md` (PhenoHandbook's own copy of the standard)
