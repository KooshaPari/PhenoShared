# Architecture Decision Records (ADR)

> **Project:** PhenoObservability/logctx  
> **Status:** Active  
> **Last Updated:** 2024

---

## 1. Introduction

### What are ADRs?

Architecture Decision Records (ADRs) capture important architectural decisions made during the development of the PhenoObservability logctx component. Each ADR describes:

- **Context**: The situation that requires a decision
- **Problem**: The specific challenge or question to address
- **Decision**: The chosen approach
- **Consequences**: The outcomes, both positive and negative
- **Status**: Current state (proposed, accepted, deprecated, superseded)

### Why ADRs Matter

1. **Knowledge Preservation**: Document reasoning that might otherwise be lost
2. **Onboarding**: Help new team members understand system design
3. **Transparency**: Make decision-making visible to stakeholders
4. **Consistency**: Guide future decisions with historical context
5. **Accountability**: Track who made decisions and when

### ADR Lifecycle

```
Proposed → Accepted → [Deprecated] → Superseded
              ↓
           Rejected
```

- **Proposed**: ADR is submitted for review
- **Accepted**: Decision is ratified by team consensus
- **Rejected**: Decision is declined
- **Deprecated**: Decision is no longer relevant
- **Superseded**: Decision has been replaced by a newer ADR

---

## 2. ADR Index

### Active Decisions

| ID | Title | Status | Date | Author | Tags |
|----|-------|--------|------|--------|------|
| 001 | [Structured Logging Format](adrs/001-structured-logging.md) | ✅ Accepted | 2024-Q1 | Team | #logging #json |
| 002 | [Context Propagation](adrs/002-context-propagation.md) | ✅ Accepted | 2024-Q1 | Core Team | #context #async |
| 003 | [Log Levels and Severity](adrs/003-log-levels.md) | ✅ Accepted | 2024-Q1 | Core Team | #levels #severity |
| 004 | [Field Naming Conventions](adrs/004-field-naming.md) | ✅ Accepted | 2024-Q2 | Architecture | #naming #conventions |
| 005 | [Async Logging](adrs/005-async-logging.md) | ✅ Accepted | 2024-Q2 | Core Team | #async #performance |
| 006 | [Correlation ID Integration](adrs/006-correlation-ids.md) | ✅ Accepted | 2024-Q2 | Core Team | #tracing #ids |
| 007 | [Sensitive Data Handling](adrs/007-sensitive-data.md) | ✅ Accepted | 2024-Q2 | Security | #security #pii |
| 008 | [Log Output Destinations](adrs/008-log-destinations.md) | ✅ Accepted | 2024-Q3 | Core Team | #output #files |
| 009 | [Rotation and Retention](adrs/009-rotation-retention.md) | ✅ Accepted | 2024-Q3 | Ops Team | #rotation #retention |
| 010 | [Context Scopes](adrs/010-context-scopes.md) | 📝 Proposed | 2024-Q4 | Architecture | #scopes #hierarchy |

### Deprecated/Superseded

| ID | Title | Status | Superseded By |
|----|-------|--------|---------------|
| - | *No deprecated ADRs yet* | - | - |

---

## 3. Decision Drivers Summary

### Performance
- Minimal allocation overhead
- Lock-free operations where possible
- Efficient serialization
- Async I/O

### Observability
- Rich contextual information
- Correlation with traces
- Queryable fields
- Structured output

### Security & Privacy
- PII redaction
- Configurable field filtering
- Secure defaults
- Audit compliance

### Developer Experience
- Easy to use API
- Clear documentation
- Good defaults
- Compile-time safety

### Operations
- Configurable at runtime
- Multiple output formats
- Log rotation
- Backpressure handling

---

## 4. ADR Categories

### 📝 Logging Core (ADR-001 to ADR-010)
Core logging functionality decisions.

**Key Topics:**
- Log entry format
- Severity levels
- Message templating
- Timestamp handling

### 🔄 Context (ADR-011 to ADR-020)
Context propagation and management.

**Key Topics:**
- Context storage
- Async task propagation
- Thread-local vs task-local
- Context inheritance

### 🔗 Correlation (ADR-021 to ADR-030)
Correlation with other observability signals.

**Key Topics:**
- Trace ID inclusion
- Span context
- Request correlation
- Distributed tracking

### 🔒 Security (ADR-031 to ADR-040)
Security and privacy considerations.

**Key Topics:**
- PII detection
- Field redaction
- Encryption
- Access control

### ⚙️ Configuration (ADR-041 to ADR-050)
Configuration and customization.

**Key Topics:**
- Environment-based config
- Dynamic reloading
- Feature flags
- Filtering rules

### 📤 Output (ADR-051 to ADR-060)
Output handling and destinations.

**Key Topics:**
- File output
- Console output
- Network sinks
- Buffering strategies

---

## 5. How to Contribute New ADRs

### Before Writing an ADR

1. **Discuss First**: Open a GitHub issue or discussion to gauge interest
2. **Check Existing**: Ensure no existing ADR covers the same decision
3. **Gather Context**: Collect requirements, constraints, and options

