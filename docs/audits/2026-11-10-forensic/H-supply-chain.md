# Lane H — Supply Chain / Dependency Forensics

**Repo:** `/Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared`
**Date:** 2026-11-10
**Mode:** read-only. No git mutations, no `cargo update`, no writes inside the repo.
**Every number below was read from a file in this checkout.** Anything not read is marked `UNKNOWN`.

---

## 1. Headline dependency metrics

| Metric | Value | Source |
|---|---|---|
| `Cargo.lock` size | 499,324 bytes (~488 KiB) | `ls -la Cargo.lock` |
| Lockfile package blocks | **1,903** | `grep -c '^\[\[package\]\]' Cargo.lock` |
| `name =` lines in lockfile | 1,904 (one extra outside a `[[package]]` block) | `grep -c '^name = ' Cargo.lock` |
| Registry (crates.io) packages | **1,611** | awk over lockfile blocks with `source = "registry+..."` |
| Local / path packages (no `source`) | **293** | same pass |
| Workspace members | **287** | `members = [...]` list in root `Cargo.toml` |
| Workspace excludes | 4 | `exclude = [...]` |
| Crate directories under `crates/` | 369 | `ls -d crates/*/ \| wc -l` |
| Crate `Cargo.toml` files under `crates/` | 337 | `ls crates/*/Cargo.toml \| wc -l` |
| `[workspace.dependencies]` entries | 123 | root `Cargo.toml` |
| Lockfile-touching commits | 156 | `git log --oneline -- Cargo.lock \| wc -l` |

**Read:** roughly **5.6 registry crates per first-party crate**. The lockfile is 2.5x the size of
a typical 700-crate Rust workspace and is the dominant surface here: 1,611 third-party packages
against 293 first-party packages.

**Reconciliation note (honest gap):** 287 declared members + 4 excludes vs 337 manifests in
`crates/` and 293 local lockfile entries. The deltas are explained by (a) excluded Tauri/fuzz
crates, (b) crates absorbed into the tree but not enumerated as members, and (c) path
dependencies outside `crates/`. **The exact set difference was NOT computed** in this lane; do
not read 369/337/293 as one consistent population.

---

## 2. Duplicate crate versions

Duplicates were measured on the **number of distinct lockfile versions per crate name**. Full
distribution is long-tailed; the table below lists every crate with 4+ simultaneously-resolved
versions plus a few high-signal 2-3 version cases.

| Crate | Versions present in lockfile | Risk |
|---|---|---|
| `windows-sys` | 0.45.0, 0.48.0, 0.52.0, 0.59.0, 0.60.2, 0.61.2 | **High churn, low runtime risk.** 6 copies of a Windows FFI surface. Compile-time + binary-size cost; no security surface on macOS/Linux. Any Windows audit must cover all 6. |
| `nix` | 0.26.4, 0.27.1, 0.28.0, 0.29.0, 0.31.3 | **Medium.** 5 major API generations. Divergent semantics for the same syscalls; multiplies the surface that security review must cover on Unix. |
| `itertools` | 0.10.5, 0.12.1, 0.13.0, 0.14.0, 0.15.0 | Low. Pure-Rust utility; 5 compilations for zero behavioural difference. |
| `hashbrown` | 0.12.3, 0.14.5, 0.15.5, 0.16.1, 0.17.1 | **Medium.** Hashing/data-structure crate reached transitively; version skew means different DoS-hardening defaults can be live in one binary. |
| `toml` | 0.5.11, 0.8.2, 0.9.12+spec-1.1.0, 1.1.6+spec-1.1.0 | **Medium.** Config parsing is a trust boundary. Two of the four are pre-1.0. |
| `toml_edit` | 4 versions | Low/Medium. Same parser family; editor-side. |
| `syn` | 1.0.109, 2.0.119, 3.0.5 | Low runtime, high build cost. Three proc-macro parser generations compiled per build. |
| `reqwest` | 0.12.28, 0.13.5 | **Medium.** Two HTTP client generations = two TLS/hyper stacks in one product. |
| `rand` | 0.8.8, 0.9.5, 0.10.2 | **Medium.** Three RNG majors. Correctness-sensitive; audit every use of randomness. |
| `rustix` | 0.38.44, 1.1.4 | Low/Medium. Two syscall layers. |
| `opentelemetry` | 4 versions | Low. Telemetry API drift; harmless but inflates the graph. |
| `core-graphics` | 4 versions | Low on non-macOS. 4 FFI generations of the same Apple framework. |
| `windows-targets` / `windows_*_msvc` / `windows_*_gnu` / `windows_*_gnullvm` | 4 each | Low. Mechanical consequence of the 6 `windows-sys` and 3 `windows`/`windows-core` generations. |
| `tracing-opentelemetry` | 3 | Low. |
| `winnow`, `windows-strings`, `windows-result`, `windows-core`, `windows`, `toml_datetime`, `strum_macros` | 3 each | Low. |

