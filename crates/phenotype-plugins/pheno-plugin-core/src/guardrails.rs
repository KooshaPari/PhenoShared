//! Runtime guard-rails — validation helpers used by the host to keep
//! plugin manifests and inputs well-formed.
//!
//! These checks are intentionally cheap, side-effect free, and callable
//! from anywhere in the host. They are the safety net behind every
//! [`PluginManifest`](crate::manifest::PluginManifest) registration and
//! every per-call input.

use crate::error::{PluginError, PluginResult};

/// Maximum allowed length of a plugin name. 64 is enough for even
/// org-prefixed names like `acme-git-mirror` and well below any sane
/// registry limit.
pub const MAX_PLUGIN_NAME_LEN: usize = 64;

/// Maximum allowed length of a semver string. Real-world semvers rarely
/// exceed 16 bytes (`255.255.255-pre+build`); we use 32 to allow for
/// unusual pre-release identifiers without inviting abuse.
pub const MAX_SEMVER_LEN: usize = 32;

/// Maximum number of dependencies a plugin may declare. Keeps the
/// dependency graph shallow and reviewable.
pub const MAX_DEPENDENCIES: usize = 16;

/// Maximum number of capabilities a plugin may declare. A plugin
/// exercising more than 16 distinct capabilities is almost always
/// doing too much.
pub const MAX_CAPABILITIES: usize = 16;

/// Validate a plugin name.
///
/// Rules:
/// - ASCII only.
/// - 1..=`MAX_PLUGIN_NAME_LEN` characters.
/// - Lowercase letters, digits, `-`, `_`, or `.` (so `org.foo-plugin_2`
///   is allowed but `Org/Plugin` and `name with space` are not).
/// - Must start with a lowercase letter (rules out `.hidden`, `-dash`,
///   `_under`).
/// - Must not be one of the reserved names in
///   [`RESERVED_PLUGIN_NAMES`].
pub fn validate_plugin_name(name: &str) -> PluginResult<()> {
    if name.is_empty() {
        return Err(PluginError::Validation(
            "plugin name must not be empty".to_string(),
        ));
    }
    if name.len() > MAX_PLUGIN_NAME_LEN {
        return Err(PluginError::Validation(format!(
            "plugin name too long: {} bytes (max {})",
            name.len(),
            MAX_PLUGIN_NAME_LEN
        )));
    }

    let mut chars = name.chars();
    let first = chars
        .next()
        .expect("non-empty: checked above")
        .to_ascii_lowercase();
    if !first.is_ascii_lowercase() {
        return Err(PluginError::Validation(format!(
            "plugin name '{}' must start with a lowercase ASCII letter",
            name
        )));
    }

    for c in name.chars() {
        let ok = c.is_ascii_lowercase()
            || c.is_ascii_digit()
            || c == '-'
            || c == '_'
            || c == '.';
        if !ok {
            return Err(PluginError::Validation(format!(
                "plugin name '{}' contains illegal character {:?}; \
                 allowed: [a-z 0-9 - _ .]",
                name, c
            )));
        }
    }

    if RESERVED_PLUGIN_NAMES.contains(&name) {
        return Err(PluginError::Validation(format!(
            "plugin name '{}' is reserved",
            name
        )));
    }

    Ok(())
}

/// Validate a semantic version string (`X.Y.Z` with optional pre-release
/// and build metadata).
///
/// We deliberately do **not** require pre-release or build metadata; the
/// minimum is three non-negative integers separated by dots.
pub fn validate_semver(version: &str) -> PluginResult<()> {
    if version.is_empty() {
        return Err(PluginError::Validation(
            "version must not be empty".to_string(),
        ));
    }
    if version.len() > MAX_SEMVER_LEN {
        return Err(PluginError::Validation(format!(
            "version too long: {} bytes (max {})",
            version.len(),
            MAX_SEMVER_LEN
        )));
    }

    // Strip the optional pre-release / build metadata before parsing the
    // numeric core. Anything after the first `-` is the pre-release, and
    // anything after the first `+` is the build metadata — both are
    // optional.
    let core = version
        .split_once('-')
        .map(|(c, _)| c)
        .unwrap_or(version);
    let core = core.split_once('+').map(|(c, _)| c).unwrap_or(core);

    let parts: Vec<&str> = core.split('.').collect();
    if parts.len() != 3 {
        return Err(PluginError::Validation(format!(
            "version '{}' must be X.Y.Z (got {} parts)",
            version,
            parts.len()
        )));
    }
    for p in &parts {
        if p.is_empty() {
            return Err(PluginError::Validation(format!(
                "version '{}' has an empty component",
                version
            )));
        }
        if !p.chars().all(|c| c.is_ascii_digit()) {
            return Err(PluginError::Validation(format!(
                "version '{}' has non-numeric component '{}'",
                version, p
            )));
        }
        // Leading zero is illegal in semver (e.g. "01.0.0").
        if p.len() > 1 && p.starts_with('0') {
            return Err(PluginError::Validation(format!(
                "version '{}' component '{}' has a leading zero",
                version, p
            )));
        }
        // Bounds-check: u32::MAX is plenty.
        if p.parse::<u32>().is_err() {
            return Err(PluginError::Validation(format!(
                "version '{}' component '{}' overflows u32",
                version, p
            )));
        }
    }
    Ok(())
}

