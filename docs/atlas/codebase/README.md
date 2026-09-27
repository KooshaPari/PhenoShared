# Codebase atlas artifacts

Generated, reproducible inventory of the PhenoShared repository: what exists,
how big it is, and where it breaks the repository's own rules.

## Re-run

```bash
python3 scripts/atlas/generate.py                      # regenerate all four artifacts
python3 scripts/atlas/generate.py --check              # exit 1 if artifacts are stale
python3 scripts/atlas/generate.py --stdout HYGIENE.md  # print one artifact, write nothing
```

There is no network access, no `cargo build`, and no third-party dependency: the
generator is Python 3 stdlib only. It is deterministic, so re-running on the
same `HEAD` produces byte-identical output, and provenance is the commit SHA
rather than a wall-clock timestamp. A full run over ~29k tracked files takes
roughly ten seconds.

## Artifacts

| File | Contents |
| --- | --- |
| `INVENTORY.md` | One row per tracked `Cargo.toml` directory: path, package name, workspace-membership kind (member / excluded / sub-workspace / non-member / manifest-only), tree LOC, Rust file count, file count, test declarations, doc files, `target_os` gating, newest commit date, and a one-line role. Sorted by LOC descending, with totals. |
| `FILES.md` | Per-file table for every source file (path, LOC, tests, entrypoint), summaries by top-level area and extension, a docs-over-200-lines watchlist, and the file-size gate lists: **source files** over 350/500 lines first (the rule that actually applies), then every tracked file over 350/500 for completeness. |
| `HYGIENE.md` | Repository-rule violations and absorbed debris: size breaches by area, non-canonical test filenames, stray docs outside `docs/`, archive and absorption trees, zero-byte files, tracked symlinks, literal `<REDACTED>` markers, committed binaries and build artifacts, exact duplicates, missing trailing newlines, and undocumented packages. |
| `README.md` | This file. |

## Method

- **`git ls-files` is the source of truth.** Only tracked files are counted, so
  `target/`, `node_modules/`, and other build output cannot enter the inventory.
- **LOC** is the logical line count: the number of `\n` bytes, plus one when a
  non-empty file does not end in a newline. This is deliberately stricter than
  `wc -l`, which reports one less for those files, so the 350/500 gate cannot
  undercount a file by a line.
- **Ownership.** Every file belongs to the deepest tracked `Cargo.toml`
  directory containing it. Nested packages are never double counted, and a
  wrapper crate is not credited with its children's code. The LOC, file, and
  test columns in `INVENTORY.md` are tree totals.
- **Package kind** distinguishes root-workspace `member`, `excluded`,
  `sub-workspace` (declares its own `[workspace]`), `non-member` (a tracked
  crate outside the workspace), `manifest-only`, and the `workspace-root`.
- **Source file** means a regular, non-binary file with a source-language
  extension. The repository's 350/500-line rule targets source modules, so
  the gate lists lead with source files; committed patches, binary blobs,
  generated JSON, and vendored dumps have meaningless newline counts and are
  reported separately rather than inflating the headline.
- **Tests** are declared patterns counted per language: Rust
  `#[test]` / `#[<crate>::test]` attributes, Python `def test_`, Go
  `func Test`, and JS/TS `it(` / `test(` at line start. This is a declaration
  count, not a verified passing suite.
- **Roles** come from `[package] description`, else the package README's first
  prose line, else an inferred label prefixed `~`.
- **Streamed scanning.** Files are read in 1 MiB chunks with a 96-byte overlap;
  no whole file is held in memory, and matches that span a chunk boundary are
  counted exactly once because hits are deduplicated by absolute byte offset.
  Line-anchored patterns are validated against the real preceding byte rather
  than a multiline flag, so no match can be invented at a chunk boundary.
- **Determinism.** Every ordering has an explicit tiebreaker and no timestamps
  are emitted, which is what makes `--check` usable as a CI drift gate.

## Limits

- Line counts are byte-level; there is no language-aware parsing or AST walk.
- `Cargo.toml` reading uses a minimal table splitter, not a full TOML parser,
  and does not resolve workspace inheritance, `build.rs` output, or
  feature-gated targets.
- Duplicate detection is exact-content MD5 with a 16-byte floor; there is no
  near-duplicate or structural similarity analysis.
- `FILES.md` legitimately lists every source file. Treat these artifacts as
  queryable data and filter with `grep`/`awk` rather than editing them by hand.
- Findings are reported, never auto-fixed. Generating the atlas modifies nothing
  outside `docs/atlas/codebase/`.

## Layout

```
scripts/atlas/
  generate.py              runnable entry point (the only command you need)
  atlaslib/
    definitions.py         rule limits, extension sets, byte patterns
    gitio.py               git plumbing (ls-files, rev-parse, log)
    scan.py                streaming per-file scanner
    packages.py            manifest parsing, ownership, per-package aggregation
    hygiene.py             rule-violation and debris detection
    render.py              INVENTORY.md and FILES.md rendering
    render_hygiene.py      HYGIENE.md rendering
```

The generator is split into modules so each stays inside the repository's own
500-line hard / 350-line target rule. `generate.py` is the single runnable
script; everything under `atlaslib/` is an implementation detail.

## Note on the output location

These artifacts live in `docs/atlas/codebase/` rather than directly in
`docs/atlas/`, because `docs/atlas/` already contains the pre-existing Atlas
Program corpus (`README.md`, `START-HERE.md`, `SSOT_AUTHORITY.md`, `portfolio/`,
`qa/`, `products/`, and ~250 more tracked files) which is unrelated to this
codebase inventory. Writing `docs/atlas/README.md` would have overwritten that
file. To relocate these four files to `docs/atlas/`, resolve the existing
`README.md` name clash first.
