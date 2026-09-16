//! Quickstart example for pheno-cargo-template.
//!
//! Run with:
//!   cargo run --example template_usage

use pheno_cargo_template::crate_name;

fn main() {
    println!("Template crate name: {}", crate_name());
    println!("This binary was generated from the pheno-cargo-template template.");
    println!();
    println!("To generate your own crate from this template:");
    println!("  cargo install cargo-generate");
    println!("  cargo generate --git https://github.com/KooshaPari/pheno-cargo-template");
}
