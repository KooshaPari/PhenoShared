# WORKSPACE BUILD AUDIT — how much of this repo actually compiles

**Epic:** E2 (build measurability)
**Repo:** `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared`
**Branch:** `main`
**Measured:** 2026-09-18 18:35 – 19:04 PDT (2026-09-19 01:35 – 02:04 UTC)
**Author:** jcode agent
**Status:** measurement complete for the workspace; **partial and bounded** for non-member crates.

**Nothing in this document is inferred from a prior inventory. Every number below comes from a command
that was run in this session, with its exit code recorded.** Where something was not measured, it says so.

---

## 0a. Coordinator verification (2026-09-19)

**Confirmed.** `cargo metadata --no-deps` → **79** members; `find . -name
Cargo.toml` (excl. `target/`) → **594**. Both match this audit exactly.

**The linker anomaly is real, and I reproduced it independently.** Plain `cc`
on a two-line C program exits **1**:

```
ld: tapi error: malformed file
/Library/Developer/CommandLineTools/SDKs/MacOSX27.0.sdk/usr/lib/libSystem.B.tbd:4:20:
  error: unknown architecture
                   arm64e.x1-macos, arm64e.x1-maccatalyst ]
clang: error: linker command failed with exit code 1
```

Toolchain split-brain confirmed: `xcode-select -p` →
`/Applications/Xcode.app/Contents/Developer`, while `xcrun --show-sdk-path` →
`/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk`. And `SDKROOT=<xcode sdk>`
alone is sufficient to fix it (exit 0, binary produced) — no `-isysroot` flag
needed.

**But the impact stated in §6 is too broad, and I am narrowing it.** §6 says a
"`cargo build` of a binary from a cold target dir" can fail. That is **not**
reproduced: a trivial cold-dir crate built fine **without** `SDKROOT`, and
`cargo build --offline -p phinbox` **linked successfully** (28 s). Ordinary Rust
linking is unaffected, because rustc resolves a usable SDK for its own link
step.

Measured blast radius instead of a general claim:

| Surface | Count | Affected? |
|---|---|---|
| Crates with a `cc` build-dependency | **2** (`kernels/qwen3.5-0.8b/rust`, `_archived/nvms-ffi`) | yes — both outside the workspace / archived |
| Crates depending on a `*-sys` crate (FFI/bindgen) | **14** | at risk; `cc` crate may or may not pass a good SDK |
| Ordinary Rust binaries | — | **no** (phinbox links) |

So this is a **narrow host defect with a known one-line workaround**, not a
workspace-wide build blocker. It should still be fixed (see E2.6 in
`docs/plan/FORWARD-WBS.md`), because a build that silently depends on rustc's
SDK resolution rather than the system's is exactly the kind of latent trap this
program exists to find.

## 0. Headline
| Question | Answer |
| --- | --- |
| Workspace members (real, from `cargo metadata`) | **79** |
| `Cargo.toml` files on disk (excl. `target/`) | **594** → 79 members + **515 non-members** |
| Does `cargo check --workspace` succeed? | **Yes**, exit 0 — both warm and **cold** (fresh `--target-dir`) |
| Does `cargo check --workspace --all-targets` succeed? | **Yes**, exit 0 — 79/79 members, incl. 70 test + 11 bench + 2 example targets |
| Crates that FAILED to compile (workspace) | **0** |
| Was the 20-minute time box hit? | **No.** Workspace compiles totalled ~297 s; full non-member sweep added ~325 s |
| Non-member manifests that even load | **75 / 515** (440 fail before compilation is attempted) |
| Non-member manifests that compile | **40 pass / 35 fail** (of the 75 that load) |
| Non-member crates with *real* compile errors | **4 distinct crates** (6 manifest entries) |
| Biggest blocker to measuring non-members | **Manifest/workspace configuration, not code**: 292 "believes it's in a workspace when it's not" + 109 `workspace = true` inheritance errors |

The single most important caveat: **`cargo check` is not `cargo build`, and `check` never links an
executable.** This environment has a genuine linker defect (Section 6) that is invisible to
`cargo check` on a warm target directory and visible only when something must actually be linked.
That distinction is carried through this whole document.

