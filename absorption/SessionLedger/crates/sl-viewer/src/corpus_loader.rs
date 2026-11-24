//! Corpus loader — bridges the Forge ingestion adapter to the viewer's data model.
//!
//! When the `sqlite` feature is enabled and a DB path is provided, loads real
//! sessions from a Forge SQLite corpus via [`ForgeDb`].  Falls back to
//! [`mock_data::sample_sessions`] when no path is given (development / demo mode).
//!
//! The data-layer is intentionally decoupled from Dioxus so it can be unit-tested
//! without a UI runtime.

use std::path::{Path, PathBuf};

use serde::{Deserialize, Serialize};
use session_ledger::domain::session::Session;
#[cfg(feature = "parquet")]
use session_ledger::ports::CorpusSource;

use crate::mock_data::sample_sessions;

/// Source configuration for the viewer's session list.
#[derive(Debug, Clone, Default)]
pub enum DataSource {
    /// Discover native session stores on the local device.
    #[default]
    Auto,
    /// In-memory mock data (explicit demo mode only).
    Mock,
    /// Load from a Forge SQLite database at the given path.
    #[cfg(feature = "sqlite")]
    ForgeDb(std::path::PathBuf),
}

/// User-supplied directories to scan in addition to (or instead of) the
/// default native session stores.
///
/// Empty `custom_paths` means "behave exactly like the legacy auto-discovery".
/// Non-empty values are layered on top of the defaults so users can keep
/// discovering their `~/.codex/sessions` etc. while also pointing the viewer
/// at, say, an archive on an external drive.
///
/// `CustomCorpusPath` is a `Vec` rather than a single `PathBuf` so the JSON
/// shape (`{"custom_paths": [...]}`) can grow without breaking older
/// releases. The UI currently only sets one entry at a time, but the data
/// layer accepts many.
///
/// Serialized as a JSON array of strings via [`serde`]; the type itself is
/// intentionally `pub` so other modules can own a `Signal<CustomCorpusPath>`
/// without going through a wrapper.
#[derive(Debug, Clone, Default, PartialEq, Eq, Serialize, Deserialize)]
pub struct CustomCorpusPath(pub Vec<PathBuf>);

impl CustomCorpusPath {
    /// Construct from an iterator of paths.
    pub fn from_paths<I>(paths: I) -> Self
    where
        I: IntoIterator<Item = PathBuf>,
    {
        Self(paths.into_iter().collect())
    }

    /// Whether no custom paths are set.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.0.is_empty()
    }

    /// Number of custom paths currently configured.
    #[must_use]
    pub fn len(&self) -> usize {
        self.0.len()
    }

    /// Iterate over the configured custom paths.
    pub fn iter(&self) -> std::slice::Iter<'_, PathBuf> {
        self.0.iter()
    }
}

impl From<Vec<PathBuf>> for CustomCorpusPath {
    fn from(paths: Vec<PathBuf>) -> Self {
        Self(paths)
    }
}

impl From<PathBuf> for CustomCorpusPath {
    fn from(path: PathBuf) -> Self {
        Self(vec![path])
    }
}

/// Load sessions from the configured source, **without** any custom paths.
///
/// Convenience wrapper that calls [`load_sessions_with_custom`] with an
/// empty [`CustomCorpusPath`]. Preserves the historical single-argument
/// signature for callers that don't participate in the custom-path
/// feature (visual fixtures, the `Mock` branch).
///
/// # Errors
///
/// Returns an error string only if the database itself cannot be opened or
/// queried (e.g. file not found, not a SQLite database).  Per-row failures are
/// surfaced on stderr as warnings and do not cause an error return.
pub fn load_sessions(source: &DataSource) -> Result<Vec<Session>, String> {
    load_sessions_with_custom(source, &CustomCorpusPath::default())
}

/// Load sessions from the configured source, layering `custom_paths` on top
/// of the default native session stores when `source` is [`DataSource::Auto`].
///
/// `Mock` and `ForgeDb` sources ignore `custom_paths` — Mock by definition,
/// ForgeDb because the SQLite database is the entire corpus.
///
/// On `Auto`: defaults plus each existing `custom_paths` directory are
/// scanned. A custom path that doesn't exist on disk is silently skipped
/// (it's a user-pickable folder that may have been deleted while the app
/// was off).
///
/// # Errors
///
/// See [`load_sessions`].
pub fn load_sessions_with_custom(
    source: &DataSource,
    custom_paths: &CustomCorpusPath,
) -> Result<Vec<Session>, String> {
    match source {
        DataSource::Mock => Ok(sample_sessions()),
        DataSource::Auto => load_discovered_sessions_with_custom(custom_paths),
        #[cfg(feature = "sqlite")]
        DataSource::ForgeDb(path) => load_from_sqlite(path),
    }
}

