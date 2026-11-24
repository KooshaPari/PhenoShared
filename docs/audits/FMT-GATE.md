# FMT-GATE: rustfmt / CI formatting gate measurement

**Date:** 2026-09-18
**Repo:** `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared`
**Branch:** `main`
**Type:** Measurement + analysis. **No repository files were reformatted, added, or committed.**
**Output:** this file is the only artifact created.

---

## 0a. Independent verification (added by the coordinator, 2026-09-19)

Every number in §0 was re-measured from scratch before this audit was accepted.
All of it reproduced:

| Claim in this audit | Independent result |
|---|---|
| stable `cargo fmt --all -- --check` exits **1** | **confirmed** (exit 1) |
| **288** distinct files under stable | **confirmed** (288 distinct paths) |
| **456** distinct files under nightly | **confirmed** (456) |
| **168** nightly-only, **0** stable-only | **confirmed** (nightly∖stable = 168, stable∖nightly = 0) |
| **69** files in `crates/phinbox` | **confirmed** (69 of 288, from 83 tracked `.rs` = 83%) |
| **19** options are nightly-only | **confirmed** — enumerating the option names stable refuses to set yields exactly 19: `brace_style, comment_width, condense_wildcard_suffixes, control_brace_style, empty_item_single_line, fn_single_line, format_macro_matchers, format_strings, group_imports, hex_literal_case, imports_granularity, normalize_comments, normalize_doc_attributes, struct_lit_single_line, trailing_comma, trailing_semicolon, unstable_features, where_single_line, wrap_comments` |
| rustfmt default toolchain on this host is **nightly** | **confirmed** (`rustup default` → `nightly-aarch64-apple-darwin`) |
| the only nightly rustfmt CI site is **dormant** | **confirmed** — `.github/workflows/perf-core-ci.yml` gates on `perf-core/**`, and `perf-core/` has **0** tracked files |

**One correction this audit prompted elsewhere.** A figure previously recorded
in `docs/plan/LONG-TERM-WBS.md:24` — "wants **334** files changed in one crate
alone" — was wrong twice over: 334 was a **hunk** count (i.e. `Diff in` lines),
not a distinct-file count, and it was never scoped to one crate. The true values
are **288** distinct files repo-wide and **69** in `phinbox`. The WBS has been
corrected. The error is worth recording because it is the same hunk-vs-file
mistake in both directions, and it is easy to make with this output format.

**Note on the hunk count.** This audit reports **1393** hunks; an independent
count yields **1394**. All 1394 `Diff in` lines are well-formed
(`Diff in <path>:<line>:`), so 1394 appears to be the exact figure. The
difference is immaterial to every conclusion here and is noted only so the
numbers agree on re-run.

## 0. Summary of measured facts

| Fact | Value |
| --- | --- |
| `cargo fmt --all -- --check` exit code (stable) | **1** |
| Distinct files stable rustfmt wants to change | **288** |
| Diff hunks across those files | **1393** |
| Of those, under `crates/phinbox/` | **69** (of 83 tracked `.rs`) |
| Same command under **nightly** | exit **1**, **456** files, 2184 hunks |
| Stable file set vs nightly file set | 288 ⊂ 456; **168 nightly-only**, **0 stable-only** |
| `rustfmt.toml` options rejected by stable | **19 of 29** |
| Warnings emitted by stable per full run | **3344** (`19 × 176` invocations) |
| Effective effect of `rustfmt.toml` on **stable** | **none — byte-identical to no-config** |

---

## 1. rustfmt version actually installed and used in CI

### 1.1 Local

```
$ rustfmt --version
rustfmt 1.9.0-stable (8bab26f4f6 2026-07-14)

$ cargo --version
cargo 1.97.1 (c980f4866 2026-06-30)

$ rustup toolchain list
stable-aarch64-apple-darwin (active)
nightly-aarch64-apple-darwin (default)      <-- note: rustup DEFAULT is nightly
nightly-2026-06-23-aarch64-apple-darwin
nightly-2026-07-31-aarch64-apple-darwin
1.88 / 1.94.0 / 1.95.0 / 1.96.0 / 1.97 / 1.98 / 1.98.0 / 1.98.1-aarch64-apple-darwin

$ rustup show
active toolchain
----------------
name: stable-aarch64-apple-darwin
active because: overridden by '.../PhenoShared/rust-toolchain.toml'
```

