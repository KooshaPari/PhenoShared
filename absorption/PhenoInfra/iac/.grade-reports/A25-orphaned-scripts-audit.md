# A25 — Orphaned Scripts Audit (`iac/`)

**Date:** 2026-06-24  
**Scope:** All `.sh`, `.rs`, and `.ps1` files under `iac/`, plus companion READMEs in `iac/scripts/`

---

## Methodology

1. Enumerate every `.sh`, `.rs`, `.ps1`, `.md` file under `iac/` (Rust crate `.rs` files
   are included for completeness but are owned by `Cargo.toml` — they are not
   standalone scripts).
2. Grep for each script's filename across the repo:
   - `iac/README.md`
   - `iac/scripts/README.md`
   - All markdown under `docs/` (runbooks, governance, specs)
   - `.github/workflows/*.yml`
   - Other `.rs`/`.sh` files that reference sibling scripts by name.
3. Classify as **Referenced** (appears in ≥1 non-trivial reference) or
   **Orphaned** (zero references outside the file itself).

---

## Results

### 1. `iac/scripts/` — Primary script directory

| File | Type | Status | References |
|------|------|--------|------------|
| `bootstrap-oci.sh` | Bash | **Referenced** | `iac/scripts/README.md:10`, `.github/workflows/terraform-plan.yml:47` |
| `health-check.sh` | Bash | **Referenced** | `iac/scripts/README.md:12`, `docs/specs/rollback-kill-switch-spec.md:34`, `docs/runbooks/node-rebuild-recovery.md:25`, `docs/runbooks/day1-oci-first-light.md:99` |
| `register-home-runner.sh` | Bash | **Referenced** | `iac/scripts/README.md:11`, `docs/runbooks/day1-home-runner-setup.md:52`, `docs/runbooks/day1-home-runner-setup.md:56` |
| `install-windows-runner.ps1` | PowerShell | **Referenced** | `iac/scripts/README.md:13,17,42,48`, `iac/scripts/README-windows-runner.md:1,48,51`, `docs/runbooks/windows-desktop-runner.md:6,27,60,125`, self-doc at end of file |
| `restore-rulesets.rs` | Rust standalone | **Referenced** | `iac/data/billing-blocked-rules.json:3` (data file description cites it as consumer), self-doc at line 23 |

### 2. Companion documentation (not scripts, inventoried for context)

| File | Type | Status | Notes |
|------|------|--------|-------|
| `iac/scripts/README.md` | Markdown | — | Primary script index; referenced by `iac/README.md:23` |
| `iac/scripts/README-windows-runner.md` | Markdown | — | Extended runner docs; referenced by nothing else — companion to `.ps1` |

### 3. `iac/oci-post-acquire/` — Hook scripts

| File | Type | Status | References |
|------|------|--------|------------|
| `oci-post-acquire.sh` | Bash | **Referenced** | `iac/README.md:13`, `iac/oci-post-acquire/Cargo.toml:11`, `iac/oci-lottery/src/hooks.rs:36,51`, `docs/governance/oci-acquire-hook-chain.md:5,12,85,100`, `docs/runbooks/day1-oci-first-light.md:24` |
| `hooks.d.example/10-update-portfolio-card.sh` | Bash | **Referenced** | `iac/oci-post-acquire/hooks.d.example/README.md:26`, `docs/governance/oci-acquire-hook-chain.md:88` |

### 4. `iac/tailscale/` — Infrastructure scripts

| File | Type | Status | References |
|------|------|--------|------------|
| `apply-acl.sh` | Bash | **Referenced** | `iac/tailscale/acl.json:3`, `docs/governance/tailscale-policy.md:115` |

### 5. Rust crate source files (not standalone scripts)

All files under the following directories are owned by their `Cargo.toml` and
are **not** standalone executable scripts. They are listed for completeness.

| Crate | `.rs` files | Entry via | Referenced by |
|-------|-------------|-----------|---------------|
| `landing-bootstrap/` | `src/main.rs` | `Cargo.toml` | `iac/README.md:15` |
| `observability/` | `src/lib.rs` | `Cargo.toml` | `Cargo.toml` workspace |
| `oci-lottery/` | `src/main.rs`, `src/config.rs`, `src/hooks.rs`, `src/oci.rs`, `src/state.rs` | `Cargo.toml` | `iac/README.md:12` |
| `oci-post-acquire/` | `src/main.rs`, `src/cf.rs`, `src/hooks.rs`, `src/mesh.rs`, `src/tailscale.rs` | `Cargo.toml` | `iac/README.md:13` |
| `phenotype-logging-stub/` | `src/lib.rs` | `Cargo.toml` | `Cargo.toml` workspace |
| `tailscale/tailscale-keygen/` | `src/main.rs` | `Cargo.toml` | `iac/README.md:14` |

---

## Summary

- **Total standalone scripts inventoried:** 6
- **Referenced:** 6 (bootstrap-oci.sh, health-check.sh, register-home-runner.sh, install-windows-runner.ps1, restore-rulesets.rs, oci-post-acquire.sh)
- **Hook scripts inventoried:** 2
- **Referenced:** 2 (10-update-portfolio-card.sh, apply-acl.sh)
- **Orphaned (standalone scripts only):** 0
- **Orphaned (hook/infra scripts):** 0

**No orphaned scripts found.** Every script under `iac/` has at least one
reference in a README, runbook, governance doc, workflow, or data file.

### Notes

- `README-windows-runner.md` is a companion doc for `install-windows-runner.ps1`.
  It has no cross-references from docs/ but is not a script — its purpose is
  served by co-location with the `.ps1` file it documents.
- `restore-rulesets.rs` is a Rust `cargo-script` (`+stable -Zscript`). It is
  referenced only from `iac/data/billing-blocked-rules.json` (which it consumes)
  and its own `--help` output. This is a valid-but-minimal reference; the script
  is alive and functional but could benefit from a runbook mention.
- All Rust crate `.rs` files are under `Cargo.toml` management and are not
  orphaned by construction.
