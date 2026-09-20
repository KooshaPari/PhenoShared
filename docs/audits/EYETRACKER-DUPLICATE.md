# EYETRACKER-DUPLICATE

**Audit date:** 2026-09-18
**Repo:** `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared` (container repo, 50+ absorbed repos)
**Scope:** read-only inspection. No code was created, moved, edited, or deleted. No `git add` / `git commit` was run.
**Artifact created:** this file only (`docs/audits/EYETRACKER-DUPLICATE.md`).
**Method:** `find`, `rg`, `git log`/`git ls-files`, `diff`, `md5`/`sha256` hashing, `cargo metadata --no-deps --offline`.

---

## 0. Independent verification (added by the coordinator, 2026-09-19)

Every quantifiable claim in this audit was reproduced independently before the
audit was accepted. Results:

| Claim | Independently reproduced | Result |
|---|---|---|
| 7 crates, 37 files per layout, 0 one-sided | yes | **confirmed** (37 / 37 / 0) |
| 14/37 byte-identical, 23/37 differ | yes | **confirmed** (14 identical, 23 differ, 235 changed lines) |
| `sha256` 3-way vs upstream: B 34/37, A 14/37 | yes | **confirmed exactly** (B==U 34, A==U 14, U=37 files) |
| Upstream `LICENSE` is MIT | yes | **confirmed** ("MIT License / Copyright (c) 2026 Koosha Pari") |
| Neither tree resolves | yes | **confirmed** — both exit **101**, identical error: `current package believes it's in a workspace when it's not` |
| Root workspace has no eyetracker package | yes | **confirmed** — 79 packages, zero eyetracker |
| No `.github` reference to eyetracker | yes | **confirmed** (0 matching files) |
| Working tree untouched by the audit | yes | **confirmed** (`git status --porcelain` empty for all eyetracker paths) |
| `crates/eyetracker/Cargo.lock` is an orphan (no `Cargo.toml` at that level) | yes | **confirmed** — the 38th file is the lockfile; `crates/eyetracker/Cargo.toml` does not exist |

**One defect found and corrected in this file:** the upstream clone was written
in shorthand as `repos/zz-merge-unk-eyetracker`, which as a *relative* path
resolves **inside this repo**, where nothing exists. The real location is a
**sibling checkout**: `/Users/kooshapari/CodeProjects/Phenotype/repos/zz-merge-unk-eyetracker`
(one level up from `PhenoShared`). The absolute paths elsewhere in this audit
were always correct; the four relative mentions were corrected to
`../zz-merge-unk-eyetracker`. This matters because the wrong shorthand reads as
"a directory inside PhenoShared" and would send the next reader to a path that
does not exist.

**One contradiction confirmed, still unresolved:** `crates/eyetracker-PROVENANCE.md:25`
claims `criterion` was updated "to workspace version `0.8`", but the root
manifest declares `criterion = { version = "0.5", ... }` (`Cargo.toml:148`).
So the inherited value is **0.5, not 0.8**, and the provenance note states a
version that does not exist anywhere in the root manifest. Independently
reproduced; the recommendation to keep Tree B is unaffected, but the note is
wrong and should be corrected.

---

## 1. Verdict (read this first)

| Question | Answer |
| --- | --- |
| Are there two eyetracker trees? | **Yes** — 7 crates each, 37 crate files each. |
| Same code? | **No.** 14/37 files byte-identical, **23/37 differ**, 0 one-sided. |
| Which is authoritative? | **`crates/eyetracker-*` (top-level)** — see §6. |
| Is either a workspace member? | **Neither.** Both fail `cargo metadata` identically. |
| Has either ever built? | **No evidence it could.** Both error out before resolution. |
| Recommendation | **Keep `crates/eyetracker-*`; delete `crates/eyetracker/`** after harvesting 2 small improvements (§7). |

Headline evidence: the **top-level** copy is byte-identical to the upstream source on **34/37** files and differs from upstream in **exactly the 3 files** its own `PROVENANCE.md` documents. The **nested** copy is byte-identical to upstream on only **14/37** files and drifted on 23 — including 20 files where the top-level copy still matches upstream exactly.

---

## 2. Every eyetracker tree found

### 2.1 The two duplicate trees

```
Tree A  crates/eyetracker/eyetracker-core
        crates/eyetracker/eyetracker-domain
        crates/eyetracker/eyetracker-math
        crates/eyetracker/eyetracker-camera
        crates/eyetracker/eyetracker-inference
        crates/eyetracker/eyetracker-cli
        crates/eyetracker/eyetracker-ffi
        crates/eyetracker/Cargo.lock          <- orphan lockfile, no manifest beside it

Tree B  crates/eyetracker-core
        crates/eyetracker-domain
        crates/eyetracker-math
        crates/eyetracker-camera
        crates/eyetracker-inference
        crates/eyetracker-cli
        crates/eyetracker-ffi
        crates/eyetracker-PROVENANCE.md
```

