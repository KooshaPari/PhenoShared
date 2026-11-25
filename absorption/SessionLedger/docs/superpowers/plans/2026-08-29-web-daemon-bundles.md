# Web Daemon Bundles Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the browser viewer render OKF bundles supplied by its local
`sl-daemon`, rather than embedded demonstration sessions.

**Architecture:** A new `daemon_source` module owns the HTTP request and the
pure OKF-to-`Session` projection. `App` selects that async path only for a
non-fixture WASM build; desktop keeps its existing local corpus loader.

**Tech Stack:** Rust, Dioxus 0.7, reqwest WASM, serde, `OkfDocument`, cargo
tests, Dioxus CLI, Playwright.

---

## File map

| File                                    | Responsibility                                                           |
| --------------------------------------- | ------------------------------------------------------------------------ |
| `crates/sl-viewer/src/daemon_source.rs` | Parse daemon JSON, map canonical OKF to `Session`, fetch `/api/bundles`. |
| `crates/sl-viewer/src/lib.rs`           | Export the module.                                                       |
| `crates/sl-viewer/src/app.rs`           | Choose daemon fetch for web, preserve desktop loader.                    |
| `crates/sl-viewer/README.md`            | Document the local web + daemon invocation.                              |

### Task 1: Canonical OKF projection

**Files:**

- Create: `crates/sl-viewer/src/daemon_source.rs`
- Modify: `crates/sl-viewer/src/lib.rs`
- Test: `crates/sl-viewer/src/daemon_source.rs`

- [ ] **Step 1: Write failing projection tests.**

```rust
#[test]
fn parses_daemon_documents_into_sessions() {
    let sessions = parse_daemon_bundles(r#"[{\"okf\":\"1.0\",\"source_id\":\"fuzz-a\",\"entities\":[{\"id\":\"intent-0\",\"type\":\"intent\",\"label\":\"ship it\",\"properties\":null},{\"id\":\"resource-1\",\"type\":\"resource\",\"label\":\"working-directory\",\"properties\":{\"cwd\":\"/tmp/demo\"}}],\"provenance\":{\"corpus\":\"forge\",\"source_id\":\"fuzz-a\"},\"tags\":[]}]"#).unwrap();
    assert_eq!(sessions[0].id, "fuzz-a");
    assert_eq!(sessions[0].corpus, Corpus::Forge);
    assert_eq!(sessions[0].cwd.as_deref(), Some("/tmp/demo"));
    assert_eq!(sessions[0].messages[0].content, "ship it");
}

#[test]
fn rejects_invalid_okf_response_without_mock_fallback() {
    let error = parse_daemon_bundles(r#"[{\"okf\":\"2.0\"}]"#).unwrap_err();
    assert!(error.contains("failed to parse daemon bundles"));
}
```

- [ ] **Step 2: Verify red.**

Run: `cargo test -p sl-viewer daemon_source::tests --locked`

Expected: compile failure because `daemon_source` and `parse_daemon_bundles`
do not exist.

- [ ] **Step 3: Implement the pure parser.**

```rust
pub fn parse_daemon_bundles(body: &str) -> Result<Vec<Session>, String> {
    let documents: Vec<OkfDocument> = serde_json::from_str(body)
        .map_err(|error| format!("failed to parse daemon bundles: {error}"))?;
    documents.into_iter().map(session_from_okf).collect()
}

fn session_from_okf(document: OkfDocument) -> Result<Session, String> {
    if !validate_okf_document(&document).is_empty() {
        return Err(format!("failed to parse daemon bundles: invalid OKF {}", document.source_id));
    }
    let corpus = corpus_from_okf(&document.provenance.corpus)?;
    let title = entity_string(&document, "state", "title");
    let cwd = entity_string(&document, "resource", "cwd");
    let messages = document.entities.iter().filter(|entity| entity.r#type == "intent")
        .filter(|entity| !entity.label.trim().is_empty())
        .map(|entity| Message::new(Role::User, entity.label.clone())).collect();
    Ok(Session { id: document.source_id, corpus, cwd, title, messages })
}
```

Map every current `Corpus` wire name (`forge`, `codex`, `claude-code`,
`cursor`, `factory-droid`, `chatgpt-web`, `claude-web`, `gemini-web`) and
return an error for unknown names. Add `pub mod daemon_source;` to `lib.rs`.

- [ ] **Step 4: Verify green and format.**

Run: `cargo test -p sl-viewer daemon_source::tests --locked && cargo fmt --all -- --check`

