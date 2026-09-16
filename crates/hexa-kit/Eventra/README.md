# Eventra

Event-driven architecture framework with CQRS and Event Sourcing.

**Status**: Integrated into PhenoEvents/pheno-events/

This directory previously contained a git submodule. The actual implementation has been merged into the PhenoEvents repository.

## Migration

- Source: <REDACTED>/Eventra (archived)
- Target: PhenoEvents/pheno-events/
- Crate: eventkit

## Features

- Event Sourcing with append-only event storage
- CQRS with separate read/write models
- Projections for building read models
- Snapshots for state optimization
- Event upcasting for schema evolution

## License

MIT OR Apache-2.0