---

## 1. Environment

| Item | Value (observed) |
| --- | --- |
| `cargo --version` | `cargo 1.97.1 (c980f4866 2026-06-30)` |
| `rustc --version` | `rustc 1.97.1 (8bab26f4f 2026-07-14)` |
| `rust-toolchain.toml` | `channel = "stable"`, components `rustfmt`, `clippy` |
| Rust workspace resolver | `resolver = "2"` |
| Host CPU count | 10 |
| Pre-existing `target/` | **8.7 GB** (present before this audit; not created or deleted by it) |
| Free disk at end | 62 GiB |
| `sccache` | installed at `/opt/homebrew/bin/sccache` but **not wired in** (`RUSTC_WRAPPER` unset, no repo `.cargo/config.toml`) |

**Baseline state matters.** `target/` was already 8.7 GB and heavily populated when this audit began.
A `cargo check --workspace` in that state reuses cached artifacts and is *not* evidence that the
sources compile from scratch. Section 3 therefore repeats the check against a **fresh `--target-dir`**,
which is the honest measurement. `cargo clean` was not run (prohibited by the task).

---

## 2. Ground truth on scope

### 2.1 Commands and results

```bash
cargo metadata --no-deps --format-version 1        # exit 0
```
- `workspace_members` = **79**
- `packages` = **79**
- `workspace_default_members` = **79**
- `target_directory` = `<repo>/target`

```bash
cargo metadata --format-version 1 --offline        # exit 0, 2.2 s
```
Full dependency resolution succeeds **offline** — the registry cache is complete for the workspace.
(Important: this is what makes `--offline` a safe measurement tool rather than an artificial blocker
for the *workspace*. It is not complete for the non-members; see 5.3.)

```bash
find . -name Cargo.toml -not -path "./target/*" | wc -l     # 594
```

### 2.2 Members: explicit vs. resolved

The root `Cargo.toml` explicitly lists **74** member strings. Cargo resolves **79**. The 5 extra are
path dependencies that live inside the workspace root, which Cargo auto-promotes to members:

```
crates/argis-extensions/pheno-otel
crates/pheno-tracing
crates/phenotype-health
crates/phenotype-router
crates/phenotype-tooling-observability
```

`listed but NOT resolved:` **none**. So 74 + 5 = 79 is fully reconciled — there is no phantom member.

### 2.3 The real on-disk vs. in-workspace gap

| Scope | Count |
| --- | --- |
| `Cargo.toml` on disk (excl. `target/`) | **594** |
| Workspace members | **79** |
| Non-member manifests | **515** |
| — of which: the repo-root workspace manifest itself (no `[package]`) | 1 |
| — **candidate non-member *package* manifests** | **514** |

Under `crates/` alone: **494 manifests = 76 members + 418 non-members.**
So **85 % of the manifests under `crates/` are not in the workspace.**

Non-member manifests by top-level directory:

| Dir | Non-members | Dir | Non-members |
| --- | --- | --- | --- |
| `crates/` | 418 | `absorption/` | 3 |
| `infrakit/` | 30 | `tests/` | 2 |
| `registry/` | 10 | `servers/` | 2 |
| `archives/` | 9 | `libs/` | 2 |
| `iac/` | 8 | `tools/`, `templates/`, `rust/`, `python/`, `native/`, `kernels/`, `fuzz/`, `bifrost/`, `forgecode-fork/`, `phenotype-router-monitor/`, root `Cargo.toml` | 1 each |
| `_archived/` | 7 | | |
| `agents/` | 5 | | |
| `audits/` | 4 | | |
| `agileplus-agents/` | 4 | | |

**40 of the 515 non-member manifests declare their own `[workspace]` table.** That means this
repository contains **at least 40 nested, independent Cargo workspaces** that the root workspace
neither builds nor sees.

### 2.4 LOC reconciliation with the prior inventory

```bash
find . -name '*.rs' -not -path './target/*' -print0 | xargs -0 cat | wc -l   # 1,104,786
find . -name '*.rs' -not -path './target/*' | wc -l                          # 5,759
```

