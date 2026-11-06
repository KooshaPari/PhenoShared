# ADR-001: Loader Port Architecture (ELF + PE)

| Field | Value |
|-------|-------|
| Status | Accepted (2026-06-11) |
| Deciders | Forge (parent agent) + user (resume review) |
| Date | 2026-06-11 |
| Supersedes | none |
| Related | V12 E.1.1, V12 E.1.2, Pine #17 |

## Context

Pine's `pine-loader` crate owns the binary-parsing adapter for ELF and PE
binaries. The `pine-core` crate defines the [`Loader`] port:

```rust
// pine-core/src/traits.rs
pub trait Loader {
    fn load(&self, path: &str) -> Result<Vec<u8>, String>;
}
```

Before this ADR, only one adapter — `ElfLoader` — implemented `Loader`,
and its `load` method was a stub that returned `Ok(vec![])` for any path.
Two tests (`elf_loader_implements_loader`,
`elf_loader_loads_empty_for_missing_file`) asserted this broken behavior,
hiding the bug from CI.

PE parsing existed as a free function `parse_pe(bytes: &[u8]) -> Result<PeBinary, LoaderError>`,
but did not implement the `Loader` port — meaning `ElfLoader` and PE
parsing were on two different code paths with no shared read interface.

## Decision

We adopt a **two-adapter** model for binary loading, with the following
properties:

1. **Two distinct adapter types, one shared port.** `ElfLoader` and
   `PeLoader` both implement [`pine_core::traits::Loader`]. They are
   zero-sized types — instantiation is free.

2. **Single source of truth for the file-read operation.** Both adapters
   delegate to `read_bytes(path: &str) -> Result<Vec<u8>, String>`,
   which is a thin wrapper around `std::fs::read`. There is no
   per-adapter file I/O code.

3. **No mocking of filesystem I/O at the adapter layer.** Tests
   exercising the I/O path write a real file to a temp directory
   (`elf_loader_round_trip`) and read it back, rather than mocking
   `fs::read`. This catches permission errors and OS-specific
   behaviors that mocks hide.

4. **Format-specific parsing stays as free functions.** `parse_pe(bytes)`
   and `parse_elf(bytes)` remain free functions that operate on
   already-loaded bytes. They do not implement `Loader` — the
   "loading" and "parsing" responsibilities are deliberately split
   to mirror the hexagonal **port → adapter → use-case** pattern:
   - `Loader.load(path)` = port (bytes in hand)
   - `parse_elf(bytes)` / `parse_pe(bytes)` = use-case (structured
     data out of bytes)

5. **Errors surface as `String` from `Loader::load`** (matching the
   existing trait signature) and as the typed [`LoaderError`] from the
   parse functions. We do not change the `Loader` trait signature in
   this ADR; the typed error is only used in the parse layer.

## Consequences

### Positive

- **`PeLoader` is a first-class port adapter**, not a free function. Any
  future caller that wants "give me PE bytes from a path" uses
  `PeLoader.load(p)` and the trait polymorphism.
- **The P1 bug in `ElfLoader::load`** (returning `Ok(vec![])` for any
  path) is fixed, with three new tests asserting the correct behavior:
  - `elf_loader_errors_for_missing_file`
  - `pe_loader_errors_for_missing_file`
  - `elf_loader_round_trip`
- **No code duplication** between the two loaders. The shared
  `read_bytes` helper is 5 lines; both adapters are 5 lines.
- **Future Mach-O adapter** (`MachOLoader`) drops in as 5 more lines
  if/when needed.

### Negative

- **The [`Loader`] port's error type is `String`**, not a typed error.
  This is a pre-existing trait design choice, not changed by this ADR.
  When the time comes to add a typed `LoaderError` to the port itself,
  it should be coordinated with `pine-core` (not a `pine-loader` change).
- **Two test files** (`src/lib.rs` unit tests +
  `tests/binary_loader_integration_tests.rs` integration tests)
  exercise the same path. This is intentional (integration tests
  catch issues that unit tests miss, and vice versa), but it does
  mean the test count is larger than the surface area of the code.

## Alternatives Considered

### A. One generic `BinaryLoader<Format>` adapter

```rust
pub struct BinaryLoader<F: BinaryFormat> { _phantom: PhantomData<F> }
impl<F: BinaryFormat> Loader for BinaryLoader<F> { ... }
```

**Rejected because** the two adapters do not actually share any
format-specific code at the `Loader` level — they both just call
`read_bytes`. The generic abstraction would be empty.

### B. Drop `Loader` and make `parse_*` take a path

```rust
pub fn parse_pe_path(path: &str) -> Result<PeBinary, LoaderError>;
```

**Rejected because** it conflates I/O and parsing, removes the
ability to test parsing on a byte slice, and breaks the
`pine_core::traits::Loader` polymorphism that the rest of the
workspace (e.g. `pine-syscall`) relies on.

### C. Use the `object` crate instead of `goblin`

The `object` crate is a more modern ELF/PE/Mach-O parser. We
**defer** the `goblin` → `object` migration to a future ADR
(F.1.1 from the V12 plan). Migrating now would be a larger PR and
is out of scope for the bug fix.

## Implementation

Implemented in Pine PR #17: https://github.com/KooshaPari/Pine/pull/17

- `crates/pine-loader/src/lib.rs` 432 → 500 LOC (+68, -20)
- 1 file changed, 5 unit tests (was 4), 3 doc tests (was 2), 4
  integration tests (unchanged), clippy 0 warnings
