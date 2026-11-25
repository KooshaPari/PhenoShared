//! Example: build a `PluginManifest` and validate it.
//!
//! This is the smallest possible "hello world" of the SDK. It does
//! not implement a port trait — it just shows the contract a plugin
//! must satisfy *before* it can be loaded.
//!
//! Run this example with `cargo run --example manifest_demo`.

use pheno_plugin_core::{
    guardrails, manifest::PluginKind, manifest::PluginManifest, Capability,
};

/// Build a manifest, validate it, and print a one-line summary.
pub fn build_and_validate() -> Result<PluginManifest, String> {
    // 1. Build the manifest. `PluginManifest::new` already calls
    //    `validate()` on the constructed instance, but we'll call it
    //    again at the end as a defensive check.
    let manifest = PluginManifest::new("pheno-plugin-hello", "0.1.0", PluginKind::Generic)
        .map_err(|e| format!("constructor failed: {}", e))?
        .with_description("A minimal example manifest".to_string())
        .with_capabilities(vec![
            Capability::Read,
            Capability::FilesystemRead,
        ])
        .with_min_host_version("0.1.0".to_string())
        .with_depends_on(vec!["pheno-plugin-core".to_string()]);

    // 2. Re-validate defensively. Cheap, and catches drift if the
    //    manifest is mutated between construction and registration.
    manifest
        .validate()
        .map_err(|e| format!("validation failed: {}", e))?;

    // 3. Spot-check the guardrails independently — this is the same
    //    logic the manifest calls, but exercising it directly is a
    //    good smoke test.
    guardrails::validate_plugin_name(&manifest.name)
        .map_err(|e| format!("name guardrail: {}", e))?;
    guardrails::validate_semver(&manifest.version)
        .map_err(|e| format!("version guardrail: {}", e))?;

    Ok(manifest)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_manifest_demo_builds() {
        let m = build_and_validate().expect("manifest should build and validate");
        assert_eq!(m.name, "pheno-plugin-hello");
        assert_eq!(m.version, "0.1.0");
        assert_eq!(m.kind, PluginKind::Generic);
        assert_eq!(m.capability_count(), 2);
        assert!(m.has_capability(Capability::Read));
        assert!(m.has_capability(Capability::FilesystemRead));
        assert!(!m.has_capability(Capability::Network));
    }

    #[test]
    fn test_manifest_demo_serializes() {
        let m = build_and_validate().unwrap();
        let json = serde_json::to_string(&m).unwrap();
        // The serialized form must be valid JSON and round-trip cleanly.
        let parsed: PluginManifest = serde_json::from_str(&json).unwrap();
        assert_eq!(parsed.name, m.name);
        assert_eq!(parsed.version, m.version);
    }
}
