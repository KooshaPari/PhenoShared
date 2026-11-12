# AgilePlus History Forensic Investigation

**Scope:** read-only forensic investigation of `KooshaPari/AgilePlus` (GitHub) only.
**Date:** 2026-11-12 (UTC 09:19–09:29Z)
**Question:** do commits `98c3ecd` and `b6008ae` exist, what do they reference, what is the source
evidence for the "acceptance chain" and the "atomic AcceptedWork" claim, and is it represented in
the repository's current default branch?
**Mode:** read-only. No edits, no issues, no pushes. No inference from a single missing identifier
or a 404 — every negative below was corroborated by at least two independent probes.

---

## 0. Environment / method note

- `gh` authenticated as `KooshaPari` (keyring, `gh_o_*`), token valid at time of run.
- No local `AgilePlus` clone exists on this host under the canonical worktree root
  (`~/CodeProjects/Phenotype/repos/`); `~/CodeProjects/Phenotype/repos/AgilePlus-space/` contains
  no `.git` at `maxdepth 3`. Local `git` history was therefore unavailable, and **all** history
  evidence below is from the GitHub REST API (`/commits`, `/git/trees`, `/contents`, `/compare`,
  `/search/code`), which serves the same object graph as local `git log`.
- Repo metadata: `KooshaPari/AgilePlus` — public, not archived, default branch `main`,
  last push `2026-11-12T07:32:38Z`. `main` HEAD at time of run:
  `8699676312dfcd787435221a7926a407af920fc6` (2026-11-10T01:59:57Z,
  `fix(deps): update libsqlite3-sys to 0.39.1 via rusqlite 0.41 (#1207)`).

---

## 1. Cited commit identifiers — BOTH EXIST

| Cited | Full SHA | Date (committer) | Subject | Files touched |
|---|---|---|---|---|
| `98c3ecd` | `98c3ecd477a7ef2050287c668e5159e76185d9e2` | 2026-10-04T19:49:12Z | `docs(architecture): codify tailnet-first deployment doctrine` | **1 file, added, +124/-0** — `docs/architecture/NETWORK_DEPLOYMENT_DOCTRINE.md` |
| `b6008ae` | `b6008ae02f903055f4eaafdc1c18d122116babe0` | 2026-10-04T19:50:25Z | `docs(recovery): codify complete forward WBS and release path` | **1 file, added, +319/-0** — `verification/FORWARD_WBS_2026-10-04.md` |

Author of both: Koosha Paridehpour. Parents: `b4de853ad…` and `545b41d7…` respectively.

Commands:
```bash
gh api repos/KooshaPari/AgilePlus/commits/98c3ecd --jq '{sha,date:.commit.committer.date,msg:.commit.message,files:(.files|length)}'
gh api repos/KooshaPari/AgilePlus/commits/b6008ae --jq '{sha,date:.commit.committer.date,msg:.commit.message,files:(.files|length)}'
gh api repos/KooshaPari/AgilePlus/commits/<sha> --jq '.files[]|"\(.status) +\(.additions)/-\(.deletions) \(.filename)"'
```

**Verdict: neither identifier is a 404 and neither is fabricated.** Both resolve to real commits
one minute apart on 2026-10-04.

### 1a. Correction to the cited pairing

The prior conversation paired `98c3ecd` with `spec/product/mature-contract.v1.json`. **That
pairing is wrong.** `98c3ecd` added exactly one file — `docs/architecture/NETWORK_DEPLOYMENT_DOCTRINE.md`
— and did **not** touch `spec/product/mature-contract.v1.json` at all. The pairing that *is*
correct is `b6008ae` → `verification/FORWARD_WBS_2026-10-04.md` (that commit created it).

---

## 2. Both commits ARE ancestors of the current default branch (`main`)

This is the load-bearing check for "represented in current repo default branch".

```bash
gh api repos/KooshaPari/AgilePlus/compare/98c3ecd...main --jq '{status,ahead_by,behind_by,merge_base:.merge_base_commit.sha}'
gh api repos/KooshaPari/AgilePlus/compare/b6008ae...main --jq '{status,ahead_by,behind_by,merge_base:.merge_base_commit.sha}'
```

