# Architecture Decision Records - template-lang-go

**Status**: Active

This document tracks architectural decisions for the template-lang-go project.

---

## ADR-LG-001: Go Language Template Layer

**Date**: 2026-04-02
**Status**: Accepted
**Deciders**: Phenotype Team

### Context

template-lang-go provides language-specific project templates for Go applications within the Phenotype platform ecosystem.

### Decision

Follow Go best practices with:
- Standard Go project layout
- Taskfile for build orchestration
- Comprehensive error handling with wrapped errors
- Context propagation for cancellation
- Structured logging with slog

### Consequences

- Developers get consistent Go project scaffolding
- Enforced coding standards across Go projects
- Faster onboarding for new Go developers

---

## ADR-LG-002: Template Composition Strategy

**Date**: 2026-04-02
**Status**: Accepted
**Deciders**: Phenotype Team

### Context

Go templates must compose with template-commons and domain layers.

### Decision

Templates layer as follows:
1. template-commons (base)
2. template-lang-go (language)
3. template-domain-* (domain, optional)

### Consequences

- Modular template composition
- Clear separation of concerns
- Reusable base templates