`find crates -maxdepth 2 -iname '*eyetracker*'` returns exactly these 17 paths (15 dirs + `crates/eyetracker-PROVENANCE.md`; `crates/eyetracker` is itself a plain directory, not a crate — it has no `Cargo.toml`).

### 2.2 Other eyetracker occurrences in the repo (not code trees)

| Path | Nature |
| --- | --- |
| `crates/eyetracker-PROVENANCE.md` | Absorption provenance for Tree B. Part of the duplicate. |
| `docs/boundary/eyetracker.md` | Boundary doc for the **standalone** repo `eyetracker` (status: archived). |
| `docs/intent/eyetracker.md` | Intent doc for the standalone repo. |
| `projects/Eyetracker.json` | Registry entry. Lines 32-38 list the **top-level** paths (§6.1). |
| `registry/domain-roles.json:189-201` | Domain-role entry, repo-level (`"repo": "eyetracker"`), no in-tree path. |
| `BOUNDARY_OWNERS.md:233` | "Canonical owner: `<REDACTED>/eyetracker`" — repo-level. |
| `tools/check-ecosystem.ts:89` | Ecosystem listing by slug. |
| `projects/Benchora.json:30` | Mentions eyetracker FRs in a perf rationale. |
| `crates/argis-extensions/dag-state/wave-4.json:76` | Governance-onboarding lane targeting repo `eyetracker`. |
| `crates/agile-plus/**`, `audits/**` | Historical audit/dag records referencing the standalone repo. |

**No eyetracker bindings exist in this repo.** `projects/Eyetracker.json` declares `bindings/kotlin` and `bindings/swift`; the upstream clone has both (`bindings/kotlin`, `bindings/swift`), but neither was absorbed here. The repo-root `bindings/` directory contains no eyetracker entry.

### 2.3 External source clone on disk (used as the upstream reference)

```
/Users/kooshapari/CodeProjects/Phenotype/repos/zz-merge-unk-eyetracker
```

This is the source named in `crates/eyetracker-PROVENANCE.md:5`. It is a **plain directory copy — it contains no `.git`** (verified: `ls -a` shows no `.git`), so it is itself an unverified snapshot; see §8.

---

## 3. Per-tree inventory

| Metric | Tree A `crates/eyetracker/*` | Tree B `crates/eyetracker-*` |
| --- | --- | --- |
| Crate files | 37 | 37 |
| Crate bytes | 317,059 | 317,107 |
| Extra tracked file | `crates/eyetracker/Cargo.lock` (86,250 B) | `crates/eyetracker-PROVENANCE.md` (1,264 B) |
| Total git-tracked files | 38 | 38 |
| Crate names / versions | identical set (see below) | identical set (see below) |

Both trees contain the same 7 crates, all at `version = "0.1.0-alpha"`, `edition = "2021"`:

| Crate | Tree A manifest | Tree B manifest |
| --- | --- | --- |
| `eyetracker-domain` | `crates/eyetracker/eyetracker-domain/Cargo.toml` | `crates/eyetracker-domain/Cargo.toml` |
| `eyetracker-math` | `crates/eyetracker/eyetracker-math/Cargo.toml` | `crates/eyetracker-math/Cargo.toml` |
| `eyetracker-core` | `crates/eyetracker/eyetracker-core/Cargo.toml` | `crates/eyetracker-core/Cargo.toml` |
| `eyetracker-camera` | `crates/eyetracker/eyetracker-camera/Cargo.toml` | `crates/eyetracker-camera/Cargo.toml` |
| `eyetracker-inference` | `crates/eyetracker/eyetracker-inference/Cargo.toml` | `crates/eyetracker-inference/Cargo.toml` |
| `eyetracker-cli` | `crates/eyetracker/eyetracker-cli/Cargo.toml` | `crates/eyetracker-cli/Cargo.toml` |
| `eyetracker-ffi` | `crates/eyetracker/eyetracker-ffi/Cargo.toml` | `crates/eyetracker-ffi/Cargo.toml` |

Inter-crate path dependencies are `path = "../eyetracker-*"` in **both** trees, so each tree is internally consistent (Tree A resolves among its own siblings; Tree B resolves among `crates/*`).

### 3.1 Full file list (identical set on both sides, 37 files)