/// Validate the size of a dependency list. Catches the obvious "I
/// listed every plugin in the registry" mistake.
pub fn validate_dependencies(deps: &[String]) -> PluginResult<()> {
    if deps.len() > MAX_DEPENDENCIES {
        return Err(PluginError::Validation(format!(
            "too many dependencies: {} (max {})",
            deps.len(),
            MAX_DEPENDENCIES
        )));
    }
    Ok(())
}

/// Validate the size of a capability list.
pub fn validate_capabilities(caps: &[crate::capabilities::Capability]) -> PluginResult<()> {
    if caps.len() > MAX_CAPABILITIES {
        return Err(PluginError::Validation(format!(
            "too many capabilities: {} (max {})",
            caps.len(),
            MAX_CAPABILITIES
        )));
    }
    Ok(())
}

/// Reserved plugin names that may not be used by any plugin. The list
/// is intentionally short — the goal is to prevent shadowing
/// well-known host concepts, not to police naming.
pub const RESERVED_PLUGIN_NAMES: &[&str] = &[
    "core", "host", "system", "internal", "registry", "all", "any", "*",
    "default", "null", "none", "self", "this",
];

#[cfg(test)]
mod tests {
    use super::*;

    // -- validate_plugin_name --

    #[test]
    fn test_plugin_name_simple_ok() {
        assert!(validate_plugin_name("git").is_ok());
        assert!(validate_plugin_name("sqlite").is_ok());
        assert!(validate_plugin_name("pheno-plugin-git").is_ok());
    }

    #[test]
    fn test_plugin_name_underscore_and_dots_ok() {
        assert!(validate_plugin_name("org.foo-plugin_2").is_ok());
        assert!(validate_plugin_name("a_b.c-d.e").is_ok());
    }

    #[test]
    fn test_plugin_name_empty_rejected() {
        assert!(validate_plugin_name("").is_err());
    }

    #[test]
    fn test_plugin_name_with_space_rejected() {
        assert!(validate_plugin_name("has space").is_err());
    }

    #[test]
    fn test_plugin_name_with_uppercase_rejected() {
        assert!(validate_plugin_name("Git").is_err());
        assert!(validate_plugin_name("MixedCase").is_err());
    }

    #[test]
    fn test_plugin_name_must_start_with_letter() {
        assert!(validate_plugin_name("1leading").is_err());
        assert!(validate_plugin_name("-dash").is_err());
        assert!(validate_plugin_name("_under").is_err());
        assert!(validate_plugin_name(".hidden").is_err());
    }

    #[test]
    fn test_plugin_name_with_slash_rejected() {
        assert!(validate_plugin_name("org/git").is_err());
    }

    #[test]
    fn test_plugin_name_max_length_accepted() {
        // 64 chars, all lowercase.
        let name = "a".repeat(64);
        assert!(validate_plugin_name(&name).is_ok());
    }

    #[test]
    fn test_plugin_name_over_max_length_rejected() {
        let name = "a".repeat(65);
        assert!(validate_plugin_name(&name).is_err());
    }

    #[test]
    fn test_plugin_name_reserved_rejected() {
        for r in RESERVED_PLUGIN_NAMES {
            assert!(
                validate_plugin_name(r).is_err(),
                "expected reserved name '{}' to be rejected",
                r
            );
        }
    }

    // -- validate_semver --

    #[test]
    fn test_semver_simple_ok() {
        assert!(validate_semver("0.0.0").is_ok());
        assert!(validate_semver("0.1.0").is_ok());
        assert!(validate_semver("1.0.0").is_ok());
        assert!(validate_semver("255.255.255").is_ok());
    }

