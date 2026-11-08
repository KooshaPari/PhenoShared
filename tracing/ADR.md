# Architecture Decision Records (ADR)

> **Project:** PhenoObservability/tracing  
> **Status:** Active  
> **Last Updated:** 2024

---

## 1. Introduction

### What are ADRs?

Architecture Decision Records (ADRs) capture important architectural decisions made during the development of the PhenoObservability tracing component. Each ADR describes:

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
| 001 | [OpenTelemetry Tracing SDK](adrs/001-otel-tracing.md) | ✅ Accepted | 2024-Q1 | Team | #otel #sdk |
| 002 | [Span Processing Strategy](adrs/002-span-processing.md) | ✅ Accepted | 2024-Q1 | Core Team | #spans #batch |
| 003 | [Sampling Algorithms](adrs/003-sampling-algorithms.md) | ✅ Accepted | 2024-Q1 | Core Team | #sampling #performance |
| 004 | [Context Propagation](adrs/004-context-propagation.md) | ✅ Accepted | 2024-Q2 | Architecture | #context #headers |
| 005 | [Span Exporters](adrs/005-span-exporters.md) | ✅ Accepted | 2024-Q2 | Core Team | #export #otlp |
| 006 | [Instrumentation Libraries](adrs/006-instrumentation.md) | ✅ Accepted | 2024-Q2 | Core Team | #auto-instrumentation |
| 007 | [Trace ID Generation](adrs/007-trace-ids.md) | ✅ Accepted | 2024-Q2 | Architecture | #w3c #random |
| 008 | [Baggage Handling](adrs/008-baggage.md) | ✅ Accepted | 2024-Q3 | Core Team | #baggage #propagation |
| 009 | [Resource Attributes](adrs/009-resource-attributes.md) | ✅ Accepted | 2024-Q3 | Core Team | #resources #metadata |
| 010 | [Span Events vs Logs](adrs/010-span-events.md) | 📝 Proposed | 2024-Q4 | Architecture | #events #logs |

### Deprecated/Superseded

| ID | Title | Status | Superseded By |
|----|-------|--------|---------------|
| - | *No deprecated ADRs yet* | - | - |

---

## 3. Decision Drivers Summary

### Performance & Overhead
- Minimal latency impact (< 1%)
- Efficient span batching
- Low memory footprint
- Async processing

### Standards Compliance
- OpenTelemetry specification
- W3C Trace Context
- W3C Baggage
- OTLP protocol

### Observability
- Complete trace visibility
- Root cause analysis
- Performance profiling
- Error tracking

### Scalability
- Handle high throughput
- Distributed architecture
- Efficient storage
- Fast queries

### Developer Experience
- Easy instrumentation
- Minimal code changes
- Clear documentation
- Good defaults

---

## 4. ADR Categories

### 📊 Core Tracing (ADR-001 to ADR-010)
Core tracing infrastructure decisions.

**Key Topics:**
- Span creation
- Trace context
- Propagation formats
- Span processors

### 🎯 Sampling (ADR-011 to ADR-020)
Sampling strategies and configurations.

**Key Topics:**
- Head-based sampling
- Tail-based sampling
- Rate limiting
- Adaptive sampling

### 📤 Export (ADR-021 to ADR-030)
Span export and delivery decisions.

**Key Topics:**
- OTLP protocol
- Retry strategies
- Buffering
- Compression

### 🔌 Instrumentation (ADR-031 to ADR-040)
Auto and manual instrumentation.

**Key Topics:**
- Library instrumentation
- Framework integration
- Custom spans
- Semantic conventions

### 🔍 Analysis (ADR-041 to ADR-050)
Trace analysis and visualization.

**Key Topics:**
- Trace querying
- Dependency graphs
- Latency histograms
- Error analysis

### ⚙️ Configuration (ADR-051 to ADR-060)
Configuration and deployment.

**Key Topics:**
- Environment variables
- Dynamic config
- Feature flags
- Defaults

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

### Tracing ADR Template (for tracing decisions)

```markdown
# ADR-XXX: [Title]

- **Status**: Proposed
- **Date**: YYYY-MM-DD
- **Author**: [Name]
- **OTel Impact**: Span | Context | Export | SDK

## Current Behavior

How tracing currently works in this area.

## Proposed Change

What will change in the tracing flow.

## Performance Impact

Expected overhead or improvement.

## Compatibility

OTel spec compliance and breaking changes.

## Migration

How users should update their code.
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
| **OTel** | OpenTelemetry |
| **OTLP** | OpenTelemetry Protocol |
| **Span** | A single operation within a trace |
| **Trace** | A collection of spans forming a request flow |
| **Context** | Metadata propagated across service boundaries |
| **Baggage** | User-defined key-value pairs in context |
| **Sampling** | Selecting which traces to record |
| **Exporter** | Component sending data to backends |
| **W3C** | World Wide Web Consortium standards |

---

## 9. Related Resources

- [Architecture Decision Records (ADR)](https://adr.github.io/)
- [Documenting Architecture Decisions](http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions)
- [OpenTelemetry Tracing](https://opentelemetry.io/docs/concepts/signals/traces/)
- [W3C Trace Context](https://www.w3.org/TR/trace-context/)
- [Tracing SPEC.md](./SPEC.md)
- [Parent Observability ADR](../ADR.md)

---

## 10. Maintenance

**ADR Shepherd**: Core Team  
**Review Schedule**: Monthly  
**Last Full Review**: 2024-Q4

---

*This index is automatically updated. Please submit a PR to add new ADRs or update existing ones.*
