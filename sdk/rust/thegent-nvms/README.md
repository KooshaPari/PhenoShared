# thegent-nvms

NVMS (NanoVM Service) FFI bindings with optional pyo3 support — migrated from
PhenoCompose `bindings/rust-ffi/` into the thegent workspace to unify polyglot
binding infrastructure.

## What lives here

| File | Purpose |
|------|---------|
| `src/lib.rs` | Low-level `sys` C ABI declarations + safe high-level wrappers (`Instance`, `GpuDevice`, `PerfStats`) |
| `src/lib.rs` (bottom) | pyo3 Python extension (`thegent_nvms` module) — gated behind `python` feature |
| `build.rs` | Links against the nanovms CGo archive (`libnvms_core.a`) |
| `pyproject.toml` | maturin packaging for Python wheels |

## Build

### Prerequisites

```bash
# Build the CGo archive in nanovms first
make -C /path/to/nanovms build-cgo
```

### Rust only

```bash
cargo check --manifest-path crates/thegent-nvms/Cargo.toml
```

### With Python extension

```bash
cargo build --manifest-path crates/thegent-nvms/Cargo.toml --features python
```

### Python wheel via maturin

```bash
cd crates/thegent-nvms
maturin develop --features python
python -c "import thegent_nvms; print(thegent_nvms.nvms_version_py())"
```

## Why this crate exists

- **thegent** already has 14+ pyo3-enabled Rust crates with a standardized pattern
  (`abi3-py312`, `extension-module`, `cdylib`/`rlib`).
- **thegent** already has a 4-tier sandbox ADR (bubblewrap / gVisor / Firecracker / Wasm)
  and a Mojo bridge.
- **nanovms** is the canonical Go runtime with a Rust SDK (`sdk/rust/`).

PhenoCompose's binding layer was a strict subset of thegent's polyglot
infrastructure. Consolidating into `thegent-nvms` eliminates duplication and
lets us reuse thegent's maturin/pyo3 build pipeline, CI, and release automation.

## Migration log

- 2026-06-14: Created from PhenoCompose `bindings/rust-ffi/` (597 LOC) +
  `pheno-compose-driver/` (167 LOC) + `bindings/go-c-export/` (319 LOC).
- Go C-export moved to `nanovms/cmd/nvms-cgo/main.go`.
- High-level driver merged into `nanovms/sdk/rust/src/driver.rs`.
- Rust FFI + pyo3 surface unified here.
