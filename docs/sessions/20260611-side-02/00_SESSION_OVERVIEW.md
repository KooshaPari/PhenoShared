# Side-02 Hexagonal Ports Audit

Scope: audited all 56 crate manifests matching `crates/*/Cargo.toml` for
`src/ports/` directory presence.

Result: 3 crates have a ports directory:

- `agileplus-domain` - 7 files: agent, content, observability, review, storage,
  vcs, module index.
- `agileplus-sqlite` - 4 files: adapter, content_storage, storage_port, module
  index.
- `phenotype-contracts` - 3 files: inbound, outbound, module index.

53 crates do not have `src/ports/`: agileplus-api, agileplus-api-types,
agileplus-benchmarks, agileplus-cache, agileplus-cli, agileplus-contract-tests,
agileplus-error-core, agileplus-events, agileplus-git, agileplus-github,
agileplus-graph, agileplus-grpc, agileplus-import, agileplus-integration-tests,
agileplus-nats, agileplus-p2p, agileplus-plane, agileplus-subcmds,
agileplus-sync, agileplus-telemetry, agileplus-triage, pheno-data-from-phenoData,
phenotype-async-traits, phenotype-cache-adapter, phenotype-casbin-wrapper,
phenotype-contract, phenotype-cost-core, phenotype-crypto, phenotype-error-core,
phenotype-error-macros, phenotype-errors, phenotype-event-sourcing,
phenotype-git-core, phenotype-health, phenotype-http-client-core,
phenotype-iter, phenotype-logging, phenotype-macros, phenotype-mcp,
phenotype-perf-budget, phenotype-policy-engine, phenotype-port-traits,
phenotype-ports-canonical, phenotype-process, phenotype-rate-limit,
phenotype-retry, phenotype-shared-config, phenotype-state-machine,
phenotype-string, phenotype-telemetry, phenotype-test-infra, phenotype-time,
phenotype-validation.

Observation: `phenotype-core/src/lib.rs` defines an inline `ports` module, but
that directory has no `Cargo.toml`; it is not counted as a crate manifest in
this audit.

Validation: `cargo test --workspace` was attempted and failed before tests ran
because Cargo could not resolve `index.crates.io` for dependency download
(`pin-project` for `phenotype-async-traits`).
