# Absorption index

Canonical index of archived repos absorbed or retired into the Phenotype platform layer. Each entry links to a disposition README under `docs/absorbed-from/<repo>/`.

## Wave G19 (2026-06-18)

Registry wave G19 stub absorption — owner repo: **phenotype-infra**. Registry ledger: `phenotype-registry` wave15 execution doc (`docs/operations/wave15-execution-2026-06-17.md`).

| Repo                                                                                       | Disposition | Absorption README                                                                                                 | Worklog ref | Notes                                                                                                                                                                                                                |
| ------------------------------------------------------------------------------------------ | ----------- | ----------------------------------------------------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [phenotype-hub](https://github.com/KooshaPari/phenotype-hub)                               | ABSORB      | [docs/absorbed-from/phenotype-hub/README.md](absorbed-from/phenotype-hub/README.md)                               | L5-111      | Governance scaffold docs; canonical owner is this repo. P8 in `phenotype-registry/ECOSYSTEM_MAP.md` §6.                                                                                                              |
| [vibeproxy-monitoring-unified](https://github.com/KooshaPari/vibeproxy-monitoring-unified) | RETIRE      | [docs/absorbed-from/vibeproxy-monitoring-unified/README.md](absorbed-from/vibeproxy-monitoring-unified/README.md) | L5-111      | Empty repository; pointer to [cliproxyapi-plusplus VIBEPROXY_ABSORPTION](https://github.com/KooshaPari/cliproxyapi-plusplus/blob/main/docs/VIBEPROXY_ABSORPTION.md). P9 in `phenotype-registry/ECOSYSTEM_MAP.md` §6. |

## Sprawl consolidation wave (2026-09-27)

Repo-sprawl reduction wave — owner repo: **PhenoShared (phenoAI)**. Five standalone repos absorbed as plain copies under `absorption/<repo>/`, each with a `PROVENANCE.md`.

| Repo                                                                                               | Disposition | Absorption README                                                                                                         | Worklog ref | Notes                                                                                                                                                 |
| -------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| [phenotype-canonicalization](https://github.com/KooshaPari/phenotype-canonicalization)             | ABSORB      | [docs/absorbed-from/phenotype-canonicalization/README.md](absorbed-from/phenotype-canonicalization/README.md)             | SPR-01      | Agent-authored canonicalization docs/audit, 44 files. Source left unarchived pending operator confirmation.                                           |
| [phenotype-cvp-audit-2026-09-14](https://github.com/KooshaPari/phenotype-cvp-audit-2026-09-14)     | ABSORB      | [docs/absorbed-from/phenotype-cvp-audit-2026-09-14/README.md](absorbed-from/phenotype-cvp-audit-2026-09-14/README.md)     | SPR-02      | One-off dated CVP audit deliverable, 6 files. Source left unarchived pending operator confirmation.                                                   |
| [phenoDesign-visual-production-v2](https://github.com/KooshaPari/phenoDesign-visual-production-v2) | ABSORB      | [docs/absorbed-from/phenoDesign-visual-production-v2/README.md](absorbed-from/phenoDesign-visual-production-v2/README.md) | SPR-03      | Distinct from the governed `phenoDesign` design-system repo. Source left unarchived pending operator confirmation.                                    |
| [PhenoMLX-temp](https://github.com/KooshaPari/PhenoMLX-temp)                                       | ABSORB      | [docs/absorbed-from/PhenoMLX-temp/README.md](absorbed-from/PhenoMLX-temp/README.md)                                       | SPR-04      | Temp snapshot; ~646 MB `.cargo-target/` excluded. Canonical source is live `KooshaPari/PhenoMLX`. GitHub repo `KooshaPari/PhenoMLX-temp` is archived. |
| [PhenoInfra](https://github.com/KooshaPari/PhenoInfra)                                             | ABSORB      | [docs/absorbed-from/PhenoInfra/README.md](absorbed-from/PhenoInfra/README.md)                                             | SPR-05      | Compute/infra monorepo snapshot; not wired into root workspace. Source repo already archived.                                                         |

## Vendored-off-Go-tool disposition wave (2026-10-29)

Vendored-copy disposition pass for a Go tool absorbed outside the `absorption/` flow — owner repo: **PhenoShared (phenoAI)**. Entry recorded so the tree is permanently excluded from CI and from future module sweeps.

| Repo                                                                       | Disposition | Absorption README                                                       | Worklog ref | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| -------------------------------------------------------------------------- | ----------- | ----------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [zz-merge-unk-hfscope](https://github.com/KooshaPari/zz-merge-unk-hfscope) | EXCLUDE     | [docs/absorbed-from/hfscope/README.md](absorbed-from/hfscope/README.md) | HF-01       | Vendored at `hfscope/` (not `absorption/`); `PROVENANCE.md` declares absorption into PhenoMLX, yet the copy lives here. **Both upstreams deleted** (`KooshaPari/hfscope`, `KooshaPari/zz-merge-unk-hfscope` → "Repository not found"). Absorption incomplete: `cmd/` missing while `go.mod`/`Makefile` reference `cmd/hfscope` + `cmd/hfscope-token`, so `make build` is broken by construction; the `templ.Home` vet failure needs `templ generate` first (gitignored `**/*_templ.go`); 10 files not gofmt-clean. **Excluded from all CI.** Canonical is the external hfscope repo (currently deleted). |

## PhenoMCPServers delta completion wave (2026-11-10)

Closes the delta left by an earlier partial absorption of PhenoMCPServers into this repo — owner repo: **PhenoShared (phenoAI)**. Files land at their upstream relative paths; nothing was placed under `absorption/`.

| Repo                                                             | Disposition | Absorption README                                                                       | Worklog ref | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      |
| ---------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [PhenoMCPServers](https://github.com/KooshaPari/PhenoMCPServers) | ABSORB      | [docs/absorbed-from/PhenoMCPServers/README.md](absorbed-from/PhenoMCPServers/README.md) | MCP-01      | Delta completion at source `8eb182b`. 46 files absorbed (2 schemas, 6 validators, 6 tests, 15 templates, 17 docs, 1 adapted CI workflow). Now 353/473 source files byte-identical here (45 of them added by this wave; the 46th landed as the adapted `phenomcp-catalog` workflow); 119 remaining diffs are the pre-existing `<REDACTED>` owner scrub plus monorepo adaptations. Source repo **left live and unarchived** pending operator decision — a prior audit recorded an unresolved `DECLARE_SPINE` recommendation. |

## Twelve-repo consolidation wave (2026-11-11)

Code and private data were separated before publication. Code lands here under `absorption/<repo>/`; withheld files went to the private `PhenoRegistry` under `repos/<repo>/`. Owner repo: **PhenoShared (phenoAI)**.

| Repo                                                         | Disposition | Absorption README                                                                                   | Worklog ref | Notes                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------------------------------------------------ | ----------- | --------------------------------------------------------------------------------------------------- | ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Authvault` (private source)                                 | ABSORB      | [docs/absorbed-from/Authvault/README.md](absorbed-from/Authvault/README.md)                         | MRG-01      | 322 code files. 11 dropped by root .gitignore (*.log, worklogs/). No private data.                                                                                                                                                                                                                                                                                                                                        |
| `ResearchLedger` (private source)                            | ABSORB      | [docs/absorbed-from/ResearchLedger/README.md](absorbed-from/ResearchLedger/README.md)               | MRG-02      | 313 code files. 6 dropped by .gitignore. `linkedin-capture.json` withheld by ignore rule.                                                                                                                                                                                                                                                                                                                                 |
| `SessionLedger` (private source)                             | ABSORB      | [docs/absorbed-from/SessionLedger/README.md](absorbed-from/SessionLedger/README.md)                 | MRG-03      | 806 code files. 6 dropped by .gitignore (vendor/, audit_scorecard.json).                                                                                                                                                                                                                                                                                                                                                  |
| `cvp-fixture` (private source)                               | ABSORB      | [docs/absorbed-from/cvp-fixture/README.md](absorbed-from/cvp-fixture/README.md)                     | MRG-04      | 17 code files, conformance fixtures.                                                                                                                                                                                                                                                                                                                                                                                      |
| `herdr-session-adapter` (private source)                     | ABSORB      | [docs/absorbed-from/herdr-session-adapter/README.md](absorbed-from/herdr-session-adapter/README.md) | MRG-05      | 12 code files.                                                                                                                                                                                                                                                                                                                                                                                                            |
| [kiro-adapters](https://github.com/KooshaPari/kiro-adapters) | ABSORB      | [docs/absorbed-from/kiro-adapters/README.md](absorbed-from/kiro-adapters/README.md)                 | MRG-06      | 160 code files. 1 file withheld for a tailnet address; path held privately.                                                                                                                                                                                                                                                                                                                                               |
| `netweave-3` (private source)                                | ABSORB      | [docs/absorbed-from/netweave-3/README.md](absorbed-from/netweave-3/README.md)                       | MRG-07      | 30 code files.                                                                                                                                                                                                                                                                                                                                                                                                            |
| `phenotype-router-spec` (private source)                     | ABSORB      | [docs/absorbed-from/phenotype-router-spec/README.md](absorbed-from/phenotype-router-spec/README.md) | MRG-08      | 22 code files, A2A protocol schemas.                                                                                                                                                                                                                                                                                                                                                                                      |
| `rule30-research` (private source)                           | ABSORB      | [docs/absorbed-from/rule30-research/README.md](absorbed-from/rule30-research/README.md)             | MRG-09      | 6 code files.                                                                                                                                                                                                                                                                                                                                                                                                             |
| `host-ops` (private source)                                  | DATA_ONLY   | private: `PhenoRegistry/repos/host-ops/tree/`                                                       | MRG-10      | 683 files and every ref, whole repo, no public copy. Grafted from source `main` (`f8b39eb8`) on 2026-11-14 onto `refs/preserved/host-ops/`; `verify_absorption.py` reports 683/683 and `verify_preserved.py` matches `tree 6879bb6f95 == branch main`. Supersedes the 107-file per-file split of 2026-11-11. The source repository is retained: five launchd jobs publish from it (see `absorption-ledger/DELETIONS.md`). |
| `harness-ops` (private source)                               | DATA_ONLY   | private: `PhenoRegistry/repos/harness-ops/`                                                         | MRG-11      | 65 files, all withheld. Agent-comms deploy scripts and wrangler config carrying the Cloudflare zone id.                                                                                                                                                                                                                                                                                                                   |
| `tailnet-smb-setup` (private source)                         | DATA_ONLY   | private: `PhenoRegistry/repos/tailnet-smb-setup/`                                                   | MRG-12      | 21 files, all withheld. `research/lanes/credentials.md` and tailnet addressing.                                                                                                                                                                                                                                                                                                                                           |

Selection policy: `host-ops`, `harness-ops` and `tailnet-smb-setup` moved wholly to the private registry because a per-file split would still publish host tooling, systemd unit names and runbook cadence. Every other repo was split per file on content. `argis-extensions` was deliberately excluded: its content already exists here at `crates/argis-extensions`.

## Multi-branch consolidation wave (2026-11-11)

The four remaining repos from the deletion list that held real history. Files land here under `absorption/<repo>/`; each repo's full commit graph is stored as a verified git bundle in the private `PhenoRegistry` under `repos/<repo>/history/`, because absorbing only the default branch would have dropped their other branches.

| Repo                                            | Disposition | Worklog ref | Files | Branches | Notes                                                                                                                                                                                          |
| ----------------------------------------------- | ----------- | ----------- | ----- | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `phenoStandards` (private source)               | ABSORB      | MRG-13      | 25    | 11       | 23 default-branch files plus `FUNDING.yml` and `docs/story-ledger-phenoStandards.md`, which existed only on non-default branches.                                                              |
| `argisexec` (private source)                    | ABSORB      | MRG-14      | 6     | 6        | 4 default-branch files plus `FUNDING.yml` and `docs/story-ledger-argisexec.md` from other branches.                                                                                            |
| `zen` (private source)                          | ABSORB      | MRG-15      | 17    | 4        | 16 default-branch files plus `docs/story-ledger-zen.md`.                                                                                                                                       |
| `vibeproxy-monitoring-unified` (private source) | EMPTY       | MRG-16      | 0     | 23       | All 23 refs point at one commit with an empty tree. Nothing to consolidate; the bundle preserves the ref graph for audit. Earlier reporting described 21 branches of content, which was wrong. |

Branch-only files were extracted per ref rather than assumed absent, and each repo's `PROVENANCE.md` names the ref each came from. A leak scan over all 52 absorbed files found no private identifiers. Deleting a repo also discards its discussion, so the threads were exported before any deletion: 61 issues, 53 pull requests and 136 comments across the four, of which 19 issues and 11 pull requests were still open. Those exports live beside the bundles in the private `PhenoRegistry` under `repos/<repo>/github/`.

### Deleted on 2026-11-11

All four source repos were deleted after the preconditions below were asserted, each verified absent by a following API call:

| Repo                           | Absorbed files | Bundle | Issues/PRs exported | Deleted |
| ------------------------------ | -------------- | ------ | ------------------- | ------- |
| `phenoStandards`               | 26             | yes    | 10 / 10             | yes     |
| `argisexec`                    | 7              | yes    | 8 / 4               | yes     |
| `zen`                          | 18             | yes    | 1 / 1               | yes     |
| `vibeproxy-monitoring-unified` | 1              | yes    | 42 / 38             | yes     |

Two further empty repos from the same deletion batch were removed with them: `4sgm-archive2` and `forge-AgilePlus`, both 0 files, 0 branches, 0 issues.

`PhenoMCPServers` was deliberately **not** deleted. Its content is fully absorbed (see the MCP-01 entry) but a prior audit left an unresolved `DECLARE_SPINE` recommendation for it, so the repo was **archived** on 2026-11-11 instead (`archived: true`, 2,610 KB retained). Archiving keeps the full history, issues and read-only source available while removing it from active work; it is reversible with `gh repo unarchive`. Deleting it would have discarded the commit history and the unscrubbed upstream wording that the 119 diverged files no longer carry.

## Cleanup and backlog wave (2026-11-11)

Final pass over the remaining candidates. Content was absorbed here; full history
and discussion were captured to the private `PhenoRegistry` before each deletion.

| Repo               | Files absorbed | Notes                                                                                                                                                                           |
| ------------------ | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `canvasApp`        | 205            | Vendored `.venv`/`node_modules` excluded as non-project content; 27 apparent secrets were all vendored library files (`certifi/cacert.pem`, google-auth), not project material. |
| `.team-status`     | 7              | NOTES_DOCS import from `~/CodeProjects/Phenotype/repos/`.                                                                                                                       |
| `analysis-archive` | 2              | Tombstone: its last commit reads "remove the tooling now that PhenoShared carries it".                                                                                          |

Also deleted as empty: `2phenoEvents` (0 KB, 2 branches, no content).

Six earlier repos were deleted the same day after full-history bundles were pushed
to `PhenoRegistry/repos/<repo>/history/` and their threads exported to
`PhenoRegistry/repos/<repo>/github/`: `PhenoInfra` (265 commits, 11 refs),
`ponytail` (455 commits, 103 refs), `kiro-adapters` (125 commits), and the three
`herdr-*` plugins. `PhenoInfra` needed a bundle rather than a file copy because its
401 file differences against the local copy were bidirectional: upstream had renamed
badges and fixed owner casing, while the local copy carried newer dependency
versions. Neither side was a superset.

### Deliberately not deleted

The `*-archive-20261106`, `*-rb-archive-*`, `exports-temp-archive-20261108`,
`work-archive-20261105` and `phenotype-archives-20261108` repos are the recovery
store: several are described as the only surviving copy of upstreams whose remotes
no longer exist, holding repaired git bundles, bare mirrors and shallow-boundary
preservations. They are not consolidation candidates and were left untouched.

That caution was re-tested on 2026-11-12 rather than left as an assertion. No
store's ref set matches any live repository, and the four that share a name with
a live repo hold no commit that exists in it: `AgilePlus`, `Melosviz`, `Pine` and
`Tracera` each have an archive carrying unmerged `pr-*` and `work-*` branches
that survive nowhere else. Evidence in
[`docs/absorption-ledger/RECOVERY-STORES.md`](absorption-ledger/RECOVERY-STORES.md).

## Private ops, oversize histories and dependency forks (2026-11-12)

Twenty-two repositories were deleted after new preservation methods were proved.
Detail and per-repo proof: [`docs/absorption-ledger/DELETIONS.md`](absorption-ledger/DELETIONS.md).

| Wave                             | Deleted | Content preserved as                                                  | History preserved as                 |
| -------------------------------- | ------: | --------------------------------------------------------------------- | ------------------------------------ |
| Private ops repositories         |       9 | `PhenoRegistry/repos/<repo>/tree/`                                    | `refs/preserved/<repo>/`             |
| Histories too large for a bundle |       2 | `absorption/PhenoMLX-temp/`, `absorption/phenotype-canonicalization/` | `refs/preserved/` and a bundle       |
| Dependency forks                 |      11 | not copied; every ref preserved                                       | `refs/preserved/<repo>/`, 2,950 refs |

Three points are worth carrying forward.

**A bundle cannot preserve a large history.** GitHub rejects any file over
100 MB, so `PhenoMLX-temp` at 187 MB could never be stored that way. History now
goes in as real git objects under `refs/preserved/`, which has no such ceiling
and restores with a plain fetch.

**Counting files is not proving them.** The private ops repos were verified by
comparing git blob ids between source and destination. Since a blob id is a
content hash, equality per path proves every file byte-identical; 769 files
across nine repos matched.

**A fork's default branch is not its work.** Several `zz-*` forks have an
inherited default branch identical to upstream while the real work sits
elsewhere, so branch-diff exports silently dropped it. Preserving every ref made
the export self-proving and avoided guessing. `Bifrost` alone carried 1,664 refs.

## Verification is required, not assumed

This index records intent, not proof. Three entries above were marked absorbed
while their content was materially incomplete, and nothing in the record said so:

| Repo            | Recorded as                        | Actually present | Missing            |
| --------------- | ---------------------------------- | ---------------- | ------------------ |
| `BytePort`      | absorbed                           | 317 of 680       | **362**            |
| `PhenoMLX-temp` | absorbed, `.cargo-target` excluded | 1,059 of 5,736   | **303 real files** |
| `SessionLedger` | absorbed                           | 811 of 934       | **123**            |

788 files in total. None of it was discoverable after deleting the sources, and a
plain file copy does not fail loudly when it misses files — `.gitignore` silently
drops whole subtrees, and a source tree can change layout between snapshots so
that path overlap looks like coverage.

### Prove it before deleting anything

```bash
python scripts/verify_absorption.py --all          # 30 absorptions, 0 incomplete
python scripts/verify_absorption.py <repo> --json  # machine-readable
python scripts/scan_absorption_secrets.py absorption/
```

`verify_absorption.py` compares every absorbed tree against its live source tree,
counts files that git ignores, resolves deliberately withheld files against the
private registry, and separates build artefacts from real content. It exits
non-zero when something is genuinely missing.

`scan_absorption_secrets.py` exists because an ad-hoc scan once checked AWS,
GitHub, Slack, tailnet and PEM formats but not the OpenAI/Anthropic/HF/Google/
Stripe ones. Real keys reached a candidate commit and were caught by GitHub Push
Protection, not by us. Nothing leaked — the push was rejected — but the lesson is
that a list of "the providers I thought of" is not a scanner.

### Rule for future waves

An entry may move to "absorbed" only after `verify_absorption.py <repo>` reports
complete for that repo. Delete the source only after that, and record the
verification date alongside the disposition.

### Verified then deleted (2026-11-12)

Nine repos were deleted only after `scripts/verify_absorption.py` reported each
complete against its live source. Verification ran immediately before deletion,
in the same pass, so no repo was deleted on a stale result.

| Repo                    | Checked | Note                                                                                        |
| ----------------------- | ------- | ------------------------------------------------------------------------------------------- |
| `Authvault`             | 332/332 |                                                                                             |
| `SessionLedger`         | 934/934 | 123 files had been recovered earlier the same day                                           |
| `ResearchLedger`        | 318/318 |                                                                                             |
| `cvp-fixture`           | 17/17   |                                                                                             |
| `netweave-3`            | 30/30   |                                                                                             |
| `phenotype-router-spec` | 22/22   |                                                                                             |
| `herdr-session-adapter` | 12/12   |                                                                                             |
| `rule30-research`       | 6/6     |                                                                                             |
| `BytePort`              | 676/680 | 3 withheld to the private registry, 1 binary artefact excluded, 362 files recovered earlier |

Each deletion was confirmed with a following API call returning 404.

The credentials that prompted this cleanup were confirmed dead by the operator
before deletion proceeded: the `canvasApp` OpenAI keys and BytePort's
`byteport-ghkey.pem` are no longer valid, so no rotation was outstanding.

## Worklog references

- **MRG-13..MRG-16** (2026-11-11): Multi-branch consolidation. Full clones rather than shallow, union of file paths across every ref compared against the default branch to find branch-only content, `git bundle create --all` per repo verified with `git bundle verify` inside the source clone, bundles pushed to the private registry via the Git Data API. Total 48 files absorbed.

- **MRG-01..MRG-12** (2026-11-11): Twelve-repo consolidation. Content-based classifier over 3,526 files (tailnet CGNAT addresses, `.ts.net` hostnames, Cloudflare zone ids, credential filenames, key formats), with canonical test vectors whitelisted so they are not mistaken for secrets: W3C traceparent `4bf92f35`/`0af76519`, RFC 4231 HMAC KAT `b0344c61`, CGNAT bounds `100.64.0.0`/`100.64.0.1`, magic DNS `100.100.100.100`, placeholder `ghp_abcdefgh`. Result: 1,708 code files to `absorption/`, 194 data files to `PhenoRegistry/repos/`, 0 copy errors. A post-copy scan of the public absorption tree found no private identifiers; the only matches were the AWS documentation placeholder `AKIAIOSFODNN7EXAMPLE` and the fake token `ghp_abcdefgh...`, both in test fixtures.

- **PRE-EXISTING LEAK NOTED** (2026-11-11): the same Cloudflare zone id and the `<tailnet-host>` hostname are already committed in this public repo under `absorption/PhenoInfra/`: `docs/governance/oci-acquire-hook-chain.md`, `iac/landing-bootstrap/src/main.rs`, `iac/oci-post-acquire/src/main.rs`, `iac/scripts/install-windows-runner.ps1`, `iac/scripts/README-windows-runner.md`, `iac/scripts/README.md`, `iac/ansible/inventory.yml.example`, `docs/runbooks/windows-desktop-runner.md`. Also `absorption/resume-all/bin/tailscale-watch` (`100.96.0.0`). Not introduced by this wave and not removed by it; flagged for separate remediation.

- **MCP-01** (2026-11-10): PhenoMCPServers delta absorption — file-level diff found 353 identical, 46 missing, 119 diverged. Absorbed the 46 missing files verbatim, renamed and narrowed `.github/workflows/catalog.yml` to `phenomcp-catalog.yml`, and verified the validation pipeline in-tree (`validate_catalog`, `validate_fork_parents`, `validate_bundle_wiring` all OK; `validate_stale_patterns` and `check_driver_mcp_sync` advisory with exit 0; 29 passed / 2 pre-existing failures on the absorbed tests, 60 passed on the substrate + pheno-org suites). The 2 failures reproduce identically on a clean source clone, so they are upstream defects, not regressions.
- **HF-01** (2026-10-29): `hfscope` vendored-copy disposition — verified both declared upstreams deleted, confirmed `cmd/` absent, `make build` unbuildable, `templ generate` required before vet can pass, and 10 non-gofmt files. Recorded as EXCLUDE (not first-class) and excluded from all CI and module sweeps.

- **SPR-01..SPR-05** (2026-09-27): Repo-sprawl consolidation pass — five standalone repos assessed, absorbed as plain copies under `absorption/`, each given a `PROVENANCE.md` (source repo/commit/date/rationale) and a `docs/absorbed-from/<repo>/README.md` disposition README. Root Cargo workspace re-validated after absorption (`cargo metadata --no-deps` OK). Source repos to be archived after this wave.

- **L5-111** (2026-06-18): Trivial governance batch — verify P8 (phenotype-hub → phenotype-infra) and P9 (vibeproxy-monitoring-unified retirement) G19 absorption, add L5-### traceability to the index, and post a follow-up deprecation pointer on each archived source repo. See `phenotype-registry/ECOSYSTEM_MAP.md` §6 for the original P5/P8/P9 actions; this entry documents the G19 retrospective verification pass.

## Adding entries

When a future wave absorbs an archived repo into `phenotype-infra`:

1. Add `docs/absorbed-from/<repo>/README.md` with source URL, absorption date, disposition, and canonical mapping.
2. Append a row to the appropriate wave section in this file.
3. Add a `Worklog ref` column entry pointing to the L5-### tracking ID (or the wave/req_id used by the registry).