/// Resolve the native defaults plus any custom paths into a deduplicated,
/// existing-only list of roots ready to scan.
///
/// The custom paths come *after* the defaults so users see their own data
/// at the bottom of the corpus table rather than pushing the standard
/// Codex/Claude/Cursor entries down. De-duplication is best-effort: equal
/// paths are coalesced; `~/foo` and `/Users/me/foo` are not, by design —
/// resolving symlinks could surprise users who deliberately linked their
/// data into the defaults.
fn collect_discovery_roots(home: &Path, custom_paths: &CustomCorpusPath) -> Vec<PathBuf> {
    let mut roots: Vec<PathBuf> = vec![
        home.join(".codex").join("sessions"),
        home.join(".claude").join("projects"),
        home.join(".cursor").join("projects"),
    ];
    for path in &custom_paths.0 {
        if !roots.iter().any(|existing| existing == path) {
            roots.push(path.clone());
        }
    }
    roots.into_iter().filter(|path| path.is_dir()).collect()
}

fn load_discovered_sessions_with_custom(
    custom_paths: &CustomCorpusPath,
) -> Result<Vec<Session>, String> {
    let home = std::env::var_os("HOME")
        .map(std::path::PathBuf::from)
        .ok_or_else(|| "HOME is not set; cannot discover local sessions".to_owned())?;
    let mut sessions = Vec::new();
    let mut discovered_roots = 0usize;

    // Native defaults — dispatch by directory name to pick the right adapter.
    for root in collect_discovery_roots(&home, custom_paths) {
        discovered_roots += load_rooted_corpus(&root, &mut sessions)?;
    }

    #[cfg(feature = "sqlite")]
    if let Some(path) = resolve_forge_db_path(&home, std::env::var_os("FORGE_DB")) {
        sessions.extend(load_from_sqlite(&path)?);
        discovered_roots += 1;
    }
    if discovered_roots == 0 {
        return Err(
            "no supported local session stores found (Codex, Claude Code, Cursor, or Forge)".into(),
        );
    }
    sessions.sort_by_key(|session| {
        session.messages.iter().filter_map(|message| message.ts_ms).max().unwrap_or_default()
    });
    sessions.reverse();
    Ok(sessions)
}

/// Scan a single root using the appropriate JSON/Parquet adapter.
///
/// Bridges the three native session stores (Codex, Claude, Cursor) with
/// the parquet subagent's work — both `.jsonl`/`.json` (today) and
/// `.parquet` (once that lane lands) live behind this single entry point.
fn load_rooted_corpus(root: &Path, sessions: &mut Vec<Session>) -> Result<usize, String> {
    let name = root.file_name().and_then(|n| n.to_str()).unwrap_or_default();
    match name {
        "sessions" => load_json_corpus(
            root,
            |path| session_ledger::CodexDir::new(path.to_path_buf()),
            sessions,
        ),
        "projects" => {
            // Claude projects and Cursor projects both live under `.projects`
            // directories in their respective roots, but the surrounding
            // directory name tells them apart at a glance. Prefer ClaudeDir
            // for ~/.claude/projects; for custom roots we try Claude first
            // and Cursor second — the adapters fail fast on the wrong
            // schema, so wrong-adapter picks simply contribute zero rows
            // and the right one wins.
            let json_rows = load_json_corpus(
                root,
                |path| session_ledger::ClaudeDir::new(path.to_path_buf()),
                sessions,
            )?;
            // Claude Code on newer macOS builds drops conversation history as
            // `.parquet` files under the same `~/.claude/projects` tree. The
            // JSONL adapter above ignores those; the parquet adapter below
            // fills that gap when the `parquet` feature is enabled.
            #[cfg(feature = "parquet")]
            {
                let parquet_rows = load_parquet_corpus(root, sessions)?;
                Ok(json_rows.saturating_add(parquet_rows))
            }
            #[cfg(not(feature = "parquet"))]
            {
                Ok(json_rows)
            }
        }
        // Generic root (most custom-path case): try Codex first, then
        // Claude, then Cursor. The first adapter that recognizes the
        // shape contributes rows; the rest contribute zero and fall
        // through silently.
        _ => load_json_corpus(
            root,
            |path| session_ledger::CodexDir::new(path.to_path_buf()),
            sessions,
        ),
    }
}

/// Load sessions from a user-picked directory regardless of which native
/// session store it belongs to.
///
/// Used by the custom-path picker to ingest arbitrary directories whose
/// schema the user has explicitly confirmed. Today this delegates to the
/// same JSON-based readers as the default discovery; the `.parquet`
/// branch is a forward-looking hook for the parquet ingestion lane.
pub fn load_parquet_or_json_corpus(root: &Path) -> Result<Vec<Session>, String> {
    let mut sessions = Vec::new();
    load_parquet_or_json_corpus_into(root, &mut sessions)?;
    Ok(sessions)
}

