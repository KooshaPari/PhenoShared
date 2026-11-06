# AGENTS.md — KlipDot

- **Location:** repos/KlipDot
- **Tier:** 0 (Phenotype-org wide-tree v11)

## Quick Links

- **Local CLAUDE.md:** See `CLAUDE.md` in this repository for project-specific guidance
- **Phenotype org governance:** `/Users/kooshapari/CodeProjects/Phenotype/repos/CLAUDE.md`
- **Global agent guidance:** `~/.claude/AGENTS.md`
- **AgilePlus work tracking:** `cd /Users/kooshapari/CodeProjects/Phenotype/repos/AgilePlus && agileplus <command>`

## Project Snapshot

| Field | Value |
| ----- | ----- |
| Language | Rust (edition 2021) |
| Crate name | `klipdot` |
| Binary | `klipdot` (`src/main.rs`) |
| Workspace | single-package (root crate) |
| Platforms | macOS, Linux (X11/Wayland), Windows |
| License | MIT (`LICENSE`) |
| Description | Universal terminal image interceptor that maps images to file paths for any CLI/TUI application |

## Tier-0 Quality Gates (run before every commit)

From the repo root:

```bash
just tier0          # umbrella: fmt-check + lint + deny + audit + pre-commit
just ci             # build + test + lint
cargo check         # minimum compile-time check
```

Individual gates (use `just --list` for the full set):

| Recipe | Purpose |
| ------ | ------- |
| `fmt-check` | Verify formatting (no auto-fix) |
| `fmt` | Auto-format the workspace |
| `lint` | Clippy with `-D warnings` |
| `test` | Run the workspace test suite |
| `build` | Debug build |
| `build-release` | Release build (LTO, strip) |
| `deny` | cargo-deny (licenses, advisories, bans, sources) |
| `audit` | cargo-audit (RustSec advisory DB) |
| `secrets` | trufflehog secret scan (if installed) |
| `pre-commit` | Run all pre-commit hooks |
| `docs` | Build rustdoc |

## Key Workflows

1. **Before implementing:** Check AgilePlus for existing specs
   ```bash
   cd /Users/kooshapari/CodeProjects/Phenotype/repos/AgilePlus
   agileplus list --repo KlipDot
   ```
2. **Quality gates:** Run `just tier0` (covers lint + tests + supply-chain)
3. **Worktrees:** Use `repos/KlipDot-wtrees/<topic>/` for feature work
4. **Integration:** Commit to canonical repo (`main`) after quality gates pass

## Hygiene Files (do not delete)

| File | Purpose |
| ---- | ------- |
| `justfile` | Single entrypoint for local CI gates |
| `rustfmt.toml` | rustfmt formatting rules |
| `clippy.toml` | clippy lint configuration |
| `deny.toml` | cargo-deny license/ban/source policy |
| `.editorconfig` | Whitespace + EOL rules per editor |
| `.gitattributes` | Line-ending normalization + binary marking |
| `.gitignore` | VCS exclusions (build artifacts, IDE state) |
| `.pre-commit-config.yaml` | pre-commit hook chain |
| `CODEOWNERS` (root and `.github/`) | PR review ownership |
| `.github/workflows/` | GitHub Actions CI pipeline |

## Project-Specific Gotchas

- **`clippy.json` at the repo root is a build artifact** (cargo
  `--message-format=json` output from a previous debug run on another
  machine). It is *not* the lint configuration. The lint configuration
  lives in `clippy.toml`. The artifact is git-ignored.
- **`clippy_*.txt` and `p3_out.txt`** are likewise build artifacts and
  are git-ignored.
- **`docs/intent/KlipDot.md`** is auto-propagated from the
  `phenotype-registry` source of truth — do **not** edit it locally;
  regenerate via `scripts/propagate-intent-to-repos.py`.
- The `clap-ext` crate is sourced from a git tag (`v0.1.0`); see
  `Cargo.toml` and `deny.toml` allow-list.

## Cross-Project Reuse

During development, proactively identify code that is sharable across
Phenotype repositories. Prefer extraction into existing shared modules;
propose new shared packages when appropriate. See
`/Users/kooshapari/CodeProjects/Phenotype/repos/CLAUDE.md` for the
canonical cross-project policy.

---

**Parent contract:** Extends Phenotype-org governance. See `CLAUDE.md`
and parent `AGENTS.md` for complete operating procedures.