| Compare | status | ahead_by | behind_by | merge_base_commit.sha |
|---|---|---|---|---|
| `98c3ecd...main` | `ahead` | 213 | **0** | `98c3ecd477a7ef2050287c668e5159e76185d9e2` |
| `b6008ae...main` | `ahead` | 211 | **0** | `b6008ae02f903055f4eaafdc1c18d122116babe0` |

`behind_by = 0` and the merge base equals the cited commit itself: **both cited commits are
direct ancestors of `main`**, 211–213 commits behind current HEAD. No branch contains them as a
tip (`/branches-where-head` returns empty), which is expected for two-week-old commits and is not
evidence of absence from the branch.

**Verdict: yes — both cited commits, and the artifacts they introduced, are represented in the
current default branch's history.**

---

## 3. Cited path existence at each ref

`gh api repos/KooshaPari/AgilePlus/git/trees/<ref>?recursive=1` (not truncated at any ref:
`false`, with 5152 entries at `98c3ecd`, 5153 at `b6008ae`, 5324 at `main`).

| Path | at `98c3ecd` | at `b6008ae` | at `main` |
|---|---|---|---|
| `spec/product/mature-contract.v1.json` | present | present | present |
| `verification/FORWARD_WBS_2026-10-04.md` | **absent** | present | present |

### 3a. `spec/product/mature-contract.v1.json` — predates both cited commits, unchanged since

Blob SHA is **identical at all three refs**:
`a1103ecfdd36f0697625427378ec137a7861dac4` at `98c3ecd`, at `b6008ae`, and at `main`.

Full file history (`/commits?path=spec/product/mature-contract.v1.json`):

| SHA | Date | Subject |
|---|---|---|
| `3382beb` | 2026-09-29T12:41:31Z | `spec(product): add 1000-FR mature-first AgilePlus contract` |
| `588b38d` | 2026-09-29T12:49:05Z | `fix(spec): withdraw quota-built baseline and unsupported verification readiness` |
| `9aacbc1` | 2026-10-01T11:25:21Z | `spec: establish authoritative mature recovery manifest` |
| `44aebce` | 2026-10-01T11:30:30Z | `spec: mark mature semantic contract accepted with runtime gates explicit` |

The file was last modified **2026-10-01, three days before** either cited commit, and has not
changed since. So the file is in the default branch, but **neither cited commit authored or
modified it** — its provenance is `9aacbc1`/`44aebce`.

### 3b. `verification/FORWARD_WBS_2026-10-04.md` — created by `b6008ae`, later reformatted

| Ref | Blob SHA | Bytes | Lines |
|---|---|---|---|
| `b6008ae` | `110b35e6aff7f5cb09a279c18529ff1cebdb9257` | 9652 | 319 |
| `main` | `67c35dc2c2c8410ce9ef29276759bd74232c7224` | 9669 | 319 |

File history: created by `b6008ae` (2026-10-04); modified once since by `4857b40`
(2026-10-18T02:53:15Z, `ci: fail-closed quality gates (qe.yml) (#1138)`).

Full diff `b6008ae → main` is **whitespace-only** (list-item indentation reflowed from 3 spaces to
4 spaces in three bullet lists). Zero semantic change; the `AcceptedWork` content at lines 292/300
is byte-identical in both versions (verified by grep against both blobs).

---

## 4. The "atomic AcceptedWork" claim — what the source actually says

The phrase was searched three ways.

```bash
gh api "search/code?q=AcceptedWork+repo:KooshaPari/AgilePlus"                       # total=10
gh api "search/code?q=AcceptedWork+repo:KooshaPari/AgilePlus+language:Rust"          # total=0
gh api "search/code?q=%22atomic+AcceptedWork%22+repo:KooshaPari/AgilePlus"           # total=0
gh api "search/code?q=%22AcceptedWork%22+%22atomic%22+repo:KooshaPari/AgilePlus"     # total=3
```

### 4a. `AcceptedWork` is a **spec-level semantic term**, not a code symbol