/// Like [`load_parquet_or_json_corpus`] but appends into an existing buffer.
pub fn load_parquet_or_json_corpus_into(
    root: &Path,
    sessions: &mut Vec<Session>,
) -> Result<usize, String> {
    if !root.is_dir() {
        return Ok(0);
    }

    // JSON / JSONL / JSONL.ZST — try each native adapter in order. The
    // first one that recognizes the schema contributes its rows; the
    // others contribute zero and fall through silently. We count the
    // session rows added in each attempt and skip later adapters once
    // any rows land, so we don't double-count if, say, a Codex-shaped
    // transcript also happens to parse as a Claude one.
    //
    // Each adapter lives in its own block so the closures don't have to
    // share a single concrete return type — `load_json_corpus` is generic
    // over the source type, so this is the cleanest spelling.
    let before = sessions.len();
    let mut attempt_before = sessions.len();
    load_json_corpus(root, |p: &Path| session_ledger::CodexDir::new(p.to_path_buf()), sessions)?;
    if sessions.len() == attempt_before {
        attempt_before = sessions.len();
        load_json_corpus(
            root,
            |p: &Path| session_ledger::ClaudeDir::new(p.to_path_buf()),
            sessions,
        )?;
    }
    if sessions.len() == attempt_before {
        load_json_corpus(
            root,
            |p: &Path| session_ledger::CursorDir::new(p.to_path_buf()),
            sessions,
        )?;
    }

    // Forward-looking hook: when the parquet ingestion lane lands, scan for
    // `.parquet` files in `root` and append their decoded sessions here.
    // Until then this branch is a no-op — the helper is shipped so the
    // public surface is stable across the JSON → Parquet transition.
    let parquet_files = walk_for_extension(root, "parquet");
    if !parquet_files.is_empty() {
        eprintln!(
            "[sl-viewer] found {} .parquet file(s) under {}; \
             Parquet ingestion is not yet wired up in this build.",
            parquet_files.len(),
            root.display()
        );
    }

    Ok(sessions.len() - before)
}

/// Collect every file under `root` with the given extension.
///
/// Returns absolute paths in lexical order. Symlinks and unreadable
/// subdirectories are silently skipped so a malformed pick doesn't fail
/// the entire discovery pass.
fn walk_for_extension(root: &Path, extension: &str) -> Vec<PathBuf> {
    let mut out = Vec::new();
    let mut stack = vec![root.to_path_buf()];
    while let Some(dir) = stack.pop() {
        let entries = match std::fs::read_dir(&dir) {
            Ok(entries) => entries,
            Err(_) => continue,
        };
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                stack.push(path);
            } else if path.extension().and_then(|e| e.to_str()) == Some(extension) {
                out.push(path);
            }
        }
    }
    out.sort();
    out
}

/// Resolve the Forge database used by automatic discovery.
///
/// An explicit `FORGE_DB` value always wins, including when it points at a
/// missing file (the subsequent open produces a useful error).  Without the
/// override, the native Forge location is used when present.
#[cfg(feature = "sqlite")]
fn resolve_forge_db_path(
    home: &std::path::Path,
    explicit: Option<std::ffi::OsString>,
) -> Option<std::path::PathBuf> {
    if let Some(path) = explicit {
        let path = std::path::PathBuf::from(path);
        return (!path.as_os_str().is_empty()).then_some(path);
    }
    let native = home.join(".forge").join(".forge.db");
    native.is_file().then_some(native)
}

fn load_json_corpus<F, S>(
    root: &std::path::Path,
    make_source: F,
    sessions: &mut Vec<Session>,
) -> Result<usize, String>
where
    F: FnOnce(&std::path::Path) -> S,
    S: session_ledger::ports::CorpusSource,
{
    if !root.is_dir() {
        return Ok(0);
    }
    let source = make_source(root);
    let ids = source.list().map_err(|e| format!("discover {}: {e}", root.display()))?;
    for id in ids {
        match source.load(&id) {
            Ok(session) if !session.messages.is_empty() => sessions.push(session),
            Ok(_) => {}
            Err(error) => eprintln!("[sl-viewer] skipping {}:{}: {error}", root.display(), id),
        }
    }
    Ok(1)
}

/// Scan `root` for Claude conversation `.parquet` files and append parsed
/// sessions to `sessions`. Returns 1 when the root contains at least one
/// parquet file (counts as a "discovered" root for the empty-store check),
/// 0 when the directory is missing or has no parquet files, and an error
/// only when the discovery step itself fails (e.g. unreadable directory).
#[cfg(feature = "parquet")]
fn load_parquet_corpus(
    root: &std::path::Path,
    sessions: &mut Vec<Session>,
) -> Result<usize, String> {
    if !root.is_dir() {
        return Ok(0);
    }
    let source = crate::parquet_source::ParquetCorpusSource::new(root);
    let ids = source.list().map_err(|e| format!("discover parquet {}: {e}", root.display()))?;
    if ids.is_empty() {
        return Ok(0);
    }
    for id in ids {
        match source.load(&id) {
            Ok(session) if !session.messages.is_empty() => sessions.push(session),
            Ok(_) => {}
            Err(error) => {
                eprintln!("[sl-viewer] skipping parquet {}:{}: {error}", root.display(), id)
            }
        }
    }
    Ok(1)
}