Prior inventory claimed 594 packages / 29,061 files / 1,104,852 Rust LOC. The LOC reconciles
(1,104,786 vs 1,104,852 — a 66-line drift consistent with edits since). Note that the prior
"**594 packages**" is actually **594 `Cargo.toml` files**, of which only 79 are real workspace
packages; the "29,061 files" figure counts all file types, not Rust files (there are 5,759 `.rs`).

---

## 3. Measurement 1 — the workspace (79 members)

### 3.1 Time box

**Time box: 20 minutes. NOT HIT.**

| Run | Wall time |
| --- | --- |
| (a) warm `target/` | 46 s |
| (b) cold, fresh `--target-dir` | 106 s |
| (c) cold control, `SDKROOT` unset | 114 s |
| (d) `--all-targets`, incremental on (b)'s dir | 31 s |
| **Total for all workspace compilation measurement** | **297 s ≈ 5 min** |

No run needed to be killed.

### 3.2 Run (a) — warm target directory

```bash
cargo check --workspace --offline --message-format=json
```
- **exit code 0**, 01:37:42Z → 01:38:28Z (**46 s**)
- `build-finished.success = True`
- 704 `compiler-artifact` events covering **586 distinct packages** (79 members + transitive deps)
- **676 artifacts were `fresh: true`, only 28 were actually (re)compiled**
- **errors: 0**, warnings: 1 (`function \`now\` is never used`)

**Interpretation — this run is weak evidence.** Because 676/704 artifacts were already cached, run (a)
proves only that *no currently-invalidated unit failed*. It is consistent with a broken tree that
simply has not been invalidated. It is **not** evidence that the 79 members compile from scratch.

The 21 non-fresh targets that were genuinely recompiled:

```
crates/driver-cli (substrate)                 crates/fabric-tui (fabric-tui)
crates/driver-http (substrate-http)           crates/phenotype-tooling-observability (breach_sim)
crates/fabric-capture (build-script-build)    crates/phinbox (phinbox, phinbox-mcp)
crates/fabric-capture (fabric-capture)        crates/substrate-tui (substrate-tui)
crates/fabric-cli (fabric)                    examples/full-demo (fabric-full-demo)
crates/fabric-daemon (fabric-daemon)          tools/fake-codex-cloud (fake-codex-cloud)
crates/fabric-graph-cli (fabric-graph-cli)    tools/fake-forge (bench-fake-forge, fake-forge)
crates/fabric-orchestrator (fabric-orchestrator)
crates/fabric-terminal (tf-sync, tf-web)
crates/fabric-tray (fabric-tray)
```

78 of 79 members produced at least one artifact. The missing one is `crates/wave-3lane-tests`, which
declares **only** a `[[test]]` target — `cargo check --workspace` without `--all-targets` does not
build test targets, so it produced no artifact. That is expected behaviour, not a failure.

### 3.3 Run (b) — COLD, fresh target directory (the real measurement)

```bash
cargo check --workspace --offline \
  --target-dir /Users/kooshapari/.jcode/scratch/phenoshared-cold-target \
  --message-format=json
```
- **exit code 0**, 01:45:50Z → 01:47:36Z (**106 s**)
- `build-finished.success = True`
- 704 `compiler-artifact` events, **`fresh: false` for all 704** — nothing was reused
- **errors: 0**, warnings: **1**
- members with artifacts: **78 / 79** (same `wave-3lane-tests` caveat)
- 1.0 GB written to the fresh target dir

**This is the strongest statement this audit can make:** with a completely empty target directory,
all 79 workspace members resolve, type-check and pass `cargo check` for their `lib` and `bin` targets,
with zero errors.

### 3.4 Run (c) — cold control, `SDKROOT` unset

```bash
env -u SDKROOT cargo check --workspace --offline \
  --target-dir /Users/kooshapari/.jcode/scratch/phenoshared-control-target
```
- **exit code 0**, 1 m 54 s (114 s). Same success, without any environment workaround.

This control matters because of Section 6: it establishes that the workspace's cold check does **not**
depend on the `SDKROOT` workaround, i.e. rustc's own link steps are not hitting the linker defect in
this configuration.

### 3.5 Run (d) — `--all-targets` (tests, benches, examples)

