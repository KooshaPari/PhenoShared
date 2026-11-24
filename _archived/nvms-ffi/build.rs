// SPDX-License-Identifier: MIT OR Apache-2.0
// Build script for nvms-ffi
//
// Orchestrates the link chain between Rust FFI bindings and the NVMS Go Core:
//
//   Mode A: Go static lib exists → link against libnvms_core.a,
//            set `cfg(nvms_core_lib)` so the Rust shim is disabled.
//   Mode B: Go static lib absent  → no external link; Rust shim module
//            provides stub `extern "C"` implementations (supports `cargo check`
//            and `cargo test` without a Go toolchain).
//
// Expected static lib location (built by `make nvms-c-archive`):
//   target/libnvms_core.a     (for linux/amd64 or darwin/amd64)
//   target/libnvms_core_arm64.a (for darwin/arm64)

use std::env;
use std::path::PathBuf;
use std::process::{Command, Stdio};

fn main() {
    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());

    // Declare the custom cfg so Rust 1.80+ doesn't emit `unexpected_cfgs` lint
    // when we set `cargo:rustc-cfg=nvms_core_lib` below.
    println!("cargo:rustc-check-cfg=cfg(nvms_core_lib)");

    // Possible locations for the Go static library
    let target_dir = manifest_dir
        .ancestors()
        .find(|p| p.join("Cargo.toml").exists())
        .map(|p| p.join("target"))
        .unwrap_or_else(|| manifest_dir.join("../target"));

    let lib_paths = [
        target_dir.join("libnvms_core.a"),
        target_dir.join("libnvms_core_linux_amd64.a"),
        target_dir.join("libnvms_core_darwin_amd64.a"),
        target_dir.join("libnvms_core_darwin_arm64.a"),
    ];

    // Try to find the Go toolchain (silenced: we don't want `go version`
    // printing to stderr on every cargo invocation when Go is absent)
    let go_available = Command::new("go")
        .arg("version")
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .output()
        .is_ok();

    // Check if any pre-built static lib exists
    let lib_exists = lib_paths.iter().any(|p| p.exists());

    if lib_exists {
        // Mode A: Link against the real Go static library
        for path in &lib_paths {
            if path.exists() {
                let dir = path.parent().unwrap();
                println!("cargo:rustc-link-search=native={}", dir.display());
                println!("cargo:rustc-link-lib=static=nvms_core");
                println!("cargo:rustc-cfg=nvms_core_lib");
                println!(
                    "cargo:warning=Linking against real NVMS Go core at {}",
                    path.display()
                );
                break;
            }
        }
    } else if go_available {
        // Mode B: Go toolchain available but no pre-built lib
        // Try to build it on-the-fly
        let go_src = manifest_dir.join("../../crates/nanovms-core/bindings/go-c-export");
        if go_src.exists() {
            let lib_name = format!("libnvms_core");
            let output_path = out_dir.join(format!("{}.a", lib_name));

            let status = Command::new("go")
                .args([
                    "build",
                    "-buildmode=c-archive",
                    "-o",
                    &output_path.to_string_lossy(),
                    ".",
                ])
                .current_dir(&go_src)
                .output();

            match status {
                Ok(output) if output.status.success() => {
                    println!("cargo:rustc-link-search=native={}", out_dir.display());
                    println!("cargo:rustc-link-lib=static=nvms_core");
                    println!("cargo:rustc-cfg=nvms_core_lib");
                    println!(
                        "cargo:warning=NVMS Go core built on-the-fly at {}",
                        output_path.display()
                    );
                }
                Ok(output) => {
                    let stderr = String::from_utf8_lossy(&output.stderr);
                    println!("cargo:warning=Go build failed: {}", stderr);
                    println!("cargo:warning=Falling back to Rust shim (stub) implementation");
                    // Mode C: Go available but build failed — use shim (no cfg needed)
                }
                Err(e) => {
                    println!("cargo:warning=Go build error: {}", e);
                    println!("cargo:warning=Falling back to Rust shim (stub) implementation");
                }
            }
        } else {
            println!("cargo:warning=Go source not found at {}", go_src.display());
            println!("cargo:warning=Falling back to Rust shim (stub) implementation");
        }
    } else {
        // Mode C: No Go toolchain and no pre-built lib
        // The Rust shim module provides stub implementations
        println!("cargo:warning=No Go toolchain found — using Rust shim (stub) for NVMS FFI");
        println!("cargo:warning=Install Go and run `make nvms-c-archive` for real NVMS linkage");
    }

    // Re-run build script if Go source changes
    let go_source_path =
        manifest_dir.join("../../crates/nanovms-core/bindings/go-c-export/nvms_core.go");
    if go_source_path.exists() {
        println!("cargo:rerun-if-changed={}", go_source_path.display());
    }

    // Re-run if our own source changes
    println!("cargo:rerun-if-changed=src/lib.rs");
}
