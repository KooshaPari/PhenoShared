# agileplus-domain

![MSRV](https://img.shields.io/badge/MSRV-1.86-blue)
![License](https://img.shields.io/badge/license-MIT-blue)

AgilePlus domain layer: core entities, configuration, credentials, ports, errors, governance, audit, and state-machine models. This crate is intentionally free of runtime I/O.

## Public API Index

- `config` - typed configuration loading and API, agent, credential, and telemetry settings.
- `credentials` - credential stores, keys, factories, memory/file/keychain backends, and credential errors.
- `domain` - business entities including API keys, audit entries, backlog, cycles, events, features, governance contracts, metrics, modules, projects, service health, snapshots, sync mappings, and work packages.
- `error` - domain error types used by services and adapters.
- `ports` - boundary traits for agents, content storage, observability, review, storage, and VCS.

## Build

```bash
cargo build -p agileplus-domain
cargo build -p agileplus-domain --features keychain
cargo build -p agileplus-domain --features plugins
```

