# TOMBSTONE 2026-11-19

Read-only audit executed 2026-11-19 (session context 19:01:07 -08:00) from `C:\Windows`. Repo: `C:\Users\koosh\PhenoShared`. No repository files modified except this report; no commits/pushes; no GitHub settings changed.

## Q1. Does `KooshaPari/phenotype-canonicalization` exist right now?

**Answer:** Present.

**Command**
```cmd
gh api repos/KooshaPari/phenotype-canonicalization --jq ".created_at"
```

**Output**
```text
2026-11-16T09:11:15Z
```

**Interpretation:** Non-404 response with `created_at` returned; repository exists.

## Q2. If present, what is its main sha, and does it equal the preserved tip `570e2c73aff565620a2c518a37d258981a31ca9e`?

**Answer:** Main SHA is `570e2c73aff565620a2c518a37d258981a31ca9e`. It equals the specified preserved tip and equals the preserved ref in PhenoRegistry.

**Commands**
```cmd
gh api repos/KooshaPari/phenotype-canonicalization/commits/main --jq ".sha"
git ls-remote --refs https://github.com/KooshaPari/PhenoRegistry.git refs/preserved/phenotype-canonicalization/heads/main
gh api repos/KooshaPari/phenotype-canonicalization --jq ".default_branch"
```

**Outputs**
```text
$ gh api repos/KooshaPari/phenotype-canonicalization/commits/main --jq ".sha"
570e2c73aff565620a2c518a37d258981a31ca9e

$ git ls-remote --refs https://github.com/KooshaPari/PhenoRegistry.git refs/preserved/phenotype-canonicalization/heads/main
570e2c73aff565620a2c518a37d258981a31ca9e	refs/preserved/phenotype-canonicalization/heads/main

$ gh api repos/KooshaPari/phenotype-canonicalization --jq ".default_branch"
main
```

**Comparison:** live `main` SHA (`570e2c73aff565620a2c518a37d258981a31ca9e`) == expected preserved tip (`570e2c73aff565620a2c518a37d258981a31ca9e`) == PhenoRegistry preserved ref `refs/preserved/phenotype-canonicalization/heads/main` (`570e2c73aff565620a2c518a37d258981a31ca9e`).

## Q3. How many live repositories exist now, and has the set changed since the 2026-11-17 baseline?

**Answer:** Current count is **118**. Baseline count is **118** (from `docs/absorption-ledger/estate-snapshot.json`, captured `2026-11-17T12:47:49Z`). No set changes detected: names present now but absent from baseline = none; baseline names now gone = none.

**Commands**
```cmd
gh repo list KooshaPari --limit 500 --json name,createdAt
gh repo list KooshaPari --limit 500 --json name -q "length"
powershell -NoProfile -Command "(Get-Content 'C:\Users\koosh\PhenoShared\docs\absorption-ledger\estate-snapshot.json' -Raw | ConvertFrom-Json).repos.PSObject.Properties.Name | Sort-Object"
powershell -NoProfile -Command "$b=(Get-Content 'C:\Users\koosh\PhenoShared\docs\absorption-ledger\estate-snapshot.json' -Raw | ConvertFrom-Json).repos.PSObject.Properties.Name; $c=(gh repo list KooshaPari --limit 500 --json name -q '.[].name'); 'PRESENT_NOW_ABSENT_BASELINE'; $c | Where-Object { $_ -notin $b }; 'ABSENT_NOW_PRESENT_BASELINE'; $b | Where-Object { $_ -notin $c }"
powershell -NoProfile -Command "$d=Get-Content 'C:\Users\koosh\PhenoShared\docs\absorption-ledger\estate-snapshot.json' -Raw | ConvertFrom-Json; $d.count"
```

**Outputs**
```text
$ gh repo list KooshaPari --limit 500 --json name -q "length"
118

$ powershell -NoProfile -Command "$d=Get-Content 'C:\Users\koosh\PhenoShared\docs\absorption-ledger\estate-snapshot.json' -Raw | ConvertFrom-Json; $d.count"
118

$ powershell -NoProfile -Command "$b=(Get-Content 'C:\Users\koosh\PhenoShared\docs\absorption-ledger\estate-snapshot.json' -Raw | ConvertFrom-Json).repos.PSObject.Properties.Name; $c=(gh repo list KooshaPari --limit 500 --json name -q '.[].name'); 'PRESENT_NOW_ABSENT_BASELINE'; $c | Where-Object { $_ -notin $b }; 'ABSENT_NOW_PRESENT_BASELINE'; $b | Where-Object { $_ -notin $c }"
PRESENT_NOW_ABSENT_BASELINE
ABSENT_NOW_PRESENT_BASELINE
```