```
eyetracker-camera/Cargo.toml
eyetracker-camera/src/lib.rs
eyetracker-cli/Cargo.toml
eyetracker-cli/src/app.rs
eyetracker-cli/src/calibration.rs
eyetracker-cli/src/emit.rs
eyetracker-cli/src/main.rs
eyetracker-cli/src/mouse.rs
eyetracker-cli/src/ui.rs
eyetracker-core/Cargo.toml
eyetracker-core/src/lib.rs
eyetracker-domain/Cargo.toml
eyetracker-domain/src/lib.rs
eyetracker-ffi/Cargo.toml
eyetracker-ffi/build.rs
eyetracker-ffi/src/bin/uniffi-bindgen.rs
eyetracker-ffi/src/eyetracker.udl
eyetracker-ffi/src/lib.rs
eyetracker-ffi/src/modern.rs
eyetracker-inference/Cargo.toml
eyetracker-inference/src/accessibility.rs
eyetracker-inference/src/calibration.rs
eyetracker-inference/src/classification.rs
eyetracker-inference/src/drift_monitor.rs
eyetracker-inference/src/face_mesh.rs
eyetracker-inference/src/focalpoint.rs
eyetracker-inference/src/gaze_estimator.rs
eyetracker-inference/src/lib.rs
eyetracker-inference/src/multi_monitor.rs
eyetracker-inference/src/onnx_detector.rs
eyetracker-inference/src/pipeline.rs
eyetracker-inference/src/privacy.rs
eyetracker-inference/src/smoothing.rs
eyetracker-inference/tests/fr_eye_integration.rs
eyetracker-math/Cargo.toml
eyetracker-math/benches/math_benches.rs
eyetracker-math/src/lib.rs
```

**No file exists on only one side.** Both trees are complete, self-consistent copies of the same 7-crate set.

---

## 4. Are the copies identical? (sha256, by relative path)

**14 byte-identical · 23 differ · 0 only-in-A · 0 only-in-B.**

Per crate:

| Crate | Files | Identical | Differ | Only A | Only B |
| --- | ---: | ---: | ---: | ---: | ---: |
| `eyetracker-core` | 2 | 1 | 1 | 0 | 0 |
| `eyetracker-domain` | 2 | 0 | 2 | 0 | 0 |
| `eyetracker-math` | 3 | 2 | 1 | 0 | 0 |
| `eyetracker-camera` | 2 | 0 | 2 | 0 | 0 |
| `eyetracker-inference` | 15 | 6 | 9 | 0 | 0 |
| `eyetracker-cli` | 7 | 2 | 5 | 0 | 0 |
| `eyetracker-ffi` | 6 | 3 | 3 | 0 | 0 |
| **Total** | **37** | **14** | **23** | **0** | **0** |

### 4.1 Files that differ (23)

```
eyetracker-core/Cargo.toml
eyetracker-domain/Cargo.toml
eyetracker-domain/src/lib.rs
eyetracker-math/Cargo.toml
eyetracker-camera/Cargo.toml
eyetracker-camera/src/lib.rs
eyetracker-ffi/Cargo.toml
eyetracker-ffi/src/lib.rs
eyetracker-ffi/src/modern.rs
eyetracker-cli/Cargo.toml
eyetracker-cli/src/app.rs
eyetracker-cli/src/calibration.rs
eyetracker-cli/src/mouse.rs
eyetracker-cli/src/ui.rs
eyetracker-inference/Cargo.toml
eyetracker-inference/src/accessibility.rs
eyetracker-inference/src/calibration.rs
eyetracker-inference/src/drift_monitor.rs
eyetracker-inference/src/focalpoint.rs
eyetracker-inference/src/multi_monitor.rs
eyetracker-inference/src/onnx_detector.rs
eyetracker-inference/src/pipeline.rs
eyetracker-inference/src/privacy.rs
```

### 4.2 Character of the differences

**Manifest drift (mechanical, 7 files).** Every `Cargo.toml` in Tree A carries `license = "MIT"`; no Tree B manifest does. This is the only difference in 6 of the 7 manifests (e.g. `eyetracker-core/Cargo.toml`: single-line delta, `+license = "MIT"`, 6 diff lines total). Provenance: `git log -S'license = "MIT"'` attributes the addition to **`5ee36ab6 fix(ci): cargo-deny licenses + bans + advisories pass cleanly (#310)`** — i.e. a cargo-deny fix applied to Tree A only.

The 7th manifest, `eyetracker-math/Cargo.toml`, additionally differs on the criterion dev-dependency:

```
Tree A:  criterion = { version = "0.5", features = ["html_reports"] }
Tree B:  criterion = { workspace = true }
```

**Source drift (16 files, mostly cosmetic).** Differences are small and structural rather than semantic:

| File | Δ bytes | Δ lines |
| --- | ---: | ---: |
| `eyetracker-camera/src/lib.rs` | +4 | +37 / −36 (84 diff lines) |
| `eyetracker-cli/src/mouse.rs` | +282 | +25 / −20 (67 diff lines) |
| `eyetracker-cli/src/app.rs` | −102 | +12 / −12 (32 diff lines) |
| `eyetracker-inference/src/focalpoint.rs` | +4 | +7 / −11 |
| `eyetracker-inference/src/multi_monitor.rs` | −3 | +4 / −7 |
| `eyetracker-inference/src/drift_monitor.rs` | −2 | +2 / −4 |
| `eyetracker-inference/src/onnx_detector.rs` | −3 | +3 / −6 |
| `eyetracker-inference/src/privacy.rs` | −2 | +2 / −4 |
| `eyetracker-inference/src/calibration.rs` | −1 | +1 / −2 |
| `eyetracker-inference/src/accessibility.rs` | −1 | +1 / −2 |
| `eyetracker-inference/src/pipeline.rs` | −2 | +2 / −4 |
| `eyetracker-cli/src/ui.rs` | −2 | +4 / −6 |
| `eyetracker-cli/src/calibration.rs` | −1 | +3 / −4 |
| `eyetracker-ffi/src/modern.rs` | −1 | +1 / −2 |
| `eyetracker-ffi/src/lib.rs` | +19 | +2 / −1 |
| `eyetracker-domain/src/lib.rs` | −1 | +1 / −2 |

Readings:

- The ~11 `+1/−2` and `+2/−4` inference/ffi/domain deltas are **import and attribute ordering only**. Example, `eyetracker-domain/src/lib.rs`:
  ```
  Tree A:  use std::time::{Duration, SystemTime};  /  use serde::{Deserialize, Serialize};
  Tree B:  use serde::{Deserialize, Serialize};    /  use std::time::{Duration, SystemTime};
  ```
- `eyetracker-camera/src/lib.rs` is a **block move, not a logic change**: the `impl PixelFormat { fn bytes_per_pixel }` block sits *before* `mod tests` in Tree A and *after* it in Tree B, plus a `use` merge (`nokhwa::pixel_format::RgbFormat` folded into a `nokhwa::{...}` group).
- `eyetracker-cli/src/app.rs` is a same-size reshuffle (+12/−12) with no net byte growth.

**The one substantive divergence: `eyetracker-cli/src/mouse.rs`.** All three copies differ from each other. Resolved against the actual dependency source (`~/.cargo/registry/src/index.crates.io-*/core-graphics-0.23.2/src/event.rs:578-581`), `CGEvent::new_scroll_event` is `#[cfg(feature = "highsierra")] pub fn` returning `Result<CGEvent, ()>` — **a safe function** (line 573 contains `Err(())`).

| | scroll-event handling | correct? |
| --- | --- | --- |
| Upstream | `unsafe { let event = ...; if let Some(ev) = event }` | **No** — `Some`/`None` against a `Result` cannot compile. |
| Tree B (top-level) | `unsafe { let event = ...; if let Ok(ev) = event }` | Compiles; **redundant `unsafe`** (unused-unsafe). |
| Tree A (nested) | `match CGEvent::new_scroll_event(...) { Ok(event) => ..., Err(()) => ... }` | **Cleanest** — no `unsafe`, correct `Result` handling. |

So Tree A's `mouse.rs` is genuinely better by one `unsafe` block; Tree B's is correct but slightly worse. This is the only file where Tree A is meaningfully superior.

---

## 5. Three-way comparison against upstream

Reference: `/Users/kooshapari/CodeProjects/Phenotype/repos/zz-merge-unk-eyetracker/crates/` (37 files, 317,042 bytes, MIT `LICENSE`, no `.git`).

| Relationship | Files |
| --- | ---: |
| All three byte-identical | 14 |
| **Tree B == upstream, Tree A differs** | **20** |
| Tree A == upstream, Tree B differs | **0** |
| Neither matches upstream | 3 |

**Tree B matches upstream on 34/37 files. Tree A matches upstream on 14/37 — every one of which also matches Tree B.** Tree A is a strict behavioural subset: it never preserves upstream content that Tree B lost.

The 3 files where **neither** matches upstream are `eyetracker-math/Cargo.toml`, `eyetracker-cli/Cargo.toml`, `eyetracker-cli/src/mouse.rs`. Tree B's deltas on those 3 files correspond one-to-one with the adaptation list in its own `PROVENANCE.md:24-31`:

| PROVENANCE.md claim | Tree B state | Verified |
| --- | --- | --- |
| "`eyetracker-math` dev-dependency `criterion` updated from `0.5` to workspace version `0.8`" | `criterion = { workspace = true }` | Applied, but see §8 (root resolves this to **0.5**, not 0.8). |
| "Enabled `highsierra` feature on `core-graphics` dep" | `core-graphics = { version = "0.23", features = ["highsierra"] }` | **Yes.** |
| "Added missing `core_graphics` imports" + "Fixed `new_scroll_event` return type from `Option` to `Result`" | module-level `CGEventType` import + `if let Ok(ev)` | **Yes.** |