**Structural read:** the duplicate mass is concentrated in (i) Windows FFI crates and (ii) the
`toml`/`syn`/`reqwest`/`rand`/`nix` families. Nothing in this table is *inherently* a
vulnerability, but each additional generation is an additional code path that an advisory must be
triaged against independently.

The repo already treats this as a warn-level signal, not a gate — see §5.

---

## 3. Vendoring status and why

**The repo does not vendor.** Evidence:

- `vendor/` is **12 KiB** and contains only `.pre-commit-config.yaml`, `.editorconfig` and
  `.github/workflows/`. **Zero crate source trees.**
- `.cargo/` contains only `audit.toml` and `rustc-wrapper.sh`. **There is no
  `.cargo/config.toml`**, therefore no `[source.crates-io] replace-with` and no
  `[source.vendored-sources]`.
- A grep for `[source` across `Cargo.toml` and `.cargo/*.toml` returned nothing.
- `deny.toml` `[sources]` explicitly allows **only** the crates.io index:
  `unknown-registry = "deny"`, `unknown-git = "deny"`, `allow-registry = ["https://github.com/rust-lang/crates.io-index"]`, `allow-git = []`.

**Read:** resolution is online, from crates.io, with git and unknown registries forbidden by
policy. Reproducibility rests entirely on `Cargo.lock` plus the checksum entries in it, **not** on
a vendored tree. There is no offline/hermetic build. Note the misleading directory name: a
`vendor/` directory exists but does not vendor anything, which is a trap for an auditor who greps
for the path instead of its contents.

---

## 4. License posture

**First-party (this repo):**

| Item | Value |
|---|---|
| `[workspace.package] license` | `"MIT OR Apache-2.0"` |
| `LICENSE` | MIT text, `Copyright (c) 2026 <REDACTED>` |
| `LICENSE-MIT` | MIT text, `Copyright (c) 2026 Koosha Pari` |
| `LICENSE-APACHE` | Apache License 2.0 |
| `NOTICE` | Dual-license statement, `SPDX-License-Identifier: Apache-2.0 OR MIT` |

Two findings, neither fatal:

1. **`LICENSE` is redacted while `LICENSE-MIT` names the holder.** A root `LICENSE` with
   `<REDACTED>` in the copyright line is not a valid MIT grant on its face. `LICENSE-MIT` is.
   `UNKNOWN` whether the redaction is intentional or an artifact of a scrubber.
2. **`NOTICE` names a different project: "phenotype-gfx".** This repo is PhenoShared. A notice
   file referring to another product is a stale absorbed artifact; it should either name
   PhenoShared or be removed. `UNKNOWN` which product the notice is legally intended for.

**Per-crate license *declaration lines* across 337 manifests under `crates/`** (these are
`grep` line counts, not one-per-file counts — 475 declaration lines exceed 337 manifests, so
some manifests produce more than one matching line. Do not divide these by 337.):

| Declaration | Count |
|---|---|
| `license.workspace = true` (inherits `MIT OR Apache-2.0`) | 259 |
| `"MIT OR Apache-2.0"` literal | 113 |
| `"MIT"` | 79 |
| `"Apache-2.0 OR MIT"` (order-flipped variant) | 16 |
| `"Apache-2.0"` | 6 |
| `license-file = "LICENSE"` | 1 |
| `{ workspace = true }` (table form) | 1 |
| **Manifests with no `license` key** | **0** |

**Read:** SPDX coverage is **complete** at the manifest level — zero crates missing a license
field. There are **no `UNKNOWN` first-party licenses**. The cost is *inconsistency*:
`MIT OR Apache-2.0`, `Apache-2.0 OR MIT`, and bare `MIT` all coexist, so 113+16 crates do not
actually inherit the workspace default and 79 are nominally MIT-only despite the
`LICENSE-APACHE` presence. Copyleft is absent first-party.

**Third-party licenses:** gated by the allow-list in `deny.toml`, not enumerated here — see §5.
One deliberately scoped exception exists: `GPL-3.0` is **not** in the allow list and is granted
per-crate only to the `winfsp` bindings reached from `sharecli-fuse` on Windows.

