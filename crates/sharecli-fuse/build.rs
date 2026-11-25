//! Link macFUSE's MFMount framework when it is available.
//!
//! IMPORTANT: a build script is compiled for the HOST, so `cfg!(target_os)`
//! here would describe the machine doing the build, not the machine the
//! artifact is for. Cross-compiling from macOS to Linux therefore emitted
//! `cargo:rustc-link-lib=framework=MFMount` for a Linux target and failed with
//! "library kind `framework` is only supported on Apple targets".
//!
//! Cargo exposes the TARGET via the CARGO_CFG_TARGET_OS environment variable,
//! which is what must be consulted.

fn main() {
    println!("cargo:rerun-if-env-changed=CARGO_CFG_TARGET_OS");
    println!("cargo:rerun-if-changed=build.rs");

    // Target OS, not host OS.
    let target_os = std::env::var("CARGO_CFG_TARGET_OS").unwrap_or_default();
    if target_os != "macos" {
        return;
    }

    // fuser is built with `macos-no-mount` for CI (no macFUSE on runners).
    // Only emit the MFMount framework link when macFUSE is actually installed,
    // so the crate still links without it.
    let macfuse = std::path::Path::new("/Library/Filesystems/macfuse.fs/Contents/Frameworks");
    if macfuse.exists() {
        println!("cargo:rustc-link-search=framework={}", macfuse.display());
        println!("cargo:rustc-link-lib=framework=MFMount");
    } else {
        println!("cargo:warning=macFUSE not installed; building without MFMount (macos-no-mount)");
    }
}
