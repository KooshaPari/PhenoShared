use pine_loader::{parse_elf, parse_pe};
use std::fs;
use std::path::PathBuf;

fn temp_dir() -> PathBuf {
    std::env::temp_dir()
}

fn write_u16(bytes: &mut [u8], offset: usize, value: u16) {
    bytes[offset..offset + 2].copy_from_slice(&value.to_le_bytes());
}

fn write_u32(bytes: &mut [u8], offset: usize, value: u32) {
    bytes[offset..offset + 4].copy_from_slice(&value.to_le_bytes());
}

fn write_u64(bytes: &mut [u8], offset: usize, value: u64) {
    bytes[offset..offset + 8].copy_from_slice(&value.to_le_bytes());
}

/// Build a minimal valid PE32 file with a single export symbol.
fn minimal_pe_with_exports_bytes() -> Vec<u8> {
    let mut b = vec![0u8; 0x600];

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
    write_u16(&mut b, 0x54, 0x00E0); // SizeOfOptionalHeader: 224
    write_u16(&mut b, 0x56, 0x0102); // Characteristics: EXECUTABLE_IMAGE | 32BIT_MACHINE

    // Optional Header (PE32, 224 bytes) at 0x58
    write_u16(&mut b, 0x58, 0x010B); // Magic: PE32
    write_u32(&mut b, 0x5C, 0x400); // SizeOfCode
    write_u32(&mut b, 0x60, 0x400); // SizeOfInitializedData
    write_u32(&mut b, 0x68, 0x1000); // AddressOfEntryPoint
    write_u32(&mut b, 0x6C, 0x1000); // BaseOfCode
    write_u32(&mut b, 0x70, 0x2000); // BaseOfData
    write_u32(&mut b, 0x74, 0x10000); // ImageBase
    write_u32(&mut b, 0x78, 0x1000); // SectionAlignment
    write_u32(&mut b, 0x7C, 0x200); // FileAlignment
    write_u16(&mut b, 0x80, 0x4); // MajorOperatingSystemVersion
    write_u16(&mut b, 0x88, 0x4); // MajorSubsystemVersion
    write_u32(&mut b, 0x90, 0x2000); // SizeOfImage
    write_u32(&mut b, 0x94, 0x200); // SizeOfHeaders
    write_u16(&mut b, 0x9C, 0x1); // Subsystem: NATIVE
    write_u32(&mut b, 0xA0, 0x100000); // SizeOfStackReserve
    write_u32(&mut b, 0xA4, 0x1000); // SizeOfStackCommit
    write_u32(&mut b, 0xA8, 0x100000); // SizeOfHeapReserve
    write_u32(&mut b, 0xAC, 0x1000); // SizeOfHeapCommit
    write_u32(&mut b, 0xB4, 0x10); // NumberOfRvaAndSizes

    // Data Directory 0: Export
    write_u32(&mut b, 0xB8, 0x1300); // Export RVA
    write_u32(&mut b, 0xBC, 0x100); // Export Size

    // Section Header (.text) at 0x138
    b[0x138] = 0x2E;
    b[0x139] = 0x74;
    b[0x13A] = 0x65;
    b[0x13B] = 0x78;
    b[0x13C] = 0x74;
    write_u32(&mut b, 0x140, 0x400); // VirtualSize
    write_u32(&mut b, 0x144, 0x1000); // VirtualAddress
    write_u32(&mut b, 0x148, 0x400); // SizeOfRawData
    write_u32(&mut b, 0x14C, 0x200); // PointerToRawData
    write_u32(&mut b, 0x15C, 0x60000020); // Characteristics: CODE | EXECUTE | READ

    // .text data at 0x200
    b[0x200] = 0xC3; // ret

    // Export data at 0x500 (RVA 0x1300 within .text section)
    // Export Directory Table (40 bytes)
    write_u32(&mut b, 0x500, 0); // export_flags
    write_u32(&mut b, 0x504, 0); // time_date_stamp
    write_u16(&mut b, 0x508, 0); // major_version
    write_u16(&mut b, 0x50A, 0); // minor_version
    write_u32(&mut b, 0x50C, 0x133C); // name_rva (DLL name)
    write_u32(&mut b, 0x510, 1); // ordinal_base
    write_u32(&mut b, 0x514, 1); // address_table_entries
    write_u32(&mut b, 0x518, 1); // number_of_name_pointers
    write_u32(&mut b, 0x51C, 0x1328); // export_address_table_rva
    write_u32(&mut b, 0x520, 0x132C); // name_pointer_rva
    write_u32(&mut b, 0x524, 0x1330); // ordinal_table_rva

    // Export Address Table (4 bytes) at 0x528
    write_u32(&mut b, 0x528, 0x1000); // RVA of exported function

    // Export Name Pointer Table (4 bytes) at 0x52C
    write_u32(&mut b, 0x52C, 0x1332); // RVA of "MyExport"

    // Export Ordinal Table (2 bytes) at 0x530
    write_u16(&mut b, 0x530, 0); // ordinal 0 -> ordinal_base + 0 = 1

    // Export name "MyExport\0" at 0x532
    b[0x532] = 0x4D;
    b[0x533] = 0x79;
    b[0x534] = 0x45;
    b[0x535] = 0x78;
    b[0x536] = 0x70;
    b[0x537] = 0x6F;
    b[0x538] = 0x72;
    b[0x539] = 0x74;
    b[0x53A] = 0x00;

    // DLL name "test.dll\0" at 0x53C
    b[0x53C] = 0x74;
    b[0x53D] = 0x65;
    b[0x53E] = 0x73;
    b[0x53F] = 0x74;
    b[0x540] = 0x2E;
    b[0x541] = 0x64;
    b[0x542] = 0x6C;
    b[0x543] = 0x6C;
    b[0x544] = 0x00;

    b
}