---

## 5. Deny / audit policy and enforcement

`deny.toml` is **196 lines**, actively maintained, and heavily commented with per-advisory
justification (its own schema-migration notes reference cargo-deny `>= 0.14` and `>= 0.19`).

| Section | Setting |
|---|---|
| `[advisories] yanked` | `"warn"` |
| `[advisories] ignore` | **12 distinct RUSTSEC IDs** |
| `[licenses] allow` | 20 SPDX ids: MIT, Apache-2.0, Apache-2.0 WITH LLVM-exception, BSD-2-Clause, BSD-3-Clause, ISC, Unicode-3.0, Unicode-DFS-2016, Zlib, BSL-1.0, 0BSD, Unlicense, CC0-1.0, CC-BY-4.0, MIT-0, NCSA, MPL-2.0, CDLA-Permissive-2.0 |
| `[licenses] confidence-threshold` | 0.8 |
| `[bans] multiple-versions` | **`"warn"`** |
| `[bans] wildcards` | `"allow"` |
| `[bans] skip` | `[]` (empty) |
| `[bans] deny` | empty (only a commented `openssl` example) |
| `[sources]` | crates.io only; unknown registry **deny**, unknown git **deny**, `allow-git = []` |

**The 12 ignored advisories** (each individually justified in-file, none blanket):

`RUSTSEC-2024-0370`, `RUSTSEC-2024-0384`, `RUSTSEC-2024-0436`, `RUSTSEC-2024-0449`,
`RUSTSEC-2025-0134`, `RUSTSEC-2025-0141`, `RUSTSEC-2026-0173`, `RUSTSEC-2026-0249`,
`RUSTSEC-2026-0370`, `RUSTSEC-2026-0371`, `RUSTSEC-2026-0372`, `RUSTSEC-2026-0374`.

Named crates behind these: `bincode 1.3.3`, `instant 0.1.13`, `paste 1.0.15`,
`proc-macro-error 1.0.4`, `proc-macro-error2 2.0.1`, `basic-toml 0.1.10`, `smartstring 1.0.1`,
`unsafe-libyaml 0.2.11`, `zbus_names 4.3.4`, `zvariant 5.15.0`. The documented closing argument
for each is "no published upgrade removes it", which is the correct shape of justification.

**A second, separate ignore list exists** in `.cargo/audit.toml` (for `cargo audit`, not
`cargo-deny`): `RUSTSEC-2025-0140` (atty), `RUSTSEC-2026-0049`, `RUSTSEC-2023-0071` (rsa 0.9.10,
Marvin attack — documented as present in the lockfile with **no active consumer**).

**Two ignore lists that overlap in purpose and do not overlap in content is itself a drift
risk**: an ID triaged in one file is not triaged in the other.

### Enforcement — this is where the posture is weaker than the policy

| Workflow | What it runs | Effective? |
|---|---|---|
| `.github/workflows/deny.yml` ("Dependency Audit") | `cargo deny check licenses`, then `advisories`, `bans`, `sources` — **at repo root, no `continue-on-error`** | **This is the real gate.** Triggers on push to `main` touching `Cargo.lock`/`Cargo.toml`/`crates/**/Cargo.toml`, plus weekly Monday 09:00 UTC. |
| `.github/workflows/cargo-deny.yml` | `cargo-deny-action` with **`manifest-path: iac/Cargo.toml`** | **Does NOT check the root workspace.** It validates the IaC sub-workspace only. Anyone reading the filename would assume the opposite. |
| `.github/workflows/ci.yml` (deny job) | `cargo-deny-action` v2, `--all-features` | `continue-on-error: true` → **advisory only**, cannot fail the build. |
| `.github/workflows/license-compliance.yml` | `cargo deny check` **and** FOSSA | Both steps `continue-on-error: true` → **advisory only.** Runs nightly + on manifest changes. |
| `security.yml`, `security-scan.yml`, `ffi-ci.yml`, `compute-infra-auditors.yml` | reference `cargo deny`/`cargo audit` | Presence confirmed; per-step gating semantics **NOT** read in this lane. |

**Read:** exactly **one** workflow (`deny.yml`) enforces `deny.toml` as a hard gate, and it runs
weekly or on lockfile-touching pushes to `main`. Everything on the PR path is
`continue-on-error: true`, so a PR can merge with a new advisory, a new disallowed license, or a
new non-crates.io source. `deny.yml` installs cargo-deny with `cargo install cargo-deny --locked`
(**unpinned version**) on `dtolnay/rust-toolchain@stable` (**not** the `1.99.0` pin used
everywhere else), so the gate's own tool version and compiler float — a gate that can change
behaviour without a repo change.

