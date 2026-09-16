//! Plugin architecture for OS syscall translators.
//!
//! This module provides a trait-based plugin system that allows syscall
//! translators to be registered statically at compile time or loaded
//! dynamically at runtime from shared libraries.
//!
//! # Architecture Overview
//!
//! ```text
//! ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
//! │  Static Plugins │────▶│  PluginRegistry │◀────│ Dynamic Plugins │
//! │  (compiled in)  │     │    (router)     │     │  (.so/.dylib)   │
//! └─────────────────┘     └─────────────────┘     └─────────────────┘
//!                               │
//!                               ▼
//!                     ┌─────────────────┐
//!                     │ SyscallTranslatorPlugin trait │
//!                     └─────────────────┘
//! ```
//!
//! # Quick Start
//!
//! ```rust
//! use pine_syscall::plugin::{SyscallTranslatorPlugin, PluginRegistry};
//! use pine_syscall::{SyscallName, SyscallResult, SyscallError};
//!
//! struct MyPlugin;
//! impl SyscallTranslatorPlugin for MyPlugin {
//!     fn name(&self) -> &str { "my-plugin" }
//!     fn version(&self) -> &str { "1.0.0" }
//!     fn supported_syscalls(&self) -> &[SyscallName] { &[SyscallName::Read] }
//!     fn translate(&self, num: u64, args: [u64; 6]) -> Result<SyscallResult, SyscallError> {
//!         Ok(SyscallResult { name: SyscallName::Read, number: num, args })
//!     }
//! }
//!
//! let mut registry = PluginRegistry::new();
//! registry.register(Box::new(MyPlugin));
//! ```
//!
//! # Dynamic Loading
//!
//! Plugins can be loaded at runtime from shared libraries. A dynamic plugin
//! must export two C symbols:
//!
//! ```c
//! void* pine_plugin_create(void);
//! void  pine_plugin_destroy(void* plugin);
//! ```
//!
//! The `create` function returns a `Box<dyn SyscallTranslatorPlugin>` cast to
//! `void*`. The `destroy` function accepts the same pointer and drops it. Both
//! functions must be `extern "C"` and `#[no_mangle]`.
//!
//! # Safety
//!
//! Dynamic loading is `unsafe` because the loaded library may execute arbitrary
//! code. The caller must ensure that the library comes from a trusted source.

use std::collections::HashMap;
use std::ffi::OsStr;
use std::fmt;
use std::path::{Path, PathBuf};

use crate::{SyscallError, SyscallName, SyscallResult, SyscallTranslator};

/// Trait for a plugin that translates OS syscalls.
///
/// Each plugin advertises the set of syscalls it supports. The
/// [`PluginRegistry`] uses this metadata to route translation requests to
/// the correct plugin.
///
/// Implementations must be `Send + Sync` so that the registry can be
/// shared across threads.
pub trait SyscallTranslatorPlugin: Send + Sync {
    /// Human-readable plugin name.
    ///
    /// This should be unique across all loaded plugins.
    fn name(&self) -> &str;

    /// Plugin version in semantic-versioning format.
    fn version(&self) -> &str;

    /// The set of syscalls this plugin can translate.
    ///
    /// The registry builds an index from this slice so that lookups are
    /// O(1) in the number of plugins.
    fn supported_syscalls(&self) -> &[SyscallName];

    /// Attempt to translate a raw syscall number into a structured result.
    ///
    /// The registry only calls this method when the syscall number is in
    /// the plugin's `supported_syscalls` list (after mapping through the
    /// base translator), but plugins may also perform their own validation.
    fn translate(&self, syscall_num: u64, args: [u64; 6]) -> Result<SyscallResult, SyscallError>;
}

/// Metadata describing a plugin without requiring trait-object dispatch.
///
/// This is useful for listing loaded plugins or generating documentation.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PluginManifest {
    /// Plugin name.
    pub name: String,
    /// Plugin version.
    pub version: String,
    /// Syscalls supported by this plugin.
    pub supported_syscalls: Vec<SyscallName>,
}

