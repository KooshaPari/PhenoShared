// Build script for omniroute-core
// Generates version information at compile time

fn main() {
    // Print compile-time version info
    println!("cargo:rerun-if-changed=build.rs");
}
