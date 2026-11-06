// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 KooshaPari <kooshapari@gmail.com>

//! Symbol resolution port for Pine processes.
//!
//! A Pine process links against many modules (the executable itself,
//! `kernel32.dll`, `ntdll.dll`, user DLLs).  Each module exports a set
//! of named symbols (functions, data) bound to virtual addresses.  The
//! port abstracts the concrete symbol backend (in-memory table, PE
//! export directory, PDB, remote symbol server) so the dynamic linker
//! and the syscall handler stay engine-agnostic.
//!
//! Reference: kmobile/crates/kmobile-core/src/ports/ (Rust port),
//! phenotype-voxel/src/ports/ (Rust port).

use std::collections::HashMap;
use std::io;
use thiserror::Error;

/// A resolved symbol: a name bound to a virtual address inside a module.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Symbol {
    /// Exported symbol name (e.g. <c>"CreateFileW"</c>).
    pub name: String,
    /// Owning module name (e.g. <c>"kernel32.dll"</c>).
    pub module: String,
    /// Virtual address of the symbol within the module.
    pub address: u64,
}

/// Port-level errors raised by symbol resolution and its adapters.
#[derive(Debug, Error)]
pub enum ResolveError {
    /// The symbol name is not exported by any module.
    #[error("symbol not found: {0}")]
    NotFound(String),
    /// The symbol name resolves to more than one address.
    #[error("ambiguous symbol '{name}': {matches} candidates")]
    Ambiguous {
        /// The ambiguous symbol name.
        name: String,
        /// Number of candidate modules that export the name.
        matches: usize,
    },
    /// Underlying backend failed (PE export walk, network symbol server, …).
    #[error("io error: {0}")]
    Io(#[from] io::Error),
}

/// Hexagonal port: resolve a symbol name to a virtual address.
///
/// Domain code depends on this trait; the concrete adapter is injected.
pub trait SymbolResolver {
    /// Resolves <c>name</c> across all loaded modules.
    ///
    /// Returns [`ResolveError::Ambiguous`] if more than one module exports
    /// the same name.  Use [`resolve_in_module`](Self::resolve_in_module)
    /// to disambiguate.
    fn resolve(&self, name: &str) -> Result<Symbol, ResolveError>;

    /// Resolves <c>name</c> within a specific <c>module</c>.
    fn resolve_in_module(&self, name: &str, module: &str) -> Result<Symbol, ResolveError>;

    /// Returns all symbols exported by <c>module</c>, in insertion order.
    fn list_module(&self, module: &str) -> Vec<&Symbol>;
}

/// Default in-memory adapter.  Used by the loader, by tests, and as the
/// canonical null-adapter when no engine symbol system is wired in.
pub struct InMemorySymbolResolver {
    /// Keyed by <c>(name, module)</c> so the same name may exist in many
    /// modules without ambiguity at this layer.
    by_key: HashMap<(String, String), Symbol>,
    /// Insertion order, kept so <c>list_module</c> is deterministic.
    order: Vec<(String, String)>,
}

impl Default for InMemorySymbolResolver {
    fn default() -> Self {
        Self::new()
    }
}

impl InMemorySymbolResolver {
    /// Creates an empty resolver.
    pub fn new() -> Self {
        Self {
            by_key: HashMap::new(),
            order: Vec::new(),
        }
    }

    /// Registers <c>symbol</c>.  If a symbol with the same
    /// <c>(name, module)</c> pair already exists, it is replaced.
    pub fn insert(&mut self, symbol: Symbol) {
        let key = (symbol.name.clone(), symbol.module.clone());
        if !self.by_key.contains_key(&key) {
            self.order.push(key.clone());
        }
        self.by_key.insert(key, symbol);
    }
}

impl SymbolResolver for InMemorySymbolResolver {
    fn resolve(&self, name: &str) -> Result<Symbol, ResolveError> {
        let hits: Vec<&Symbol> = self.by_key.values().filter(|s| s.name == name).collect();
        match hits.len() {
            0 => Err(ResolveError::NotFound(name.to_owned())),
            1 => Ok(hits[0].clone()),
            n => Err(ResolveError::Ambiguous {
                name: name.to_owned(),
                matches: n,
            }),
        }
    }

    fn resolve_in_module(&self, name: &str, module: &str) -> Result<Symbol, ResolveError> {
        self.by_key
            .get(&(name.to_owned(), module.to_owned()))
            .cloned()
            .ok_or_else(|| ResolveError::NotFound(name.to_owned()))
    }

    fn list_module(&self, module: &str) -> Vec<&Symbol> {
        self.order
            .iter()
            .filter_map(|key| {
                if key.1 == module {
                    self.by_key.get(key)
                } else {
                    None
                }
            })
            .collect()
    }
}

/// Recording mock for domain tests.  Each call is appended to
/// <c>calls</c> so a test can assert on the interaction order.
pub struct MockSymbolResolver {
    canned: HashMap<(String, String), Symbol>,
    /// Sequence of operation signatures invoked on this mock.
    pub calls: std::cell::RefCell<Vec<String>>,
}

impl Default for MockSymbolResolver {
    fn default() -> Self {
        Self::new()
    }
}

impl MockSymbolResolver {
    /// Creates an empty recording mock.
    pub fn new() -> Self {
        Self {
            canned: HashMap::new(),
            calls: std::cell::RefCell::new(Vec::new()),
        }
    }

