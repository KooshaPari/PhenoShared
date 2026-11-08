# Governance Template Fleet Defaults

**Status:** Active  
**Date:** 2026-06-17  
**Owner:** `<REDACTED>/phenokits-commons`  
**Authority:** [`phenotype-registry/BOUNDARY_OWNERS.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/BOUNDARY_OWNERS.md) §Governance plane  
**Disposition:** [`docs/boundary/DISPOSITION.md`](../docs/boundary/DISPOSITION.md)

This spec defines the **default governance bootstrap** copied into new Phenotype fleet
repos. It supersedes copying from archived `PhenoProc` or `PhenoKits`.

---

## When to use this source

| Scenario | Bootstrap from | Notes |
|----------|----------------|-------|
| New repo via `hexakit init` | HexaKit `.template.*` + this spec | HexaKit stamps infra-generic files; add governance depth from here |
| Manual repo bootstrap | **This repo** `governance/phenoproc-*` | Copy-on-init, then tailor per repo |
| `agileplus validate` | `governance/phenoproc-configs/` | ADR-005: AgilePlus consumes templates, does not own them |
| CI workflow templates | `configs/cicd/github-actions/workflows/` | Copy-source; org reusables at `<REDACTED>/.github` |

**Do not** copy governance templates from archived `PhenoProc`, `PhenoKits`, or
stale HexaKit `phenotype-governance/` paths.

---

## Default copy set (minimum viable fleet member)

### 1. Language configs — `governance/phenoproc-configs/`

| Path | Purpose |
|------|---------|
| `universal/.editorconfig` | Editor baseline |
| `universal/_typos.toml` | Spell check |
| `rust/rustfmt.toml`, `rust/clippy.toml` | Rust formatting + lint |
| `python/ruff.toml` | Python lint/format |
| `typescript/eslint.config.js` | TS/JS lint |
| `go/golangci.yml` | Go lint |
| `deny.toml`, `buf.yaml`, `buf.gen.yaml` | Supply-chain + protobuf (if applicable) |
| `oxlint.config.json` | Fast JS lint pass |

### 2. CI / integration templates — `governance/phenoproc-templates/`

| Path | Purpose |
|------|---------|
| `ci/adr-validation.yml.template` | ADR gate workflow |
| `ci/coverage-rust.yml.template` | Rust coverage |
| `ci/container-rust.yml.template` | Container build |
| `ci/release-rust.yml.template` | Release automation |
| `github/AGENTS.md.template` | Agent instructions stub |
| `rust/bdd_integration/` | BDD scaffold (feature + steps) |
| `rust/http_client_integration/` | HTTP client + mock tests |
| `rust/validation_integration/` | Config validation scaffold |
| `INTEGRATION_CHECKLIST.md` | Post-copy verification |
| `Taskfile.yml` | Local task runner baseline |

### 3. CI workflow copy-source — `configs/cicd/github-actions/workflows/`

Prefer **reusable** workflows from `<REDACTED>/.github` when available:

| Reusable (org) | Local template fallback |
|----------------|-------------------------|
| `reusable-rust-ci.yml` | `rust-template.yml` |
| `reusable-python-ci.yml` | `python-template.yml` |
| `reusable-typescript-ci.yml` | `typescript-template.yml` |
| `reusable-go-ci.yml` | (add when published) |
| `reusable-cargo-deny.yml` | `security-template.yml` |
| `reusable-policy-gate.yml` | `policy-gate.yml` |

### 4. Per-repo test harness (optional by stack)

| Stack | Copy from |
|-------|-----------|
| Docsite (VitePress/etc.) | `docs/tests/` |
| Webapp template | `templates/webapp/docs/tests/` + `templates/webapp/.github/` |
| Hexagonal Python | `templates/hexagonal/hexagonal-python/tests/` |
| Hexagon reference | `hexagon/templates/*/docs/tests/` |

---

## Bootstrap procedure

```text
1. Create repo (HexaKit init OR manual)
2. Copy governance/phenoproc-configs/<langs-used>/ → repo root or config dirs
3. Copy governance/phenoproc-templates/ci/*.template → .github/workflows/ (strip .template)
4. Copy github/AGENTS.md.template → AGENTS.md (fill repo-specific sections)
5. Wire reusable workflows from <REDACTED>/.github OR local configs/cicd templates
6. Run governance/phenoproc-templates/INTEGRATION_CHECKLIST.md
7. Register repo in phenotype-registry ECOSYSTEM_MAP (if new canonical boundary)
```

For Rust repos, also copy integration scaffolds from `governance/phenoproc-templates/rust/`
into `tests/` or `examples/` as appropriate.

---

## Customization rules

| Artifact type | Org-locked | Repo-editable |
|---------------|------------|---------------|
| `phenoproc-configs/universal/*` | Yes — do not weaken | Extend via local overrides documented in ADR |
| CI workflow templates | Base structure locked | Job matrix, crate names, paths |
| `AGENTS.md.template` | Section headers | Repo-specific commands and paths |
| Integration scaffolds | Pattern locked | Domain examples and feature text |

---

## Validation

After bootstrap, verify:

- [ ] `pre-commit` runs (if enrolled)
- [ ] Language configs match repo stack (see `phenotype-registry/LANGUAGE_STACK.md`)
- [ ] No copy from archived PhenoProc/PhenoKits paths
- [ ] `agileplus validate` passes (AgilePlus repos)
- [ ] Boundary declared in repo `BOUNDARY.md` or `AGENTS.md` scaffold section

---

## Related

- [`governance/README.md`](README.md)
- [`docs/absorption/PHENOPROC_GOVERNANCE_PORT.md`](../docs/absorption/PHENOPROC_GOVERNANCE_PORT.md)
- [`phenotype-registry/docs/adr/ADR-005-agileplus-governance-boundary.md`](https://github.com/KooshaPari/phenotype-registry/blob/main/docs/adr/ADR-005-agileplus-governance-boundary.md)
- [`HexaKit/docs/scaffolding/FLEET_INIT.md`](https://github.com/KooshaPari/HexaKit/blob/main/docs/scaffolding/FLEET_INIT.md) (when published)
