# phenotype-compliance-scanner

**Governance rule types and federation schema only.**

This crate is **not** the Phenotype linter runtime. For static analysis, vibes, scoring, and MCP fix loops, use:

- [KodeVibe](https://github.com/KooshaPari/KodeVibe) `engine/` (successor to archived KodeVibeGo)
- [kwality](https://github.com/KooshaPari/kwality) for LLM output validation

See [KodeVibe quality platform architecture](https://github.com/KooshaPari/KodeVibe/blob/main/docs/architecture/quality-platform.md).

## Scope

- `KodeVibeRuleSet` YAML schema types
- Minimal regex policy rules for CI federation gates
- Config cross-reference to `.kodevibe.yaml`

Full scanner implementation intentionally lives outside HexaKit.