Expected: all daemon-source tests pass and formatting is clean.

- [ ] **Step 5: Commit.**

```bash
git add crates/sl-viewer/src/daemon_source.rs crates/sl-viewer/src/lib.rs
git commit -m "feat(sl-viewer): parse daemon bundles"
```

### Task 2: WASM daemon fetch selection

**Files:**

- Modify: `crates/sl-viewer/src/daemon_source.rs`
- Modify: `crates/sl-viewer/src/app.rs:400-440`
- Test: `crates/sl-viewer/src/daemon_source.rs`

- [ ] **Step 1: Write failing fetch URL test.**

```rust
#[test]
fn daemon_bundle_url_uses_shared_daemon_base() {
    assert_eq!(daemon_bundle_url(), "http://127.0.0.1:8080/api/bundles");
}
```

- [ ] **Step 2: Verify red.**

Run: `cargo test -p sl-viewer daemon_bundle_url_uses_shared_daemon_base --locked`

Expected: compile failure because `daemon_bundle_url` does not exist.

- [ ] **Step 3: Add fetch and select it for web.**

```rust
pub fn daemon_bundle_url() -> String { daemon_api_url("/api/bundles") }

pub async fn fetch_daemon_sessions() -> Result<Vec<Session>, String> {
    let response = reqwest::Client::new().get(daemon_bundle_url()).send().await
        .map_err(|error| format!("daemon not reachable: {error}"))?;
    if !response.status().is_success() {
        return Err(format!("daemon returned {}", response.status()));
    }
    parse_daemon_bundles(&response.text().await.map_err(|error| error.to_string())?)
}
```

In `App`'s existing discovery effect, use `fetch_daemon_sessions().await` for
`#[cfg(all(feature = "web", not(feature = "desktop")))]`; keep the existing
`load_sessions_with_custom` path under the complementary cfg. Keep fixture and
explicit `SL_VIEWER_DEMO=1` paths on `DataSource::Mock`.

- [ ] **Step 4: Verify green.**

Run: `cargo test -p sl-viewer --locked && cargo clippy -p sl-viewer --all-targets --all-features --locked -- -D warnings`

Expected: all viewer tests and strict clippy pass.

- [ ] **Step 5: Commit.**

```bash
git add crates/sl-viewer/src/daemon_source.rs crates/sl-viewer/src/app.rs
git commit -m "fix(sl-viewer): load web bundles from daemon"
```

### Task 3: Local operator contract and browser proof

**Files:**

- Modify: `crates/sl-viewer/README.md`
- Test: temporary daemon fixture plus static Dioxus artifact; no test output committed

- [ ] **Step 1: Document the local pairing.** Add an example that runs a
      loopback daemon on `127.0.0.1:8080`, then invokes `dx serve --platform web
--no-default-features --features web`; explicitly state that the web screen
      shows daemon bundles and desktop still scans local corpora.

- [ ] **Step 2: Build the web artifact.**

Run: `dx build --web --release --no-default-features --features web`

Expected: generated `target/dx/sl-viewer/release/web/public/index.html` plus
WASM assets.

- [ ] **Step 3: Run fixture-backed browser proof.** Start `sl-daemon serve`
      against `fuzz/corpus/jsonl_ingest/two_sessions.jsonl`, host the built static
      directory, then use Playwright to assert that the Bundles tab contains
      `fuzz-a` and `fuzz-b`, excludes `forge-session-001`, and records a successful
      `GET http://127.0.0.1:8080/api/bundles` request.

- [ ] **Step 4: Run final gates.**

Run: `cargo fmt --all -- --check && cargo clippy --all-targets --all-features --locked -- -D warnings && cargo nextest run --all-features --locked --status-level fail && cargo build --manifest-path crates/sl-daemon/Cargo.toml --locked`

Expected: all commands exit zero.

- [ ] **Step 5: Commit documentation.**

```bash
git add crates/sl-viewer/README.md
git commit -m "docs(sl-viewer): document web daemon bundle flow"
```

## Plan self-review

- Spec coverage: Tasks 1 and 2 cover parsing, daemon fetch, WASM selection,
  plain-language errors, and desktop preservation; Task 3 covers browser
  evidence and operator documentation.
- Placeholder scan: no deferred behavior is included; web replay and public
  hosting remain explicit non-goals.
- Type consistency: `OkfDocument` is the canonical wire shape, all rendered
  paths still consume `Vec<Session>`, and the daemon URL comes from
  `daemon_api_url`.
