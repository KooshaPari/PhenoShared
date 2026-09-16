//! pine-loader — ELF/PE loader adapter.
//!
//! This crate parses ELF and PE binaries using the [`goblin`] crate
//! and exposes structured representations of sections, symbols, and
//! metadata.
//!
//! # Example
//!
//! ```
//! use pine_loader::{parse_pe, parse_elf, ElfLoader};
//! use pine_core::traits::Loader;
//!
//! // Use the ElfLoader trait implementation
//! let loader = ElfLoader;
//! let _ = loader.load("/path/to/binary.elf");
//! ```

#![warn(missing_docs)]

use std::fmt;
use std::fs;
use std::io;
use std::path::Path;

use pine_core::traits::Loader;

/// Read all bytes from a path on disk.
///
/// This is a thin wrapper around [`std::fs::read`] that produces a
/// [`String`] error suitable for the [`pine_core::traits::Loader`]
/// trait. Use [`read_bytes_into`] when you want a richer error type.
pub fn read_bytes(path: &str) -> Result<Vec<u8>, String> {
    fs::read(Path::new(path)).map_err(|e| format!("read {path}: {e}"))
}

/// Same as [`read_bytes`] but returns the typed [`io::Error`] directly.
pub fn read_bytes_into(path: &str) -> io::Result<Vec<u8>> {
    fs::read(Path::new(path))
}

/// ELF binary loader.
///
/// Reads the file at the given path and returns its bytes, or a stringified
/// I/O error. The struct is a zero-sized type — instantiation is free.
///
/// # Example
///
/// ```
/// use pine_loader::ElfLoader;
/// use pine_core::traits::Loader;
///
/// let loader = ElfLoader;
/// // Loading a missing path is an error (not `Ok(vec![])`):
/// assert!(loader.load("/nonexistent/path/that/does/not/exist.elf").is_err());
/// ```
pub struct ElfLoader;

impl Loader for ElfLoader {
    /// Read the file at `path` and return its bytes.
    ///
    /// Returns `Err(msg)` if the file does not exist, the process lacks
    /// permission to read it, or any other I/O error occurs.
    fn load(&self, path: &str) -> Result<Vec<u8>, String> {
        read_bytes(path)
    }
}

/// PE binary loader.
///
/// Reads the file at the given path and returns its bytes, or a stringified
/// I/O error. Mirrors [`ElfLoader`] but is exposed as a distinct type so
/// downstream code can pattern-match on the format when parsing.
///
/// # Example
///
/// ```
/// use pine_loader::PeLoader;
/// use pine_core::traits::Loader;
///
/// let loader = PeLoader;
/// assert!(loader.load("/nonexistent/path/that/does/not/exist.exe").is_err());
/// ```
pub struct PeLoader;

impl Loader for PeLoader {
    /// Read the file at `path` and return its bytes.
    fn load(&self, path: &str) -> Result<Vec<u8>, String> {
        read_bytes(path)
    }
}

// ========== Typed errors ==========

/// Error type for loader operations.
#[derive(Debug)]
pub enum LoaderError {
    /// Error from the goblin parser.
    Goblin(goblin::error::Error),
    /// Invalid PE file.
    InvalidPE(String),
}

impl fmt::Display for LoaderError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            LoaderError::Goblin(e) => write!(f, "goblin error: {e}"),
            LoaderError::InvalidPE(msg) => write!(f, "invalid PE: {msg}"),
        }
    }
}

impl std::error::Error for LoaderError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match self {
            LoaderError::Goblin(e) => Some(e),
            LoaderError::InvalidPE(_) => None,
        }
    }
}

impl From<goblin::error::Error> for LoaderError {
    fn from(e: goblin::error::Error) -> Self {
        LoaderError::Goblin(e)
    }
}

/// Parsed representation of a PE section.
#[derive(Debug, Clone, PartialEq)]
pub struct PeSection {
    /// Section name.
    pub name: String,
    /// Virtual address.
    pub virtual_address: u64,
    /// Virtual size.
    pub virtual_size: u64,
    /// Size in file.
    pub raw_size: u64,
    /// Offset in file.
    pub raw_offset: u64,
    /// Section characteristics flags.
    pub characteristics: u32,
}

/// Parsed representation of a PE symbol.
#[derive(Debug, Clone, PartialEq)]
pub struct PeSymbol {
    /// Symbol name.
    pub name: String,
    /// Symbol address (RVA).
    pub address: u64,
    /// Symbol size.
    pub size: u64,
    /// Symbol kind (e.g., "export", "import").
    pub kind: String,
}