---

## 6. Update automation

**Both Dependabot and Renovate are configured.** This is deliberate or accreted; either way it is
duplicated machinery.

`.github/dependabot.yml` — **weekly** for every surface, `open-pull-requests-limit: 10` each:

| Ecosystem | Directory |
|---|---|
| cargo | `/` (all updates grouped into `cargo-workspace`) |
| bun | `/` |
| gomod | `/crates/argis-extensions` |
| uv | `/python`, `/agileplus-mcp` |
| npm | `/docs`, `/crates/policystack`, `/crates/logify/docs`, `/crates/hexa-kit/templates/typescript`, `/crates/hexa-kit/templates/hexagon/typescript` |
| github-actions | `/` |
| terraform | `/iac/terraform`, `/iac/terraform/oci` |

`renovate.json` — `config:recommended` + `helpers:pinGitHubActionDigests`, labels
`["dependencies"]`, schedule **before 6am Monday**, `timezone: America/Los_Angeles`,
`prConcurrentLimit: 5`, `prHourlyLimit: 2`. Every `packageRules` entry sets
**`automerge: false`**; the comment states merging is owned by a Mergify queue, not Renovate.

**Read:** cadence is weekly on both tools with **no auto-merge** and a bounded PR rate (Renovate
caps at 5 concurrent / 2 hourly; Dependabot at 10 per ecosystem — so the actual ceiling is the
combined sum, roughly 40+ open PRs across the ecosystems listed). Two tools on one repo means two
competing PR streams and two ignore/label vocabularies. **No `UNKNOWN` here** — both files were
read.

---

## 7. Toolchain pinning

| Setting | Value | Source |
|---|---|---|
| `rust-toolchain.toml` `channel` | **`"1.99.0"`** (exact, deliberately not `stable`) | `rust-toolchain.toml` |
| components | `["rustfmt", "clippy"]` | same |
| `[workspace.package] rust-version` | `"1.80"` | root `Cargo.toml:857` |
| `[workspace.package] edition` | `"2021"` | root `Cargo.toml:852` |
| `[workspace.package] version` | `"0.3.10"` | root `Cargo.toml` |

The pin is documented in-file: a floating channel previously left local rustup at 1.97.1 while
CI's `dtolnay@stable` floated to 1.98/1.99, so a locally-green `make check` failed cold in CI. The
file instructs bumping `rust-toolchain.toml` and `.github/workflows/quality-gate.yml` **together in
one commit**.

**Read:** MSRV (1.80) and the pinned toolchain (1.99.0) are 19 minor versions apart, which is
consistent with a build-on-latest policy and a conservative claimed MSRV. **Whether 1.80 actually
builds this tree was not verified** (`UNKNOWN`) — claiming 1.80 while compiling on 1.99 for an
extended period is the normal way an MSRV claim rots.

**Inconsistency with §5:** the hard gate `deny.yml` uses `dtolnay/rust-toolchain@stable` and an
unpinned `cargo install cargo-deny`, so the one enforcing job is the one job that ignores the pin.

---

## 8. Non-Rust dependency surfaces

| Surface | Present | Size / evidence |
|---|---|---|
| Node/bun | **Yes** | `package.json` 1,751 B. `pnpm-lock.yaml` **absent**. Dependabot targets the `bun` ecosystem at `/`, plus 5 separate `npm` directories. |
| Python | **Yes** | `pyproject.toml` 5,652 B, **`uv.lock` 417,290 B** (~407 KiB). Dependabot: `uv` at `/python` and `/agileplus-mcp`. |
| Go | Not at root | `go.sum` **absent at root**; Dependabot declares `gomod` at `/crates/argis-extensions`, whose comment cites "the critical/high advisories". A Go surface therefore exists inside the Rust tree. |
| Terraform / IaC | **Yes** | `iac/terraform` and `iac/terraform/oci` (from Dependabot); `iac/Cargo.toml` is a separate cargo manifest that `cargo-deny.yml` actually targets. |
| FOSSA | Configured | `.github/workflows/license-compliance.yml`, `continue-on-error: true`, nightly. |

