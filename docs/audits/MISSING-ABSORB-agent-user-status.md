# Missing-absorb forensics: `agent-user-status`

**Measured:** 2026-09-19 (this session). Methods: `gh api`, `git cat-file`,
`git log --all --diff-filter=A`, `git bundle list-heads`, `mdfind`, bounded `find`,
filesystem probes. Every negative below was actually tested, not inferred.

## Verdict

`agent-user-status` (Python ≥3.12, 615 KB, 35 source files + stdio MCP server +
12 Swift native-monitor files, 91 unit tests; see
`docs/absorption/agent-user-status/README.md` for the full profile) is **not
recoverable from any location we can reach**. The record trail claims three
homes; all three are empty.

## Where the records say it should be, and what was tested

| Claimed home | Record | Test run | Result |
|---|---|---|---|
| GitHub `KooshaPari/agent-user-status` (archived 2026-07-17) | `projects/agent-user-status.json` (`archive_method: gh repo archive`) | `gh api repos/KooshaPari/agent-user-status` | **404. Not archived — deleted.** No redirect (clone over HTTPS: "Repository not found"). Absent from `users/KooshaPari/repos?type=all` (37 repos incl. archived/forks), from `gh repo list` (50), and from search. |
| `phenotype-tooling` @ `salvage/phenotype-tooling-workspace-2026-07-15`, commit `29ce5dd4` | `projects/agent-user-status.json:absorbed_commit`; `docs/absorption/agent-user-status/README.md` | `git cat-file -t 29ce5dd4` in `phenotype-tooling`, `PhenoTooling`, `_full_tooling`, `phenotype-tooling-mergify`; branch/reflog scan; `git fetch` (remote gone: `git@github.com:KooshaPari/phenotype-tooling.git` → 404; repo does not exist on GitHub under any spelling) | **Commit does not exist anywhere.** Branch `salvage/phenotype-tooling-workspace-2026-07-15` does not exist locally or remotely. |
| Source tree snapshot @ `1122875483...` (2026-06-20) | `docs/absorption/agent-user-status/README.md:4` | Probed in all local tooling checkouts and in 8 preservation bundles: `zz-archive/git-bundles-20260910/phenotype-archive.bundle`, `PhenotypeBackups/20260809/{wip-preservation,FULL-224928,FULL-225034,wip-priority-A}`, `phase-2-snapshots/{home-recovery-2026-07,repos-pre-delete-dirty-snapshots}` | **Absent from every bundle.** Neither SHA resolves anywhere. No checkout, no site-packages install, no Trash copy. |

## What survives on this machine (all non-source)

- Registry/boundary/doc records in 6 checkouts (`PhenoShared`, `pheno`,
  `phenotype-registry-wtrees/phenotype-registry`, `phenoAI`, …): README, boundary
  doc, `projects/agent-user-status.json`, absorption justification
  (`audits/absorption-justifications/agent-user-status-2026-07-17.md`, unredacted
  GitHub URL), 2026-04-24 org audit scorecard.
- 5 disabled LaunchAgents: `~/Library/LaunchAgents/com.phenotype.agent-user-status*.plist.disabled`
  (statusd, cursor-tracker, webcam-eye-tracker, tray).
- Runtime residue: `~/.local/share/agent-imessage/state/*.{out,err}.log` (daemon
  last failed 2026-07-16 with "can't open file .../agent-user-statusd"), empty
  `correction_events.jsonl`, `~/Library/HTTPStorages/agent-user-status-native-monitor/`,
  CrashReporter plists for `AgentUserStatusMonitor` (crash 2026-05-07).
- Indirect reference: `phenotype-tooling/docs/absorbed-from-phenotype-teamcomm/docs/SDD.md:147,347`
  describes the 5-state status model but contains no code.

## How the loss happened (best-supported reconstruction)

1. 2026-07-17: audited and absorbed into `phenotype-tooling` on branch
   `salvage/phenotype-tooling-workspace-2026-07-15` @ `29ce5dd4`; source archived
   on GitHub per record (post-archival 404 + no redirect means it was later
   **deleted**, not just archived).
2. `phenotype-tooling` itself was later deleted from GitHub (repo 404, no
   redirect) and the local checkouts never contained the salvage branch —
   the absorption landed on a branch that was never pushed or was pushed only
   to the now-deleted remote.
3. With the source archived-then-deleted and the absorbing branch unrecoverable,
   the only surviving copies were the registry metadata.

This is the second confirmed "record claims absorbed, content does not exist"
case (after `agent-user-status` was flagged 2026-09-18). It upgrades the
missing-absorb class from suspicion to provenance-verified data loss.

## Practical recovery options (all currently dead ends)

- GitHub restore via UI/API: requires the repo to be archived, not deleted.
  Deleted-repo restore is only possible within 90 days via GitHub support.
  Archive date 2026-07-17 → window closes ~2026-10-15. **Action available now:
  contact GitHub support to request restore of `KooshaPari/agent-user-status`.**
- Forks/clones elsewhere: GitHub code search for `agent_imessage_mcp` and repo
  search for the name found nothing (private deleted repos don't surface).
- Time Machine / APFS snapshots: not checked by this pass (out of scope,
  operator-owned backups).

## Deltas to lineage classification

- `projects/agent-user-status.json` `status: absorbed` → truth is
  **absorbed-then-lost** (source deleted, absorption commit unrecoverable).
- `docs/audits/ABSORPTION-STATUS-TRUTH.md` bucket (b) gains a hard-confirmed
  entry: destination claimed at `crates/agent-user-status/` in a repo that
  itself no longer exists on the remote.
- Both prior session notes were wrong in one detail: the harness-supplied
  summary said "survives as disposition records in 4 checkouts" — the count is
  6, including `phenoAI`.
