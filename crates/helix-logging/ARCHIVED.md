# ARCHIVED — phenotype-logger

**Status:** This repository has been archived.

## What happened

The crate has been extracted and productized under a neutral name.

## Canonical location

```
https://github.com/phenotype-dev/helix-logging
```

Package name: `helix-logging`

## Migration

Replace in `Cargo.toml`:

```toml
# Old
phenotype-logger = { path = "path/to/phenotype-logger" }

# New
helix-logging = { git = "https://github.com/phenotype-dev/helix-logging" }
```

Replace in source code:

```rust
// Old
use phenotype_logger::{LoggerConfig, LogContext, init};

// New
use helix_logging::{LoggerConfig, LogContext, init};
```

## Timeline

- Archived: 2026-03-26
- Phase 6 productization
