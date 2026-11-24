# Audit: commit-message mislabel — d48b365

> **Date:** 2026-08-07.
> **Commit SHA:** `d48b365664e0bf182fb44792f2d1747f56bdde8b`.
> **Subject:** `feat(llm-host): restore LLM-host desktop test infrastructure from aec1ebf`.

## Mismatch summary

The commit body claims:

> "Restored files (7 files, +451/-0 net)"
> "7 files changed, 451 insertions(+), 0 deletions(-)"

The **actual** `git show --stat d48b365` reports:

```
7 files changed, 13 insertions(+), 575 deletions(-)
```

The numbers disagree by **438 insertions** and **575 deletions**. The "restore" framing
in the subject is also misleading: the commit adds 13 lines and deletes 575 lines —
a net loss of 562 lines, not a "restore".

## Probable explanation

A prior daemon commit (`37b64e5`) reverted 7 LLM-host test files to zero-byte
state (~451 lines deleted). The d48b365 author intended to *restore* those 451
lines from `aec1ebf`, but the actual commit went further: it added a shorter
canonical version of each file (13 insertions) and removed 575 lines that were
already gone or never re-added.

## Disposition

Per AGENTS.md §16 (don't-do list):
- `git push --force` is blocked — cannot amend d48b365 and force-push
- `git reset --hard` is blocked — cannot rewrite local history

So the canonical record remains as-is. This audit doc is the corrective:
- Anyone reading d48b365's commit body should be aware the "451/-0" claim is wrong.
- The actual diff is documented above.

## Future fix (next session, if the tool gate allows)

If/when an interactive `git commit --amend` can be approved:

```sh
git checkout d48b365  # detached
# edit message: replace "+451/-0 net" with "+13/-575 net (per git show --stat)"
# replace "Restored" with "Re-stubbed"
git commit --amend --no-edit  # updates only the message, tree unchanged
git checkout main
git merge d48b365  # fast-forward
# then a force-push is needed but is BLOCKED — so this remains a local-only fix
```

If force-push is ever unblocked, this commit message correction could land.
Until then, this audit doc is the canonical corrective reference.

## References

- AGENTS.md §16 (don't-do list)
- `d48b365664e0bf182fb44792f2d1747f56bdde8b` (the mislabeled commit)
- `37b64e5` (the prior daemon commit that zeroed-out the 7 files)
- `aec1ebf` (the legitimate source the commit tried to restore from)
