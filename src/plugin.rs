//! Runtime plugin loading system.
//!
//! Provides a [`Plugin`] trait, a [`PluginContext`] that is passed to plugins
//! during initialisation, and a [`PluginManager`] that keeps track of loaded
//! plugins and dispatches lifecycle calls.
//!
//! # Loading
//!
//! Plugins are loaded from a directory using [`PluginManager::load_from_dir`].
//! A *plugin manifest* is a file named `*.plugin` containing a TOML or JSON
//! document describing a [`PluginDescriptor`]. The loader parses each
//! manifest, validates required fields, and yields one descriptor per file.
//! The descriptor carries enough information (name, version, author,
//! description, kind, entry) for higher layers (or this manager in the
//! future) to instantiate a [`Plugin`] implementation. Dynamic `.so` /
//! `.dylib` loading via `dlopen` / `libloading` is explicitly out of scope;
//! see `docs/adr/ADR-NN-plugin-loading.md` for the planned extension.

use std::collections::HashMap;
use std::fmt;
use std::path::Path;

// ---------------------------------------------------------------------------
// Errors
// ---------------------------------------------------------------------------

/// Errors that can occur during plugin operations.
#[derive(Debug, Clone)]
pub enum PluginError {
    /// A plugin with the given name is already registered.
    AlreadyRegistered(String),
    /// No plugin with the given name is registered.
    NotFound(String),
    /// The directory path could not be read.
    IoError(String),
    /// Plugin initialisation returned an error.
    InitFailed(String),
    /// A `.plugin` file was found but its manifest could not be parsed.
    ManifestParse {
        /// The file path that failed to parse.
        path: String,
        /// Reason the parse failed.
        reason: String,
    },
    /// A manifest was parsed but is missing required fields.
    ManifestInvalid {
        /// The file path with the invalid manifest.
        path: String,
        /// Which field is missing or invalid.
        field: &'static str,
    },
}

impl fmt::Display for PluginError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PluginError::AlreadyRegistered(n) => write!(f, "plugin already registered: {n}"),
            PluginError::NotFound(n) => write!(f, "plugin not found: {n}"),
            PluginError::IoError(e) => write!(f, "I/O error: {e}"),
            PluginError::InitFailed(e) => write!(f, "plugin init failed: {e}"),
            PluginError::ManifestParse { path, reason } => {
                write!(f, "plugin manifest '{path}' could not be parsed: {reason}")
            }
            PluginError::ManifestInvalid { path, field } => {
                write!(f, "plugin manifest '{path}' is missing required field '{field}'")
            }
        }
    }
}

impl std::error::Error for PluginError {}

// ---------------------------------------------------------------------------
// PluginInfo
// ---------------------------------------------------------------------------

/// Descriptive metadata about a plugin.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PluginInfo {
    /// Human-readable plugin name.
    pub name: String,
    /// Semantic version string.
    pub version: String,
    /// Author / maintainer.
    pub author: String,
    /// Free-text description.
    pub description: String,
}

/// What kind of plugin a manifest describes.
///
/// Plugins that must execute alongside the engine are marked `Native`; pure
/// data/asset bundles are marked `Data`.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PluginKind {
    /// A native code plugin that exposes a `Plugin` implementation.
    Native,
    /// A data-only plugin (asset bundle, descriptor file, etc.).
    Data,
}

impl Default for PluginKind {
    fn default() -> Self {
        PluginKind::Native
    }
}

/// Parsed contents of a single `.plugin` manifest file.
///
/// A `.plugin` file is a TOML document of the form:
///
/// ```toml
/// kind = "native"
/// entry = "libmy_plugin.so"
/// [info]
/// name = "my-plugin"
/// version = "0.1.0"
/// author = "Acme"
/// description = "Adds new operators"
/// ```
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PluginDescriptor {
    /// Parsed [`PluginInfo`] block (required).
    pub info: PluginInfo,
    /// Plugin kind (defaults to [`PluginKind::Native`]).
    pub kind: PluginKind,
    /// Path or identifier of the plugin's entry point (e.g. library path).
    /// Optional for [`PluginKind::Data`] plugins.
    pub entry: Option<String>,
}