`rust-toolchain.toml` (whole file, 3 lines):

```toml
[toolchain]
channel = "stable"
components = ["rustfmt", "clippy"]
```

**Trap worth recording:** the rustup **default** toolchain on this host is `nightly`, while the
repo is pinned to `stable` only via `rust-toolchain.toml`. Any bare `rustfmt` invocation from a
directory **outside** this repo therefore runs **nightly**, silently. Verified directly:

```
# /Users/.../repos/PhenoShared   -> rustfmt 1.9.0-stable (8bab26f4f6 2026-07-14)
# ~/.jcode/scratch/fmtprobe      -> rustfmt 1.9.0-nightly (d0babd8b6b 2026-07-15)
```

This invalidated a first attempt at §3; see §3.2.

### 1.2 CI formatting jobs (every occurrence in `.github/workflows/`)

There are **four** formatting sites, in three workflows.

**A. `.github/workflows/ci.yml` — ADVISORY, cannot fail the build**

```
84:     runs-on: ubuntu-latest
85:     continue-on-error: true
88:       - uses: dtolnay/rust-toolchain@stable
90:       - name: cargo fmt --check
91:         run: |
92:           cargo fmt --all -- --check 2>&1 || echo "::warning::cargo fmt issues (advisory)"
```

Toolchain: **stable**. Gate strength: **advisory** — the `|| echo ::warning::` swallows the
non-zero exit, and the job additionally sets `continue-on-error: true` (line 85). This job reports
green regardless of formatting.

**B. `.github/workflows/quality-gate.yml` — HARD gate**

```
55:       - uses: actions/checkout@v4
56:       - uses: dtolnay/rust-toolchain@stable
57:         with:
58:           toolchain: stable
59:           components: rustfmt, clippy
67:       - run: cargo fmt --check
```

Toolchain: **stable**. Gate strength: **hard** — no `continue-on-error` anywhere in this workflow
(checked), and line 67 is a plain `run:` with no `||` fallback. This is the job that is currently
red. Guarded by `if: needs.changes.outputs.rust == 'true'` (line 52).

**C. `.github/workflows/iac-rust.yml` — HARD gate, pinned action SHA**

```
40:         uses: dtolnay/rust-toolchain@29eef336d9b2848a0b548edc03f92a220660cdb8
42:           components: clippy, rustfmt
49:       - name: cargo fmt --check
50:         run: cargo fmt --manifest-path iac/Cargo.toml --all -- --check
```

and again for `iac/landing-bootstrap`:

```
69:         uses: dtolnay/rust-toolchain@29eef336d9b2848a0b548edc03f92a220660cdb8
71:           components: clippy, rustfmt
78:       - name: cargo fmt --check
79:         run: cargo fmt --manifest-path iac/landing-bootstrap/Cargo.toml --all -- --check
```

Toolchain: **stable** (SHA-pinned `dtolnay/rust-toolchain`, stable). Hard gate.

**D. `.github/workflows/perf-core-ci.yml` — NIGHTLY, but dormant**

```
31:         uses: dtolnay/rust-toolchain@nightly
33:           components: rustfmt, clippy
225:       - name: rustfmt changed Rust files
227:         working-directory: perf-core
230:             rustfmt --edition 2021 --check "../$file"
```

Toolchain: **nightly**. This is the only nightly-rustfmt site. It is triggered only on
`paths: ["perf-core/**"]` (lines 6-11), and **`perf-core/` does not exist in this repo**
(`git ls-files | grep -c '^perf-core/'` → `0`). The job is dormant; it also has
`working-directory: perf-core` (line 227) and no `continue-on-error`, so if it ever triggered it
would fail on a missing directory. Flagged as a separate finding, out of scope here.

**Conclusion for §1:** CI's *binding* rustfmt is **stable**, and it is only genuinely binding in
`quality-gate.yml` and `iac-rust.yml`. The stated premise that "CI runs stable rustfmt" is
**confirmed**, and only one dormant job uses nightly.