```bash
cargo check --workspace --all-targets --offline \
  --target-dir /Users/kooshapari/.jcode/scratch/phenoshared-cold-target \
  --message-format=json
```
- **exit code 0**, 30.9 s (incremental on top of run (b))
- `build-finished.success = True`
- **members covered: 79 / 79** — including `crates/wave-3lane-tests`
- target kinds exercised: `lib` 136, `test` **70**, `bin` 38, `bench` **11**, `example` 2, `cdylib` 4, `rlib` 2, `custom-build` 1
- **errors: 0**, **warnings: 46**

So the workspace's **test, bench and example code also compiles** — 70 test targets, 11 benches.

Warning breakdown (46 total, all warnings — no errors):

| Code | Count |
| --- | --- |
| `deprecated` | 18 |
| `unused_imports` | 14 |
| `dead_code` | 7 |
| `unexpected_cfgs` | 3 |
| `unused_must_use` | 3 |
| `dropping_references` | 1 |

Cargo also emitted a future-incompatibility note (not an error):

```
warning: the following packages contain code that will be rejected by a future version of Rust:
  block v0.1.6, proc-macro-error2 v2.0.1
```

### 3.6 Verdict for the workspace

> **79 / 79 workspace members "compile" in the `cargo check` sense: 79/79 for `lib`+`bin`, and 79/79
> including test/bench/example targets, from a cold target directory, zero errors.**
>
> They do **not** "build" in the full sense — no binary was linked and no test was *run*. See §7 for
> exactly what "compiles" excludes here.

Members that **failed to compile: 0**.

---

## 4. Failing crates observed

### 4.1 Workspace members

**None.** Zero workspace members failed.

### 4.2 Non-member crates with real compile errors

6 manifest entries, covering **4 distinct crates**:

| Crate | Error | Literal text |
| --- | --- | --- |
| `iac/oci-lottery` | E0432 ×2 | `error[E0432]: unresolved import \`oci_helpers\`` |
| `iac/oci-post-acquire` | E0432 ×3 | `error[E0432]: unresolved import \`oci_helpers\`` |
| `iac` (workspace, same root cause) | exit 101 | `error: could not compile \`oci-lottery\` (bin "oci-lottery") due to 2 previous errors` |
| `crates/argis-extensions/argis-monitor` | E0432, E0624, E0271 | `error[E0432]: unresolved import \`opentelemetry_sdk::trace::TracerProvider\`` / `error[E0624]: associated function \`new\` is private` / `error[E0271]: type mismatch resolving \`<Vec<KeyValue> as IntoIterator>::Item == KeyValue\`` |
| `crates/hexa-kit/agileplus-agents/crates/agileplus-agent-service` | E0308 | `error[E0308]: mismatched types` → `error: could not compile \`agileplus-agent-service\` (build script) due to 1 previous error` |

Full literal output for the cleanest reproduction:

```bash
cargo check --manifest-path iac/Cargo.toml --offline     # exit 101
```
```
error[E0432]: unresolved import `oci_helpers`
 --> oci-lottery/src/config.rs:1:5
  |
1 | use oci_helpers::home_or_fallback;
  |     ^^^^^^^^^^^ use of unresolved module or unlinked crate `oci_helpers`
  |
  = help: if you wanted to use a crate named `oci_helpers`, use `cargo add oci_helpers` to add it to your `Cargo.toml`

error[E0432]: unresolved import `oci_helpers`
 --> oci-lottery/src/hooks.rs:6:5
  |
6 | use oci_helpers::which_on_path;
  |     ^^^^^^^^^^^ use of unresolved module or unlinked crate `oci_helpers`
...
error: could not compile `oci-lottery` (bin "oci-lottery") due to 2 previous errors
```

`oci_helpers` is referenced as a crate but is not declared in `oci-lottery`'s `[dependencies]`. That
is a missing-dependency defect, not a toolchain issue. Three crates depend on it, so this single
omission fails the whole `iac/` workspace.

---

## 5. Measurement 2 — the 515 non-member manifests

`cargo check --workspace` never touches these. They were measured in two stages: first "can Cargo even
read the manifest", then "does it compile".

### 5.1 Stage 1 — loadability (all 515 manifests)

