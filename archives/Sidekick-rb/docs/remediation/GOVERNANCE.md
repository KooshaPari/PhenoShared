# Governance Remediation — Sidekick

**Audit pillar:** L-Gov (34%)  
**Status:** Remediation scaffold — FR/NFR traceability, quality gates, and compliance hooks.  
**Last updated:** 2026-06-25

## Summary

Sidekick lacked a canonical `docs/specs/SPEC.md` with formal FR/NFR IDs traceable to tests and CI. This remediation establishes governance artifacts without replacing Phenotype org policy (see parent `CLAUDE.md`, `AGENTS.md`).

---

## Governance artifacts

| Artifact | Path | Purpose |
|----------|------|---------|
| Functional + non-functional spec | `docs/specs/SPEC.md` | FR/NFR IDs, acceptance criteria |
| Functional requirements (legacy) | `docs/FUNCTIONAL_REQUIREMENTS.md` | Scaffold; superseded by SPEC for new work |
| Data remediation | `docs/remediation/DATA.md` | I-Data pillar |
| Observability remediation | `docs/remediation/OBSERVABILITY.md` | G-Obs pillar |
| Testing remediation | (this section + test stubs) | D-Test pillar |
| Intent / boundary | `docs/intent/sidekick.md`, `docs/boundary/sidekick.md` | L7 taxonomy |
| Worklogs | `docs/worklogs/GOVERNANCE.md` | Session notes |

---

## Requirement traceability matrix

| ID | Type | Statement | Verification |
|----|------|-----------|--------------|
| SIDE-FR-001 | FR | Multi-provider messaging adapter | `sidekick-messaging` unit + integration tests |
| SIDE-FR-002 | FR | Budget LLM routing via MCP | `cheap-llm-mcp` pytest suite |
| SIDE-FR-003 | FR | Agent dispatch to providers | Dispatch storage stubs + future CI |
| SIDE-FR-004 | FR | User presence tracking | Presence cutover + future pytest |
| SIDE-NFR-001 | NFR | Apache-2.0 license on all crates | `LICENSE`, `Cargo.toml` |
| SIDE-NFR-002 | NFR | No secrets in repo | TruffleHog CI, `trufflehog.yml` |
| SIDE-NFR-003 | NFR | Workspace quality gates | `cargo fmt`, `clippy`, `test` in CI |
| SIDE-NFR-004 | NFR | Structured observability | OBSERVABILITY.md + observability stubs |
| SIDE-NFR-005 | NFR | Documented persistence contracts | DATA.md + storage stubs |
| SIDE-DATA-001 | NFR | Per-crate storage ownership | DATA.md |
| SIDE-OBS-001 | NFR | JSON structured logs | `logging_util`, `sidekick-observability` |
| SIDE-GOV-001 | NFR | FR/NFR spec exists | `docs/specs/SPEC.md` |

---

## Quality gates (mandatory before merge)

```bash
cargo fmt --check
cargo clippy --workspace -- -D warnings
cargo test --workspace
# Python (cheap-llm-mcp):
cd crates/cheap-llm-mcp && uv run pytest
```

**CI workflows:** `.github/workflows/ci.yml` plus security (CodeQL, cargo-audit, trufflehog, scorecard).

---

## AgilePlus integration

Work tracked in Phenotype `AgilePlus` repo per `CLAUDE.md`:

```bash
cd /path/to/AgilePlus
agileplus specify --title "Sidekick audit remediation" --description "I/G/D/L pillars"
agileplus status <id> --wp <wp> --state <state>
```

**WP mapping (suggested):**

| Work package | Pillar | Branch prefix |
|--------------|--------|---------------|
| Data persistence | I-Data | `fix/sidekick-data-*` |
| Observability | G-Obs | `fix/sidekick-obs-*` |
| Testing | D-Test | `fix/sidekick-test-*` |
| Governance | L-Gov | `fix/sidekick-gov-*` |

---

## Release governance

| Crate | Registry | Version policy | Attestation |
|-------|----------|----------------|-------------|
| `sidekick-messaging` | crates.io (planned) | SemVer from workspace | `release-attestation.yml` |
| `sidekick-dispatch` | crates.io (alpha) | Independent patch OK | SBOM in `docs/security/` |
| `cheap-llm-mcp` | PyPI (planned) | `pyproject.toml` version | SBOM |
| `sidekick-presence` | PyPI (planned) | pyproject version | — |

See `RELEASE.md`, `release-registry.toml`, `docs/slsa.md`.

---

## Review cadence

| Review | Cadence | Owner | Next |
|--------|---------|-------|------|
| Boundary (`docs/boundary/sidekick.md`) | 30d | Maintainer | 2026-07-21 |
| FR/NFR spec (`docs/specs/SPEC.md`) | Per release | Maintainer | v0.1.0 |
| Audit scorecard | Quarterly | Forge / composer lane | 2026-09-25 |
| SBOM refresh | On dependency bump | CI (`sbom-refresh.yml`) | Automated |

---

## Remediation checklist

- [x] Author `docs/specs/SPEC.md` with FR/NFR IDs
- [x] Author governance remediation doc (this file)
- [x] Cross-link DATA, OBSERVABILITY, and test stubs
- [ ] Populate `docs/boundary/sidekick.md` in-scope / out-of-scope tables
- [ ] Fill `docs/intent/sidekick.md` intent statement
- [ ] AgilePlus WP registration for audit pillars
- [ ] FR coverage matrix in CI (fail on untested FR IDs)

---

## Anti-patterns (do not)

1. **Shared mutable global state** across crates — violates workspace independence.
2. **Undocumented file paths** under `~/.sidekick/` — must appear in DATA.md first.
3. **FR IDs without tests** — every FR in SPEC.md needs a `#[test]` or pytest trace comment.
4. **Bypassing CI** — no `--no-verify` on governance commits.

**Parent contract:** Extends Phenotype org `AGENTS.md`. Sidekick is **non-canonical** per L7 taxonomy (`docs/intent/sidekick.md`).
