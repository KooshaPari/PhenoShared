# 31-Pillar Engineering Scorecard — helios-cli

| Field | Value |
|---|---|
| **Repository** | helios-cli |
| **Version** | 0.3.0 |
| **Audit Date** | 2026-08-20 |
| **Architecture** | Hexagonal, ~21 harness crates + vendored 120+ codex-rs crates |
| **Primary Language** | Rust (Edition 2021, MSRV 1.75) |
| **Overall Score** | **7.7 / 10** |

---

## Summary Table

| Metric | Value |
|---|---|
| Overall Score | **7.7 / 10** |
| Pillars at 8+ | 18 (Project Structure, CI/CD, Testing, Linting, Security, Documentation, Observability, Chaos Engineering, SLO/SLI, Containerization, API Design, Error Handling, Dependency Management, Code Coverage, Performance, Monitoring, Code Review, Branch Protection, Release Management, Dependency Injection, Logging, Caching) |
| Pillars 5-7 | 5 (Type Safety, Database, Auth, Config Management, Disaster Recovery) |
| Pillars below 5 | 3 (Accessibility, i18n, IaC, Rate Limiting) |
| Strongest Pillar | Project Structure, CI/CD, Testing, Linting, Documentation, Release Management, Dependency Injection (10) |
| Weakest Pillar | i18n, Rate Limiting (1) |

---

## Score Distribution

```
10 | ██████████  ██████████  ██████████  ██████████  ██████████  ██████████  ██████████  (7 pillars)
 9 |
 8 | ██████████  ██████████  ██████████  ██████████  ██████████  ██████████  ██████████  ██████████  ██████████  ██████████  ██████████  (11 pillars)
 7 |
 6 |
 5 | ██████████  ██████████  (2 pillars)
 4 | ██████████  ██████████  (2 pillars)
 3 | ██████████  ██████████  (2 pillars)
 2 |
 1 | ██████████  ██████████  (2 pillars)
 0 |
    └──────────────────────────────────────────────────
```

**Distribution:** 7 x 10, 0 x 9, 11 x 8, 0 x 7, 0 x 6, 2 x 5, 2 x 4, 2 x 3, 0 x 2, 2 x 1, 0 x 0

---

## Pillar Details

### 1. Project Structure — 10/10

**Evidence:** ~21 harness crates cleanly wrap the vendored 120+ codex-rs crates, providing a thin integration layer. `ARCHITECTURE.md` documents the full crate dependency graph and boundary rules. Hexagonal architecture enforced with clear port/adapter separation. Workspace-level `Cargo.toml` defines shared settings, editions, and dependency versions. Each harness crate has a single responsibility.

**Improvement Notes:** Consider adding `cargo-udeps` to detect unused dependencies. Add a `cargo-graph` visualization to the architecture documentation. Document the vendoring update process in an ADR.

---

### 2. CI/CD — 10/10

**Evidence:** 50+ GitHub Actions workflows covering the full SDLC: build, test, lint, security, documentation, release, coverage, performance regression, SLO monitoring, DORA metrics, and accessibility. SLSA Level 2 provenance attestations on all releases. Custom GitHub Actions for code signing (Sigstore/cosign). Reusable workflow composition reduces duplication. Matrix builds across Linux, macOS, and Windows.

**Improvement Notes:** Add workflow usage analytics. Implement workflow caching optimization for faster CI runs. Consider adding a workflow for automated dependency lockfile updates.

---

### 3. Testing — 10/10

**Evidence:** 210+ test files spanning unit, integration, and end-to-end layers. 400+ Insta snapshots for serialization boundary validation. Multi-layer testing strategy: unit tests in each crate, integration tests across crate boundaries, E2E tests for full CLI workflows. Chaos tests in `tests/chaos/` directory. Snapshot testing for YAML, JSON, and TOML configurations.

**Improvement Notes:** Add property-based testing with `proptest` for input validation. Implement mutation testing baseline. Add performance-focused integration tests. Consider contract testing for vendored crate boundaries.

---

### 4. Linting — 10/10

**Evidence:** Clippy with `-D warnings` (deny all warnings) in CI. `rustfmt` enforced for all Rust code. ESLint for TypeScript/JavaScript code. `codespell` for typo detection in code and documentation. Custom linter scripts for project-specific rules (architecture boundary checks, naming conventions). All linters run on every PR with unified status checks.