---

## 2. `cargo fmt --check` — real result

### 2.1 Primary command

```
$ cd /Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared
$ cargo fmt --all -- --check
EXIT=1
```

Measured output volumes: **16680** stdout lines (the diffs), **3345** stderr lines (warnings).

Method for the file count: strip ANSI escapes, then extract every `Diff in <path>:<line>:` header
and de-duplicate the path.

```
$ sed -E 's/\x1b\[[0-9;]*m//g' fmtcheck.out | grep -oE '^Diff in [^:]+' \
    | sed 's/^Diff in //' | sort -u | wc -l
288
```

- **Distinct files: 288**
- **Total hunks: 1393**
- **Under `crates/phinbox/`: 69** (83 `.rs` files are tracked there, so **83%** of the crate drifts)

Largest contributing areas (top 10), by distinct files:

| Area | Files |
| --- | --- |
| `crates/phinbox` | 69 |
| `crates/fabric-graph` | 30 |
| `crates/fabric-cli` | 20 |
| `crates/fabric-daemon` | 19 |
| `crates/fabric-capability` | 13 |
| `crates/phenotype-gfx` | 9 |
| `crates/fabric-web` | 9 |
| `crates/fabric-capture` | 8 |
| `crates/pheno-tracing` | 7 |
| `crates/fabric-persist` | 7 |

### 2.2 The other CI commands

| Command | Source | Exit | Distinct files |
| --- | --- | --- | --- |
| `cargo fmt --all -- --check` | `ci.yml:92` | 1 | 288 |
| `cargo fmt --check` | `quality-gate.yml:67` | **1** | 288 |
| `cargo fmt --manifest-path iac/Cargo.toml --all -- --check` | `iac-rust.yml:50` | **1** | 5 |
| `cargo fmt --manifest-path iac/landing-bootstrap/Cargo.toml --all -- --check` | `iac-rust.yml:79` | **1** | 1 |

All four exit **1**. `cargo fmt --check` at the workspace root resolves to the same 288-file set as
`--all --check`, so the two spellings are equivalent here.

### 2.3 Nightly comparison (the (a)-vs-(b) discriminator)

```
$ cargo +nightly fmt --all -- --check
EXIT=1
```

| | stable | nightly |
| --- | --- | --- |
| exit code | 1 | 1 |
| distinct files | **288** | **456** |
| hunks | 1393 | 2184 |
| `crates/phinbox` files | 69 / 83 | 81 / 83 |

Set relationship: `comm` over the two sorted file lists gives **288 in both, 0 stable-only,
168 nightly-only**. The stable set is a strict subset of the nightly set.

**This is the decisive measurement:** pointing CI at nightly makes the gate fail on **more** files
(456 vs 288), not fewer. Option (a) does not move the gate toward green.

---

## 3. `rustfmt.toml` option-by-option stability

### 3.1 The config

`rustfmt.toml` (29 active options; the commented-out `ignore` block at lines 43-47 is inert).

### 3.2 Method, and the false start

**Attempted method 1 (rejected).** Probe each option on a scratch copy and look for stable
rustfmt's warning `Warning: can't set \`X\`, unstable features are only available in nightly
channel.` This returned "accepted" for **all 29 options, including the control options
`skip_children` and `error_on_unformatted`**, which are unambiguously nightly-only. **The method
failed its own control**, so the result was discarded rather than reported.

Root cause: the probe ran in `~/.jcode/scratch/fmtprobe/`, which has no `rust-toolchain.toml`, so
bare `rustfmt` resolved to the rustup **default** toolchain — **nightly** (§1.1). Nightly accepts
and applies all of these options, so no warnings appeared and the options visibly took effect.
This is a genuine trap: a scratch-directory probe of this repo's rustfmt config silently measures
the wrong toolchain.

**Method used (validated).** Pin the toolchain explicitly with `rustup run <tc> rustfmt`, one
option per scratch config:
- for each option, write a scratch `rustfmt.toml` containing **only that option**;
- run `rustup run stable rustfmt --check --edition 2021 sample.rs`, capture stderr;
- classify as NIGHTLY-ONLY iff stderr matches `unstable features are only available`;
- **controls**: `skip_children` and `error_on_unformatted` (both known nightly-only) must classify
  as NIGHTLY-ONLY on stable and accepted on nightly.

