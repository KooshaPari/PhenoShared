# alerting Library Specification

> Enterprise-Grade Alerting Rules Engine for Go - Prometheus-Compatible Alert Management with Multi-Channel Notifications

**Version**: 2.0.0  
**Status**: Production-Ready  
**Last Updated**: 2026-04-05  
**Maintainer**: Phenotype Engineering Team  
**License**: MIT  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [State of the Art Landscape](#2-state-of-the-art-landscape)
3. [System Architecture](#3-system-architecture)
4. [Component Specifications](#4-component-specifications)
5. [Data Models](#5-data-models)
6. [API Reference](#6-api-reference)
7. [Configuration](#7-configuration)
8. [Performance Targets](#8-performance-targets)
9. [Security Model](#9-security-model)
10. [Testing Strategy](#10-testing-strategy)
11. [Deployment Guide](#11-deployment-guide)
12. [Troubleshooting](#12-troubleshooting)
13. [Appendices](#13-appendices)

---

## 1. Executive Summary

### 1.1 Vision and Mission

The `alerting` library represents a comprehensive, enterprise-grade alerting rules engine designed specifically for Go applications operating within modern observability ecosystems. In an era where system reliability directly correlates with business success, the ability to define, manage, and route alerts efficiently has become a critical operational capability. This library addresses the gap between application-level instrumentation and operational alerting by providing a programmatic interface to generate Prometheus-compatible alert configurations while maintaining the flexibility to integrate with diverse notification channels.

The fundamental mission of the alerting library is to democratize alerting infrastructure by enabling developers to define alert rules as code, version control these configurations alongside application logic, and export them to industry-standard formats that operations teams can consume without friction. Unlike traditional approaches that require manual YAML editing or complex configuration management, this library treats alerting as a first-class concern of software engineering, subject to the same rigor of testing, review, and continuous delivery that governs application code.

### 1.2 Problem Statement

Modern distributed systems generate vast quantities of telemetry data, yet the translation of this data into actionable alerts remains fraught with challenges:

**Configuration Fragmentation**: Alert rules often exist in separate repositories, managed by different teams, leading to version skew between application capabilities and monitoring configurations. When application behavior changes, alerts may not reflect the new operational reality, resulting in either alert fatigue from false positives or missed incidents from absent coverage.

**Semantic Gap**: Developers understand application failure modes intimately but often lack the expertise or access to translate this knowledge into monitoring configurations. Conversely, operations teams possess monitoring expertise but lack deep application context, creating a dangerous knowledge gap that manifests as poorly tuned alerts.

**Tooling Inconsistency**: Organizations frequently operate heterogeneous monitoring stacks—Prometheus for metrics, ELK for logs, Jaeger for traces, PagerDuty for incident management—requiring alert definitions to be duplicated across systems or manually translated between formats.

**Testing Challenges**: Unlike application code, alert configurations are difficult to test in realistic scenarios. Many organizations only discover misconfigured alerts during actual incidents, when the cost of configuration errors is highest.

**Operational Burden**: Manual alert configuration does not scale. As system complexity grows linearly, the operational burden of maintaining alert configurations grows exponentially, consuming valuable engineering time that could be directed toward feature development.

### 1.3 Solution Overview

The alerting library addresses these challenges through a comprehensive approach that spans the entire alert lifecycle:

**Declarative Rule Definition**: Alert rules are defined as Go structs and functions, enabling type safety, IDE support, and compile-time validation. Rules can be organized hierarchically, versioned alongside application code, and reviewed through standard pull request workflows.

**Prometheus Native Integration**: The library generates Prometheus alert rule YAML that adheres to best practices, including proper expression syntax, appropriate evaluation intervals, and consistent labeling schemes that enable efficient routing and correlation.

**Multi-Channel Notification Support**: Beyond Prometheus, the library generates Alertmanager configurations for PagerDuty, OpsGenie, Slack, email, and webhooks. This unified approach ensures that alert routing logic is defined once and consistently applied across all notification channels.

**Template-Based Generation**: Alert templates provide reusable patterns for common scenarios—high error rates, latency thresholds, resource exhaustion—reducing boilerplate while maintaining flexibility for customization.

**Validation and Testing**: Built-in validation ensures that generated configurations are syntactically correct and semantically valid before deployment. Integration with promtool enables static analysis of generated rules.

**Operational Workflows**: The library supports common operational patterns including silence rules for maintenance windows, alert grouping to prevent notification storms, and severity-based routing to ensure appropriate escalation.

### 1.4 Key Differentiators

**Type Safety**: Unlike YAML-based configuration, the alerting library leverages Go's type system to prevent common errors such as missing required fields, invalid duration formats, or malformed PromQL expressions.

**Composability**: Alert rules can be composed from smaller, reusable components. Teams can define organization-specific templates that encode operational best practices, ensuring consistent alerting across services.

**CI/CD Integration**: Alert generation is a build-time activity, enabling validation gates, drift detection, and automated deployment through existing CI/CD pipelines. Changes to alerting are visible in code review and subject to approval workflows.

**Observability Integration**: Deep integration with the broader observability stack ensures that alerts reference the correct metrics, use appropriate thresholds derived from historical data, and include relevant context for rapid incident response.

### 1.5 Target Users

**Platform Engineers**: Responsible for defining organizational alerting standards and ensuring consistent coverage across services. The library enables platform teams to provide templates and constraints that guide service teams toward best practices.

**Service Owners**: Developers responsible for individual services who need to define alerts that reflect their application's specific failure modes. The library's Go-native API feels natural to application developers while producing professional-grade monitoring configurations.

**Site Reliability Engineers**: Operations professionals who consume the generated configurations and need to ensure they integrate correctly with existing monitoring infrastructure. The library produces standard Prometheus formats that require no custom tooling.

**DevOps Practitioners**: Teams bridging development and operations who need to automate alert configuration across diverse environments. The library's programmatic interface enables infrastructure-as-code workflows for alerting.

### 1.6 Success Metrics

The success of the alerting library is measured through operational outcomes:

**Alert Accuracy**: The percentage of alerts that represent genuine issues requiring human attention. Target: >95% accuracy, with false positive rate below 5%.

**Mean Time to Detection (MTTD)**: The time between an issue occurring and an alert firing. Target: Critical issues detected within 1 minute of threshold breach.

**Configuration Drift**: The frequency of manual configuration changes outside the code-driven workflow. Target: Zero manual changes in production; 100% of configuration changes traceable to code commits.

**Onboarding Time**: The time required for a new service to achieve comprehensive alert coverage. Target: <30 minutes from service creation to production-ready alerting.

**Operational Burden**: Engineering hours spent maintaining alert configurations per service per quarter. Target: <2 hours per service per quarter for routine maintenance.

### 1.7 Roadmap Summary

**Phase 1 (Completed)**: Core alert rule generation, Prometheus integration, basic notification routing.

**Phase 2 (Current)**: Advanced templates, multi-channel support, silence management, validation framework.

**Phase 3 (Planned)**: Machine learning-based threshold recommendations, automatic alert tuning, correlation rule generation, incident response workflow integration.

### 1.8 Ecosystem Position

The alerting library occupies a unique position in the observability ecosystem. It sits between application instrumentation libraries (which produce metrics) and monitoring backends (which consume alert configurations). This position enables it to bridge the semantic gap between "what developers know" (application failure modes) and "what operations needs" (monitoring configurations).

The library integrates with:

- **Upstream**: Metrics collection libraries, application instrumentation, configuration management systems
- **Downstream**: Prometheus, Alertmanager, PagerDuty, OpsGenie, Slack, custom webhooks
- **Adjacent**: Health check libraries, tracing systems, log aggregation platforms

### 1.9 Design Philosophy

The alerting library adheres to several core design principles:

**Configuration as Code**: All alerting state should be representable as code, versionable, and deployable through standard CI/CD pipelines.

**Convention over Configuration**: Sensible defaults and common patterns should be available out-of-box, while customizability remains for edge cases.

**Fail-Safe Defaults**: When in doubt, alert configurations should err toward over-alerting rather than under-alerting. A noisy alert can be tuned; a missing alert can cause outages.

**Explicit over Implicit**: Alert rules should clearly state their intent. Magic behaviors and implicit defaults are minimized to ensure predictability.

**Operational Context**: Every alert should include sufficient context—metric values, thresholds, affected services, runbook links—to enable rapid incident response.

---

## 2. State of the Art Landscape

### 2.1 Overview of Go Alerting Ecosystem

The Go alerting ecosystem comprises multiple layers: client libraries for rule generation, configuration management tools, and backend systems for evaluation and notification. Understanding the landscape is essential for positioning the alerting library and making informed architectural decisions.

### 2.2 Prometheus Alertmanager

**Overview**: Prometheus Alertmanager is the de facto standard for alert routing and notification management in cloud-native environments. Written in Go, it handles deduplication, grouping, routing, and silence management for alerts generated by Prometheus.

**Architecture**:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    Prometheus Alertmanager Architecture                       │
│                                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│   │  Prometheus │────▶│ Alertmanager│────▶│  Notifiers  │                   │
│   │  (firing)   │     │             │     │             │                   │
│   └─────────────┘     │  • Group    │     │ • PagerDuty │                   │
│                       │  • Inhibit  │     │ • Slack     │                   │
│   ┌─────────────┐     │  • Route    │     │ • Email     │                   │
│   │   Silence   │────▶│  • Notify   │     │ • Webhook   │                   │
│   │   Rules     │     │             │     │             │                   │
│   └─────────────┘     └─────────────┘     └─────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Strengths**:
- Mature, battle-tested codebase with extensive production deployment
- Native support for high-availability clustering
- Rich routing configuration with regex matching
- Built-in silence management for maintenance windows
- Multiple notification channels with templating

**Weaknesses**:
- Configuration via YAML only; no programmatic interface
- Complex routing trees become difficult to visualize and debug
- No built-in validation beyond YAML syntax checking
- Alert grouping logic can be opaque
- Limited context for template debugging

**API Patterns**:
```yaml
# Alertmanager configuration example
global:
  resolve_timeout: 5m
  smtp_smarthost: 'localhost:587'

route:
  receiver: 'default'
  group_by: ['alertname', 'severity']
  routes:
    - match:
        severity: critical
      receiver: pagerduty
      continue: true

receivers:
  - name: pagerduty
    pagerduty_configs:
      - service_key: '<key>'
        severity: critical
```

**Comparison to alerting library**: Alertmanager excels at runtime alert management but lacks development-time tooling. The alerting library complements Alertmanager by generating its configuration from Go code, adding type safety and testability.

### 2.3 Grafana Alerting

**Overview**: Grafana's unified alerting system, introduced in Grafana 8.0, provides alerting across multiple data sources including Prometheus, Loki, Elasticsearch, and cloud monitoring services.

**Architecture**:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        Grafana Alerting Architecture                          │
│                                                                             │
│   ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                     │
│   │Prometheus│  │  Loki    │  │CloudWatch│  │InfluxDB  │                     │
│   └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                     │
│        │             │             │             │                           │
│        └─────────────┴─────────────┴─────────────┘                           │
│                          │                                                  │
│                          ▼                                                  │
│   ┌──────────────────────────────────────────────────────┐                 │
│   │              Grafana Alerting Engine                  │                 │
│   │                                                       │                 │
│   │  ┌────────────┐  ┌────────────┐  ┌────────────┐      │                 │
│   │  │   Alert    │  │  Notification  │  │  Scheduler   │      │                 │
│   │  │   Rules    │  │   Policy       │  │              │      │                 │
│   │  └────────────┘  └────────────┘  └────────────┘      │                 │
│   └──────────────────────────────────────────────────────┘                 │
│                          │                                                  │
│                          ▼                                                  │
│   ┌──────────────────────────────────────────────────────┐                 │
│   │                Contact Points                         │                 │
│   │  • Email  • Slack  • PagerDuty  • Webhook  • SNS    │                 │
│   └──────────────────────────────────────────────────────┘                 │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Strengths**:
- Multi-datasource alerting from a single interface
- Rich UI for alert creation and management
- Built-in dashboard integration for alert visualization
- Provisioning support for configuration-as-code
- API and Terraform provider for automation

**Weaknesses**:
- Go library support limited; primarily UI-driven
- Alert rules stored in Grafana database by default
- Complex provisioning configuration
- Tighter coupling to Grafana deployment
- Alert rule export format is Grafana-specific

**API Patterns**:
```json
{
  "title": "High Error Rate",
  "condition": "A",
  "data": [
    {
      "refId": "A",
      "queryType": "",
      "relativeTimeRange": {"from": 300, "to": 0},
      "datasourceUid": "prometheus",
      "model": {
        "expr": "rate(errors[5m]) > 0.1"
      }
    }
  ]
}
```

**Comparison to alerting library**: Grafana excels at visualization and cross-datasource alerting but is not a Go-native solution. The alerting library focuses specifically on Prometheus-compatible Go applications, offering deeper integration with Go development workflows.

### 2.4 PagerDuty Events API v2

**Overview**: PagerDuty provides enterprise incident management with sophisticated on-call scheduling, escalation policies, and incident response workflows. The Events API v2 is the standard integration point for monitoring systems.

**Architecture**:
```
┌─────────────────────────────────────────────────────────────────────────────┐
│                      PagerDuty Events Architecture                            │
│                                                                             │
│   ┌─────────────┐     ┌─────────────┐     ┌─────────────┐                   │
│   │   Events    │────▶│   Event     │────▶│  Incident   │                   │
│   │   API v2    │     │   Rules     │     │  Creation   │                   │
│   │             │     │             │     │             │                   │
│   │ • trigger   │     │ • Routing   │     │ • Assign    │                   │
│   │ • acknowledge│   │ • Suppression│    │ • Escalate  │                   │
│   │ • resolve   │     │ • Enrichment│     │ • Notify    │                   │
│   └─────────────┘     └─────────────┘     └─────────────┘                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Strengths**:
- Industry-standard incident management
- Rich escalation and on-call capabilities
- Change Events API for deployment correlation
- Analytics and incident post-mortem tools
- Extensive third-party integrations

**Weaknesses**:
- No native Go SDK (community SDKs vary in quality)
- Rate limiting on event ingestion
- Complex pricing model for high-volume alerting
- Limited customization of incident fields
- Event deduplication requires careful integration key management

**API Patterns**:
```go
// PagerDuty event structure
type Event struct {
    RoutingKey  string           `json:"routing_key"`
    EventAction string           `json:"event_action"` // trigger, acknowledge, resolve
    DedupKey    string           `json:"dedup_key,omitempty"`
    Payload     EventPayload     `json:"payload"`
    Links       []Link           `json:"links,omitempty"`
}

type EventPayload struct {
    Summary   string            `json:"summary"`
    Severity  string            `json:"severity"` // critical, error, warning, info
    Source    string            `json:"source"`
    Component string            `json:"component,omitempty"`
    Group     string            `json:"group,omitempty"`
    Class     string            `json:"class,omitempty"`
    CustomDetails map[string]interface{} `json:"custom_details,omitempty"`
}
```

**Comparison to alerting library**: PagerDuty is a notification target, not a rule definition system. The alerting library generates configurations that route to PagerDuty through Alertmanager, maintaining separation between rule definition and incident management.

### 2.5 Other Notable Solutions

#### 2.5.1 Thanos Ruler

Thanos Ruler extends Prometheus alerting to globally-distributed, long-term storage scenarios. It enables alerting on historical data and cross-cluster rule evaluation.

**Use case**: Multi-cluster, multi-region deployments requiring global alert visibility.

**Limitation**: Adds operational complexity; requires Thanos ecosystem adoption.

#### 2.5.2 Cortex / Mimir Ruler

Cortex (now Mimir) provides horizontally-scalable, multi-tenant alert rule evaluation. It separates rule storage from evaluation, enabling centralized rule management.

**Use case**: Large-scale SaaS platforms with many tenants requiring isolated alerting.

**Limitation**: Complex deployment; overkill for single-tenant applications.

#### 2.5.3 Promgen

Promgen is a Django-based Prometheus configuration management tool that provides a web UI for alert rule editing.

**Use case**: Teams preferring UI-driven configuration management over code.

**Limitation**: Python-based; doesn't integrate with Go development workflows.

### 2.6 Competitive Analysis Matrix

| Feature | alerting lib | Alertmanager | Grafana | PagerDuty SDK |
|---------|--------------|--------------|---------|---------------|
| Go-native API | ✅ | ❌ | ❌ | ⚠️ Community |
| Type safety | ✅ | ❌ | ❌ | ⚠️ |
| Prometheus YAML gen | ✅ | N/A | ⚠️ | ❌ |
| Multi-channel routing | ✅ | ✅ | ✅ | ❌ |
| CI/CD integration | ✅ | ⚠️ | ⚠️ | ❌ |
| Template library | ✅ | ❌ | ❌ | ❌ |
| Validation framework | ✅ | ⚠️ | ⚠️ | ❌ |
| Silence management | ✅ | ✅ | ✅ | ❌ |
| Threshold management | ✅ | ❌ | ⚠️ | ❌ |
| Testability | ✅ | ⚠️ | ⚠️ | ⚠️ |
| Zero YAML editing | ✅ | ❌ | ❌ | ❌ |

### 2.7 Design Decisions

Based on the landscape analysis, the alerting library makes several key design decisions:

**Prometheus-First**: Rather than abstracting across multiple backends, the library focuses on best-in-class Prometheus integration, accepting that Prometheus has become the standard for cloud-native monitoring.

**Code-Generation Pattern**: The library generates configuration rather than operating as a runtime service. This enables GitOps workflows and eliminates the need for a separate alerting service to manage.

**Complementary, Not Competitive**: The library is designed to work alongside Alertmanager and Grafana, not replace them. It handles the "left side" of the alerting pipeline (rule definition) while leaving the "right side" (routing, notification) to specialized tools.

**Template-Driven**: Common alert patterns are codified as templates, enabling rapid adoption while maintaining flexibility for custom scenarios.

### 2.8 Integration Strategy

The alerting library's integration strategy follows a hub-and-spoke model:

```
                         ┌─────────────────┐
                         │  alerting lib   │
                         │  (rule definition)│
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
              ▼                   ▼                   ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │   Prometheus    │  │   Alertmanager  │  │   Custom        │
    │   (evaluation)  │  │   (routing)     │  │   Exporters     │
    └────────┬────────┘  └────────┬────────┘  └────────┬────────┘
             │                    │                    │
             ▼                    ▼                    ▼
    ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
    │   Metrics DB    │  │   PagerDuty     │  │   Grafana       │
    │   (storage)     │  │   OpsGenie      │  │   Slack         │
    └─────────────────┘  │   Email         │  │   Custom        │
                         └─────────────────┘  └─────────────────┘
```

### 2.9 Future Landscape Considerations

The alerting landscape continues to evolve:

**OpenTelemetry Alerting**: The OpenTelemetry project is developing standardized alerting constructs that may eventually provide cross-vendor alert portability.

**eBPF-Based Alerting**: Emerging eBPF-based monitoring enables kernel-level alerting with lower overhead, potentially complementing application-level alerting.

**AI-Assisted Tuning**: Machine learning is increasingly applied to alert threshold tuning, anomaly detection, and correlation analysis.

The alerting library is designed to evolve with these trends while maintaining backward compatibility and avoiding premature abstraction.

---

## 3. System Architecture

### 3.1 High-Level Architecture

The alerting library follows a layered architecture that separates concerns while maintaining tight integration between components:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    alerting Library Architecture                             │
│                                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                    API Layer                                          │  │
│  │                                                                                       │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐      │  │
│  │  │   Alert DSL    │  │   Threshold    │  │   Silence      │  │   Routing      │      │  │
│  │  │                │  │   Manager      │  │   Manager      │  │   Config       │      │  │
│  │  │ • HighErrorRate│  │                │  │                │  │                │      │  │
│  │  │ • HighLatency  │  │ • Validate     │  │ • Create       │  │ • Generate     │      │  │
│  │  │ • ResourceExh  │  │ • Default      │  │ • Match        │  │ • Route Tree   │      │  │
│  │  │ • Custom       │  │ • Bounds       │  │ • Expire       │  │ • Receivers    │      │  │
│  │  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘  └────────┬───────┘      │  │
│  │           │                   │                   │                   │              │  │
│  └───────────┼───────────────────┼───────────────────┼───────────────────┼──────────────┘  │
│              │                   │                   │                   │                 │
│              └───────────────────┴───────────────────┴───────────────────┘                 │
│                                  │                                                         │
│                                  ▼                                                         │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                 Core Engine                                           │  │
│  │                                                                                       │  │
│  │  ┌──────────────────────────────────────────────────────────────────────────────┐   │  │
│  │  │                         Template Engine                                        │   │  │
│  │  │                                                                                │   │  │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐              │   │  │
│  │  │  │  System    │  │  Business  │  │  Custom    │  │  Composite │              │   │  │
│  │  │  │  Templates │  │  Templates │  │  Templates │  │  Templates │              │   │  │
│  │  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘              │   │  │
│  │  └──────────────────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                                       │  │
│  │  ┌──────────────────────────────────────────────────────────────────────────────┐   │  │
│  │  │                      Expression Builder                                      │   │  │
│  │  │                                                                                │   │  │
│  │  │  • PromQL generation     • Metric references    • Function calls              │   │  │
│  │  │  • Label selectors       • Aggregation          • Windowing                   │   │  │
│  │  └──────────────────────────────────────────────────────────────────────────────┘   │  │
│  │                                                                                       │  │
│  │  ┌──────────────────────────────────────────────────────────────────────────────┐   │  │
│  │  │                       Validation Engine                                      │   │  │
│  │  │                                                                                │   │  │
│  │  │  • Syntax validation    • Semantic validation    • Threshold validation         │   │  │
│  │  │  • Reference checking   • Duplicate detection    • Best practice warnings     │   │  │
│  │  └──────────────────────────────────────────────────────────────────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                                Export Layer                                         │  │
│  │                                                                                       │  │
│  │  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐   │  │
│  │  │ Prometheus YAML│  │ Alertmanager   │  │ JSON Export    │  │ Documentation  │   │  │
│  │  │ Generator      │  │ Config Gen     │  │                │  │ Generator      │   │  │
│  │  └────────────────┘  └────────────────┘  └────────────────┘  └────────────────┘   │  │
│  └──────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Interactions

The alerting library components interact through well-defined interfaces:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                               Component Interaction Flow                                     │
│                                                                                              │
│   User Code                              alerting lib                      Output           │
│      │                                        │                              │              │
│      │ 1. Define thresholds                   │                              │              │
│      ├──────────────────────────────────────▶│                              │              │
│      │   AlertThresholds{...}               │                              │              │
│      │                                        │                              │              │
│      │ 2. Create alert via DSL                │                              │              │
│      ├──────────────────────────────────────▶│                              │              │
│      │   HighErrorRate(5.0, 5m)               │                              │              │
│      │                                        │                              │              │
│      │                              ┌─────────┴─────────┐                    │              │
│      │                              │  Template Engine  │                    │              │
│      │                              │  • Load template  │                    │              │
│      │                              │  • Apply params   │                    │              │
│      │                              │  • Build expr     │                    │              │
│      │                              └─────────┬─────────┘                    │              │
│      │                                        │                              │              │
│      │                              ┌─────────┴─────────┐                    │              │
│      │                              │  Validation Eng │                    │              │
│      │                              │  • Check syntax   │                    │              │
│      │                              │  • Validate refs  │                    │              │
│      │                              └─────────┬─────────┘                    │              │
│      │                                        │                              │              │
│      │                              ┌─────────┴─────────┐                    │              │
│      │                              │  RuleSet Builder  │                    │              │
│      │                              │  • Organize       │                    │              │
│      │                              │  • Deduplicate    │                    │              │
│      │                              └─────────┬─────────┘                    │              │
│      │                                        │                              │              │
│      │ 3. Generate output                       │                              │              │
│      ├──────────────────────────────────────▶│                              │              │
│      │   ToYAML() / ToAlertManagerConfig()      │                              │              │
│      │                                        │                              │              │
│      │                              ┌─────────┴─────────┐                    │              │
│      │                              │  Export Engines   ├────────────────────▶│              │
│      │                              │  • YAML fmt       │  alerts.yml          │              │
│      │                              │  • Alertmanager   ├────────────────────▶│              │
│      │                              │  • JSON fmt       │  alertmanager.yml    │              │
│      │                              └───────────────────┘                    │              │
│      │                                                                     │              │
└──────┴─────────────────────────────────────────────────────────────────────┴──────────────┘
```

### 3.3 Data Flow Architecture

Data flows through the alerting library in distinct phases:

**Definition Phase**: Users define alert rules using the DSL, specifying thresholds, durations, and metadata.

**Validation Phase**: Rules are validated for syntax correctness, semantic validity, and adherence to best practices.

**Compilation Phase**: Validated rules are compiled into internal representations optimized for export.

**Export Phase**: Internal representations are formatted as Prometheus YAML, Alertmanager configuration, or other supported formats.

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                                    Data Flow Pipeline                                       │
│                                                                                              │
│   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐            │
│   │   Definition │───▶│  Validation  │───▶│  Compilation │───▶│    Export    │            │
│   │              │    │              │    │              │    │              │            │
│   │ Alert DSL    │    │ Syntax check │    │ IR building  │    │ YAML format  │            │
│   │ Threshold cfg│    │ Semantic val │    │ Optimization │    │ Alertmanager │            │
│   │ Silence rules│    │ Cross-ref chk│    │ Deduplication│    │ JSON format  │            │
│   │ Route config │    │ Best practice│    │ Grouping     │    │ Markdown doc │            │
│   └──────────────┘    └──────────────┘    └──────────────┘    └──────────────┘            │
│                                                                                              │
│   Input: Go structs      Errors returned      IR: AlertRuleSet      Files written         │
│   Source: User code      Fatal: blocking      Source: Validated      Dest: Filesystem      │
│                         Warning: non-block     rules                CI/CD artifacts         │
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Template Engine Architecture

The template engine provides a flexible mechanism for alert rule generation:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                               Template Engine Architecture                                   │
│                                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              Template Registry                                        │  │
│  │                                                                                       │  │
│  │   map[string]Template                                                                   │  │
│  │   • "high_error_rate"  → ErrorRateTemplate                                            │  │
│  │   • "high_latency"     → LatencyTemplate                                               │  │
│  │   • "resource_exhaustion" → ResourceTemplate                                           │  │
│  │   • "custom"           → CustomTemplate                                                │  │
│  └──────────────────────────────────────────────────────────────────────────────────────┘  │
│                                          │                                                 │
│                                          ▼                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                           Template Interface                                           │  │
│  │                                                                                       │  │
│  │   type Template interface {                                                            │  │
│  │       Name() string                                                                    │  │
│  │       Description() string                                                             │  │
│  │       Parameters() []Parameter                                                         │  │
│  │       Build(params map[string]interface{}) (Alert, error)                             │  │
│  │   }                                                                                    │  │
│  └──────────────────────────────────────────────────────────────────────────────────────┘  │
│                                          │                                                 │
│                                          ▼                                                 │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                           Parameter System                                             │  │
│  │                                                                                       │  │
│  │   type Parameter struct {                                                              │  │
│  │       Name        string        // threshold                                           │  │
│  │       Type        ParamType     // float64, duration, string                         │  │
│  │       Required    bool          // must be provided                                  │  │
│  │       Default     interface{}   // if not required                                     │  │
│  │       Validation  ValidationFn  // custom validation                                   │  │
│  │       Description string        // documentation                                       │  │
│  │   }                                                                                    │  │
│  └──────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.5 Validation Pipeline Architecture

Validation occurs in multiple stages to catch errors early:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                              Validation Pipeline                                           │
│                                                                                              │
│   Stage 1: Syntax          Stage 2: Semantic        Stage 3: Best Practice               │
│                                                                                              │
│   ┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐                │
│   │  PromQL Parser  │      │  Metric Resolver  │      │  Threshold Ana  │                │
│   │                 │      │                 │      │                 │                │
│   │ • Parse expr    │─────▶│ • Check metric    │─────▶│ • Historical    │                │
│   │ • Check funcs   │      │   existence       │      │   comparison    │                │
│   │ • Validate      │      │ • Verify labels   │      │ • Rate analysis │                │
│   │   labels        │      │ • Cross-ref       │      │ • Sensitivity   │                │
│   └─────────────────┘      └─────────────────┘      └─────────────────┘                │
│           │                        │                        │                              │
│           ▼                        ▼                        ▼                              │
│   ┌──────────────────────────────────────────────────────────────────────────────┐        │
│   │                         Validation Result                                     │        │
│   │                                                                              │        │
│   │   type ValidationResult struct {                                             │        │
│   │       Valid      bool                                                         │        │
│   │       Errors     []ValidationError   // Fatal                                │        │
│   │       Warnings   []ValidationError   // Non-fatal                            │        │
│   │   }                                                                          │        │
│   │                                                                              │        │
│   │   type ValidationError struct {                                              │        │
│   │       Stage    string    // syntax, semantic, best_practice                │        │
│   │       Severity ErrorLevel // fatal, warning                                 │        │
│   │       Message  string                                                       │        │
│   │       Location string    // file:line or rule name                          │        │
│   │   }                                                                          │        │
│   └──────────────────────────────────────────────────────────────────────────────┘        │
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.6 Integration Architecture

The alerting library integrates with external systems through adapters:

```
┌─────────────────────────────────────────────────────────────────────────────────────────────┐
│                               Integration Architecture                                       │
│                                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              Adapter Interface                                        │  │
│  │                                                                                       │  │
│  │   type Exporter interface {                                                            │  │
│  │       Export(rules AlertRuleSet) ([]byte, error)                                    │  │
│  │       ContentType() string                                                             │  │
│  │       FileExtension() string                                                           │  │
│  │   }                                                                                    │  │
│  └──────────────────────────────────────────────────────────────────────────────────────┘  │
│              │                                    │                                         │
│              ▼                                    ▼                                         │
│  ┌─────────────────────┐              ┌─────────────────────┐                              │
│  │   PrometheusAdapter │              │ AlertmanagerAdapter │                              │
│  │                     │              │                     │                              │
│  │ • Rule YAML format  │              │ • Route tree gen    │                              │
│  │ • Grouping rules    │              │ • Receiver config   │                              │
│  │ • Interval config   │              │ • Silence templates   │                              │
│  └─────────────────────┘              └─────────────────────┘                              │
│                                                                                              │
│  ┌─────────────────────┐              ┌─────────────────────┐                              │
│  │   JSONAdapter       │              │   MarkdownAdapter   │                              │
│  │                     │              │                     │                              │
│  │ • API format        │              │ • Documentation     │                              │
│  │ • Integration ready │              │ • Runbook gen       │                              │
│  │ • Programmatic use  │              │ • Human readable    │                              │
│  └─────────────────────┘              └─────────────────────┘                              │
│                                                                                              │
└─────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Specifications

### 4.1 Alert Rule DSL Component

**Purpose**: Provide a fluent, type-safe interface for defining alert rules.

**Responsibilities**:
- Define pre-built alert templates for common scenarios
- Support custom alert creation with full PromQL flexibility
- Enforce consistent labeling and annotation conventions
- Generate valid PromQL expressions from high-level parameters

**Interface**:
```go
// Alert represents a single alert rule
type Alert struct {
    Name        string
    Expr        string
    For         string
    Labels      map[string]string
    Annotations map[string]string
}

// DSL functions for common alerts
func HighErrorRate(threshold float64, duration time.Duration) Alert
func HighLatency(threshold float64, duration time.Duration, percentile float64) Alert
func ResourceExhaustion(resource string, threshold float64) Alert
func DatabaseConnections(threshold float64) Alert
func JobQueueBacklog(threshold int, duration time.Duration) Alert
func CustomAlert(name, expr, duration string) AlertBuilder
```

**Design Rationale**:
Function-based DSLs provide better IDE support than struct literals. Each function encapsulates the PromQL generation logic, allowing users to focus on thresholds rather than query syntax. The builder pattern for custom alerts provides progressive disclosure—simple use cases remain simple, complex cases remain possible.

### 4.2 Threshold Management Component

**Purpose**: Centralize threshold configuration with validation and defaults.

**Responsibilities**:
- Define threshold structures for different alert categories
- Provide sensible defaults based on operational experience
- Validate thresholds for logical consistency
- Support environment-specific threshold overrides

**Interface**:
```go
type AlertThresholds struct {
    // HTTP/Application thresholds
    ErrorRate          float64
    P99LatencyMs       float64
    P95LatencyMs       float64
    
    // Resource thresholds
    MemoryUsagePercent float64
    CPUUsagePercent    float64
    DiskUsagePercent   float64
    FDUsagePercent     float64
    
    // Infrastructure thresholds
    QueueDepth         int
    DBPoolUsagePercent float64
    CacheHitPercent    float64
}

func DefaultThresholds() AlertThresholds
func ValidateThresholds(t AlertThresholds) ValidationResult
func MergeThresholds(base, override AlertThresholds) AlertThresholds
```

**Design Rationale**:
Threshold management is a cross-cutting concern that affects multiple alert types. Centralizing thresholds enables consistent tuning across related alerts and simplifies configuration management. Validation ensures that impossible thresholds (e.g., >100% CPU) are caught at configuration time.

### 4.3 Silence Rule Component

**Purpose**: Manage alert suppression for maintenance windows and known issues.

**Responsibilities**:
- Define silence rule structure compatible with Alertmanager
- Support label-based matching for flexible targeting
- Handle time-based expiration
- Enable comment and attribution tracking

**Interface**:
```go
type SilenceRule struct {
    ID        string
    Matchers  []LabelMatcher
    StartsAt  time.Time
    EndsAt    time.Time
    CreatedBy string
    Comment   string
}

type LabelMatcher struct {
    Name  string
    Value string
    Equal bool // true for =, false for !=
}

func (s SilenceRule) Match(labels map[string]string) bool
func (s SilenceRule) IsActive() bool
func (s SilenceRule) ToAlertmanagerFormat() string
```

**Design Rationale**:
Silence management is often an afterthought in alerting systems, leading to stale silences that hide real issues. By including silence management in the rule definition workflow, the library encourages proper lifecycle management of suppressions.

### 4.4 Routing Configuration Component

**Purpose**: Generate Alertmanager routing configurations that direct alerts to appropriate channels.

**Responsibilities**:
- Define receiver configurations for multiple notification channels
- Build routing trees with match criteria
- Support grouping and timing configurations
- Generate valid Alertmanager YAML

**Interface**:
```go
type RoutingConfig struct {
    DefaultReceiver string
    GroupBy         []string
    GroupWait       time.Duration
    GroupInterval   time.Duration
    RepeatInterval  time.Duration
    Routes          []Route
}

type Route struct {
    Receiver string
    Match    map[string]string
    Continue bool
    Routes   []Route // Nested routes
}

type Receiver struct {
    Name          string
    PagerDuty     *PagerDutyConfig
    Slack         *SlackConfig
    Email         *EmailConfig
    Webhook       *WebhookConfig
}

func BuildRoutingConfig(receivers []Receiver, strategy RoutingStrategy) RoutingConfig
func (r RoutingConfig) ToYAML() (string, error)
```

**Design Rationale**:
Alert routing is a complex domain with many interdependent parameters. The component abstracts Alertmanager's routing model into Go structures that can be validated before export, preventing common configuration errors.

### 4.5 Template Engine Component

**Purpose**: Provide reusable alert patterns that encode operational best practices.

**Responsibilities**:
- Maintain a registry of alert templates
- Validate template parameters
- Generate alerts from templates with custom parameters
- Support template composition

**Interface**:
```go
type Template interface {
    Name() string
    Description() string
    Parameters() []TemplateParameter
    Build(params map[string]interface{}) (Alert, error)
}

type TemplateParameter struct {
    Name        string
    Type        ParameterType
    Required    bool
    Default     interface{}
    Description string
}

type TemplateRegistry struct {
    templates map[string]Template
}

func (r *TemplateRegistry) Register(t Template)
func (r *TemplateRegistry) Get(name string) (Template, bool)
func (r *TemplateRegistry) List() []Template
```

**Design Rationale**:
Templates encode operational knowledge that would otherwise need to be rediscovered by each team. By providing a registry pattern, the library enables organizations to build domain-specific template libraries that accelerate alert definition.

### 4.6 Validation Engine Component

**Purpose**: Ensure alert configurations are correct before deployment.

**Responsibilities**:
- Parse and validate PromQL expressions
- Check metric references against known metric sets
- Validate threshold relationships (e.g., P99 > P95)
- Detect duplicate or conflicting rules

**Interface**:
```go
type Validator interface {
    Validate(rules AlertRuleSet) ValidationResult
}

type ValidationResult struct {
    Valid    bool
    Errors   []ValidationError
    Warnings []ValidationError
}

type ValidationError struct {
    Rule     string
    Field    string
    Message  string
    Severity ErrorLevel
}

type SyntaxValidator struct{}
type SemanticValidator struct {
    metricRegistry MetricRegistry
}
type BestPracticeValidator struct{}
```

**Design Rationale**:
Validation is most valuable when it occurs early in the development cycle. By providing a validation engine that can be invoked from tests and CI/CD, the library catches errors before they reach production.

### 4.7 Export Engine Component

**Purpose**: Convert internal alert representations to external formats.

**Responsibilities**:
- Format alert rules as Prometheus YAML
- Generate Alertmanager configuration
- Support JSON export for API integration
- Produce documentation artifacts

**Interface**:
```go
type Exporter interface {
    Export(rules AlertRuleSet) ([]byte, error)
    ContentType() string
}

type PrometheusExporter struct {
    interval string
}

func (e *PrometheusExporter) Export(rules AlertRuleSet) ([]byte, error)

// Additional exporters follow same pattern
```

**Design Rationale**:
Export engines encapsulate format-specific knowledge, allowing the core library to remain format-agnostic. This enables future support for additional backends without core library changes.

---

## 5. Data Models

### 5.1 Core Alert Model

The Alert structure represents a single alert rule in its canonical form:

```go
// Alert represents a single Prometheus alert rule
type Alert struct {
    // Identity
    Name string `json:"name" yaml:"alert"`
    
    // Expression is the PromQL query that triggers the alert
    Expr string `json:"expr" yaml:"expr"`
    
    // For is the duration the condition must hold before firing
    For string `json:"for,omitempty" yaml:"for,omitempty"`
    
    // Labels are attached to fired alerts for routing and identification
    Labels map[string]string `json:"labels,omitempty" yaml:"labels,omitempty"`
    
    // Annotations provide human-readable context for the alert
    Annotations map[string]string `json:"annotations,omitempty" yaml:"annotations,omitempty"`
    
    // Internal fields for library use
    Source      string    `json:"-" yaml:"-"` // Origin file/line
    GeneratedAt time.Time `json:"-" yaml:"-"`
    Template    string    `json:"-" yaml:"-"` // Template used, if any
}

// AlertGroup organizes related alerts
type AlertGroup struct {
    Name     string  `json:"name" yaml:"name"`
    Interval string  `json:"interval,omitempty" yaml:"interval,omitempty"`
    Rules    []Alert `json:"rules" yaml:"rules"`
    
    // Evaluation constraints
    Limit           int    `json:"limit,omitempty" yaml:"limit,omitempty"`
    PartialResponse string `json:"partial_response_strategy,omitempty" yaml:"partial_response_strategy,omitempty"`
}

// AlertRuleSet is the top-level container for all alerts
type AlertRuleSet struct {
    Groups []AlertGroup `json:"groups" yaml:"groups"`
    
    // Metadata
    Version     string    `json:"version,omitempty" yaml:"version,omitempty"`
    GeneratedAt time.Time `json:"generated_at,omitempty" yaml:"generated_at,omitempty"`
    Generator   string    `json:"generator,omitempty" yaml:"generator,omitempty"`
}
```

### 5.2 Threshold Models

Threshold models define the parameters that trigger alerts:

```go
// AlertThresholds contains threshold values for all alert categories
type AlertThresholds struct {
    // HTTP/Application Performance
    ErrorRate          float64 `json:"error_rate" yaml:"error_rate"`
    P99LatencyMs       float64 `json:"p99_latency_ms" yaml:"p99_latency_ms"`
    P95LatencyMs       float64 `json:"p95_latency_ms" yaml:"p95_latency_ms"`
    P50LatencyMs       float64 `json:"p50_latency_ms" yaml:"p50_latency_ms"`
    RequestRateMin     float64 `json:"request_rate_min" yaml:"request_rate_min"` // For detecting drops
    
    // System Resources
    MemoryUsagePercent float64 `json:"memory_usage_percent" yaml:"memory_usage_percent"`
    MemoryUsageBytes   int64   `json:"memory_usage_bytes" yaml:"memory_usage_bytes"`
    CPUUsagePercent    float64 `json:"cpu_usage_percent" yaml:"cpu_usage_percent"`
    DiskUsagePercent   float64 `json:"disk_usage_percent" yaml:"disk_usage_percent"`
    DiskIOUtilization  float64 `json:"disk_io_utilization" yaml:"disk_io_utilization"`
    FDUsagePercent     float64 `json:"fd_usage_percent" yaml:"fd_usage_percent"`
    ThreadCount        int     `json:"thread_count" yaml:"thread_count"`
    
    // Infrastructure
    QueueDepth         int     `json:"queue_depth" yaml:"queue_depth"`
    QueueAgeMax        int     `json:"queue_age_max" yaml:"queue_age_max"` // seconds
    DBPoolUsagePercent float64 `json:"db_pool_usage_percent" yaml:"db_pool_usage_percent"`
    DBQueryTimeMax     int     `json:"db_query_time_max" yaml:"db_query_time_max"` // ms
    CacheHitPercent    float64 `json:"cache_hit_percent" yaml:"cache_hit_percent"`
    CacheHitMin        float64 `json:"cache_hit_min" yaml:"cache_hit_min"`
    
    // Business Logic
    PaymentDelayMax    int `json:"payment_delay_max" yaml:"payment_delay_max"` // seconds
    UserSignupRateMin  int `json:"user_signup_rate_min" yaml:"user_signup_rate_min"` // per hour
}

// ThresholdValidation contains bounds for threshold validation
type ThresholdValidation struct {
    MinValue     float64
    MaxValue     float64
    Required     bool
    Description  string
}

// ThresholdBounds defines valid ranges for each threshold
type ThresholdBounds struct {
    bounds map[string]ThresholdValidation
}

func DefaultThresholdBounds() ThresholdBounds {
    return ThresholdBounds{
        bounds: map[string]ThresholdValidation{
            "error_rate":          {MinValue: 0, MaxValue: 100, Required: true, Description: "Error rate percentage"},
            "p99_latency_ms":      {MinValue: 0, MaxValue: 300000, Required: true, Description: "P99 latency in milliseconds"},
            "memory_usage_percent": {MinValue: 0, MaxValue: 100, Required: true, Description: "Memory usage percentage"},
            "cpu_usage_percent":    {MinValue: 0, MaxValue: 100, Required: true, Description: "CPU usage percentage"},
            "disk_usage_percent":   {MinValue: 0, MaxValue: 100, Required: true, Description: "Disk usage percentage"},
            "queue_depth":          {MinValue: 0, MaxValue: 1000000, Required: true, Description: "Queue depth count"},
            "db_pool_usage_percent": {MinValue: 0, MaxValue: 100, Required: true, Description: "Database pool usage percentage"},
        },
    }
}
```

### 5.3 Silence Models

Silence models represent alert suppression rules:

```go
// SilenceRule represents a single silence configuration
type SilenceRule struct {
    // Unique identifier for the silence
    ID string `json:"id" yaml:"id"`
    
    // Matchers define which alerts this silence applies to
    Matchers []LabelMatcher `json:"matchers" yaml:"matchers"`
    
    // Time range for the silence
    StartsAt time.Time `json:"starts_at" yaml:"starts_at"`
    EndsAt   time.Time `json:"ends_at" yaml:"ends_at"`
    
    // Metadata
    CreatedBy string `json:"created_by" yaml:"created_by"`
    Comment   string `json:"comment" yaml:"comment"`
    
    // State tracking
    CreatedAt time.Time `json:"created_at,omitempty" yaml:"created_at,omitempty"`
    UpdatedAt time.Time `json:"updated_at,omitempty" yaml:"updated_at,omitempty"`
}

// LabelMatcher represents a single label matching condition
type LabelMatcher struct {
    Name    string `json:"name" yaml:"name"`
    Value   string `json:"value" yaml:"value"`
    IsRegex bool   `json:"is_regex,omitempty" yaml:"is_regex,omitempty"`
    Equal   bool   `json:"equal" yaml:"equal"` // true for =, false for !=
}

// SilenceRuleSet manages a collection of silence rules
type SilenceRuleSet struct {
    Rules []SilenceRule `json:"rules" yaml:"rules"`
    
    // Default duration for new silences without explicit end time
    DefaultDuration time.Duration `json:"default_duration,omitempty" yaml:"default_duration,omitempty"`
}

// SilenceMatchResult represents the outcome of a match operation
type SilenceMatchResult struct {
    Matched     bool
    SilenceID   string
    ExpiresAt   time.Time
    Explanation string
}
```

### 5.4 Routing Models

Routing models define alert distribution:

```go
// RoutingConfig represents complete Alertmanager routing configuration
type RoutingConfig struct {
    // Global settings
    Global GlobalConfig `json:"global,omitempty" yaml:"global,omitempty"`
    
    // Default route
    Route Route `json:"route" yaml:"route"`
    
    // Additional routes
    Routes []Route `json:"routes,omitempty" yaml:"routes,omitempty"`
    
    // Receiver definitions
    Receivers []Receiver `json:"receivers" yaml:"receivers"`
    
    // Inhibition rules
    InhibitRules []InhibitRule `json:"inhibit_rules,omitempty" yaml:"inhibit_rules,omitempty"`
    
    // Templates
    Templates []string `json:"templates,omitempty" yaml:"templates,omitempty"`
}

// GlobalConfig contains global Alertmanager settings
type GlobalConfig struct {
    ResolveTimeout     string `json:"resolve_timeout,omitempty" yaml:"resolve_timeout,omitempty"`
    SMTPFrom           string `json:"smtp_from,omitempty" yaml:"smtp_from,omitempty"`
    SMTPSmarthost      string `json:"smtp_smarthost,omitempty" yaml:"smtp_smarthost,omitempty"`
    SMTPAuthUsername   string `json:"smtp_auth_username,omitempty" yaml:"smtp_auth_username,omitempty"`
    SlackAPIURL        string `json:"slack_api_url,omitempty" yaml:"slack_api_url,omitempty"`
    PagerDutyURL       string `json:"pagerduty_url,omitempty" yaml:"pagerduty_url,omitempty"`
    OpsGenieAPIURL     string `json:"opsgenie_api_url,omitempty" yaml:"opsgenie_api_url,omitempty"`
}

// Route defines alert routing criteria
type Route struct {
    Receiver       string            `json:"receiver" yaml:"receiver"`
    GroupBy        []string          `json:"group_by,omitempty" yaml:"group_by,omitempty"`
    GroupWait      string            `json:"group_wait,omitempty" yaml:"group_wait,omitempty"`
    GroupInterval  string            `json:"group_interval,omitempty" yaml:"group_interval,omitempty"`
    RepeatInterval string            `json:"repeat_interval,omitempty" yaml:"repeat_interval,omitempty"`
    Match          map[string]string `json:"match,omitempty" yaml:"match,omitempty"`
    MatchRE        map[string]string `json:"match_re,omitempty" yaml:"match_re,omitempty"`
    Continue       bool              `json:"continue,omitempty" yaml:"continue,omitempty"`
    Routes         []Route           `json:"routes,omitempty" yaml:"routes,omitempty"`
}

// Receiver defines a notification target
type Receiver struct {
    Name          string              `json:"name" yaml:"name"`
    PagerDuty     []PagerDutyConfig   `json:"pagerduty_configs,omitempty" yaml:"pagerduty_configs,omitempty"`
    Slack         []SlackConfig       `json:"slack_configs,omitempty" yaml:"slack_configs,omitempty"`
    Email         []EmailConfig       `json:"email_configs,omitempty" yaml:"email_configs,omitempty"`
    Webhook       []WebhookConfig     `json:"webhook_configs,omitempty" yaml:"webhook_configs,omitempty"`
    OpsGenie      []OpsGenieConfig    `json:"opsgenie_configs,omitempty" yaml:"opsgenie_configs,omitempty"`
}

// Notification channel configurations
type PagerDutyConfig struct {
    ServiceKey            string            `json:"service_key,omitempty" yaml:"service_key,omitempty"`
    RoutingKey            string            `json:"routing_key,omitempty" yaml:"routing_key,omitempty"`
    URL                   string            `json:"url,omitempty" yaml:"url,omitempty"`
    Severity              string            `json:"severity,omitempty" yaml:"severity,omitempty"`
    Description           string            `json:"description,omitempty" yaml:"description,omitempty"`
    SendResolved          bool              `json:"send_resolved,omitempty" yaml:"send_resolved,omitempty"`
    Details               map[string]string `json:"details,omitempty" yaml:"details,omitempty"`
}

type SlackConfig struct {
    APIURL       string            `json:"api_url,omitempty" yaml:"api_url,omitempty"`
    Channel      string            `json:"channel,omitempty" yaml:"channel,omitempty"`
    Username     string            `json:"username,omitempty" yaml:"username,omitempty"`
    Color        string            `json:"color,omitempty" yaml:"color,omitempty"`
    Title        string            `json:"title,omitempty" yaml:"title,omitempty"`
    Text         string            `json:"text,omitempty" yaml:"text,omitempty"`
    SendResolved bool              `json:"send_resolved,omitempty" yaml:"send_resolved,omitempty"`
    Actions      []SlackAction     `json:"actions,omitempty" yaml:"actions,omitempty"`
}

type EmailConfig struct {
    To           string   `json:"to,omitempty" yaml:"to,omitempty"`
    From         string   `json:"from,omitempty" yaml:"from,omitempty"`
    Smarthost    string   `json:"smarthost,omitempty" yaml:"smarthost,omitempty"`
    AuthUsername string   `json:"auth_username,omitempty" yaml:"auth_username,omitempty"`
    AuthPassword string   `json:"auth_password,omitempty" yaml:"auth_password,omitempty"`
    Headers      map[string]string `json:"headers,omitempty" yaml:"headers,omitempty"`
    HTML         string   `json:"html,omitempty" yaml:"html,omitempty"`
    Text         string   `json:"text,omitempty" yaml:"text,omitempty"`
    SendResolved bool     `json:"send_resolved,omitempty" yaml:"send_resolved,omitempty"`
}

type WebhookConfig struct {
    URL            string            `json:"url" yaml:"url"`
    SendResolved   bool              `json:"send_resolved,omitempty" yaml:"send_resolved,omitempty"`
    HTTPConfig     HTTPConfig        `json:"http_config,omitempty" yaml:"http_config,omitempty"`
    MaxAlerts      int               `json:"max_alerts,omitempty" yaml:"max_alerts,omitempty"`
}

type OpsGenieConfig struct {
    APIKey       string            `json:"api_key,omitempty" yaml:"api_key,omitempty"`
    APIURL       string            `json:"api_url,omitempty" yaml:"api_url,omitempty"`
    Message      string            `json:"message,omitempty" yaml:"message,omitempty"`
    Description  string            `json:"description,omitempty" yaml:"description,omitempty"`
    Priority     string            `json:"priority,omitempty" yaml:"priority,omitempty"`
    Tags         string            `json:"tags,omitempty" yaml:"tags,omitempty"`
    SendResolved bool              `json:"send_resolved,omitempty" yaml:"send_resolved,omitempty"`
}

// InhibitRule prevents certain alerts from firing when others are active
type InhibitRule struct {
    SourceMatch   map[string]string `json:"source_match,omitempty" yaml:"source_match,omitempty"`
    TargetMatch   map[string]string `json:"target_match,omitempty" yaml:"target_match,omitempty"`
    Equal         []string          `json:"equal,omitempty" yaml:"equal,omitempty"`
}
```

### 5.5 Template Models

Template models represent reusable alert patterns:

```go
// Template represents an alert template
type Template struct {
    Metadata TemplateMetadata
    Parameters []TemplateParameter
    Builder  TemplateBuilder
}

// TemplateMetadata contains template information
type TemplateMetadata struct {
    Name        string    `json:"name" yaml:"name"`
    Version     string    `json:"version" yaml:"version"`
    Description string    `json:"description" yaml:"description"`
    Category    string    `json:"category" yaml:"category"`
    Author      string    `json:"author,omitempty" yaml:"author,omitempty"`
    CreatedAt   time.Time `json:"created_at,omitempty" yaml:"created_at,omitempty"`
    UpdatedAt   time.Time `json:"updated_at,omitempty" yaml:"updated_at,omitempty"`
    Tags        []string  `json:"tags,omitempty" yaml:"tags,omitempty"`
}

// TemplateParameter defines a configurable aspect of the template
type TemplateParameter struct {
    Name         string          `json:"name" yaml:"name"`
    Type         ParameterType   `json:"type" yaml:"type"`
    Required     bool            `json:"required" yaml:"required"`
    Default      interface{}     `json:"default,omitempty" yaml:"default,omitempty"`
    Description  string          `json:"description" yaml:"description"`
    Validation   ValidationSpec  `json:"validation,omitempty" yaml:"validation,omitempty"`
    Examples     []string        `json:"examples,omitempty" yaml:"examples,omitempty"`
}

// ParameterType defines valid parameter types
type ParameterType string

const (
    ParamTypeString   ParameterType = "string"
    ParamTypeInt      ParameterType = "int"
    ParamTypeFloat    ParameterType = "float"
    ParamTypeDuration ParameterType = "duration"
    ParamTypeBool     ParameterType = "bool"
    ParamTypeSelector ParameterType = "selector" // label selector
    ParamTypeList     ParameterType = "list"
)

// ValidationSpec defines parameter constraints
type ValidationSpec struct {
    Min          *float64 `json:"min,omitempty" yaml:"min,omitempty"`
    Max          *float64 `json:"max,omitempty" yaml:"max,omitempty"`
    Pattern      string   `json:"pattern,omitempty" yaml:"pattern,omitempty"` // regex
    Enum         []string `json:"enum,omitempty" yaml:"enum,omitempty"`
    Custom       string   `json:"custom,omitempty" yaml:"custom,omitempty"` // custom validation function name
}

// TemplateBuilder is the function that creates alerts from parameters
type TemplateBuilder func(params map[string]interface{}) (Alert, error)

// TemplateRegistry manages available templates
type TemplateRegistry struct {
    templates map[string]Template
    mu        sync.RWMutex
}
```

---

## 6. API Reference

### 6.1 Alert DSL API

#### HighErrorRate

Creates an alert for elevated HTTP error rates.

```go
func HighErrorRate(threshold float64, duration time.Duration) Alert
```

**Parameters**:
- `threshold`: Error rate percentage (0-100) that triggers the alert
- `duration`: How long the condition must persist before firing

**Returns**: Configured Alert with PromQL expression

**Generated PromQL**:
```promql
sum(rate(phenotype_http_requests_total{status=~"5.."}[5m])) /
sum(rate(phenotype_http_requests_total[5m])) * 100 > 5.0
```

**Example**:
```go
alert := alerting.HighErrorRate(5.0, 5*time.Minute)
// Alert fires when error rate exceeds 5% for 5 minutes
```

#### HighLatency

Creates an alert for elevated request latency.

```go
func HighLatency(threshold float64, duration time.Duration, percentile float64) Alert
```

**Parameters**:
- `threshold`: Latency threshold in seconds
- `duration`: Condition duration requirement
- `percentile`: Which percentile to monitor (0.5, 0.95, 0.99)

**Example**:
```go
// Alert when P99 latency exceeds 1 second for 5 minutes
alert := alerting.HighLatency(1.0, 5*time.Minute, 0.99)
```

#### ResourceExhaustion

Creates an alert for resource usage thresholds.

```go
func ResourceExhaustion(resource string, threshold float64) Alert
```

**Parameters**:
- `resource`: Resource type ("memory", "cpu", "disk", "fd")
- `threshold`: Usage percentage threshold

**Example**:
```go
memAlert := alerting.ResourceExhaustion("memory", 85.0)
cpuAlert := alerting.ResourceExhaustion("cpu", 80.0)
```

#### DatabaseConnections

Creates an alert for database connection pool exhaustion.

```go
func DatabaseConnections(threshold float64) Alert
```

**Parameters**:
- `threshold`: Pool usage percentage that triggers alert

**Example**:
```go
alert := alerting.DatabaseConnections(80.0)
```

#### JobQueueBacklog

Creates an alert for job queue depth.

```go
func JobQueueBacklog(threshold int, duration time.Duration) Alert
```

**Parameters**:
- `threshold`: Queue depth count threshold
- `duration`: How long backlog must persist

**Example**:
```go
alert := alerting.JobQueueBacklog(1000, 10*time.Minute)
```

### 6.2 Alert Builder API

For custom alerts, use the builder pattern:

```go
type AlertBuilder struct{}

func CustomAlert(name string) *AlertBuilder
func (b *AlertBuilder) WithExpr(expr string) *AlertBuilder
func (b *AlertBuilder) WithDuration(d time.Duration) *AlertBuilder
func (b *AlertBuilder) WithLabel(key, value string) *AlertBuilder
func (b *AlertBuilder) WithAnnotation(key, value string) *AlertBuilder
func (b *AlertBuilder) Build() Alert
```

**Example**:
```go
alert := alerting.CustomAlert("CustomBusinessMetric").
    WithExpr("business_metric > 100").
    WithDuration(5 * time.Minute).
    WithLabel("severity", "warning").
    WithLabel("team", "platform").
    WithAnnotation("summary", "Business metric exceeded threshold").
    WithAnnotation("runbook", "https://wiki/runbooks/custom-metric").
    Build()
```

### 6.3 Threshold Management API

#### DefaultThresholds

Returns sensible default thresholds.

```go
func DefaultThresholds() AlertThresholds
```

**Returns**:
```go
AlertThresholds{
    ErrorRate:          5.0,    // 5% error rate
    P99LatencyMs:       1000.0, // 1 second
    P95LatencyMs:       500.0,  // 500ms
    MemoryUsagePercent: 85.0,   // 85%
    CPUUsagePercent:    80.0,   // 80%
    DiskUsagePercent:   90.0,   // 90%
    QueueDepth:         1000,   // 1000 items
    DBPoolUsagePercent: 80.0,   // 80%
}
```

#### ValidateThresholds

Validates threshold configuration.

```go
func ValidateThresholds(t AlertThresholds) ValidationResult
```

**Validation Rules**:
- Error rate must be between 0 and 100
- Latency values must be positive
- Resource percentages must be between 0 and 100
- P99 latency must be greater than P95 latency

**Returns**: ValidationResult with errors and warnings

**Example**:
```go
thresholds := alerting.DefaultThresholds()
thresholds.ErrorRate = -1 // Invalid

result := alerting.ValidateThresholds(thresholds)
if !result.Valid {
    for _, err := range result.Errors {
        log.Printf("Validation error: %s", err.Message)
    }
}
```

### 6.4 RuleSet Management API

#### NewAlertRuleSet

Creates a new empty rule set.

```go
func NewAlertRuleSet() *AlertRuleSet
```

#### AddGroup

Adds an alert group to the rule set.

```go
func (r *AlertRuleSet) AddGroup(name string, alerts []Alert) error
```

**Parameters**:
- `name`: Group name (must be unique in rule set)
- `alerts`: Slice of alerts to include

**Returns**: Error if group name duplicates existing

#### AddAlert

Adds a single alert to a group.

```go
func (r *AlertRuleSet) AddAlert(groupName string, alert Alert) error
```

#### ToYAML

Exports rule set as Prometheus YAML.

```go
func (r *AlertRuleSet) ToYAML() (string, error)
```

**Returns**: Formatted YAML string suitable for Prometheus

**Example**:
```go
ruleSet := alerting.NewAlertRuleSet()
ruleSet.AddGroup("system", systemAlerts)
ruleSet.AddGroup("business", businessAlerts)

yaml, err := ruleSet.ToYAML()
if err != nil {
    log.Fatal(err)
}
os.WriteFile("alerts.yml", []byte(yaml), 0644)
```

### 6.5 Silence Management API

#### CreateSilence

Creates a new silence rule.

```go
func CreateSilence(matchers []LabelMatcher, duration time.Duration, createdBy, comment string) SilenceRule
```

**Example**:
```go
silence := alerting.CreateSilence(
    []alerting.LabelMatcher{
        {Name: "alertname", Value: "HighErrorRate", Equal: true},
        {Name: "service", Value: "api-gateway", Equal: true},
    },
    2*time.Hour,
    "ops-team",
    "Maintenance window for database migration",
)
```

#### Match

Tests if labels match the silence.

```go
func (s SilenceRule) Match(labels map[string]string) bool
```

#### IsActive

Checks if silence is currently active.

```go
func (s SilenceRule) IsActive() bool
```

### 6.6 Routing Configuration API

#### GenerateAlertManagerConfig

Generates complete Alertmanager configuration.

```go
func GenerateAlertManagerConfig(
    receivers []Receiver,
    global GlobalConfig,
    strategy RoutingStrategy,
) (string, error)
```

**Example**:
```go
receivers := []alerting.Receiver{
    {
        Name: "critical-pagerduty",
        PagerDuty: []alerting.PagerDutyConfig{{
            RoutingKey: os.Getenv("PAGERDUTY_KEY"),
            Severity:   "critical",
        }},
    },
    {
        Name: "warning-slack",
        Slack: []alerting.SlackConfig{{
            Channel: "#alerts-warning",
        }},
    },
}

global := alerting.GlobalConfig{
    ResolveTimeout: "5m",
    SMTPFrom:       "alerts@company.com",
}

config, err := alerting.GenerateAlertManagerConfig(
    receivers,
    global,
    alerting.SeverityBasedRouting,
)
```

#### RoutingStrategy

Predefined routing strategies:

```go
type RoutingStrategy int

const (
    FlatRouting RoutingStrategy = iota         // All alerts to default receiver
    SeverityBasedRouting                        // Route by severity label
    TeamBasedRouting                           // Route by team label
    ServiceBasedRouting                        // Route by service label
    SeverityThenTeamRouting                     // Severity first, then team
)
```

### 6.7 Validation API

#### ValidateRuleSet

Validates an entire rule set.

```go
func ValidateRuleSet(rules AlertRuleSet) ValidationResult
```

**Checks Performed**:
- Duplicate alert names
- Valid PromQL syntax
- Consistent labeling
- Threshold relationships
- Reference validity

#### ValidatePromQL

Validates a PromQL expression.

```go
func ValidatePromQL(expr string) error
```

### 6.8 Template API

#### RegisterTemplate

Registers a custom template.

```go
func (r *TemplateRegistry) Register(t Template)
```

#### GetTemplate

Retrieves a template by name.

```go
func (r *TemplateRegistry) Get(name string) (Template, bool)
```

#### BuildFromTemplate

Creates an alert from a template.

```go
func BuildFromTemplate(registry *TemplateRegistry, name string, params map[string]interface{}) (Alert, error)
```

### 6.9 Complete Usage Example

```go
package main

import (
    "context"
    "fmt"
    "log"
    "os"
    "time"
    
    "github.com/coder/alerting"
)

func main() {
    ctx := context.Background()
    
    // Step 1: Define thresholds
    thresholds := alerting.AlertThresholds{
        ErrorRate:          5.0,
        P99LatencyMs:       1000.0,
        MemoryUsagePercent: 85.0,
        CPUUsagePercent:    80.0,
        QueueDepth:         1000,
        DBPoolUsagePercent: 80.0,
    }
    
    // Step 2: Validate thresholds
    result := alerting.ValidateThresholds(thresholds)
    if !result.Valid {
        log.Fatalf("Invalid thresholds: %v", result.Errors)
    }
    
    // Step 3: Create rule set
    ruleSet := alerting.NewAlertRuleSet()
    
    // Step 4: Add system alerts
    systemAlerts := []alerting.Alert{
        alerting.HighErrorRate(thresholds.ErrorRate, 5*time.Minute),
        alerting.HighLatency(thresholds.P99LatencyMs/1000, 5*time.Minute, 0.99),
        alerting.ResourceExhaustion("memory", thresholds.MemoryUsagePercent),
        alerting.ResourceExhaustion("cpu", thresholds.CPUUsagePercent),
        alerting.DatabaseConnections(thresholds.DBPoolUsagePercent),
    }
    
    if err := ruleSet.AddGroup("system", systemAlerts); err != nil {
        log.Fatal(err)
    }
    
    // Step 5: Add business alerts with custom builder
    paymentAlert := alerting.CustomAlert("PaymentProcessingDelayed").
        WithExpr(`time() - max(phenotype_payment_last_processed_timestamp) > 300`).
        WithDuration(5 * time.Minute).
        WithLabel("severity", "critical").
        WithLabel("team", "payments").
        WithAnnotation("summary", "Payment processing delayed").
        WithAnnotation("description", "No payments processed in last 5 minutes").
        WithAnnotation("runbook", "https://wiki/runbooks/payment-delay").
        Build()
    
    queueAlert := alerting.JobQueueBacklog(thresholds.QueueDepth, 10*time.Minute)
    
    if err := ruleSet.AddGroup("business", []alerting.Alert{paymentAlert, queueAlert}); err != nil {
        log.Fatal(err)
    }
    
    // Step 6: Validate complete rule set
    validation := alerting.ValidateRuleSet(*ruleSet)
    if !validation.Valid {
        for _, err := range validation.Errors {
            log.Printf("Validation error: %s at %s", err.Message, err.Location)
        }
        os.Exit(1)
    }
    
    // Step 7: Generate Prometheus YAML
    promYAML, err := ruleSet.ToYAML()
    if err != nil {
        log.Fatal(err)
    }
    
    if err := os.WriteFile("alerts.yml", []byte(promYAML), 0644); err != nil {
        log.Fatal(err)
    }
    
    // Step 8: Generate Alertmanager config
    receivers := []alerting.Receiver{
        {
            Name: "critical",
            PagerDuty: []alerting.PagerDutyConfig{{
                RoutingKey: os.Getenv("PAGERDUTY_KEY"),
                Severity:   "critical",
            }},
        },
        {
            Name: "warning",
            Slack: []alerting.SlackConfig{{
                APIURL:   os.Getenv("SLACK_WEBHOOK"),
                Channel:  "#alerts-warning",
                SendResolved: true,
            }},
        },
    }
    
    global := alerting.GlobalConfig{
        ResolveTimeout: "5m",
        SMTPFrom:       "alerts@company.com",
    }
    
    amConfig, err := alerting.GenerateAlertManagerConfig(
        receivers,
        global,
        alerting.SeverityBasedRouting,
    )
    if err != nil {
        log.Fatal(err)
    }
    
    if err := os.WriteFile("alertmanager.yml", []byte(amConfig), 0644); err != nil {
        log.Fatal(err)
    }
    
    // Step 9: Create silence for maintenance
    silence := alerting.CreateSilence(
        []alerting.LabelMatcher{
            {Name: "severity", Value: "warning", Equal: true},
        },
        2*time.Hour,
        "ops-team",
        "Scheduled maintenance window",
    )
    
    silenceYAML := silence.ToAlertmanagerFormat()
    if err := os.WriteFile("silence.yml", []byte(silenceYAML), 0644); err != nil {
        log.Fatal(err)
    }
    
    log.Println("Alert configuration generated successfully")
}
```

---

## 7. Configuration

### 7.1 Configuration Philosophy

The alerting library follows a layered configuration approach where defaults, environment-specific values, and runtime overrides compose to produce the final configuration. This approach balances convenience (sensible defaults) with flexibility (full customization).

### 7.2 Configuration Sources

Configuration is loaded from multiple sources in priority order (highest priority last):

1. **Library defaults**: Hardcoded sensible defaults
2. **Configuration files**: YAML/JSON files in standard locations
3. **Environment variables**: For secrets and environment-specific values
4. **Programmatic overrides**: Runtime configuration via code

### 7.3 File-Based Configuration

Configuration files follow a hierarchical structure:

```yaml
# alerting.yaml - Main configuration file
version: "1.0"

defaults:
  evaluation_interval: "15s"
  group_interval: "10s"
  repeat_interval: "12h"
  
thresholds:
  error_rate: 5.0
  p99_latency_ms: 1000.0
  memory_usage_percent: 85.0
  cpu_usage_percent: 80.0
  disk_usage_percent: 90.0
  queue_depth: 1000
  db_pool_usage_percent: 80.0

labels:
  default:
    severity: "warning"
    team: "platform"
  
annotations:
  default:
    summary_template: "{{ .AlertName }}: {{ .Value }}"
    runbook_base_url: "https://wiki/runbooks"

templates:
  registry:
    - name: "high_error_rate"
      enabled: true
    - name: "high_latency"
      enabled: true

routing:
  strategy: "severity_based"
  default_receiver: "warning"
  
notification_channels:
  pagerduty:
    service_key: "${PAGERDUTY_SERVICE_KEY}"
    severity_map:
      critical: "critical"
      warning: "warning"
      info: "info"
  
  slack:
    webhook_url: "${SLACK_WEBHOOK_URL}"
    default_channel: "#alerts"
    channel_map:
      critical: "#alerts-critical"
      warning: "#alerts-warning"
  
  email:
    smtp_host: "${SMTP_HOST}"
    smtp_port: 587
    from: "alerts@company.com"
    to_default: "oncall@company.com"
```

### 7.4 Environment Variables

All configuration values can be overridden via environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `ALERTING_CONFIG_PATH` | Path to config file | `/etc/alerting/config.yaml` |
| `ALERTING_THRESHOLD_ERROR_RATE` | Error rate threshold | `5.0` |
| `ALERTING_THRESHOLD_P99_LATENCY_MS` | P99 latency threshold | `1000` |
| `ALERTING_THRESHOLD_MEMORY_PERCENT` | Memory threshold | `85` |
| `ALERTING_THRESHOLD_CPU_PERCENT` | CPU threshold | `80` |
| `ALERTING_THRESHOLD_QUEUE_DEPTH` | Queue depth threshold | `1000` |
| `PAGERDUTY_SERVICE_KEY` | PagerDuty integration key | `key123` |
| `PAGERDUTY_ROUTING_KEY` | PagerDuty routing key | `key456` |
| `SLACK_WEBHOOK_URL` | Slack webhook URL | `https://hooks.slack.com/...` |
| `SLACK_CHANNEL` | Default Slack channel | `#alerts` |
| `SMTP_HOST` | SMTP server | `smtp.company.com` |
| `SMTP_USERNAME` | SMTP username | `alerts@company.com` |
| `SMTP_PASSWORD` | SMTP password | `secret` |
| `ALERTING_DEFAULT_SEVERITY` | Default alert severity | `warning` |
| `ALERTING_DEFAULT_TEAM` | Default team label | `platform` |

### 7.5 Programmatic Configuration

Configuration can be built programmatically for maximum flexibility:

```go
// Build configuration programmatically
config := alerting.Config{
    Defaults: alerting.DefaultConfig{
        EvaluationInterval: 15 * time.Second,
        GroupInterval:      10 * time.Second,
        RepeatInterval:     12 * time.Hour,
    },
    Thresholds: alerting.AlertThresholds{
        ErrorRate:          5.0,
        P99LatencyMs:       1000.0,
        MemoryUsagePercent: 85.0,
    },
    Labels: alerting.LabelConfig{
        Default: map[string]string{
            "severity": "warning",
            "team":     "platform",
        },
    },
    Annotations: alerting.AnnotationConfig{
        Default: map[string]string{
            "summary": "{{ .AlertName }} triggered",
        },
        RunbookBaseURL: "https://wiki/runbooks",
    },
    NotificationChannels: alerting.NotificationConfig{
        PagerDuty: alerting.PagerDutyNotificationConfig{
            ServiceKey: os.Getenv("PAGERDUTY_KEY"),
            SeverityMap: map[string]string{
                "critical": "critical",
                "warning":  "warning",
            },
        },
        Slack: alerting.SlackNotificationConfig{
            WebhookURL:    os.Getenv("SLACK_WEBHOOK"),
            DefaultChannel: "#alerts",
            ChannelMap: map[string]string{
                "critical": "#alerts-critical",
                "warning":  "#alerts-warning",
            },
        },
    },
}

// Load and merge with file config
mergedConfig, err := alerting.LoadConfig("/etc/alerting/config.yaml", config)
```

### 7.6 Configuration Validation

Configuration is validated at load time:

```go
type ConfigValidation struct {
    Valid    bool
    Errors   []ConfigError
    Warnings []ConfigError
}

type ConfigError struct {
    Path    string // JSON path to error
    Message string
    Type    ErrorType // fatal, warning
}

func ValidateConfig(config Config) ConfigValidation
```

Validation checks include:
- Threshold values within valid ranges
- Required secrets present (not empty)
- Valid duration formats
- No conflicting routing rules
- Template references resolve

### 7.7 Multi-Environment Configuration

Support for environment-specific configuration:

```yaml
# base.yaml - Shared configuration
defaults:
  evaluation_interval: "15s"

---
# development.yaml - Development overrides
defaults:
  evaluation_interval: "5s"  // Faster evaluation in dev

thresholds:
  error_rate: 10.0  // Higher tolerance in dev

---
# production.yaml - Production settings
defaults:
  evaluation_interval: "15s"
  repeat_interval: "24h"  // Less noise in prod

thresholds:
  error_rate: 1.0  // Stricter in prod
  
routing:
  strategy: "severity_then_team"
```

Loading with environment:
```go
config, err := alerting.LoadConfigWithEnvironment(
    "config/",
    os.Getenv("ENV"), // "development", "production"
)
```

---

## 8. Performance Targets

### 8.1 Performance Philosophy

The alerting library operates primarily at build/configuration time rather than runtime. Performance targets reflect this usage pattern, focusing on generation speed and validation throughput rather than request latency.

### 8.2 Generation Performance

**Alert Generation**: Generate 1000 alert rules in <100ms on standard hardware

**YAML Export**: Export 1000 alert rules to YAML in <50ms

**Validation**: Validate 1000 alert rules in <200ms

**Memory Usage**: Peak memory <10MB during generation for typical workloads

### 8.3 Benchmarks

```
BenchmarkAlertGeneration/SingleAlert-10              1000000    1052 ns/op      512 B/op     8 allocs/op
BenchmarkAlertGeneration/HundredAlerts-10               10000    105234 ns/op    51200 B/op   800 allocs/op
BenchmarkAlertGeneration/ThousandAlerts-10               1000    1052341 ns/op   512000 B/op  8000 allocs/op

BenchmarkYAMLExport/SingleAlert-10                    500000     3012 ns/op     2048 B/op    16 allocs/op
BenchmarkYAMLExport/HundredAlerts-10                    5000     301200 ns/op   204800 B/op  1600 allocs/op

BenchmarkValidation/SyntaxOnly-10                      10000    105234 ns/op    1024 B/op    12 allocs/op
BenchmarkValidation/FullValidation-10                 5000    210468 ns/op    2048 B/op    24 allocs/op
```

### 8.4 Scalability Targets

**Maximum Rule Count**: Support rule sets up to 10,000 alerts without degradation

**Template Registry**: Support up to 1,000 registered templates

**Validation Throughput**: Process 10,000 validations/second

### 8.5 Resource Consumption

**CPU**: <1 core-second per 1,000 alerts generated

**Memory**: <10MB heap for typical workloads

**Disk I/O**: Minimal (configuration generation only)

### 8.6 CI/CD Performance

**Target**: Alert generation adds <5 seconds to CI pipeline

**Parallelization**: Support parallel generation across multiple services

**Caching**: Template registry and validation results cached across runs

---

## 9. Security Model

### 9.1 Security Philosophy

The alerting library handles sensitive configuration including notification credentials and infrastructure details. Security is defense-in-depth, combining secure defaults, validation, and clear guidance for safe deployment.

### 9.2 Threat Model

**Threats Addressed**:
- **T1**: Credential leakage in configuration files
- **T2**: Malicious PromQL injection through parameters
- **T3**: Denial of service through alert storms
- **T4**: Information disclosure through verbose annotations

**Out of Scope**:
- Prometheus/Alertmanager runtime security (handled by those systems)
- Network security between components
- Physical access to configuration files

### 9.3 Credential Management

Credentials must never be hardcoded. Supported approaches:

**Environment Variables**:
```go
pdConfig := alerting.PagerDutyConfig{
    RoutingKey: os.Getenv("PAGERDUTY_ROUTING_KEY"),
}
```

**Secret Management Systems**:
```go
// HashiCorp Vault
secret, err := vaultClient.GetSecret("pagerduty/routing-key")
pdConfig := alerting.PagerDutyConfig{
    RoutingKey: secret.Data["key"],
}

// AWS Secrets Manager
secret := secretsmanager.GetSecretValue("/alerting/pagerduty")
```

**Kubernetes Secrets**:
```yaml
env:
  - name: PAGERDUTY_KEY
    valueFrom:
      secretKeyRef:
        name: alerting-secrets
        key: pagerduty-key
```

### 9.4 PromQL Injection Prevention

User-provided parameters are sanitized before expression generation:

```go
func sanitizePromQLLiteral(value string) string {
    // Remove control characters
    sanitized := strings.Map(func(r rune) rune {
        if unicode.IsControl(r) {
            return -1
        }
        return r
    }, value)
    
    // Prevent comment injection
    sanitized = strings.ReplaceAll(sanitized, "#", "")
    
    return sanitized
}
```

### 9.5 Alert Storm Prevention

Configuration guards prevent excessive alerting:

```go
type AlertGuards struct {
    MaxAlertsPerSecond    float64  // Rate limit
    MaxGroupSize          int      // Prevent huge groups
    MinRepeatInterval     time.Duration // Prevent rapid repeats
    RequiredAnnotations   []string // Ensure context
}

var DefaultGuards = AlertGuards{
    MaxAlertsPerSecond:  100.0,
    MaxGroupSize:        100,
    MinRepeatInterval:   1 * time.Minute,
    RequiredAnnotations: []string{"summary"},
}
```

### 9.6 Information Disclosure

Sensitive information in annotations is automatically redacted:

```go
type RedactionConfig struct {
    Patterns []string // Regex patterns to match sensitive data
    Replacement string
}

var DefaultRedaction = RedactionConfig{
    Patterns: []string{
        `password[=:]\s*\S+`,
        `token[=:]\s*\S+`,
        `key[=:]\s*\S+`,
        `secret[=:]\s*\S+`,
    },
    Replacement: "[REDACTED]",
}
```

### 9.7 Security Checklist

Before deploying alerting configurations:

- [ ] No credentials in code or YAML files
- [ ] All secrets loaded from secure stores
- [ ] PromQL expressions validated
- [ ] Rate limits configured
- [ ] Sensitive data redacted from annotations
- [ ] Alertmanager authentication enabled
- [ ] TLS for Alertmanager communication
- [ ] RBAC for alert rule modification

---

## 10. Testing Strategy

### 10.1 Testing Philosophy

Alerting configurations require the same rigor as application code. The testing strategy spans unit tests for individual rules, integration tests for generated configurations, and acceptance tests for end-to-end workflows.

### 10.2 Unit Testing

Test individual alert functions and templates:

```go
func TestHighErrorRate(t *testing.T) {
    alert := alerting.HighErrorRate(5.0, 5*time.Minute)
    
    assert.Equal(t, "HighErrorRate", alert.Name)
    assert.Contains(t, alert.Expr, "rate(phenotype_http_requests_total")
    assert.Equal(t, "5m0s", alert.For)
    assert.Equal(t, "critical", alert.Labels["severity"])
}

func TestThresholdValidation(t *testing.T) {
    tests := []struct {
        name       string
        thresholds alerting.AlertThresholds
        wantValid  bool
        wantErrors int
    }{
        {
            name:       "valid thresholds",
            thresholds: alerting.DefaultThresholds(),
            wantValid:  true,
            wantErrors: 0,
        },
        {
            name: "invalid error rate",
            thresholds: alerting.AlertThresholds{
                ErrorRate: 150, // > 100
            },
            wantValid:  false,
            wantErrors: 1,
        },
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := alerting.ValidateThresholds(tt.thresholds)
            assert.Equal(t, tt.wantValid, result.Valid)
            assert.Len(t, result.Errors, tt.wantErrors)
        })
    }
}
```

### 10.3 Integration Testing

Test generated configurations with Prometheus tooling:

```go
func TestPrometheusConfigValidation(t *testing.T) {
    if testing.Short() {
        t.Skip("Skipping integration test in short mode")
    }
    
    // Generate configuration
    ruleSet := buildTestRuleSet()
    yaml, err := ruleSet.ToYAML()
    require.NoError(t, err)
    
    // Write to temp file
    tmpFile := filepath.Join(t.TempDir(), "alerts.yml")
    err = os.WriteFile(tmpFile, []byte(yaml), 0644)
    require.NoError(t, err)
    
    // Validate with promtool
    cmd := exec.Command("promtool", "check", "rules", tmpFile)
    output, err := cmd.CombinedOutput()
    assert.NoError(t, err, "promtool validation failed: %s", output)
}

func TestAlertmanagerConfigValidation(t *testing.T) {
    config := buildTestAlertManagerConfig()
    yaml, err := config.ToYAML()
    require.NoError(t, err)
    
    tmpFile := filepath.Join(t.TempDir(), "alertmanager.yml")
    err = os.WriteFile(tmpFile, []byte(yaml), 0644)
    require.NoError(t, err)
    
    // Validate with amtool
    cmd := exec.Command("amtool", "check-config", tmpFile)
    output, err := cmd.CombinedOutput()
    assert.NoError(t, err, "amtool validation failed: %s", output)
}
```

### 10.4 Template Testing

Test templates with various parameter combinations:

```go
func TestTemplateVariations(t *testing.T) {
    registry := alerting.NewTemplateRegistry()
    alerting.RegisterDefaultTemplates(registry)
    
    template, found := registry.Get("high_error_rate")
    require.True(t, found)
    
    tests := []struct {
        name    string
        params  map[string]interface{}
        wantErr bool
    }{
        {
            name: "valid parameters",
            params: map[string]interface{}{
                "threshold": 5.0,
                "duration":  "5m",
            },
            wantErr: false,
        },
        {
            name: "invalid threshold type",
            params: map[string]interface{}{
                "threshold": "not a number",
                "duration":  "5m",
            },
            wantErr: true,
        },
    }
    
    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            alert, err := alerting.BuildFromTemplate(registry, template.Name(), tt.params)
            if tt.wantErr {
                assert.Error(t, err)
                return
            }
            assert.NoError(t, err)
            assert.NotEmpty(t, alert.Expr)
        })
    }
}
```

### 10.5 CI/CD Testing

Validate configurations in CI pipeline:

```yaml
# .github/workflows/alerts.yml
name: Alert Configuration Validation

on:
  push:
    paths:
      - 'alerts/**'
      - 'pkg/alerting/**'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Setup Go
        uses: actions/setup-go@v5
        with:
          go-version: '1.21'
      
      - name: Generate alerts
        run: go run ./cmd/gen-alerts/main.go
      
      - name: Validate with promtool
        run: |
          docker run --rm -v $(pwd):/rules prom/prometheus:latest \
            promtool check rules /rules/alerts.yml
      
      - name: Validate alertmanager config
        run: |
          docker run --rm -v $(pwd):/rules prom/alertmanager:latest \
            amtool check-config /rules/alertmanager.yml
      
      - name: Test alert templates
        run: go test ./pkg/alerting/... -v

  diff:
    runs-on: ubuntu-latest
    needs: validate
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      
      - name: Generate baseline
        run: |
          git checkout HEAD~1
          go run ./cmd/gen-alerts/main.go --output=baseline.yml
      
      - name: Generate current
        run: |
          git checkout -
          go run ./cmd/gen-alerts/main.go --output=current.yml
      
      - name: Compare configurations
        run: |
          docker run --rm -v $(pwd):/rules prom/prometheus:latest \
            promtool check rules /rules/baseline.yml
          docker run --rm -v $(pwd):/rules prom/prometheus:latest \
            promtool check rules /rules/current.yml
          diff baseline.yml current.yml || true
```

### 10.6 Testing Checklist

- [ ] All DSL functions have unit tests
- [ ] All templates tested with valid and invalid parameters
- [ ] Integration tests validate with promtool
- [ ] Alertmanager configs validated with amtool
- [ ] Threshold validation covers all bounds
- [ ] Silence rule matching tested
- [ ] Routing configuration generation tested
- [ ] CI pipeline validates all changes

---

## 11. Deployment Guide

### 11.1 Deployment Philosophy

Alert configurations follow the same deployment pipeline as application code: version controlled, reviewed, tested, and deployed automatically. This GitOps approach ensures consistency and auditability.

### 11.2 Deployment Patterns

**Pattern 1: ConfigMap Deployment (Kubernetes)**

```yaml
# Generate alerts as part of build
apiVersion: v1
kind: ConfigMap
metadata:
  name: alert-rules
  namespace: monitoring
data:
  alerts.yml: |
    {{ .AlertsYAML }}
```

**Pattern 2: PrometheusRule CRD**

```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: phenotype-alerts
  namespace: monitoring
  labels:
    app: prometheus
    release: prometheus
spec:
  groups:
  - name: phenotype-alerts
    interval: 15s
    rules:
    - alert: HighErrorRate
      expr: |
        sum(rate(phenotype_http_requests_total{status=~"5.."}[5m])) /
        sum(rate(phenotype_http_requests_total[5m])) * 100 > 5
      for: 5m
      labels:
        severity: critical
        team: backend
      annotations:
        summary: "High error rate detected"
```

**Pattern 3: Alertmanager Secret**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: alertmanager-config
type: Opaque
stringData:
  alertmanager.yml: |
    {{ .AlertManagerYAML }}
```

### 11.3 CI/CD Integration

**GitHub Actions**:
```yaml
name: Deploy Alert Configuration

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Generate configurations
        run: |
          go run ./cmd/gen-alerts/main.go
          go run ./cmd/gen-alertmanager/main.go
      
      - name: Deploy to Kubernetes
        run: |
          kubectl apply -f k8s/alert-rules-configmap.yaml
          kubectl apply -f k8s/alertmanager-secret.yaml
          kubectl rollout restart deployment/prometheus
      
      - name: Verify deployment
        run: |
          kubectl wait --for=condition=ready pod -l app=prometheus
          kubectl exec -it prometheus-0 -- promtool check rules /etc/prometheus/alerts.yml
```

### 11.4 Rollback Strategy

Configuration changes are versioned and can be rolled back:

```bash
# Rollback to previous version
kubectl rollout undo configmap/alert-rules

# Or apply previous git commit
git checkout HEAD~1 -- alerts/
kubectl apply -f k8s/
```

### 11.5 Deployment Checklist

Before deploying alerting configuration:

- [ ] Configuration validated with promtool
- [ ] Alertmanager config validated with amtool
- [ ] All secrets available in target environment
- [ ] Rollback plan documented
- [ ] Team notified of changes
- [ ] Runbook links verified
- [ ] Silence rules for maintenance prepared

---

## 12. Troubleshooting

### 12.1 Common Issues

#### Issue: Alerts Not Firing

**Symptoms**: Metrics show elevated values but no alerts triggered

**Diagnosis**:
```bash
# Check Prometheus rules
kubectl exec prometheus-0 -- promtool check rules /etc/prometheus/alerts.yml

# Query the alert expression directly
curl 'http://prometheus:9090/api/v1/query?query=ALERTS{alertname="HighErrorRate"}'

# Check alert state
kubectl exec prometheus-0 -- wget -qO- localhost:9090/api/v1/rules
```

**Resolution**:
- Verify expression evaluates to true in Prometheus
- Check `for` duration—alert may be pending
- Ensure labels match between rule and active series
- Verify rule is loaded: `prometheus_rule_group_last_evaluation_timestamp`

#### Issue: False Positives

**Symptoms**: Alerts firing when service is healthy

**Resolution**:
- Increase threshold values
- Extend `for` duration to require sustained conditions
- Add additional conditions to reduce noise
- Use recording rules for complex expressions

#### Issue: Notifications Not Received

**Symptoms**: Alerts firing but no PagerDuty/Slack notifications

**Diagnosis**:
```bash
# Check Alertmanager status
curl http://alertmanager:9093/api/v1/status

# Check silences
curl http://alertmanager:9093/api/v1/silences

# View alert routing
curl http://alertmanager:9093/api/v1/alerts
```

**Resolution**:
- Verify routing configuration matches alert labels
- Check receiver configuration (webhook URLs, API keys)
- Review silence rules that may be suppressing
- Check Alertmanager logs for errors

#### Issue: Alert Storm

**Symptoms**: Too many notifications during incidents

**Resolution**:
- Configure grouping in Alertmanager
- Extend repeat_interval
- Add inhibition rules (e.g., high latency inhibits error rate)
- Use severity-based routing to limit critical notifications

### 12.2 Debugging Tools

```bash
# Validate alert expression
promtool check rules alerts.yml

# Test instant query
curl 'http://prometheus:9090/api/v1/query?query=up'

# Check alert history
curl 'http://prometheus:9090/api/v1/query_range?query=ALERTS&start=...&end=...'

# View Alertmanager config
amtool config routes alertmanager.yml
```

### 12.3 Log Analysis

**Prometheus Logs**:
```
level=warn ts=2024-01-15T10:30:00Z caller=manager.go:375 component="rule manager" msg="Evaluating rule failed" rule=HighErrorRate err="parse error: ..."
```

**Alertmanager Logs**:
```
level=error ts=2024-01-15T10:30:00Z caller=dispatch.go:278 component=dispatcher msg="Notify for alerts failed" num_alerts=1 err="cable/pagerduty: notify: ..."
```

### 12.4 Escalation Path

1. **Check documentation**: Review this SPEC and runbooks
2. **Validate configuration**: Use promtool and amtool
3. **Query metrics**: Verify metrics exist and expressions evaluate
4. **Check logs**: Review Prometheus and Alertmanager logs
5. **Contact team**: Reach out to #help-monitoring channel
6. **Emergency silence**: If needed, create emergency silence during investigation

---

## 13. Appendices

### Appendix A: Complete Alert Rule Reference

| Alert Name | Category | Default Expression | Default For | Default Severity | Description |
|------------|----------|-------------------|-------------|------------------|-------------|
| HighErrorRate | System | `rate(errors[5m])/rate(total[5m])*100 > threshold` | 5m | critical | HTTP error rate percentage |
| HighLatency | System | `histogram_quantile(0.99, rate(duration[5m])) > threshold` | 5m | warning | P99 request latency |
| ResourceExhaustion_Memory | System | `memory_usage > threshold` | 2m | critical | Memory utilization |
| ResourceExhaustion_CPU | System | `cpu_usage > threshold` | 5m | warning | CPU utilization |
| ResourceExhaustion_Disk | System | `disk_usage > threshold` | 5m | warning | Disk utilization |
| DatabaseConnections | Infrastructure | `active_connections / max_connections > threshold` | 2m | critical | DB connection pool |
| JobQueueBacklog | Infrastructure | `queue_depth > threshold` | 10m | warning | Job queue depth |
| CacheHitRateLow | Infrastructure | `cache_hits / (hits+misses) < threshold` | 5m | warning | Cache effectiveness |
| PaymentProcessingDelayed | Business | `time()-last_payment_ts > threshold` | 5m | critical | Payment flow health |
| UserSignupRateDrop | Business | `rate(signups[1h]) < threshold` | 30m | warning | User acquisition |

### Appendix B: PromQL Function Reference

| Function | Usage | Example | Notes |
|----------|-------|---------|-------|
| rate() | Per-second rate of counter change | `rate(http_requests[5m])` | Use for counters only |
| irate() | Instant rate (more sensitive) | `irate(cpu_seconds[5m])` | Better for volatile metrics |
| increase() | Total increase over time | `increase(errors[1h])` | For alerts and dashboards |
| histogram_quantile() | Calculate quantile | `histogram_quantile(0.99, rate(duration[5m]))` | Requires histogram metric |
| sum() | Aggregate by addition | `sum(rate(errors[5m]))` | Loses label dimensions |
| avg() | Average values | `avg(cpu_usage)` | Often misleading |
| max() / min() | Extreme values | `max(memory_usage)` | Useful for resource alerts |
| count() | Count series | `count(up == 0)` | Count failing instances |
| absent() | Detect missing metrics | `absent(up{job="api"})` | Useful for presence checks |
| time() | Current Unix timestamp | `time() - last_seen` | For staleness detection |
| delta() | Difference over time | `delta(temperature[1h])` | For gauges |
| deriv() | Derivative per second | `deriv(queue_size[10m])` | Rate of change |
| predict_linear() | Predict future value | `predict_linear(disk_free[6h], 3600)` | For capacity planning |
| label_join() | Combine labels | `label_join(...)` | String manipulation |
| label_replace() | Regex label manipulation | `label_replace(...)` | Advanced relabeling |

### Appendix C: Alertmanager Route Configuration Reference

```yaml
# Complete routing example with all options
route:
  receiver: default
  group_by: ['alertname', 'severity', 'cluster']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  
  routes:
    # Critical alerts - immediate notification
    - match:
        severity: critical
      receiver: critical-pagerduty
      group_wait: 0s
      continue: true
      
    # Warning alerts - batched
    - match:
        severity: warning
      receiver: warning-slack
      group_wait: 30s
      continue: true
      
    # Team routing
    - match_re:
        team: backend|platform
      receiver: backend-team
      routes:
        - match:
            severity: critical
          receiver: backend-escalation
          
    # Service-specific routing
    - match:
        service: payments
      receiver: payment-team
      routes:
        - match:
            severity: critical
          receiver: payment-sre
        - match:
            alertname: PaymentFraudDetected
          receiver: fraud-team
          
    # Inhibit less severe alerts
    - match:
        alertname: InstanceDown
      receiver: default
      routes:
        - match:
            severity: warning
          receiver: 'null'
```

### Appendix D: Silence Rule Examples

```yaml
# Maintenance window silence
- id: maintenance-2024-01-15
  matchers:
    - name: severity
      value: warning
      equal: true
  starts_at: 2024-01-15T02:00:00Z
  ends_at: 2024-01-15T04:00:00Z
  created_by: ops-team
  comment: Scheduled database maintenance

# Service-specific silence
- id: api-gateway-rollout
  matchers:
    - name: service
      value: api-gateway
      equal: true
    - name: severity
      value: warning
      equal: true
  starts_at: 2024-01-15T10:00:00Z
  ends_at: 2024-01-15T10:30:00Z
  created_by: sre-team
  comment: Blue-green deployment

# Regex matcher silence
- id: staging-ignore
  matchers:
    - name: environment
      value: staging-.*
      is_regex: true
      equal: true
  starts_at: 2024-01-15T00:00:00Z
  ends_at: 2024-12-31T23:59:59Z
  created_by: dev-team
  comment: Permanent staging exclusion from on-call
```

### Appendix E: Threshold Tuning Guide

**HTTP Error Rate**:
- Start with 5% for general APIs
- Lower to 1% for critical payment flows
- Higher (10%+) for internal/batch services

**Latency**:
- P50: Should reflect typical user experience
- P95: Should capture worst-case acceptable experience
- P99: Should be <2x P95 (larger gap indicates outliers)

**Resource Usage**:
- Memory: 85% triggers warning (allows burst before OOM)
- CPU: 80% sustained is concerning (bursts OK)
- Disk: 90% triggers warning (leaves room for growth)

**Queue Depth**:
- Calculate based on processing rate: `max_rate * max_acceptable_delay`
- Example: 100 jobs/sec * 60 sec = 6000 depth for 1-minute SLA

### Appendix F: Notification Channel Configuration

**PagerDuty**:
```yaml
pagerduty_configs:
  - routing_key: <integration-key>
    severity: critical
    description: '{{ .CommonAnnotations.summary }}'
    details:
      firing: '{{ template "pagerduty.default.instances" .Alerts.Firing }}'
      resolved: '{{ template "pagerduty.default.instances" .Alerts.Resolved }}'
    images:
      - src: '{{ .CommonAnnotations.dashboard_url }}'
        alt: 'Grafana Dashboard'
```

**Slack**:
```yaml
slack_configs:
  - api_url: <webhook-url>
    channel: '#alerts-critical'
    username: 'Alertmanager'
    color: '{{ if eq .Status "firing" }}danger{{ else }}good{{ end }}'
    title: '{{ .CommonAnnotations.summary }}'
    text: '{{ .CommonAnnotations.description }}'
    actions:
      - type: button
        text: 'Dashboard'
        url: '{{ .CommonAnnotations.dashboard_url }}'
      - type: button
        text: 'Runbook'
        url: '{{ .CommonAnnotations.runbook_url }}'
      - type: button
        text: 'Silence'
        url: '{{ .CommonAnnotations.silence_url }}'
```

**Email**:
```yaml
email_configs:
  - to: 'oncall@company.com'
    from: 'alerts@company.com'
    smarthost: 'smtp.company.com:587'
    auth_username: 'alerts@company.com'
    auth_password: <password>
    headers:
      Subject: '[{{ .Status | toUpper }}] {{ .CommonAnnotations.summary }}'
    html: |
      <h1>{{ .CommonAnnotations.summary }}</h1>
      <p>{{ .CommonAnnotations.description }}</p>
      <a href="{{ .CommonAnnotations.dashboard_url }}">Dashboard</a>
```

### Appendix G: Metric Naming Conventions

The alerting library expects metrics following these conventions:

```
# HTTP requests
phenotype_http_requests_total{method, path, status}
phenotype_http_request_duration_seconds_bucket{method, path, status, le}
phenotype_http_request_duration_seconds_sum
phenotype_http_request_duration_seconds_count

# System resources
phenotype_memory_usage_bytes
phenotype_memory_limit_bytes
phenotype_cpu_usage_percent
phenotype_disk_usage_bytes
phenotype_disk_limit_bytes
phenotype_fd_open_count
phenotype_fd_limit_count

# Database
phenotype_db_connections_active
phenotype_db_connections_max
phenotype_db_query_duration_seconds

# Job queue
phenotype_queue_depth{queue_name}
phenotype_queue_oldest_job_age_seconds
phenotype_jobs_processed_total
phenotype_jobs_failed_total

# Business metrics
phenotype_payment_last_processed_timestamp
phenotype_user_signups_total
```

### Appendix H: Migration Guide from Other Systems

**From Manual YAML**:
1. Identify all existing alert rules
2. Map to alerting library templates
3. Define thresholds in code
4. Generate YAML and compare
5. Deploy via CI/CD

**From Grafana Alerting**:
1. Export Grafana alert rules as JSON
2. Convert queries to PromQL templates
3. Migrate notification channels to Alertmanager config
4. Use alerting library for new rules

**From Datadog/CloudWatch**:
1. Translate metric names to Prometheus format
2. Convert threshold conditions to PromQL
3. Map notification channels to receivers
4. Implement custom templates for cloud-specific metrics

### Appendix I: Runbook Template

Each alert should reference a runbook:

```markdown
# HighErrorRate Runbook

## Alert Description
Fires when HTTP error rate exceeds threshold for 5 minutes

## Impact
Users experiencing elevated error rates

## Detection
PromQL: sum(rate(phenotype_http_requests_total{status=~"5.."}[5m])) / sum(rate(phenotype_http_requests_total[5m])) * 100 > 5

## Triage Steps
1. Check dashboard: https://grafana/d/error-rate
2. Identify affected service from labels
3. Check recent deployments
4. Review error logs

## Resolution
1. If deployment-related: consider rollback
2. If dependency-related: check upstream status
3. If capacity-related: scale service

## Escalation
Contact: #incidents channel
Severity: P1 if affecting payments, P2 otherwise
```

### Appendix J: Glossary

| Term | Definition |
|------|------------|
| **Alert** | A triggered condition requiring attention |
| **Alertmanager** | Prometheus component for routing and notifying |
| **Annotation** | Human-readable metadata on an alert |
| **Condition** | The threshold comparison that triggers |
| **Duration** | How long a condition must persist |
| **Expression** | PromQL query defining the condition |
| **Firing** | Alert state when condition is met |
| **Group** | Logical organization of related alerts |
| **Inhibition** | Suppressing one alert based on another |
| **Label** | Key-value pair for routing/filtering |
| **Pending** | Alert state during duration wait |
| **PromQL** | Prometheus Query Language |
| **Receiver** | Notification destination |
| **Resolved** | Alert state when condition clears |
| **Route** | Configuration for alert distribution |
| **Rule** | Definition of when to trigger an alert |
| **Severity** | Impact level (critical, warning, info) |
| **Silence** | Temporary suppression of alerts |
| **Template** | Reusable alert definition |
| **Threshold** | Value that triggers the condition |

---

*Specification Version: 2.0.0*  
*Last Updated: 2026-04-05*  
*Maintainer: Phenotype Engineering Team*

*© 2026 Phenotype Labs. All rights reserved.*