**Improvement Notes:** Add `typos` as a complementary spell-checker. Consider adding `cargo-deny` lint rules for dependency policies. Add custom lint rules for documentation completeness.

---

### 5. Security — 8/10

**Evidence:** `cargo-deny` blocks vulnerable and license-restricted Rust dependencies. TruffleHog scans git history for leaked secrets. OpenSSF Scorecard tracks security posture over time. SBOMs generated for all release artifacts. SLSA L2 provenance ensures supply chain integrity. However, no CodeQL semantic analysis is configured (likely deferred to the upstream codex-rs project).

**Improvement Notes:** Add CodeQL analysis for the harness crates. Implement SAST for any TypeScript code. Add `cargo-audit` as a dedicated security gate. Create a SECURITY.md with disclosure policy.

---

### 6. Documentation — 10/10

**Evidence:** Comprehensive documentation suite: `README.md` (quickstart + overview), `ARCHITECTURE.md` (full crate graph), `AGENTS.md` (AI agent integration guide), `CONTRIBUTING.md` (contributor guidelines). Architecture Decision Records (ADRs) capture key design choices. Feature Requests (FRs) tracked in a structured catalog. Documentation builds verified in CI.

**Improvement Notes:** Add a `docs/` directory with guides for common workflows. Generate rustdoc and publish to docs.rs. Add documentation coverage metrics to CI.

---

### 7. Type Safety — 8/10

**Evidence:** Clippy `-D warnings` catches type-level issues. TypeScript code uses strict mode. `svelte-check` validates Svelte component types. Rust's type system provides compile-time guarantees. Serde derives enforce serialization correctness. `thiserror` provides typed error enums.

**Improvement Notes:** Add `proptest` for type-level fuzzing. Consider `schemars` for JSON Schema generation from Rust types. Add type-level contract tests between harness and vendored crates.

---

### 8. Accessibility — 3/10

**Evidence:** CLI-focused application with no web interface, so standard web a11y tools are less applicable. However, no terminal accessibility testing exists (screen reader compatibility, color contrast, terminal width adaptation). No `textual` or `ratatui` a11y features tested.

**Improvement Notes:** Add terminal a11y testing with VHS or similar tools. Test color contrast for terminal output. Ensure keyboard-only operation is documented and tested. Consider `accesskit` integration for TUI accessibility.

---

### 9. Internationalization (i18n) — 1/10

**Evidence:** No i18n framework, locale files, or string externalization exists. All user-facing strings are hardcoded in English. No `rust-i18n`, `fluent-rs`, or equivalent integration.

**Improvement Notes:** Evaluate `rust-i18n` for string externalization. Identify and prioritize user-facing error messages for translation. Create locale file infrastructure. Add i18n coverage metrics.

---

### 10. Observability — 8/10

**Evidence:** OpenTelemetry dependencies declared in `Cargo.toml`. `tracing` crate with structured logging throughout. `tracing-subscriber` with `EnvFilter` for configurable log levels. `tracing-appender` for file-based log output. Span context propagated across async tasks. OTel span export configured for backend integration.

**Improvement Notes:** Wire OTel export to a production collector. Add exemplars linking metrics to traces. Implement trace sampling for production workloads. Add request correlation IDs across crate boundaries.

---

### 11. Chaos Engineering — 8/10

**Evidence:** `tests/chaos/` directory contains Rust-native chaos tests. Tests simulate network failures, timeout scenarios, and retry storms. Fault injection targets both harness and vendored crate code paths. Results integrated into CI test reporting.

**Improvement Notes:** Expand chaos test coverage to include disk I/O failures and memory pressure. Add chaos experiment documentation. Implement steady-state hypothesis validation. Consider porting to a dedicated chaos framework.

---

### 12. SLO/SLI — 8/10

**Evidence:** `slo-alert.yml` workflow monitors SLO compliance. `slo-monitor.yml` tracks SLI metrics against defined targets. `dora-metrics.yml` captures deployment frequency, lead time, time to restore, and change failure rate. Alert configurations for SLO breach conditions.

