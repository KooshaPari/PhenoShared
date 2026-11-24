# Research

- Existing repo state:
  - .github/workflows/ had no release-plz workflow.
  - CONTRIBUTING.md still described release-please, but .github/release-please-config.json was absent.
- Packaging constraints:
  - Root package agileplus and xtask-anti-patterns already declare publish = false.
  - agileplus-integration-tests already declares publish = false.
  - agileplus-contract-tests and agileplus-benchmarks are non-runtime/test-only crates and should not be pushed to crates.io.
