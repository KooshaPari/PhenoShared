# Deletion readiness, 2026-11-16

Two repositories meet the three conditions that `prepare_deletion.py` exists to
enforce: absorbed content verified, history preserved, discussion exported. This
records the evidence so the deletion is checkable rather than asserted, and
records that **nothing has been deleted**.

## `phenotype-canonicalization` — DELETE-AUTHORISED

```
$ python scripts/prepare_deletion.py phenotype-canonicalization
== phenotype-canonicalization
   verified 43/44 files
   bundled  cdaa7cfe6994 (103.1 KB)
   threads  0 issues, 0 pulls, 0 comments
   DELETE-AUTHORISED phenotype-canonicalization
```

| Condition | Evidence |
|---|---|
| Content | `absorption/phenotype-canonicalization` holds 43 of 44 files byte-identical by git blob id; the only gap is `verification/unit-tests.log`, a generated test log |
| History | bundle `cdaa7cfe6994`, 103.1 KB in the private registry, plus 1 preserved ref over 8 commits |
| Discussion | 0 issues, 0 pull requests, 0 comments |

## `host-credentials` — ready by measurement, not by `prepare_deletion.py`

`prepare_deletion.py` refuses it, and the refusal is correct rather than a
malfunction: its completeness check calls `verify_absorption.py`, which compares a
repository against `absorption/<name>/`. `host-credentials` was absorbed into the
**private registry** instead, because it held live credentials, so there is no
`absorption/` tree for that check to read.

The equivalent evidence, measured separately:

| Condition | Evidence |
|---|---|
| Content | `PhenoRegistry/repos/host-credentials/tree/` covers 5 of 5 files exactly, by git blob id (`scripts/registry_coverage.py`) |
| History | 1 preserved ref under `refs/preserved/host-credentials/` in the registry |
| Discussion | 0 issues, 0 pull requests (`gh api .../issues?state=all`, `.../pulls?state=all` both return `[]`) |

## Two reasons to wait

1. **The restorer is still unidentified.** `host-credentials` was recreated during
   the 2026-11-14 burst at 17:22, after having been deleted for holding
   credentials. Deleting it again may be undone within minutes, and each cycle
   makes the account harder to reason about. The estate has gone 86, 104, 110,
   111, 112 in two days.
2. **`host-ops` showed how wrong the structural signal was.** It was classified
   delete-eligible on the same basis as these two and turned out to be missing 172
   files including most of its closure evidence. These two have had the content
   check run properly; that is worth stating plainly because its predecessor had
   not.

## A fix this exposes

`prepare_deletion.py` can only verify content that landed in `absorption/`. A
repository absorbed into the registry — which is the rule for private and
credential-bearing repositories — cannot be authorised by it at all. That is a
gap in the tool, not in the data, and it should grow a `--registry-tree` mode that
runs the same three checks against `repos/<name>/tree/`.

## Nothing deleted

No repository has been removed. This document authorises the next step; it does
not take it.
