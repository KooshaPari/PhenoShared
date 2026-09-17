use anyhow::{bail, Result};

pub const STACK_POLICY_URL: &str =
    "https://github.com/KooshaPari/phenotype-registry/blob/main/docs/rationalization/STACK_POLICY.md";

const CORE_LANGS: &[&str] = &["rust", "zig", "mojo"];
const EDGE_LANGS: &[&str] = &[
    "go",
    "python",
    "py",
    "typescript",
    "ts",
    "kotlin",
    "swift",
    "csharp",
    "java",
];

pub fn normalize_lang(lang: &str) -> String {
    match lang.to_lowercase().as_str() {
        "py" => "python".into(),
        "ts" => "typescript".into(),
        other => other.to_string(),
    }
}

pub fn is_core_lang(lang: &str) -> bool {
    CORE_LANGS.contains(&normalize_lang(lang).as_str())
}

pub fn is_edge_lang(lang: &str) -> bool {
    EDGE_LANGS.contains(&normalize_lang(lang).as_str())
}

pub fn validate_lang_gate(lang: &str, justify: Option<&str>) -> Result<()> {
    let norm = normalize_lang(lang);
    if is_core_lang(&norm) {
        return Ok(());
    }
    if is_edge_lang(&norm) {
        let text = justify.unwrap_or("").trim();
        if text.is_empty() {
            bail!(
                "edge-tier language {lang:?} requires --justify (see STACK_POLICY: {STACK_POLICY_URL})"
            );
        }
        return Ok(());
    }
    bail!(
        "unknown language {lang:?}; core: {core}; edge: {edge}",
        core = CORE_LANGS.join(", "),
        edge = EDGE_LANGS.join(", ")
    );
}

pub fn render_edge_justification(lang: &str, justify: &str) -> String {
    format!(
        "\n## Edge language: {lang}\n\
         - **Scope:** fleet bootstrap via `hexakit init`\n\
         - **Reason:** {justify}\n\
         - **Exit criteria:** fold into Core tier or drop edge when charter allows\n\
         - **ADR:** N/A (init-time justification)\n",
        lang = crate::registry::format_lang(&normalize_lang(lang)),
        justify = justify.trim(),
    )
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn core_lang_ok_without_justify() {
        assert!(validate_lang_gate("rust", None).is_ok());
    }

    #[test]
    fn edge_lang_requires_justify() {
        assert!(validate_lang_gate("go", None).is_err());
        assert!(validate_lang_gate("go", Some("deploy binary today")).is_ok());
    }
}
