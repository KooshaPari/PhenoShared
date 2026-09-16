//! Canonical Phenotype Rust crate template.

/// Returns the template crate name.
pub fn crate_name() -> &'static str {
    "pheno-cargo-template"
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn crate_name_matches_package() {
        assert_eq!(crate_name(), "pheno-cargo-template");
    }
}