```bash
cargo metadata --no-deps --offline --manifest-path <each non-member manifest>
```

| Outcome | Count |
| --- | --- |
| **exit 0 — manifest loads** | **75** |
| **non-zero — manifest does not load** | **440** |

**This is the single most important non-member finding: 85 % of non-member manifests cannot be
handed to Cargo at all.** Compilation was never attempted for them, and they must not be counted as
"failing to compile".

Top error causes among the 440 (literal text, first error line):

| Cause | Count | Literal error |
| --- | --- | --- |
| Package not attached to any workspace | **292** | `error: current package believes it's in a workspace when it's not:` |
| `workspace = true` inheritance with no resolvable root | **109** | `error: failed to parse manifest at \`<path>\`` → `Caused by: error inheriting \`<dep>\` from workspace root manifest's \`workspace.dependencies.<dep>\`` |
| Nested workspace member unloadable | **33** | `error: failed to load manifest for workspace member \`<path>\`` |
| Other | 6 | `error: duplicate key`; `error: failed searching for potential workspace` |

Representative literal errors:

```
error: current package believes it's in a workspace when it's not:
current:   <repo>/crates/datakit/Cargo.toml
workspace: <repo>/Cargo.toml

this may be fixable by adding `crates/datakit` to the `workspace.members` array of the manifest located at: <repo>/Cargo.toml
Alternatively, to keep it out of the workspace, add the package to the `workspace.exclude` array, or add an empty `[workspace]` table to the package's manifest.
```

```
error: failed to load manifest for workspace member `<repo>/crates/hexa-kit/crates/phenotype-core`
referenced by workspace at `<repo>/crates/hexa-kit/Cargo.toml`

Caused by:
  failed to parse manifest at `<repo>/crates/hexa-kit/crates/phenotype-core/Cargo.toml`

Caused by:
  dependency (phenotype-health) specified without providing a local path, Git repository, version, or workspace dependency to use
```

The 109 `workspace = true` failures are dominated by missing `[workspace.dependencies]`/`[workspace.package]`
keys at the resolved root:

| Missing inherited key | Crates |
| --- | --- |
| `workspace.package.keywords` | 17 |
| `workspace.dependencies.sha2` | 10 |
| `workspace.package.description` | 8 |
| `workspace.dependencies.serde_yaml` | 7 |
| `no targets specified in the manifest` | 6 |
| `workspace.dependencies.focus-connectors` | 5 |
| `workspace.dependencies.secrecy` | 5 |
| `workspace.dependencies.hex` | 5 |
| `workspace.dependencies.walkdir` | 4 |
| `workspace.dependencies.dirs` | 4 |

These are extensions that were written against a *different* workspace root and were left behind when
the package was moved into this repo. They are structurally orphaned, not broken code.

### 5.2 Stage 2 — compilation (the 75 loadable manifests)

```bash
cargo check --offline --manifest-path <each loadable manifest> \
  --target-dir /Users/kooshapari/.jcode/scratch/nm-target        # shared target dir, per-call timeout 150 s
```

- Global deadline: 12 minutes. **Not hit** — every manifest was attempted (no `NOT_ATTEMPTED`, no `TIMEOUT`).
- Wall time: 5 m 25 s (325 s).

| Outcome | Count |
| --- | --- |
| **exit 0 — compiles** | **40** |
| **non-zero — does not compile** | **35** |
| — of which *blocked only by unavailable dependencies* (not a compile result) | **29** |
| — of which *real compile errors* | **6** (4 distinct crates) |

> Because 1 of the 75 loadable manifests is the repo root workspace manifest itself, the honest
> package-level reading is: **of 74 loadable non-member packages, 39 compile and 35 do not.**

The 29 offline-blocked failures are **NOT ATTEMPTED**, not failures. They failed before compiling
anything:

```
error: failed to download `async-nats v0.47.0`
Caused by:
  attempting to make an HTTP request, but --offline was specified
```
```
error: no matching package named `crc32c` found
```
```
error: checksum for `serde v1.0.217` changed between lock files
```

