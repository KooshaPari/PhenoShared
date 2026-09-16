// SPDX-License-Identifier: MIT OR Apache-2.0
// Build script for nanovms-core
// Compiles Go source into a C static archive for Rust FFI linkage.

use std::env;
use std::path::PathBuf;
use std::process::Command;

fn main() {
    let out_dir = PathBuf::from(env::var("OUT_DIR").unwrap());
    let manifest_dir = PathBuf::from(env::var("CARGO_MANIFEST_DIR").unwrap());
    let go_src = manifest_dir.join("bindings/go-c-export/");

    // Check if Go toolchain is available
    let go_check = Command::new("go").arg("version").output();
    if go_check.is_err() {
        // Go not available — emit a warning and generate stub files
        println!("cargo:warning=Go toolchain not found; nanovms-core static lib will be stubbed");
        generate_stub_archive(&out_dir);
        return;
    }

    // Determine target arch
    let target = env::var("TARGET").unwrap_or_default();
    let go_arch = if target.contains("aarch64") || target.contains("arm64") {
        "arm64"
    } else if target.contains("x86_64") || target.contains("amd64") {
        "amd64"
    } else {
        "amd64"
    };

    let go_os = if target.contains("windows") {
        "windows"
    } else if target.contains("darwin") {
        "darwin"
    } else {
        "linux"
    };

    // Build the Go C archive
    let lib_name = format!("nvms_core_{}_{}", go_os, go_arch);
    let output = Command::new("go")
        .args([
            "build",
            "-buildmode=c-archive",
            &format!("-o={}/lib{}.a", out_dir.display(), lib_name),
            ".",
        ])
        .current_dir(&go_src)
        .output()
        .expect("Failed to execute go build");

    if !output.status.success() {
        let stderr = String::from_utf8_lossy(&output.stderr);
        println!("cargo:warning=Go build failed:\n{}", stderr);
        println!("cargo:warning=Falling back — nanovms-core static lib not available");
        return;
    }

    // Link the static library
    println!("cargo:rustc-link-search=native={}", out_dir.display());
    println!("cargo:rustc-link-lib=static={}", lib_name);
    println!("cargo:rerun-if-changed={}", go_src.display());
}

fn generate_stub_archive(out_dir: &PathBuf) {
    // Generate an empty stub .a file so linking doesn't fail
    let stub_path = out_dir.join("libnvms_core_stub.a");
    // On Windows we need a minimal .lib stub; on Unix a .a
    // For now, just create an empty file — this will fail linking
    // but prevents a hard build error before the Go toolchain is installed
    std::fs::write(&stub_path, b"")
        .unwrap_or_else(|_| panic!("Failed to write stub archive to {:?}", stub_path));
    println!("cargo:warning=Go static lib stubbed at {:?}", stub_path);
    println!("cargo:rustc-link-search=native={}", out_dir.display());
    println!("cargo:rustc-link-lib=static=nvms_core_stub");
}
