# ADR-0008: Intent Graph Ontology

## Status

Accepted

## Context

User intent must trace from prompt → spec → code → test → PR without ad-hoc link tables.
AgilePlus and `agileplus-mcp-intent` need a shared, validated graph model. The PM-core
spine (`traceability-core::intent_graph`) is the org-wide source for node types, DAG
stages, and relationship semantics.

## Decision

1. **Canonical model**: `IntentGraph` with typed `Node` (`NodeType`: Intent, Plan, Feature,
   Story, Task, Spec, Commit, Test, PR, Bug, Artifact), `Edge` (`RelationshipType`), and
   `DagStage` ordering.
2. **Human source, machine derivative**: Markdown intent artifacts and kitty-specs are the
   human-readable source of truth; JSON intent graphs are validated derivatives (see
   `convert_prompt_to_intent_graph` in agileplus-mcp-intent).
3. **Validation at ingest**: `IntentGraph::validate()` enforces acyclic DAG constraints,
   allowed node/edge combinations, and canonical link types before persistence or MCP export.
4. **Traceability bridge**: Intent-graph nodes link to spine artifacts (`ArtifactRef`,
   `RequirementId`) and coverage-matrix rows; they do not replace Tracera trace links.
5. **AgilePlus re-exports** spine types from `agileplus-domain`; no parallel ontology.

## Consequences

- Agents and CLI tools share one intent vocabulary across repos.
- Invalid graphs are rejected at authoring time, not at ship gate.
- Graph validation logic is centralized in PM-core; AgilePlus consumes updates via
  `cargo update -p traceability-core`.
- MCP intent tooling and kitty-specs must align node ids with graph validation rules.

## References

- ADR-0005: traceability-core git dependency
- `crates/traceability-core/src/intent_graph.rs`
- `docs/superpowers/specs/2026-06-14-intent-artifact-design.md`
