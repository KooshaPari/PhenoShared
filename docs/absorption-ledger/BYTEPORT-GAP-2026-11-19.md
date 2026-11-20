# BytePort absorption gap, 2026-11-19

Read-only investigation of the discrepancy between `absorb_private.py` reporting
`absorbed 680 files exact` and `prepare_deletion.py` reporting
`verified 676/680 files` for `BytePort`. No absorption, deletion, commit, push,
or registry write was performed.

Audit state at review time:

- `git -C C:\Users\koosh\PhenoShared status --porcelain` showed only
  `?? docs/absorption-ledger/BYTEPORT-GAP-2026-11-19.md`, so the tree was dirty
  solely because this deliverable was already present as an untracked file.
- `docs/absorption-ledger/ABSORB-BATCH3-2026-11-19.md` exists
  (2,716 bytes, dated 11/19/2026 04:55 AM).

The old record in `docs/absorption-ledger/FOLLOWUP-2026-11-15.md` lines 68-70
claimed `676/680, 3 files withheld to the private registry and 1 compiled binary
excluded`. That claim is **confirmed** by the checks below.

## 1. Verification output and the four paths

Command run (absolute path equivalent of the requested repo-root command):

```text
python3 -u C:\Users\koosh\PhenoShared\scripts\verify_absorption.py BytePort --json
```

Full output:

```json
[
 {
  "repo": "BytePort",
  "status": "complete",
  "root": "C:\\Users\\koosh\\PhenoShared\\absorption\\BytePort",
  "compared_at": "HEAD",
  "remote_files": 680,
  "local_files": 890,
  "covered": 676,
  "missing": 0,
  "excluded_build_or_log": 1,
  "withheld_in_registry": 3,
  "missing_sample": [],
  "source_drift": 0,
  "source_drift_sample": []
 }
]
```

There are **zero unresolved missing paths**. `missing_sample` is empty. The JSON
reports counts only, so the four paths were recovered read-only by applying
`verify_absorption.py`'s own classification rules to the live source tree, the
local absorption roots, and the private registry tree.

| Classification | Path |
| --- | --- |
| Withheld in registry | `docs/handover/byteport-handover-to-windows-agent.md` |
| Withheld in registry | `docs/sessions/20260918-byteport-handoff/HANDOFF.md` |
| Withheld in registry | `docs/sessions/20260918-jcode-session-handoff/SESSION-HANDOFF.md` |
| Excluded build/log | `backend/byteport/byteport-server.exe` |

Unresolved after classification: none.

## 2. Registry contents for BytePort

Top-level command and result:

```text
gh api repos/KooshaPari/PhenoRegistry/contents/repos/BytePort --jq ".[].name"
docs
history
tree
```

Descended one level per call:

```text
gh api repos/KooshaPari/PhenoRegistry/contents/repos/BytePort/docs --jq ".[].name"
handover
sessions

gh api repos/KooshaPari/PhenoRegistry/contents/repos/BytePort/docs/handover --jq ".[].name"
byteport-handover-to-windows-agent.md

gh api repos/KooshaPari/PhenoRegistry/contents/repos/BytePort/docs/sessions --jq ".[].name"
20260918-byteport-handoff
20260918-jcode-session-handoff

gh api repos/KooshaPari/PhenoRegistry/contents/repos/BytePort/docs/sessions/20260918-byteport-handoff --jq ".[].name"
HANDOFF.md

gh api repos/KooshaPari/PhenoRegistry/contents/repos/BytePort/docs/sessions/20260918-jcode-session-handoff --jq ".[].name"
SESSION-HANDOFF.md

gh api repos/KooshaPari/PhenoRegistry/contents/repos/BytePort/tree --jq ".[].name"
... backend ...

gh api repos/KooshaPari/PhenoRegistry/contents/repos/BytePort/tree/backend --jq ".[].name"
README.md
byteport

gh api repos/KooshaPari/PhenoRegistry/contents/repos/BytePort/tree/backend/byteport --jq ".[].name"
... byteport-server.exe ...
```

| Candidate path | Present in registry? |
| --- | --- |
| `docs/handover/byteport-handover-to-windows-agent.md` | **YES**, under `repos/BytePort/docs/handover/` |
| `docs/sessions/20260918-byteport-handoff/HANDOFF.md` | **YES**, under `repos/BytePort/docs/sessions/20260918-byteport-handoff/` |
| `docs/sessions/20260918-jcode-session-handoff/SESSION-HANDOFF.md` | **YES**, under `repos/BytePort/docs/sessions/20260918-jcode-session-handoff/` |
| `backend/byteport/byteport-server.exe` | **YES**, under `repos/BytePort/tree/backend/byteport/` |

All four disputed paths are present somewhere in the registry. Three are the
deliberately withheld private documents. None is lost.

## 3. The fourth path: compiled binary, not source

The fourth path is **`backend/byteport/byteport-server.exe`**. It is a **compiled
binary**, not genuine source.

- `.exe` is in `verify_absorption.py`'s `EXCLUDE_SUFFIXES`, documented as
  object and binary artefacts regenerated from the source that is kept.
- Registry metadata reports `name=byteport-server.exe`, `type=file`,
  `size=64092020`, `encoding=base64`.
- Decoding the registry content yields a Git LFS pointer, not source bytes:

```text
version https://git-lfs.github.com/spec/v1
oid sha256:ff33a801eb485cdf649ac64cc02a72213cbb159e42b692fd59ea26258c7014a4
size 64092020
```

A 64 MB Git LFS Windows executable is build output. Excluding it from the
source-file count is correct.

## 4. Ref preservation with no bundle

No bundle was generated because BytePort history is 231.8 MB. The registry note
at `repos/BytePort/history/PRESERVED-AS-REFS.md` states that full history is
preserved as git refs because GitHub rejects files over 100 MB, and that every
branch and tag tip was verified against the source after the push.

Commands and counts:

```text
gh api repos/KooshaPari/PhenoRegistry/git/refs --paginate --jq ".[] | select(.ref|startswith(\"refs/preserved/BytePort\")) | .ref" | find /c /v ""
3

git ls-remote --refs https://github.com/KooshaPari/BytePort.git | find /c /v ""
3
```

**The counts do not differ. Preserved refs are complete.**

Names and SHAs also match one for one:

| Preserved ref | SHA | Live ref |
| --- | --- | --- |
| `refs/preserved/BytePort/heads/main` | `eb8693ab855a68c45b8f0c16bb633194a6038b71` | `refs/heads/main` |
| `refs/preserved/BytePort/tags/v1.0.2` | `5b1f958ab2ec678eeebcfc034e1dda6a6cfcb7e4` | `refs/tags/v1.0.2` |
| `refs/preserved/BytePort/tags/v1.0.3` | `8aec4818eb23b9c5fc2754a4e3892324adb96e9f` | `refs/tags/v1.0.3` |

## Verdict

**the four files are fully accounted for - three withheld, one compiled binary - so 676/680 is correct and the 680 claim is the tool's error**

`absorb_private.py`'s `680` counted every source-tree file it saw.
`prepare_deletion.py`'s `676` is the verified content count after excluding one
regenerable executable and crediting the three privately withheld documents.
Preserved refs are complete: 3 preserved refs match 3 live refs at identical
SHAs, with no bundle expected for this oversized history.