// ---------------------------------------------------------------------------
// Plugin trait
// ---------------------------------------------------------------------------

/// Trait that every runtime plugin must implement.
pub trait Plugin: Send {
    /// Return the unique name of this plugin.
    fn name(&self) -> &str;

    /// Return the version of this plugin.
    fn version(&self) -> &str;

    /// Initialise the plugin with the given [`PluginContext`].
    fn init(&mut self, ctx: &mut PluginContext) -> Result<(), PluginError>;
}

// ---------------------------------------------------------------------------
// PluginContext
// ---------------------------------------------------------------------------

/// Context object handed to plugins during [`Plugin::init`].
pub struct PluginContext {
    /// Opaque renderer handle (reserved for future use).
    pub renderer: (),
    /// Configuration key-value pairs.
    pub config: HashMap<String, String>,
}

impl PluginContext {
    /// Create a new context with an empty renderer and no config.
    pub fn new() -> Self {
        Self {
            renderer: (),
            config: HashMap::new(),
        }
    }
}

impl Default for PluginContext {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// PluginManager
// ---------------------------------------------------------------------------

/// Manages the lifecycle of plugins: registration, loading from a directory,
/// and execution.
pub struct PluginManager {
    /// Registered plugin instances keyed by name.
    plugins: Vec<Box<dyn Plugin>>,
    /// Metadata for every registered plugin.
    infos: Vec<PluginInfo>,
}

impl PluginManager {
    /// Create an empty manager.
    pub fn new() -> Self {
        Self {
            plugins: Vec::new(),
            infos: Vec::new(),
        }
    }

    /// Register a plugin.  Returns an error if a plugin with the same name is
    /// already registered.  Note: this only adds the plugin; call
    /// [`execute_all`](Self::execute_all) to initialise and run all registered
    /// plugins.
    pub fn register<P: Plugin + 'static>(
        &mut self,
        plugin: P,
        info: PluginInfo,
    ) -> Result<(), PluginError> {
        let name = plugin.name().to_owned();
        if self.plugins.iter().any(|p| p.name() == name) {
            return Err(PluginError::AlreadyRegistered(name));
        }
        self.plugins.push(Box::new(plugin));
        self.infos.push(info);
        Ok(())
    }

    /// Load plugin manifests from a directory.
    ///
    /// For every `*.plugin` file found in `dir`, read its contents and parse
    /// it as a manifest.  Files that cannot be read or parsed produce
    /// [`PluginError::IoError`] / [`PluginError::ManifestParse`]; files parsed
    /// but missing required fields produce [`PluginError::ManifestInvalid`].
    /// On the first error the method aborts and returns that error — partial
    /// loads are not retained, matching the "fail loud" principle.
    ///
    /// This method does **not** instantiate a [`Plugin`] implementation from
    /// each descriptor.  Dynamic library loading is out of scope for this
    /// crate; future work should add a `register_from_descriptor` step that
    /// maps `kind = "native"` + `entry` to a concrete `Box<dyn Plugin>`.
    pub fn load_from_dir(&self, dir: &Path) -> Result<Vec<PluginDescriptor>, PluginError> {
        let entries = std::fs::read_dir(dir).map_err(|e| {
            PluginError::IoError(format!(
                "failed to read directory '{}': {e}",
                dir.display()
            ))
        })?;

        let mut manifests = Vec::new();
        let mut paths: Vec<std::path::PathBuf> = entries
            .flatten()
            .map(|e| e.path())
            .filter(|p| {
                p.extension()
                    .and_then(|e| e.to_str())
                    .map(|s| s.eq_ignore_ascii_case("plugin"))
                    .unwrap_or(false)
            })
            .collect();
        // Stable ordering — manifests must not depend on `read_dir` order.
        paths.sort();

        for path in &paths {
            let descriptor = parse_plugin_descriptor(path)?;
            manifests.push(descriptor);
        }
        Ok(manifests)
    }