Distinct unavailable dependency specs (11): `async-nats v0.47.0`, `crc32c`, `fancy-regex v0.13.0`,
`hashlink v0.8.4`, `octocrab v0.42.1`, `serde v1.0.217`, `sysinfo v0.32.1`, `toml v0.7.8`,
`tonic-health v0.12.3`, `ureq v3.4.1`, `uuid v1.23.4`.

Whether these would compile with network access is **unmeasured**.

### 5.3 Non-member verdict

> **Of 514 non-member package manifests: 440 cannot be loaded by Cargo at all, 39 compile, 6 fail with
> real compile errors, and 29 are unmeasured because their dependencies are not in the local registry
> cache.**
>
> The arithmetic closes exactly: **440 + 39 + 6 + 29 = 514.** (The 6 failing manifest entries are 4
> distinct crates; three `iac/` entries share one root cause, and two `hexa-kit` entries share another.)

---

## 6. Toolchain anomaly found during this audit (NOT a repo defect)

This is a real, reproducible defect of the **host**, and it is the main reason `cargo check` results
must not be equated with "builds".

### 6.1 Standalone `cc` cannot link

```bash
printf 'int main(void){return 0;}\n' | cc -x c - -o /tmp/probe
```
- **exit code 1**, reproduced 3× (01:39Z, 01:45Z, 01:52Z)
- no output binary produced

Literal error:

```
ld: tapi error: malformed file
/Library/Developer/CommandLineTools/SDKs/MacOSX27.0.sdk/usr/lib/libSystem.B.tbd:4:20: error: unknown architecture
                   arm64e.x1-macos, arm64e.x1-maccatalyst ]
                   ^~~~~~~~~~~~~~~
 in '/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/lib/libSystem.tbd'
clang: error: linker command failed with exit code 1 (use -v to see invocation)
```

Linking a dylib fails identically (`exit 1`). The default SDK that `cc` resolves —
`/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk` → `MacOSX27.0.sdk` — contains `.tbd` stubs
declaring architecture `arm64e.x1-macos` / `arm64e.x1-maccatalyst`, which the installed linker
(`ld-1221.4`, shipped with Xcode 26.0) cannot parse.

**Confirmed workaround:**

```bash
printf 'int main(void){return 0;}\n' | cc -x c - \
  -isysroot /Applications/Xcode.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX.sdk \
  -o /tmp/probe
# exit code 0
```

Also note the split-brain toolchain configuration: `xcode-select -p` reports
`/Applications/Xcode.app/Contents/Developer` (Xcode 26.0), while `xcrun --show-sdk-path` reports the
Command Line Tools SDK (`/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk`). The CLT SDK directory
was written 2026-09-17, one day before this audit.

**Impact:** any build on this host that drives `cc`/`clang` directly — C, C++, Objective-C, or any
`build.rs` invoking the C compiler, or `cargo build` of a binary from a cold target dir — can fail for
a reason that has nothing to do with this repository. This is a **false-negative generator**. Do not
interpret a `cc: unknown architecture` error as a repo bug.

### 6.2 Transient `cc` link failures — OBSERVED BUT NOT REPRODUCED

Between 01:39Z and 01:41Z, two consecutive attempts to `cargo check` five non-member crates produced:

```
error: linking with `cc` failed: exit status: 1
...
error: could not compile `serde_json` (build script) due to 1 previous error
```

with the same `tapi error: malformed file ... unknown architecture` body. The affected crates were
`crates/forge_daemon`, `crates/fabric-gui/src-tauri`, `crates/fabric-frame-transport/fuzz`,
`infrakit/`, `iac/`.

**Under identical cold conditions later, all five succeeded:**

| Crate | Cold retry (fresh `--target-dir`, `SDKROOT` unset) |
| --- | --- |
| `crates/forge_daemon` | exit 0, 16.0 s |
| `crates/fabric-frame-transport/fuzz` | exit 0, 14.5 s |
| `crates/fabric-gui/src-tauri` | exit 0, 68.3 s |
| `infrakit/` | exit 0, 12.7 s |
| `iac/` | exit 101 — **but with real E0432 errors, i.e. it now compiles past the link stage** |