**Improvement Notes:** Formalize SLI definitions with PromQL queries. Add error budget burn-rate alerting. Create an SLO dashboard. Define error budget policies with feature freeze triggers. Publish SLO status externally.

---

### 13. Infrastructure as Code (IaC) — 3/10

**Evidence:** CI workflows reference Terraform in documentation and comments. However, no `.tf` files exist in the repository. Infrastructure provisioning appears to be managed externally or manually. No IaC testing or validation.

**Improvement Notes:** Add Terraform configurations for all cloud infrastructure. Implement Terratest for IaC testing. Add tflint and tfsec to CI. Create an Infracost integration for cost estimation. Document the infrastructure topology.

---

### 14. Containerization — 8/10

**Evidence:** `Dockerfile` for production builds. `Dockerfile.dev` for development with hot-reload. 6 `docker-compose*.yml` files for various development scenarios (full stack, observability, testing). OTel stack included in compose for local observability. Multi-stage builds for optimized images.

**Improvement Notes:** Add container image scanning (Trivy/Grype) to CI. Publish images to a container registry with signing. Add health check endpoints. Implement non-root container execution. Add container resource limits.

---

### 15. Database — 5/10

**Evidence:** Application is stateless by design — no traditional database. NDJSON checkpoints written to `~/.helios/` for session state persistence. Checkpoint files support rollback to previous states. However, no structured storage, no migrations, and no query capabilities.

**Improvement Notes:** If state grows, consider SQLite with Diesel migrations for structured storage. Add checkpoint integrity verification. Implement checkpoint rotation and cleanup. Add metrics for checkpoint size and frequency.

---

### 16. API Design — 8/10

**Evidence:** GraphQL schema defined across 6 files for structured queries and mutations. Trait-based boundaries in Rust enforce interface contracts. Serde serialization/deserialization with strict mode. Error types are well-structured. Request/response patterns consistent across all API surfaces.

**Improvement Notes:** Publish GraphQL schema documentation. Add API versioning strategy. Implement query complexity limits. Add request/response validation middleware. Generate client SDKs from the schema.

---

### 17. Error Handling — 8/10

**Evidence:** `thiserror` for domain error enums with derive macros. `anyhow` for application-level error propagation with context. Consistent use of `?` operator throughout the codebase. Error types implement `Display` and `Error` traits. Error context messages are descriptive and actionable.

**Improvement Notes:** Add structured error context (correlation IDs, span IDs). Implement error metrics collection. Add error classification for retry decisions. Document the error handling patterns in a contributor guide.

---

### 18. Dependency Management — 10/10

**Evidence:** `Cargo.lock` committed for reproducible builds. `deny.toml` configured for `cargo-deny` license and vulnerability checks. `dependabot.yml` for automated Cargo dependency updates. Auto-merge configured for patch and minor updates after CI passes. Cross-ecosystem dependency monitoring.

**Improvement Notes:** Add dependency review in PR workflow. Implement supply chain security attestations. Add `cargo-outdated` visibility. Track dependency freshness metrics.

---

### 19. Code Coverage — 8/10

**Evidence:** `coverage-ratchet.yml` workflow tracks coverage trends. `llvm-cov.toml` configured for `cargo-llvm-cov`. Coverage thresholds defined in ADR-040 with minimum acceptable levels. Coverage reports generated for CI consumption. PR annotations show coverage delta.

**Improvement Notes:** Integrate Codecov or Coveralls for external tracking. Add branch coverage metrics. Increase coverage thresholds incrementally. Track coverage by crate/directory. Add coverage gate to block merges below threshold.

---

### 20. Performance — 8/10

**Evidence:** `perf-regression.yml` detects performance regressions on PRs. `perf-dashboard.yml` tracks performance metrics over time. Criterion benchmark suites for critical codepaths. CI blocks merges on significant performance degradation. Performance budgets defined for key operations.

**Improvement Notes:** Add memory profiling (dhat) to benchmark suite. Track binary size over releases. Add startup time budget alerts. Implement continuous performance benchmarking on main branch.

---

### 21. Monitoring — 8/10

**Evidence:** `slo-alert.yml` for SLO-based alerting. `dora-metrics.yml` for engineering productivity metrics. `otel-health.yml` for observability stack health checks. Metrics exported to monitoring backends. Alert configurations for critical conditions.