    /// Stages a canned response for <c>(name, module)</c>.  If
    /// <c>module</c> is the empty string, the symbol is also returned by
    /// <c>resolve</c> regardless of module.
    pub fn stage(&mut self, symbol: Symbol) {
        let key = (symbol.name.clone(), symbol.module.clone());
        self.canned.insert(key, symbol);
    }
}

impl SymbolResolver for MockSymbolResolver {
    fn resolve(&self, name: &str) -> Result<Symbol, ResolveError> {
        self.calls.borrow_mut().push(format!("resolve({name})"));
        let hits: Vec<&Symbol> = self.canned.values().filter(|s| s.name == name).collect();
        match hits.len() {
            0 => Err(ResolveError::NotFound(name.to_owned())),
            1 => Ok(hits[0].clone()),
            n => Err(ResolveError::Ambiguous {
                name: name.to_owned(),
                matches: n,
            }),
        }
    }

    fn resolve_in_module(&self, name: &str, module: &str) -> Result<Symbol, ResolveError> {
        self.calls
            .borrow_mut()
            .push(format!("resolve_in_module({name}, {module})"));
        self.canned
            .get(&(name.to_owned(), module.to_owned()))
            .cloned()
            .ok_or_else(|| ResolveError::NotFound(name.to_owned()))
    }

    fn list_module(&self, module: &str) -> Vec<&Symbol> {
        self.calls
            .borrow_mut()
            .push(format!("list_module({module})"));
        self.canned
            .values()
            .filter(|s| s.module == module)
            .collect()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn sym(name: &str, module: &str, address: u64) -> Symbol {
        Symbol {
            name: name.to_owned(),
            module: module.to_owned(),
            address,
        }
    }

    #[test]
    fn in_memory_resolve_resolve_in_module_and_list() {
        let mut r = InMemorySymbolResolver::new();
        r.insert(sym("CreateFileW", "kernel32.dll", 0x7ffe_0001_0000));
        r.insert(sym("ReadFile", "kernel32.dll", 0x7ffe_0001_0010));

        let s = r.resolve_in_module("CreateFileW", "kernel32.dll").unwrap();
        assert_eq!(s.address, 0x7ffe_0001_0000);

        let listed = r.list_module("kernel32.dll");
        assert_eq!(listed.len(), 2);
        assert_eq!(listed[0].name, "CreateFileW");
        assert_eq!(listed[1].name, "ReadFile");

        // Cross-module resolve is a miss.
        assert!(matches!(
            r.resolve_in_module("CreateFileW", "ntdll.dll"),
            Err(ResolveError::NotFound(_))
        ));
    }

    #[test]
    fn in_memory_ambiguous_resolve_returns_error() {
        let mut r = InMemorySymbolResolver::new();
        r.insert(sym("memcpy", "msvcrt.dll", 0x1000));
        r.insert(sym("memcpy", "ntdll.dll", 0x2000));
        match r.resolve("memcpy") {
            Err(ResolveError::Ambiguous { name, matches }) => {
                assert_eq!(name, "memcpy");
                assert_eq!(matches, 2);
            }
            other => panic!("expected Ambiguous, got {:?}", other),
        }
        // resolve_in_module disambiguates.
        let s = r.resolve_in_module("memcpy", "msvcrt.dll").unwrap();
        assert_eq!(s.address, 0x1000);
    }

    #[test]
    fn mock_implements_symbol_resolver_trait() {
        // Compile-time + runtime trait conformance.
        let mut mock = MockSymbolResolver::new();
        mock.stage(sym("NtCreateFile", "ntdll.dll", 0x7fff_0000));
        let resolver: &dyn SymbolResolver = &mock;
        let s = resolver.resolve("NtCreateFile").unwrap();
        assert_eq!(s.address, 0x7fff_0000);
    }

    #[test]
    fn mock_records_calls_in_order() {
        let mut mock = MockSymbolResolver::new();
        mock.stage(sym("ExitProcess", "kernel32.dll", 0x7ffe_0010));
        mock.stage(sym("ExitProcess", "msvcrt.dll", 0x0040_0000));
        let _ = mock.resolve("ExitProcess"); // ambiguous
        let _ = mock.resolve_in_module("ExitProcess", "kernel32.dll");
        let _ = mock.list_module("kernel32.dll");

        let calls = mock.calls.borrow();
        assert_eq!(calls.len(), 3);
        assert_eq!(calls[0], "resolve(ExitProcess)");
        assert_eq!(calls[1], "resolve_in_module(ExitProcess, kernel32.dll)");
        assert_eq!(calls[2], "list_module(kernel32.dll)");
    }

    #[test]
    fn not_found_and_io_error_paths() {
        let r = InMemorySymbolResolver::new();
        // NotFound surface
        match r.resolve("nope") {
            Err(ResolveError::NotFound(n)) => assert_eq!(n, "nope"),
            other => panic!("expected NotFound, got {:?}", other),
        }

        // Io variant is constructible from a std::io::Error (#[from] io::Error).
        let io_err = io::Error::other("backend down");
        let resolve_err: ResolveError = io_err.into();
        match resolve_err {
            ResolveError::Io(e) => assert_eq!(e.kind(), io::ErrorKind::Other),
            other => panic!("expected Io, got {:?}", other),
        }
    }
}