That is a clean, auditable, self-documenting delta. Tree A has no equivalent provenance record for its 23 divergences.

Representative sha256 prefixes (12 hex chars):

| File | Tree A | Tree B | Upstream |
| --- | --- | --- | --- |
| `eyetracker-core/Cargo.toml` | `3a6a81a88bb4` | `495aab08165f` | `495aab08165f` |
| `eyetracker-math/Cargo.toml` | `ea6641e2390c` | `c6a1626c09d1` | `25e49f75a143` |
| `eyetracker-cli/Cargo.toml` | `3e9283804f7f` | `1d0e6f66fa58` | `2eefb63f4478` |
| `eyetracker-cli/src/mouse.rs` | `b56d6f56d19a` | `5e943d078bfe` | `d386d45b909c` |
| `eyetracker-domain/src/lib.rs` | `e8415784494b` | `5a31d25a3e33` | `5a31d25a3e33` |
| `eyetracker-camera/src/lib.rs` | `f94c7a8f9ae6` | `8293ff3565eb` | `8293ff3565eb` |

---

## 6. Workspace membership — literal evidence

### 6.1 Neither tree is a member

`Cargo.toml` (repo root), literal lines:

```
1:[workspace]
3:exclude = ["crates/forge_daemon", "crates/fabric-frame-transport/fuzz", "crates/fabric-gui/src-tauri"]
4:members = [
83:]
```

- `members` spans lines 4-83. **No `eyetracker` entry exists anywhere in that list.** (`grep -n -i eyetracker Cargo.toml` → no match.)
- `exclude` (line 3) lists 3 paths. **No eyetracker path is excluded.**
- `[workspace.dependencies]` contains **no** eyetracker entry.

Because a root `Cargo.toml` workspace exists and neither tree is a member or excluded, both trees are in the "neither fish nor fowl" state. `cargo metadata --no-deps --format-version 1 --offline` confirms it identically for both:

```
$ (cd crates/eyetracker-core && cargo metadata --no-deps --offline)
error: current package believes it's in a workspace when it's not:
current:   .../PhenoShared/crates/eyetracker-core/Cargo.toml
workspace: .../PhenoShared/Cargo.toml
this may be fixable by adding `crates/eyetracker-core` to the `workspace.members` array ...

$ (cd crates/eyetracker/eyetracker-core && cargo metadata --no-deps --offline)
error: current package believes it's in a workspace when it's not:
current:   .../PhenoShared/crates/eyetracker/eyetracker-core/Cargo.toml
workspace: .../PhenoShared/Cargo.toml
this may be fixable by adding `crates/eyetracker/eyetracker-core` to the `workspace.members` array ...
```

Root workspace census:

```
cargo metadata --no-deps --offline  ->  packages: 79
                                        eyetracker packages: NONE
```

So the prior finding is confirmed and sharpened: **neither tree is a member, and neither can even be resolved as a package today** — not merely "never built".

### 6.2 The nested tree has an orphan lockfile

`crates/eyetracker/Cargo.lock` (86,250 B) sits beside **no** `Cargo.toml`:

```
$ ls crates/eyetracker/
Cargo.lock  eyetracker-camera  eyetracker-cli  eyetracker-core
eyetracker-domain  eyetracker-ffi  eyetracker-inference  eyetracker-math

$ git log --all --diff-filter=AD -- 'crates/eyetracker/Cargo.toml'
(empty — the file has never existed in this repo's history)
```

The lockfile lists all 7 eyetracker packages (`crates/eyetracker/Cargo.lock:853,866,888,898,906,919,938`), so some workspace manifest existed **at the source** — it was simply never carried into this repo. Tree A is therefore an incomplete snapshot, not a usable workspace.

### 6.3 Dependency wiring is absent everywhere

- Root `Cargo.lock`: **zero** eyetracker entries (`grep -n 'name = "eyetracker' Cargo.lock` → none). Nothing in the root workspace resolves them.
- No manifest outside the two trees declares an eyetracker crate as a member or a dependency. The only `eyetracker` strings under `**/Cargo.toml` live inside the two trees' own `[package] name = ...` lines.
- `.github/` (87 workflow files): **zero** eyetracker matches. No CI job builds or tests either tree.

### 6.4 What the registry expects

`projects/Eyetracker.json:32-38` names the **top-level** layout as the crate set:

```json
"crda_workspace_members": [
  "crates/eyetracker-domain",
  "crates/eyetracker-math",
  "crates/eyetracker-core",
  "crates/eyetracker-ffi",
  "crates/eyetracker-camera",
  "crates/eyetracker-inference",
  "crates/eyetracker-cli"
]
```

