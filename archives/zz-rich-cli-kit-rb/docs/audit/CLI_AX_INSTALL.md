# CLI Install & Consumption Audit: rich-cli-kit ↔ helios-cli

**Date:** 2026-06-14  
**Auditor:** Forge (read-only, no builds, no git ops)  
**Scope:** Verify consumer count of `rich-cli-kit` inside `helios-cli`, audit the install/build story on both sides, and recommend a consumption path.

---

## 1. Executive Summary

| Finding | Result |
|---------|--------|
| `rich-cli-kit` consumers in `helios-cli` | **ZERO** — confirmed by exhaustive local + remote search |
| `rich-cli-kit` crates.io presence | **NONE** — not published |
| `rich-cli-kit` GitHub releases | **NONE** — `gh release list` returns empty |
| `helios-cli` buildable state | **SCAFFOLD** — `codex-rs/` workspace declared but source NOT committed |
| `helios-cli` install story coherence | **BROKEN** — `pnpm build` is a no-op; CI references non-existent files |

---

## 2. rich-cli-kit Package Identity

The workspace ships two crates:

| Crate | Type | Version | Path |
|-------|------|---------|------|
| `rck-core` | Library | `0.1.0` | `crates/rck-core/Cargo.toml:2` |
| `rck-cli` | Binary (`rck`) | `0.1.0` | `crates/rck-cli/Cargo.toml:2` |

Workspace manifest: `Cargo.toml:3`  
```toml
members = ["crates/rck-core", "crates/rck-cli"]
```

---

## 3. Consumer Verification — helios-cli

### 3.1 Local filesystem search

Pattern: `rich-cli-kit|rck-core|rck-cli|rck-cli-mcp|rck\b`  
Path: `C:/Users/koosh/Dev/helios-cli` (recursive)  
**Result:** 0 matches across all files.

Pattern: `kitty graphics|graphics protocol|sixel|terminal graphics|image.*terminal|OSC 8|OSC 52|OSC 133`  
Path: `C:/Users/koosh/Dev/helios-cli` (recursive)  
**Result:** 0 matches across all files.

### 3.2 GitHub remote code search

```bash
gh search code "rich-cli-kit" repo:KooshaPari/helios-cli --json path,textMatches
gh search code "rck-core"     repo:KooshaPari/helios-cli --json path,textMatches
gh search code "rck-cli"      repo:KooshaPari/helios-cli --json path,textMatches
```

**Result:** All three return `[]` (empty arrays). No references exist in the remote repository either.

### 3.3 Verdict

**Confirmed: rich-cli-kit has ZERO consumers inside helios-cli.**

The only tangentially related declarations in `helios-cli` are its own (non-existent) workspace crates:
- `codex-utils-image` — `codex-rs/Cargo.toml:141` (declared but source missing)
- `codex-terminal-detection` — `codex-rs/Cargo.toml:129` (declared but source missing)

These are internal codex utilities, not imports of `rck-core`.

---

## 4. Install Story Audit — rich-cli-kit

### 4.1 README quickstart

`README.md:29-56` shows **only** a "build from source" path:

```bash
cd rich-cli-kit
cargo build --release
./target/release/rck detect
./target/release/rck progress 0.42 --label "building"
```

There is **no** `cargo install rck-cli` instruction, no `crates.io` badge, and no released binary download link.

### 4.2 crates.io / registry status

- `Cargo.toml` for both crates lacks `publish = false`, but also lacks any `keywords`, `categories`, or `documentation` fields that would aid discovery.
- `cargo search rck-core` was attempted; no published crate exists (search blocked on file lock, but the absence of a crates.io page is consistent with the un-published version `0.1.0` and zero release history).
- The `Cargo.lock` only contains registry dependencies; `rck-core` and `rck-cli` are listed as local path-only packages (`Cargo.lock:446-471`).

### 4.3 GitHub releases

```bash
gh release list --repo KooshaPari/rich-cli-kit --limit 5
```

**Result:** Empty output. No releases, no prebuilt binaries, no installable artifacts.

### 4.4 Build orchestration