```text
$ gh repo list KooshaPari --limit 500 --json name,createdAt
[{"createdAt":"2026-11-12T11:17:10Z","name":"host-ops"},{"createdAt":"2026-02-28T23:49:47Z","name":"AgilePlus"},{"createdAt":"2026-04-03T08:14:12Z","name":"PhenoShared"},{"createdAt":"2026-09-11T10:27:09Z","name":"KCode"},{"createdAt":"2026-11-15T00:37:40Z","name":"slipstream"},{"createdAt":"2026-04-04T08:21:22Z","name":"PhenoRegistry"},{"createdAt":"2026-05-01T03:53:56Z","name":"OmniRoute"},{"createdAt":"2026-02-20T03:20:13Z","name":"Tracera"},{"createdAt":"2026-11-11T08:13:56Z","name":"kimaki"},{"createdAt":"2025-05-10T05:31:02Z","name":"zz-pause-Localbase"},{"createdAt":"2026-03-25T09:09:18Z","name":"ShareCLI"},{"createdAt":"2026-03-10T09:46:06Z","name":"Dino"},{"createdAt":"2026-08-04T06:41:23Z","name":"Khostty"},{"createdAt":"2026-11-17T11:34:27Z","name":"clap-ext"},{"createdAt":"2026-11-06T01:15:48Z","name":"PhenoVCS-rb-archive-20261106"},{"createdAt":"2026-11-14T17:37:34Z","name":"phenotype-landing"},{"createdAt":"2026-11-08T23:37:10Z","name":"phenotype-archives-20261108"},{"createdAt":"2026-10-06T09:28:08Z","name":"Personal"},{"createdAt":"2026-11-14T17:22:26Z","name":"dagrun"},{"createdAt":"2026-06-08T02:39:51Z","name":"Melosviz"},{"createdAt":"2026-04-19T01:47:45Z","name":"PhenoMLX"},{"createdAt":"2026-11-14T17:32:47Z","name":"audit-snapshot-OmniRoute"},{"createdAt":"2026-11-14T17:37:07Z","name":"audit-snapshot-agentapi"},{"createdAt":"2026-11-14T17:35:02Z","name":"audit-snapshot-tooling"},{"createdAt":"2026-11-14T17:31:49Z","name":"audit-snapshot-AgilePlus"},{"createdAt":"2026-11-14T17:30:43Z","name":"audit-snapshot-pheno"},{"createdAt":"2026-11-14T17:31:34Z","name":"audit-snapshot-PhenoVCS"},{"createdAt":"2026-11-14T17:33:45Z","name":"audit-snapshot-hwLedger"},{"createdAt":"2026-11-16T13:34:03Z","name":"zz-HexaKit"},{"createdAt":"2026-11-16T13:33:53Z","name":"zz-argis-extensions"},{"createdAt":"2026-11-14T23:17:29Z","name":"cliproxyapi-plusplus"},{"createdAt":"2026-11-09T01:18:59Z","name":"PhenoTooling"},{"createdAt":"2026-11-16T13:29:08Z","name":"browser-infra"},{"createdAt":"2026-11-14T23:17:08Z","name":"hwledger"},{"createdAt":"2026-11-16T09:11:21Z","name":"phenotype-cvp-audit-2026-09-14"},{"createdAt":"2026-11-16T09:11:15Z","name":"phenotype-canonicalization"},{"createdAt":"2026-11-16T09:11:08Z","name":"phenoDesign-visual-production-v2"},{"createdAt":"2026-09-10T04:37:32Z","name":"PhenoFabric"},{"createdAt":"2026-02-23T11:17:23Z","name":"zz-pause-inc-Parpoura"},{"createdAt":"2026-11-15T06:16:01Z","name":"claude-plugins-official"},{"createdAt":"2026-11-14T23:17:49Z","name":"argis-extensions-preserved-20261114"},{"createdAt":"2026-11-14T23:17:17Z","name":"hexakit"},{"createdAt":"2026-11-14T22:57:47Z","name":"host-credentials"},{"createdAt":"2026-11-14T17:37:48Z","name":"cvp-fixture"},{"createdAt":"2026-11-14T17:33:58Z","name":"audit-snapshot-HexaKit"},{"createdAt":"2026-11-14T17:33:33Z","name":"audit-snapshot-argis"},{"createdAt":"2026-11-14T17:30:04Z","name":"PhenoVCS"},{"createdAt":"2026-11-14T17:26:36Z","name":"audit-system"},{"createdAt":"2026-11-14T17:24:01Z","name":"BytePort"},{"createdAt":"2026-11-14T17:23:37Z","name":"zz-aa-dep-AirLock"},{"createdAt":"2026-11-14T17:22:44Z","name":"rule30-research"},{"createdAt":"2026-11-14T17:22:34Z","name":"harness-ops"},{"createdAt":"2026-06-18T05:43:33Z","name":"PhenoApps"},{"createdAt":"2026-08-28T10:02:48Z","name":"KooshaPari"},{"createdAt":"2026-05-01T01:28:07Z","name":"zz-ref-HeliosLite"},{"createdAt":"2026-02-23T11:16:49Z","name":"Civis"},{"createdAt":"2024-09-26T02:27:24Z","name":"chatta"},{"createdAt":"2026-11-06T01:17:19Z","name":"zz-Parpoura-rb-archive-20261106"},{"createdAt":"2026-11-06T01:17:22Z","name":"zz-QuadSGM-rb-archive-20261106"},{"createdAt":"2026-11-06T01:17:33Z","name":"zz-localbase-rb-archive-20261106"},{"createdAt":"2026-02-23T11:43:06Z","name":"zz-pause-inc-QuadSGM"},{"createdAt":"2026-11-09T01:15:53Z","name":"argis-extensions"},{"createdAt":"2026-02-20T03:22:04Z","name":"zz-pause-unk-Thegent"},{"createdAt":"2026-06-14T22:55:44Z","name":"Substrate"},{"createdAt":"2026-02-24T04:33:22Z","name":"Portage"},{"createdAt":"2026-05-01T14:40:35Z","name":"Pine"},{"createdAt":"2026-07-22T08:25:05Z","name":"CivicWarfare"},{"createdAt":"2026-10-09T06:32:17Z","name":"herdr"},{"createdAt":"2026-09-16T23:03:12Z","name":"cmux"},{"createdAt":"2026-02-24T03:25:14Z","name":"zz-ref-HeliosCLI"},{"createdAt":"2026-11-09T01:16:17Z","name":"zz-archive-grapheon"},{"createdAt":"2026-04-24T19:42:34Z","name":"zz-zz-agentcheck-PhenoInfra"},{"createdAt":"2025-06-27T00:24:43Z","name":"PhenoBot"},{"createdAt":"2026-06-15T02:29:04Z","name":"PhenoLab"},{"createdAt":"2025-06-07T23:06:53Z","name":"zz-pause-ref-AtomsTech"},{"createdAt":"2026-04-26T00:45:56Z","name":"zz-zz-agentcheck-zz-pause-Agentora"},{"createdAt":"2026-11-06T01:30:40Z","name":"Stashly-rb-archive-20261106-exact"},{"createdAt":"2026-11-06T01:15:58Z","name":"Quillr-rb-archive-20261106"},{"createdAt":"2026-11-06T01:15:57Z","name":"Pine-rb-archive-20261106"},{"createdAt":"2026-11-06T01:15:45Z","name":"PhenoFastMCP-rb-archive-20261106"},{"createdAt":"2026-03-01T10:44:14Z","name":"PhenoDesign"},{"createdAt":"2026-02-26T13:11:29Z","name":"HeliosLab"},{"createdAt":"2026-11-08T07:21:13Z","name":"Tasken-rb-archive-20261108"},{"createdAt":"2026-11-08T07:21:06Z","name":"Sidekick-rb-archive-20261108"},{"createdAt":"2026-05-18T02:39:15Z","name":"WorldSphereMod"},{"createdAt":"2026-11-08T07:12:18Z","name":"exports-temp-archive-20261108"},{"createdAt":"2026-09-27T18:48:34Z","name":"HarnessDesk"},{"createdAt":"2026-11-06T01:25:12Z","name":"Tasken-archive-20261106-exact"},{"createdAt":"2026-11-06T01:17:41Z","name":"zz-rich-cli-kit-archive-20261106"},{"createdAt":"2026-11-06T01:17:26Z","name":"Tasken-archive-20261106"},{"createdAt":"2026-11-06T01:17:17Z","name":"Tracera-rb-archive-20261106"},{"createdAt":"2026-11-06T01:17:15Z","name":"Stashly-archive-20261106"},{"createdAt":"2026-11-06T01:16:03Z","name":"phenotype-registry-rb-archive-20261106"},{"createdAt":"2026-11-06T01:17:01Z","name":"Sidekick-archive-20261106"},{"createdAt":"2026-11-06T01:16:10Z","name":"Stashly-rb-archive-20261106"},{"createdAt":"2026-11-06T01:15:16Z","name":"AgilePlus-rb-archive-20261106"},{"createdAt":"2026-11-06T01:15:17Z","name":"forgecode-rb-archive-20261106"},{"createdAt":"2026-11-06T01:15:16Z","name":"Melosviz-rb-archive-20261106"},{"createdAt":"2026-11-06T00:54:24Z","name":"PhenoProc-archive-20261106"},{"createdAt":"2026-11-06T00:50:20Z","name":"work-archive-20261105"},{"createdAt":"2026-11-05T08:34:13Z","name":"claude-remember"},{"createdAt":"2026-10-17T05:23:03Z","name":"phenoreg-browser-audit"},{"createdAt":"2026-10-07T23:41:45Z","name":"shopping-home"},{"createdAt":"2026-02-27T12:47:22Z","name":"heliosApp"},{"createdAt":"2026-04-02T18:27:21Z","name":".github"},{"createdAt":"2026-09-17T10:53:07Z","name":"zz-zz-agentcheck-docs-5"},{"createdAt":"2026-06-17T00:03:41Z","name":"zz-zz-agentcheck-PhenoGfx"},{"createdAt":"2026-04-05T12:51:04Z","name":"PhenoAI"},{"createdAt":"2026-09-19T03:30:10Z","name":"ratatui"},{"createdAt":"2026-04-24T23:08:18Z","name":"zz-pause-inc-FocalPoint"},{"createdAt":"2025-04-03T18:12:43Z","name":"zz-pause-inc-AgsLag"},{"createdAt":"2026-07-17T10:00:25Z","name":"StealthStartup"},{"createdAt":"2026-07-29T00:38:51Z","name":"zz-archive-source-drops-2026-07"},{"createdAt":"2026-07-17T09:31:43Z","name":"zz-archive-4sgm-archive"},{"createdAt":"2026-07-16T01:10:29Z","name":"zz-archive-AgilePlus-recovery-evidence"},{"createdAt":"2026-07-15T03:28:01Z","name":"zz-archive-pheno-predict"},{"createdAt":"2026-07-15T03:27:56Z","name":"zz-archive-pheno-drift-detector"},{"createdAt":"2026-07-15T03:27:02Z","name":"zz-archive-agileplus-spec-harmonizer-tool"}]
```