**Cause: UNRESOLVED.** The persistent standalone-`cc` defect in 6.1 is real and reproducible, but it
does not by itself explain these cases, because rustc-driven cold links succeed. Both observations are
recorded as facts: the failures were seen twice and were not reproducible afterwards. Nothing in this
document depends on either interpretation — all workspace results are confirmed by cold runs that
succeeded.

---

## 7. What this audit did NOT measure

Stated explicitly, so nobody converts one of these into a stronger claim:

1. **`cargo build` / linking of any workspace binary — NOT ATTEMPTED.** Only `cargo check` was run, and
   `cargo check` does not link. Given the linker defect in §6.1, **the number of workspace members
   that produce a working executable is unmeasured and is the single biggest remaining unknown.**
2. **Test execution — NOT ATTEMPTED.** 70 test targets *type-check*; **zero tests were run**. No claim
   about test pass/fail rates is made anywhere in this document.
3. **A truly cold build from a pristine `target/` on a healthy toolchain — NOT ATTEMPTED.** `cargo clean`
   was prohibited. The cold runs used a separate `--target-dir`, which is equivalent for Cargo's own
   resolution but does not clear the C compiler/`sccache` layer (sccache is installed but not wired in).
4. **437 of 515 non-member manifests — NOT ATTEMPTED** (440 unloadable, minus 3 that are nested
   workspace roots). They cannot be measured until their manifest/workspace wiring is fixed.
5. **29 non-member manifests — NOT ATTEMPTED** because their dependencies are absent from the local
   registry cache and `--offline` was required. A network-enabled run may change this.
6. **`Cargo.lock` was never rewritten**; `--locked` was never passed, and no `cargo update`, `cargo fix`
   or `cargo clean` was run. The lock file is untouched.
7. **Non-Rust components** (Python, TypeScript, Go, Mojo, shell, IaC) — **NOT ATTEMPTED**, out of scope.
8. **Doctests, `cargo clippy`, `cargo fmt --check`, `cargo test --no-run`** — **NOT ATTEMPTED**.
9. **Whether the 8.7 GB pre-existing `target/` masks staleness** — unmeasured. Its contents were not
   inspected beyond artifact freshness flags.
10. **macOS/Windows targets, `--all-features`, `--release` profile** — **NOT ATTEMPTED.**

### Summary table of the four states

| State | Count | Definition used here |
| --- | --- | --- |
| **Compiles** | 79 workspace members; 39 non-member packages | `cargo check` exit 0 |
| **Compiles with warnings** | 46 warnings across the workspace, 0 errors | `cargo check` exit 0 with warnings only |
| **Fails** | 0 workspace members; **4 distinct non-member crates** | `cargo check` exit non-zero with a rustc error |
| **Not attempted** | 440 unloadable + 29 dep-blocked non-member manifests; all linking, all test execution | Cargo could not start, or was prohibited |

---

## 8. Commands used (verbatim)

```bash
# scope
cargo metadata --no-deps --format-version 1
cargo metadata --format-version 1 --offline
find . -name Cargo.toml -not -path "./target/*"

# workspace compilation — warm
cargo check --workspace --offline --message-format=json

# workspace compilation — COLD (authoritative)
cargo check --workspace --offline \
  --target-dir /Users/kooshapari/.jcode/scratch/phenoshared-cold-target \
  --message-format=json

# workspace cold control (no SDKROOT)
env -u SDKROOT cargo check --workspace --offline \
  --target-dir /Users/kooshapari/.jcode/scratch/phenoshared-control-target

# all-targets
cargo check --workspace --all-targets --offline \
  --target-dir /Users/kooshapari/.jcode/scratch/phenoshared-cold-target \
  --message-format=json

# non-members — loadability (all 515)
cargo metadata --no-deps --offline --manifest-path <manifest>

# non-members — compilation (the 75 that load)
cargo check --offline --manifest-path <manifest> \
  --target-dir /Users/kooshapari/.jcode/scratch/nm-target

# toolchain probe
printf 'int main(void){return 0;}\n' | cc -x c - -o <out>     # exit 1
printf 'int main(void){return 0;}\n' | cc -x c - -isysroot <Xcode MacOSX.sdk> -o <out>  # exit 0
```