    /// Initialise and execute every registered plugin with the given context.
    ///
    /// Returns a list of `(name, Ok(()))` or `(name, Err(message))` pairs.
    pub fn execute_all(&mut self, ctx: &mut PluginContext) -> Vec<(String, Result<(), String>)> {
        let mut results = Vec::with_capacity(self.plugins.len());
        for plugin in self.plugins.iter_mut() {
            let name = plugin.name().to_owned();
            let result = plugin.init(ctx).map_err(|e| e.to_string());
            results.push((name, result));
        }
        results
    }

    /// Return metadata for all registered plugins.
    pub fn list_plugins(&self) -> Vec<PluginInfo> {
        self.infos.clone()
    }

    /// Number of registered plugins.
    pub fn len(&self) -> usize {
        self.plugins.len()
    }

    /// Whether no plugins are registered.
    pub fn is_empty(&self) -> bool {
        self.plugins.is_empty()
    }
}

impl Default for PluginManager {
    fn default() -> Self {
        Self::new()
    }
}

// ---------------------------------------------------------------------------
// Manifest parsing
// ---------------------------------------------------------------------------

/// Parse a single `.plugin` manifest file into a [`PluginDescriptor`].
///
/// Manifests are TOML documents with a required `[info]` block and
/// optional `kind` / `entry` keys.  We intentionally do not pull in a TOML
/// crate dependency for this: a minimal grammar (lines of the form
/// `key = "value"` and a `[info]` section header) covers the manifest shape
/// and keeps the dependency surface zero.  When the manifest grammar
/// grows, this function is the one to swap for a real TOML / JSON parser.
fn parse_plugin_descriptor(path: &Path) -> Result<PluginDescriptor, PluginError> {
    let raw = std::fs::read_to_string(path).map_err(|e| {
        PluginError::IoError(format!("failed to read '{}': {e}", path.display()))
    })?;

    let manifest = Manifest::parse(&raw).map_err(|reason| PluginError::ManifestParse {
        path: path.display().to_string(),
        reason,
    })?;

    let info = manifest.info.ok_or_else(|| PluginError::ManifestInvalid {
        path: path.display().to_string(),
        field: "info",
    })?;
    if info.name.is_empty() {
        return Err(PluginError::ManifestInvalid {
            path: path.display().to_string(),
            field: "info.name",
        });
    }

    let kind = match manifest.kind.as_deref() {
        None | Some("native") => PluginKind::Native,
        Some("data") => PluginKind::Data,
        Some(other) => {
            return Err(PluginError::ManifestParse {
                path: path.display().to_string(),
                reason: format!("unknown plugin kind '{other}'"),
            });
        }
    };

    Ok(PluginDescriptor {
        info,
        kind,
        entry: manifest.entry,
    })
}

/// Minimal key=value manifest parser used by [`parse_plugin_descriptor`].
struct Manifest {
    info: Option<PluginInfo>,
    kind: Option<String>,
    entry: Option<String>,
}

