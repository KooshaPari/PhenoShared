# focus-ir

FocalPoint Intermediate Representation (IR). Single canonical JSON format for all FocalPoint documents: Rule, Connector, Template, Task, Schedule, Pose, CoachingConfig, EnforcementPolicy, WalletMutation, Ritual, SoundCue, AuditQuery. Content-addressed via SHA-256 hash of canonical JSON (sorted keys, no whitespace).

## Purpose

Provides a stable, version-aware IR that serializes all domain types to a single canonical format. Enables lossless round-trip compilation from high-level languages (Starlark, TOML, UI forms) to IR and back. Hash-based content addressing ensures determinism and enables deduplication.

## Key Types

- `Document` — top-level wrapper with kind, version, content, metadata
- `Content` enum — variants for Rule, Connector, Template, Task, Schedule, etc.
- `Metadata` — created_at, updated_at, author, tags, description
- Canonical JSON serialization with deterministic hashing

## Entry Points

- `Document::new()` — construct with content, auto-compute hash
- `Document::to_json()` / `from_json()` — serialization
- `canonical_hash()` — deterministic SHA-256 of sorted JSON

## Functional Requirements

- Single canonical format for all FocalPoint primitives
- Deterministic hashing for content addressing
- Lossless round-trip from source languages to IR

## Consumers

- `focus-lang` (Starlark → IR compiler)
- `focus-transpilers` (TOML ↔ IR, Graph ↔ IR, Wizard ↔ IR)
- `focus-templates` (template pack serialization)
- Storage adapters (universal document persistence)
