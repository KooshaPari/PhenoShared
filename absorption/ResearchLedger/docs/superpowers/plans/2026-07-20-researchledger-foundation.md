# ResearchLedger Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first working ResearchLedger slice: a Tauri 2 desktop shell, a local Markdown vault, a SQLite metadata/index database, and an authenticated GitHub starred-repository importer.

**Architecture:** The React/TypeScript frontend owns presentation and typed command invocation. A Rust core owns filesystem boundaries, SQLite migrations, canonical document identity, and import orchestration. GitHub is an API adapter; all imported records become deterministic Markdown plus derived SQLite state. LinkedIn, embeddings, graph enrichment, and external wiki adapters are follow-on vertical slices.

**Tech Stack:** Tauri 2, React, TypeScript, Rust, SQLite with FTS5, GitHub REST API, Vitest, Rust unit/integration tests.

---

## Scope boundaries

This plan intentionally delivers one testable foundation slice. It does not implement LinkedIn browser automation, LLM calls, embeddings, or external wiki publishing. Those will use the interfaces established here and receive separate plans. LinkedIn's first supported path remains manual export import or an approved API integration.

## File map

```text
ResearchLedger/
  apps/desktop/
    src/                    # React UI
    src-tauri/
      src/commands.rs       # typed Tauri command handlers
      src/github.rs         # GitHub API client and response models
      src/import.rs         # import orchestration and Markdown rendering
      src/storage.rs        # vault paths and SQLite repository
      src/models.rs         # shared Rust domain types
      migrations/            # SQLite schema migrations
  crates/core/              # pure domain logic reusable by other frontends
    src/lib.rs
    src/identity.rs
    src/markdown.rs
  tests/fixtures/github/    # deterministic API fixtures
  docs/superpowers/plans/   # implementation plans
```

The exact generated Tauri paths may differ slightly after scaffolding; keep the
responsibility boundaries above even if the scaffold uses a different entrypoint name.

## Task 1: Scaffold the repository and desktop shell

**Files:**
- Create: `package.json`
- Create: `apps/desktop/package.json`
- Create: `apps/desktop/index.html`
- Create: `apps/desktop/src/main.tsx`
- Create: `apps/desktop/src/App.tsx`
- Create: `apps/desktop/src-tauri/tauri.conf.json`
- Create: `apps/desktop/src-tauri/Cargo.toml`
- Create: `apps/desktop/src-tauri/src/main.rs`
- Create: `.gitignore`
- Create: `README.md`

- [ ] **Step 1: Add the root workspace manifest and ignored local state.**

  Define npm scripts for `dev`, `build`, `test`, and `lint`. Ignore `node_modules`,
  Tauri build output, local vaults, SQLite databases, browser profiles, tokens, and
  generated artifacts.

- [ ] **Step 2: Scaffold the smallest Tauri/React window.**

  The first screen must render the product name, vault status, and a disabled import
  button. Tauri must launch a native window and the frontend must load without network
  access.

- [ ] **Step 3: Add a smoke test for the frontend root.**

  Test that `App` renders `ResearchLedger` and a visible `Select vault` control.

- [ ] **Step 4: Run the shell checks.**

  Run:

  ```bash
  npm install
  npm test -- --run
  npm run build
  cargo check --manifest-path apps/desktop/src-tauri/Cargo.toml
  ```

  Expected: frontend tests, TypeScript build, and Rust compilation all pass.

- [ ] **Step 5: Commit the scaffold.**

  ```bash
  git add .
  git commit -m "feat: scaffold ResearchLedger desktop shell"
  ```

## Task 2: Add the canonical domain model and deterministic IDs

**Files:**
- Create: `crates/core/Cargo.toml`
- Create: `crates/core/src/lib.rs`
- Create: `crates/core/src/identity.rs`
- Create: `crates/core/src/markdown.rs`
- Create: `crates/core/tests/identity.rs`
- Modify: `Cargo.toml`

- [ ] **Step 1: Write identity and normalization tests.**

  Cover repository IDs, URL normalization, slug generation, stable IDs across repeated
  calls, and collision resistance for two different repositories.

- [ ] **Step 2: Implement pure domain functions.**

  Use these interfaces:

  ```rust
  pub fn github_document_id(owner: &str, repo: &str) -> String;
  pub fn canonical_github_url(owner: &str, repo: &str) -> String;
  pub fn safe_slug(input: &str) -> String;
  pub fn render_source_markdown(document: &SourceDocument) -> String;
  ```

  `SourceDocument` must carry stable ID, title, source kind, source URI, captured time,
  content hash, description, and Markdown body. Markdown frontmatter must be sorted and
  deterministic so repeated imports produce no noisy diffs.