**Control outcome (method validated):**

```
toolchain=stable
NIGHTLY_ONLY   ctl_skip_children
NIGHTLY_ONLY   ctl_error_on_unformatted
toolchain=nightly
accepted       ctl_skip_children
accepted       ctl_error_on_unformatted
```

**Independent cross-check.** The 19 options this probe flags on stable exactly equal the 19
distinct option names in the 3344 warning lines produced by the *real* `cargo fmt --all -- --check`
run of §2. Two independent methods, identical 19-option set.

### 3.3 Result

**10 options accepted on stable** — and all 10 sit at rustfmt's default values:

| Option | Repo value | rustfmt default | Effect on stable |
| --- | --- | --- | --- |
| `edition` | `"2021"` | (crate edition) | matches `Cargo.toml:86` `edition = "2021"` |
| `max_width` | `100` | `100` | no-op |
| `hard_tabs` | `false` | `false` | no-op |
| `tab_spaces` | `4` | `4` | no-op |
| `newline_style` | `"Unix"` | `"Auto"` | **differs**, but `Auto` resolves to Unix on Linux/macOS runners → no-op in practice |
| `use_small_heuristics` | `"Default"` | `"Default"` | no-op |
| `reorder_imports` | `true` | `true` | no-op |
| `match_block_trailing_comma` | `false` | `false` | no-op |
| `use_try_shorthand` | `false` | `false` | no-op |
| `force_explicit_abi` | `true` | `true` | no-op |

Defaults read from `rustup run stable rustfmt --print-config default`.

**Behavioral consequence, verified directly.** Formatting one file three ways:

```
A: stable, no config
B: stable, repo rustfmt.toml
C: nightly, repo rustfmt.toml

A vs B: IDENTICAL   -> rustfmt.toml is INERT on stable
A vs C: DIFFER      -> the nightly-only options do change output, on nightly
```

So **on stable, the entire `rustfmt.toml` currently has no effect**: stable formats the repo with
pure rustfmt defaults. The config's intent is being silently discarded. This is a stronger (and
simpler) statement than "CI runs a different formatter": there is exactly one effective style in
play in CI today, and it is *default* rustfmt, not the configured style.

**19 options rejected on stable** (all confirmed by both the probe and the real run):

`group_imports`, `imports_granularity`, `format_strings`, `format_macro_matchers`,
`normalize_comments`, `normalize_doc_attributes`, `wrap_comments`, `comment_width`,
`trailing_comma`, `trailing_semicolon`, `brace_style`, `control_brace_style`,
`empty_item_single_line`, `fn_single_line`, `where_single_line`, `struct_lit_single_line`,
`hex_literal_case`, `condense_wildcard_suffixes`, `unstable_features`

---

## 4. Option (b): what would be dropped, and the formatting consequence

Of the 19 rejected options, **9 are already set to their rustfmt default value**, so dropping them
costs *nothing* even on nightly. The remaining **10 are genuine divergences** and represent the
real style loss.

### 4.1 Dropped with zero consequence (value already equals the default)

| Option | Repo value | Default |
| --- | --- | --- |
| `trailing_comma` | `"Vertical"` | `"Vertical"` |
| `trailing_semicolon` | `true` | `true` |
| `brace_style` | `"SameLineWhere"` | `"SameLineWhere"` |
| `control_brace_style` | `"AlwaysSameLine"` | `"AlwaysSameLine"` |
| `empty_item_single_line` | `true` | `true` |
| `fn_single_line` | `false` | `false` |
| `where_single_line` | `false` | `false` |
| `condense_wildcard_suffixes` | `false` | `false` |
| `unstable_features` | `false` | `false` |

These are noise: they were written to make intent explicit, but they restate defaults.

### 4.2 Dropped with a real consequence (10 options)