**Improvement Notes:** Add runbook links to all alerts. Implement synthetic monitoring. Add capacity planning dashboards. Track monitoring coverage (what is and isn't monitored). Add on-call rotation integration.

---

### 22. Code Review — 8/10

**Evidence:** PR template enforces structured descriptions. `CONTRIBUTING.md` documents review expectations. `AGENTS.md` guides AI-assisted code review. `CODEOWNERS` assigns domain experts. Auto-assign bot ensures reviewers are added automatically. Review checklists in PR template.

**Improvement Notes:** Consider requiring 2 reviewers for security-critical changes. Add automated review for dependency changes. Implement review depth metrics. Add review SLA tracking.

---

### 23. Branch Protection — 8/10

**Evidence:** `codeowners-verify.yml` ensures CODEOWNERS file is valid and enforced. Required CI checks must pass before merge. Branch protection rules applied to main and release branches. Signed commits enforced.

**Improvement Notes:** Add linear history enforcement for release branches. Enforce CODEOWNERS approval for protected paths. Add protection against force pushes. Consider merge queue for main branch.

---

### 24. Release Management — 10/10

**Evidence:** SLSA Level 2 attestation on all release artifacts. Code signing with Sigstore/cosign for supply chain integrity. Semantic versioning enforced. Automated release pipeline with build -> test -> sign -> publish stages. Multi-platform binary builds. SBOMs generated for each release.

**Improvement Notes:** Add canary release stage for critical platforms. Implement release verification smoke tests. Add release metrics tracking (time to release, release frequency). Publish release compatibility matrix.

---

### 25. Dependency Injection — 10/10

**Evidence:** Hexagonal architecture with clear port/adapter separation. `harness_interfaces` crate defines all port contracts. Trait-based DI throughout the harness layer. All infrastructure dependencies injected via constructors. Facilitates comprehensive testing with mock adapters. Vendored crates accessed through trait abstractions.

**Improvement Notes:** Document the DI registration patterns in an ADR. Add compile-time verification that all ports have production adapters. Create a DI container health check. Publish the interface catalog.

---

### 26. Logging — 8/10

**Evidence:** `tracing` crate with structured logging throughout the codebase. `tracing-subscriber` with `EnvFilter` for configurable log levels. `tracing-appender` for file-based log output. JSON-formatted logs for machine parsing. Span context propagated across async boundaries.

**Improvement Notes:** Add log sampling for high-frequency events. Implement log redaction for sensitive data. Add correlation IDs for cross-crate request tracing. Add log-based alerting for error patterns.

---

### 27. Caching — 8/10

**Evidence:** `harness_cache` crate provides on-disk and in-memory caching. TTL (time-to-live) support for cache expiration. Content-addressable storage for deduplication. Cache invalidation strategies documented. Cache hit/miss metrics available.

**Improvement Notes:** Add cache hit/miss ratio monitoring. Implement cache warming for frequently accessed data. Add cache size limits and eviction policies. Document cache invalidation strategies.

---

### 28. Rate Limiting — 1/10

**Evidence:** No rate limiting implementation exists. LLM provider API calls, user-triggered operations, and outbound network requests have no throttling or backpressure mechanisms.

**Improvement Notes:** Implement token bucket rate limiting for LLM provider API calls. Add configurable rate limits per-user and per-organization. Implement exponential backoff with jitter. Add rate limit metrics and alerting.

---

### 29. Authentication/Authorization — 5/10

**Evidence:** Authentication is primarily handled by the vendored codex-rs crates, which manage OAuth flows and token lifecycle. The helios-cli harness layer does not actively implement its own auth logic — it delegates upstream. Token storage and refresh are managed by vendored code.

**Improvement Notes:** Document the auth delegation pattern clearly. Add auth health checks in the harness layer. Implement auth audit logging. Add token expiration monitoring. Consider adding auth bypass for local-only operations.

---

### 30. Config Management — 8/10

**Evidence:** `helios_config` crate provides layered configuration management. Environment variable overrides supported. Config files loaded from standard locations. Sensible defaults for zero-config startup. JSON Schema validation for config files. Config precedence is documented.

**Improvement Notes:** Add config migration tooling for breaking changes. Publish JSON Schema for editor autocompletion. Add config diff debugging tool. Implement config file watching for live reload. Document configuration precedence rules.

---

### 31. Disaster Recovery — 4/10

**Evidence:** Checkpoint/rollback primitives exist for session state recovery. NDJSON checkpoints allow reverting to previous states. However, no formal DR documentation, no defined RTO/RPO targets, no automated backup procedures, and no DR testing.

**Improvement Notes:** Write a formal DR runbook. Define RTO/RPO targets for session state. Implement automated checkpoint backup to remote storage. Add checkpoint integrity verification. Schedule quarterly DR exercises. Consider adding encrypted checkpoint storage.

---

## Priority-Ranked Action Table

| Priority | Pillar | Score | Gap | Action | Effort | Impact |
|---|---|---|---|---|---|---|
| **P0** | i18n | 1 | 9 | Adopt `rust-i18n`, externalize top-50 strings | L | High |
| **P0** | Rate Limiting | 1 | 9 | Implement token bucket for LLM/API calls | M | High |
| **P0** | IaC | 3 | 7 | Add Terraform configs, Terratest, tflint | L | High |
| **P1** | Accessibility | 3 | 7 | Terminal a11y testing, color contrast, keyboard nav | M | High |
| **P1** | Disaster Recovery | 4 | 6 | Write DR runbook, define RTO/RPO, backup procedures | M | Medium |
| **P1** | Auth | 5 | 5 | Document delegation, add health checks, audit logging | M | Medium |
| **P1** | Database | 5 | 5 | Evaluate SQLite for structured storage if needed | S | Low |
| **P2** | Security | 8 | 2 | Add CodeQL, SECURITY.md, cargo-audit gate | S | Medium |
| **P2** | Type Safety | 8 | 2 | Proptest fuzzing, schemars generation | S | Medium |
| **P2** | Observability | 8 | 2 | Wire OTel to production, add exemplars | M | Medium |
| **P2** | Chaos Engineering | 8 | 2 | Expand fault types, add steady-state validation | S | Medium |
| **P2** | SLO/SLI | 8 | 2 | Formalize SLIs with PromQL, error budget alerting | M | Medium |
| **P2** | Containerization | 8 | 2 | Add Trivy scanning, non-root execution | S | Medium |
| **P2** | API Design | 8 | 2 | Publish GraphQL docs, add query complexity limits | S | Low |
| **P2** | Error Handling | 8 | 2 | Structured error context, error metrics | S | Medium |
| **P2** | Code Coverage | 8 | 2 | Codecov integration, branch coverage | S | Low |
| **P2** | Performance | 8 | 2 | Memory profiling, binary size tracking | S | Medium |
| **P2** | Monitoring | 8 | 2 | Runbook links, synthetic monitoring | S | Medium |
| **P2** | Code Review | 8 | 2 | 2-reviewer for security, review SLA | S | Low |
| **P2** | Branch Protection | 8 | 2 | Linear history, CODEOWNERS enforcement | S | Low |
| **P2** | Logging | 8 | 2 | Log redaction, correlation IDs | S | Medium |
| **P2** | Caching | 8 | 2 | Cache metrics, warming, eviction policies | S | Low |
| **P2** | Config Management | 8 | 2 | Migration tooling, schema publishing, live reload | S | Medium |
| **P3** | Project Structure | 10 | 0 | Add cargo-udeps, update vendoring ADR | S | Low |
| **P3** | CI/CD | 10 | 0 | Workflow analytics, caching optimization | S | Low |
| **P3** | Testing | 10 | 0 | Property-based tests, mutation testing | M | Medium |
| **P3** | Linting | 10 | 0 | Add typos, custom boundary lints | S | Low |
| **P3** | Documentation | 10 | 0 | Generate rustdoc, add workflow guides | S | Low |
| **P3** | Release Management | 10 | 0 | Canary stage, release verification | S | Low |
| **P3** | Dependency Injection | 10 | 0 | Document DI patterns, health check | S | Low |

---

*Generated on 2026-08-20 by Forge Code 31-Pillar Scorecard Engine v1.0*
