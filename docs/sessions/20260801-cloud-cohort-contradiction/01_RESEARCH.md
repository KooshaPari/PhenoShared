# Research and API Evidence

## Commands and authority

The following read-only probes were run against GitHub's REST API and Git refs:

```sh
gh api repos/KooshaPari/<intake-name>
gh api repos/KooshaPari/<canonical-name>/commits/<default-branch> --jq .sha
gh api --include repos/KooshaPari/<missing-name>
gh api user/repos?per_page=100 --paginate
git ls-remote git@github.com:KooshaPari/phenotype-registry.git refs/heads/main
```

The direct API response's `full_name`, `default_branch`, `archived`, and `fork` fields are
authoritative for the snapshot. Default-branch SHA values below are full 40-character API values.
The three missing rows returned `HTTP/2.0 404 Not Found` at 08:34:34Z-08:34:35Z.

## Twenty-row snapshot

| Intake name | API result / canonical full name | Default branch | Archived | Fork | Default SHA |
|---|---|---|---:|---:|---|
| `AgilePlus-recovery-20260714` | `KooshaPari/zz-archive-AgilePlus-recovery-20260714` | `recovery/isolated-20260714` | true | false | `0aafdf9692c11abb6e426f36857aeec7bb6cd942` |
| `AgilePlus-recovery-evidence-20260714` | HTTP 404 | - | - | - | - |
| `agileplus-spec-harmonizer-tool-archive-2026-07-14` | HTTP 404 | - | - | - | - |
| `4sgm-archive` | HTTP 404 | - | - | - | - |
| `phenotype-registry-archive` | `KooshaPari/zz-archive-phenotype-registry` | `phenotype-registry-archived-local-work/docs/preserve-archived-local-work-2026-06-20` | true | false | `82239e3dd58a374fb3132fef4ec73c45cb6c3498` |
| `phenotype-org-audits-archive2` | `KooshaPari/zz-archive-phenotype-org-audits-archive2` | `archive/phenotype-org-audits` | true | false | `47433354dc1b7649e35f263951e18b8ffa60a386` |
| `PhenoRuntime-archive` | `KooshaPari/zz-archive-PhenoRuntime-archive` | `local/chore/governance-baseline` | true | false | `54f2df34f95fa982a2ee21d279372cb79da2d5e3` |
| `Parpoura-archive` | `KooshaPari/zz-archive-Parpoura-archive` | `local/chore/governance-baseline` | true | false | `6f9013a1361768d6a8bb1cb1f8dd57a49bb4a3a1` |
| `ResilienceKit-archive` | `KooshaPari/zz-archive-ResilienceKit-archive` | `local/chore/absorb-httpora-rate-limiter-2026-06-20` | true | false | `2a9c112bc3633ccb65b14e6da18668e85d7b263a` |
| `phenoResearchEngine-archive` | `KooshaPari/zz-archive-phenoResearchEngine-archive` | `local/main` | true | false | `a1817c643c6e09cd59481bf8bdafeff0a9f2c3e3` |
| `home-recovery-2026-07-archive` | `KooshaPari/zz-archive-home-recovery-2026-07-archive` | `local/main` | true | false | `434b4e3eaf98afab54d70f5f3d049a3c517a5a2d` |
| `phenotype-monorepo-state-archive` | `KooshaPari/zz-archive-phenotype-monorepo-state-archive` | `main` | true | false | `59a49e03f570a5986498ae6e125881d263121d43` |
| `phenotype-shared-archive` | `KooshaPari/zz-archive-phenotype-shared-archive` | `main` | true | false | `41865ef1fca343b89885e5e56fed2a298746d7e5` |
| `agent-user-status-archive` | `KooshaPari/zz-archive-agent-user-status-archive` | `local/orch-v12-s2-017/tier-0-baseline` | true | false | `12167818b39dfb0a311a8889f488dcb43b7ff033` |
| `PriceyApp` | `KooshaPari/PriceyApp` | `main` | false | true | `828e7754aad3649049e1483313bacc2eb4f63423` |
| `Quillr` | `KooshaPari/Quillr` | `main` | false | false | `da3ea9f0427498ec2392db1f66d32e825100adf5` |
| `Stashly` | `KooshaPari/Stashly` | `main` | false | false | `1b491ca1c30f5eea10a15e5a039d82741a89d1bd` |
| `router-docs` | `KooshaPari/router-docs` | `main` | true | false | `8dc9d880b5d3a790c00c05bf70db7d37febec6fd` |
| `template-commons` | `KooshaPari/template-commons` | `main` | true | false | `fcacc0a2072d2abed860543c0c02c05f0842b7b5` |
| `phenotype-teamcomm` | `KooshaPari/phenotype-teamcomm` | `main` | false | false | `8486133e2a3fe74a7e29d2ebd7f9a1a9c00fd6db` |

## Committed policy and outcome being contradicted

- `docs/sessions/20260722-consolidation-20/00_SESSION_OVERVIEW.md`: says docket #1 was the sole
  archive and the other nineteen remained HOLD or VERIFY-ONLY.
- `docs/sessions/20260722-consolidation-20/02_SPECIFICATIONS.md`: FR-12, FR-16, and the binary
  acceptance criteria restrict READY actions and remote mutation.
- `docs/sessions/20260722-repository-preservation-wave/preservation-manifest.json`: policy sets
  `archive`, `delete`, `rename`, and `force_push` to false.
- `plans/2026-07-31-estate-execution-ledger.md`: requires durable provenance, independent restore,
  a complete manifest, and exact sponsor acknowledgement before archive.

These files are evidence of the intended governance state, not proof of the actor or authority for
the current cloud changes.