| Option | Repo value | Default | Formatting consequence of dropping |
| --- | --- | --- | --- |
| `imports_granularity` | `"Crate"` | `"Preserve"` | `use a::X;` + `use a::Y;` no longer merge into `use a::{X, Y};` — more `use` lines per file |
| `group_imports` | `"StdExternalCrate"` | `"Preserve"` | std / external / crate import groups no longer separated by blank lines |
| `format_strings` | `true` | `false` | long string literals are no longer wrapped with `\` continuations; long string lines stay long |
| `wrap_comments` + `comment_width` | `true` / `100` | `false` / `80` | over-long comments are no longer reflowed. Note `comment_width` **only applies when `wrap_comments` is on**, so these two are one feature |
| `hex_literal_case` | `"Lower"` | `"Preserve"` | hex digits keep their authored case instead of being lowercased |
| `normalize_comments` | `true` | `false` | `/* ... */` is no longer rewritten to `//` |
| `normalize_doc_attributes` | `true` | `false` | `#[doc = "..."]` is no longer rewritten to `///` |
| `format_macro_matchers` | `true` | `false` | macro matcher patterns (`$x:expr`) are no longer reformatted |
| `struct_lit_single_line` | `false` | `true` | struct literals that fit on one line **are** collapsed again |

Net: dropping to stable keeps ~10 real style choices and loses ~10.

**Critically — this does not make the gate pass.** Option (b) changes what the *config says*, not
whether the *code conforms*. Because the config is already inert on stable (§3.3), trimming it
changes stable output by **zero bytes** (aside from `newline_style`, which is a no-op on Unix).
`cargo fmt --all -- --check` would still exit 1 on the same **288** files.

---

## 5. Recommendation

**Recommendation: take option (b) — trim `rustfmt.toml` to stable options — and treat the
288-file bulk reformat as the real, separately-scoped work. Do not point CI at nightly.**

Evidence:

1. **Nightly makes the gate strictly worse.** 456 files vs 288, and the stable set is a strict
   subset (168 nightly-only files, 0 stable-only). Choosing (a) increases the backlog by 58%.
2. **Neither option fixes the gate.** Both exit 1. The failure is 288 unformatted files
   (1393 hunks), which is independent of the toolchain question.
3. **The config is already inert on stable** (A vs B byte-identical). Trimming to stable is
   therefore a *behavior-preserving* change on stable: it cannot regress CI formatting, and it
   removes 3344 warning lines from every run.
4. **Nightly rustfmt is unstable across nightlies.** Option (a) would require pinning an exact
   nightly date; `@nightly` is a moving target, and rustfmt's unstable style has no stability
   guarantee. The repo already pins its stable intent in `rust-toolchain.toml`.
5. **Dropping the 19 options costs less than it appears**: 9 of 19 are already defaults.

Concrete follow-on sequence (not performed here, out of scope):

- **(b-1)** Reduce `rustfmt.toml` to the 10 stable-accepted options, and delete the 9 no-op
  entries from §4.1. Outcome-neutral on stable; silences all warnings.
- **(b-2)** Decide separately whether to keep the 10 diverging options. Keeping them means the
  repo must commit to nightly rustfmt with a **pinned nightly date** and a bulk reformat to that
  style. This is the only path that preserves `imports_granularity`/`group_imports`/`wrap_comments`.
- **(b-3)** Run the bulk `cargo fmt --all` **once**, as its own reviewable commit, *after*
  resolving (b-2). 288 files / 1393 hunks is the blast radius on stable; 456 / 2184 on nightly.
- **(b-4)** Make the gate's strength intentional. `quality-gate.yml:67` and both `iac-rust.yml`
  sites are hard gates and are red today; `ci.yml:92` is advisory (and `continue-on-error: true`,
  line 85) and is green today. That inconsistency should be resolved deliberately rather than left
  to drift.
- **(b-5)** Independent of the above: `perf-core-ci.yml` can never trigger (path filter
  `perf-core/**` matches nothing, `perf-core/` does not exist) and would fail on
  `working-directory: perf-core` if it did. Dead CI should be removed or repointed.

---

## 6. Explicitly unverified / limits of this measurement

- **CI behavior was read from YAML, not observed.** I did not execute the GitHub Actions jobs. The
  advisory-vs-hard classification follows from `continue-on-error` and the `|| echo` fallback in
  the workflow text; no workflow run was inspected.
