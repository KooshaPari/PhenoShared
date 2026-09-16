# focus-audit

Append-only audit log with tamper-evident SHA-256 hash chains. Each record commits to its predecessor's hash; the first record chains from the literal string `"genesis"`. Hashes are computed over canonicalized JSON (sorted keys, no whitespace) for cross-platform determinism.

## Purpose

Provides immutable, cryptographically-verifiable audit trail for all state mutations (rewards, penalties, policy changes). Enables detection of tampering, replay audits, and compliance reporting. Traces to FR-STATE-004 (audit append on mutation) and FR-DATA-003 (chain verification).

## Key Types

- `AuditRecord` — timestamp, mutation type, user_id, payload, prev_hash, hash
- `AuditChain` — collection of records with `verify_chain()` to detect tampering
- `ChainError` — variants for missing record, hash mismatch, invalid payload
- `canonical::canonicalize()` — deterministic JSON serialization

## Entry Points

- `AuditChain::append()` — add record with automatic hash chaining
- `AuditChain::verify_chain()` — validate all hashes; returns `ChainError` on mismatch
- `AuditChain::from_sqlite()` — load and verify chain from storage

## Functional Requirements

- FR-DATA-002 (Audit append on state mutations)
- FR-DATA-003 (Chain verification detects tampering)
- FR-STATE-004 (Mutations recorded immutably)

## Consumers

- `focus-storage::sqlite` (persists audit records)
- `focus-rewards`, `focus-penalties`, `focus-policy` (append on mutation)
- Admin reporting + compliance audits