**No source file, `Cargo.toml`, or lockfile was modified. No `cargo clean`, `cargo update`, `cargo fix`,
`git add`, or `git commit` was run.** The only file created inside the repository is this document.
Measurement artifacts (target dirs, JSON logs) live under `/Users/kooshapari/.jcode/scratch/`
(≈ 3 GB: `phenoshared-cold-target` 1.0 G, `phenoshared-control-target` 1.0 G, `nm-target`,
`t-tauri` 809 M, `t-fuzz` 109 M, `infrakit-cold-target` 91 M, `t-forge_daemon` 72 M) and can be
deleted freely.

---

## 9. Appendix — the 40 non-member manifests that compile

```
Cargo.toml                                                        (repo root workspace, not a package)
agileplus-agents/crates/agileplus-agent-dispatch/Cargo.toml
agileplus-agents/crates/agileplus-agent-review/Cargo.toml
audits/org-audit-snapshots/audits/2026-04-24/aggregator/Cargo.toml
audits/org-audits/2026-07/zz-archive-archive2/wt-audit-rebuild-v38/audits/2026-04-24/aggregator/Cargo.toml
audits/org-audits/2026-07/zz-archive-archive2/wt-feature-state-table-org/audits/2026-04-24/aggregator/Cargo.toml
crates/agile-plus/agileplus-agents/crates/agileplus-agent-dispatch/Cargo.toml
crates/agile-plus/agileplus-agents/crates/agileplus-agent-review/Cargo.toml
crates/agile-plus/crates/agileplus-domain/fuzz/Cargo.toml
crates/agile-plus/crates/agileplus-mcp/Cargo.toml
crates/agile-plus/crates/agileplus-subcmds/Cargo.toml
crates/agile-plus/rust/Cargo.toml
crates/apisync/fuzz/Cargo.toml
crates/argis-extensions/pheno-port-adapter/Cargo.toml
crates/argis-extensions/pheno-port-adapter/fuzz/Cargo.toml
crates/cli-wrapper/Cargo.toml
crates/fabric-frame-transport/fuzz/Cargo.toml
crates/fabric-gui/src-tauri/Cargo.toml
crates/forge_daemon/Cargo.toml
crates/hexa-kit/agileplus-agents/crates/agileplus-agent-dispatch/Cargo.toml
crates/hexa-kit/agileplus-agents/crates/agileplus-agent-review/Cargo.toml
crates/hexa-kit/rust/Cargo.toml
crates/pheno-proc-runtime/pheno-proc-dedup/fuzz/Cargo.toml
crates/pheno-proc-runtime/pheno-proc-queue/fuzz/Cargo.toml
crates/playcua-app/Cargo.toml
crates/playcua-bare/Cargo.toml
crates/policystack/wrappers/rust/Cargo.toml
crates/port-input/Cargo.toml
crates/port-renderer/Cargo.toml
crates/port-window-mgr/Cargo.toml
iac/tailscale/tailscale-keygen/Cargo.toml
infrakit/Cargo.toml
infrakit/crates/phenotype-cache-adapter/Cargo.toml
infrakit/crates/phenotype-contracts/Cargo.toml
infrakit/crates/phenotype-cost-core/Cargo.toml
infrakit/crates/phenotype-event-sourcing/Cargo.toml
infrakit/crates/phenotype-observability/Cargo.toml
infrakit/crates/phenotype-policy-engine/Cargo.toml
infrakit/crates/phenotype-state-machine/Cargo.toml
tools/iac-plan-viewer/Cargo.toml
```

## 10. Recommended next measurements (not done here)

1. **`cargo build --workspace` on a host with a working SDK** — this is the only way to learn how many
   members link. Highest-value unknown.
2. Repair the `cc`/SDK mismatch (§6.1) — either reinstall matching Command Line Tools or pin
   `SDKROOT` to the Xcode 26.0 SDK. Until then, linking results on this host are untrustworthy.
3. Decide the fate of the 292 + 109 + 33 unloadable manifests: either add them back to
   `workspace.members`/`exclude`, or add an empty `[workspace]` table so they are independently
   buildable and measurable.
4. Re-run the 29 dependency-blocked manifests with network access.
5. Run `cargo test --workspace --no-run` to extend coverage from "type-checks" to "test binaries link".
