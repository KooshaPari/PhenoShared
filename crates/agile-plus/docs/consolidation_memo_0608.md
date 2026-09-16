# Consolidation Memo — 2026-06-08

Sources: 183 <REDACTED> remote repos (`/tmp/<REDACTED>_repos.json`); 84 archived / 99 active. Local inventory = 26 private/unmapped. Subagent final summaries (a07c11fa784760d90, af42b80b52800828e, aef0db3108fce5969, a6594d3bf05b04960, a118b2eec5a1cfeee, a6de5053d6d624824, ac224231df1a13f83, a42d2b660e617d400, a3cdf65138b9ba727, aa8a7f23bd65bfda3, ab63751cf1cf7203a, a46c3a16fd14fdd60, ac4182a91ddd4b9ca).

## 1. Top 5 cross-repo libifications
1. **Workflow-hygiene reusable workflow** -> `<REDACTED>/phenoShared/.github/workflows/reusable/workflow-hygiene.yml` (target repo). 1861 `*.yml` files across `repos/*/.github/`; only 96 delegate to `phenoShared`. Centralize SHA-pin audit, runner-pin audit, `permissions:` audit, actionlint. Replace 1764 inline copies.
2. **Electron cross-platform release** -> `<REDACTED>/phenotypeActions/electron-release` (new reusable). OmniRoute's `electron-release.yml` and VibeProxy's `release.yml` share tag dispatch, checkout, version extraction, softprops `gh-release` fan-in. Keep macOS Swift flow (codesign/notarytool/Sparkle) separate.
3. **Phenotype caching** -> merge `Stashly` (TTL/multi-tier/singleflight) into `phenoUtils` (or new `pheno-cache` crate in `phenoUtils`). Already flagged as overlap with `pheno-utils` cache layer.
4. **Phenotype xDD** -> `FocalPoint/tooling/xdd-lib` (or new `pheno-xdd` crate). Unify `phenoXddLib` (property/contract/mutation crates) + `phenoXdd` (150+ patterns repo) into one Rust crate consumed by `AgilePlus`, `FocalPoint`, and `phenotype-tooling`.
5. **MCP framework** -> fork `McpKit` (archived, Phenotype MCP framework SDK) into a new `phenotype-mcp` crate, and wrap the official `modelcontextprotocol/python-sdk` (MIT) for Python. Single `phenotype-mcp` namespace replaces `AgentMCP`, `MCPForge`, `PhenoMCP`, `phenotype-ops-mcp`.

## 2. Top 5 OSS to fork/wrap (action hardening, MCP, observability)
1. **woodruffw/zizmor** (Rust, MIT) — workflow YAML static analysis. Self-host in CI to enforce SHA-pin / `pull_request_target` / `permissions:` rules. Action hardener.
2. **step-security/harden-runner** (TS, Apache-2.0) — runtime network egress + SHA-pinning detection. Wrap as a composite action in `phenotypeActions`.
3. **rhysd/actionlint** (Go, MIT) — workflow syntax/shell-injection checker. Pin and call from `workflow-hygiene.yml`; already canonical, just enforce.
4. **modelcontextprotocol/python-sdk** (Python, MIT) — official MCP SDK with `FastMCP` class. Wrap (do not fork); Prefect's `fastmcp` 2.0 fork only if auth/OpenAPI auto-gen needed.
5. **tokio-rs/tracing-opentelemetry** + **opentelemetry-rust** (MIT / Apache-2.0) — Rust observability bridge + OTel SDK. Wrap into `agileplus-telemetry` and expose to `pheno`, `FocalPoint`, `phenoData`. Use `metrics-rs` for the metrics facet.

## 3. Top 5 repos to delete
1. **`projects-landing`** — Astro auto-gen portfolio, archived, superseded by `phenotype-landing`.
2. **`thegent-landing`** — Astro thegent.<REDACTED>.com page, archived, folded into `phenotype-landing`.
3. **`helios-cli-backup`** — self-marked DEPRECATED; canonical is `helios-cli` in `HexaKit/`.
4. **`phenotype-colab-extensions`** — archived, no callers.
5. **`forge`** (archived 2026-03) — CLI task runner subsumed by `phenoForge`.

## 4. Top 5 repos to unarchive
1. **`Stashly`** — Rust universal caching; overlaps `pheno-utils` cache layer. Work: extract, integrate, and deprecate.
2. **`phenoXddLib`** — `src/{lib,contract,domain,mutation,property,spec}.rs` xDD utilities. Work: wire into `FocalPoint/tooling/xdd-lib` CI.
3. **`phenoXdd`** — 150+ xDD patterns catalog. Work: convert to a docs site under `phenotype-handbook`.
4. **`phenoForge`** — Rust task runner. Work: merge into `pheno` monorepo alongside `phenoUtils`.
5. **`McpKit`** — Phenotype MCP framework SDK. Work: consolidate with `AgentMCP` / `PhenoMCP` into a single `phenotype-mcp` crate (see §1.5).

## 5. Top 5 repos to merge into a specific target
1. **`Stashly`** -> `phenoUtils` (caching crate).
2. **`phenoXddLib` + `phenoXdd`** -> `FocalPoint/tooling/xdd-lib` (single Rust crate).
3. **`phenoForge`** -> `pheno` monorepo (`crates/`).
4. **`McpKit` + `AgentMCP` + `PhenoMCP` + `phenotype-ops-mcp`** -> new `phenotype-mcp` namespace (NOT `phenotype-tooling`).
5. **`helios-cli-backup` + `HeliosCLI` (local)** -> `helios-cli` (single canonical). `HeliosCLI` already self-describes as superseded by `helios-cli`.

## 6. Top 5 intra-AgilePlus crate libifications
1. **`agileplus-cli` -> `agileplus-subcmds`** — `cli/src/lib.rs:1` is a 1-line stub; `subcmds` already has the `SubCommandRegistry` + clap derive. Fold and re-export.
2. **`agileplus-sync` + `agileplus-plane`** — both re-implement sync orchestration (`sync/orchestrator` vs `plane/sync_queue`). Move `plane::sync/orchestrator` into `agileplus-sync`; `plane` keeps only the Plane API client.
3. **`agileplus-contract-tests` -> `agileplus-integration-tests`** — same `domain+events+sqlite+rusqlite+serde+tokio+tracing` dep set; merge under a `contract` feature flag.
4. **`agileplus-cache` + `agileplus-nats`** — both implement `EventBus`/`Store` hexagonal port (in-mem + remote). Keep the pattern (it's the deliberate core), but extract a shared `agileplus-bus` trait crate.
5. **`agileplus-telemetry` + `agileplus-governance`** — both define an `Error` enum + tracing-subscriber init. Leave `Error` enums (domain-specific), but extract the `tracing` init helper into `agileplus-telemetry::init`.

## Data gaps
- `eport` — local absent, remote returns 404 / unresolved. Cannot triage. Resolve source first; do not merge into `phenotype-tooling`.
