# FR-GITHUB-001 — AgilePlus GitHub Integration

> Spec anchor: `specs/014-agileplus-github/`
> Status: PROPOSED → accepted on `cargo test -p agileplus-github` pass
> Crate: `agileplus-github`

## Description

The `agileplus-github` adapter synchronizes AgilePlus work packages with
GitHub issues, pull requests, and project boards. Webhook ingestion is
idempotent (delivery ID + event type), and outbound writes go through a
rate-limited GraphQL/REST port. Tokens are loaded from
`agileplus-config` and never logged; webhook signatures are verified
against the configured secret.

## Acceptance Criteria

| AC  | Criterion |
|-----|-----------|
| AC1 | Webhook handler accepts `issues`, `pull_request`, and `project_card` events. |
| AC2 | Duplicate webhook deliveries (same delivery ID) are silently dropped after the first. |
| AC3 | Webhook signature is verified against the configured secret; invalid signatures return 401. |
| AC4 | Tokens are loaded from `agileplus-config` and never appear in logs or traces. |
| AC5 | Outbound API calls are rate-limited (token bucket, configurable RPS). |
| AC6 | At least one sync direction (inbound issue → work package) is wired with a passing test. |
| AC7 | 5xx responses trigger exponential backoff with jitter, capped at 6 retries. |
| AC8 | `github_integration.rs` proves ACs above with at least one assertion per AC. |

## Traceability

- Spec: `specs/014-agileplus-github/`
- Code: `crates/agileplus-github/src/`
- BDD: `specs/014-agileplus-github/bdd/`
- Tests: `crates/agileplus-github/tests/github_integration.rs`
- Journey: `docs/journeys/github-sync.md`
