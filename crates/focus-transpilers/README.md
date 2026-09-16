# focus-transpilers

Lossless round-trip compilers between IR and authoring surfaces. Implements bidirectional transpilers for: TOML ↔ IR (legacy template-pack migration), Wizard form state ↔ IR (UI form serialization), Graph JSON ↔ IR (ReactFlow export format), focus_rules::Rule ↔ IR (native rule format).

## Purpose

Enables authoring in multiple formats (TOML, UI wizard, graph editor, native Rust struct) with automatic conversion to IR for storage. Preserves byte-equivalence through canonical hashing so "same rule, different source" hashes to the same value. Supports round-trip without data loss.

## Key Types

- `focus_rules_transpiler` — Rule ↔ IR (canonical Rust format)
- `toml_transpiler` — TOML ↔ IR (legacy migration)
- `wizard_transpiler` — Form state ↔ IR (UI wizard outputs)
- `graph_transpiler` — ReactFlow JSON ↔ IR (visual rule editor)
- `SourceFormat` enum — variants for each transpiler
- Stub modules for future transpilers (connector, policy, ritual, task, wallet)

## Entry Points

- `transpile()` — convert from any source format to IR
- `transpile_back()` — convert from IR to source format
- Canonical hashing ensures deterministic round-trips

## Functional Requirements

- Lossless round-trip transpilation
- Deterministic hashing for deduplication
- Support for multiple authoring surfaces

## Consumers

- `focus-templates` (TOML → IR)
- Web rule editor (graph/form → IR)
- Admin CLI (export to TOML/JSON)
