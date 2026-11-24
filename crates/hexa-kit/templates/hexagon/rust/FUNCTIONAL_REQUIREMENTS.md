# Functional Requirements: Phenotype Kits Workspace

## FR-KIT-001: Workspace Structure
The workspace SHALL define all kit crates in a single `Cargo.toml` workspace manifest.

## FR-KIT-002: clikit — CLI Framework
FR-KIT-002a: clikit SHALL provide a `CliApp` builder that registers subcommands via trait objects.
FR-KIT-002b: clikit SHALL support skill dispatch — routing subcommand invocations to registered `Skill` trait implementations.
FR-KIT-002c: clikit SHALL emit structured exit codes (0=success, 1=usage error, 2=runtime error).

## FR-KIT-003: agentkit — Agent Framework
FR-KIT-003a: agentkit SHALL define an `Agent` trait with `spawn()`, `send_message()`, and `terminate()` methods.
FR-KIT-003b: agentkit SHALL support async message passing via tokio channels.
FR-KIT-003c: agentkit SHALL expose `AgentHandle` for lifecycle management from parent context.

## FR-KIT-004: evalkit — Evaluation Framework
FR-KIT-004a: evalkit SHALL provide `EvalHarness` for running scored evaluation suites.
FR-KIT-004b: evalkit SHALL support assertion types: exact match, fuzzy match, contains, regex.
FR-KIT-004c: evalkit SHALL produce a machine-readable `EvalReport` (JSON/TOML).

## FR-KIT-005: taskkit — Task Execution
FR-KIT-005a: taskkit SHALL support sequential and parallel task graphs via DAG execution.
FR-KIT-005b: taskkit SHALL support per-task timeouts and retry policies.
FR-KIT-005c: taskkit SHALL emit task lifecycle events (started, completed, failed, retried).

## FR-KIT-006: configkit — Configuration Management
FR-KIT-006a: configkit SHALL load configuration from layered sources: defaults < file < env < flags.
FR-KIT-006b: configkit SHALL support TOML, YAML, and JSON configuration files.
FR-KIT-006c: configkit SHALL validate configuration against a schema and report all errors at startup.

## FR-KIT-007: authkit — Auth/AuthZ Framework
FR-KIT-007a: authkit SHALL validate JWT tokens with configurable key sources (JWKS, static secret).
FR-KIT-007b: authkit SHALL implement RBAC policy evaluation with allow/deny rules.
FR-KIT-007c: authkit SHALL expose a `PolicyEnforcer` trait for custom policy adapters.

## FR-KIT-008: cachekit — Caching Abstraction
FR-KIT-008a: cachekit SHALL define a `Cache<K, V>` trait with get, set, delete, and TTL.
FR-KIT-008b: cachekit SHALL provide an in-memory LRU adapter and a Redis adapter.
FR-KIT-008c: cachekit SHALL support cache stampede prevention (single-flight pattern).

## FR-KIT-009: Error Handling
All kit crates SHALL use `thiserror` for error types and expose domain-specific error enums. No `unwrap()` or `expect()` in library code.

## FR-KIT-010: Documentation
All public APIs SHALL have rustdoc documentation including at least one `# Example` section.

