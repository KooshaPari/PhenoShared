# Architecture Decision Records (ADR)

> **Project:** PhenoObservability/alerting  
> **Status:** Active  
> **Last Updated:** 2024

---

## 1. Introduction

### What are ADRs?

Architecture Decision Records (ADRs) capture important architectural decisions made during the development of the PhenoObservability alerting component. Each ADR describes:

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
| 001 | [Prometheus AlertManager](adrs/001-alertmanager.md) | ✅ Accepted | 2024-Q1 | Team | #prometheus #alertmanager |
| 002 | [Alert Rule Format](adrs/002-alert-rules.md) | ✅ Accepted | 2024-Q1 | Core Team | #rules #yaml |
| 003 | [Multi-Channel Routing](adrs/003-channel-routing.md) | ✅ Accepted | 2024-Q1 | Core Team | #routing #channels |
| 004 | [Severity Levels](adrs/004-severity-levels.md) | ✅ Accepted | 2024-Q2 | Architecture | #severity #priority |
| 005 | [Silencing and Muting](adrs/005-silencing.md) | ✅ Accepted | 2024-Q2 | Core Team | #silence #maintenance |
| 006 | [Inhibition Rules](adrs/006-inhibition.md) | ✅ Accepted | 2024-Q2 | Core Team | #inhibition #noise |
| 007 | [Notification Templates](adrs/007-templates.md) | ✅ Accepted | 2024-Q2 | Architecture | #templates #formatting |
| 008 | [Grouping Strategy](adrs/008-grouping.md) | ✅ Accepted | 2024-Q3 | Core Team | #grouping #aggregation |
| 009 | [SLO-Based Alerting](adrs/009-slo-alerting.md) | ✅ Accepted | 2024-Q3 | Architecture | #slo #error-budget |
| 010 | [Auto-Remediation](adrs/010-auto-remediation.md) | 📝 Proposed | 2024-Q4 | Architecture | #automation #remediation |

### Deprecated/Superseded

| ID | Title | Status | Superseded By |
|----|-------|--------|---------------|
| - | *No deprecated ADRs yet* | - | - |

---

## 3. Decision Drivers Summary

### Reliability
- Alert delivery guarantees
- Duplicate suppression
- Failover support
- State persistence

### Signal vs Noise
- High signal-to-noise ratio
- Intelligent grouping
- Context-rich notifications
- Actionable alerts only

### Operational Excellence
- Self-healing capabilities
- Runbook integration
- Escalation policies
- On-call rotation support

### Flexibility
- Multi-channel support
- Custom routing
- Template customization
- Webhook integration

### Scalability
- Handle high alert volume
- Efficient processing
- Horizontal scaling
- Resource efficiency

---

## 4. ADR Categories

### 🚨 Alert Rules (ADR-001 to ADR-010)
Alert rule definition and management.

**Key Topics:**
- Rule syntax
- Evaluation intervals
- Recording rules
- Alert conditions

### 📢 Notification (ADR-011 to ADR-020)
Notification channels and delivery.

**Key Topics:**
- Email notifications
- Slack integration
- PagerDuty
- Webhooks

### 🎯 Routing (ADR-021 to ADR-030)
Alert routing and assignment.

**Key Topics:**
- Label-based routing
- Team assignment
- Escalation chains
- Time-based routing

### 🔇 Noise Reduction (ADR-031 to ADR-040)
Alert noise reduction strategies.

**Key Topics:**
- Silencing
- Inhibition
- Grouping
- Throttling

### 📊 SLO/SLI (ADR-041 to ADR-050)
SLO-based alerting decisions.

**Key Topics:**
- Error budgets
- Burn rate alerts
- SLI definitions
- Multi-window alerts

### ⚙️ Operations (ADR-051 to ADR-060)
Operational and maintenance decisions.

**Key Topics:**
- Maintenance windows
- Auto-remediation
- Runbook links
- Post-mortem integration

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

### Alerting ADR Template (for alert decisions)

```markdown
# ADR-XXX: [Title]

- **Status**: Proposed
- **Date**: YYYY-MM-DD
- **Author**: [Name]
- **Alert Impact**: Rules | Routing | Notification | SLO

## Current Alert Behavior

How alerting currently works.

## Proposed Change

What will change in the alerting system.

## Example Alert

```yaml
alert: ExampleAlert
expr: up == 0
for: 5m
labels:
  severity: critical
annotations:
  summary: "Instance down"
```

## Operational Impact

Effect on on-call and incident response.

## Rollback Plan

How to disable if causing issues.
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
| **Alert** | Notification of anomalous condition |
| **AlertManager** | Prometheus alert handling system |
| **Silence** | Temporary alert suppression |
| **Inhibition** | Alert suppression by another alert |
| **SLI** | Service Level Indicator |
| **SLO** | Service Level Objective |
| **Error Budget** | Acceptable error threshold |
| **Burn Rate** | Rate of error budget consumption |
| **Escalation** | Alert forwarding to higher priority |

---

## 9. Related Resources

- [Architecture Decision Records (ADR)](https://adr.github.io/)
- [Documenting Architecture Decisions](http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions)
- [Prometheus Alerting](https://prometheus.io/docs/alerting/latest/overview/)
- [Google SRE Workbook - Alerting](https://sre.google/workbook/alerting/)
- [Alerting SPEC.md](./SPEC.md)
- [Parent Observability ADR](../ADR.md)

---

## 10. Maintenance

**ADR Shepherd**: Core Team  
**Review Schedule**: Monthly  
**Last Full Review**: 2024-Q4

---

*This index is automatically updated. Please submit a PR to add new ADRs or update existing ones.*