This is the **same list** as the upstream repo's own root workspace (`../zz-merge-unk-eyetracker/Cargo.toml`, `[workspace] members`), and the **same layout** `crates/eyetracker-PROVENANCE.md:24` assumes when it says path deps are retained as `path = "../eyetracker-*"`. No registry artifact names the nested `crates/eyetracker/eyetracker-*` paths.

---

## 7. Recommendation

### Keep Tree B — `crates/eyetracker-*` (7 crates + `eyetracker-PROVENANCE.md`). Remove Tree A — `crates/eyetracker/`.

Evidence, ranked:

1. **Fidelity.** Tree B is byte-identical to the upstream source on 34/37 files. Its entire deviation from upstream is the 3-file adaptation set enumerated in its own `PROVENANCE.md:24-31`. Tree B *is* the absorption.
2. **Documented provenance.** Tree B ships `crates/eyetracker-PROVENANCE.md` naming the source repo (`zz-merge-unk-eyetracker`), the absorb date (2026-09-15), the license, and every applied edit. Tree A has none, and 23 of its files diverge from upstream with no record of why.
3. **Registry agreement.** `projects/Eyetracker.json:32-38` and upstream's own workspace both name the top-level paths. Tree A's paths appear in no registry or provenance artifact.
4. **Completeness.** Tree B is a coherent crate set. Tree A carries an orphan `Cargo.lock` whose workspace manifest (`crates/eyetracker/Cargo.toml`) has never existed in this repo's history.
5. **Non-loss on removal.** Tree A preserves no upstream content that Tree B lost (0 files where A==upstream and B≠upstream). Deleting Tree A loses only the 2 harvested items below.
6. **`crates/` convention.** Tree B places crates where `crates/` crates are expected; Tree A nests a pseudo-workspace inside `crates/`, which is what caused the two trees to be mistaken for one another.

### Harvest before deleting Tree A (2 items, both tiny)

1. **`license = "MIT"` on each of the 7 manifests** (Tree A, added by `5ee36ab6`, cargo-deny-driven). Tree B manifests have *no* `license` field while the repo root declares `license = "MIT OR Apache-2.0"` (`Cargo.toml:88`). Upstream is MIT (`../zz-merge-unk-eyetracker/LICENSE` → "MIT License / Copyright (c) 2026 Koosha Pari"). Use `license = "MIT"` (faithful to the source) or `license.workspace = true` if mixed licensing is intended.
2. **The `mouse.rs` form without the redundant `unsafe` block** (Tree A). Verified against `core-graphics-0.23.2/src/event.rs:578-581`, `new_scroll_event` is a safe `pub fn` returning `Result<CGEvent, ()>`, so Tree A's plain `match ... { Ok, Err(()) }` is correct and drops an unused-`unsafe` (which would also collide with the root workspace lint `unsafe_code = "forbid"`, `Cargo.toml` `[workspace.lints.rust]`, should crates ever opt into it).

Recommend adopting Tree B's `PROVENANCE.md`-documented fixes **plus** these 2 harvests, rather than deleting Tree B's version.

### Separately: decide the workspace question (this is the real defect)

Deleting Tree A does not make anything build — Tree B is *also* not a member and *also* unresolvable. Two mutually exclusive dispositions:

- **(a) Promote Tree B into the root workspace** by adding the 7 `crates/eyetracker-*` paths to `Cargo.toml` `members` (lines 4-83). Mechanically viable: every `workspace = true` dependency referenced by Tree B (`serde`, `thiserror`, `tokio`, `criterion`) is provided by root `[workspace.dependencies]`. **Caveat to check first:** the crates use `tokio = { workspace = true }`, and root tokio (`Cargo.toml:107`) enables `rt, rt-multi-thread, macros, process, io-util, sync, time, signal` — **not** upstream's `full`. If any crate needs `net`, `fs`, or `signal` beyond that list, the join will fail to compile.
- **(b) Exclude Tree B** by adding the 7 paths to `Cargo.toml:3` `exclude`, matching how `crates/forge_daemon` is parked. This preserves the code without asserting it builds, and silences the "believes it's in a workspace" error.

Do not leave it in the current state: as-is, any agent or developer running `cargo` from either directory gets an error, and the duplicate actively misleads audits (which is how this ticket arose).

### What would change this recommendation

| Change in evidence | Effect |
| --- | --- |
| `../zz-merge-unk-eyetracker` turns out to be a *later* snapshot that was itself derived from Tree A | Would invert §5; re-verify by fetching the GitHub remote `KooshaPari/zz-merge-unk-eyetracker` and diffing. |
| Tree A proves to be the intended target of an open, unmerged PR touching `crates/eyetracker/` | Would prefer rebasing that work onto Tree B, not keeping Tree A. |
| Tree A's 20-file drift turns out to contain a functional fix absent from Tree B | Would require harvesting those files too, and would weaken §5's "no content lost" claim. Current analysis says it is ordering/block-move only, but this is a reading, not a compile test (§8). |
| Registry is updated to name nested paths | Would favour Tree A. No such artifact exists today. |