```text
$ powershell -NoProfile -Command "(Get-Content 'C:\Users\koosh\PhenoShared\docs\absorption-ledger\estate-snapshot.json' -Raw | ConvertFrom-Json).repos.PSObject.Properties.Name | Sort-Object"
.github
AgilePlus
AgilePlus-rb-archive-20261106
argis-extensions
argis-extensions-preserved-20261114
audit-snapshot-agentapi
audit-snapshot-AgilePlus
audit-snapshot-argis
audit-snapshot-HexaKit
audit-snapshot-hwLedger
audit-snapshot-OmniRoute
audit-snapshot-pheno
audit-snapshot-PhenoVCS
audit-snapshot-tooling
audit-system
browser-infra
BytePort
chatta
CivicWarfare
Civis
clap-ext
claude-plugins-official
claude-remember
cliproxyapi-plusplus
cmux
cvp-fixture
dagrun
Dino
exports-temp-archive-20261108
forgecode-rb-archive-20261106
HarnessDesk
harness-ops
heliosApp
HeliosLab
herdr
hexakit
host-credentials
host-ops
hwledger
KCode
Khostty
kimaki
KooshaPari
Melosviz
Melosviz-rb-archive-20261106
OmniRoute
Personal
PhenoAI
PhenoApps
PhenoBot
PhenoDesign
phenoDesign-visual-production-v2
PhenoFabric
PhenoFastMCP-rb-archive-20261106
PhenoLab
PhenoMLX
PhenoProc-archive-20261106
phenoreg-browser-audit
PhenoRegistry
PhenoShared
PhenoTooling
phenotype-archives-20261108
phenotype-canonicalization
phenotype-cvp-audit-2026-09-14
phenotype-landing
phenotype-registry-rb-archive-20261106
PhenoVCS
PhenoVCS-rb-archive-20261106
Pine
Pine-rb-archive-20261106
Portage
Quillr-rb-archive-20261106
ratatui
rule30-research
ShareCLI
shopping-home
Sidekick-archive-20261106
Sidekick-rb-archive-20261108
slipstream
Stashly-archive-20261106
Stashly-rb-archive-20261106
Stashly-rb-archive-20261106-exact
StealthStartup
Substrate
Tasken-archive-20261106
Tasken-archive-20261106-exact
Tasken-rb-archive-20261108
Tracera
Tracera-rb-archive-20261106
work-archive-20261105
WorldSphereMod
zz-aa-dep-AirLock
zz-archive-4sgm-archive
zz-archive-AgilePlus-recovery-evidence
zz-archive-agileplus-spec-harmonizer-tool
zz-archive-grapheon
zz-archive-pheno-drift-detector
zz-archive-pheno-predict
zz-archive-source-drops-2026-07
zz-argis-extensions
zz-HexaKit
zz-localbase-rb-archive-20261106
zz-Parpoura-rb-archive-20261106
zz-pause-inc-AgsLag
zz-pause-inc-FocalPoint
zz-pause-inc-Parpoura
zz-pause-inc-QuadSGM
zz-pause-Localbase
zz-pause-ref-AtomsTech
zz-pause-unk-Thegent
zz-QuadSGM-rb-archive-20261106
zz-ref-HeliosCLI
zz-ref-HeliosLite
zz-rich-cli-kit-archive-20261106
zz-zz-agentcheck-docs-5
zz-zz-agentcheck-PhenoGfx
zz-zz-agentcheck-PhenoInfra
zz-zz-agentcheck-zz-pause-Agentora
```