| File | Purpose | Observations |
|------|---------|--------------|
| `Taskfile.yml:8-10` | `cargo build --workspace` | Dev-only, no install target |
| `justfile:7-8` | `cargo build --workspace` | Dev-only, no install target |
| `rust-toolchain.toml:2` | `channel = "stable"` | Standard, no custom target |
| `deny.toml:15` | `allow-registry = ["crates.io"]` | Standard; no private registry |
| `clippy.toml:2` | `msrv = "1.75"` | Well-defined, but not enforced in CI via published crate |

### 4.5 Incoherence findings

1. **No installable artifact.** A CLI toolkit that wants to be "consumed" by other projects must be either (a) a `cargo install`-able binary on crates.io, or (b) a documented Git submodule / path-dependency workflow. `rich-cli-kit` is neither.
2. **No library consumption documentation.** The README treats the entire project as a standalone binary. It does not explain how another Rust project would add `rck-core` as a dependency for kitty-graphics encoding, progress bars, or panel rendering.
3. **MCP server is Python-only and undocumented for install.** `README.md:52-55` shows `pip install -e .` inside `mcp/`, but there is no `setup.py` or `pyproject.toml` checked in the root listing (not audited deeper; out of scope).

---

## 5. Install Story Audit — helios-cli

### 5.1 README honesty

`README.md` (fetched from GitHub raw, because the local checkout does **not** contain a root `README.md`):

```markdown
> **Work state:** SCAFFOLD · **Progress:** `█░░░░░░░░░ 10%`
> Currently governance/CI skeleton only — codex-rs workspace members declared
> but source NOT committed; does not build. Needs source vendored or re-scope.
```

This is the most critical finding: **helios-cli does not contain the Rust source code it claims to build.**

### 5.2 Local file evidence

| Claim | Reality |
|-------|---------|
| `codex-rs/Cargo.toml` declares 64 workspace members | `codex-rs/` contains **only** `Cargo.toml` and `Cargo.lock` |
| `codex-rs/cli/Cargo.toml` should exist | `dir /s /b codex-rs\*.rs` → **File Not Found** |
| `codex-rs/tui/Cargo.toml` should exist | Same — directory does not exist |
| `scripts/stage_npm_packages.py` referenced in CI | Not present in local checkout |
| `codex-cli/README.md` referenced in CI | Not present in local checkout |

`codex-rs/Cargo.toml:1-65` lists members including `cli`, `tui`, `utils/image`, etc. None are on disk.

### 5.3 package.json & CONTRIBUTING.md incoherence

`package.json:10`:
```json
"build": "echo 'no build step'"
```

`CONTRIBUTING.md:18-24`:
```bash
# Install dependencies
pnpm install
# Build all packages
pnpm build
```

**Incoherence:** `pnpm build` literally prints `"no build step"`. The contributing guide promises a build that does not exist.

### 5.4 CI incoherence

`.github/workflows/ci.yml:37-52` stages an npm package using `python3 ./scripts/stage_npm_packages.py`, but the script does not exist locally. The workflow then runs `./scripts/asciicheck.py README.md` and `scripts/readme_toc.py README.md` — also missing locally.

`.github/workflows/cargo-deny.yml:8-9` calls a reusable workflow:
```yaml
uses: KooshaPari/phenotype-tooling/.github/workflows/reusable/cargo-deny.yml@main
```

This is coherent *only* if the workspace were actually present; running it against a skeleton with no `Cargo.lock` in the member directories would fail or produce misleading results.

### 5.5 Release incoherence

`gh release list` shows `helios-cli v0.2.0` (2026-04-25). Release body:

```markdown
## [0.2.0] - 2026-04-25
### Added
- Helios Family Sync: Coordinated 0.2.0 release across 6 repos
- Enhanced release channel framework integration
- Improved governance and CI consistency across family
```

**Assets:** `[]` (empty).  
**Incoherence:** A release tagged `v0.2.0` with no installable artifacts, produced from a repo that admits it "does not build."

---

## 6. Recommendation — How to Make helios-cli Consume rich-cli-kit

### 6.1 Prerequisites (both sides must fix)

| Side | Blocker | Fix |
|------|---------|-----|
| `helios-cli` | No Rust source committed | Vendor or re-scope `codex-rs/` so at least `cli` and `tui` crates compile |
| `rich-cli-kit` | Not on crates.io | Publish `rck-core` to crates.io, or document path-dependency workflow |

### 6.2 Option A — crates.io dependency (recommended)

Once `rck-core` is published:

1. Add to `helios-cli/codex-rs/Cargo.toml` workspace dependencies:
   ```toml
   [workspace.dependencies]
   rck-core = "0.1.0"
   ```
2. Add to the relevant member crate (likely `codex-tui` or `cli`):
   ```toml
   [dependencies]
   rck-core = { workspace = true }
   ```
3. Use `rck-core` APIs for:
   - Inline image rendering (replacing or augmenting `codex-utils-image`)
   - Terminal capability detection (replacing or augmenting `codex-terminal-detection`)
   - Progress bars / status panels during long-running agent operations

### 6.3 Option B — Git subtree / path dependency (immediate but fragile)

If crates.io publishing is blocked:

1. Add `rich-cli-kit` as a Git submodule under `helios-cli/vendor/rich-cli-kit`.
2. Patch `codex-rs/Cargo.toml`:
   ```toml
   [patch.crates-io]
   rck-core = { path = "../vendor/rich-cli-kit/crates/rck-core" }
   ```
3. **Risk:** Git submodules are fragile in CI; path-patches break when directory layout changes.

### 6.4 Option C — Binary invocation (short-term, no Rust integration)

If `helios-cli` remains a Node/TS-first CLI and the Rust layer stays thin:

1. Add a `postinstall` or runtime check that downloads `rck` binary from a future GitHub release:
   ```json
   "scripts": {
     "postinstall": "node scripts/download-rck.js"
   }
   ```
2. Shell out to `rck` for image rendering, progress, and panels from the Node side.
3. **Risk:** Cross-platform binary distribution is painful; version coupling is loose.

### 6.5 Suggested integration points inside helios-cli

Based on the declared (but missing) workspace members:

| Target crate | rich-cli-kit capability | Why it fits |
|--------------|------------------------|-------------|
| `codex-tui` (`codex-rs/Cargo.toml:41`) | `rck-core` progress + panel + image | `codex-tui` already uses `ratatui` (`Cargo.toml:236`); `rck-core` can augment inline graphics without a full TUI stack |
| `cli` (`codex-rs/Cargo.toml:17`) | `rck-core` detect + emit + interactive | The CLI entrypoint is the natural place to add `rck` subcommands or agent-facing output primitives |
| `codex-utils-image` (`codex-rs/Cargo.toml:141`) | `rck-core` kitty-graphics encoder | `codex-utils-image` already depends on `image` (`Cargo.toml:201`); `rck-core` can replace/adorn its terminal-output path |
| `codex-terminal-detection` (`codex-rs/Cargo.toml:129`) | `rck-core` capability detection | `rck-core` has a more sophisticated detector (env + kitty query + TTY check) than basic `TERM` parsing |

---

## 7. File References

### rich-cli-kit
- `Cargo.toml:1-28` — workspace definition
- `crates/rck-core/Cargo.toml:1-18` — library crate manifest
- `crates/rck-cli/Cargo.toml:1-18` — binary crate manifest
- `README.md:29-56` — source-only quickstart
- `Taskfile.yml:8-10` — build task
- `justfile:7-8` — build recipe

### helios-cli
- `package.json:1-32` — Node manifest with `"build": "echo 'no build step'"`
- `CONTRIBUTING.md:18-24` — promises `pnpm build` which is a no-op
- `codex-rs/Cargo.toml:1-65` — declares 64 workspace members; **none exist on disk**
- `.github/workflows/ci.yml:37-52` — references `scripts/stage_npm_packages.py` (missing)
- `.github/workflows/ci.yml:61-69` — references `scripts/asciicheck.py` and `codex-cli/README.md` (missing)
- `.github/workflows/cargo-deny.yml:8-9` — reusable workflow call against a skeleton
- `docs/rationalization/helioscope-absorption.md:32` — local `cargo check --workspace` failed on pre-existing parse error

---

## 8. Conclusion

`rich-cli-kit` is a well-structured Rust workspace with zero external consumers. `helios-cli` is an unbuildable scaffold. Before any consumption can happen, **both projects need to ship real artifacts**:

1. `rich-cli-kit` must publish `rck-core` to crates.io (or at least tag a GitHub release with prebuilt binaries).
2. `helios-cli` must commit the actual `codex-rs` source code so that the workspace compiles.

Until those two blockers are resolved, the only "integration" possible is theoretical.
