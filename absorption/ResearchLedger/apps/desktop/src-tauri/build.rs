fn main() {
    // Unit tests exercise the Rust core without producing a desktop bundle. Keep
    // production resource parity strict, but let that explicit test-only switch
    // remove bundle resources from Tauri's in-memory merge-patched config.
    println!("cargo:rerun-if-env-changed=RESEARCHLEDGER_SKIP_BUNDLE_RESOURCE_VALIDATION");
    if std::env::var("RESEARCHLEDGER_SKIP_BUNDLE_RESOURCE_VALIDATION")
        .ok()
        .as_deref()
        == Some("1")
    {
        if std::env::var_os("TAURI_CONFIG").is_some() {
            panic!(
                "RESEARCHLEDGER_SKIP_BUNDLE_RESOURCE_VALIDATION cannot be combined with TAURI_CONFIG"
            );
        }
        std::env::set_var("TAURI_CONFIG", r#"{"bundle":{"resources":null}}"#);
    }
    tauri_build::build()
}
