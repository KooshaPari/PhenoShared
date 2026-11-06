# Sidekick — Functional & Non-Functional Specification

**REPOID:** SIDEKICK  
**Version:** 0.0.1-remediation  
**Status:** Audit remediation scaffold  
**Last updated:** 2026-06-25

Supersedes informal FRs in `docs/FUNCTIONAL_REQUIREMENTS.md` for traceability purposes. All new work MUST reference IDs from this document.

---

## Scope

Sidekick is a named collection of agent utility crates for the Phenotype ecosystem:

- `sidekick-messaging` — multi-provider messaging adapter (Rust)
- `sidekick-dispatch` — multi-provider agent dispatch (Rust, pending workspace)
- `sidekick-presence` — user presence and focus mode (Python, pending cutover)
- `cheap-llm-mcp` — budget LLM routing MCP server (Python)

---

## Functional Requirements (FR)

### Messaging

| ID | Requirement | Acceptance criteria | Test trace |
|----|-------------|---------------------|------------|
| SIDE-FR-001 | The system SHALL expose a `MessagingAdapter` trait for pluggable providers | Trait has `send` and `is_available`; impls are `Send + Sync` | `sidekick-messaging` lib tests |
| SIDE-FR-002 | The system SHALL support iMessage, SMS, and Email providers | `MessageProvider` enum with all three variants | `test_provider_display` |
| SIDE-FR-003 | The system SHALL model messages with recipient, body, and provider | `Message::new` constructs valid struct | `test_message_creation` |
| SIDE-FR-004 | The system SHALL return typed errors for provider and auth failures | `MessagingError` variants are `PartialEq` in tests | `test_error_usage` |

### Dispatch (planned)

| ID | Requirement | Acceptance criteria | Test trace |
|----|-------------|---------------------|------------|
| SIDE-FR-010 | The system SHALL route agent jobs to configured providers | Router selects provider from config | `sidekick-dispatch` (pending) |
| SIDE-FR-011 | The system SHALL persist dispatch jobs for retry | Append to durable store | `storage_stubs.rs` scaffold |
| SIDE-FR-012 | The system SHALL log dispatch outcomes | Structured JSON per job | OBSERVABILITY.md |

### Presence (planned)

| ID | Requirement | Acceptance criteria | Test trace |
|----|-------------|---------------------|------------|
| SIDE-FR-020 | The system SHALL track user availability status | JSON snapshot readable/writable | Cutover verification |
| SIDE-FR-021 | The system SHALL support focus-mode signaling | `focus_mode` field in presence.json | DATA.md schema |

### LLM routing

| ID | Requirement | Acceptance criteria | Test trace |
|----|-------------|---------------------|------------|
| SIDE-FR-030 | The system SHALL route prompts to budget LLM providers | `Router.complete` returns `Completion` | `test_router.py` |
| SIDE-FR-031 | The system SHALL enforce monthly spend caps | `Ledger` rejects over-cap calls | `test_ledger.py` |
| SIDE-FR-032 | The system SHALL cache repeated prompts in dev | `TTLCache` hit/miss semantics | `test_cache.py` |
| SIDE-FR-033 | The system SHALL expose MCP tools for completion | Server integration tests pass | `test_server_integration.py` |

---

## Non-Functional Requirements (NFR)

### Data (I-Data)

| ID | Requirement | Acceptance criteria | Test trace |
|----|-------------|---------------------|------------|
| SIDE-DATA-001 | Each crate SHALL own its persistence contract | Documented in DATA.md | Manual review |
| SIDE-DATA-002 | No crate SHALL share another crate's database file | Boundary diagram in DATA.md | Architecture review |
| SIDE-DATA-003 | PII at rest SHALL be minimized | Messaging has no local store by default | `storage_stubs.rs` |
| SIDE-DATA-004 | Ledger entries SHALL be append-only | `Ledger` writes JSONL only | `test_storage_stubs.py` |

### Observability (G-Obs)

| ID | Requirement | Acceptance criteria | Test trace |
|----|-------------|---------------------|------------|
| SIDE-OBS-001 | Python MCP SHALL emit JSON structured logs | `JsonFormatter` output parseable | `test_logging.py` |
| SIDE-OBS-002 | Rust crates SHALL support tracing initialization | `init_tracing` exports | `observability_stubs.rs` |
| SIDE-OBS-003 | Logs SHALL NOT contain raw secrets or tokens | Hash/truncate policy in OBSERVABILITY.md | Code review |
| SIDE-OBS-004 | Operations SHALL be correlatable via request_id | `request_scope` binds ID | `test_observability_stubs.py` |

### Testing (D-Test)

| ID | Requirement | Acceptance criteria | Test trace |
|----|-------------|---------------------|------------|
| SIDE-TEST-001 | Every workspace crate SHALL have `#[cfg(test)]` or integration tests | CI `cargo test --workspace` green | CI |
| SIDE-TEST-002 | Least-covered modules SHALL have test stubs | Stubs marked `audit-stub` | This remediation |
| SIDE-TEST-003 | Python package SHALL maintain pytest coverage on core modules | pytest in CI (planned) | `cheap-llm-mcp/tests/` |

### Governance (L-Gov)

| ID | Requirement | Acceptance criteria | Test trace |
|----|-------------|---------------------|------------|
| SIDE-GOV-001 | Repository SHALL maintain FR/NFR spec | This file exists | Manual review |
| SIDE-GOV-002 | Repository SHALL run security scans in CI | trufflehog, codeql, cargo-audit | `.github/workflows/` |
| SIDE-GOV-003 | All crates SHALL use Apache-2.0 | LICENSE + manifest | `Cargo.toml` |
| SIDE-GOV-004 | Remediation docs SHALL exist per audit pillar | `docs/remediation/*.md` | Manual review |

### Operations (K-Ops)

| ID | Requirement | Acceptance criteria | Test trace |
|----|-------------|---------------------|------------|
| SIDE-OPS-001 | CI SHALL run fmt, clippy, and test on push | `ci.yml` | GitHub Actions |
| SIDE-OPS-002 | Releases SHALL produce SBOM | `docs/security/sbom.json` | `sbom-refresh.yml` |
| SIDE-OPS-003 | Health checks SHALL be documented | OBSERVABILITY.md P1 | Follow-up |

---

## Out of scope

- Unified agent orchestration (lives in Phenotype canonical repos)
- Frontend UI (L16 — HTML docs only)
- Multi-tenant SaaS deployment
- Real-time messaging delivery guarantees (provider-dependent)

---

## Change log

| Date | Change | Author |
|------|--------|--------|
| 2026-06-25 | Initial FR/NFR scaffold for audit remediation | composer lane |