- **Per-option attribution is not measured.** I did **not** attribute the 168 nightly-only files
  to individual options. The §4.2 consequence column is rustfmt's *documented* semantics for each
  option, corroborated only for `imports_granularity` and `format_strings`, which I observed
  changing output in the nightly run (A vs C in §3.3). The other eight are documented but not
  individually isolated.
- **Version-pinned numbers.** 288 / 456 / 1393 / 2184 are for `rustfmt 1.9.0-stable (8bab26f4f6)`
  and `rustfmt 1.9.0-nightly (d0babd8b6b)` on this host. CI uses floating
  `dtolnay/rust-toolchain@stable` (and a SHA-pinned stable in `iac-rust.yml`), so a newer stable
  could shift the counts. They should be re-measured if the toolchain moves.
- **`crates/phinbox`: 69 of 83 is exact as measured**, but the 288 is "files `cargo fmt --all`
  reported", not "all `.rs` files in the tree". The repo tracks **5759** `.rs` files and the
  workspace declares **74** members, so files outside the workspace are not covered by `--all`.
  I did not verify member coverage exhaustively.
- **Nested `rustfmt.toml` files exist and were not fully exercised.** 12 `rustfmt.toml` /
  `.rustfmt.toml` files exist in the tree (e.g. `crates/apisync/`, `crates/hexa-kit/`,
  `crates/settly/`, `rust/`, `phenotype-governance/configs/rust/`). rustfmt resolves config
  nearest-first, so those directories can shadow the root file. I checked the 288 flagged files
  against those directories and **found 0 flagged files in any of them**, so shadowing does not
  affect the counts reported here — but the nested configs' own stability was not audited.
- **`edition` mismatch not resolved.** Root `Cargo.toml:86` is `edition = "2021"`, root
  `rustfmt.toml:12` is `edition = "2021"`, but `iac/Cargo.toml:19` is `edition = "2024"`.
  `iac/` has no local `rustfmt.toml`. What rustfmt actually uses for the edition-2024 iac crates
  was not measured.
- **No mutation was performed.** Per the task rules I did not run `cargo fmt` without `--check`,
  did not edit `rustfmt.toml`, `Cargo.toml`, or any workflow, and did not `git add`/`commit`.
  `git status` was clean of my changes; all scratch files live under
  `~/.jcode/scratch/fmt` and `~/.jcode/scratch/fmtprobe`.

---

## Appendix: evidence commands

```bash
# toolchain
rustfmt --version ; rustup toolchain list ; rustup show
# (trap) bare rustfmt outside the repo resolves to the rustup DEFAULT toolchain
cd ~/.jcode/scratch/fmtprobe && rustfmt --version   # -> 1.9.0-nightly

# primary measurement
cargo fmt --all -- --check ; echo "EXIT=$?"          # EXIT=1
# file count
sed -E 's/\x1b\[[0-9;]*m//g' fmtcheck.out | grep -oE '^Diff in [^:]+' \
  | sed 's/^Diff in //' | sort -u | wc -l               # 288
grep -c 'crates/phinbox' files.txt                      # 69

# nightly comparison
cargo +nightly fmt --all -- --check ; echo "EXIT=$?"  # EXIT=1, 456 files

# nightly-only option list, from the real run (authoritative)
grep -oE "Warning: can't set \`[^\`]+\`" fmtcheck.err | sort -u   # 19 options

# validated probe (pinned toolchain) + controls
rustup run stable rustfmt --check --edition 2021 sample.rs       # warns + ignores
rustup run nightly rustfmt --check --edition 2021 sample.rs      # accepts

# config-is-inert proof
rustup run stable rustfmt --emit stdout --edition 2021 sample.rs > A.out   # no config
cp <repo>/rustfmt.toml . ; rustup run stable rustfmt --emit stdout --edition 2021 sample.rs > B.out
diff A.out B.out    # identical
```

Artifacts (scratch, outside the repo): `~/.jcode/scratch/fmt/` (fmtcheck.out/.err/.exit,
files.txt, nightly.out/.err/.exit, nightly_files.txt) and
`~/.jcode/scratch/fmtprobe/` (sample.rs, probe.sh, probe2.sh, defaults.toml, inert/A.out B.out C.out).