impl Manifest {
    fn parse(input: &str) -> Result<Self, String> {
        let mut info_lines: Vec<(String, String)> = Vec::new();
        let mut top_lines: Vec<(String, String)> = Vec::new();
        let mut current_section: Option<&str> = None;

        for (idx, raw) in input.lines().enumerate() {
            let line = raw.trim();
            if line.is_empty() || line.starts_with('#') {
                continue;
            }
            if let Some(stripped) = line.strip_prefix('[').and_then(|s| s.strip_suffix(']')) {
                current_section = Some(stripped.trim());
                continue;
            }
            let (key, value) = line.split_once('=').ok_or_else(|| {
                format!("line {}: expected 'key = value', got '{raw}'", idx + 1)
            })?;
            let key = key.trim().to_owned();
            // Strip optional quotes from value.
            let value = value.trim();
            let value = value
                .strip_prefix('"')
                .and_then(|s| s.strip_suffix('"'))
                .unwrap_or(value)
                .to_owned();

            match current_section {
                Some("info") => info_lines.push((key, value)),
                _ => top_lines.push((key, value)),
            }
        }

        let info = if info_lines.is_empty() {
            None
        } else {
            let mut name = String::new();
            let mut version = String::new();
            let mut author = String::new();
            let mut description = String::new();
            for (k, v) in info_lines {
                match k.as_str() {
                    "name" => name = v,
                    "version" => version = v,
                    "author" => author = v,
                    "description" => description = v,
                    other => {
                        return Err(format!("unknown [info] field '{other}'"));
                    }
                }
            }
            Some(PluginInfo {
                name,
                version,
                author,
                description,
            })
        };

        let mut kind = None;
        let mut entry = None;
        for (k, v) in top_lines {
            match k.as_str() {
                "kind" => kind = Some(v),
                "entry" => entry = Some(v),
                other => return Err(format!("unknown top-level key '{other}'")),
            }
        }

        Ok(Manifest {
            info,
            kind,
            entry,
        })
    }
}