impl PluginManifest {
    /// Create a manifest from a plugin instance.
    pub fn from_plugin(plugin: &dyn SyscallTranslatorPlugin) -> Self {
        Self {
            name: plugin.name().to_string(),
            version: plugin.version().to_string(),
            supported_syscalls: plugin.supported_syscalls().to_vec(),
        }
    }
}

/// Error returned by the plugin loader.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PluginLoaderError {
    /// The shared library could not be loaded.
    LibraryLoadFailed(String),
    /// The required symbol was not found in the library.
    SymbolNotFound(String),
    /// The plugin path does not exist or is not a file.
    InvalidPath(PathBuf),
    /// The plugin directory could not be read.
    DirectoryReadFailed(String),
}

impl fmt::Display for PluginLoaderError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PluginLoaderError::LibraryLoadFailed(msg) => {
                write!(f, "failed to load library: {msg}")
            }
            PluginLoaderError::SymbolNotFound(sym) => {
                write!(f, "symbol not found: {sym}")
            }
            PluginLoaderError::InvalidPath(path) => {
                write!(f, "invalid plugin path: {}", path.display())
            }
            PluginLoaderError::DirectoryReadFailed(msg) => {
                write!(f, "failed to read directory: {msg}")
            }
        }
    }
}

impl std::error::Error for PluginLoaderError {}

/// Registry that holds and routes between multiple plugins.
///
/// A `PluginRegistry` is typically populated by a [`PluginLoader`] and
/// then used as the single entry-point for syscall translation.
///
/// The registry maintains an index from [`SyscallName`] to plugin index,
/// enabling O(1) routing once the syscall number is mapped to a name.
/// If no base translator is configured, the registry falls back to a
/// linear scan over all registered plugins.
pub struct PluginRegistry {
    plugins: Vec<Box<dyn SyscallTranslatorPlugin>>,
    index: HashMap<SyscallName, usize>,
    base_translator: Option<Box<dyn SyscallTranslator + Send + Sync>>,
}

impl Default for PluginRegistry {
    fn default() -> Self {
        Self::new()
    }
}

impl PluginRegistry {
    /// Create an empty registry with no base translator.
    pub fn new() -> Self {
        Self {
            plugins: Vec::new(),
            index: HashMap::new(),
            base_translator: None,
        }
    }

    /// Create a registry with a base translator for number-to-name mapping.
    ///
    /// The base translator is used to resolve syscall numbers before
    /// routing to the appropriate plugin. If a plugin is not found for the
    /// resolved name, the base translator's result is returned directly.
    pub fn with_translator<T: SyscallTranslator + Send + Sync + 'static>(translator: T) -> Self {
        Self {
            plugins: Vec::new(),
            index: HashMap::new(),
            base_translator: Some(Box::new(translator)),
        }
    }

    /// Set or replace the base translator.
    pub fn set_translator<T: SyscallTranslator + Send + Sync + 'static>(&mut self, translator: T) {
        self.base_translator = Some(Box::new(translator));
    }

    /// Register a plugin.
    ///
    /// Each syscall in the plugin's `supported_syscalls` is added to the
    /// routing index. If a syscall is already claimed by another plugin,
    /// the new plugin takes precedence (last-write-wins).
    pub fn register(&mut self, plugin: Box<dyn SyscallTranslatorPlugin>) {
        let idx = self.plugins.len();
        for &name in plugin.supported_syscalls() {
            self.index.insert(name, idx);
        }
        self.plugins.push(plugin);
    }

    /// Translate a syscall using the registered plugin that claims it.
    ///
    /// If a base translator is configured, the registry first resolves the
    /// number to a name, looks up the plugin, and delegates translation. If
    /// no plugin claims the syscall, the base translator's result is returned.
    ///
    /// Without a base translator, the registry iterates over all plugins
    /// and returns the first successful translation.
    pub fn translate(
        &self,
        syscall_num: u64,
        args: [u64; 6],
    ) -> Result<SyscallResult, SyscallError> {
        if let Some(ref translator) = self.base_translator {
            let base_result = translator.translate(syscall_num, args)?;
            if let Some(&idx) = self.index.get(&base_result.name) {
                self.plugins[idx].translate(syscall_num, args)
            } else {
                Ok(base_result)
            }
        } else {
            for plugin in &self.plugins {
                match plugin.translate(syscall_num, args) {
                    Ok(result) => return Ok(result),
                    Err(SyscallError::UnknownSyscall(_)) => continue,
                    Err(other) => return Err(other),
                }
            }
            Err(SyscallError::UnknownSyscall(syscall_num))
        }
    }

    /// Return a list of manifests for all registered plugins.
    pub fn list_plugins(&self) -> Vec<PluginManifest> {
        self.plugins
            .iter()
            .map(|p| PluginManifest::from_plugin(p.as_ref()))
            .collect()
    }

    /// Return the number of registered plugins.
    pub fn len(&self) -> usize {
        self.plugins.len()
    }

    /// Return true if no plugins are registered.
    pub fn is_empty(&self) -> bool {
        self.plugins.is_empty()
    }

    /// Look up a plugin by name.
    pub fn find_plugin(&self, name: &str) -> Option<&dyn SyscallTranslatorPlugin> {
        self.plugins
            .iter()
            .find(|p| p.name() == name)
            .map(|p| p.as_ref())
    }
}

