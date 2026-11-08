# Architecture Decision Records (ADR)

> **Project:** PhenoObservability/dashboards  
> **Status:** Active  
> **Last Updated:** 2024

---

## 1. Introduction

### What are ADRs?

Architecture Decision Records (ADRs) capture important architectural decisions made during the development of the PhenoObservability dashboards component. Each ADR describes:

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
| 001 | [Grafana as Primary Platform](adrs/001-grafana-platform.md) | ✅ Accepted | 2024-Q1 | Team | #grafana #platform |
| 002 | [Dashboard as Code](adrs/002-dashboard-as-code.md) | ✅ Accepted | 2024-Q1 | Core Team | #iac #jsonnet |
| 003 | [Standard Panel Library](adrs/003-panel-library.md) | ✅ Accepted | 2024-Q1 | Core Team | #panels #reusable |
| 004 | [Variable Templating](adrs/004-variable-templating.md) | ✅ Accepted | 2024-Q2 | Architecture | #variables #templating |
| 005 | [Alert Panel Integration](adrs/005-alert-panels.md) | ✅ Accepted | 2024-Q2 | Core Team | #alerts #visualization |
| 006 | [Dark Mode Default](adrs/006-dark-mode.md) | ✅ Accepted | 2024-Q2 | UX Team | #theme #dark |
| 007 | [Responsive Layout](adrs/007-responsive-layout.md) | ✅ Accepted | 2024-Q2 | UX Team | #responsive #mobile |
| 008 | [Dashboard Versioning](adrs/008-versioning.md) | ✅ Accepted | 2024-Q3 | Core Team | #git #versioning |
| 009 | [Cross-Dashboard Linking](adrs/009-cross-linking.md) | ✅ Accepted | 2024-Q3 | UX Team | #navigation #links |
| 010 | [Annotation Standards](adrs/010-annotations.md) | 📝 Proposed | 2024-Q4 | Architecture | #annotations #events |

### Deprecated/Superseded

| ID | Title | Status | Superseded By |
|----|-------|--------|---------------|
| - | *No deprecated ADRs yet* | - | - |

---

## 3. Decision Drivers Summary

### User Experience
- Intuitive navigation
- Consistent visual language
- Fast loading times
- Mobile accessibility

### Maintainability
- Dashboard as code
- Version control integration
- Reusable components
- Automated testing

### Scalability
- Support for high cardinality
- Efficient queries
- Caching strategies
- Resource optimization

### Standardization
- Consistent panel types
- Standardized layouts
- Common color schemes
- Uniform time ranges

### Integration
- Multi-data source support
- Alert correlation
- External link embedding
- API accessibility

---

## 4. ADR Categories

### 📊 Visualization (ADR-001 to ADR-010)
Dashboard visualization and design decisions.

**Key Topics:**
- Panel types
- Chart selection
- Color schemes
- Layout grids

### 🎨 UX/UI (ADR-011 to ADR-020)
User experience and interface decisions.

**Key Topics:**
- Navigation patterns
- Responsive design
- Accessibility
- Theme support

### 🔧 Configuration (ADR-021 to ADR-030)
Dashboard configuration and management.

**Key Topics:**
- Variables and templating
- Data source config
- Permissions
- Provisioning

### 📈 Metrics (ADR-031 to ADR-040)
Metrics visualization and query decisions.

**Key Topics:**
- PromQL queries
- Aggregation
- Time ranges
- Legends

### 🔗 Integration (ADR-041 to ADR-050)
Integration with other systems.

**Key Topics:**
- Data sources
- External links
- Embedded content
- API access

### ⚙️ Operations (ADR-051 to ADR-060)
Operational and deployment decisions.

**Key Topics:**
- Dashboard deployment
- Backup and restore
- Performance tuning
- Scaling

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

### Dashboard ADR Template (for dashboard decisions)

```markdown
# ADR-XXX: [Title]

- **Status**: Proposed
- **Date**: YYYY-MM-DD
- **Author**: [Name]
- **Dashboard Impact**: Layout | Panel | Query | UX

## Current State

How dashboards currently work.

## Proposed Change

What will change in the dashboard system.

## Visual Impact

Screenshots or mockups if applicable.

## User Impact

How this affects dashboard users.

## Migration

Steps to update existing dashboards.
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
| **Dashboard** | Visual data representation |
| **Panel** | Individual visualization unit |
| **Query** | Data retrieval command |
| **Variable** | Dynamic dashboard parameter |
| **Templating** | Dynamic content generation |
| **Annotation** | Time-based event marker |
| **PromQL** | Prometheus Query Language |
| **JSONnet** | Data templating language |
| **IaC** | Infrastructure as Code |

---

## 9. Related Resources

- [Architecture Decision Records (ADR)](https://adr.github.io/)
- [Documenting Architecture Decisions](http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions)
- [Grafana Documentation](https://grafana.com/docs/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
- [Dashboards SPEC.md](./docs/SPEC.md)
- [Parent Observability ADR](../ADR.md)

---

## 10. Maintenance

**ADR Shepherd**: Core Team  
**Review Schedule**: Monthly  
**Last Full Review**: 2024-Q4

---

*This index is automatically updated. Please submit a PR to add new ADRs or update existing ones.*
