// build.rs — cc crate bridge that compiles cpp/kernel_engine.mm
// into a shared library on macOS so the `pheno-qwen-kernels` cdylib can
// statically re-export the Objective-C++ C ABI symbols and Python's ctypes
// can resolve them after `dlopen`.
//
// On non-macOS targets this script is a no-op: the cc crate is still
// declared (so Cargo doesn't complain about a missing dependency) but we
// never invoke it.  The Rust crate itself remains macOS-only at link time.

use std::env;
use std::path::PathBuf;

fn main() {
    let target_os = env::var("CARGO_CFG_TARGET_OS")
        .unwrap_or_else(|_| String::from("unknown"));

    // Locate `../cpp/kernel_engine.mm` relative to the rust crate root.
    let crate_dir = env::var("CARGO_MANIFEST_DIR")
        .expect("CARGO_MANIFEST_DIR is set by cargo for build scripts");
    let cpp_src: PathBuf = [
        crate_dir.as_str(),
        "..",
        "cpp",
        "kernel_engine.mm",
    ]
    .iter()
    .collect();

    // Rerun if the Objective-C++ source or any of the C headers it consumes
    // change.  The script itself is implicitly watched by cargo.
    println!("cargo:rerun-if-changed={}", cpp_src.display());
    println!("cargo:rerun-if-changed={}/include/kernel_engine.h",
        PathBuf::from(&crate_dir).join("..").display());
    println!("cargo:rerun-if-changed={}/include/qwen3_5.h",
        PathBuf::from(&crate_dir).join("..").display());

    // macOS-only: compile the .mm into libpheno_qwen.dylib via cc crate so
    // the same symbols that build_dylib.sh exposes end up inside the Rust
    // cdylib too.
    if target_os == "macos" {
        if !cpp_src.exists() {
            // Hard fail with a descriptive message; cargo will surface it
            // in the build log.
            panic!(
                "build.rs: kernel_engine.mm not found at {} \
                 — was build_dylib.sh set up?",
                cpp_src.display()
            );
        }

        let mut build = cc::Build::new();
        build
            .file(&cpp_src)
            .flag("-std=c++17")
            .flag("-stdlib=libc++")
            .flag("-fobjc-arc")
            .flag("-O3")
            .flag("-fPIC")
            .flag("-dynamiclib")
            .shared_flag(true);

        // Match the include/ layout from scripts/build_dylib.sh so the
        // #include paths in kernel_engine.mm resolve identically.
        build.include(PathBuf::from(&crate_dir).join("../include"));

        build.compile("pheno_qwen");

        // Explicit link hint (cc crate normally emits this for shared_flag,
        // but emitting it ourselves keeps the contract documented in the
        // build script's interface).
        println!("cargo:rustc-link-lib=dylib=pheno_qwen");
        println!("cargo:rustc-link-lib=c++");
        println!("cargo:rustc-link-lib=framework=Metal");
        println!("cargo:rustc-link-lib=framework=Foundation");
    } else {
        // Non-macOS: the Rust crate will still build (lib.rs has no
        // direct Metal deps), but it won't be able to dlopen the engine
        // against a real .metallib.  Emit a one-line hint so the failure
        // mode is discoverable from cargo's output.
        println!(
            "cargo:warning=build.rs: target_os={} — skipping pheno_qwen dylib build; \
             the cdylib will not expose C ABI symbols on this platform",
            target_os
        );
    }
}
