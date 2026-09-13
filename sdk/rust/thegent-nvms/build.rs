// SPDX-License-Identifier: MIT OR Apache-2.0
use std::env;
use std::path::PathBuf;

fn main() {
    let manifest_dir = env::var("CARGO_MANIFEST_DIR").unwrap();
    let out_dir = env::var("OUT_DIR").unwrap();

    // Allow the user to override the nanovms path via env var
    let nanovms_base = env::var("NANOVMS_BASE")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            // Default: walk up from thegent/crates/thegent-nvms to the workspace root,
            // then into nanovms
            PathBuf::from(&manifest_dir)
                .ancestors()
                .nth(3)
                .expect("Cannot find workspace root")
                .join("nanovms")
        });

    let cgo_dir = nanovms_base.join("build/cgo");

    // Check for the platform-specific archive first, then fall back to the generic one
    let target = env::var("TARGET").unwrap();
    let platform_archive = match target.as_str() {
        "aarch64-apple-darwin" => cgo_dir.join("darwin-arm64/libnvms_core.a"),
        "x86_64-apple-darwin" => cgo_dir.join("darwin-amd64/libnvms_core.a"),
        "x86_64-unknown-linux-gnu" => cgo_dir.join("linux-amd64/libnvms_core.a"),
        _ => cgo_dir.join("libnvms_core.a"),
    };

    let archive = if platform_archive.exists() {
        platform_archive
    } else {
        cgo_dir.join("libnvms_core.a")
    };

    if archive.exists() {
        println!("cargo:rustc-link-lib=static=nvms_core");
        println!("cargo:rustc-link-search=native={}", archive.parent().unwrap().display());
    } else {
        // Emit a warning; the crate will still compile for `cargo check` but
        // linking will fail until the user runs `make -C nanovms build-cgo`.
        println!("cargo:warning=NVMS CGo archive not found at {}. Run `make -C {} build-cgo` to build it.",
            archive.display(), nanovms_base.display());
    }

    // If a header exists, copy it to OUT_DIR so bindgen or cc can use it
    let header = cgo_dir.join("libnvms_core.h");
    if header.exists() {
        let dest = PathBuf::from(&out_dir).join("libnvms_core.h");
        std::fs::copy(&header, &dest).ok();
    }

    println!("cargo:rerun-if-changed={}", archive.display());
    println!("cargo:rerun-if-env-changed=NANOVMS_BASE");
}