    #[test]
    fn test_semver_with_pre_release_and_build_ok() {
        assert!(validate_semver("1.0.0-alpha").is_ok());
        assert!(validate_semver("1.0.0-rc.1").is_ok());
        assert!(validate_semver("1.0.0+build.1").is_ok());
        assert!(validate_semver("1.0.0-rc.1+build.42").is_ok());
    }

    #[test]
    fn test_semver_empty_rejected() {
        assert!(validate_semver("").is_err());
    }

    #[test]
    fn test_semver_too_short_rejected() {
        assert!(validate_semver("1.0").is_err());
        assert!(validate_semver("1").is_err());
    }

    #[test]
    fn test_semver_too_long_rejected() {
        // A version string longer than MAX_SEMVER_LEN is rejected.
        let s: String = std::iter::repeat('1').take(MAX_SEMVER_LEN + 1).collect();
        assert!(validate_semver(&s).is_err());
    }

    #[test]
    fn test_semver_with_letters_in_core_rejected() {
        assert!(validate_semver("1.0.x").is_err());
        assert!(validate_semver("a.b.c").is_err());
    }

    #[test]
    fn test_semver_with_leading_zero_rejected() {
        assert!(validate_semver("01.0.0").is_err());
        assert!(validate_semver("0.01.0").is_err());
        assert!(validate_semver("0.0.01").is_err());
    }

    #[test]
    fn test_semver_with_four_parts_rejected() {
        // Strict X.Y.Z, not X.Y.Z.W.
        assert!(validate_semver("1.0.0.0").is_err());
    }

    #[test]
    fn test_semver_overflow_rejected() {
        // 2^32 overflows u32.
        let s = format!("{}.0.0", u64::from(u32::MAX) + 1);
        assert!(validate_semver(&s).is_err());
    }

    #[test]
    fn test_semver_empty_component_rejected() {
        assert!(validate_semver("1..0").is_err());
        assert!(validate_semver(".1.0").is_err());
        assert!(validate_semver("1.0.").is_err());
    }

    // -- validate_dependencies / validate_capabilities --

    #[test]
    fn test_dependencies_under_limit_ok() {
        let deps: Vec<String> = (0..MAX_DEPENDENCIES)
            .map(|i| format!("dep-{}", i))
            .collect();
        assert!(validate_dependencies(&deps).is_ok());
    }

    #[test]
    fn test_dependencies_over_limit_rejected() {
        let deps: Vec<String> = (0..MAX_DEPENDENCIES + 1)
            .map(|i| format!("dep-{}", i))
            .collect();
        assert!(validate_dependencies(&deps).is_err());
    }

    #[test]
    fn test_capabilities_under_limit_ok() {
        // 5 distinct capabilities is well under the limit.
        let caps = vec![
            crate::capabilities::Capability::Read,
            crate::capabilities::Capability::FilesystemRead,
            crate::capabilities::Capability::Network,
            crate::capabilities::Capability::Storage,
            crate::capabilities::Capability::Audit,
        ];
        assert!(validate_capabilities(&caps).is_ok());

        // 15 duplicates are also fine: the guardrail checks count, not
        // uniqueness — uniqueness is enforced by the manifest validator.
        let dupes: Vec<_> = (0..15)
            .map(|_| crate::capabilities::Capability::Read)
            .collect();
        assert!(validate_capabilities(&dupes).is_ok());
    }

    #[test]
    fn test_capabilities_over_limit_rejected() {
        let caps: Vec<_> = (0..MAX_CAPABILITIES + 1)
            .map(|_| crate::capabilities::Capability::Read)
            .collect();
        assert!(validate_capabilities(&caps).is_err());
    }

    #[test]
    fn test_empty_caps_and_deps_ok() {
        let caps: Vec<crate::capabilities::Capability> = vec![];
        let deps: Vec<String> = vec![];
        assert!(validate_capabilities(&caps).is_ok());
        assert!(validate_dependencies(&deps).is_ok());
    }

    // -- constants --

    #[test]
    fn test_constants_are_sane() {
        assert!(MAX_PLUGIN_NAME_LEN > 0);
        assert!(MAX_SEMVER_LEN > 0);
        assert!(MAX_DEPENDENCIES > 0);
        assert!(MAX_CAPABILITIES > 0);
    }
}