/// Loader for discovering and instantiating plugins.
///
/// The loader supports two modes:
///
/// 1. **Static loading** — plugins are compiled into the binary and
///    registered directly with [`PluginRegistry::register`].
/// 2. **Dynamic loading** — plugins are loaded at runtime from shared
///    libraries (`.so`, `.dylib`, `.dll`) that export a standard
///    `pine_plugin_create` entry point.
///
/// # Dynamic Plugin ABI
///
/// A dynamic plugin must export two C symbols:
///
/// ```c
/// void* pine_plugin_create(void);
/// void  pine_plugin_destroy(void* plugin);
/// ```
///
/// The `create` function returns a `Box<dyn SyscallTranslatorPlugin>`
/// cast to `void*`. The `destroy` function accepts the same pointer and
/// drops it. Both functions must be `extern "C"`.
///
/// # Safety
///
/// Dynamic loading is `unsafe` because the loaded library may execute
/// arbitrary code. The caller must ensure that the library comes from a
/// trusted source.
pub struct PluginLoader;

impl Default for PluginLoader {
    fn default() -> Self {
        Self::new()
    }
}

impl PluginLoader {
    /// Create a new plugin loader.
    pub fn new() -> Self {
        Self
    }

    /// Register a statically-linked plugin.
    ///
    /// This is a convenience wrapper around `PluginRegistry::register`.
    pub fn register_static<P: SyscallTranslatorPlugin + 'static>(
        &self,
        registry: &mut PluginRegistry,
        plugin: P,
    ) {
        registry.register(Box::new(plugin));
    }

    /// Load a single dynamic plugin from a shared library path.
    ///
    /// # Safety
    ///
    /// The library must be a valid plugin that exports `pine_plugin_create`
    /// and `pine_plugin_destroy`. The caller is responsible for ensuring
    /// the library is trusted.
    ///
    /// # Errors
    ///
    /// Returns `PluginLoaderError` if the library cannot be loaded or the
    /// required symbols are missing.
    pub unsafe fn load_dynamic(
        &self,
        path: &Path,
    ) -> Result<Box<dyn SyscallTranslatorPlugin>, PluginLoaderError> {
        if !path.exists() {
            return Err(PluginLoaderError::InvalidPath(path.to_path_buf()));
        }

        let lib = libloading::Library::new(path)
            .map_err(|e| PluginLoaderError::LibraryLoadFailed(format!("{e}")))?;

        let create: libloading::Symbol<unsafe extern "C" fn() -> *mut std::ffi::c_void> = lib
            .get(b"pine_plugin_create\0")
            .map_err(|_| PluginLoaderError::SymbolNotFound("pine_plugin_create".to_string()))?;

        let ptr = create();
        if ptr.is_null() {
            return Err(PluginLoaderError::LibraryLoadFailed(
                "plugin_create returned null".to_string(),
            ));
        }

        // The library must stay loaded as long as the plugin is alive.
        // We wrap it in a DynamicPlugin that owns both the library and the
        // plugin instance.
        let plugin = *Box::from_raw(ptr as *mut Box<dyn SyscallTranslatorPlugin>);
        Ok(Box::new(DynamicPlugin { _lib: lib, plugin }))
    }

    /// Load all dynamic plugins from a directory.
    ///
    /// Non-library files are silently skipped.
    ///
    /// # Safety
    ///
    /// See [`Self::load_dynamic`].
    pub unsafe fn load_directory(
        &self,
        dir: &Path,
    ) -> Result<Vec<Box<dyn SyscallTranslatorPlugin>>, PluginLoaderError> {
        let entries = std::fs::read_dir(dir)
            .map_err(|e| PluginLoaderError::DirectoryReadFailed(format!("{e}")))?;

        let mut plugins = Vec::new();
        for entry in entries {
            let entry =
                entry.map_err(|e| PluginLoaderError::DirectoryReadFailed(format!("{e}")))?;
            let path = entry.path();
            if is_plugin_library(&path) {
                match self.load_dynamic(&path) {
                    Ok(plugin) => plugins.push(plugin),
                    Err(_) => continue, // skip invalid plugins
                }
            }
        }
        Ok(plugins)
    }
}