**Read:** the supply chain is **polyglot**, and the Rust lockfile is not the only large one —
`uv.lock` at 417 KiB is comparable in weight to the Rust graph. The Go module is the one surfaced
as carrying "critical/high" advisories in the Dependabot comment, i.e. the highest-severity
known-risk statement in the repo applies to a **non-Rust** surface that no Rust gate can see.

---

## 9. Top supply-chain risks, with evidence

1. **PR-path enforcement of `deny.toml` is nominal.** `ci.yml` deny job is
   `continue-on-error: true`; `license-compliance.yml` is `continue-on-error: true` on both
   cargo-deny and FOSSA; `cargo-deny.yml` checks `iac/Cargo.toml`, not the root. Only
   `deny.yml` (weekly + on `main` lockfile pushes) gates. **A PR can introduce a disallowed
   license, a new advisory, or a non-crates.io source and merge green.** Evidence: the four
   workflow files named, read directly.

2. **12 advisory IDs ignored in `deny.toml` + 3 more in `.cargo/audit.toml`, in two files that
   do not share a list.** Each root-toml entry carries a real justification, but the split
   inventory means triage state is not single-source. `cargo audit` and `cargo deny` can therefore
   disagree about the same RUSTSEC in the same tree. Evidence: both files read and counted.

3. **1,611 registry packages against 293 first-party crates, with 6 `windows-sys`, 5 `nix`,
   5 `itertools`, 5 `hashbrown`, 4 `toml`, 3 `syn`, 3 `rand`, 2 `reqwest`, 2 `rustix`
   generations live simultaneously.** `deny.toml` sets `multiple-versions = "warn"` and
   `skip = []`, so no duplicate is gated. Each duplicate generation is an independent advisory
   target and an independent review surface. Evidence: lockfile version counts per crate.

4. **Two competing dependency-update bots.** Dependabot (weekly, 10/ecosystem) and Renovate
   (Monday pre-6am, 5 concurrent) both run on the same manifests with `automerge: false` on all
   rules. Duplicate PR streams dilute review attention precisely on the surface that most needs
   attention. Evidence: `dependabot.yml` + `renovate.json` read in full.

5. **The single enforcing gate floats its own toolchain.** `deny.yml` runs
   `dtolnay/rust-toolchain@stable` and `cargo install cargo-deny --locked` (unpinned version),
   while the repo's own contract in `rust-toolchain.toml` pins `1.99.0` and instructs lockstep
   bumps. The gate's behaviour can change with no commit in this repo. Evidence: `deny.yml`
   lines 24-39 vs `rust-toolchain.toml`.

6. **No vendoring, no `[source]` replacement — reproducibility is lockfile-only.** `vendor/` is a
   12 KiB non-vendor directory; there is no `.cargo/config.toml`; `deny.toml` `[sources]` allows
   only crates.io. Any crates.io outage, yank, or index inconsistency is a build outage.
   Evidence: directory listings, absence of `config.toml`, `[sources]` block.

7. **First-party license artifacts are internally inconsistent.** `LICENSE` carries
   `Copyright (c) 2026 <REDACTED>` while `LICENSE-MIT` names Koosha Pari; `NOTICE` names
   **phenotype-gfx**, a different product. Meanwhile 79 crates declare bare `MIT` and 6 declare
   bare `Apache-2.0`, so the stated `MIT OR Apache-2.0` workspace default is not what every crate
   offers. Evidence: files read, manifest license histogram. **The exact per-file split was not
   computed** — the histogram is declaration-line counts — so treat the divergence as
   demonstrated-in-kind, not quantified.

8. **The highest-severity known advisories sit on a non-Rust surface that the Rust gate cannot
   see.** `dependabot.yml` labels the Go module `/crates/argis-extensions` "with the
   critical/high advisories". `cargo-deny` covers none of Go, Python (`uv.lock`, 417 KiB), or
   npm. Evidence: `dependabot.yml` comments; absence of a Go gate in the read workflows
   (`go-audit` exists in `deny.yml` at line ~42, but its gating semantics were not read —
   **`UNKNOWN`, not cleared**).

9. **`[workspace.package] rust-version = "1.80"` while the pinned toolchain is 1.99.0.** Nineteen
   minor versions of drift between the claimed MSRV and the compiler anyone actually uses. The
   claim is unverified in this lane (`UNKNOWN`), which is itself the risk. Evidence: both values.

10. **`vendor/` is a decoy.** An auditor or a `vendor/`-grepping CI policy would conclude the repo
    vendors its dependencies. It does not. Evidence: `du -sh vendor` → 12K; `find vendor` → three
    config files, zero crate sources.
