# GitHub archive policy (STRICT)

**Never delete GitHub repositories on this account.**

## Required pattern

When a repo is superseded:

1. **Mirror** all needed history/branches into the canonical home (if not already there).
2. **Rename** to `zz-archive-<original-name>` so it sorts to the bottom of the org list.
3. **Archive** the repo (read-only) via `gh repo archive`.
4. Set **description** to `SUPERSEDED YYYY-MM-DD — … mirrored to <canonical>. Do not push here.`
5. Set **homepage** to the canonical repo URL.
6. Optionally add root `SUPERSEDED.md` pointing at the canonical home.

## Forbidden

- `gh repo delete`
- UI “Delete this repository”
- Force-removing remotes that erase the only copy of history

## Recovery

If something was deleted by mistake: use GitHub Support restore, then re-apply the `zz-archive-*` pattern above. Do not leave restored stand-ins as active writable remotes.

## Canonical oMLX example (2026-07-22)

| Role | Repo |
|------|------|
| Active | `<REDACTED>/phenotype-omlx` |
| Stand-in (hidden) | `<REDACTED>/zz-archive-phenotype-omlx-tmp` |
| Stand-in (hidden) | `<REDACTED>/zz-archive-phenotype-omlx-temp` |