/// Build a minimal valid ELF64 file with a .text section and a symbol table.
fn minimal_elf64_bytes() -> Vec<u8> {
    let mut b = vec![0u8; 0x800];

    // ELF Header (64 bytes)
    b[0x00] = 0x7F;
    b[0x01] = b'E';
    b[0x02] = b'L';
    b[0x03] = b'F';
    b[0x04] = 2; // ELFCLASS64
    b[0x05] = 1; // ELFDATA2LSB
    b[0x06] = 1; // EV_CURRENT
                 // e_ident[7..16] = 0

    write_u16(&mut b, 0x10, 2); // e_type: ET_EXEC
    write_u16(&mut b, 0x12, 62); // e_machine: EM_X86_64
    write_u32(&mut b, 0x14, 1); // e_version: EV_CURRENT
    write_u64(&mut b, 0x18, 0x1000); // e_entry
    write_u64(&mut b, 0x20, 0x40); // e_phoff
    write_u64(&mut b, 0x28, 0x500); // e_shoff
    write_u32(&mut b, 0x30, 0); // e_flags
    write_u16(&mut b, 0x34, 64); // e_ehsize
    write_u16(&mut b, 0x36, 56); // e_phentsize
    write_u16(&mut b, 0x38, 1); // e_phnum
    write_u16(&mut b, 0x3A, 64); // e_shentsize
    write_u16(&mut b, 0x3C, 5); // e_shnum
    write_u16(&mut b, 0x3E, 4); // e_shstrndx

    // Program Header (56 bytes) at 0x40
    write_u32(&mut b, 0x40, 1); // p_type: PT_LOAD
    write_u32(&mut b, 0x44, 5); // p_flags: PF_R | PF_X
    write_u64(&mut b, 0x48, 0); // p_offset
    write_u64(&mut b, 0x50, 0x1000); // p_vaddr
    write_u64(&mut b, 0x58, 0x1000); // p_paddr
    write_u64(&mut b, 0x60, 0x200); // p_filesz
    write_u64(&mut b, 0x68, 0x200); // p_memsz
    write_u64(&mut b, 0x70, 0x1000); // p_align

    // .text data at 0x100
    b[0x100] = 0xCC; // int3
    b[0x101] = 0xC3; // ret

    // .shstrtab at 0x200
    let shstrtab = b"\0.text\0.symtab\0.strtab\0.shstrtab\0";
    b[0x200..0x200 + shstrtab.len()].copy_from_slice(shstrtab);

    // .strtab at 0x300
    let strtab = b"\0_start\0";
    b[0x300..0x300 + strtab.len()].copy_from_slice(strtab);

    // .symtab at 0x400 (2 symbols: NULL + _start)
    let symtab_start = 0x400;
    // Symbol 0: NULL
    write_u32(&mut b, symtab_start, 0); // st_name
    b[symtab_start + 4] = 0; // st_info
    b[symtab_start + 5] = 0; // st_other
    write_u16(&mut b, symtab_start + 6, 0); // st_shndx
    write_u64(&mut b, symtab_start + 8, 0); // st_value
    write_u64(&mut b, symtab_start + 16, 0); // st_size

    // Symbol 1: _start
    write_u32(&mut b, symtab_start + 24, 1); // st_name (index of "_start" in .strtab)
    b[symtab_start + 28] = 0x12; // st_info: STB_GLOBAL | STT_FUNC
    b[symtab_start + 29] = 0; // st_other
    write_u16(&mut b, symtab_start + 30, 1); // st_shndx: .text
    write_u64(&mut b, symtab_start + 32, 0x1000); // st_value
    write_u64(&mut b, symtab_start + 40, 0x10); // st_size

    // Section Headers at 0x500
    let sh_start = 0x500;

    // Section 0: NULL (all zeros)

    // Section 1: .text
    let sh1 = sh_start + 64;
    write_u32(&mut b, sh1, 1); // sh_name
    write_u32(&mut b, sh1 + 4, 1); // sh_type: SHT_PROGBITS
    write_u64(&mut b, sh1 + 8, 6); // sh_flags: SHF_ALLOC | SHF_EXECINSTR
    write_u64(&mut b, sh1 + 16, 0x1000); // sh_addr
    write_u64(&mut b, sh1 + 24, 0x100); // sh_offset
    write_u64(&mut b, sh1 + 32, 0x10); // sh_size
    write_u32(&mut b, sh1 + 40, 0); // sh_link
    write_u32(&mut b, sh1 + 44, 0); // sh_info
    write_u64(&mut b, sh1 + 48, 1); // sh_addralign
    write_u64(&mut b, sh1 + 56, 0); // sh_entsize

    // Section 2: .symtab
    let sh2 = sh_start + 128;
    write_u32(&mut b, sh2, 7); // sh_name
    write_u32(&mut b, sh2 + 4, 2); // sh_type: SHT_SYMTAB
    write_u64(&mut b, sh2 + 8, 0); // sh_flags
    write_u64(&mut b, sh2 + 16, 0); // sh_addr
    write_u64(&mut b, sh2 + 24, 0x400); // sh_offset
    write_u64(&mut b, sh2 + 32, 0x30); // sh_size: 2 symbols * 24 bytes
    write_u32(&mut b, sh2 + 40, 3); // sh_link: .strtab
    write_u32(&mut b, sh2 + 44, 1); // sh_info: last local + 1
    write_u64(&mut b, sh2 + 48, 8); // sh_addralign
    write_u64(&mut b, sh2 + 56, 24); // sh_entsize

    // Section 3: .strtab
    let sh3 = sh_start + 192;
    write_u32(&mut b, sh3, 15); // sh_name
    write_u32(&mut b, sh3 + 4, 3); // sh_type: SHT_STRTAB
    write_u64(&mut b, sh3 + 8, 0); // sh_flags
    write_u64(&mut b, sh3 + 16, 0); // sh_addr
    write_u64(&mut b, sh3 + 24, 0x300); // sh_offset
    write_u64(&mut b, sh3 + 32, 0x08); // sh_size
    write_u32(&mut b, sh3 + 40, 0); // sh_link
    write_u32(&mut b, sh3 + 44, 0); // sh_info
    write_u64(&mut b, sh3 + 48, 1); // sh_addralign
    write_u64(&mut b, sh3 + 56, 0); // sh_entsize

    // Section 4: .shstrtab
    let sh4 = sh_start + 256;
    write_u32(&mut b, sh4, 23); // sh_name
    write_u32(&mut b, sh4 + 4, 3); // sh_type: SHT_STRTAB
    write_u64(&mut b, sh4 + 8, 0); // sh_flags
    write_u64(&mut b, sh4 + 16, 0); // sh_addr
    write_u64(&mut b, sh4 + 24, 0x200); // sh_offset
    write_u64(&mut b, sh4 + 32, 0x21); // sh_size
    write_u32(&mut b, sh4 + 40, 0); // sh_link
    write_u32(&mut b, sh4 + 44, 0); // sh_info
    write_u64(&mut b, sh4 + 48, 1); // sh_addralign
    write_u64(&mut b, sh4 + 56, 0); // sh_entsize

    b
}