/// Parsed representation of a PE binary.
#[derive(Debug, Clone, PartialEq)]
pub struct PeBinary {
    /// Entry point RVA.
    pub entry_point: u64,
    /// Parsed sections.
    pub sections: Vec<PeSection>,
    /// Preferred image base address.
    pub image_base: u64,
    /// Whether the PE is 64-bit.
    pub is_64_bit: bool,
    /// Parsed symbols (exports and imports).
    pub symbols: Vec<PeSymbol>,
}

/// Parsed representation of an ELF section.
#[derive(Debug, Clone, PartialEq)]
pub struct ElfSection {
    /// Section name.
    pub name: String,
    /// Virtual address.
    pub address: u64,
    /// Section size.
    pub size: u64,
    /// File offset.
    pub offset: u64,
    /// Section flags.
    pub flags: u64,
}

/// Parsed representation of an ELF symbol.
#[derive(Debug, Clone, PartialEq)]
pub struct ElfSymbol {
    /// Symbol name.
    pub name: String,
    /// Symbol address.
    pub address: u64,
    /// Symbol size.
    pub size: u64,
    /// Symbol type (e.g., FUNC, OBJECT).
    pub kind: String,
}

/// Parsed representation of an ELF binary.
#[derive(Debug, Clone, PartialEq)]
pub struct ElfBinary {
    /// Entry point virtual address.
    pub entry_point: u64,
    /// Parsed sections.
    pub sections: Vec<ElfSection>,
    /// Whether the ELF is 64-bit.
    pub is_64_bit: bool,
    /// Architecture (e_machine).
    pub architecture: u16,
    /// Parsed symbols.
    pub symbols: Vec<ElfSymbol>,
    /// Interpreter path (dynamic linker), if any.
    pub interpreter: Option<String>,
    /// Dynamic libraries, if any.
    pub libraries: Vec<String>,
}

/// Parse a PE binary from raw bytes.
///
/// Uses `goblin::pe::PE` to parse headers, sections, and the entry point.
pub fn parse_pe(bytes: &[u8]) -> Result<PeBinary, LoaderError> {
    let pe = goblin::pe::PE::parse(bytes)?;

    let entry_point = pe.entry as u64;
    let image_base = pe.image_base;
    let is_64_bit = pe.is_64;

    let sections = pe
        .sections
        .iter()
        .map(|s| {
            let name = String::from_utf8_lossy(&s.name)
                .trim_end_matches('\0')
                .to_string();
            PeSection {
                name,
                virtual_address: s.virtual_address as u64,
                virtual_size: s.virtual_size as u64,
                raw_size: s.size_of_raw_data as u64,
                raw_offset: s.pointer_to_raw_data as u64,
                characteristics: s.characteristics,
            }
        })
        .collect();

    let mut symbols = Vec::new();
    for export in &pe.exports {
        symbols.push(PeSymbol {
            name: export.name.unwrap_or("").to_string(),
            address: export.rva as u64,
            size: export.size as u64,
            kind: "export".to_string(),
        });
    }
    for import in &pe.imports {
        symbols.push(PeSymbol {
            name: import.name.to_string(),
            address: import.rva as u64,
            size: import.size as u64,
            kind: "import".to_string(),
        });
    }

    Ok(PeBinary {
        entry_point,
        sections,
        image_base,
        is_64_bit,
        symbols,
    })
}

