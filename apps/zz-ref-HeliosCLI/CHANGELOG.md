# Changelog

All notable changes to **HeliosCLI** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.11.11](https://github.com/KooshaPari/HeliosCLI/compare/v0.11.10...v0.11.11) (2026-10-17)


### Bug Fixes

* **deps:** bump quinn-proto 0.11.17→0.11.19, rustls 0.23.43→0.23.45 ([254e690](https://github.com/KooshaPari/HeliosCLI/commit/254e690952de9dcf83f41c505cd0567b196301f8))

## [0.11.10](https://github.com/KooshaPari/HeliosCLI/compare/v0.11.9...v0.11.10) (2026-10-08)


### Bug Fixes

* **deps:** bump aws-smithy-json to 0.62.7 for GHSA-8ffr-xgwf-xj56 (alert [#133](https://github.com/KooshaPari/HeliosCLI/issues/133)) ([bd1656d](https://github.com/KooshaPari/HeliosCLI/commit/bd1656de65fe66b1f27b69c587d9a423a889aba8))

## [0.11.9](https://github.com/KooshaPari/HeliosCLI/compare/v0.11.8...v0.11.9) (2026-10-04)


### Bug Fixes

* **ci:** paths-ignore release files on pull_request (race-proof zero-job fix) ([6b80c26](https://github.com/KooshaPari/HeliosCLI/commit/6b80c269d03822dd6e59a3ae566d9032ddf5fde8))

## [0.11.8](https://github.com/KooshaPari/HeliosCLI/compare/v0.11.7...v0.11.8) (2026-10-04)


### Bug Fixes

* **ci:** skip pull_request runs on release-please branch (zero-job merge race) ([8e3c0af](https://github.com/KooshaPari/HeliosCLI/commit/8e3c0af0b355ce0fc94064e0d0f495a5f125cfaa))

## [0.11.7](https://github.com/KooshaPari/HeliosCLI/compare/v0.11.6...v0.11.7) (2026-10-02)


### Bug Fixes

* **ci:** pin attest-build-provenance to v2.1.0 SHA ([#692](https://github.com/KooshaPari/HeliosCLI/issues/692)) ([2bde7c4](https://github.com/KooshaPari/HeliosCLI/commit/2bde7c434bfd59a861989ec38d97a4ca55926f25))

## [0.11.6](https://github.com/KooshaPari/HeliosCLI/compare/v0.11.5...v0.11.6) (2026-10-02)


### Bug Fixes

* **ci:** least-privilege permissions for 8 workflows ([#692](https://github.com/KooshaPari/HeliosCLI/issues/692)) ([e979e2a](https://github.com/KooshaPari/HeliosCLI/commit/e979e2aad5de1cae7cd14c91ac78ac1568705c7d))

## [0.11.5](https://github.com/KooshaPari/HeliosCLI/compare/v0.11.4...v0.11.5) (2026-10-01)


### Bug Fixes

* **deps:** security bumps for 9 open Dependabot alerts ([#124](https://github.com/KooshaPari/HeliosCLI/issues/124)-[#132](https://github.com/KooshaPari/HeliosCLI/issues/132)) ([0122ace](https://github.com/KooshaPari/HeliosCLI/commit/0122aced97c9cbd6d1547df722eff1837e17645c))
* **mergify:** release-please PRs are authored by github-actions[bot] ([76d37f1](https://github.com/KooshaPari/HeliosCLI/commit/76d37f1132f241c3b0418b86a2efeabbec35331e))

## [0.11.4](https://github.com/KooshaPari/HeliosCLI/compare/v0.11.3...v0.11.4) (2026-10-01)


### Bug Fixes

* **ci:** attestations:write for release attest + pin actions (workflow audit) ([4aa2b40](https://github.com/KooshaPari/HeliosCLI/commit/4aa2b40d6efb5585ec86bb92f4147a2a09e36521))

## [0.11.3](https://github.com/KooshaPari/HeliosCLI/compare/v0.11.2...v0.11.3) (2026-09-29)


### Bug Fixes

* **ci:** grant issues:write to codex-upstream-sync (403'd on 6 straight weekly runs) ([7f93fed](https://github.com/KooshaPari/HeliosCLI/commit/7f93fed2585d614b59ecb421fc5807cc9955f8d8))

## [0.11.2](https://github.com/KooshaPari/HeliosCLI/compare/v0.11.1...v0.11.2) (2026-09-27)


### Bug Fixes

* **harness:** honor circuit breaker recovery threshold ([df7cc3a](https://github.com/KooshaPari/HeliosCLI/commit/df7cc3a7ebe77647a2800306e71257e99e418608))

## [0.11.1](https://github.com/KooshaPari/HeliosCLI/compare/v0.11.0...v0.11.1) (2026-09-24)


### Performance Improvements

* **model-provider:** raise models refresh HTTP timeout from 5s to 30s ([#681](https://github.com/KooshaPari/HeliosCLI/issues/681)) ([0b32b61](https://github.com/KooshaPari/HeliosCLI/commit/0b32b61e325038a66511f4e83b88ceee31777439))

## [0.11.0](https://github.com/KooshaPari/HeliosCLI/compare/v0.10.3...v0.11.0) (2026-09-20)


### Features

* **network-proxy:** migrate rama 0.3.0-alpha.4 -&gt; 0.3.0, clearing both hickory alerts ([#675](https://github.com/KooshaPari/HeliosCLI/issues/675)) ([a118c1a](https://github.com/KooshaPari/HeliosCLI/commit/a118c1af88c83f56f3bd03f6f60762c07ebb4b9a))


### Bug Fixes

* add missing serde imports to helios-ai/persistence.rs ([1c33985](https://github.com/KooshaPari/HeliosCLI/commit/1c33985e1ed38525cd430e516c99765875c6878a))
* **bazel:** point llvm flag at toolchains_llvm_bootstrapped, stop MODULE.bazel.lock drift ([#676](https://github.com/KooshaPari/HeliosCLI/issues/676)) ([f03532b](https://github.com/KooshaPari/HeliosCLI/commit/f03532bb63a515c6736a2287f7c092ce21c21c3e))
* **ci:** add rust-toolchain step before cargo-deny ([51191b0](https://github.com/KooshaPari/HeliosCLI/commit/51191b0af71e005ede462cc5904046d42e5ed020))
* **ci:** clear remaining dependabot advisories and unblock codex-rs fmt ([ae6fde8](https://github.com/KooshaPari/HeliosCLI/commit/ae6fde847897575be23f81df549c5032a492b98b))
* **ci:** job-level continue-on-error in v8-canary so runner-allocation failures do not fail the run ([408af36](https://github.com/KooshaPari/HeliosCLI/commit/408af360d909eb108e7dc24b06f1e264e7f24dad))
* **ci:** regenerate argument-comment-lint Cargo.lock with conflict markers in it ([c93f8e3](https://github.com/KooshaPari/HeliosCLI/commit/c93f8e32575223e775479f9fbeb12449826fca9d))
* **ci:** restore the bench-smoke recipe the Format job invokes ([9a01f36](https://github.com/KooshaPari/HeliosCLI/commit/9a01f36248e2eb934f19de1334a061430c3d0457))
* **ci:** stop rust-ci-full jobs that can never acquire a runner ([1dee523](https://github.com/KooshaPari/HeliosCLI/commit/1dee523f99312be2fff79b3f80626a88ee5817a3))
* **deps:** address Dependabot security alerts ([6e2057d](https://github.com/KooshaPari/HeliosCLI/commit/6e2057dd4cdaa08e60a702399fe71ee8b137487b))
* **deps:** bump openssl, actix-http, cmov and pyo3 past advisories ([d221085](https://github.com/KooshaPari/HeliosCLI/commit/d221085c3ad6dc0a4ca53873ca98771ae9f36a67))
* **deps:** bump ratatui 0.29-&gt;0.30, crossterm 0.28-&gt;0.29, lru 0.12-&gt;0.18 ([d86e5cb](https://github.com/KooshaPari/HeliosCLI/commit/d86e5cb5b7584c205fd563e780cfa34a93e1ee44))
* **deps:** bump rmcp 1.8-&gt;3.4, opentelemetry 0.31-&gt;0.32, reqwest otel 0.12-&gt;0.13 ([4119318](https://github.com/KooshaPari/HeliosCLI/commit/4119318e5b67a1c42e97d198ee992ed247be44cb))
* **deps:** bump transitive Rust deps for Dependabot alerts ([107ee16](https://github.com/KooshaPari/HeliosCLI/commit/107ee164cd68bc57d8347a1becad5c735b2457f8))
* **deps:** prune stale `atty` from root Cargo.lock ([585de76](https://github.com/KooshaPari/HeliosCLI/commit/585de7674de046fd90189298a11cbfb3ca1d54c4))
* **deps:** replace dead rich-cli-kit git dep with local rck-core stub ([70fa6dd](https://github.com/KooshaPari/HeliosCLI/commit/70fa6ddcc02f2f0dd83d95361c156aa828c2cf02))
* **helios-ai:** remove unused Delta import in sse.rs ([fe8bb2f](https://github.com/KooshaPari/HeliosCLI/commit/fe8bb2f7e42ce586d5682c3ded62aa0e575fb164))
* **mcp-server:** name task methods in unsupported-request replies ([c59396a](https://github.com/KooshaPari/HeliosCLI/commit/c59396acffab06e085f04ee2c4c235acb01464a3))
* **mcp:** complete rmcp 1.8 -&gt; 3.4 migration for test targets ([eaeba90](https://github.com/KooshaPari/HeliosCLI/commit/eaeba901c9b318fe3832163f75ae0acaa580555d))
* **mergify:** correct action name to delete_head_branch (delete_branch is invalid and broke the whole config) ([32af8ed](https://github.com/KooshaPari/HeliosCLI/commit/32af8edeed7c59f35df3177474e9328deefb85fe))
* **model-provider-info:** reject ws://http:// double-scheme base_url ([#672](https://github.com/KooshaPari/HeliosCLI/issues/672)) ([429160f](https://github.com/KooshaPari/HeliosCLI/commit/429160f27ad80b1c58ebf9e4fb8f2b3523cbb7ed))
* remove unused imports in harness_verify test module flagged by clippy ([3a4e268](https://github.com/KooshaPari/HeliosCLI/commit/3a4e268a75e8e899eecad85c1c0ceadac1d258e0))
* remove useless .map_err(Into::into) flagged by clippy ([0c75ed3](https://github.com/KooshaPari/HeliosCLI/commit/0c75ed33ce68ca9abd5a1f7b8a3f2971e00946e4))
* **repo:** repair manifests zeroed and mis-indented by 3f44dec84 ([3ee9313](https://github.com/KooshaPari/HeliosCLI/commit/3ee93133675661959a5a2f995ec9b74d096a2960))
* resolve CI failures from decomposition and new advisories ([ade819b](https://github.com/KooshaPari/HeliosCLI/commit/ade819b3bd602de1726b9f7e926fce62086aeaaf))
* resolve clap short flag collision causing debug_assert panic ([0c8cdd2](https://github.com/KooshaPari/HeliosCLI/commit/0c8cdd217422a9ab08b9d1b5b990f2bba65c93cc))
* resolve test compilation error and unused import warnings ([17cbfdb](https://github.com/KooshaPari/HeliosCLI/commit/17cbfdbd9a716f5d1c288674fe6202d01d25c1f3))
* **rmcp-client:** migrate rmcp 1.8 -&gt; 3.4 API changes (lib + all bins) ([da7ba96](https://github.com/KooshaPari/HeliosCLI/commit/da7ba9603945bbdc6a6541a44ca211ca9de1975d))
* **sdk:** resolve npm advisories, declare phantom deps, fix Windows test path ([f2ca4b7](https://github.com/KooshaPari/HeliosCLI/commit/f2ca4b7ffc83cdab388a38be403ffb935d6729cf))

## [0.10.3](https://github.com/KooshaPari/HeliosCLI/compare/v0.10.2...v0.10.3) (2026-09-16)


### Bug Fixes

* **mergify:** migrate commit_message_template to commit_message_format ([0e3f2c6](https://github.com/KooshaPari/HeliosCLI/commit/0e3f2c6a1d17cb7caad071fa7908618100e0a349))

## [0.10.2](https://github.com/KooshaPari/helios-cli/compare/v0.10.1...v0.10.2) (2026-09-08)


### Bug Fixes

* **harness:** preserve JSON and UTF-8 prompt caps ([#665](https://github.com/KooshaPari/helios-cli/issues/665)) ([19d749d](https://github.com/KooshaPari/helios-cli/commit/19d749d894e01ff6e0029cbbcd7d61cfbacb737c))

## [0.10.1](https://github.com/KooshaPari/helios-cli/compare/v0.10.0...v0.10.1) (2026-09-04)


### Bug Fixes

* clear dead_code CI gate + CRITICAL vitest CVE ([#663](https://github.com/KooshaPari/helios-cli/issues/663)) ([2c3f4d6](https://github.com/KooshaPari/helios-cli/commit/2c3f4d6ca212a9ccd1a14bce0b9347b5ae60a598))

## [0.10.0](https://github.com/KooshaPari/helios-cli/compare/v0.9.0...v0.10.0) (2026-09-02)


### Features

* **harness:** wire RollbackEngine to query CheckpointStore when local git_sha is absent ([#657](https://github.com/KooshaPari/helios-cli/issues/657)) ([9fe8840](https://github.com/KooshaPari/helios-cli/commit/9fe8840da518f7da89e9a0e3a7ef3cd1b6f12f61))


### Bug Fixes

* **ci:** install jq before Trunk Check ([#662](https://github.com/KooshaPari/helios-cli/issues/662)) ([8afcce6](https://github.com/KooshaPari/helios-cli/commit/8afcce664ecba264849903285db46a4768953be4))
* **mergify:** add owner-only auto-merge rule for KooshaPari PRs ([077879d](https://github.com/KooshaPari/helios-cli/commit/077879d87494b4bf088564b7854e0bd9d9dfc341))

## [0.9.0](https://github.com/KooshaPari/helios-cli/compare/v0.8.1...v0.9.0) (2026-09-02)


### Features

* **release:** sign + notarize helios-cli (v3) ([#658](https://github.com/KooshaPari/helios-cli/issues/658)) ([e98058c](https://github.com/KooshaPari/helios-cli/commit/e98058ccc72e5fdd74916e266b1d4a4caecd4498))

## [0.8.1](https://github.com/KooshaPari/helios-cli/compare/v0.8.0...v0.8.1) (2026-09-02)


### Bug Fixes

* **harness:** restore strict benchmark envelopes ([#652](https://github.com/KooshaPari/helios-cli/issues/652)) ([9bb96d7](https://github.com/KooshaPari/helios-cli/commit/9bb96d7c7b8d80412d2161aa900dc0ad94bda0fe))
* **harness:** address codeant nitpicks + enforce prompt cap (AP-ITEM:6 H-05R1) ([#655](https://github.com/KooshaPari/helios-cli/issues/655)) ([90de6ae](https://github.com/KooshaPari/helios-cli/commit/90de6aed3e1a78485116f840257765301cc218f2))
* unblock AP-ITEM:4 — clean Cargo.lock + clear CI gates ([#651](https://github.com/KooshaPari/helios-cli/issues/651)) ([3c6c289](https://github.com/KooshaPari/helios-cli/commit/3c6c28906f1f2d36c4b09b8537e842f62b32b3ce))

## [0.8.0] - 2026-08-31

### Added

- **tui**: ratatui-based terminal UI scaffold ([`6469cc5`](https://github.com/KooshaPari/helios-cli/commit/6469cc5))
- **tui**: add ratatui-based terminal UI scaffold ([`efead0a`](https://github.com/KooshaPari/helios-cli/commit/efead0a))

### Changed

- fix Landlock file descriptor type (#648) ([#648](https://github.com/KooshaPari/helios-cli/pull/648))

### Fixed

- **ai**: upgrade reqwest to clear cargo-deny advisories (#647) ([#647](https://github.com/KooshaPari/helios-cli/pull/647))
- **verify**: resolve strict Clippy warnings (AP-ITEM:1) (#646) ([#646](https://github.com/KooshaPari/helios-cli/pull/646))

## [0.7.0] - 2026-08-31

### Added

- **cost**: add token usage tracking and budget limits to agent loop ([`ab910b4`](https://github.com/KooshaPari/helios-cli/commit/ab910b4))
- **sandbox**: implement real Landlock sandboxing for helios exec ([`e16440a`](https://github.com/KooshaPari/helios-cli/commit/e16440a))
- add SSE streaming and approval policies ([`13b7cfa`](https://github.com/KooshaPari/helios-cli/commit/13b7cfa))
- **helios-ai**: add session persistence and helios resume (H-E3) ([`43425da`](https://github.com/KooshaPari/helios-cli/commit/43425da))
- **helios-tools**: add FileEditTool crate for agent file operations (H-E2) ([`cfb66b8`](https://github.com/KooshaPari/helios-cli/commit/cfb66b8))
- **helios**: add exec agent loop stub (H-E1) ([`cb4f2be`](https://github.com/KooshaPari/helios-cli/commit/cb4f2be))

### Tests

- make-zero-timeout-deterministic (#641) ([#641](https://github.com/KooshaPari/helios-cli/pull/641))

### Documentation

- **governance**: track HeliosCLI work externally in AgilePlus (#644) ([#644](https://github.com/KooshaPari/helios-cli/pull/644))
- **readme**: add AI slop inside + downloads badges ([`d4f4e0c`](https://github.com/KooshaPari/helios-cli/commit/d4f4e0c))

### Maintenance

- update Cargo.lock ([`f94b6ca`](https://github.com/KooshaPari/helios-cli/commit/f94b6ca))

## [0.6.0] - 2026-08-28

### Added

- **run**: add --sandbox flag for platform-aware sandboxing ([`877512f`](https://github.com/KooshaPari/helios-cli/commit/877512f))
- **helios**: add multi-turn chat mode (--chat flag) and performance/security verify rules ([`513ab53`](https://github.com/KooshaPari/helios-cli/commit/513ab53))
- **verify**: implement Performance rule with real benchmark execution ([`af16424`](https://github.com/KooshaPari/helios-cli/commit/af16424))
- **ai**: add helios-ai crate with OpenAI-compatible client ([`4176b67`](https://github.com/KooshaPari/helios-cli/commit/4176b67))
- **helios**: wire harness_recorder as kla dependency, fix split_matches error ([`11d859a`](https://github.com/KooshaPari/helios-cli/commit/11d859a))
- **helios**: add e2e tests, remove harness_recorder dead crate, add codex sync marker ([`e312dbc`](https://github.com/KooshaPari/helios-cli/commit/e312dbc))
- **helios**: unified binary wiring harness_queue, runner, rollback, checkpoint ([`1d15745`](https://github.com/KooshaPari/helios-cli/commit/1d15745))
- **rollback**: integrate with harness_checkpoint for real git restoration ([`8bb5a2d`](https://github.com/KooshaPari/helios-cli/commit/8bb5a2d))

### Changed

- rust-ci-unblock-deterministic-timeout-and-clippy (#643) ([#643](https://github.com/KooshaPari/helios-cli/pull/643))

### Fixed

- **verify**: add metacharacter check to Custom rule, fix test assertion ([`7432021`](https://github.com/KooshaPari/helios-cli/commit/7432021))
- add try_send to Channel<T> and implement KLA convert subcommand ([`fdf036f`](https://github.com/KooshaPari/helios-cli/commit/fdf036f))
- **helios**: improve screenshot font, add helios binary tests, remove dead code ([`cd8f752`](https://github.com/KooshaPari/helios-cli/commit/cd8f752))
- **runner**: prevent shell command injection in shell mode ([`d7c7831`](https://github.com/KooshaPari/helios-cli/commit/d7c7831))
- **kla**: implement GIF recording (capture frames + write output) ([`f7ef099`](https://github.com/KooshaPari/helios-cli/commit/f7ef099))
- avoid-clippy-single-match (#640) ([#640](https://github.com/KooshaPari/helios-cli/pull/640))
- **kla**: wire binary to use library crate modules, remove duplicate mod declarations ([`e5ded92`](https://github.com/KooshaPari/helios-cli/commit/e5ded92))

### Build

- restrict-rust-workflow-token-permissions (#639) ([#639](https://github.com/KooshaPari/helios-cli/pull/639))
- **upstream**: add weekly Codex upstream sync check workflow ([`62b5c7a`](https://github.com/KooshaPari/helios-cli/commit/62b5c7a))

### Tests

- use-io-error-other-constructor (#642) ([#642](https://github.com/KooshaPari/helios-cli/pull/642))

### Maintenance

- update Cargo.lock after harness_recorder removal ([`dbbf8fe`](https://github.com/KooshaPari/helios-cli/commit/dbbf8fe))
- remove dead harness_scaling crate from helios-cli ([`56fb18c`](https://github.com/KooshaPari/helios-cli/commit/56fb18c))
- add codex upstream sync marker ([`26cb670`](https://github.com/KooshaPari/helios-cli/commit/26cb670))
- remove local audit/build artifacts ([`d589c01`](https://github.com/KooshaPari/helios-cli/commit/d589c01))

## [0.5.0] - 2026-08-21

### Added

- **unified**: M3 - Unified search, notification center, embedded Tracera/AgilePlus panels, command palette enhancement ([`b8a8697`](https://github.com/KooshaPari/helios-cli/commit/b8a8697))
- **agents**: M2 - Agent management panel, task queue, log viewer, Tracera/AgilePlus integration ([`69ed4c9`](https://github.com/KooshaPari/helios-cli/commit/69ed4c9))
- **desktop**: M1 - Helios Command Center dashboard with Tauri 2, repo monitoring, and CI status ([`bde424f`](https://github.com/KooshaPari/helios-cli/commit/bde424f))

### Fixed

- **kla**: add missing clap::Subcommand import to fix workspace build ([`a4a384e`](https://github.com/KooshaPari/helios-cli/commit/a4a384e))

### Build

- **scorecard**: add automated 88-pillar scorecard CI ([`24342ce`](https://github.com/KooshaPari/helios-cli/commit/24342ce))
- add 88-pillar scorecard workflow for regression prevention ([`2070386`](https://github.com/KooshaPari/helios-cli/commit/2070386))

### Tests

- **harness**: add unit tests to harness_queue, harness_runner, harness_rollback, and helios_config ([`86afb2e`](https://github.com/KooshaPari/helios-cli/commit/86afb2e))

### Maintenance

- **deps**: bump opentelemetry_sdk from 0.22.1 to 0.32.1 (#637) ([#637](https://github.com/KooshaPari/helios-cli/pull/637))
- **cleanup**: remove GUI scaffolding, i18n stubs, OTel configs, Terraform, and 27 scaffolding CI workflows ([`1d29470`](https://github.com/KooshaPari/helios-cli/commit/1d29470))
- **quality**: add missing gates ([`60645bd`](https://github.com/KooshaPari/helios-cli/commit/60645bd))

## [0.4.0] - 2026-08-20

### Added

- **sre**: add SLO alerting, OTel deployment scripts, terraform validate CI ([`a32d976`](https://github.com/KooshaPari/helios-cli/commit/a32d976))
- **sre**: add SLO monitoring, Terraform CI validation, and performance dashboard ([`20a1265`](https://github.com/KooshaPari/helios-cli/commit/20a1265))
- **sre**: add chaos CI gate, Terraform IaC, SLO burn rate alerting, and OTel collector config ([`edf00f3`](https://github.com/KooshaPari/helios-cli/commit/edf00f3))

### Build

- **bench**: add benchmark workflow ([`e44fa6a`](https://github.com/KooshaPari/helios-cli/commit/e44fa6a))

### Maintenance

- **ci**: update otel-deploy workflow for SLO monitoring integration ([`6e5f962`](https://github.com/KooshaPari/helios-cli/commit/6e5f962))
- **ci**: update slo-monitor, terraform-plan workflows; add otel scripts ([`293d088`](https://github.com/KooshaPari/helios-cli/commit/293d088))
- **quality**: add fuzz, mutation, benchmark scaffolds ([`3417373`](https://github.com/KooshaPari/helios-cli/commit/3417373))
- add deploy scripts, otel workflows, fuzz targets, terraform modules, slo alerting ([`2f9752d`](https://github.com/KooshaPari/helios-cli/commit/2f9752d))

## [0.3.0] - 2026-08-20

### Added

- **infra**: add OpenTelemetry, chaos testing, perf dashboard, and multi-region docs ([`24c45db`](https://github.com/KooshaPari/helios-cli/commit/24c45db))
- **fuzz**: add corpus seeds, perf trend tracking, and SLA/SLO docs ([`271983b`](https://github.com/KooshaPari/helios-cli/commit/271983b))
- **testing**: add fuzz harnesses, wire i18n into CLI, 3 new locales, and codeowners verification ([`81ea651`](https://github.com/KooshaPari/helios-cli/commit/81ea651))
- **devex**: add ADRs, DORA metrics, Docker dev env, and incident response playbook ([`b5dabc1`](https://github.com/KooshaPari/helios-cli/commit/b5dabc1))
- add i18n Rust module and locale files, perf baselines ([`fcf0eb1`](https://github.com/KooshaPari/helios-cli/commit/fcf0eb1))
- add integration tests, release-please, SBOM workflow, and i18n locales ([`94415dd`](https://github.com/KooshaPari/helios-cli/commit/94415dd))
- **metrics**: add observability metrics collector with tests + dashboard workflow ([`e60efee`](https://github.com/KooshaPari/helios-cli/commit/e60efee))
- **i18n**: add internationalization scaffolding with English locale ([`e480687`](https://github.com/KooshaPari/helios-cli/commit/e480687))
- **agileplus**: bootstrap full AgilePlus setup with 31-pillar scorecard, sprint tracking, quality gates ([`d24cc21`](https://github.com/KooshaPari/helios-cli/commit/d24cc21))
- **helios**: land benchmark-provenance + harness-preservation + toolchain-refresh (#628) ([#628](https://github.com/KooshaPari/helios-cli/pull/628))
- **harness_runner**: dual-harness shared-3task fixture adapter ([`d7c718e`](https://github.com/KooshaPari/helios-cli/commit/d7c718e))
- **harness_recorder**: absorb KLA (KommandLineAutomation) as harness_recorder crate (L5-200) (#600) ([#600](https://github.com/KooshaPari/helios-cli/pull/600))
- **absorb**: add CHANGELOG.md + justfile from HeliosCLI final wave ([`ae2f311`](https://github.com/KooshaPari/helios-cli/commit/ae2f311))
- **absorb**: complete HeliosCLI absorption (build configs + docs + artifacts + 6 crates) ([`f743027`](https://github.com/KooshaPari/helios-cli/commit/f743027))
- **absorb**: merge HeliosCLI workspace (20 crates + root config + 9 dirs) into helios-cli ([`fc6a792`](https://github.com/KooshaPari/helios-cli/commit/fc6a792))
- **dashboard**: migrate UI components from helios-router ([`1f4df51`](https://github.com/KooshaPari/helios-cli/commit/1f4df51))

### Fixed

- **ci**: replace broken trunk-action with prettier-scoped check (#631) ([#631](https://github.com/KooshaPari/helios-cli/pull/631))
- **ci**: restore working trunk config on main (#629) ([#629](https://github.com/KooshaPari/helios-cli/pull/629))
- **ci**: restore working trunk config on main ([`2eb20d4`](https://github.com/KooshaPari/helios-cli/commit/2eb20d4))
- **ci**: migrate trunk.yaml to schema v0.1 (lint/fmt blocks) (#626) ([#626](https://github.com/KooshaPari/helios-cli/pull/626))
- **ci**: pin codeql upload-sarif to valid v3.37.6 SHA in scorecard (#624) ([#624](https://github.com/KooshaPari/helios-cli/pull/624))
- **ci**: pin trunk-action to valid v1.3.1 SHA in trunk-check (#623) ([#623](https://github.com/KooshaPari/helios-cli/pull/623))
- **ci**: restore main CI (#622) ([#622](https://github.com/KooshaPari/helios-cli/pull/622))
- **codex-rs**: use ReviewDecision::Denied for mcp-server approvals ([`343b7c2`](https://github.com/KooshaPari/helios-cli/commit/343b7c2))
- **codex-rs**: restore tui animation frame assets from snapshot ([`eec6db7`](https://github.com/KooshaPari/helios-cli/commit/eec6db7))
- **codex-rs**: restore explorer builtin role config ([`50cdd8f`](https://github.com/KooshaPari/helios-cli/commit/50cdd8f))
- **codex-rs**: restore web_search_detail from snapshot ([`c4e9e32`](https://github.com/KooshaPari/helios-cli/commit/c4e9e32))
- **codex-rs**: restore 6 missing include and source files ([`7846d4c`](https://github.com/KooshaPari/helios-cli/commit/7846d4c))
- **codex-rs**: restore 57 missing source files from snapshot ([`eed4e1d`](https://github.com/KooshaPari/helios-cli/commit/eed4e1d))
- **codex-rs**: restore additional missing upstream source modules ([`00e9504`](https://github.com/KooshaPari/helios-cli/commit/00e9504))
- **codex-rs**: restore login pkce module ([`f067ce4`](https://github.com/KooshaPari/helios-cli/commit/f067ce4))
- **codex-rs**: restore agent_job model for helios fork state runtime ([`a58572b`](https://github.com/KooshaPari/helios-cli/commit/a58572b))
- **codex-rs**: restore workspace_acl and config overrides modules ([`f63dc3f`](https://github.com/KooshaPari/helios-cli/commit/f63dc3f))
- **codex-rs**: restore missing secrets sanitizer and otel metrics modules ([`f96ff48`](https://github.com/KooshaPari/helios-cli/commit/f96ff48))
- **codex-rs**: sync state model from upstream and restore backfill_state ([`d19d576`](https://github.com/KooshaPari/helios-cli/commit/d19d576))
- **codex-rs**: restore file-search and utils/cli sources from upstream ([`463a6a6`](https://github.com/KooshaPari/helios-cli/commit/463a6a6))
- **codex-rs**: restore missing openapi-models and protocol sources ([`fe6d878`](https://github.com/KooshaPari/helios-cli/commit/fe6d878))
- **codex-rs**: TransportError url as String + rustls aws_lc_rs ([`a2aa4cb`](https://github.com/KooshaPari/helios-cli/commit/a2aa4cb))
- **codex-client**: add url dep for TransportError ([`3c2b322`](https://github.com/KooshaPari/helios-cli/commit/3c2b322))
- **codex-rs**: starlark 0.14 + restore codex-client error module ([`9fdab01`](https://github.com/KooshaPari/helios-cli/commit/9fdab01))
- **codex-rs**: align sqlx 0.9 + v8 149 for sqlite links ([`09cba62`](https://github.com/KooshaPari/helios-cli/commit/09cba62))
- **codex-rs**: restore json-to-toml and prune missing workspace members ([`d6a0dd9`](https://github.com/KooshaPari/helios-cli/commit/d6a0dd9))
- **codex-rs**: restore codex-skills crate manifest from upstream ([`feab082`](https://github.com/KooshaPari/helios-cli/commit/feab082))
- **codex-rs**: backfill workspace deps for codex-cli manifest graph ([`e161c7c`](https://github.com/KooshaPari/helios-cli/commit/e161c7c))
- **codex-rs**: add model-provider crates to workspace manifest ([`1c83322`](https://github.com/KooshaPari/helios-cli/commit/1c83322))
- **ci**: apply rustfmt for coverage test modules ([`3e89105`](https://github.com/KooshaPari/helios-cli/commit/3e89105))
- **ci**: gate kla PTY test_settings on target OS for clippy ([`b0df018`](https://github.com/KooshaPari/helios-cli/commit/b0df018))
- **recorder**: avoid duplicate logger initialization ([`ee70a02`](https://github.com/KooshaPari/helios-cli/commit/ee70a02))
- **ci**: close PR gates with AgilePlus trace ([`68872cd`](https://github.com/KooshaPari/helios-cli/commit/68872cd))
- **ci**: load .codespellrc in Codespell workflow ([`95212a8`](https://github.com/KooshaPari/helios-cli/commit/95212a8))
- **ci**: ignore transitive rustsec advisories; skip codespell noise ([`3745d19`](https://github.com/KooshaPari/helios-cli/commit/3745d19))
- **ci**: hard-fork harness green - ascii, deny, disable bazel/sdk/ACL ([`97cc436`](https://github.com/KooshaPari/helios-cli/commit/97cc436))
- **p3**: clippy clean + fmt + test coverage (#603) ([#603](https://github.com/KooshaPari/helios-cli/pull/603))
- **ci**: apply oxfmt formatting to workflow files and docs (#582) ([#582](https://github.com/KooshaPari/helios-cli/pull/582))
- **ci**: add codex-cli/README.md stub required by ASCII check CI (#581) ([#581](https://github.com/KooshaPari/helios-cli/pull/581))
- **ci**: replace em-dash with ASCII hyphen in README (asciicheck fix) (#580) ([#580](https://github.com/KooshaPari/helios-cli/pull/580))
- **ci**: add root README.md required by ASCII check CI step (#579) ([#579](https://github.com/KooshaPari/helios-cli/pull/579))
- **ci**: use python3 explicitly for script invocations (permission fix) (#578) ([#578](https://github.com/KooshaPari/helios-cli/pull/578))
- **ci**: add missing scripts/asciicheck.py and readme_toc.py from upstream (#577) ([#577](https://github.com/KooshaPari/helios-cli/pull/577))
- **helios-cli**: add workspace.dependencies to resolve criterion reference (#563) ([#563](https://github.com/KooshaPari/helios-cli/pull/563))
- **ci**: resolve merge conflict markers and invalid action refs in ci.yml (#574) ([#574](https://github.com/KooshaPari/helios-cli/pull/574))
- **workspace**: unblock codex-rs cargo resolution (#570) ([#570](https://github.com/KooshaPari/helios-cli/pull/570))
- resolve merge conflicts in codex-rs workspace (143 tests passing) (#559) ([#559](https://github.com/KooshaPari/helios-cli/pull/559))

### Build

- add release-please config, dependabot auto-merge, and auto-assign reviewers ([`b4012f6`](https://github.com/KooshaPari/helios-cli/commit/b4012f6))
- **coverage**: add coverage ratchet workflow with PR comments and main-branch auto-update ([`cb0c4bf`](https://github.com/KooshaPari/helios-cli/commit/cb0c4bf))
- add Infisical integration workflow ([`5b98dcf`](https://github.com/KooshaPari/helios-cli/commit/5b98dcf))
- update workflow with stable lint/test gate names ([`0181849`](https://github.com/KooshaPari/helios-cli/commit/0181849))
- update .github/workflows/ci.yml ([`36349bb`](https://github.com/KooshaPari/helios-cli/commit/36349bb))
- add .pre-commit-config.yaml ([`1334f12`](https://github.com/KooshaPari/helios-cli/commit/1334f12))
- add .trunk/trunk.yaml ([`684293a`](https://github.com/KooshaPari/helios-cli/commit/684293a))
- add .github/stale.yml ([`394a22c`](https://github.com/KooshaPari/helios-cli/commit/394a22c))
- add renovate.json ([`d06650c`](https://github.com/KooshaPari/helios-cli/commit/d06650c))
- add .github/workflows/scorecard.yml ([`1626bd0`](https://github.com/KooshaPari/helios-cli/commit/1626bd0))
- add .github/workflows/trunk-check.yml ([`ed05200`](https://github.com/KooshaPari/helios-cli/commit/ed05200))
- add CircleCI parallel pipeline ([`c353c41`](https://github.com/KooshaPari/helios-cli/commit/c353c41))
- add Trunk.io lint/format config ([`fd7984d`](https://github.com/KooshaPari/helios-cli/commit/fd7984d))
- add Mergify auto-merge rules ([`66d0d56`](https://github.com/KooshaPari/helios-cli/commit/66d0d56))
- fix pnpm lockfile config mismatch (use --no-frozen-lockfile) ([`491e8a8`](https://github.com/KooshaPari/helios-cli/commit/491e8a8))
- SonarCloud advisory (non-blocking main CI) (#575) ([#575](https://github.com/KooshaPari/helios-cli/pull/575))
- add FUNDING.yml (GitHub Sponsors link) ([`d53c19f`](https://github.com/KooshaPari/helios-cli/commit/d53c19f))
- add trufflehog secrets scan ([`3f261b7`](https://github.com/KooshaPari/helios-cli/commit/3f261b7))
- SHA-pin setup-python (fix corrupted SHA typo in v8/rusty workflows) ([`78773ee`](https://github.com/KooshaPari/helios-cli/commit/78773ee))
- SHA-pin GitHub Actions (normalize to canonical SHAs) ([`96b92c1`](https://github.com/KooshaPari/helios-cli/commit/96b92c1))

### Tests

- **coverage**: reach 86.44% line coverage; refresh CI evidence ([`ee5ab61`](https://github.com/KooshaPari/helios-cli/commit/ee5ab61))
- **coverage**: expand harness tests; record 68% line cov evidence ([`56a268a`](https://github.com/KooshaPari/helios-cli/commit/56a268a))
- **ci**: enforce complete WP02 traceability ([`711c7db`](https://github.com/KooshaPari/helios-cli/commit/711c7db))

### Documentation

- **coverage**: record final 86.44% gate metrics for PR #604 ([`855a642`](https://github.com/KooshaPari/helios-cli/commit/855a642))
- **governance**: add AGENTS.md with ratatui fork SOTA exception (L5-104) (#598) ([#598](https://github.com/KooshaPari/helios-cli/pull/598))
- **rationalization**: add triage notes for issue #596 (#597) ([#597](https://github.com/KooshaPari/helios-cli/pull/597))
- add work-state header to README (#583) ([#583](https://github.com/KooshaPari/helios-cli/pull/583))
- add SECURITY.md vulnerability reporting policy (#565) ([#565](https://github.com/KooshaPari/helios-cli/pull/565))
- **rationalization**: block helioscope full subtree into helios-cli (#569) ([#569](https://github.com/KooshaPari/helios-cli/pull/569))
- **iconography**: complete Fluent + Material icon sets (20+20) (#560) ([#560](https://github.com/KooshaPari/helios-cli/pull/560))
- **iconography**: add combined icons.svg sprite ([`22ce02a`](https://github.com/KooshaPari/helios-cli/commit/22ce02a))
- add journey-traceability + iconography ([`2ec31bb`](https://github.com/KooshaPari/helios-cli/commit/2ec31bb))
- fix README title to Helios-CLI (avoids camel/hyphen collision) ([`9d1ee2c`](https://github.com/KooshaPari/helios-cli/commit/9d1ee2c))
- add helios-cli sladge badge ([`4846607`](https://github.com/KooshaPari/helios-cli/commit/4846607))

### Maintenance

- **quality**: add 2 missing quality pillar files ([`30f122b`](https://github.com/KooshaPari/helios-cli/commit/30f122b))
- add Makefile and pre-commit CI workflow ([`1c3b4fd`](https://github.com/KooshaPari/helios-cli/commit/1c3b4fd))
- **deps**: add Dependabot config for Go modules, GitHub Actions, and npm ([`e8f0182`](https://github.com/KooshaPari/helios-cli/commit/e8f0182))
- **deps-dev**: bump datamodel-code-generator in /sdk/python (#615) ([#615](https://github.com/KooshaPari/helios-cli/pull/615))
- **deps**: bump nanoid from 3.3.11 to 3.3.16 (#621) ([#621](https://github.com/KooshaPari/helios-cli/pull/621))
- **deps**: inline ffi_utils to parking_lot (phenotype-shared deleted) (#627) ([#627](https://github.com/KooshaPari/helios-cli/pull/627))
- capture wip/2026-08-02-helios-cli-m7 (audit 2026-07-24..08-02) (#617) ([#617](https://github.com/KooshaPari/helios-cli/pull/617))
- **harness**: consolidate benchmark envelope work ([`945b6bb`](https://github.com/KooshaPari/helios-cli/commit/945b6bb))
- auto-commit daemon 2026-07-19T11:46:34Z ([`8f223cf`](https://github.com/KooshaPari/helios-cli/commit/8f223cf))
- preserve meaningful local work (20260717-0307) ([`5ed81be`](https://github.com/KooshaPari/helios-cli/commit/5ed81be))
- **L5-130**: replace stale 'Helioscope' references in helios-cli docs (#599) ([#599](https://github.com/KooshaPari/helios-cli/pull/599))
- **audit**: v37 overhaul - clippy clean, tests green, CI + ARCHITECTURE ([`5bca5d4`](https://github.com/KooshaPari/helios-cli/commit/5bca5d4))
- upstream/main into fork main (superset) ([`4723d2c`](https://github.com/KooshaPari/helios-cli/commit/4723d2c))
- add deny.toml for cargo-deny guardrail ([`3c975d3`](https://github.com/KooshaPari/helios-cli/commit/3c975d3))
- close duplicate PR #571 (workspace deps landed via #527) (#571) ([#571](https://github.com/KooshaPari/helios-cli/pull/571))
- **deps**: bump tar in /tools/argument-comment-lint (#572) ([#572](https://github.com/KooshaPari/helios-cli/pull/572))
- **ci**: adopt reusable workflow templates (#573) ([#573](https://github.com/KooshaPari/helios-cli/pull/573))
- **deps**: bump rmcp from 0.15.0 to 1.4.0 in /codex-rs (#566) ([#566](https://github.com/KooshaPari/helios-cli/pull/566))
- **deps**: bump openssl from 0.10.78 to 0.10.80 in /codex-rs (#567) ([#567](https://github.com/KooshaPari/helios-cli/pull/567))
- **deps**: bump tar from 0.4.45 to 0.4.46 in /codex-rs (#568) ([#568](https://github.com/KooshaPari/helios-cli/pull/568))
- **cargo-deny**: remove stale RUSTSEC-2026-0049 ignore (#562) ([#562](https://github.com/KooshaPari/helios-cli/pull/562))
- bootstrap trufflehog.yml (#561) ([#561](https://github.com/KooshaPari/helios-cli/pull/561))
- prune stale RUSTSEC-2025-0134 advisory ignore ([`218c663`](https://github.com/KooshaPari/helios-cli/commit/218c663))
- pin GitHub Actions to commit SHAs (#557) ([#557](https://github.com/KooshaPari/helios-cli/pull/557))
- pin all GitHub Actions to commit SHAs (#556) ([#556](https://github.com/KooshaPari/helios-cli/pull/556))
- pin GitHub Actions to commit SHAs (#555) ([#555](https://github.com/KooshaPari/helios-cli/pull/555))
- pin setup-python to immutable SHA (#554) ([#554](https://github.com/KooshaPari/helios-cli/pull/554))
- add standard README badges (#551) ([#551](https://github.com/KooshaPari/helios-cli/pull/551))
- pin GitHub Actions to immutable SHAs (#553) ([#553](https://github.com/KooshaPari/helios-cli/pull/553))
- pin actions/checkout to SHA (#552) ([#552](https://github.com/KooshaPari/helios-cli/pull/552))
- upgrade softprops/action-gh-release from v2 to v3.0.0 ([`176cb04`](https://github.com/KooshaPari/helios-cli/commit/176cb04))

## Earlier Releases

Versions prior to 0.3.0 are documented via the git tag history.
See the full tag listing at <https://github.com/KooshaPari/helios-cli/tags>.

[0.8.0]: https://github.com/KooshaPari/helios-cli/releases/tag/0.8.0
[0.7.0]: https://github.com/KooshaPari/helios-cli/compare/0.8.0...0.7.0
[0.6.0]: https://github.com/KooshaPari/helios-cli/compare/0.7.0...0.6.0
[0.5.0]: https://github.com/KooshaPari/helios-cli/compare/0.6.0...0.5.0
[0.4.0]: https://github.com/KooshaPari/helios-cli/compare/0.5.0...0.4.0
[0.3.0]: https://github.com/KooshaPari/helios-cli/releases/tag/0.3.0
