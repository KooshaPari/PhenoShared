// SPDX-License-Identifier: MIT OR Apache-2.0
// SPDX-FileCopyrightText: 2026 KooshaPari <kooshapari@gmail.com>

//! PE section reader port for Pine processes.
//!
//! A loaded PE image is divided into named sections (<c>.text</c>,
//! <c>.data</c>, <c>.rdata</c>, <c>.rsrc</c>, …).  Each section has a
//! virtual address, a virtual size, and a backing byte buffer.  The
//! port abstracts the concrete reader (in-memory slice, mmap, remote
//! fetch) so the loader, the syscall handler, and the inspector stay
//! engine-agnostic.
//!
//! Reference: kmobile/crates/kmobile-core/src/ports/ (Rust port),
//! phenotype-voxel/src/ports/ (Rust port).

use std::collections::HashMap;
use std::io;
use thiserror::Error;

/// Inert, content-addressed description of a PE section.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Section {
    /// Section name as it appears in the PE header (e.g. <c>".text"</c>).
    pub name: String,
    /// Virtual address of the first byte of the section.
    pub virtual_address: u64,
    /// Virtual size of the section in bytes (may exceed <c>raw_data.len()</c>).
    pub virtual_size: u64,
    /// Backing bytes; trailing bytes inside <c>virtual_size</c> are
    /// implicitly zero (per the PE spec).
    pub raw_data: Vec<u8>,
}

/// Port-level errors raised by section readers and their adapters.
#[derive(Debug, Error)]
pub enum SectionError {
    /// No section with the given name is present in the image.
    #[error("section not found: {0}")]
    NotFound(String),
    /// Underlying reader backend failed (mmap, network fetch, …).
    #[error("io error: {0}")]
    Io(#[from] io::Error),
    /// A <c>read_bytes</c> request fell outside any loaded section.
    #[error("read out of bounds: va=0x{va:x}, len={len}")]
    OutOfBounds {
        /// Virtual address the caller asked about.
        va: u64,
        /// Requested byte count.
        len: usize,
    },
}

/// Hexagonal port: read named sections and arbitrary virtual-address
/// ranges from a loaded PE image.
///
/// Domain code depends on this trait; the concrete adapter is injected.
pub trait SectionReader {
    /// Reads a whole section by name.
    fn read_section(&self, name: &str) -> Result<Section, SectionError>;

    /// Returns the names of all loaded sections, in insertion order.
    fn list_sections(&self) -> Vec<String>;

    /// Reads <c>len</c> bytes starting at virtual address <c>va</c>.
    /// Returns [`SectionError::OutOfBounds`] if the range is not fully
    /// contained within a single loaded section.
    fn read_bytes(&self, virtual_address: u64, len: usize) -> Result<Vec<u8>, SectionError>;
}

/// Default in-memory adapter.  Used by the loader, by tests, and as the
/// canonical null-adapter when no engine image is wired in.
pub struct InMemorySectionReader {
    by_name: HashMap<String, Section>,
    order: Vec<String>,
}

impl Default for InMemorySectionReader {
    fn default() -> Self {
        Self::new()
    }
}

impl InMemorySectionReader {
    /// Creates an empty reader.
    pub fn new() -> Self {
        Self {
            by_name: HashMap::new(),
            order: Vec::new(),
        }
    }

    /// Inserts (or replaces) a section.
    pub fn insert(&mut self, section: Section) {
        if !self.by_name.contains_key(&section.name) {
            self.order.push(section.name.clone());
        }
        self.by_name.insert(section.name.clone(), section);
    }

    /// Returns the section that owns <c>va</c>, if any.
    fn section_at(&self, va: u64) -> Option<&Section> {
        self.by_name
            .values()
            .find(|s| va >= s.virtual_address && va < s.virtual_address + s.virtual_size)
    }
}

impl SectionReader for InMemorySectionReader {
    fn read_section(&self, name: &str) -> Result<Section, SectionError> {
        self.by_name
            .get(name)
            .cloned()
            .ok_or_else(|| SectionError::NotFound(name.to_owned()))
    }

    fn list_sections(&self) -> Vec<String> {
        self.order.clone()
    }

    fn read_bytes(&self, virtual_address: u64, len: usize) -> Result<Vec<u8>, SectionError> {
        let s = self
            .section_at(virtual_address)
            .ok_or(SectionError::OutOfBounds {
                va: virtual_address,
                len,
            })?;
        let end = virtual_address
            .checked_add(len as u64)
            .ok_or(SectionError::OutOfBounds {
                va: virtual_address,
                len,
            })?;
        if end > s.virtual_address + s.virtual_size {
            return Err(SectionError::OutOfBounds {
                va: virtual_address,
                len,
            });
        }
        let offset = (virtual_address - s.virtual_address) as usize;
        let mut out = Vec::with_capacity(len);
        for i in 0..len {
            let idx = offset + i;
            out.push(*s.raw_data.get(idx).unwrap_or(&0));
        }
        Ok(out)
    }
}

/// Recording mock for domain tests.  Each call is appended to
/// <c>calls</c> so a test can assert on the interaction order.
pub struct MockSectionReader {
    sections: HashMap<String, Section>,
    /// Sequence of operation signatures invoked on this mock.
    pub calls: std::cell::RefCell<Vec<String>>,
}

impl Default for MockSectionReader {
    fn default() -> Self {
        Self::new()
    }
}

impl MockSectionReader {
    /// Creates an empty recording mock.
    pub fn new() -> Self {
        Self {
            sections: HashMap::new(),
            calls: std::cell::RefCell::new(Vec::new()),
        }
    }