- **Zero occurrences in Rust** (`language:Rust` → `total=0`).
- Repo-wide it appears in exactly 10 files, all specification/verification documents:
  `spec/product/CANONICAL_SEMANTIC_DECISIONS.md`, `spec/product/journeys.v1.json`,
  `spec/product/requirements.semantic.v1.json`, `spec/product/INTERFACE_PROFILE_CONTRACTS.md`,
  `spec/product/recovery-2026-10-14/README.md`, `verification/semantic-verification-cases.v1.json`,
  `verification/FORWARD_WBS_2026-10-04.md`, `verification/EXECUTION_QUEUE.md`,
  `verification/RUNTIME_EVIDENCE_PLAN.md`, `AGENTS.md`.

Authoritative definition — `spec/product/CANONICAL_SEMANTIC_DECISIONS.md:53`:
> `**AcceptedWork** — all mandatory criteria and transition governance are satisfied.`

`spec/product/journeys.v1.json:105`:
> `"Award AcceptedWork only when mandatory correctness criteria pass and transition governance/authority also permits acceptance."`

`AGENTS.md:17` (invariant):
> `AgilePlus AcceptedWork is not Tracera Satisfied.`

### 4b. "Atomic" belongs to a **different vocabulary** — the acceptance-receipt implementation

The atomicity claim in this repo is expressed as **"atomic acceptance"**, over **acceptance
receipts**, not as "AcceptedWork". The atomic implementation chain is real and is on `main`:

| Anchor | Location on `main` | Evidence |
|---|---|---|
| `2433aed` (2026-10-02T17:51:17Z) `feat(acceptance): commit work state audit event and receipt atomically` | 20 files incl. `crates/agileplus-domain/src/domain/acceptance.rs`, `crates/agileplus-application/src/use_cases/acceptance.rs`, `crates/agileplus-sqlite/src/migrations/030_atomic_acceptance.sql`, `crates/agileplus-sqlite/tests/atomic_acceptance.rs`, `crates/agileplus-api/tests/atomic_acceptance_http.rs`, `crates/agileplus-grpc/tests/atomic_acceptance_rpc.rs`, `verification/ATOMIC_ACCEPTANCE_BOUNDARY_2026-10-02.md` | commit exists in `main` ancestry |
| `crates/agileplus-sqlite/src/migrations/030_atomic_acceptance.sql` | `feature_acceptance_receipts` table, `request_id` PK, plus `acceptance_receipts_no_update` / `acceptance_receipts_no_delete` triggers that `RAISE(ABORT, 'acceptance receipts are immutable' / 'append-only')` | file content read at `main` |
| `crates/agileplus-sqlite/tests/atomic_acceptance.rs` | 8551 bytes, **19** occurrences of "atomic", **0** of "AcceptedWork" | content read at `main` |
| `verification/ATOMIC_ACCEPTANCE_GATE_2026-10-03.md`, `verification/ATOMIC_ACCEPTANCE_BOUNDARY_2026-10-02.md` | present on `main` | tree listing |
| `.github/workflows/recovery-acceptance.yml` | present on `main` | tree listing |

### 4c. The composite phrase "atomic AcceptedWork" does not exist in the repo

- Exact-phrase search `"atomic AcceptedWork"` → `total=0`.
- The 3 files matching `"AcceptedWork" AND "atomic"` are the two documents already listed plus
  `requirements.semantic.v1.json` / `semantic-verification-cases.v1.json`; inspection shows the two
  words appear in **separate, unrelated sections** (e.g. `journeys.v1.json` has 3 `AcceptedWork`
  hits and **0** "atomic" hits; `EXECUTION_QUEUE.md` has 1 `AcceptedWork` hit and **0** "atomic"
  hits; `CANONICAL_SEMANTIC_DECISIONS.md` likewise 1 and 0).

**Verdict: "atomic AcceptedWork" is a conflation of two distinct concepts in this repo.**
(1) `AcceptedWork` = the semantic award term (spec/text only, no code symbol);
(2) "atomic acceptance" = the receipt-commit implementation (Rust/SQLite, on `main`).
They are adjacent in the subject matter but are never used as one term, and the atomic
implementation never uses the word `AcceptedWork`.

