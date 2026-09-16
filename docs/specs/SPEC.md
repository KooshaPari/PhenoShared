# Pine Spec Oracle

Scope
: This document defines the **Pine** functional and non-functional requirements
based on the current exported public surface in `main` at the moment this branch
was created.

Public surface context
- `cargo metadata` currently resolves **no CLI binary crate** in the workspace.
  The repo exposes only library crates and their exported Rust APIs.
- Primary public entrypoints are crate-level modules under:
  - `pine-core`
  - `pine-compat`
  - `pine-loader`
  - `pine-nvms`
  - `pine-syscall`

Functional Requirements

FR-1 — Binary byte loading handles missing input paths as errors
Description: `read_bytes` and `read_bytes_into` must report missing/unreadable files through the documented error channel.
Acceptance: Given a path that does not exist, both `pine_loader::read_bytes` and `pine_loader::read_bytes_into` return errors, and the string-based one includes the attempted path.
Source surface:
- `crates/pine-loader/src/lib.rs`: `read_bytes`, `read_bytes_into`, `Loader` trait usage in `ElfLoader`, `PeLoader`.

FR-2 — ELF loader and PE loader return file bytes as raw payload
Description: `ElfLoader` and `PeLoader` must expose the same `Loader` contract by returning exact file contents as `Vec<u8>`.
Acceptance: For a sample binary on disk, `ElfLoader::load(path)` and `PeLoader::load(path)` both return byte vectors exactly equal to `std::fs::read(path)`.
Source surface:
- `crates/pine-loader/src/lib.rs`: `ElfLoader`, `PeLoader`.

FR-3 — PE parser emits a normalized `PeBinary` description
Description: `parse_pe` must parse entry metadata and expose section metadata with stable fields.
Acceptance: Parsing a synthetic PE fixture succeeds and returns expected `entry_point`, `image_base`, and one `.text` section with expected addressing metadata.
Source surface:
- `crates/pine-loader/src/lib.rs`: `parse_pe`, `PeBinary`, `PeSection`.

FR-4 — ELF parser emits a normalized `ElfBinary` description
Description: `parse_elf` must parse entry and section/symbol metadata into the exported structure.
Acceptance: Parsing valid ELF bytes yields populated `ElfBinary` with expected `entry_point`, `architecture`, sections, and symbols.
Source surface:
- `crates/pine-loader/src/lib.rs`: `parse_elf`, `ElfBinary`, `ElfSection`, `ElfSymbol`.

FR-5 — Asset registry enforces registration semantics and lookup contracts
Description: `AssetRegistry` implementations must support add/get/list/remove behavior and return typed errors.
Acceptance: `register` rejects duplicates with `AssetError::AlreadyRegistered`, `get` returns `AssetError::NotFound` for unknown ids, and `list` reflects inserted descriptors.
Source surface:
- `crates/pine-core/src/ports/assets.rs`: `AssetId`, `AssetDescriptor`, `AssetError`, `AssetRegistry`, `InMemoryAssetRegistry`, `RecordingAssetRegistry`.

FR-6 — Symbol resolution supports exact and module-scoped lookups
Description: `SymbolResolver` implementations must resolve by symbol name and by `(name, module)` with deterministic ambiguity behavior.
Acceptance: `resolve` returns `ResolveError::Ambiguous` when duplicate unqualified names exist; `resolve_in_module` resolves only matching module entries.
Source surface:
- `crates/pine-core/src/ports/resolve.rs`: `Symbol`, `ResolveError`, `SymbolResolver`, `InMemorySymbolResolver`, `MockSymbolResolver`.

FR-7 — Section reader supports random-access reads within loaded ranges
Description: `SectionReader` implementations must expose section metadata and fail on out-of-bounds reads with typed errors.
Acceptance: `read_bytes` succeeds only for fully-bounded virtual ranges and errors with `SectionError::OutOfBounds` otherwise, including implicit zero-fill for gaps beyond `raw_data`.
Source surface:
- `crates/pine-core/src/ports/section.rs`: `Section`, `SectionError`, `SectionReader`, `InMemorySectionReader`, `MockSectionReader`.

FR-8 — Process snapshots can be serialized and hydrated
Description: `JsonFileSerializationPort` must persist and reload `ProcessSnapshot` and validate destination/input invariants.
Acceptance: Saving to an empty destination path errors; loading empty content errors; valid JSON writes and round-trips into equivalent `ProcessSnapshot`.
Source surface:
- `crates/pine-core/src/ports/serialization.rs`: `ProcessSnapshot`, `SerializationError`, `SerializationPort`, `JsonFileSerializationPort`, `MockSerializationPort`.

FR-9 — Compatibility/runtime adapter types are instantiable without args
Description: `CompatibilityLayer` and `NvmsRuntime` should both provide zero-cost construction and `Default` behavior.
Acceptance: `CompatibilityLayer::new()`, `CompatibilityLayer::default()`, `NvmsRuntime::new()`, and `NvmsRuntime::default()` all succeed and return values.
Source surface:
- `crates/pine-compat/src/lib.rs`: `CompatibilityLayer`
- `crates/pine-nvms/src/lib.rs`: `NvmsRuntime`