- [ ] **Step 3: Run the core tests.**

  ```bash
  cargo test -p researchledger-core
  ```

  Expected: all identity and rendering tests pass.

- [ ] **Step 4: Commit the domain layer.**

  ```bash
  git add Cargo.toml crates/core
  git commit -m "feat: add canonical research document model"
  ```

## Task 3: Add SQLite migrations and vault storage

**Files:**
- Create: `apps/desktop/src-tauri/migrations/001_initial.sql`
- Create: `apps/desktop/src-tauri/src/storage.rs`
- Create: `apps/desktop/src-tauri/src/models.rs`
- Create: `apps/desktop/src-tauri/tests/storage.rs`
- Modify: `apps/desktop/src-tauri/Cargo.toml`
- Modify: `apps/desktop/src-tauri/src/main.rs`

- [ ] **Step 1: Write storage tests against a temporary directory.**

  Verify vault initialization, database creation, migration application, document upsert,
  content-hash no-op behavior, and safe atomic Markdown writes.

- [ ] **Step 2: Add the initial schema.**

  Create `documents`, `document_versions`, `chunks`, `provenance`, `import_jobs`, and an
  external-content FTS5 table over chunks. Include unique constraints on stable document IDs
  and content hashes. Add a schema version table and indexes for source kind and updated time.

- [ ] **Step 3: Implement the storage repository.**

  Expose:

  ```rust
  pub fn initialize(root: &Path) -> Result<LedgerPaths>;
  pub fn upsert_document(&self, document: &SourceDocument) -> Result<UpsertResult>;
  pub fn write_markdown_atomic(&self, path: &Path, content: &str) -> Result<()>;
  pub fn rebuild_fts(&self) -> Result<()>;
  ```

  Configure WAL mode, a busy timeout, and one writer connection. Never write outside the
  selected vault or app-support database path.

- [ ] **Step 4: Run storage tests and inspect the schema.**

  ```bash
  cargo test -p researchledger-desktop --test storage
  sqlite3 /tmp/researchledger-test.db '.schema'
  ```

  Expected: migration and idempotency tests pass, and the schema contains all required
  tables plus `chunk_fts`.

- [ ] **Step 5: Commit storage.**

  ```bash
  git add apps/desktop/src-tauri
  git commit -m "feat: add local vault and SQLite ledger"
  ```

## Task 4: Implement the GitHub API adapter

**Files:**
- Create: `apps/desktop/src-tauri/src/github.rs`
- Create: `apps/desktop/src-tauri/tests/github.rs`
- Create: `tests/fixtures/github/starred-page.json`
- Create: `tests/fixtures/github/readme.json`
- Modify: `apps/desktop/src-tauri/Cargo.toml`

- [ ] **Step 1: Write fixture-based API tests.**

  Cover pagination, repository field mapping, README base64 decoding, missing README
  handling, malformed response errors, `403` rate-limit handling, and token redaction from
  error messages.

- [ ] **Step 2: Implement typed GitHub models and client.**

  Expose:

  ```rust
  pub struct GithubClient { ... }
  pub async fn list_starred(&self) -> Result<Vec<StarredRepository>>;
  pub async fn read_readme(&self, owner: &str, repo: &str) -> Result<Option<String>>;
  ```

  Use the official REST endpoints, `per_page=100`, response headers for rate-limit state,
  bounded sequential pagination, and `Retry-After` when present. Read the token from the
  OS environment or secure configuration; never persist it in SQLite or Markdown.

- [ ] **Step 3: Run adapter tests.**

  ```bash
  cargo test -p researchledger-desktop --test github
  ```

  Expected: all fixture tests pass without network access.

- [ ] **Step 4: Commit the adapter.**

  ```bash
  git add apps/desktop/src-tauri tests/fixtures/github
  git commit -m "feat: add GitHub starred repository client"
  ```

## Task 5: Build GitHub import orchestration

**Files:**
- Create: `apps/desktop/src-tauri/src/import.rs`
- Create: `apps/desktop/src-tauri/tests/import.rs`
- Modify: `apps/desktop/src-tauri/src/main.rs`
- Modify: `crates/core/src/markdown.rs`