/// Parse an ELF binary from raw bytes.
///
/// Uses `goblin::elf::Elf` to parse headers, sections, symbols, and metadata.
pub fn parse_elf(bytes: &[u8]) -> Result<ElfBinary, LoaderError> {
    let elf = goblin::elf::Elf::parse(bytes)?;

    let entry_point = elf.entry;
    let is_64_bit = elf.is_64;
    let architecture = elf.header.e_machine;

    let sections = elf
        .section_headers
        .iter()
        .map(|sh| {
            let name = elf.shdr_strtab.get_at(sh.sh_name).unwrap_or("").to_string();
            ElfSection {
                name,
                address: sh.sh_addr,
                size: sh.sh_size,
                offset: sh.sh_offset,
                flags: sh.sh_flags,
            }
        })
        .collect();

    let symbols = elf
        .syms
        .iter()
        .map(|sym| {
            let name = elf.strtab.get_at(sym.st_name).unwrap_or("").to_string();
            let kind = match sym.st_type() {
                1 => "OBJECT",
                2 => "FUNC",
                3 => "SECTION",
                4 => "FILE",
                5 => "COMMON",
                6 => "TLS",
                _ => "UNKNOWN",
            }
            .to_string();
            ElfSymbol {
                name,
                address: sym.st_value,
                size: sym.st_size,
                kind,
            }
        })
        .collect();

    let interpreter = elf.interpreter.map(|s| s.to_string());
    let libraries = elf.libraries.iter().map(|&s| s.to_string()).collect();

    Ok(ElfBinary {
        entry_point,
        sections,
        is_64_bit,
        architecture,
        symbols,
        interpreter,
        libraries,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write_u16(bytes: &mut [u8], offset: usize, value: u16) {
        bytes[offset..offset + 2].copy_from_slice(&value.to_le_bytes());
    }

    fn write_u32(bytes: &mut [u8], offset: usize, value: u32) {
        bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
    }

    /// Build a minimal valid PE32 file in memory.
    fn minimal_pe_bytes() -> Vec<u8> {
        let mut b = vec![0u8; 0x400];

        // DOS Header (64 bytes)
        b[0x00] = 0x4D; // 'M'
        b[0x01] = 0x5A; // 'Z'
        write_u32(&mut b, 0x3C, 0x40); // e_lfanew = 0x40

        // PE Signature at 0x40
        b[0x40] = 0x50; // 'P'
        b[0x41] = 0x45; // 'E'
        b[0x42] = 0x00;
        b[0x43] = 0x00;

        // COFF Header (20 bytes) at 0x44
        write_u16(&mut b, 0x44, 0x14C); // Machine: i386
        write_u16(&mut b, 0x46, 0x0001); // NumberOfSections: 1
                                         // TimeDateStamp (0x48), PointerToSymbolTable (0x4C), NumberOfSymbols (0x50) = 0
        write_u16(&mut b, 0x54, 0x00E0); // SizeOfOptionalHeader: 224
        write_u16(&mut b, 0x56, 0x0102); // Characteristics: EXECUTABLE_IMAGE | 32BIT_MACHINE

        // Optional Header (PE32, 224 bytes) at 0x58
        write_u16(&mut b, 0x58, 0x010B); // Magic: PE32
        b[0x5A] = 0x01; // MajorLinkerVersion
                        // SizeOfCode: 0x200
        write_u32(&mut b, 0x5C, 0x200);
        // SizeOfInitializedData: 0x200
        write_u32(&mut b, 0x60, 0x200);
        // SizeOfUninitializedData: 0
        // AddressOfEntryPoint: 0x1000
        write_u32(&mut b, 0x68, 0x1000);
        // BaseOfCode: 0x1000
        write_u32(&mut b, 0x6C, 0x1000);
        // BaseOfData: 0x2000
        write_u32(&mut b, 0x70, 0x2000);
        // ImageBase: 0x10000
        write_u32(&mut b, 0x74, 0x10000);
        // SectionAlignment: 0x1000
        write_u32(&mut b, 0x78, 0x1000);
        // FileAlignment: 0x200
        write_u32(&mut b, 0x7C, 0x200);
        // MajorOperatingSystemVersion: 4
        write_u16(&mut b, 0x80, 0x4);
        // MajorSubsystemVersion: 4
        write_u16(&mut b, 0x88, 0x4);
        // SizeOfImage: 0x2000
        write_u32(&mut b, 0x90, 0x2000);
        // SizeOfHeaders: 0x200
        write_u32(&mut b, 0x94, 0x200);
        // CheckSum: 0
        // Subsystem: 1 (NATIVE)
        write_u16(&mut b, 0x9C, 0x1);
        // DllCharacteristics: 0
        // SizeOfStackReserve: 0x100000
        write_u32(&mut b, 0xA0, 0x100000);
        // SizeOfStackCommit: 0x1000
        write_u32(&mut b, 0xA4, 0x1000);
        // SizeOfHeapReserve: 0x100000
        write_u32(&mut b, 0xA8, 0x100000);
        // SizeOfHeapCommit: 0x1000
        write_u32(&mut b, 0xAC, 0x1000);
        // LoaderFlags: 0
        // NumberOfRvaAndSizes: 16
        write_u32(&mut b, 0xB4, 0x10);
        // Data directories: 16 * 8 = 128 bytes of zeros at 0xB8 (already zeroed)

        // Section Header (40 bytes) at 0x58 + 224 = 0x138
        // Name: ".text\0\0\0" (8 bytes)
        b[0x138] = 0x2E;
        b[0x139] = 0x74;
        b[0x13A] = 0x65;
        b[0x13B] = 0x78;
        b[0x13C] = 0x74;
        // VirtualSize: 0x200
        write_u32(&mut b, 0x140, 0x200);
        // VirtualAddress: 0x1000
        write_u32(&mut b, 0x144, 0x1000);
        // SizeOfRawData: 0x200
        write_u32(&mut b, 0x148, 0x200);
        // PointerToRawData: 0x200
        write_u32(&mut b, 0x14C, 0x200);
        // PointerToRelocations: 0
        // PointerToLinenumbers: 0
        // NumberOfRelocations: 0
        // NumberOfLinenumbers: 0
        // Characteristics: 0x60000020 (CODE | EXECUTE | READ)
        write_u32(&mut b, 0x15C, 0x60000020);

        b
    }

    #[test]
    fn parse_pe_minimal_fixture() {
        let bytes = minimal_pe_bytes();
        let pe = parse_pe(&bytes).expect("should parse minimal PE fixture");
        assert_eq!(pe.entry_point, 0x1000);
        assert_eq!(pe.image_base, 0x10000);
        assert!(!pe.is_64_bit);
        assert_eq!(pe.sections.len(), 1);
        assert_eq!(pe.sections[0].name, ".text");
        assert_eq!(pe.sections[0].virtual_address, 0x1000);
        assert_eq!(pe.sections[0].virtual_size, 0x200);
        assert_eq!(pe.sections[0].raw_size, 0x200);
        assert_eq!(pe.sections[0].raw_offset, 0x200);
        assert_eq!(pe.sections[0].characteristics, 0x60000020);
    }

    #[test]
    fn parse_pe_invalid_data() {
        let result = parse_pe(b"not a pe");
        assert!(result.is_err());
    }

    #[test]
    fn elf_loader_errors_for_missing_file() {
        let loader = ElfLoader;
        let result = loader.load("/nonexistent/path/that/does/not/exist.elf");
        assert!(
            result.is_err(),
            "loading a missing file must be an Err, got Ok"
        );
        let msg = result.unwrap_err();
        assert!(
            msg.contains("/nonexistent/path/that/does/not/exist.elf"),
            "error must include the path that failed: {msg}"
        );
    }

    #[test]
    fn pe_loader_errors_for_missing_file() {
        let loader = PeLoader;
        let result = loader.load("/nonexistent/path/that/does/not/exist.exe");
        assert!(
            result.is_err(),
            "loading a missing file must be an Err, got Ok"
        );
    }

    #[test]
    fn parse_pe_empty_bytes() {
        assert!(parse_pe(b"").is_err());
    }

    #[test]
    fn parse_elf_empty_bytes() {
        assert!(parse_elf(b"").is_err());
    }

    #[test]
    fn invalid_pe_data_is_loader_error() {
        let result =
            parse_pe(b"not a pe\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff");
        assert!(result.is_err());
        let err = result.unwrap_err();
        // Must surface as a LoaderError, not a panic
        assert!(matches!(
            err,
            LoaderError::Goblin(_) | LoaderError::InvalidPE(_)
        ));
    }

    #[test]
    fn invalid_elf_data_is_loader_error() {
        let result = parse_elf(b"not an elf\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff");
        assert!(result.is_err());
        let err = result.unwrap_err();
        assert!(matches!(
            err,
            LoaderError::Goblin(_) | LoaderError::InvalidPE(_)
        ));
    }

    #[test]
    fn elf_loader_round_trip() {
        // Build a minimal ELF file in /tmp and confirm we can read it back.
        let dir = std::env::temp_dir();
        let path = dir.join("pine_loader_roundtrip_test.elf");
        let payload: Vec<u8> = (0u8..=255).cycle().take(1024).collect();
        std::fs::write(&path, &payload).expect("write tmp ELF");

        let loader = ElfLoader;
        let read = loader.load(path.to_str().unwrap()).expect("load tmp ELF");
        assert_eq!(read, payload, "loader must return exact file contents");

        // PeLoader should behave identically for the read path.
        let read2 = PeLoader
            .load(path.to_str().unwrap())
            .expect("PeLoader load");
        assert_eq!(read2, payload);

        std::fs::remove_file(&path).ok();
    }
}

#[cfg(test)]
mod proptests {
    use crate::{parse_elf, parse_pe};
    use proptest::prelude::*;

    proptest! {
        /// parse_pe must never panic on any input (returns Err or Ok).
        #[test]
        fn parse_pe_never_panics(bytes in proptest::collection::vec(any::<u8>(), 0..1024)) {
            let _ = parse_pe(&bytes);
        }

        /// parse_elf must never panic on any input (returns Err or Ok).
        #[test]
        fn parse_elf_never_panics(bytes in proptest::collection::vec(any::<u8>(), 0..1024)) {
            let _ = parse_elf(&bytes);
        }
    }
}
