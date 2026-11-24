# phenotype-error-core

![MSRV](https://img.shields.io/badge/MSRV-1.75-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

Canonical error types for Phenotype crates. Use this crate to keep API, domain, repository, configuration, storage, and wire-format errors consistent across the workspace.

## Public API Index

- `ApiError` - transport-facing error enum with HTTP status mapping and retryability checks.
- `DomainError` - business-rule, validation, invariant, state-transition, policy, and permission errors.
- `RepositoryError` - persistence errors for records, connections, queries, serialization, sequence gaps, and integrity.
- `ConfigError` - configuration loading, parsing, environment, and validation errors.
- `StorageError` - low-level I/O, not-found, permission, capacity, and connection errors.
- `ErrorEnvelope` - serializable JSON/API error envelope.
- `ErrorContext` - extension trait for adding context to generic `Result` errors.

## Build

```bash
cargo build -p phenotype-error-core
```

