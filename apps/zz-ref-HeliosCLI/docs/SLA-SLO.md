# Service Level Agreement (SLA) and Service Level Objectives (SLO) - Helios CLI

## Overview
This document outlines the Service Level Agreement (SLA) and Service Level Objectives (SLO) for the Helios CLI.

## Availability Targets
- **Target Availability:** 99.0%
- **Measurement Period:** Monthly
- **Downtime Budget:** ~7 hours 18 minutes per month

## Response Time Targets
| Metric | Target | Measurement |
|---|---|---|
| Command Execution (p50) | < 500ms | Median response time |
| Command Execution (p99) | < 2s | 99th percentile |
| Authentication Time | < 1s | 95th percentile |
| Help/Doc Lookup | < 200ms | Median local lookup time |

## CLI-Specific Performance SLOs
| Metric | Target | Measurement |
|---|---|---|
| CLI Startup Latency (p95) | < 500ms | Time from invocation to ready prompt |
| `cargo check` / Build Check (p95) | < 120s | Full workspace type-check on clean build |
| Test Suite Wall Time | < 300s | End-to-end `cargo test` including unit + integration |
| CI Pipeline Pass Rate | >= 98% | Rolling 30-day green-run rate on `main` |
| Fuzz Coverage | >= 500 paths / 24h | Unique code paths discovered per 24-hour fuzz run |
| Binary Release Size | < 10 MB | Stripped release binary for tier-1 platforms |
| Config Load Latency (p95) | < 50ms | `HeliosConfig::from_file` parse + env overlay |
| Spec Parse Latency (p95) | < 20ms | `harness_spec::parser::parse_yaml` on <1 KB specs |

## Key SLO Focus Areas
- **CLI Installation Success Rate:** Target 99.5% successful installs across all supported platforms.
- **Command Execution Reliability:** Core commands (run, build, test) should have a failure rate of less than 0.1%.
- **Documentation Freshness:** Documentation should reflect the current version within 24 hours of release.

## Recovery Time Objectives (RTO) & RPO
- **Recovery Time Objective (RTO):** 4 hours
- **Recovery Point Objective (RPO):** N/A (CLI is a stateless local tool)

## Escalation Contacts
1. **P0 - Installation/Execution Failure (> 10% users):** CLI Core Team (Slack: #helios-cli-urgent)
2. **P1 - Specific Command Breakage:** Command Maintainer / Issue Tracker
3. **P2 - Documentation Inaccuracies:** Technical Writing Team

## Measurement Methodology
- Installation success rates measured via telemetry (opt-in) and CI/CD test matrix.
- Execution reliability tracked via community issue reports and automated smoke tests.
- Documentation freshness measured by time between git release tag and doc site build completion.

## Review Schedule
- **Monthly:** Issue resolution and success rate review.
- **Quarterly:** Tooling and documentation audit.
- **Annually:** SLA target recalibration based on user feedback.