/// Open a Forge SQLite DB at `path` and ingest all conversations.
#[cfg(feature = "sqlite")]
fn load_from_sqlite(path: &std::path::Path) -> Result<Vec<Session>, String> {
    use session_ledger::ingestion::forge::ForgeDb;

    let db = ForgeDb::open(path)
        .map_err(|e| format!("cannot open forge DB at {}: {e}", path.display()))?;

    let (sessions, report) =
        db.ingest_all().map_err(|e| format!("forge ingest_all failed: {e}"))?;

    if !report.is_clean() {
        eprintln!("[sl-viewer] forge ingestion: {} skipped rows:", report.skipped.len());
        for (id, reason) in &report.skipped {
            eprintln!("  skip {id}: {reason}");
        }
    }

    eprintln!(
        "[sl-viewer] forge ingestion: {} sessions loaded from {}",
        sessions.len(),
        path.display()
    );

    Ok(sessions)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Mutex;

    // `HOME` is process-global. These two tests replace it to exercise native
    // discovery, so they must not race each other under Rust's parallel test
    // runner and accidentally scan the developer's real corpus.
    static HOME_ENV_LOCK: Mutex<()> = Mutex::new(());
    /// Restores `HOME` on scope exit, including assertion panics.
    struct HomeEnvGuard {
        previous: Option<std::ffi::OsString>,
    }

    impl HomeEnvGuard {
        fn set(path: &std::path::Path) -> Self {
            let previous = std::env::var_os("HOME");
            std::env::set_var("HOME", path);
            Self { previous }
        }
    }

    impl Drop for HomeEnvGuard {
        fn drop(&mut self) {
            match self.previous.take() {
                Some(value) => std::env::set_var("HOME", value),
                None => std::env::remove_var("HOME"),
            }
        }
    }

    #[test]
    fn home_env_guard_restores_the_previous_value() {
        let _home_guard = HOME_ENV_LOCK.lock().expect("HOME lock");
        let previous = std::env::var_os("HOME");
        let temporary_home = tempfile::tempdir().expect("temporary HOME");

        {
            let _temporary_home = HomeEnvGuard::set(temporary_home.path());
            assert_eq!(
                std::env::var_os("HOME"),
                Some(temporary_home.path().as_os_str().to_os_string())
            );
        }

        assert_eq!(std::env::var_os("HOME"), previous);
    }

    // ── Mock source ───────────────────────────────────────────────────────────

    #[test]
    fn mock_source_returns_non_empty_sessions() {
        let sessions = load_sessions(&DataSource::Mock).expect("mock load");
        assert!(!sessions.is_empty(), "mock data must contain at least one session");
    }

    #[test]
    fn auto_source_missing_store_is_an_explicit_error() {
        // Hold the process-global HOME lock across both discovery and loading.
        // Other tests temporarily replace HOME to exercise their own isolated
        // stores; without this guard, the precondition and the loader could
        // observe different homes under the parallel test runner.
        let _home_guard = HOME_ENV_LOCK.lock().expect("HOME lock");
        let root = std::env::var_os("HOME").map(std::path::PathBuf::from).unwrap_or_default();
        if !root.join(".codex/sessions").exists()
            && !root.join(".claude/projects").exists()
            && !root.join(".cursor/projects").exists()
        {
            assert!(load_sessions(&DataSource::Auto).is_err());
        }
    }

    #[test]
    fn mock_sessions_have_valid_ids() {
        let sessions = load_sessions(&DataSource::Mock).expect("mock load");
        for s in &sessions {
            assert!(!s.id.is_empty(), "session id must be non-empty");
        }
    }

    #[test]
    fn mock_sessions_have_messages() {
        let sessions = load_sessions(&DataSource::Mock).expect("mock load");
        for s in &sessions {
            assert!(!s.messages.is_empty(), "mock session {} has no messages", s.id);
        }
    }

    #[test]
    fn auto_loader_accepts_claude_projects_root() {
        let root = tempfile::tempdir().expect("temp root");
        let project = root.path().join("-Users-demo-repo");
        std::fs::create_dir_all(&project).expect("project root");
        std::fs::write(
            project.join("session.jsonl"),
            serde_json::json!({
                "type": "user",
                "sessionId": "claude-local-1",
                "message": {"role": "user", "content": "hello"}
            })
            .to_string(),
        )
        .expect("write transcript");

        let mut sessions = Vec::new();
        let roots = load_json_corpus(
            root.path(),
            |path| session_ledger::ClaudeDir::new(path.to_path_buf()),
            &mut sessions,
        )
        .expect("discover Claude transcripts");

        assert_eq!(roots, 1);
        assert_eq!(sessions.len(), 1);
        assert_eq!(sessions[0].id, "claude-local-1");
    }

    // ── Parquet source ────────────────────────────────────────────────────────

    /// Re-export of the fixture writer used to materialise a tiny parquet file
    /// on disk for corpus-loader integration tests. The fixture matches the
    /// Claude-conversation schema used by [`crate::parquet_source`]'s unit tests.
    #[cfg(feature = "parquet")]
    fn write_parquet_fixture(
        path: &std::path::Path,
        rows: &[crate::parquet_source::test_fixture::FixtureRow],
    ) {
        crate::parquet_source::test_fixture::write_fixture(path, rows);
    }

    #[cfg(feature = "parquet")]
    #[test]
    fn parquet_loader_returns_one_when_root_contains_a_parquet_file() {
        use crate::parquet_source::test_fixture::FixtureRow;

        let root = tempfile::tempdir().expect("temp root");
        let path = root.path().join("transcripts.parquet");
        write_parquet_fixture(
            &path,
            &[FixtureRow {
                session_id: "parquet-session-1".into(),
                role: "user".into(),
                content: "hello from parquet".into(),
                ts_ms: Some(1_700_000_000_000),
                cwd: Some("/code/parquet".into()),
                title: Some("Parquet session".into()),
            }],
        );

        let mut sessions = Vec::new();
        let roots = load_parquet_corpus(root.path(), &mut sessions).expect("parquet discover");

        assert_eq!(roots, 1);
        assert_eq!(sessions.len(), 1);
        assert_eq!(sessions[0].id, "parquet-session-1");
        assert_eq!(sessions[0].corpus, session_ledger::domain::session::Corpus::ClaudeCode);
        assert_eq!(sessions[0].messages.len(), 1);
        assert_eq!(sessions[0].messages[0].content, "hello from parquet");
        assert_eq!(sessions[0].messages[0].ts_ms, Some(1_700_000_000_000));
    }

    #[cfg(feature = "parquet")]
    #[test]
    fn parquet_loader_returns_zero_when_root_has_no_parquet_files() {
        let root = tempfile::tempdir().expect("temp root");
        std::fs::write(root.path().join("README.md"), b"no parquet here").expect("write file");

        let mut sessions = Vec::new();
        let roots = load_parquet_corpus(root.path(), &mut sessions).expect("parquet discover");
        assert_eq!(roots, 0);
        assert!(sessions.is_empty());
    }

    #[cfg(feature = "parquet")]
    #[test]
    fn parquet_loader_returns_zero_for_missing_root() {
        let root = tempfile::tempdir().expect("temp root");
        let mut sessions = Vec::new();
        let roots =
            load_parquet_corpus(&root.path().join("does-not-exist"), &mut sessions).expect("ok");
        assert_eq!(roots, 0);
        assert!(sessions.is_empty());
    }

    #[cfg(feature = "parquet")]
    #[test]
    fn jsonl_and_parquet_loaders_coexist_on_claude_projects_root() {
        use crate::parquet_source::test_fixture::FixtureRow;

        // Both loaders scan the same `~/.claude/projects` tree; the JSONL
        // adapter should ignore parquet files and vice-versa, so two
        // physically-distinct sessions — one JSONL, one parquet — both survive.
        let root = tempfile::tempdir().expect("temp root");
        let project = root.path().join("-Users-demo-parquet");
        std::fs::create_dir_all(&project).expect("project root");

        std::fs::write(
            project.join("session.jsonl"),
            serde_json::json!({
                "type": "user",
                "sessionId": "jsonl-session-1",
                "message": {"role": "user", "content": "hello from jsonl"}
            })
            .to_string(),
        )
        .expect("write jsonl");
        write_parquet_fixture(
            &project.join("session.parquet"),
            &[FixtureRow {
                session_id: "parquet-session-2".into(),
                role: "user".into(),
                content: "hello from parquet".into(),
                ts_ms: Some(1_700_000_000_000),
                cwd: Some("/code/parquet".into()),
                title: None,
            }],
        );

        // JSONL loader sees only the JSONL file.
        let mut jsonl_sessions = Vec::new();
        let jsonl_roots = load_json_corpus(
            root.path(),
            |path| session_ledger::ClaudeDir::new(path.to_path_buf()),
            &mut jsonl_sessions,
        )
        .expect("jsonl discover");
        assert_eq!(jsonl_roots, 1);
        assert_eq!(jsonl_sessions.len(), 1);
        assert_eq!(jsonl_sessions[0].id, "jsonl-session-1");

        // Parquet loader sees only the parquet file.
        let mut parquet_sessions = Vec::new();
        let parquet_roots =
            load_parquet_corpus(root.path(), &mut parquet_sessions).expect("parquet discover");
        assert_eq!(parquet_roots, 1);
        assert_eq!(parquet_sessions.len(), 1);
        assert_eq!(parquet_sessions[0].id, "parquet-session-2");
        assert_eq!(parquet_sessions[0].messages[0].content, "hello from parquet");
    }

    #[cfg(feature = "sqlite")]
    #[test]
    fn forge_auto_resolution_prefers_explicit_override() {
        let home = tempfile::tempdir().expect("home");
        let native = home.path().join(".forge/.forge.db");
        std::fs::create_dir_all(native.parent().expect("parent")).expect("mkdir");
        std::fs::write(&native, b"fixture").expect("native db");

        let explicit = std::ffi::OsString::from("/custom/forge.db");
        assert_eq!(
            resolve_forge_db_path(home.path(), Some(explicit)),
            Some(std::path::PathBuf::from("/custom/forge.db"))
        );
    }

    #[cfg(feature = "sqlite")]
    #[test]
    fn forge_auto_resolution_discovers_native_database() {
        let home = tempfile::tempdir().expect("home");
        let native = home.path().join(".forge/.forge.db");
        std::fs::create_dir_all(native.parent().expect("parent")).expect("mkdir");
        std::fs::write(&native, b"fixture").expect("native db");

        assert_eq!(resolve_forge_db_path(home.path(), None), Some(native));
    }

    #[cfg(feature = "sqlite")]
    #[test]
    fn forge_auto_resolution_ignores_absent_native_database() {
        let home = tempfile::tempdir().expect("home");
        assert_eq!(resolve_forge_db_path(home.path(), None), None);
    }

    // ── SQLite source ─────────────────────────────────────────────────────────

    #[cfg(feature = "sqlite")]
    mod sqlite_tests {
        use std::path::Path;

        use rusqlite::Connection;

        use super::*;

        type FixtureRow<'a> =
            (&'a str, Option<&'a str>, Option<&'a str>, Option<Vec<u8>>, Option<&'a str>);

        /// Build a minimal Forge SQLite fixture DB at `path` with `rows` rows.
        fn write_fixture_db(path: &Path, rows: &[FixtureRow<'_>]) {
            let conn = Connection::open(path).expect("create fixture db");
            conn.execute_batch(
                "CREATE TABLE IF NOT EXISTS conversations (
                    id            TEXT PRIMARY KEY,
                    title         TEXT,
                    cwd           TEXT,
                    context_zstd  BLOB,
                    context       TEXT
                 );",
            )
            .expect("create table");
            for (id, title, cwd, blob, plain) in rows {
                conn.execute(
                    "INSERT OR IGNORE INTO conversations \
                     (id, title, cwd, context_zstd, context) VALUES (?1,?2,?3,?4,?5)",
                    rusqlite::params![id, title, cwd, blob, plain],
                )
                .expect("insert row");
            }
        }

        fn zstd_compress(s: &str) -> Vec<u8> {
            zstd::stream::encode_all(s.as_bytes(), 3).expect("compress")
        }

        #[test]
        fn sqlite_source_loads_real_sessions() {
            let tmp = tempfile::NamedTempFile::new().expect("tempfile");
            let ctx = serde_json::json!([
                {"role": "user", "content": "implement the thing"},
                {"role": "assistant", "content": "done"}
            ])
            .to_string();
            let blob = zstd_compress(&ctx);

            write_fixture_db(
                tmp.path(),
                &[
                    (
                        "forge-real-001",
                        Some("Real session"),
                        Some("/code/project"),
                        Some(blob.clone()),
                        None,
                    ),
                    (
                        "forge-real-002",
                        Some("Another real session"),
                        Some("/code/other"),
                        Some(blob),
                        None,
                    ),
                ],
            );

            let source = DataSource::ForgeDb(tmp.path().to_owned());
            let sessions = load_sessions(&source).expect("sqlite load");

            assert_eq!(sessions.len(), 2);
            assert_eq!(sessions[0].id, "forge-real-001");
            assert_eq!(sessions[0].title.as_deref(), Some("Real session"));
            assert_eq!(sessions[0].cwd.as_deref(), Some("/code/project"));
            assert_eq!(sessions[0].messages.len(), 2);
        }

        #[test]
        fn sqlite_source_skips_corrupt_rows_and_returns_clean_rows() {
            let tmp = tempfile::NamedTempFile::new().expect("tempfile");
            let ctx = serde_json::json!([
                {"role": "user", "content": "hello"}
            ])
            .to_string();
            let good_blob = zstd_compress(&ctx);
            let bad_blob = vec![0xDE, 0xAD, 0xBE, 0xEF];

            write_fixture_db(
                tmp.path(),
                &[
                    ("corrupt-row", None, None, Some(bad_blob), None),
                    ("clean-row", Some("ok"), Some("/ok"), Some(good_blob), None),
                ],
            );

            let source = DataSource::ForgeDb(tmp.path().to_owned());
            let sessions = load_sessions(&source).expect("sqlite load");

            // Only the clean row should appear.
            assert_eq!(sessions.len(), 1);
            assert_eq!(sessions[0].id, "clean-row");
        }

        #[test]
        fn sqlite_source_plain_text_fallback() {
            let tmp = tempfile::NamedTempFile::new().expect("tempfile");
            let ctx = serde_json::json!([
                {"role": "user", "content": "plain text fallback"}
            ])
            .to_string();

            write_fixture_db(
                tmp.path(),
                &[("plain-row", Some("Plain"), Some("/plain"), None, Some(ctx.as_str()))],
            );

            let source = DataSource::ForgeDb(tmp.path().to_owned());
            let sessions = load_sessions(&source).expect("sqlite load");

            assert_eq!(sessions.len(), 1);
            assert_eq!(sessions[0].messages[0].content, "plain text fallback");
        }

        #[test]
        fn sqlite_source_error_on_nonexistent_file() {
            let source = DataSource::ForgeDb(std::path::PathBuf::from("/tmp/does_not_exist_sl.db"));
            let result = load_sessions(&source);
            assert!(result.is_err(), "should fail on missing file");
            let err = result.unwrap_err();
            assert!(err.contains("cannot open"), "error should describe open failure, got: {err}");
        }

        // ── Committed fixture DB integration test ────────────────────────────

        /// Build (or re-use if already present) the committed fixture DB at
        /// `tests/fixtures/forge_fixture.db`, then load it through the real
        /// corpus loader path and assert the expected session count.
        #[test]
        fn committed_fixture_db_loads_expected_sessions() {
            let fixture_path = std::path::Path::new(env!("CARGO_MANIFEST_DIR"))
                .join("tests")
                .join("fixtures")
                .join("forge_fixture.db");

            // Re-create the fixture each run so the test is hermetic.
            if fixture_path.exists() {
                std::fs::remove_file(&fixture_path).expect("remove old fixture");
            }
            std::fs::create_dir_all(fixture_path.parent().expect("parent")).expect("mkdir");

            let ctx_a = serde_json::json!([
                {"role": "user", "content": "fix the login timeout"},
                {"role": "assistant", "content": "bumped TTL to 1800s"},
                {"role": "user", "content": "looks good, ship it"}
            ])
            .to_string();
            let ctx_b = serde_json::json!([
                {"role": "user", "content": "add billing to the API"},
                {"role": "assistant", "content": "stripe integration done"},
                {"role": "user", "content": "approved"}
            ])
            .to_string();

            let blob_a = zstd_compress(&ctx_a);
            let blob_b = zstd_compress(&ctx_b);

            write_fixture_db(
                &fixture_path,
                &[
                    (
                        "fixture-session-001",
                        Some("Login timeout fix"),
                        Some("/code/auth-service"),
                        Some(blob_a),
                        None,
                    ),
                    (
                        "fixture-session-002",
                        Some("API billing"),
                        Some("/code/api-gateway"),
                        Some(blob_b),
                        None,
                    ),
                ],
            );

            let source = DataSource::ForgeDb(fixture_path.clone());
            let sessions = load_sessions(&source).expect("load committed fixture");

            assert_eq!(sessions.len(), 2, "fixture must contain exactly 2 sessions");

            let s1 = sessions.iter().find(|s| s.id == "fixture-session-001").expect("s1");
            assert_eq!(s1.title.as_deref(), Some("Login timeout fix"));
            assert_eq!(s1.messages.len(), 3);
            assert_eq!(s1.messages[0].role, session_ledger::domain::session::Role::User);

            let s2 = sessions.iter().find(|s| s.id == "fixture-session-002").expect("s2");
            assert_eq!(s2.title.as_deref(), Some("API billing"));
            assert_eq!(s2.messages.len(), 3);
        }
    }

    // ── Custom corpus path ────────────────────────────────────────────────────

    /// Build a Claude-shaped transcript file under `project_dir/<project>`.
    fn write_claude_project(project_dir: &std::path::Path, session_id: &str, body: &str) {
        std::fs::create_dir_all(project_dir).expect("project dir");
        std::fs::write(
            project_dir.join("session.jsonl"),
            format!(
                "{}\n",
                serde_json::json!({
                    "type": "user",
                    "sessionId": session_id,
                    "message": {"role": "user", "content": body}
                })
            ),
        )
        .expect("write transcript");
    }

    #[test]
    fn custom_corpus_path_default_is_empty() {
        let custom = CustomCorpusPath::default();
        assert!(custom.is_empty());
        assert_eq!(custom.len(), 0);
        assert_eq!(custom.iter().count(), 0);
    }

    #[test]
    fn custom_corpus_path_from_single_path() {
        let custom: CustomCorpusPath = PathBuf::from("/tmp/foo").into();
        assert_eq!(custom.len(), 1);
        assert_eq!(custom.iter().next().expect("one"), &PathBuf::from("/tmp/foo"));
    }

    #[test]
    fn custom_corpus_path_from_many_paths() {
        let custom =
            CustomCorpusPath::from_paths(vec![PathBuf::from("/tmp/a"), PathBuf::from("/tmp/b")]);
        assert_eq!(custom.len(), 2);
        assert!(!custom.is_empty());
    }

    #[test]
    fn custom_corpus_path_serializes_as_json_array() {
        let custom =
            CustomCorpusPath::from_paths(vec![PathBuf::from("/tmp/a"), PathBuf::from("/tmp/b")]);
        let json = serde_json::to_string(&custom).expect("serialize");
        // The on-disk shape is a bare array of strings, which the
        // CorpusPathConfig wraps under {"custom_paths": ...}.
        assert_eq!(json, r#"["/tmp/a","/tmp/b"]"#);
    }

    #[test]
    fn custom_corpus_path_deserializes_from_json_array() {
        let custom: CustomCorpusPath =
            serde_json::from_str(r#"["/tmp/x","/tmp/y"]"#).expect("deserialize");
        assert_eq!(custom.len(), 2);
        assert_eq!(custom.iter().next().expect("first"), &PathBuf::from("/tmp/x"));
    }

    #[test]
    fn load_parquet_or_json_corpus_returns_zero_for_missing_dir() {
        let root = tempfile::tempdir().expect("tempdir");
        let bogus = root.path().join("does-not-exist");
        let sessions = load_parquet_or_json_corpus(&bogus).expect("missing dir");
        assert!(sessions.is_empty());
    }

    #[test]
    fn load_parquet_or_json_corpus_reads_claude_shaped_root() {
        let root = tempfile::tempdir().expect("tempdir");
        let project = root.path().join("-Users-foo-bar");
        write_claude_project(&project, "custom-path-1", "hello from a custom corpus");

        let sessions = load_parquet_or_json_corpus(root.path()).expect("custom path load");
        assert_eq!(sessions.len(), 1, "should pick up the Claude-shaped transcript");
        assert_eq!(sessions[0].id, "custom-path-1");
        assert_eq!(sessions[0].messages.len(), 1);
        assert_eq!(sessions[0].messages[0].content, "hello from a custom corpus");
    }

    #[test]
    fn load_parquet_or_json_corpus_handles_empty_directory() {
        let root = tempfile::tempdir().expect("tempdir");
        let sessions = load_parquet_or_json_corpus(root.path()).expect("empty dir");
        assert!(sessions.is_empty(), "empty directory yields no sessions");
    }

    #[test]
    fn load_sessions_with_custom_layers_custom_paths_onto_defaults() {
        let _home_guard = HOME_ENV_LOCK.lock().expect("HOME lock");
        // Custom path isolated from $HOME so the test doesn't depend on
        // which session stores happen to be installed on the runner.
        let fake_home = tempfile::tempdir().expect("home");
        let _temporary_home = HomeEnvGuard::set(fake_home.path());

        let custom_root = tempfile::tempdir().expect("custom root");
        let project = custom_root.path().join("-Users-custom-repo");
        write_claude_project(&project, "layered-1", "first message");

        let custom = CustomCorpusPath::from_paths(vec![custom_root.path().to_path_buf()]);

        let sessions =
            load_sessions_with_custom(&DataSource::Auto, &custom).expect("auto + custom load");

        // The custom path should contribute exactly one session.
        let custom_count = sessions.iter().filter(|s| s.id == "layered-1").count();
        assert_eq!(custom_count, 1, "custom path must contribute its session");
    }

    #[test]
    fn load_sessions_with_custom_skips_missing_custom_paths() {
        let _home_guard = HOME_ENV_LOCK.lock().expect("HOME lock");
        let fake_home = tempfile::tempdir().expect("home");
        let _temporary_home = HomeEnvGuard::set(fake_home.path());

        let custom =
            CustomCorpusPath::from_paths(vec![PathBuf::from("/tmp/does-not-exist-anywhere")]);

        // With no defaults and a non-existent custom path, discovery must
        // surface a clear error rather than panic or silently succeed.
        let result = load_sessions_with_custom(&DataSource::Auto, &custom);
        assert!(result.is_err(), "missing custom path + no defaults must error");
    }

    #[test]
    fn walk_for_extension_collects_only_matching_files() {
        let root = tempfile::tempdir().expect("tempdir");
        std::fs::write(root.path().join("a.parquet"), b"x").expect("a");
        std::fs::write(root.path().join("b.jsonl"), b"x").expect("b");
        std::fs::create_dir(root.path().join("nested")).expect("nested");
        std::fs::write(root.path().join("nested").join("c.parquet"), b"x").expect("c");
        std::fs::write(root.path().join("nested").join("d.txt"), b"x").expect("d");

        let files = walk_for_extension(root.path(), "parquet");
        assert_eq!(files.len(), 2);
        for path in &files {
            assert_eq!(path.extension().and_then(|e| e.to_str()), Some("parquet"));
        }
        // Sorted lexically.
        assert!(files[0].to_string_lossy().ends_with("a.parquet"));
        assert!(files[1].to_string_lossy().ends_with("nested/c.parquet"));
    }
}