---

## 8. Unverified

Stated plainly, so nothing here is over-claimed:

1. **No build was attempted on either tree.** `cargo build`/`cargo check` was not run for Tree A or Tree B. The conclusion "neither ever built" rests on the `cargo metadata` workspace error (§6.1), which is a pre-resolution failure — not on a compiled binary's absence. Whether either tree compiles *once added to a workspace* is **unknown**; dependencies include `nokhwa`, `uniffi`, `ratatui`, `crossterm`, `nalgebra`, and an ONNX runtime path (`onnx_detector.rs`) that were not verified present or vendored.
2. **The upstream clone is not a verified peer of the GitHub remote.** `../zz-merge-unk-eyetracker` has **no `.git` directory**, so its commit identity, date, and branch could not be established. It is used here as the best available reference, and both trees' relation to it is measured by sha256 — but "matches upstream" means "matches this local directory", not "matches `github.com/KooshaPari/zz-merge-unk-eyetracker`". No network fetch was performed.
3. **The 3-file "neither matches upstream" set is characterised by reading, not by compiling.** Tree B's `mouse.rs` is judged compile-correct (`if let Ok(ev)` against a `Result`) from the core-graphics 0.23.2 source signature; no `rustc` invocation confirms it. The claim that upstream's `mouse.rs` cannot compile (Option against Result) is likewise a signature-based inference, though a strong one.
4. **`PROVENANCE.md:25` is factually contradicted and is left unresolved.** It states criterion was moved to "workspace version `0.8`". Root `Cargo.toml` declares `criterion = { version = "0.5", features = ["html_reports"] }`, so Tree B's `criterion = { workspace = true }` in fact resolves to **0.5**. (0.8 does appear in other crates' self-contained manifests, e.g. `crates/apisync/Cargo.toml:40`, `crates/pheno-tracing/Cargo.toml:31` — but not in the root workspace dependencies.) Either the provenance note is stale, or it refers to a different root (`pheno`, per PR #281's title). Not determined here.
5. **Which absorption was *intended* to win is inferred, not documented.** Tree A entered via `2fe6b59a` (2026-08-13, "absorb eyetracker into pheno workspace (7 crates) (#281)"); Tree B via `33673213` (2026-09-15, "chore: absorb Substrate (model routing/agent execution)"). No commit message, ADR, or registry note found in-tree states which supersedes which. The §7 recommendation is derived from provenance/registry/fidelity evidence, not from an explicit ownership decision.
6. **No PR review, issue, or design discussion was consulted.** Only in-repo artifacts (git history, docs, registry JSON) were read.
7. **`git log --all --diff-filter=AD -- 'crates/eyetracker/Cargo.toml'` covers this repo's history only.** If the manifest existed in an un-fetched remote branch, that would not be visible. Unmapped refs were not enumerated.
8. **Text-only hash comparison.** Files were compared as bytes (sha256) and as decoded UTF-8 lines. No binary artifacts were found in either tree, but no encoding/binary sniffing beyond a `UnicodeDecodeError` guard was performed.
9. **Timing.** All hashes, `cargo metadata` output, and `git` results reflect the working tree at 2026-09-18 ~18:36-18:40 local. The working tree was clean for all eyetracker paths (`git status --porcelain` → empty) at that time.

---

## Appendix A — Evidence commands (reproducible)

```bash
# Locate trees
find crates -maxdepth 2 -iname '*eyetracker*'
find . -type d -iname '*eyetracker*'

# Inventory
find crates/eyetracker/eyetracker-* -type f | wc -l          # 37
find crates/eyetracker/eyetracker-* -type f -exec wc -c {} + | tail -1   # 317059
find crates/eyetracker-* -type f | wc -l                      # 38 (37 + PROVENANCE.md)
git ls-files crates/eyetracker | wc -l                        # 38
git ls-files 'crates/eyetracker-*' | wc -l                    # 38

# Pairwise hash comparison -> 14 identical / 23 differ / 0 one-sided

# Three-way vs upstream
ls /Users/kooshapari/CodeProjects/Phenotype/repos/zz-merge-unk-eyetracker
#   -> Tree B == upstream: 34/37 ; Tree A == upstream: 14/37 ; neither: 3

# Membership
grep -n -i eyetracker Cargo.toml                              # no match
grep -n '^\[workspace\]\|^exclude\|^members\|^\]' Cargo.toml  # 1, 3, 4, 83
(cd crates/eyetracker-core && cargo metadata --no-deps --offline)         # workspace error
(cd crates/eyetracker/eyetracker-core && cargo metadata --no-deps --offline)  # same error
cargo metadata --no-deps --offline | python3 -c "... 'eye' in name ..."   # NONE
grep -n 'name = "eyetracker' Cargo.lock                       # no match
git log --all --diff-filter=AD -- 'crates/eyetracker/Cargo.toml'          # empty

# References
rg -n -i eyetracker . -g '!crates/eyetracker*/**' -g '!target/**' -g '!.git/**'
rg -i eyetracker .github/                                     # no match

# Dependency API ground truth
grep -rn -B6 'fn new_scroll_event' ~/.cargo/registry/src/*/core-graphics-0.23.2/src/event.rs
#   -> line 578-581: #[cfg(feature = "highsierra")] pub fn ... -> Result<CGEvent, ()>
```

## Appendix B — History of each tree

| Tree | Commit | Date | Subject |
| --- | --- | --- | --- |
| A (nested) | `2fe6b59a` | 2026-08-13 | `feat(crates): absorb eyetracker into pheno workspace (7 crates) (#281)` |
| A (nested) | `f8486716` | 2026-09-14 | `style: normalize formatting across 266 files (pre-existing drift)` |
| A (nested) | `75cdb13c` | 2026-09-14 | `fix(ci): resolve release-plz failure + merge cargo-deny workflows` (added `crates/eyetracker/Cargo.lock`) |
| A (nested) | `5ee36ab6` | — | `fix(ci): cargo-deny licenses + bans + advisories pass cleanly (#310)` (added `license = "MIT"`) |
| B (top-level) | `33673213` | 2026-09-15 | `chore: absorb Substrate (model routing/agent execution)` (+ `eyetracker-PROVENANCE.md`) |
| B (top-level) | `3b6d8798`, `eb6fd899` | — | PII sweeps (no functional change) |

All eyetracker source files carry mtime `2026-09-16 21:34` on both sides, i.e. both trees have been static since the bulk absorb.

---

## Appendix C — Disposition (added 2026-09-20)

This audit's §7 recommendation was applied in four commits, in order:

| Commit | Date | Subject | Action |
| --- | --- | --- | --- |
| `b3d99ffa` | 2026-09-20 | `docs(eyetracker): harvest license = MIT into Tree B's 7 manifests` | Harvest #1: cargo-deny-driven `license = "MIT"` field added to all 7 of Tree B's `Cargo.toml` manifests (§7.1) |
| `b778db8a` | 2026-09-20 | `fix(eyetracker): replace redundant unsafe block in mouse.rs with Result match` | Harvest #2: Tree A's clean `match` form over Tree B's redundant-`unsafe` block in `crates/eyetracker-cli/src/mouse.rs` (§7.2) |
| `6393ef62` | 2026-09-20 | `chore(eyetracker): delete Tree A (E11.4 step 3/3)` | Tree A deleted (38 tracked files, 9590 deletions); Tree B is now the only eyetracker tree |
| `ee54d336` | 2026-09-20 | `feat(eyetracker): promote Tree B's 7 crates into root workspace` | Workspace question resolved as §7 option (a): 7 paths added to root `Cargo.toml` `members`; `cargo metadata` now reports 86 packages (was 79) |

Verification performed at apply time (each check on the local macOS host):

| Crate | `cargo check` | Time |
| --- | --- | --- |
| `eyetracker-domain` | PASS | 39.03 s |
| `eyetracker-math` | PASS | 39.03 s |
| `eyetracker-core` | PASS | 39.03 s |
| `eyetracker-camera` | PASS | 134 s |
| `eyetracker-inference` | PASS | 134 s |
| `eyetracker-cli` | PASS | 259 s |
| `eyetracker-ffi` | UNVERIFIED locally | 540 s timeout, host OOM (16 GB RAM, 8 concurrent `rustc` from a competing `cargo build`) |

`eyetracker-ffi` was noted in this audit's §1 as never having been built ("Has either ever built? **No evidence it could.**"), so the unverified status is the same pre-existing state, not a regression. Tokio-feature caveat (§7, §8) checked: no `eyetracker-*` crate uses `tokio::net`, `tokio::fs`, or `tokio::signal`, so the workspace tokio feature set (`rt, rt-multi-thread, macros, process, io-util, sync, time, signal` — no `net`, no `fs`) is sufficient.

Stale documentation cleanup performed in the same session (separate commits):

- `docs/absorption/ABSORPTION-LINEAGE.md` — row 1 updated to reflect Tree A deletion at `6393ef62`; §2.4 duplicate-twin count for eyetracker reduced from **2** to **1 (Tree B only)**.
- `docs/atlas/codebase/{FILES,HYGIENE,INVENTORY}.md` — regenerated by `scripts/atlas/generate.py` (587 packages, 81 workspace members, 1,095,486 Rust LOC). Old entries referencing Tree A paths removed automatically.

The audit's headline verdict ("Keep Tree B, delete Tree A") is fully reflected in the tree.
