# Absorption Batch 1: 2026-11-19

Commands were run sequentially, one repository at a time. No repository or branch was deleted. No commit or push was performed by this batch workflow outside the two named scripts. The other 22 private repositories were not touched.

| Repository | Files absorbed | Refs | Commits | Verify result (`prepare_deletion.py`) | DELETE-AUTHORISED | Error text |
|---|---:|---:|---:|---|---|---|
| cvp-fixture | 17 | 1 | 1 | `verified 17/17 files` | yes | none |
| StealthStartup | 34 | 1 | 4 | `verified 34/34 files exact (registry tree)` | yes | none |
| harness-ops | 69 | 1 | 44 | `verified 69/69 files exact (registry tree)` | yes | none |
| dagrun | 192 | 2 | 55 | `verified 192/192 files exact (registry tree)` | yes | none |
| audit-system | 454 | 2 | 43 | `verified 454/454 files exact (registry tree)` | yes | none |

All five verification counts match the corresponding absorption counts exactly. Independent verification reported no mismatches, no refusals, and exit code 0 for all five commands. DELETE-AUTHORISED is evidence only; no deletion was performed.

## Exact absorption output

```text
== cvp-fixture
   absorbed  17 files exact, 1 refs, 1 commits
   DELETE-AUTHORISED cvp-fixture

absorbed 1, blocked 0
```

```text
== StealthStartup
   absorbed  34 files exact, 1 refs, 4 commits
   DELETE-AUTHORISED StealthStartup

absorbed 1, blocked 0
```

```text
== harness-ops
   absorbed  69 files exact, 1 refs, 44 commits
   DELETE-AUTHORISED harness-ops

absorbed 1, blocked 0
```

```text
== dagrun
   absorbed  192 files exact, 2 refs, 55 commits
   DELETE-AUTHORISED dagrun

absorbed 1, blocked 0
```

```text
== audit-system
   absorbed  454 files exact, 2 refs, 43 commits
   DELETE-AUTHORISED audit-system

absorbed 1, blocked 0
```

## Exact independent verification output

```text
== cvp-fixture
   verified 17/17 files
   bundled  5914f2360ed5 (26.3 KB)
   threads  0 issues, 0 pulls, 0 comments
   DELETE-AUTHORISED cvp-fixture

prepared 1, blocked 0
```

```text
== StealthStartup
   verified 34/34 files exact (registry tree)
   bundled  06552b887107 (754.8 KB)
   threads  0 issues, 0 pulls, 0 comments
   DELETE-AUTHORISED StealthStartup

prepared 1, blocked 0
```

```text
== harness-ops
   verified 69/69 files exact (registry tree)
   bundled  81f8c98e36da (279.3 KB)
   threads  0 issues, 0 pulls, 0 comments
   DELETE-AUTHORISED harness-ops

prepared 1, blocked 0
```

```text
== dagrun
   verified 192/192 files exact (registry tree)
   bundled  544fb4155b88 (556.2 KB)
   threads  1 issues, 1 pulls, 2 comments
   DELETE-AUTHORISED dagrun

prepared 1, blocked 0
```

```text
== audit-system
   verified 454/454 files exact (registry tree)
   bundled  f1f7c222753f (2031.9 KB)
   threads  0 issues, 0 pulls, 0 comments
   DELETE-AUTHORISED audit-system

prepared 1, blocked 0
```

Summary: 5 of 5 repositories are fully absorbed and independently verified.