### Writing Process

1. **Use the Template**: Copy from [templates/adr-template.md](templates/adr-template.md)
2. **Be Concise**: Focus on the decision and its context
3. **Include Options**: Document alternatives considered
4. **Be Honest**: Acknowledge trade-offs and negative consequences

### Submission Checklist

- [ ] Uses the standard ADR template
- [ ] Assigned a sequential ID
- [ ] Status set to "Proposed"
- [ ] All sections completed
- [ ] Linked in the index above
- [ ] PR submitted with clear description

### Review Process

```
1. Author submits PR with ADR in "Proposed" status
2. Maintainers review within 5 business days
3. Community feedback period (3 days minimum)
4. Decision: Accept, Request Changes, or Reject
5. If accepted, merge and update index
```

### ADR Format Requirements

**File Naming**: `XXX-descriptive-title.md`
- Three-digit sequential number (001, 002, etc.)
- Lowercase words separated by hyphens
- Place in `adrs/` directory

**Required Sections**:
1. Title and metadata
2. Context
3. Decision
4. Consequences
5. Status
6. References (optional)

---

## 6. Templates

### Standard ADR Template

```markdown
# ADR-XXX: [Title]

- **Status**: Proposed | Accepted | Rejected | Deprecated | Superseded by ADR-YYY
- **Date**: YYYY-MM-DD
- **Author**: [Name](mailto:email@example.com)
- **Tags**: #tag1 #tag2

## Context

What is the issue that we're seeing that is motivating this decision or change?

## Decision

What is the change that we're proposing or have agreed to implement?

## Consequences

What becomes easier or more difficult to do and any risks introduced by the change?

### Positive

- Benefit 1
- Benefit 2

### Negative

- Drawback 1
- Drawback 2

## Alternatives Considered

### Alternative A: [Name]

Description and why it was rejected.

### Alternative B: [Name]

Description and why it was rejected.

## References

- Link 1
- Link 2
```

### Lightweight ADR Template (for minor decisions)

```markdown
# ADR-XXX: [Title]

- **Status**: Accepted
- **Date**: YYYY-MM-DD
- **Author**: [Name]
- **Impact**: Low

## Decision

Brief description of the decision.

## Rationale

Why this decision was made.

## Consequences

- Impact 1
- Impact 2
```

### Logging ADR Template (for logging decisions)

```markdown
# ADR-XXX: [Title]

- **Status**: Proposed
- **Date**: YYYY-MM-DD
- **Author**: [Name]
- **Log Impact**: Format | Context | Performance | Security

## Current Implementation

How logging currently works.

## Proposed Change

What will change in the logging system.

## Compatibility

Breaking changes and migration path.

## Performance Impact

Benchmarks or expected overhead.

## Security Considerations

PII, sensitive data, or audit implications.
```

---

## 7. Best Practices

### Do's

✅ **Focus on decisions, not just documentation**  
ADRs record why we chose a particular approach, not just what the approach is.

✅ **Write them when the decision is fresh**  
Capture context while it's still in recent memory.

✅ **Include the "why"**  
Explain the reasoning behind the decision, not just the outcome.

✅ **Be honest about trade-offs**  
Every decision has downsides. Acknowledge them.

✅ **Keep them immutable once accepted**  
Don't edit accepted ADRs; supersede them with new ones instead.

✅ **Make them discoverable**  
Link from README, index, and relevant code comments.

### Don'ts

❌ **Don't use ADRs for trivial decisions**  
Not every code change needs an ADR. Reserve them for significant architectural choices.

❌ **Don't let them become outdated**  
Update the status when decisions change.

❌ **Don't write them in isolation**  
Discuss significant decisions with the team before documenting.

❌ **Don't make them overly long**  
Aim for 1-2 pages. Longer ADRs may indicate scope creep.

---

## 8. Glossary

| Term | Definition |
|------|------------|
| **ADR** | Architecture Decision Record |
| **PII** | Personally Identifiable Information |
| **Async** | Asynchronous execution |
| **Context** | Request-scoped metadata |
| **Correlation ID** | Identifier linking related operations |
| **Structured Logging** | Machine-readable log format |
| **Severity** | Log level (DEBUG, INFO, WARN, ERROR) |
| **Span** | Unit of work in distributed tracing |
| **Trace** | Collection of spans |
| **Scope** | Hierarchical context boundary |

---

## 9. Related Resources

- [Architecture Decision Records (ADR)](https://adr.github.io/)
- [Documenting Architecture Decisions](http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions)
- [OpenTelemetry Logging](https://opentelemetry.io/docs/specs/otel/logs/)
- [LogCtx SPEC.md](./SPEC.md)
- [Parent Observability ADR](../ADR.md)

---

## 10. Maintenance

**ADR Shepherd**: Core Team  
**Review Schedule**: Monthly  
**Last Full Review**: 2024-Q4

---

*This index is automatically updated. Please submit a PR to add new ADRs or update existing ones.*