/// Internal wrapper that keeps a dynamic library loaded while the plugin
/// is in use.
struct DynamicPlugin {
    _lib: libloading::Library,
    plugin: Box<dyn SyscallTranslatorPlugin>,
}

impl SyscallTranslatorPlugin for DynamicPlugin {
    fn name(&self) -> &str {
        self.plugin.name()
    }
    fn version(&self) -> &str {
        self.plugin.version()
    }
    fn supported_syscalls(&self) -> &[SyscallName] {
        self.plugin.supported_syscalls()
    }
    fn translate(&self, syscall_num: u64, args: [u64; 6]) -> Result<SyscallResult, SyscallError> {
        self.plugin.translate(syscall_num, args)
    }
}

unsafe impl Send for DynamicPlugin {}
unsafe impl Sync for DynamicPlugin {}

/// Check whether a path looks like a plugin shared library.
fn is_plugin_library(path: &Path) -> bool {
    if let Some(ext) = path.extension().and_then(OsStr::to_str) {
        matches!(ext, "so" | "dylib" | "dll")
    } else {
        false
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{SyscallError, SyscallName, SyscallResult};

    struct TestPlugin {
        name: String,
        version: String,
        syscalls: Vec<SyscallName>,
    }

    impl SyscallTranslatorPlugin for TestPlugin {
        fn name(&self) -> &str {
            &self.name
        }
        fn version(&self) -> &str {
            &self.version
        }
        fn supported_syscalls(&self) -> &[SyscallName] {
            &self.syscalls
        }
        fn translate(
            &self,
            syscall_num: u64,
            args: [u64; 6],
        ) -> Result<SyscallResult, SyscallError> {
            if let Some(&name) = self.syscalls.first() {
                Ok(SyscallResult {
                    name,
                    number: syscall_num,
                    args,
                })
            } else {
                Err(SyscallError::UnknownSyscall(syscall_num))
            }
        }
    }

    #[test]
    fn registry_empty_translate_fails() {
        let registry = PluginRegistry::new();
        let result = registry.translate(0, [0; 6]);
        assert!(matches!(result, Err(SyscallError::UnknownSyscall(0))));
    }

    #[test]
    fn registry_static_plugin() {
        let mut registry = PluginRegistry::new();
        let plugin = TestPlugin {
            name: "test".to_string(),
            version: "0.1.0".to_string(),
            syscalls: vec![SyscallName::Read, SyscallName::Write],
        };
        registry.register(Box::new(plugin));
        assert_eq!(registry.len(), 1);
        assert!(!registry.is_empty());
    }

    #[test]
    fn registry_translate_with_base_translator() {
        let mut registry = PluginRegistry::with_translator(crate::X86_64SyscallTranslator::new());
        let plugin = TestPlugin {
            name: "file-plugin".to_string(),
            version: "1.0.0".to_string(),
            syscalls: vec![SyscallName::Read],
        };
        registry.register(Box::new(plugin));
        let result = registry.translate(0, [1, 2, 3, 4, 5, 6]).unwrap();
        assert_eq!(result.name, SyscallName::Read);
        assert_eq!(result.number, 0);
        assert_eq!(result.args, [1, 2, 3, 4, 5, 6]);
    }

    #[test]
    fn registry_fallback_to_base_translator() {
        let mut registry = PluginRegistry::with_translator(crate::X86_64SyscallTranslator::new());
        let plugin = TestPlugin {
            name: "empty".to_string(),
            version: "0.0.0".to_string(),
            syscalls: vec![],
        };
        registry.register(Box::new(plugin));
        let result = registry.translate(0, [0; 6]).unwrap();
        assert_eq!(result.name, SyscallName::Read);
    }

    #[test]
    fn registry_list_plugins() {
        let mut registry = PluginRegistry::new();
        registry.register(Box::new(TestPlugin {
            name: "a".to_string(),
            version: "1.0.0".to_string(),
            syscalls: vec![SyscallName::Read],
        }));
        let list = registry.list_plugins();
        assert_eq!(list.len(), 1);
        assert_eq!(list[0].name, "a");
        assert_eq!(list[0].version, "1.0.0");
        assert_eq!(list[0].supported_syscalls, vec![SyscallName::Read]);
    }

    #[test]
    fn registry_find_plugin() {
        let mut registry = PluginRegistry::new();
        registry.register(Box::new(TestPlugin {
            name: "finder".to_string(),
            version: "2.0.0".to_string(),
            syscalls: vec![],
        }));
        assert!(registry.find_plugin("finder").is_some());
        assert!(registry.find_plugin("missing").is_none());
    }

    #[test]
    fn plugin_loader_register_static() {
        let loader = PluginLoader::new();
        let mut registry = PluginRegistry::new();
        loader.register_static(
            &mut registry,
            TestPlugin {
                name: "static".to_string(),
                version: "1.0.0".to_string(),
                syscalls: vec![SyscallName::Open],
            },
        );
        assert_eq!(registry.len(), 1);
    }

    #[test]
    fn is_plugin_library_matches_extensions() {
        assert!(is_plugin_library(Path::new("foo.so")));
        assert!(is_plugin_library(Path::new("foo.dylib")));
        assert!(is_plugin_library(Path::new("foo.dll")));
        assert!(!is_plugin_library(Path::new("foo.txt")));
        assert!(!is_plugin_library(Path::new("foo")));
    }

    #[test]
    fn plugin_manifest_from_plugin() {
        let plugin = TestPlugin {
            name: "manifest-test".to_string(),
            version: "0.5.0".to_string(),
            syscalls: vec![SyscallName::Close],
        };
        let manifest = PluginManifest::from_plugin(&plugin);
        assert_eq!(manifest.name, "manifest-test");
        assert_eq!(manifest.version, "0.5.0");
        assert_eq!(manifest.supported_syscalls, vec![SyscallName::Close]);
    }

    #[test]
    fn plugin_loader_error_display() {
        let e = PluginLoaderError::SymbolNotFound("foo".to_string());
        assert_eq!(e.to_string(), "symbol not found: foo");
        let e2 = PluginLoaderError::InvalidPath(PathBuf::from("/tmp"));
        assert!(e2.to_string().contains("/tmp"));
    }
}