// ===========================================================================
// Tests
// ===========================================================================

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    // ---- helpers ----------------------------------------------------------

    /// A trivial plugin that always initialises successfully.
    struct DummyPlugin {
        name: &'static str,
        version: &'static str,
    }

    impl Plugin for DummyPlugin {
        fn name(&self) -> &str {
            self.name
        }
        fn version(&self) -> &str {
            self.version
        }
        fn init(&mut self, _ctx: &mut PluginContext) -> Result<(), PluginError> {
            Ok(())
        }
    }

    fn dummy_info(name: &str) -> PluginInfo {
        PluginInfo {
            name: name.to_owned(),
            version: "0.1.0".to_owned(),
            author: "Test".to_owned(),
            description: "A test plugin".to_owned(),
        }
    }

    /// A plugin that fails during initialisation.
    struct FailingPlugin;

    impl Plugin for FailingPlugin {
        fn name(&self) -> &str {
            "failing"
        }
        fn version(&self) -> &str {
            "0.0.0"
        }
        fn init(&mut self, _ctx: &mut PluginContext) -> Result<(), PluginError> {
            Err(PluginError::InitFailed("boom".into()))
        }
    }

    /// RAII temp directory used in tests. Avoids pulling in `tempfile`
    /// because this module ships std-only.
    struct TmpDir {
        path: std::path::PathBuf,
    }
    impl TmpDir {
        fn new() -> Self {
            use std::sync::atomic::{AtomicU64, Ordering};
            static COUNTER: AtomicU64 = AtomicU64::new(0);
            let id = COUNTER.fetch_add(1, Ordering::SeqCst);
            let pid = std::process::id();
            let dir = std::env::temp_dir().join(format!("phenotype-plugin-test-{pid}-{id}"));
            std::fs::create_dir_all(&dir).expect("create tempdir");
            Self { path: dir }
        }
        fn path(&self) -> &Path {
            &self.path
        }
    }
    impl Drop for TmpDir {
        fn drop(&mut self) {
            let _ = std::fs::remove_dir_all(&self.path);
        }
    }

    /// Helper: write a manifest file into `dir` and return its path.
    fn write_manifest(dir: &Path, file_name: &str, body: &str) -> PathBuf {
        let path = dir.join(file_name);
        std::fs::write(&path, body).expect("failed to write manifest");
        path
    }

    // ---- tests ------------------------------------------------------------

    #[test]
    fn register_and_list_plugins() {
        let mut mgr = PluginManager::new();
        mgr.register(
            DummyPlugin {
                name: "a",
                version: "1.0",
            },
            dummy_info("a"),
        )
        .unwrap();
        mgr.register(
            DummyPlugin {
                name: "b",
                version: "2.0",
            },
            dummy_info("b"),
        )
        .unwrap();

        let list = mgr.list_plugins();
        assert_eq!(list.len(), 2);
        assert_eq!(list[0].name, "a");
        assert_eq!(list[1].name, "b");
    }

    #[test]
    fn duplicate_register_returns_error() {
        let mut mgr = PluginManager::new();
        mgr.register(
            DummyPlugin {
                name: "dup",
                version: "1",
            },
            dummy_info("dup"),
        )
        .unwrap();

        let err = mgr
            .register(
                DummyPlugin {
                    name: "dup",
                    version: "2",
                },
                dummy_info("dup"),
            )
            .unwrap_err();

        assert!(
            matches!(err, PluginError::AlreadyRegistered(ref n) if n == "dup"),
            "expected AlreadyRegistered, got: {err}"
        );
    }

    #[test]
    fn execute_all_runs_all_plugins() {
        let mut mgr = PluginManager::new();
        mgr.register(
            DummyPlugin {
                name: "x",
                version: "1",
            },
            dummy_info("x"),
        )
        .unwrap();
        mgr.register(
            DummyPlugin {
                name: "y",
                version: "1",
            },
            dummy_info("y"),
        )
        .unwrap();

        let results = mgr.execute_all(&mut PluginContext::new());
        assert_eq!(results.len(), 2);
        assert!(results.iter().all(|(_, r)| r.is_ok()));
    }

    #[test]
    fn execute_all_propagates_init_failure() {
        let mut mgr = PluginManager::new();
        mgr.register(
            DummyPlugin {
                name: "ok",
                version: "1",
            },
            dummy_info("ok"),
        )
        .unwrap();
        mgr.register(FailingPlugin, dummy_info("failing")).unwrap();

        let results = mgr.execute_all(&mut PluginContext::new());
        assert_eq!(results.len(), 2);

        let ok_result = results.iter().find(|(n, _)| n == "ok").unwrap();
        assert!(ok_result.1.is_ok());

        let fail_result = results.iter().find(|(n, _)| n == "failing").unwrap();
        assert!(fail_result.1.is_err());
        assert!(fail_result.1.as_ref().unwrap_err().contains("boom"));
    }

    #[test]
    fn len_and_is_empty_reflect_registrations() {
        let mut mgr = PluginManager::new();
        assert!(mgr.is_empty());
        assert_eq!(mgr.len(), 0);

        mgr.register(
            DummyPlugin {
                name: "one",
                version: "1",
            },
            dummy_info("one"),
        )
        .unwrap();
        assert!(!mgr.is_empty());
        assert_eq!(mgr.len(), 1);
    }

    #[test]
    fn plugin_context_default_is_empty() {
        let ctx = PluginContext::new();
        assert!(ctx.config.is_empty());
    }

    #[test]
    fn load_from_dir_nonexistent_returns_io_error() {
        let mgr = PluginManager::new();
        let err = mgr
            .load_from_dir(Path::new("/nonexistent/path/that/does/not/exist"))
            .unwrap_err();
        assert!(
            matches!(err, PluginError::IoError(_)),
            "expected IoError variant, got: {err}"
        );
    }

    #[test]
    fn load_from_dir_returns_empty_when_no_manifests() {
        let dir = TmpDir::new();
        // Write a non-.plugin file; the loader must ignore it.
        std::fs::write(dir.path().join("not_a_plugin.txt"), "ignored").unwrap();
        let mgr = PluginManager::new();
        let manifests = mgr.load_from_dir(dir.path()).unwrap();
        assert!(manifests.is_empty());
    }

    #[test]
    fn load_from_dir_parses_well_formed_manifests() {
        let dir = TmpDir::new();
        write_manifest(
            dir.path(),
            "alpha.plugin",
            r#"kind = "native"
entry = "libalpha.so"

[info]
name = "alpha"
version = "1.2.3"
author = "Acme"
description = "first plugin"
"#,
        );
        write_manifest(
            dir.path(),
            "beta.plugin",
            r#"kind = "data"

[info]
name = "beta"
version = "0.0.1"
author = "Acme"
description = "data bundle"
"#,
        );

        let mgr = PluginManager::new();
        let mut manifests = mgr.load_from_dir(dir.path()).unwrap();
        // alphabetical ordering: alpha < beta
        manifests.sort_by(|a, b| a.info.name.cmp(&b.info.name));

        assert_eq!(manifests.len(), 2);

        let alpha = &manifests[0];
        assert_eq!(alpha.info.name, "alpha");
        assert_eq!(alpha.info.version, "1.2.3");
        assert_eq!(alpha.info.author, "Acme");
        assert_eq!(alpha.kind, PluginKind::Native);
        assert_eq!(alpha.entry.as_deref(), Some("libalpha.so"));

        let beta = &manifests[1];
        assert_eq!(beta.info.name, "beta");
        assert_eq!(beta.kind, PluginKind::Data);
        assert_eq!(beta.entry, None);
    }

    #[test]
    fn load_from_dir_missing_info_section_errors() {
        let dir = TmpDir::new();
        write_manifest(
            dir.path(),
            "broken.plugin",
            r#"kind = "native"
entry = "libbroken.so"
"#,
        );
        let mgr = PluginManager::new();
        let err = mgr.load_from_dir(dir.path()).unwrap_err();
        assert!(
            matches!(err, PluginError::ManifestInvalid { .. }),
            "expected ManifestInvalid, got: {err}"
        );
    }

    #[test]
    fn load_from_dir_empty_name_errors() {
        let dir = TmpDir::new();
        write_manifest(
            dir.path(),
            "noname.plugin",
            r#"[info]
name = ""
version = "0.0.1"
"#,
        );
        let mgr = PluginManager::new();
        let err = mgr.load_from_dir(dir.path()).unwrap_err();
        assert!(
            matches!(
                err,
                PluginError::ManifestInvalid {
                    field: "info.name",
                    ..
                }
            ),
            "expected ManifestInvalid field=info.name, got: {err}"
        );
    }

    #[test]
    fn load_from_dir_unknown_kind_errors() {
        let dir = TmpDir::new();
        write_manifest(
            dir.path(),
            "weird.plugin",
            r#"kind = "exotic"

[info]
name = "weird"
version = "0.0.1"
"#,
        );
        let mgr = PluginManager::new();
        let err = mgr.load_from_dir(dir.path()).unwrap_err();
        assert!(
            matches!(err, PluginError::ManifestParse { .. }),
            "expected ManifestParse, got: {err}"
        );
    }

    #[test]
    fn plugin_info_clone_eq_and_debug() {
        let info = PluginInfo {
            name: "p".to_owned(),
            version: "1.0".to_owned(),
            author: "me".to_owned(),
            description: "desc".to_owned(),
        };
        let info2 = info.clone();
        assert_eq!(info2.name, "p");
        let _ = format!("{info2:?}");
    }

    #[test]
    fn manifest_parser_handles_blank_lines_and_comments() {
        let raw = r#"
# leading comment
kind = "native"
# inline comment
entry = "libfoo.so"

[info]
name = "foo"
version = "0.1.0"
author = "x"
description = "y"
"#;
        let m = Manifest::parse(raw).expect("parse should succeed");
        let info = m.info.expect("[info] should produce info");
        assert_eq!(info.name, "foo");
        assert_eq!(m.kind.as_deref(), Some("native"));
        assert_eq!(m.entry.as_deref(), Some("libfoo.so"));
    }

    #[test]
    fn manifest_parser_rejects_malformed_line() {
        let raw = "[info]\nnot_a_kv_line\n";
        let err = Manifest::parse(raw).unwrap_err();
        assert!(err.contains("expected 'key = value'"));
    }

    #[test]
    fn plugin_kind_default_is_native() {
        assert_eq!(PluginKind::default(), PluginKind::Native);
    }
}