    /// Stages a section for the mock to serve.
    pub fn stage(&mut self, section: Section) {
        self.sections.insert(section.name.clone(), section);
    }
}

impl SectionReader for MockSectionReader {
    fn read_section(&self, name: &str) -> Result<Section, SectionError> {
        self.calls
            .borrow_mut()
            .push(format!("read_section({name})"));
        self.sections
            .get(name)
            .cloned()
            .ok_or_else(|| SectionError::NotFound(name.to_owned()))
    }

    fn list_sections(&self) -> Vec<String> {
        self.calls.borrow_mut().push("list_sections".to_owned());
        let mut names: Vec<String> = self.sections.keys().cloned().collect();
        names.sort();
        names
    }

    fn read_bytes(&self, virtual_address: u64, len: usize) -> Result<Vec<u8>, SectionError> {
        self.calls.borrow_mut().push(format!(
            "read_bytes(va=0x{va:x}, len={len})",
            va = virtual_address
        ));
        let s = self
            .sections
            .values()
            .find(|s| {
                virtual_address >= s.virtual_address
                    && virtual_address < s.virtual_address + s.virtual_size
            })
            .ok_or(SectionError::OutOfBounds {
                va: virtual_address,
                len,
            })?;
        let end = virtual_address
            .checked_add(len as u64)
            .ok_or(SectionError::OutOfBounds {
                va: virtual_address,
                len,
            })?;
        if end > s.virtual_address + s.virtual_size {
            return Err(SectionError::OutOfBounds {
                va: virtual_address,
                len,
            });
        }
        let offset = (virtual_address - s.virtual_address) as usize;
        let mut out = Vec::with_capacity(len);
        for i in 0..len {
            let idx = offset + i;
            out.push(*s.raw_data.get(idx).unwrap_or(&0));
        }
        Ok(out)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn section(name: &str, va: u64, vsize: u64, data: Vec<u8>) -> Section {
        Section {
            name: name.to_owned(),
            virtual_address: va,
            virtual_size: vsize,
            raw_data: data,
        }
    }

    #[test]
    fn in_memory_read_section_and_list() {
        let mut r = InMemorySectionReader::new();
        r.insert(section(".text", 0x1000, 0x100, vec![0x90; 16]));
        r.insert(section(".rdata", 0x2000, 0x40, b"hello".to_vec()));

        // list_sections preserves insertion order
        assert_eq!(r.list_sections(), vec![".text", ".rdata"]);

        let text = r.read_section(".text").unwrap();
        assert_eq!(text.virtual_address, 0x1000);
        assert_eq!(text.raw_data.len(), 16);

        // happy path: read_bytes inside .text
        let bytes = r.read_bytes(0x1004, 4).unwrap();
        assert_eq!(bytes, vec![0x90, 0x90, 0x90, 0x90]);
    }

    #[test]
    fn read_bytes_past_section_end_returns_out_of_bounds() {
        let mut r = InMemorySectionReader::new();
        r.insert(section(".data", 0x4000, 0x10, vec![0xAA; 8]));
        // Range straddles the section boundary.
        match r.read_bytes(0x4008, 16) {
            Err(SectionError::OutOfBounds { va, len }) => {
                assert_eq!(va, 0x4008);
                assert_eq!(len, 16);
            }
            other => panic!("expected OutOfBounds, got {:?}", other),
        }
        // Range entirely outside any section.
        match r.read_bytes(0x9999, 4) {
            Err(SectionError::OutOfBounds { .. }) => {}
            other => panic!("expected OutOfBounds, got {:?}", other),
        }
    }

    #[test]
    fn virtual_size_larger_than_raw_data_zero_fills() {
        // Per the PE spec, bytes within virtual_size but past raw_data
        // are implicitly zero.  read_bytes must yield those zeros.
        let mut r = InMemorySectionReader::new();
        r.insert(section(".bss", 0x8000, 0x1000, Vec::new()));
        let bytes = r.read_bytes(0x8010, 4).unwrap();
        assert_eq!(bytes, vec![0, 0, 0, 0]);
    }

    #[test]
    fn mock_implements_section_reader_trait() {
        // Trait conformance: MockSectionReader is a SectionReader.
        let mut mock = MockSectionReader::new();
        mock.stage(section(".text", 0x1000, 0x100, vec![0xCC; 8]));
        let reader: &dyn SectionReader = &mock;
        let s = reader.read_section(".text").unwrap();
        assert_eq!(s.raw_data, vec![0xCC; 8]);
        let names = reader.list_sections();
        assert_eq!(names, vec![".text"]);
    }

    #[test]
    fn mock_records_calls_and_surfaces_errors() {
        let mut mock = MockSectionReader::new();
        mock.stage(section(".text", 0x1000, 0x100, vec![0xCC; 8]));

        let _ = mock.list_sections();
        let _ = mock.read_section(".text");
        // NotFound path
        match mock.read_section(".missing") {
            Err(SectionError::NotFound(n)) => assert_eq!(n, ".missing"),
            other => panic!("expected NotFound, got {:?}", other),
        }
        // OutOfBounds path
        let _ = mock.read_bytes(0x9999, 1);

        let calls = mock.calls.borrow();
        assert_eq!(calls.len(), 4);
        assert_eq!(calls[0], "list_sections");
        assert_eq!(calls[1], "read_section(.text)");
        assert_eq!(calls[2], "read_section(.missing)");
        assert!(calls[3].starts_with("read_bytes(va=0x9999"));
    }
}
