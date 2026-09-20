//! `trace-scan` binary — walk a source tree and print trace annotations as JSON.
//!
//! Usage: `trace-scan --src <dir>`

use std::path::PathBuf;
use std::process;

use traceability_decorators::{patterns::Patterns, scan_dir};

fn main() {
    let mut src = PathBuf::from("src");
    let mut args = std::env::args().skip(1);
    while let Some(flag) = args.next() {
        if flag == "--src" {
            if let Some(val) = args.next() {
                src = PathBuf::from(val);
            }
        }
    }

    let patterns = Patterns::new();
    match scan_dir(&src, &patterns) {
        Ok(links) => {
            println!("{}", serde_json::to_string_pretty(&links).expect("json"));
        }
        Err(e) => {
            eprintln!("trace-scan error: {e}");
            process::exit(2);
        }
    }
}
