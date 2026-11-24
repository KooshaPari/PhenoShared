# Codebase Atlas - PhenoShared

| Field | Value |
|---|---|
| Repo | KooshaPari/PhenoShared |
| Commit | `origin/main` @ `6ec4ae563` (1,214 commits on main) |
| Working tree observed | `ad667428b` on `layer/governance-happy-path-claims` |
| Caveat | A concurrent process re-checked-out this working tree mid-analysis. Structural counts were stable across the run; CI/governance file deltas are possible. |
| Analysed | 2026-11-10 |
| Method | Static structural inspection of the working tree plus independent re-measurement of every headline count |
| Confidence | counts independently re-measured from the working tree; module purposes inferred from names and manifests |

## One-screen orientation

PhenoShared is a Rust-workspaced monorepo with heavy multi-language satellites, not one Rust crate.
The visible spine is `crates/` (13,848 tracked files) rooted in a real `[workspace]` with 283 declared crate paths.
The actual code mass is Python (~52% of code LOC), with Rust ~22% and Go ~18%.
It is also a host for absorbed products: `absorption/`, `_archived/`, `archive(s)/`, and vendored `.vendor/lancedb`.
Markdown outnumbers code (10,532 `.md` vs 7,209 `.rs`), so documentation is a first-class maintenance surface.
The dominant structural hazard is triple-vendoring of the AgilePlus family (23 + 51 + 25 crate dirs).
Naive per-directory LOC sums overstate the repo ~2.2x; de-duplicate before quoting size.
~87% of crate dirs are under 2.5k LOC: a broad platform surface, not a few large services.
No first-party Rust file exceeds 3,254 lines, yet 2-3.2k-line `lib.rs`/`main.rs` roots are common. Counts are reproducible only with the atlas's quoted commands.

## Scale and shape

| Metric | Value |
|---|---|
| Commits (all refs) | 3,635 at first measurement; 3,641 on re-measure 2026-11-10T07:38Z (live count, drifts as branches are pushed) |
| Commits (main) | 1,215 on `origin/main` (1,214 at first measurement); 1,210 on local `main` |
| Remote branches | 74 (live count 2026-11-10; drifts as branches are pushed) |
| Tags | 9 |
| Tracked files | 42,225 |
| Workspace members | 283 unique crate paths (287 quoted strings: 1 comment line, 3 duplicates) |
| Lockfile packages | 1,904 |
| Crate dirs (`crates/*`) | 372 total, 369 crate-like |
| First-party Rust LOC | 304,248 |
| `[[bin]]` targets / crates with `src/main.rs` | 154 / 85 |

Language split (~1.384M code LOC): Python ~52%, Rust ~22%, Go ~18%, Shell ~3.8%, TypeScript+TSX ~3.4%, JavaScript ~1.2%.

## Territory map

| Directory | Purpose | Size class |
|---|---|---|
| `crates/` | Rust workspace, core code spine | XL (13,848 files) |
| `docs/` | Records: ADRs, docs, `absorbed-from-*` trees | XL (11,721) |
| `absorption/` | Historical: absorbed upstream code | L (4,414) |
| `audits/` | Records: audit evidence | L (1,750) |
| `agents/` | Core: agent definitions | L (1,534) |
| `agileplus/` | Product surface | L (1,106) |
| `_archived/` | Historical | M (632) |
| `sites/` | Product: web surfaces | M (603) |
| `bench/` `scripts/` | Ops and tooling | M (391/388) |
| `servers/` `python/` `tests/` `infrakit/` `registry/` | Core code, tests, registry | M (386/314/297/265/147) |
| `archive(s)/` | Historical | M (225) |
| `state/` `traces/` `datasets/` | State and artifacts | S |
| `projects/` `handbook/` `kitty-specs/` | Records and specs | M (178/142/170) |
| `unity/` `apps/` `web/` `gui/` | Product surfaces | S-M |
| `.github/` | Ops: CI | S (141) |

