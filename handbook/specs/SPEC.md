# SPEC: PhenoHandbook — Patterns & Guidelines Registry

## Meta

- **ID**: phenohandbook-001
- **Title**: PhenoHandbook Specification — Design Patterns & Best Practices
- **Created**: 2026-04-04
- **Updated**: 2026-04-04
- **State**: specified
- **Version**: 1.0.0
- **Language**: Markdown (MkDocs + VitePress)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Vision & Goals](#vision--goals)
3. [Architecture Overview](#architecture-overview)
4. [Content Model](#content-model)
5. [Pattern Format Specification](#pattern-format-specification)
6. [Anti-Pattern Format](#anti-pattern-format)
7. [Guidelines Format](#guidelines-format)
8. [Methodology Specifications](#methodology-specifications)
9. [Checklist Format](#checklist-format)
10. [Registry Index](#registry-index)
11. [Publication Pipeline](#publication-pipeline)
12. [Quality Assurance](#quality-assurance)
13. [Tooling Integration](#tooling-integration)
14. [Governance Model](#governance-model)
15. [Content Roadmap](#content-roadmap)
16. [Success Metrics](#success-metrics)
17. [Risks & Mitigations](#risks--mitigations)
18. [References](#references)
19. [Appendix](#appendix)

---

## Executive Summary

PhenoHandbook is the authoritative living documentation for design patterns, anti-patterns, guidelines, and best practices in the Phenotype ecosystem. It serves as the central knowledge base for building software the "Phenotype way" — consumed by developers and indexed by automated tooling.

### Key Statistics

| Metric | Target | Current |
|--------|--------|---------|
| Patterns | 100+ | 15 |
| Anti-patterns | 50+ | 5 |
| Guidelines | 30+ | 4 |
| Methodologies | 7 | 7 |
| Checklists | 20+ | 3 |
| Code Examples | 500+ | 75 |
| ADRs | 20+ | 3 |

### Document Hierarchy

```
Phenotype Documentation Ecosystem:

┌─────────────────────────────────────────────────────────────────┐
│                    PhenoHandbook (This Spec)                     │
│              Patterns, Guidelines, Best Practices               │
├─────────────────────────────────────────────────────────────────┤
│                            │                                     │
│              ┌─────────────┴─────────────┐                      │
│              ▼                           ▼                      │
│    ┌──────────────────┐       ┌──────────────────┐             │
│    │   PhenoSpecs     │       │    HexaKit       │             │
│    │  Specifications  │◄─────►│  Templates       │             │
│    │  (Designs/ADRs)  │       │  (Scaffolding)   │             │
│    └──────────────────┘       └──────────────────┘             │
│              │                           │                      │
│              └─────────────┬─────────────┘                      │
│                            ▼                                     │
│              ┌───────────────────────────┐                     │
│              │      AgilePlus            │                     │
│              │  (Spec-Driven Development)│                     │
│              └───────────────────────────┘                     │
│                                                                  │
│  Cross-References:                                               │
│  • Pattern → Links to Spec implementation                       │
│  • Spec → Links to Template                                     │
│  • Template → Links to Handbook patterns                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Vision & Goals

### Vision Statement

> To be the most comprehensive, practical, and actionable patterns resource for spec-driven, hexagonal-architecture software development.

### Goals

| Goal ID | Goal | Priority | Success Metric |
|---------|------|----------|----------------|
| G1 | Document all core patterns | P0 | 100% coverage of identified patterns |
| G2 | Provide multi-language examples | P0 | Rust, Go, TypeScript, Python for each pattern |
| G3 | Link patterns to specs and templates | P0 | Bidirectional linking 100% |
| G4 | Enable automated consumption | P1 | Machine-readable registry |
| G5 | Community contributions | P1 | 30% external contributions |
| G6 | Integration with heliosCLI | P1 | CLI can query and apply patterns |
| G7 | Video/visual supplements | P2 | 25% of patterns have diagrams |

### Non-Goals

- Reproduce language-specific documentation
- Duplicate framework tutorials
- Cover proprietary/closed patterns
- Provide production deployment configs (moved to PhenoSpecs)

---

## Architecture Overview

### System Context

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       PhenoHandbook System Context                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌────────────────────────────────────────────────────────────────────┐    │
│   │                         Content Sources                             │    │
│   │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                │    │
│   │  │   patterns/  │  │ anti-patterns/│  │ guidelines/  │                │    │
│   │  │              │  │              │  │              │                │    │
│   │  │ • auth/      │  │ • security/  │  │ • style/     │                │    │
│   │  │ • caching/   │  │ • performance│  │ • review/    │                │    │
│   │  │ • async/     │  │ • api/       │  │ • workflow/  │                │    │
│   │  │ • database/  │  │ • testing/   │  │ • languages/ │                │    │
│   │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                │    │
│   └─────────┼─────────────────┼─────────────────┼────────────────────────┘    │
│             │                 │                 │                              │
│   ┌─────────┴─────────────────┴─────────────────┴─────────────────────────────┐│
│   │                            Indexing Layer                                    ││
│   │  ┌─────────────────────────────────────────────────────────────────────┐    ││
│   │  │              Registry Index (registry.yaml)                            │    ││
│   │  │                                                                      │    ││
│   │  │   Pattern ID → File path → Tags → Related specs → Code examples       │    ││
│   │  │   PATTERN-AUTH-001 → patterns/auth/oauth-pkce.md                      │    ││
│   │  │   PATTERN-ARCH-001 → patterns/architecture/hexagonal.md               │    ││
│   │  │   ANTI-PATTERN-001 → anti-patterns/security/plaintext-tokens.md     │    ││
│   │  └─────────────────────────────────────────────────────────────────────┘    ││
│   └─────────────────────────────────┬───────────────────────────────────────────┘│
│                                     │                                           │
│   ┌─────────────────────────────────┴───────────────────────────────────────────────┐│
│   │                          Publication Layer (VitePress)                          ││
│   │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐       ││
│   │  │  Markdown       │  │  VitePress    │  │  GitHub Pages           │       ││
│   │  │  sources        │  │  (config)       │  │  (deployment)           │       ││
│   │  │                 │  │                 │  │                         │       ││
│   │  │ • Syntax: GFM   │  │ • Theme: Custom │  │ • Auto-deploy            │       ││
│   │  │ • Frontmatter   │  │ • Search        │  │ • PR previews            │       ││
│   │  │ • Code blocks   │  │ • Dark mode     │  │ • Versioning             │       ││
│   │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘       ││
│   └───────────────────────────────────────────────────────────────────────────────┘│
│                                                                                      │
│   ┌─────────────────────────────────────────────────────────────────────────────┐   │
│   │                         Consumer Interfaces                                  │   │
│   │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐      │   │
│   │  │  Web (Human)    │  │  CLI (Developer)│  │  API (Agent/Tooling)    │      │   │
│   │  │                 │  │                 │  │                         │      │   │
│   │  │ handbook.pheno  │  │ pheno handbook  │  │ /api/patterns           │      │   │
│   │  │ type.dev        │  │   search        │  │ /api/anti-patterns      │      │   │
│   │  └─────────────────┘  └─────────────────┘  └─────────────────────────┘      │   │
│   └─────────────────────────────────────────────────────────────────────────────┘   │
│                                                                                      │
└─────────────────────────────────────────────────────────────────────────────────────┘
```

### Component Details

| Component | Path | Language | Responsibility | Status |
|-----------|------|----------|----------------|--------|
| **Patterns** | `patterns/` | Markdown | Design patterns by domain | Active |
| **Anti-patterns** | `anti-patterns/` | Markdown | Common mistakes to avoid | Active |
| **Guidelines** | `guidelines/` | Markdown | Coding standards | Active |
| **Methodologies** | `methodologies/` | Markdown | Development workflows (TDD, BDD, DDD) | Active |
| **Checklists** | `checklists/` | Markdown | Verification lists | Active |
| **ADRs** | `adrs/` | Markdown | Architecture decisions | Active |
| **Site Config** | `docs/.vitepress/config.mts` | TypeScript | VitePress configuration | Active |
| **Registry** | `registry.yaml` | YAML | Machine-readable index | Active |
| **SOTA** | `SOTA.md` | Markdown | State of the Art research | Active |

---

## Content Model

### Pattern Document Structure

```yaml
---
# Frontmatter (required)
id: PATTERN-{CATEGORY}-{NNN}
title: Human-Readable Pattern Name
category: {auth|caching|async|database|observability|api|testing|cli|architecture}
domain: {specific-subdomain}
tags: [tag1, tag2, tag3]
related_specs: [SPEC-XXX-NNN, ADR-NNN]
related_patterns: [PATTERN-XXX-NNN]
created: YYYY-MM-DD
updated: YYYY-MM-DD
status: {draft|review|stable|deprecated}
author: Author Name
---

# Pattern Title

## Summary
One-sentence description of what this pattern solves.

## Problem
### Context
Where does this problem occur?

### Symptoms
How do you recognize this problem?

### Forces
What makes this problem difficult?

## Solution
### Overview
High-level approach.

### Implementation
Detailed steps.

### Structure
```
ASCII diagrams showing structure
```

## Example
### Rust
```rust
// Production-ready Rust code
```

### Go
```go
// Production-ready Go code
```

### TypeScript
```typescript
// Production-ready TypeScript code
```

### Python
```python
# Production-ready Python code
```

## When to Use
- Scenario 1
- Scenario 2
- Scenario 3

## When NOT to Use
- Anti-scenario 1
- Anti-scenario 2

## Variations
### Variation A
Description and when to use.

### Variation B
Description and when to use.

## Consequences
### Benefits
- Benefit 1
- Benefit 2

### Trade-offs
- Trade-off 1
- Trade-off 2

## Related Patterns
- [Pattern Name](link)
- SPEC-XXX-NNN

## References
- External reference 1
- External reference 2

## See Also
- ADR-NNN: Related decision
```

### Anti-Pattern Document Structure

```yaml
---
id: ANTI-PATTERN-{CATEGORY}-{NNN}
title: Anti-Pattern Name
category: {security|performance|architecture|testing|api}
severity: {critical|high|medium|low}
detection: {static-analysis|runtime|manual-review}
fix_complexity: {simple|moderate|complex|architectural}
---

# Anti-Pattern Name

## Summary
What is this anti-pattern?

## The Problem
### Code Example (Bad)
```rust
// Bad code example
```

### Why It's Bad
- Reason 1
- Reason 2

## The Solution
### Code Example (Good)
```rust
// Good code example
```

### Refactoring Steps
1. Step 1
2. Step 2
3. Step 3

## Detection
### Static Analysis
```bash
# Command to detect
```

### Code Review Checklist
- [ ] Check 1
- [ ] Check 2

## Prevention
### Education
How to teach developers to avoid this.

### Tooling
Tools that prevent this.

## References
- External resources
```

### Guidelines Document Structure

```yaml
---
id: GUIDELINE-{CATEGORY}-{NNN}
title: Guideline Name
category: {style|review|workflow|language}
applies_to: [rust, go, typescript, python, all]
enforcement: {required|recommended|optional}
---

# Guideline Name

## Purpose
Why this guideline exists.

## Rule
### The Standard
Clear statement of the rule.

### Examples
#### Correct
```rust
// Correct example
```

#### Incorrect
```rust
// Incorrect example
```

## Rationale
Why this rule matters.

## Exceptions
When it's OK to break this rule.

## Tooling
### Linting
```bash
# Lint command
```

### Formatting
```bash
# Format command
```

## Migration
How to apply this to existing code.
```

### Methodology Document Structure

```yaml
---
id: METHODOLOGY-{XXX}-{NNN}
title: Methodology Name
acronym: {TDD|BDD|DDD|SDD|FDD|CDD|AI-DD}
scope: {unit|feature|system|organization}
---

# Methodology Name

## Overview
What is this methodology?

## When to Use
Appropriate contexts.

## Workflow
### Phase 1: XXX
Description and activities.

### Phase 2: YYY
Description and activities.

### Phase 3: ZZZ
Description and activities.

## Artifacts
### Input
Required inputs.

### Output
Produced artifacts.

### Decision Points
Where decisions are made.

## Tools
Recommended tooling.

## Examples
### Example 1: XXX
Walkthrough.

### Example 2: YYY
Walkthrough.

## Integration
How this integrates with other methodologies.

## Success Metrics
How to measure effectiveness.
```

---

## Pattern Format Specification

### Required Sections

| Section | Required | Length | Purpose |
|---------|----------|--------|---------|
| Summary | Yes | 1 sentence | Quick understanding |
| Problem | Yes | 2-5 paragraphs | Context and forces |
| Solution | Yes | 3-10 paragraphs | The approach |
| Example | Yes | Multi-language | Implementation |
| When to Use | Yes | Bullet list | Applicability |
| Related Patterns | Yes | Links | Navigation |

### Optional Sections

| Section | Use When |
|---------|----------|
| Variations | Multiple approaches exist |
| Consequences | Complex trade-offs |
| When NOT to Use | Common misapplications |
| Performance | Performance-critical |
| Security | Security implications |
| References | External citations |

### Code Example Standards

#### Completeness
```rust
// ✓ Complete, compilable example
use std::collections::HashMap;

pub struct Cache<K, V> {
    store: HashMap<K, V>,
    max_size: usize,
}

impl<K: Eq + std::hash::Hash, V: Clone> Cache<K, V> {
    pub fn new(max_size: usize) -> Self {
        Self {
            store: HashMap::new(),
            max_size,
        }
    }
    
    pub fn get(&mut self, key: &K) -> Option<V> {
        self.store.get(key).cloned()
    }
    
    pub fn put(&mut self, key: K, value: V) {
        if self.store.len() >= self.max_size {
            // LRU eviction logic
        }
        self.store.insert(key, value);
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn cache_stores_and_retrieves() {
        let mut cache = Cache::new(100);
        cache.put("key", "value");
        assert_eq!(cache.get(&"key"), Some("value"));
    }
}
```

#### Testing
Every code example should include:
- Unit tests for pure logic
- Integration test sketch for adapters
- Error handling examples

---

## Anti-Pattern Format

### Severity Levels

| Level | Description | Response Time | Examples |
|-------|-------------|---------------|----------|
| **Critical** | Security vulnerability, data loss | Immediate fix | SQL injection, plaintext passwords |
| **High** | Production incident risk | Fix in current sprint | Memory leaks, race conditions |
| **Medium** | Maintainability impact | Fix next sprint | God objects, tight coupling |
| **Low** | Code smell, tech debt | Fix opportunistically | Commented code, magic numbers |

### Detection Methods

| Method | Coverage | Implementation |
|--------|----------|----------------|
| **Static Analysis** | High | clippy, eslint, semgrep |
| **Runtime Detection** | Medium | Profiling, tracing |
| **Manual Review** | Low | Checklists, patterns |
| **Automated Tests** | Medium | Property-based tests |

---

## Methodology Specifications

### xDD Methodologies

| Methodology | Scope | Primary Artifact | Secondary Artifacts | Phenotype Tool |
|-------------|-------|-----------------|--------------------|----------------|
| **TDD** | Unit | Passing tests | Test list, refactor notes | cargo test |
| **BDD** | Feature | Scenarios (Gherkin) | Step definitions, reports | cucumber-rs |
| **DDD** | System | Ubiquitous language | Bounded contexts, aggregates | Miro, Whimsical |
| **SDD** | System | Specifications | Specs, ADRs, checklists | heliosCLI |
| **FDD** | Feature | Feature lists | Feature trees, progress | Linear, Jira |
| **CDD** | API | Contracts | OpenAPI, schemas | OpenAPI, Smithy |
| **AI-DD** | Unit/Feature | AI-generated code | Prompts, reviews | Claude, Cursor |

### Integration Matrix

```
Methodology Integration:

SDD (Spec-Driven)
    │
    ├──► Creates Specs
    │
    ├──► DDD ──► Defines Bounded Contexts
    │     │
    │     └──► Within each context:
    │           │
    │           ├──► BDD ──► Feature Scenarios
    │           │     │
    │           │     └──► FDD ──► Feature Delivery
    │           │
    │           └──► CDD ──► API Contracts
    │                 │
    │                 └──► TDD ──► Unit Tests
    │                       │
    │                       └──► AI-DD ──► Implementation
    │
    └──► ADR ──► Records Decisions
```

---

## Registry Index

### Registry Schema (registry.yaml)

```yaml
version: "1.0"
last_updated: "2026-04-04"

patterns:
  auth:
    oauth-pkce:
      id: PATTERN-AUTH-001
      path: patterns/auth/oauth-pkce.md
      title: OAuth 2.0 with PKCE
      tags: [oauth, pkce, security, mobile, spa]
      languages: [rust, go, typescript]
      related_specs: [SPEC-AUTH-001]
      related_adrs: [ADR-004]
      status: stable
      
    jwt-management:
      id: PATTERN-AUTH-002
      path: patterns/auth/jwt-management.md
      title: JWT Token Management
      tags: [jwt, tokens, security]
      languages: [rust, go]
      related_specs: [SPEC-AUTH-002]
      status: stable

  architecture:
    hexagonal:
      id: PATTERN-ARCH-001
      path: patterns/architecture/hexagonal.md
      title: Hexagonal Architecture
      tags: [architecture, ports, adapters, testing]
      languages: [rust, go, typescript, python]
      related_specs: [SPEC-ARCH-001]
      related_adrs: [ADR-001]
      status: stable
      
    cqrs:
      id: PATTERN-ARCH-002
      path: patterns/architecture/cqrs.md
      title: CQRS Pattern
      tags: [architecture, cqrs, read-model, write-model]
      languages: [rust]
      related_specs: [SPEC-ARCH-002]
      status: stable

  async:
    event-driven:
      id: PATTERN-ASYNC-001
      path: patterns/async/event-driven.md
      title: Event-Driven Architecture
      tags: [async, events, messaging, nats]
      languages: [rust]
      related_specs: [SPEC-MESSAGING-001]
      related_adrs: [ADR-002]
      status: stable
      
    saga:
      id: PATTERN-ASYNC-002
      path: patterns/async/saga.md
      title: Saga Pattern
      tags: [async, distributed-transactions, compensation]
      languages: [rust]
      related_specs: [SPEC-WORKFLOW-001]
      status: stable
      
    outbox:
      id: PATTERN-ASYNC-003
      path: patterns/async/outbox.md
      title: Outbox Pattern
      tags: [async, reliability, exactly-once]
      languages: [rust]
      related_specs: [SPEC-MESSAGING-002]
      status: stable

anti_patterns:
  security:
    plaintext-tokens:
      id: ANTI-PATTERN-SEC-001
      path: anti-patterns/security/plaintext-tokens.md
      title: Storing Tokens in Plaintext
      severity: critical
      detection: static-analysis
      fix_complexity: simple
      
    hardcoded-secrets:
      id: ANTI-PATTERN-SEC-002
      path: anti-patterns/security/hardcoded-secrets.md
      title: Hardcoded Secrets
      severity: critical
      detection: static-analysis
      fix_complexity: simple

guidelines:
  rust:
    id: GUIDELINE-RUST-001
    path: guidelines/rust.md
    title: Rust Guidelines
    enforcement: required
    tools: [rustfmt, clippy]
    
  go:
    id: GUIDELINE-GO-001
    path: guidelines/go.md
    title: Go Guidelines
    enforcement: required
    tools: [gofmt, golint]

methodologies:
  tdd:
    id: METHODOLOGY-TDD-001
    path: methodologies/tdd.md
    acronym: TDD
    scope: unit
    
  bdd:
    id: METHODOLOGY-BDD-001
    path: methodologies/bdd.md
    acronym: BDD
    scope: feature
    
  sdd:
    id: METHODOLOGY-SDD-001
    path: methodologies/sdd.md
    acronym: SDD
    scope: system

checklists:
  deployment:
    id: CHECKLIST-001
    path: checklists/deployment.md
    title: Pre-Deployment Checklist
    
  security:
    id: CHECKLIST-002
    path: checklists/security.md
    title: Security Review Checklist

adrs:
  hexagonal:
    id: ADR-001
    path: adrs/001-hexagonal-architecture.md
    title: Hexagonal Architecture as Foundational Pattern
    status: accepted
    date: "2026-04-04"
    
  nats:
    id: ADR-002
    path: adrs/002-nats-jetstream.md
    title: NATS JetStream as Event Backbone
    status: accepted
    date: "2026-04-04"
    
  pbt:
    id: ADR-003
    path: adrs/003-property-based-testing.md
    title: Property-Based Testing as Default Strategy
    status: accepted
    date: "2026-04-04"
```

---

## Publication Pipeline

### Build Process

```
┌─────────────────────────────────────────────────────────────────┐
│                    Publication Pipeline                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Source Change (Git Push)                                     │
│            │                                                      │
│            ▼                                                      │
│  2. Validation Phase                                             │
│     ┌───────────────────────────────────────────┐                 │
│     │ • Markdown lint (markdownlint)          │                 │
│     │ • Link check (lychee)                    │                 │
│     │ • Spell check (vale)                   │                 │
│     │ • Code block validation (extract & compile)│               │
│     │ • Registry schema validation            │                 │
│     └───────────────────────────────────────────┘                 │
│            │                                                      │
│            ▼                                                      │
│  3. Build Phase                                                   │
│     ┌───────────────────────────────────────────┐                 │
│     │ • VitePress build                        │                 │
│     │ • Search index generation                │                 │
│     │ • Sitemap generation                     │                 │
│     │ • OG image generation                    │                 │
│     └───────────────────────────────────────────┘                 │
│            │                                                      │
│            ▼                                                      │
│  4. Deployment                                                    │
│     ┌───────────────────────────────────────────┐                 │
│     │ • Deploy to GitHub Pages                │                 │
│     │ • CDN cache invalidation                │                 │
│     │ • Search index update                   │                 │
│     └───────────────────────────────────────────┘                 │
│            │                                                      │
│            ▼                                                      │
│  5. Verification                                                  │
│     ┌───────────────────────────────────────────┐                 │
│     │ • Smoke tests                            │                 │
│     │ • Link verification                      │                 │
│     │ • Performance check (Lighthouse)         │                 │
│     └───────────────────────────────────────────┘                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### CI/CD Configuration

```yaml
# .github/workflows/publish.yml
name: Publish Handbook

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          
      - name: Install dependencies
        run: npm ci
        
      - name: Lint markdown
        run: npx markdownlint-cli2 '**/*.md'
        
      - name: Check links
        run: npx lychee --format detailed .
        
      - name: Validate registry
        run: npx ajv-cli validate -s registry.schema.json -d registry.yaml
        
      - name: Extract and verify code blocks
        run: ./scripts/verify-code-blocks.sh

  build:
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          
      - name: Install dependencies
        run: npm ci
        
      - name: Build VitePress
        run: npm run build
        
      - name: Upload artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: docs/.vitepress/dist

  deploy:
    needs: build
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    steps:
      - name: Deploy to GitHub Pages
        uses: actions/deploy-pages@v4
```

---

## Quality Assurance

### Content Quality Gates

| Gate | Check | Tool | Threshold |
|------|-------|------|-----------|
| Structure | Required sections present | custom script | 100% |
| Links | No broken internal links | lychee | 0 failures |
| Code | All code blocks compile | rust/go/ts compile | 100% |
| Spelling | No spelling errors | vale | 0 errors |
| Style | Style guide compliance | vale | 0 warnings |
| Images | Alt text present | custom script | 100% |
| Frontmatter | Valid YAML | ajv | 100% |

### Review Process

```
┌─────────────────────────────────────────────────────────────────┐
│                    Content Review Process                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Author creates content                                        │
│            │                                                      │
│            ▼                                                      │
│  2. Automated checks (CI)                                        │
│     ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│     │ Structure    │  │ Links        │  │ Code         │       │
│     │ ✓            │  │ ✓            │  │ ✓            │       │
│     └──────────────┘  └──────────────┘  └──────────────┘       │
│            │                                                      │
│            ▼                                                      │
│  3. Peer review (1 reviewer minimum)                               │
│     • Technical accuracy                                          │
│     • Clarity                                                     │
│     • Completeness                                                │
│     • Examples quality                                            │
│            │                                                      │
│            ▼                                                      │
│  4. Technical review (architecture team)                           │
│     • Pattern correctness                                         │
│     • Alignment with ADRs                                         │
│     • Spec links                                                  │
│            │                                                      │
│            ▼                                                      │
│  5. Editorial review (optional)                                    │
│     • Style consistency                                           │
│     • Grammar                                                     │
│            │                                                      │
│            ▼                                                      │
│  6. Merge and publish                                              │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tooling Integration

### heliosCLI Integration

```bash
# Search patterns
pheno pattern search "oauth"

# View pattern
pheno pattern view PATTERN-AUTH-001

# Apply pattern (generate code)
pheno pattern apply PATTERN-AUTH-001 --target ./src/auth/

# List anti-patterns
pheno anti-pattern list --severity critical

# Check project against guidelines
pheno guideline check --lang rust ./src/

# Generate checklist
pheno checklist generate deployment > deploy-checklist.md
```

### IDE Integration

```
VS Code Extension (planned):
- Pattern snippets
- Quick docs on hover
- Anti-pattern warnings
- Guideline enforcement

IntelliJ Plugin (planned):
- Pattern templates
- Architecture verification
- Navigation to handbook
```

### API Endpoints

```yaml
# REST API for programmatic access
/api/v1/patterns:
  get:
    summary: List all patterns
    parameters:
      - category: filter by category
      - tag: filter by tag
      - status: filter by status
      
/api/v1/patterns/{id}:
  get:
    summary: Get pattern by ID
    
/api/v1/search:
  post:
    summary: Search across all content
    body:
      query: search string
      filters: category, language, etc.
```

---

## Governance Model

### Content Ownership

| Content Type | Owner | Reviewers | Approval |
|--------------|-------|-----------|----------|
| **Patterns** | Domain experts | Architecture team | Tech Lead |
| **Anti-patterns** | Security/Platform team | All teams | Security Lead |
| **Guidelines** | Language leads | All developers | Tech Lead |
| **Methodologies** | Process team | All teams | Engineering Manager |
| **ADRs** | Decision makers | Architecture team | CTO |
| **SOTA** | Research team | Domain experts | Tech Lead |

### Change Process

```
Change Request (RFC) Process:

1. RFC Creation
   ├── Problem statement
   ├── Proposed change
   ├── Impact analysis
   └── Migration guide (if breaking)

2. RFC Review (1 week)
   ├── Community feedback
   ├── Expert review
   └── Revision

3. RFC Decision
   ├── Accepted → Create content
   ├── Rejected → Archive with rationale
   └── Deferred → Revisit later

4. Content Creation
   ├── Draft content
   ├── Review process
   └── Publish
```

---

## Content Roadmap

### Phase 1: Foundation (Q2 2026)

| Deliverable | Count | Owner | Status |
|-------------|-------|-------|--------|
| Core patterns | 25 | Architecture team | In Progress |
| Critical anti-patterns | 10 | Security team | In Progress |
| Language guidelines | 4 | Language leads | Done |
| xDD methodologies | 7 | Process team | Done |
| Basic checklists | 5 | Platform team | In Progress |

### Phase 2: Expansion (Q3 2026)

| Deliverable | Count | Owner | Status |
|-------------|-------|-------|--------|
| Extended patterns | 50 | Domain experts | Planned |
| Domain anti-patterns | 20 | All teams | Planned |
| Advanced checklists | 15 | Platform team | Planned |
| Video supplements | 10 | Education team | Planned |

### Phase 3: Maturity (Q4 2026)

| Deliverable | Count | Owner | Status |
|-------------|-------|-------|--------|
| Complete pattern set | 100 | All teams | Planned |
| Tooling integration | Full | Platform team | Planned |
| Community contributions | 30% | Community | Planned |
| Certifications | 3 | Education team | Planned |

---

## Success Metrics

### Usage Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Page views | 10K/month | Analytics |
| Search queries | 1K/month | Search logs |
| CLI pattern applies | 500/month | Telemetry |
| Time on page | 5 min avg | Analytics |
| Return visitors | 40% | Analytics |

### Content Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Pattern coverage | 100% | 15% |
| Multi-language examples | 100% | 30% |
| Linked specs | 100% | 60% |
| Reviewed content | 100% | 80% |
| Freshness (< 1 year) | 90% | 100% |

### Quality Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Code example accuracy | 100% | CI verification |
| Link validity | 100% | CI lychee |
| Spelling errors | 0 | CI vale |
| User ratings | 4.5/5 | Feedback form |
| Issue resolution | 48 hours | GitHub issues |

---

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| **Content staleness** | High | Medium | Automated freshness checks, review reminders |
| **Incomplete coverage** | Medium | High | Roadmap, prioritization framework |
| **Low adoption** | Medium | High | Tooling integration, training |
| **Quality degradation** | Medium | High | Automated checks, review process |
| **Contributor burnout** | Low | Medium | Rotation, recognition |
| **Technology changes** | Medium | Medium | SOTA process, version tracking |

---

## References

### Internal

1. [SOTA.md](./SOTA.md) — State of the Art research
2. [PLAN.md](./PLAN.md) — Implementation plan
3. [README.md](./README.md) — Quick start guide
4. [PhenoSpecs](https://github.com/KooshaPari/PhenoSpecs) — Specification registry
5. [HexaKit](https://github.com/KooshaPari/HexaKit) — Template registry
6. [AgilePlus](https://github.com/KooshaPari/AgilePlus) — Spec-driven development

### External

1. [MkDocs](https://www.mkdocs.org/) — Documentation site generator
2. [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) — Theme
3. [VitePress](https://vitepress.dev/) — Alternative static site generator
4. [Architecture Decision Records](https://adr.github.io/) — ADR format
5. [Pattern Languages of Program Design](https://en.wikipedia.org/wiki/Pattern_Languages_of_Program_Design) — Academic reference

---

## Appendix

### A. Pattern Template

See `templates/pattern.md`

### B. Anti-Pattern Template

See `templates/anti-pattern.md`

### C. Guidelines Template

See `templates/guideline.md`

### D. ADR Template

See `templates/adr.md`

### E. Glossary

| Term | Definition |
|------|------------|
| **Pattern** | Proven solution to a recurring problem |
| **Anti-pattern** | Common mistake with documented solution |
| **Guideline** | Recommended practice or standard |
| **Methodology** | Development process or workflow |
| **ADR** | Architecture Decision Record |
| **SOTA** | State of the Art |
| **Port** | Interface in hexagonal architecture |
| **Adapter** | Implementation of a port |
| **Aggregate** | Consistency boundary in DDD |
| **Saga** | Long-running transaction pattern |

### F. Category Taxonomy

```
Pattern Categories:
├── architecture
│   ├── hexagonal
│   ├── clean
│   ├── microservices
│   └── modular-monolith
├── auth
│   ├── oauth
│   ├── jwt
│   ├── rbac
│   └── mfa
├── caching
│   ├── cache-aside
│   ├── write-through
│   └── multi-tier
├── async
│   ├── event-driven
│   ├── cqrs
│   ├── saga
│   └── outbox
├── database
│   ├── repository
│   ├── unit-of-work
│   └── db-per-service
├── observability
│   ├── tracing
│   ├── logging
│   └── metrics
├── api
│   ├── rest
│   ├── graphql
│   └── rpc
├── testing
│   ├── unit
│   ├── integration
│   └── e2e
└── cli
    ├── argument-parsing
    ├── interactive
    └── plugin-system
```

### G. File Naming Convention

```
Naming Rules:

Patterns:         {category}/{kebab-case-name}.md
                  patterns/auth/oauth-pkce.md
                  
Anti-patterns:    anti-patterns/{category}/{kebab-case-name}.md
                  anti-patterns/security/plaintext-tokens.md
                  
Guidelines:       guidelines/{scope}-{name}.md
                  guidelines/rust.md
                  guidelines/code-review.md
                  
Methodologies:    methodologies/{kebab-case}.md
                  methodologies/tdd.md
                  methodologies/bdd.md
                  
Checklists:       checklists/{kebab-case}.md
                  checklists/deployment.md
                  
ADRs:             adrs/{NNN}-{kebab-case}.md
                  adrs/001-hexagonal-architecture.md
                  
Images:           assets/{category}/{name}.{ext}
                  assets/architecture/hexagonal.svg
```

### H. Frontmatter Schema

```yaml
# Pattern frontmatter schema
id:
  type: string
  pattern: "^PATTERN-[A-Z]+-[0-9]{3}$"
  required: true
  
title:
  type: string
  maxLength: 100
  required: true
  
category:
  type: string
  enum: [architecture, auth, caching, async, database, observability, api, testing, cli]
  required: true
  
domain:
  type: string
  required: false
  
tags:
  type: array
  items:
    type: string
  minItems: 1
  required: true
  
related_specs:
  type: array
  items:
    type: string
    pattern: "^SPEC-[A-Z]+-[0-9]{3}$"
  required: false
  
related_patterns:
  type: array
  items:
    type: string
    pattern: "^PATTERN-[A-Z]+-[0-9]{3}$"
  required: false
  
created:
  type: string
  format: date
  required: true
  
updated:
  type: string
  format: date
  required: true
  
status:
  type: string
  enum: [draft, review, stable, deprecated]
  required: true
  default: draft
  
author:
  type: string
  required: false
```

### I. Code Block Annotation Schema

```markdown
Code block annotations:

```rust,norun
// Code that should not be executed (illustration)
```

```rust,editable
// Code that can be edited in the browser (future)
```

```rust,linenos
// Code with line numbers
```

```rust,tested
// Code that is automatically tested in CI
```

```rust,ignore
// Code that is skipped in CI
```
```

### J. Contribution Checklist

- [ ] Content follows template structure
- [ ] Frontmatter is valid YAML
- [ ] ID follows naming convention
- [ ] Examples compile and work
- [ ] Links are valid
- [ ] Spell check passes
- [ ] Related specs linked
- [ ] Related patterns linked
- [ ] Images have alt text
- [ ] No sensitive data in examples
- [ ] Attribution for external content

### K. Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2026-04-04 | Initial comprehensive specification | Architecture Team |

### L. Future Enhancements

- [ ] Interactive code playgrounds
- [ ] Pattern decision trees
- [ ] AI-assisted pattern matching
- [ ] Video walkthroughs
- [ ] Certification program
- [ ] Community translations
- [ ] Pattern usage analytics
- [ ] Automated pattern suggestions

---

*Generated: 2026-04-04*  
*Version: 1.0.0*  
*Status: Specified*  
*Next Review: 2026-07-04*

---

*Total Lines: 2500+*

---

## Detailed Pattern Specifications

### Authentication Patterns

#### PATTERN-AUTH-001: OAuth 2.0 with PKCE

**Purpose**: Secure delegated authorization for public clients

**Applicability Matrix**:
| Client Type | Recommended | Notes |
|-------------|-------------|-------|
| Mobile apps | Yes | Required by OAuth 2.1 |
| SPAs | Yes | Prevents token leakage |
| Desktop apps | Yes | Secure code exchange |
| Server-side | Optional | Confidential clients can use client secret |

**Security Considerations**:
- Code verifier must be 43-128 characters
- SHA256 (S256) method required
- State parameter for CSRF protection
- Short authorization code lifetime (10 minutes max)

**Performance Characteristics**:
- Additional round trip: 0 (same flow, just extra params)
- Hash computation: < 1ms on modern hardware
- Storage overhead: 128 bytes per flow

**Implementation Checklist**:
- [ ] Code verifier generation uses cryptographically secure RNG
- [ ] Code challenge computed with SHA256
- [ ] State parameter generated and validated
- [ ] PKCE parameters included in authorization request
- [ ] Server validates code_challenge_method = S256
- [ ] Server rejects requests without PKCE for public clients

#### PATTERN-AUTH-002: JWT Token Management

**Purpose**: Stateless authentication with signed tokens

**Token Structure**:
```
┌─────────────────────────────────────────────────────────────────┐
│                    JWT Structure                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Header:                                                        │
│  {                                                               │
│    "alg": "RS256",        // Algorithm                        │
│    "typ": "JWT",          // Type                               │
│    "kid": "key-2024-01"   // Key ID for rotation               │
│  }                                                               │
│                                                                  │
│  Payload:                                                       │
│  {                                                               │
│    "sub": "user-123",     // Subject                           │
│    "iss": "auth.phenotype.dev", // Issuer                      │
│    "aud": "api.phenotype.dev",  // Audience                    │
│    "exp": 1704067200,     // Expiration                        │
│    "iat": 1704063600,     // Issued at                         │
│    "jti": "unique-id",    // JWT ID (revocation)              │
│    "scope": "read write", // Permissions                       │
│    "org_id": "org-456"     // Custom claims                    │
│  }                                                               │
│                                                                  │
│  Signature:                                                     │
│  RSASHA256(                                                     │
│    base64url(header) + "." + base64url(payload),              │
│    private_key                                                  │
│  )                                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Storage Recommendations**:
| Storage | XSS Risk | CSRF Risk | Recommendation |
|---------|----------|-----------|----------------|
| httpOnly Cookie | Low | Medium | **Recommended for web** |
| Memory | Low | Low | **Recommended for SPAs (BFF pattern)** |
| localStorage | High | Low | Avoid for sensitive tokens |
| sessionStorage | High | Low | Session-only data only |

**Token Lifetimes**:
| Token Type | Recommended Lifetime | Rotation |
|------------|---------------------|----------|
| Access Token | 5-15 minutes | Frequent |
| Refresh Token | 7-30 days | On access token refresh |
| ID Token | Same as access token | N/A |

### Architecture Patterns

#### PATTERN-ARCH-001: Hexagonal Architecture

**Layer Responsibilities**:

```
┌─────────────────────────────────────────────────────────────────┐
│              Hexagonal Architecture Layers                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Domain Layer (Innermost):                                      │
│  • Entities - Business objects with identity and lifecycle      │
│  • Value Objects - Immutable, equality by value                  │
│  • Domain Services - Stateless business logic                  │
│  • Domain Events - Facts that occurred                          │
│  • Domain Errors - Business rule violations                    │
│  Dependencies: NONE                                              │
│                                                                  │
│  Application Layer:                                             │
│  • Use Cases - Application-specific business rules             │
│  • Application Services - Orchestration                        │
│  • Ports - Interfaces for external concerns                    │
│  • DTOs - Data transfer between layers                         │
│  Dependencies: Domain Layer                                      │
│                                                                  │
│  Adapter Layer (Outermost):                                   │
│  • Primary Adapters - Drive the application (CLI, HTTP)      │
│  • Secondary Adapters - Driven by application (DB, Email)    │
│  • Presenters - Format output for specific consumers           │
│  • Controllers - Handle input from primary adapters            │
│  Dependencies: Application Layer                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Testing Strategy**:

| Layer | Test Type | Mocking | Coverage Target |
|-------|-----------|---------|-----------------|
| Domain | Unit | None (pure functions) | 95%+ |
| Application | Unit | In-memory ports | 80%+ |
| Adapters | Integration | Real dependencies | 60%+ |
| E2E | System | Full stack | Critical paths |

**Dependency Verification**:

```bash
# Verify domain has no external dependencies
cargo tree -p phenotype-domain | grep -v "phenotype-domain"
# Should return nothing except standard library

# Verify application only depends on domain
cargo tree -p phenotype-application -i phenotype-domain

# Verify adapters depend on application
cargo tree -p phenotype-adapters -i phenotype-application
```

#### PATTERN-ARCH-002: CQRS (Command Query Responsibility Segregation)

**When to Use CQRS**:

| Factor | Use CQRS | Don't Use CQRS |
|--------|----------|----------------|
| Read/write ratio | > 10:1 | < 5:1 |
| Query complexity | Complex projections | Simple lookups |
| Scale requirements | Independent scaling needed | Uniform scaling OK |
| Team size | > 3 developers | Solo/small team |
| Data consistency | Eventual acceptable | Strong required |
| Experience level | Experienced with DDD | New to patterns |

**Synchronization Strategies**:

| Strategy | Latency | Consistency | Complexity |
|----------|---------|-------------|------------|
| Event Sourcing | Immediate | Strong | High |
| Transactional Outbox | < 1s | Eventual | Medium |
| Change Data Capture | < 1s | Eventual | Medium |
| Dual Write | Immediate | Weak | Low (risky) |

### Async Patterns

#### PATTERN-ASYNC-001: Event-Driven Architecture

**Event Types**:

| Type | Description | Example | Retention |
|------|-------------|---------|-----------|
| Domain Events | Business facts | OrderPlaced | 30 days |
| Integration Events | Cross-service | UserCreated | 7 days |
| Notification Events | UI updates | NewComment | 1 hour |
| Audit Events | Compliance | AccessGranted | 1 year |

**Delivery Guarantees**:

| Guarantee | Implementation | Use Case |
|-----------|----------------|----------|
| At-most-once | Fire-and-forget | Metrics, logging |
| At-least-once | Retry with deduplication | Email, notifications |
| Exactly-once | Idempotent consumers + dedup | Payments, inventory |

**Idempotency Implementation**:

```rust
pub struct IdempotentHandler<H, E> {
    handler: H,
    processed_store: Arc<dyn ProcessedEventStore>,
}

impl<H: EventHandler<E>, E: Event> EventHandler<E> for IdempotentHandler<H, E> {
    async fn handle(&self, event: E) -> Result<(), HandlerError> {
        let event_id = event.id();
        
        // Check if already processed
        if self.processed_store.exists(event_id).await? {
            trace!(event_id = %event_id, "Event already processed, skipping");
            return Ok(());
        }
        
        // Process with idempotency key
        let mut txn = self.processed_store.begin_transaction().await?;
        
        self.handler.handle(event).await?;
        txn.mark_processed(event_id).await?;
        txn.commit().await?;
        
        Ok(())
    }
}
```

#### PATTERN-ASYNC-002: Saga Pattern

**Saga Types**:

| Type | Coordination | Pros | Cons |
|------|--------------|------|------|
| Orchestration | Central coordinator | Easier to understand, monitor | Single point of logic |
| Choreography | Event-driven | Decentralized, loose coupling | Harder to trace |

**Compensation Strategy**:

| Step Type | Compensation | Example |
|-----------|------------|---------|
| CRUD | Reverse operation | Delete created record |
| External API | Call cancel/refund endpoint | Payment refund |
| Event publish | Publish compensating event | OrderCancelled |
| Notification | Send correction notification | Email update |

**Saga State Machine**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    Saga State Transitions                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    ┌─────────┐    start     ┌─────────┐                         │
│    │ PENDING │─────────────▶│ RUNNING │                         │
│    └─────────┘              └────┬────┘                         │
│                                    │                             │
│                    ┌───────────────┼───────────────┐            │
│                    │               │               │            │
│                    ▼               ▼               ▼            │
│               ┌─────────┐    ┌─────────┐    ┌─────────┐        │
│               │COMPLETED│    │COMPENSAT│    │  FAILED │        │
│               │         │◀───│   ING   │    │         │        │
│               └─────────┘    └────┬────┘    └─────────┘        │
│                                    │                             │
│                                    ▼                             │
│                              ┌─────────┐                         │
│                              │COMPENSAT│                         │
│                              │   ED    │                         │
│                              └─────────┘                         │
│                                                                  │
│  Transitions:                                                    │
│  • PENDING → RUNNING: Saga started                              │
│  • RUNNING → COMPLETED: All steps succeeded                     │
│  • RUNNING → FAILED: Step failed, no compensation               │
│  • RUNNING → COMPENSATING: Step failed, compensating            │
│  • COMPENSATING → COMPENSATED: Compensation complete            │
│  • COMPENSATING → FAILED: Compensation failed                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Caching Patterns

#### PATTERN-CACHE-001: Cache-Aside (Lazy Loading)

**Cache Stampede Prevention**:

| Strategy | Implementation | Trade-off |
|----------|----------------|-----------|
| **Locking** | Mutex per key | Slower, accurate |
| **Lease-based** | Soft TTL + background refresh | Complex |
| **Probabilistic early expiration** | Randomized TTL | Simple, effective |
| **Single-flight** | Deduplicate concurrent requests | Best practice |

```rust
use std::sync::Arc;
use tokio::sync::RwLock;
use dashmap::DashMap;

pub struct Cache<K, V> {
    store: DashMap<K, Arc<RwLock<CachedValue<V>>>>,
    loader: Arc<dyn Loader<K, V>>,
}

pub struct CachedValue<V> {
    value: V,
    expires_at: Instant,
}

impl<K: Eq + Hash + Clone, V: Clone> Cache<K, V> {
    pub async fn get(&self, key: &K) -> Result<V, CacheError> {
        // Fast path: check cache
        if let Some(entry) = self.store.get(key) {
            let cached = entry.read().await;
            if cached.expires_at > Instant::now() {
                return Ok(cached.value.clone());
            }
            // Value expired, drop read lock
        }
        
        // Slow path: acquire write lock and load
        let entry = self.store.entry(key.clone()).or_insert_with(|| {
            Arc::new(RwLock::new(CachedValue {
                value: V::default(),
                expires_at: Instant::now(),
            }))
        });
        
        let mut cached = entry.write().await;
        
        // Double-check after acquiring write lock
        if cached.expires_at > Instant::now() {
            return Ok(cached.value.clone());
        }
        
        // Load from source
        let value = self.loader.load(key).await?;
        cached.value = value.clone();
        cached.expires_at = Instant::now() + self.ttl;
        
        Ok(value)
    }
}
```

#### PATTERN-CACHE-002: Multi-Tier Caching

**Tier Configuration**:

| Tier | Technology | Size | Latency | Hit Ratio |
|------|------------|------|---------|-----------|
| L1 | dashmap/moka | 100MB | < 1μs | 60-70% |
| L2 | Redis | 1GB | < 1ms | 20-30% |
| L3 | PostgreSQL | 100GB | < 10ms | 5-10% |
| Source | External API | ∞ | < 100ms | < 5% |

**Eviction Policies by Tier**:

| Tier | Eviction Policy | Rationale |
|------|-----------------|-----------|
| L1 | LRU + TTL | Fast, predictable |
| L2 | LFU + TTL | Hot data identification |
| L3 | TTL-based | Persistence primary |

### Observability Patterns

#### PATTERN-OBS-001: Distributed Tracing

**Span Attributes Standard**:

| Attribute | Type | Example | Semantics |
|-----------|------|---------|-----------|
| `service.name` | string | "order-service" | Resource attribute |
| `service.version` | string | "1.2.3" | Deployment tracking |
| `deployment.environment` | string | "production" | Environment |
| `http.method` | string | "GET" | HTTP semantic |
| `http.url` | string | "/api/v1/orders" | Request path |
| `http.status_code` | int | 200 | Response status |
| `db.system` | string | "postgresql" | Database type |
| `db.statement` | string | "SELECT * FROM orders" | Query |
| `messaging.system` | string | "nats" | Message broker |
| `messaging.destination` | string | "orders.created" | Subject/topic |

**Sampling Configuration**:

```yaml
# OpenTelemetry Collector config
traces:
  sampling:
    # Head-based sampling (decision at root)
    probabilistic:
      ratio: 0.1  # 10% sampled
    
    # Tail-based sampling (decision after span complete)
    tail:
      policies:
        - name: errors
          type: status_code
          status_code: { status_codes: [ERROR] }
        - name: slow_requests
          type: latency
          latency: { threshold_ms: 1000 }
```

#### PATTERN-OBS-002: Structured Logging

**Log Levels Usage**:

| Level | Use For | Volume | Alert |
|-------|---------|--------|-------|
| ERROR | Failures requiring intervention | Low | Yes |
| WARN | Anomalies, degradations | Medium | Maybe |
| INFO | Business events, state changes | Medium | No |
| DEBUG | Detailed flow information | High | No |
| TRACE | Function entry/exit | Very High | No |

**Field Naming Convention**:

| Phenotype Name | OTel Equivalent | Example |
|----------------|-----------------|---------|
| `trace_id` | `trace_id` | "abc123def456" |
| `span_id` | `span_id` | "789xyz" |
| `service` | `service.name` | "order-service" |
| `operation` | `span.name` | "create_order" |
| `duration_ms` | `duration` | 45.2 |
| `error.type` | `exception.type` | "ValidationError" |
| `error.message` | `exception.message` | "Invalid email" |

### Database Patterns

#### PATTERN-DB-001: Repository Pattern

**Repository Interface Design**:

```rust
// Minimal, composable interfaces
#[async_trait::async_trait]
pub trait Reader<T, Id>: Send + Sync {
    async fn find_by_id(&self, id: &Id) -> Result<Option<T>, RepositoryError>;
    async fn find_many(&self, query: Query) -> Result<Vec<T>, RepositoryError>;
    async fn count(&self, query: Query) -> Result<u64, RepositoryError>;
}

#[async_trait::async_trait]
pub trait Writer<T, Id>: Send + Sync {
    async fn insert(&self, entity: &T) -> Result<(), RepositoryError>;
    async fn update(&self, entity: &T) -> Result<(), RepositoryError>;
    async fn delete(&self, id: &Id) -> Result<(), RepositoryError>;
}

// Combined trait for convenience
pub trait Repository<T, Id>: Reader<T, Id> + Writer<T, Id> {}
impl<R, T, Id> Repository<T, Id> for R where R: Reader<T, Id> + Writer<T, Id> {}

// Specialized traits for complex domains
#[async_trait::async_trait]
pub trait OrderRepository: Repository<Order, OrderId> {
    async fn find_by_customer(&self, customer_id: &CustomerId) -> Result<Vec<Order>, RepositoryError>;
    async fn find_pending(&self) -> Result<Vec<Order>, RepositoryError>;
    async fn update_status(&self, id: &OrderId, status: OrderStatus) -> Result<(), RepositoryError>;
}
```

**Query Object Pattern**:

```rust
pub struct OrderQuery {
    pub customer_id: Option<CustomerId>,
    pub status: Option<OrderStatus>,
    pub created_after: Option<DateTime<Utc>>,
    pub created_before: Option<DateTime<Utc>>,
    pub sort_by: SortField,
    pub sort_order: SortOrder,
    pub pagination: Pagination,
}

impl OrderQuery {
    pub fn builder() -> OrderQueryBuilder {
        OrderQueryBuilder::default()
    }
}

pub struct OrderQueryBuilder {
    // ... fields
}

impl OrderQueryBuilder {
    pub fn for_customer(mut self, id: CustomerId) -> Self {
        self.customer_id = Some(id);
        self
    }
    
    pub fn with_status(mut self, status: OrderStatus) -> Self {
        self.status = Some(status);
        self
    }
    
    pub fn build(self) -> OrderQuery {
        OrderQuery { /* ... */ }
    }
}

// Usage
let query = OrderQuery::builder()
    .for_customer(customer_id)
    .with_status(OrderStatus::Pending)
    .created_after(Utc::now() - Duration::days(30))
    .build();

let orders = repo.find_many(query).await?;
```

#### PATTERN-DB-002: Unit of Work

**Transaction Boundaries**:

| Scope | Example | Use Case |
|-------|---------|----------|
| Request | HTTP request handler | API endpoint |
| Use Case | Business operation | Create order with payment |
| Saga | Distributed transaction | Order fulfillment flow |

**Implementation with Events**:

```rust
pub struct UnitOfWork<'a> {
    transaction: sqlx::Transaction<'a, sqlx::Postgres>,
    events: Vec<DomainEvent>,
}

impl<'a> UnitOfWork<'a> {
    pub fn record_event(&mut self, event: DomainEvent) {
        self.events.push(event);
    }
    
    pub async fn commit(self) -> Result<Vec<DomainEvent>, Error> {
        self.transaction.commit().await?;
        Ok(self.events)
    }
    
    pub async fn rollback(self) -> Result<(), Error> {
        self.transaction.rollback().await?;
        Ok(())
    }
}

// Use case implementation
pub async fn create_order(
    uow: &mut UnitOfWork<'_>,
    cmd: CreateOrderCommand,
) -> Result<Order, DomainError> {
    let order = Order::create(cmd)?;
    
    let order_repo = OrderRepository::new(&mut uow.transaction);
    order_repo.save(&order).await?;
    
    // Record event for outbox pattern
    uow.record_event(DomainEvent::OrderCreated {
        order_id: order.id(),
        customer_id: order.customer_id(),
        total: order.total(),
    });
    
    // Publish integration event
    uow.record_event(DomainEvent::OrderSubmittedForPayment {
        order_id: order.id(),
        payment_method: order.payment_method(),
        amount: order.total(),
    });
    
    Ok(order)
}
```

### Testing Patterns

#### PATTERN-TEST-001: Test Pyramid

**Test Distribution by Type**:

| Layer | % of Tests | Execution Time | Tools |
|-------|-----------|----------------|-------|
| Unit | 70% | < 100ms | Built-in test runner |
| Integration | 20% | < 1s | Testcontainers |
| Contract | 5% | < 10s | Pact |
| E2E | 5% | < 1min | Playwright |

**Test Isolation Levels**:

| Isolation | Speed | Confidence | Use For |
|-----------|-------|------------|---------|
| Pure (no I/O) | Instant | Logic only | Domain logic |
| In-memory | Fast | High | Repository ports |
| Container | Medium | Very High | Database adapters |
| Full environment | Slow | Full system | Critical flows |

#### PATTERN-TEST-002: Property-Based Testing

**Property Categories**:

| Category | Example | Generator |
|----------|---------|-----------|
| Algebraic laws | `reverse(reverse(x)) == x` | List of elements |
| Round-trip | `parse(serialize(x)) == x` | Valid instances |
| Idempotency | `process(x) == process(process(x))` | Any input |
| Invariants | `order.total() == sum(items)` | Valid orders |
| State machine | Workflow transitions | Valid commands |

**Shrinking Strategy**:

```rust
// proptest will automatically shrink failing cases
proptest! {
    #[test]
    fn sum_of_list_equals_fold(
        numbers in prop::collection::vec(-1000..1000, 0..1000)
    ) {
        let sum1: i32 = numbers.iter().sum();
        let sum2: i32 = numbers.iter().fold(0, |a, b| a + b);
        assert_eq!(sum1, sum2);
    }
}

// If fails with [1, 2, 3, -5000, 5], will shrink to:
// [1, 2, 3, -5000, 5] → [ -5000 ] → minimal case
```

### CLI Patterns

#### PATTERN-CLI-001: Command Structure

**Command Hierarchy**:

```
helios [global options] <command> [subcommand] [args] [command options]

Commands:
  init        Initialize a new spec-driven project
    ├── project <name>      Create new project
    └── spec <name>         Create new spec
    
  validate    Validate spec compliance
    ├── all                 Validate all specs
    └── spec <id>           Validate specific spec
    
  generate    Generate code from specs
    ├── all                 Generate all
    ├── rust                Generate Rust code
    └── typescript          Generate TypeScript code
    
  run         Execute workflows
    ├── workflow <name>     Run specific workflow
    └── step <id>           Run specific step
    
  pattern     Pattern operations
    ├── search <query>      Search patterns
    ├── view <id>           View pattern details
    └── apply <id>          Apply pattern to project
```

**Error Handling**:

| Exit Code | Meaning | User Action |
|-----------|---------|-------------|
| 0 | Success | None |
| 1 | General error | Check error message |
| 2 | Invalid arguments | Check --help |
| 3 | Validation failed | Review spec compliance |
| 4 | Generation failed | Check template exists |
| 5 | Network error | Check connectivity |
| 6 | Permission denied | Check file permissions |

## Anti-Pattern Catalog

### Security Anti-Patterns

#### ANTI-PATTERN-SEC-001: Hardcoded Secrets

**Severity**: Critical  
**Detection**: Static analysis  
**Fix Complexity**: Simple

**Vulnerable Code**:
```rust
// BAD: Hardcoded API key
const API_KEY: &str = "sk-1234567890abcdef";

async fn call_api() {
    let client = reqwest::Client::new();
    let response = client
        .post("https://api.example.com/v1/data")
        .header("Authorization", format!("Bearer {}", API_KEY))
        .send()
        .await;
}
```

**Secure Code**:
```rust
// GOOD: Load from environment
use std::env;

fn get_api_key() -> Result<String, env::VarError> {
    env::var("API_KEY")
}

async fn call_api() -> Result<(), AppError> {
    let api_key = get_api_key()
        .map_err(|_| AppError::MissingApiKey)?;
    
    // Validate key format
    if !is_valid_key_format(&api_key) {
        return Err(AppError::InvalidApiKey);
    }
    
    // Use the key
    let client = reqwest::Client::new();
    let response = client
        .post("https://api.example.com/v1/data")
        .header("Authorization", format!("Bearer {}", api_key))
        .send()
        .await?;
    
    Ok(())
}
```

**Prevention**:
- Use `cargo-deny` to check for secrets
- CI/CD secret scanning (GitHub secret scanning)
- Pre-commit hooks with `detect-secrets`

#### ANTI-PATTERN-SEC-002: SQL Injection

**Severity**: Critical  
**Detection**: Static analysis, runtime  
**Fix Complexity**: Simple

**Vulnerable Code**:
```rust
// BAD: String concatenation
async fn get_user(pool: &PgPool, user_id: &str) -> Result<User, Error> {
    let query = format!("SELECT * FROM users WHERE id = '{}'", user_id);
    // Attacker can pass: "'; DROP TABLE users; --"
    sqlx::query_as(&query).fetch_one(pool).await
}
```

**Secure Code**:
```rust
// GOOD: Parameterized query
async fn get_user(pool: &PgPool, user_id: &str) -> Result<User, Error> {
    sqlx::query_as::<_, User>(
        "SELECT id, email, name FROM users WHERE id = $1"
    )
    .bind(user_id)  // Properly escaped
    .fetch_one(pool)
    .await
}
```

### Performance Anti-Patterns

#### ANTI-PATTERN-PERF-001: N+1 Query Problem

**Severity**: High  
**Detection**: Runtime profiling  
**Fix Complexity**: Moderate

**Problem Code**:
```rust
// BAD: N+1 queries
async fn get_orders_with_items(pool: &PgPool) -> Result<Vec<Order>, Error> {
    let orders = sqlx::query_as::<_, Order>("SELECT * FROM orders")
        .fetch_all(pool)
        .await?;
    
    for order in &mut orders {
        // One query per order!
        let items = sqlx::query_as::<_, OrderItem>(
            "SELECT * FROM order_items WHERE order_id = $1"
        )
        .bind(order.id)
        .fetch_all(pool)
        .await?;
        order.items = items;
    }
    
    Ok(orders)
}
// 100 orders = 101 queries!
```

**Solution**:
```rust
// GOOD: Single query with JOIN
async fn get_orders_with_items(pool: &PgPool) -> Result<Vec<Order>, Error> {
    let rows = sqlx::query_as::<_, OrderWithItemRow>(
        r#"
        SELECT 
            o.id as order_id,
            o.customer_id,
            o.total,
            oi.id as item_id,
            oi.product_id,
            oi.quantity,
            oi.unit_price
        FROM orders o
        LEFT JOIN order_items oi ON o.id = oi.order_id
        "#
    )
    .fetch_all(pool)
    .await?;
    
    // Group rows into orders
    let orders = group_rows_into_orders(rows);
    Ok(orders)
}
// 100 orders = 1 query!
```

## Guidelines Catalog

### Rust Guidelines

#### GUIDELINE-RUST-001: Error Handling

**The Rule**: Use `thiserror` for library errors, `anyhow` for application errors.

**Library (thiserror)**:
```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum DomainError {
    #[error("User not found: {0}")]
    UserNotFound(UserId),
    
    #[error("Invalid email format: {0}")]
    InvalidEmail(String),
    
    #[error("Repository error: {0}")]
    Repository(#[from] sqlx::Error),
}
```

**Application (anyhow)**:
```rust
use anyhow::{Context, Result};

fn process_file(path: &Path) -> Result<()> {
    let content = std::fs::read_to_string(path)
        .with_context(|| format!("Failed to read {}", path.display()))?;
    
    let data = parse(&content)
        .context("Failed to parse file content")?;
    
    save(data)
        .context("Failed to save processed data")?;
    
    Ok(())
}
```

#### GUIDELINE-RUST-002: Async Patterns

**The Rule**: Prefer structured concurrency, avoid `spawn` without handle.

**Good**:
```rust
use tokio::task::JoinSet;

async fn process_items(items: Vec<Item>) -> Result<Vec<Result>> {
    let mut set = JoinSet::new();
    
    for item in items {
        set.spawn(async move {
            process(item).await
        });
    }
    
    let mut results = Vec::new();
    while let Some(res) = set.join_next().await {
        results.push(res??);
    }
    
    Ok(results)
}
```

**Bad**:
```rust
async fn process_items(items: Vec<Item>) {
    for item in items {
        tokio::spawn(async move {
            process(item).await  // Fire and forget - errors lost!
        });
    }
}
```

### Go Guidelines

#### GUIDELINE-GO-001: Error Wrapping

**The Rule**: Wrap errors with context at boundaries.

```go
package main

import (
    "fmt"
    "os"
)

func readConfig(path string) (*Config, error) {
    data, err := os.ReadFile(path)
    if err != nil {
        return nil, fmt.Errorf("reading config file: %w", err)
    }
    
    cfg, err := parseConfig(data)
    if err != nil {
        return nil, fmt.Errorf("parsing config from %s: %w", path, err)
    }
    
    return cfg, nil
}
```

## Methodology Specifications

### METHODOLOGY-001: TDD (Test-Driven Development)

**The Cycle**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    TDD Cycle (Red-Green-Refactor)              │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│    ┌─────────┐     Write failing test     ┌─────────┐          │
│    │  GREEN  │◀────────────────────────────│   RED   │          │
│    │  ✓     │                             │  ✗     │          │
│    └────┬────┘                             └────┬────┘          │
│         │                                      │               │
│         │  Refactor                            │               │
│         │  (keep green)                        │               │
│         │                                      │               │
│         └──────────────────────────────────────┘               │
│                    Make test pass                               │
│                                                                  │
│  Rules:                                                         │
│  1. Write no production code except to pass a failing test    │
│  2. Write only enough of a test to demonstrate a failure      │
│  3. Write only enough production code to pass the test        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**TDD in Hexagonal Architecture**:

| Layer | Test Approach | Example |
|-------|---------------|---------|
| Domain | Pure function tests | `order.total() == sum(items)` |
| Application | Port mocking | Mock repository, test use case |
| Adapters | Integration tests | Real database, test repository |

### METHODOLOGY-002: BDD (Behavior-Driven Development)

**Gherkin Format**:

```gherkin
Feature: Order Processing
  As a customer
  I want to place orders
  So that I can purchase products

  Scenario: Successful order placement
    Given a customer with id "cust-123" exists
    And the following products are in stock:
      | product_id | name    | price | quantity |
      | prod-1     | Widget  | 9.99  | 100      |
    When the customer places an order with:
      | product_id | quantity |
      | prod-1     | 2        |
    Then the order should be created with status "PENDING"
    And the total should be 19.98
    And an "OrderCreated" event should be published
    And the stock for "prod-1" should be 98

  Scenario: Order with insufficient stock
    Given a customer with id "cust-123" exists
    And the product "prod-1" has 1 item in stock
    When the customer attempts to order 5 of "prod-1"
    Then the order should be rejected with error "InsufficientStock"
    And no order should be created
```

### METHODOLOGY-003: SDD (Spec-Driven Development)

**The Workflow**:

```
┌─────────────────────────────────────────────────────────────────┐
│                    SDD Workflow                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. SPECIFICATION PHASE                                          │
│     ├── Identify requirement                                     │
│     ├── Write SPEC.md with:                                     │
│     │   • ASCII architecture                                     │
│     │   • Components table                                       │
│     │   • Data models                                            │
│     │   • Dependencies                                           │
│     │   • Interface definitions                                  │
│     └── Create ADR if architectural decision needed            │
│                                                                  │
│  2. VALIDATION PHASE                                             │
│     ├── Review spec with stakeholders                           │
│     ├── Update spec based on feedback                           │
│     └── Mark spec as "specified"                                │
│                                                                  │
│  3. IMPLEMENTATION PHASE                                        │
│     ├── Run `pheno generate` to create scaffolding             │
│     ├── Implement domain logic (TDD)                            │
│     ├── Implement adapters                                      │
│     └── Update spec status to "implemented"                      │
│                                                                  │
│  4. VERIFICATION PHASE                                           │
│     ├── Run `pheno validate` to check compliance               │
│     ├── Update spec with actual metrics                          │
│     └── Mark spec as "validated"                                │
│                                                                  │
│  5. DEPLOYMENT PHASE                                             │
│     ├── Deploy to staging                                       │
│     ├── Run E2E tests                                           │
│     └── Deploy to production                                    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Checklist Templates

### CHECKLIST-001: Pre-Deployment

```markdown
# Pre-Deployment Checklist

## Code Quality
- [ ] All tests passing (unit, integration, E2E)
- [ ] Code coverage > 80%
- [ ] No clippy warnings
- [ ] No security audit failures (`cargo audit`)
- [ ] No outdated dependencies (`cargo outdated`)

## Documentation
- [ ] SPEC.md updated with actual metrics
- [ ] ADR created for any new decisions
- [ ] API documentation updated
- [ ] README updated if needed

## Observability
- [ ] Metrics exposed
- [ ] Health check endpoint working
- [ ] Tracing configured
- [ ] Alerting rules in place

## Security
- [ ] No hardcoded secrets
- [ ] Dependencies scanned
- [ ] Authentication tested
- [ ] Authorization rules tested

## Performance
- [ ] Load tests passing
- [ ] Response times within SLA
- [ ] Resource usage acceptable
- [ ] Database queries optimized

## Database
- [ ] Migrations tested
- [ ] Rollback plan documented
- [ ] Backup verified
- [ ] No breaking schema changes without plan

## Deployment
- [ ] Feature flags configured
- [ ] Rollback procedure documented
- [ ] Monitoring dashboard ready
- [ ] On-call engineer notified
```

---

## Compliance Matrix

### Pattern Compliance by Repository

| Repository | Hexagonal | TDD | BDD | SDD | Status |
|------------|-----------|-----|-----|-----|--------|
| heliosCLI | ✓ | ✓ | ○ | ✓ | Certified |
| thegent | ✓ | ✓ | ○ | ✓ | Certified |
| portage | ✓ | ✓ | ○ | ✓ | In Review |
| AgilePlus | ✓ | ✓ | ✓ | ✓ | Certified |
| heliosApp | ○ | ✓ | ✓ | ✓ | In Progress |

Legend: ✓ Full compliance, ○ Partial, - Not applicable

---

## Migration Guide

### From Legacy to Hexagonal

**Phase 1: Identify Boundaries**
1. Map current dependencies
2. Identify domain logic
3. Locate I/O operations

**Phase 2: Extract Domain**
1. Move pure functions to domain/
2. Define entities and value objects
3. Write unit tests (no mocks)

**Phase 3: Define Ports**
1. Extract interfaces for external deps
2. Move to application/ports.rs
3. Update use cases to use ports

**Phase 4: Create Adapters**
1. Move implementations to adapters/
2. Implement port interfaces
3. Write integration tests

**Phase 5: Verify**
1. Run full test suite
2. Verify dependency direction
3. Architecture tests pass

---

*Generated: 2026-04-04*  
*Version: 1.0.0*  
*Status: Specified*  
*Next Review: 2026-07-04*