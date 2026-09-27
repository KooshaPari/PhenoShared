# ADR-002: Technology Stack Selection

## Status

**Accepted** — 2026-05-25

## Author

KooshaPari

## Context

The Phenotype org builds a mix of engine-side tooling and web-facing products. We need a coherent language and framework baseline that covers CLI/backend performance, safe systems programming, and productive web development. The stack must be consistent enough that contributors can move across repos without re-learning tooling.

## Decision

We adopt **Rust** as the primary language for all backend, CLI, and systems-level components, and **TypeScript** with **TanStack** (Router, Query, Form, Table) for all web/dashboard frontends. Python is used for AI/ML glue tooling via **FastMCP**.

Rust delivers memory safety and deterministic performance with no GC pauses, which is critical for engine and simulation workloads. TypeScript with TanStack provides type-safe, framework-agnostic primitives that compose well and avoid the churn associated with full-framework lock-in. FastMCP offers a minimal, decorator-driven surface for exposing Python inference code as Model Context Protocol servers.

## Consequences

### Positive
- Single language per layer reduces context-switching cost
- Rust ownership model eliminates whole classes of runtime bugs
- TanStack's headless primitives avoid opinionated UI lock-in
- FastMCP keeps Python services thin and MCP-compliant by default

### Negative / Trade-offs
- Rust compile times are longer than Go or TypeScript
- Rust learning curve is steep for developers new to the ownership model
- Mixing three languages requires discipline to avoid layering violations

## References

- [Phenotype scripting hierarchy](../CLAUDE.md)
- ADR-001 — Hexagonal Architecture

---

*Decision Date: 2026-05-25*
*Next Review: 2027-05-25*