---

## 5. What the mature contract itself claims (and explicitly does not claim)

`spec/product/mature-contract.v1.json` @ `main` (blob `a1103ecf…`, 2037 bytes), verbatim fields:

```json
"status": "accepted_mature_semantic_contract_runtime_evidence_pending",
"accepted": true,
"mature_complete": false,
"grading_eligible_for_semantic_spine": true,
"grading_eligible_for_full_mature_contract": false,
"mature_semantic_complete": true,
"grading_eligible_for_semantic_contract": true,
"grading_eligible_for_runtime_completion": false
```
with
```json
"verification": {
  "path": "verification/semantic-verification-cases.v1.json",
  "status": "specified_not_executed",
  "case_count": 92,
  "requirement_trace_complete": true
}
```

This is decisive for how the "atomic AcceptedWork" claim must be qualified: the repo's own
authoritative manifest marks the **semantic contract as accepted** while marking
**runtime evidence as `specified_not_executed`** and **runtime completion as not grade-eligible**.
`verification/FORWARD_WBS_2026-10-04.md:42-67` says the same in prose — P0 is
"make canonical atomic acceptance **natively green**", an open gate with an explicit exit
criterion ("one concrete commit has native evidence that Rust tests actually executed and the
atomic acceptance suite passed"), and the document's own discipline rule:
`test not executed != test passed` (also `AGENTS.md:19`).

---

## 6. Verdict table

| Claim under test | Verdict | Primary evidence |
|---|---|---|
| Commit `98c3ecd` exists | **TRUE** | `98c3ecd477a7e…`, 2026-10-04T19:49:12Z, 1 file added |
| Commit `b6008ae` exists | **TRUE** | `b6008ae02f90…`, 2026-10-04T19:50:25Z, 1 file added |
| `98c3ecd` ↔ `spec/product/mature-contract.v1.json` | **FALSE pairing** | `98c3ecd` added only `docs/architecture/NETWORK_DEPLOYMENT_DOCTRINE.md`; the contract file's last edit is `44aebce` (2026-10-01) |
| `b6008ae` ↔ `verification/FORWARD_WBS_2026-10-04.md` | **TRUE** | commit created the file (+319/-0); file persists on `main` |
| Both commits in current default branch history | **TRUE** | `compare` → `behind_by=0`, merge_base == the commit; 211/213 commits behind HEAD |
| `spec/product/mature-contract.v1.json` on `main` | **TRUE** | blob `a1103ecf…` identical at `98c3ecd`, `b6008ae`, `main` |
| `verification/FORWARD_WBS_2026-10-04.md` on `main` | **TRUE** | blob `67c35dc2…`; only change since is whitespace (diff verified) |
| "atomic AcceptedWork" as a repo term | **NOT FOUND** | exact phrase → 0 hits; `AcceptedWork` in Rust → 0 hits |
| `AcceptedWork` concept exists in repo | **TRUE (spec-level only)** | defined `CANONICAL_SEMANTIC_DECISIONS.md:53`; 10 doc/json files on `main` |
| atomic acceptance implementation exists on `main` | **TRUE (code)** | `2433aed`; `030_atomic_acceptance.sql` immutability triggers; `atomic_acceptance{,_http,_rpc}` tests |
| mature contract's runtime evidence executed | **FALSE per repo's own manifest** | `verification.status = "specified_not_executed"`, `mature_complete = false`, `grading_eligible_for_runtime_completion = false` |

**Bottom line.** Nothing cited was found to be nonexistent. Both commits are real, are ancestors of
`main`, and the two cited paths are present in the current default branch (one unchanged since
2026-10-01, one created by the cited commit and later only whitespace-reformatted). The single
defect in the prior account is the `98c3ecd` ↔ `mature-contract.v1.json` pairing, and the single
defect in the "atomic AcceptedWork" phrasing is that it merges a **spec-only semantic award term**
with a **code-level atomic-receipt implementation** that never uses the word `AcceptedWork`.
The repo's own authoritative manifest is the appropriate qualifier: the mature **semantic**
contract is `accepted`, while **runtime evidence is `specified_not_executed`** and atomic
acceptance native-greenness remains an open P0 gate.

---

## 7. Commands used (full reproducibility)

```bash
# repo + auth
gh auth status
gh api repos/KooshaPari/AgilePlus --jq '{name:.full_name,default_branch,pushed_at,archived,visibility}'
gh api repos/KooshaPari/AgilePlus/commits/main --jq '{sha,date:.commit.committer.date,msg:.commit.message}'

# cited commits
gh api repos/KooshaPari/AgilePlus/commits/98c3ecd --jq '{sha,date:.commit.committer.date,author:.commit.author.name,msg:(.commit.message|split("\n")[0]),parents:[.parents[].sha]}'
gh api repos/KooshaPari/AgilePlus/commits/b6008ae --jq '{...}'
gh api repos/KooshaPari/AgilePlus/commits/<sha> --jq '.files[]|"\(.status) +\(.additions)/-\(.deletions) \(.filename)"'

# ancestry / default-branch representation
gh api "repos/KooshaPari/AgilePlus/compare/98c3ecd...main" --jq '{status,ahead_by,behind_by,merge_base:.merge_base_commit.sha}'
gh api "repos/KooshaPari/AgilePlus/compare/b6008ae...main" --jq '{...}'
gh api repos/KooshaPari/AgilePlus/commits/b6008ae/branches-where-head --jq '.[].name'

# trees / paths
for r in main 98c3ecd b6008ae; do
  gh api "repos/KooshaPari/AgilePlus/git/trees/$r?recursive=1" --jq '.truncated,(.tree|length)'
  gh api "repos/KooshaPari/AgilePlus/git/trees/$r?recursive=1" --jq '.tree[]|select(.path|test("mature-contract|FORWARD_WBS|AcceptedWork|acceptance";"i"))|.path'
done

# blob identity + file history
gh api "repos/KooshaPari/AgilePlus/contents/<path>?ref=<ref>" --jq '.sha,.size'
gh api "repos/KooshaPari/AgilePlus/commits?path=<path>&per_page=100" --jq '.[]|"\(.sha[0:7]) \(.commit.committer.date) \(.commit.message|split("\n")[0])"'
gh api -H "Accept: application/vnd.github.raw" "repos/KooshaPari/AgilePlus/contents/<path>?ref=<ref>" > local.md

# term search
gh api "search/code?q=AcceptedWork+repo:KooshaPari/AgilePlus" --jq '{total:.total_count,items:[.items[].path]}'
gh api "search/code?q=AcceptedWork+repo:KooshaPari/AgilePlus+language:Rust" --jq '{total:.total_count}'
gh api "search/code?q=%22atomic+AcceptedWork%22+repo:KooshaPari/AgilePlus" --jq '.total_count'
gh api "search/code?q=%22AcceptedWork%22+%22atomic%22+repo:KooshaPari/AgilePlus" --jq '{total:.total_count,items:[.items[].path]}'

# local-clone availability probe (bounded, no $HOME recursion)
find ~/CodeProjects/Phenotype/repos/AgilePlus-space -maxdepth 3 -name .git -print
```

Artifacts retained in this directory: `mc_main.json`, `wbs_main.md`, `wbs_b6008ae.md`,
`agents_main.md`.

---

## 8. Limits of this investigation

- Read-only. No branch, tag, PR, issue, or file was created or modified in `KooshaPari/AgilePlus`.
- No local clone of `AgilePlus` was available, so `git log`/`git blame` were not run directly; the
  GitHub API serves the identical object graph, and every ancestry claim here is corroborated by
  two API surfaces (`compare` merge-base, and `/commits?path=` file history).
- `search/code` indexes the default branch. `AcceptedWork` occurrences on non-default branches
  were therefore not enumerated; the claim under test concerned the default branch, which is
  fully covered.
- Branch-level (non-`main`) occurrences of either cited commit as a tip: none
  (`/branches-where-head` empty for `b6008ae`; `compare` proves ancestry regardless).