- [ ] **Step 1: Write import tests.**

  Verify a repository becomes one Markdown document with name, description, URL, README,
  capture metadata, and deterministic frontmatter. Re-import an unchanged repository and
  assert that no new version is created. Change the README and assert that exactly one new
  version and one updated Markdown file are produced.

- [ ] **Step 2: Implement the import service.**

  Expose:

  ```rust
  pub async fn import_github_starred(
      client: &GithubClient,
      storage: &Storage,
      progress: impl Fn(ImportProgress) + Send + Sync,
  ) -> Result<ImportSummary>;
  ```

  Use the stable GitHub document ID as the key, render `sources/github/<owner>--<repo>.md`,
  preserve source URI and retrieval timestamp, calculate content hashes, and emit progress
  events for fetched, skipped, written, and failed records.

- [ ] **Step 3: Run import tests.**

  ```bash
  cargo test -p researchledger-desktop --test import
  ```

  Expected: import, re-import, update, and failure-isolation tests pass.

- [ ] **Step 4: Commit the importer.**

  ```bash
  git add apps/desktop/src-tauri crates/core/src/markdown.rs
  git commit -m "feat: import GitHub stars into the research vault"
  ```

## Task 6: Expose typed Tauri commands and first UI workflow

**Files:**
- Create: `apps/desktop/src-tauri/src/commands.rs`
- Create: `apps/desktop/src-tauri/src/events.rs`
- Create: `apps/desktop/src/components/VaultStatus.tsx`
- Create: `apps/desktop/src/components/ImportPanel.tsx`
- Create: `apps/desktop/src/hooks/useLedger.ts`
- Create: `apps/desktop/src/lib/tauri.ts`
- Create: `apps/desktop/src/App.test.tsx`
- Modify: `apps/desktop/src/App.tsx`
- Modify: `apps/desktop/src-tauri/src/main.rs`

- [ ] **Step 1: Write command/UI contract tests.**

  Test command payload serialization, vault selection state, disabled import without a
  configured vault, progress rendering, successful summary rendering, and a redacted error
  state.

- [ ] **Step 2: Add typed commands.**

  Provide `select_vault`, `vault_status`, `import_github`, and `search_documents` command
  signatures. Validate all user-selected paths in Rust and return serializable DTOs rather
  than leaking database or HTTP client types to the frontend.

- [ ] **Step 3: Implement the first user workflow.**

  The UI must let the user select a vault, see document/import counts, start GitHub import,
  observe progress, and open the generated Markdown folder. Tokens are entered through a
  local configuration flow and are never rendered after submission.

- [ ] **Step 4: Run frontend and Rust checks.**

  ```bash
  npm test -- --run
  npm run build
  cargo test --workspace
  cargo clippy --workspace --all-targets -- -D warnings
  ```

  Expected: all tests pass, the frontend builds, and Clippy reports no warnings.

- [ ] **Step 5: Commit the vertical slice.**

  ```bash
  git add apps/desktop
  git commit -m "feat: add ResearchLedger GitHub import workflow"
  ```

## Task 7: Verification, documentation, and snapshot

**Files:**
- Modify: `README.md`
- Create: `docs/TESTING.md`
- Create: `docs/SECURITY.md`

- [ ] **Step 1: Document local setup and credential handling.**

  Include exact commands for installing dependencies, launching the app, creating a vault,
  configuring a GitHub token, running fixture tests, and removing local state. State that
  browser profiles, tokens, databases, and imported personal data are local-only.

- [ ] **Step 2: Run the complete verification matrix.**

  ```bash
  npm test -- --run
  npm run build
  cargo fmt --all -- --check
  cargo test --workspace
  cargo clippy --workspace --all-targets -- -D warnings
  git diff --check
  ```

  Expected: every command exits zero.

- [ ] **Step 3: Check file sizes and secrets.**

  ```bash
  find . -type f \( -name '*.rs' -o -name '*.ts' -o -name '*.tsx' \) -not -path './node_modules/*' -exec wc -l {} + | awk '$1 > 350'
  rg -n -i 'ghp_|github_pat_|BEGIN PRIVATE KEY|password|bearer [A-Za-z0-9]' . --glob '!target/**' --glob '!node_modules/**'
  ```

  Expected: no production file exceeds the target size without decomposition and no real
  secret is present.

- [ ] **Step 4: Create the required Airlock snapshot if the workspace tool is available.**

  ```bash
  python3 /path/to/phenotype/repos/.airlock/bin/airlock-v2.py snapshot "$PWD"
  ```

  If the path is unavailable, record that fact in the final handoff and do not substitute a
  destructive or broad git operation.