**Delta summary**
- Present now but absent from baseline (with `createdAt`): none.
- Baseline names now gone: none.

## Q4. Is restoration still a replay of preserved refs? For up to 5 of the newly appeared repositories, compare the live default-branch sha with `refs/preserved/<name>/*` in the registry and report how many match exactly.

**Answer:** Cannot determine from newly appeared repositories in this audit because there are 0 newly appeared repositories relative to the 2026-11-17 baseline (Q3). Therefore, 0 repositories were compared under this specific criterion and 0/0 exact matches can be reported from that set.

**Evidence gathered**
```cmd
git ls-remote https://github.com/KooshaPari/PhenoRegistry.git "refs/preserved/*"
```
Command was run; output was large/truncated in capture, but a targeted preserved-ref lookup confirmed at least:
```text
570e2c73aff565620a2c518a37d258981a31ca9e	refs/preserved/phenotype-canonicalization/heads/main
```
(see Q2). No newly appeared repositories existed to select for default-branch-vs-preserved comparison.

## Step 3 verification addendum (2026-11-19)

The step 3 checks were repeated during the ledger reconciliation. Results:

```text
$ gh api repos/KooshaPari/phenotype-canonicalization/commits/main --jq .sha
570e2c73aff565620a2c518a37d258981a31ca9e

$ git ls-remote --refs https://github.com/KooshaPari/PhenoRegistry.git refs/preserved/phenotype-canonicalization/heads/main
570e2c73aff565620a2c518a37d258981a31ca9e	refs/preserved/phenotype-canonicalization/heads/main

$ gh repo list KooshaPari --limit 500 --json name --jq "length"
118
```

`KooshaPari/phenotype-canonicalization` exists, its live `main` SHA matches the preserved tip `570e2c73aff565620a2c518a37d258981a31ca9e` exactly, and the live repository count is 118. This is not a test of the tombstone: the repository was recreated on 2026-11-16 (as shown in Q1), before tombstones existed on 2026-11-17, and has not been deleted since. The tombstone remains untested; the SHA match only confirms parity of a repository that never underwent a tombstone-driven deletion.

## Verdict

**Verdict:** Tombstone remains untested. No repository set change was observed versus the 2026-11-17 baseline, and `phenotype-canonicalization` exists with a live `main` SHA equal to its preserved tip, but that repository predates tombstones and has not been deleted since. Restoration replay status for newly appeared repos cannot be determined from this check because there were no newly appeared repos to compare; available evidence for `phenotype-canonicalization` is consistent with replay of a preserved ref, not with tombstone behavior.