#[test]
fn test_parse_pe_real_file() {
    let bytes = minimal_pe_with_exports_bytes();
    let path = temp_dir().join("pine_test_minimal.exe");
    fs::write(&path, &bytes).unwrap();

    let data = fs::read(&path).unwrap();
    let pe = parse_pe(&data).expect("should parse minimal PE fixture");

    assert_eq!(pe.entry_point, 0x1000);
    assert_eq!(pe.image_base, 0x10000);
    assert!(!pe.is_64_bit);

    assert_eq!(pe.sections.len(), 1);
    let text = &pe.sections[0];
    assert_eq!(text.name, ".text");
    assert_eq!(text.virtual_address, 0x1000);
    assert_eq!(text.virtual_size, 0x400);
    assert_eq!(text.raw_size, 0x400);
    assert_eq!(text.raw_offset, 0x200);

    assert_eq!(pe.symbols.len(), 1);
    let sym = &pe.symbols[0];
    assert_eq!(sym.name, "MyExport");
    assert_eq!(sym.kind, "export");
    assert_eq!(sym.address, 0x1000);
}

#[test]
fn test_parse_elf_real_file() {
    let bytes = minimal_elf64_bytes();
    let path = temp_dir().join("pine_test_minimal.elf");
    fs::write(&path, &bytes).unwrap();

    let data = fs::read(&path).unwrap();
    let elf = parse_elf(&data).expect("should parse minimal ELF fixture");

    assert_eq!(elf.entry_point, 0x1000);
    assert!(elf.is_64_bit);
    assert_eq!(elf.architecture, 62); // EM_X86_64

    // Check sections (including NULL at index 0)
    assert_eq!(elf.sections.len(), 5);
    let text = &elf.sections[1];
    assert_eq!(text.name, ".text");
    assert_eq!(text.address, 0x1000);
    assert_eq!(text.size, 0x10);

    let symtab = &elf.sections[2];
    assert_eq!(symtab.name, ".symtab");
    assert_eq!(symtab.offset, 0x400);

    let shstrtab = &elf.sections[4];
    assert_eq!(shstrtab.name, ".shstrtab");

    // Check symbols (NULL + _start)
    assert_eq!(elf.symbols.len(), 2);
    let start_sym = elf
        .symbols
        .iter()
        .find(|s| s.name == "_start")
        .expect("_start symbol should exist");
    assert_eq!(start_sym.kind, "FUNC");
    assert_eq!(start_sym.address, 0x1000);
    assert_eq!(start_sym.size, 0x10);

    let null_sym = elf
        .symbols
        .iter()
        .find(|s| s.name.is_empty())
        .expect("NULL symbol should exist");
    assert_eq!(null_sym.kind, "UNKNOWN");
    assert_eq!(null_sym.address, 0);
}

#[test]
fn test_parse_pe_invalid_data() {
    let result = parse_pe(b"not a pe");
    assert!(result.is_err());
}

#[test]
fn test_parse_elf_invalid_data() {
    let result = parse_elf(b"not an elf");
    assert!(result.is_err());
}