FR-10 — Syscall translation maps known Linux numbers to structured names
Description: Base translator behavior must map syscall numbers to stable `SyscallName` values and reject unknown numbers.
Acceptance: `X86_64SyscallTranslator::new().translate(n, args)` returns expected `SyscallResult` for known numbers (`0`, `1`, `2`, `9`, `60`) and `SyscallError::UnknownSyscall` for unknown numbers.
Source surface:
- `crates/pine-syscall/src/lib.rs`: `SyscallName`, `SyscallResult`, `SyscallError`, `SyscallTranslator`, `X86_64SyscallTranslator`, `LinuxSyscallHandler`.

FR-11 — Platform-specific translator constants remain coherent with lookup tables
Description: Linux platform constants in `LinuxSyscallTranslator` must be valid aliases into the shared x86_64 table.
Acceptance: Calling `translate` with documented constants (for example `READ`, `WRITE`, `OPEN`, `MMAP`, `OPENAT`, `GETRANDOM`) returns the expected enum variants.
Source surface:
- `crates/pine-syscall/src/linux.rs`: `LinuxSyscallTranslator`.

FR-12 — Windows translator constants map to documented NT syscall numbers
Description: Windows translator constants and lookup APIs must be coherent with NT syscall names.
Acceptance: `WindowsNtSyscallTranslator` translates known constants (e.g. `NT_CREATE_FILE`, `NT_READ_FILE`, `NT_WRITE_FILE`, `NT_ALLOCATE_VIRTUAL_MEMORY`, `NT_WAIT_FOR_SINGLE_OBJECT`) to corresponding `WindowsSyscallName`.
Source surface:
- `crates/pine-syscall/src/windows.rs`: `WindowsNtSyscallTranslator`, `WindowsSyscallName`, `WindowsSyscallResult`.

FR-13 — Plugin registry composes plugins with optional base translator
Description: `PluginRegistry` must register plugins and route translation through index-first mapping when a base translator is present.
Acceptance: With a registered plugin that supports `SyscallName::Read`, translate on number `0` returns plugin output; unsupported names fall back to base translator.
Source surface:
- `crates/pine-syscall/src/plugin.rs`: `SyscallTranslatorPlugin`, `PluginManifest`, `PluginLoaderError`, `PluginRegistry`, `PluginLoader`.

FR-14 — Core identifiers remain typed and explicit in public model
Description: Core domain wrappers and traits must enforce strongly typed boundaries at the public layer.
Acceptance: Constructing `ProcessId`, `SyscallNumber`, `Symbol`, `Section`, `AssetDescriptor`, and `ProcessSnapshot` from their constructors/populated fields yields typed values and accessible fields without escaping through raw primitives.
Source surface:
- `crates/pine-core/src/types.rs`: `ProcessId`, `SyscallNumber`
- `crates/pine-core/src/ports/resolve.rs`: `Symbol`
- `crates/pine-core/src/ports/section.rs`: `Section`
- `crates/pine-core/src/ports/assets.rs`: `AssetDescriptor`, `AssetId`
- `crates/pine-core/src/ports/serialization.rs`: `ProcessSnapshot`

Non-Functional Requirements

NFR-1 — Deterministic ordering is preserved by in-memory readers/registries
Description: In-memory adapters must preserve deterministic behavior for list/readable order-dependent outputs.
Acceptance: Listing sections and symbols returns deterministic ordering in stable insertion tests (e.g., asset/section list order) and does not depend on hash map randomization.
Source surface:
- `crates/pine-core/src/ports/assets.rs`
- `crates/pine-core/src/ports/section.rs`
- `crates/pine-core/src/ports/resolve.rs`

NFR-2 — Error signaling is explicit and recoverable
Description: Public adapters and translators must surface failures via dedicated error types instead of panics.
Acceptance: Invalid operations return `AssetError`, `ResolveError`, `SectionError`, `SerializationError`, `SyscallError`, `WindowsSyscallError`, or `PluginLoaderError` as the current design indicates.
Source surface:
- `crates/pine-core/src/ports/assets.rs`
- `crates/pine-core/src/ports/resolve.rs`
- `crates/pine-core/src/ports/section.rs`
- `crates/pine-core/src/ports/serialization.rs`
- `crates/pine-syscall/src/lib.rs`
- `crates/pine-syscall/src/windows.rs`
- `crates/pine-syscall/src/plugin.rs`

NFR-3 — File-system boundaries are explicit and minimal
Description: Only filesystem-backed ports should perform direct filesystem I/O; mock/in-memory ports must avoid filesystem dependence.
Acceptance: `InMemory*` and `Mock*` adapters satisfy operations without writing disk files.
Source surface:
- `crates/pine-core/src/ports/assets.rs`
- `crates/pine-core/src/ports/resolve.rs`
- `crates/pine-core/src/ports/section.rs`
- `crates/pine-core/src/ports/serialization.rs`
- `crates/pine-syscall/src/plugin.rs`

NFR-4 — Windows/Linux platform surface remains additive
Description: Platform-specific translator modules must not remove shared base contracts.
Acceptance: Both Linux and Windows translator types continue to implement the shared contract (`translate` method shapes) without requiring changes to base consumer code using `SyscallTranslator`.
Source surface:
- `crates/pine-syscall/src/lib.rs`
- `crates/pine-syscall/src/linux.rs`
- `crates/pine-syscall/src/windows.rs`

NFR-5 — Public surface is library-only in this repo revision
Description: This release has no user-facing CLI commands or HTTP endpoints, so acceptance of API changes is scoped to crate symbols.
Acceptance: Validation checks in this spec confirm no `main` binary in `crates/*` and no exported endpoint handlers.
Source surface:
- `Cargo.toml`
- Workspace crate tree under `crates/*`

