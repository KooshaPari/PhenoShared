# Provenance: sharecli family, PhenoInfra, PhenoTooling, PhenoMLX-temp

Repo: `Phenotype/repos/PhenoShared` @ read-only worktree. Measured 2026-11-10. Repo path bounded; no `$HOME` recursion.

| Item | Files | Size | Workspace refs | Provenance manifest? | Languages |
|---|---|---|---|---|---|
| A) `crates/sharecli*` (12 dirs: 10 `sharecli*` + 2 `sharecli-tray-*`) | 575 (504 `.rs`) | ~7.5 MB (`du -sh` rows; main crate 6.3 MB) | 12/12 members, `Cargo.toml:64-75`; **zero consumers inside workspace** | **NONE** (no PROVENANCE.md/README.md in `crates/sharecli/`) | Rust only; 119,855 LOC |
| B) `absorption/PhenoInfra/` | 2532 | 28 MB | **0 path refs**; only 2 comment lines (`Cargo.toml:262`, `:915`) | YES `PROVENANCE.md`: `ecf486cab18b8e84213838d497a39ea3a94aca71`, absorbed 2026-09-27 | md 766, json 293, go 205, yml 163, rs 157 |
| C) `absorption/PhenoTooling/` | — | — | — | **DOES NOT EXIST** | — |
| C') `docs/absorbed-from-PhenoTooling/` (the real ~70 MB payload) | 8257 | 70 MB | 0 | YES `ABSORPTION.md` (repo `KooshaPari/PhenoTooling`, archived; **no commit revision recorded**) | js/npm + docs; source dirs `authkit/`, `bluebubbles/`, `cr_router/`, `bin/` |
| D) `absorption/PhenoMLX-temp/` | 1349 | 10 MB | 40 `PhenoMLX` matches in `Cargo.toml` (members :8, :818-845; deps :1001-1010) | YES `PROVENANCE.md`: `70529a879715a8078e26eb564f8fc312e1923f57`, absorbed 2026-09-27 | rs 511, py 173, md 146, json 101 |

## Corrections to the brief

- **A**: claim "~9 sharecli dirs + 2 tray" undercounts: there are **12** (`sharecli`, `-core`, `-ffi`, `-fleet`, `-fuse`, `-ipc`, `-mesh`, `-session`, `-sync`, `-thermal-tui`, `-tray-linux`, `-tray-windows`).
- **A**: upstream `~/CodeProjects/sharecli` **does not exist** (`ls` → No such file or directory; no `*sharecli*` under `~/CodeProjects`). There is no upstream to reconcile against, and the crates carry no provenance file recording one.
- **A**: the only cross-crate dependency is `crates/harness-native/Cargo.toml:28-29` → `sharecli-core`, `sharecli-ipc`. But `harness-native` **is not a workspace member** (`grep 'harness' Cargo.toml` → only `crates/perfharness`, `absorption/.../eval-harness`). So the dependency is unbuilt, not load-bearing.
- **B**: 2532 files / 28 MB confirmed; zero workspace refs confirmed. Note only **157 `rs` files**: the comment at `:262` says PhenoInfra crates were absorbed *into* the main `crates/` dir, so this tree is the residue (docs/IaC/Go), not the live Rust.
- **C**: the 70 MB payload is **not** in `absorption/` — it is `docs/absorbed-from-PhenoTooling/` (70 MB, 8257 files). `docs/absorbed-from-zz-zz-agentcheck-PhenoTooling/` is 4.0 KB / 1 file and holds only the manifest pointer. No duplication of the payload; no duplicate tree.
- **D**: 40 refs, not 38. Consumed for real: 28 member entries plus 10 `[workspace.dependencies]` path pins.

## Verdicts

- **A) sharecli family — `promote`** — 119,855 LOC of real source (`src/`, `tests/`, `benches/`, `VERSION`), all 12 crates are workspace members, and it is the only substantial Rust body here; it is dead weight only in the sense that nothing else consumes it, and deleting 120k LOC with no upstream and no history to restore from is unrecoverable.
- **B) absorption/PhenoInfra — `evict-keep-manifest`** — 28 MB / 2532 files with zero workspace refs, whose Rust has already been extracted into `crates/`; the pinned commit `ecf486cab` makes the tree reproducible from `KooshaPari/PhenoInfra` (archived, so fetchable).
- **C) docs/absorbed-from-PhenoTooling — `evict-keep-manifest`** — 70 MB / 8257 mostly-JS-and-docs files with zero refs, but `ABSORPTION.md` records **no commit revision**, so the manifest must be completed (pin a SHA, or record the archive URL) *before* the payload is dropped, otherwise the content is unrecoverable.
- **D) absorption/PhenoMLX-temp — `promote`** — the one genuinely load-bearing tree: 28 member entries plus 10 dependency pins, and the source repo is a `-temp` snapshot, so it is the only durable copy of those crates.

## Disk hazard

**None found.** Checked and empty across every tree: no nested `.git` anywhere under `absorption/` (depth 5) or `crates/sharecli*`; no `target`, no `.cargo-target`, no `node_modules` under `absorption/` (depth 6) or `absorption/PhenoMLX-temp/`. All sizes above are source-only, so 70 MB is a real deduction, not build output.

## UNKNOWN

- `ABSORPTION.md` commit revision for PhenoTooling: absent. Command that would resolve it: `git ls-remote https://github.com/KooshaPari/PhenoTooling` against the archived mirror, then diff `docs/absorbed-from-PhenoTooling` file list.
- Whether `harness-native` was ever buildable: `cargo metadata` would show it is excluded; not run (read-only lane, no builds).
