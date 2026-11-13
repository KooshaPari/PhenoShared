# dprint scope

`dprint.json` at the repo root owns exactly two file types:
**TOML** and **Dockerfile**. Nothing else.

## What it deliberately does not own

| File type | Owner | Why not dprint |
|---|---|---|
| Markdown | markdownlint (3 configs) | already gated; a second formatter would fight it |
| Python | ruff (advisory lane) | ruff owns import order and style |
| JS/TS | prettier + oxlint | already gated in the TS/JS lane |

Adding any of those to dprint would put a fourth formatter in
competition with the three already in place. That is why the original
`crates/hexa-kit/dprint.json` (4 plugins, executed by nothing) was
narrowed to two plugins when it moved to the root.

## Gate shape

- **Dockerfile: repo-wide.** Every tracked Dockerfile is checked. This
  is a hard gate because the set is small and every member is clean.
- **TOML: changed files only.** A pull request is checked on the TOML
  it touches. This gates new contributions without reddening the build
  on pre-existing debt.

## Measured TOML debt (baseline 2026-11-13, dprint 0.64.3)

| Count | Meaning |
|---|---|
| 798 | tracked TOML files whose formatting differs |
| 545 | of those, first-party |
| 253 | of those, inside absorbed or archived corpora |

First-party breaks down as crates 415, agents 29, python 23,
infrakit 23, iac 9, repo root 8, other 38.

47 further files are **excluded** rather than reformatted, because the
toml plugin cannot parse them at all: 42 `mise.toml`,
4 `phenotype-versions.toml`, 1 `trace-gate.toml`. They are tool-version
and generated files. Excluding them takes `dprint check` from 47 hard
errors to 0, which is what lets the gate report differences honestly.

## Re-measure

```bash
dprint check --config dprint.json                   # TOML + Dockerfile
git ls-files | grep -Ei '(^|/)Dockerfile' \
  | xargs dprint check --config dprint.json         # Dockerfile gate, expect 0
dprint check --config dprint.json --list-different  # the 798 paths
```

Run these from the repo root: dprint resolves includes and excludes
against the config file's directory, so a config invoked from elsewhere
checks the wrong tree and reports "No files found" rather than failing.

## Reducing the debt

Nothing here blocks a contribution. To retire the debt, reformat one
directory at a time (`dprint fmt --config dprint.json crates/<name>`)
and drop it from the counts above, rather than reformatting 798 files
in a single change no reviewer can read.
