//! Minimal i18n scaffold (C01 L16).
//!
//! Phase-0 ships JSON catalogs under `locales/` (`en` + soft `es`) plus a
//! lookup helper with `SL_LOCALE` selection. No Fluent/ICU `MessageFormat`
//! runtime yet — that remains a documented future hook in `docs/ops/i18n.md`.

use serde::Deserialize;
use std::collections::HashMap;
use std::sync::OnceLock;

/// Default catalog locale.
pub const DEFAULT_LOCALE: &str = "en";

/// Soft second-locale catalog tag (Phase-0 multi-locale evidence).
pub const SOFT_LOCALE_ES: &str = "es";

/// Embedded English catalog (compile-time include of `locales/en.json`).
const EN_CATALOG_JSON: &str = include_str!("../locales/en.json");

/// Embedded Spanish soft catalog (compile-time include of `locales/es.json`).
const ES_CATALOG_JSON: &str = include_str!("../locales/es.json");

#[derive(Debug, Deserialize)]
struct CatalogFile {
    locale: String,
    messages: HashMap<String, String>,
}

/// Loaded message catalog for one locale.
#[derive(Debug, Clone)]
pub struct Catalog {
    locale: String,
    messages: HashMap<String, String>,
}

impl Catalog {
    /// Parse a JSON catalog document (`{ "locale", "messages": { key: text } }`).
    ///
    /// # Errors
    /// Returns a serde error when the JSON shape is invalid.
    pub fn from_json(json: &str) -> Result<Self, serde_json::Error> {
        let file: CatalogFile = serde_json::from_str(json)?;
        Ok(Self { locale: file.locale, messages: file.messages })
    }

    /// Locale tag for this catalog (BCP 47-ish, e.g. `en`).
    #[must_use]
    pub fn locale(&self) -> &str {
        &self.locale
    }

    /// Look up `key`; returns `None` when missing.
    #[must_use]
    pub fn get(&self, key: &str) -> Option<&str> {
        self.messages.get(key).map(String::as_str)
    }

    /// Look up `key`, falling back to the key itself when missing.
    #[must_use]
    pub fn t<'a>(&'a self, key: &'a str) -> &'a str {
        self.get(key).unwrap_or(key)
    }

    /// Number of message entries.
    #[must_use]
    pub fn len(&self) -> usize {
        self.messages.len()
    }

    /// Whether the catalog has no messages.
    #[must_use]
    pub fn is_empty(&self) -> bool {
        self.messages.is_empty()
    }
}

static EN_CATALOG: OnceLock<Catalog> = OnceLock::new();
static ES_CATALOG: OnceLock<Catalog> = OnceLock::new();

/// Return the embedded English catalog (parsed once).
///
/// # Panics
/// Panics only if the checked-in `locales/en.json` is invalid JSON — a
/// packaging bug caught by unit tests and `SelfCheck`.
#[must_use]
pub fn en_catalog() -> &'static Catalog {
    EN_CATALOG.get_or_init(|| {
        Catalog::from_json(EN_CATALOG_JSON)
            .expect("locales/en.json must parse as a message catalog")
    })
}

/// Return the embedded Spanish soft catalog (parsed once).
///
/// # Panics
/// Panics only if the checked-in `locales/es.json` is invalid JSON.
#[must_use]
pub fn es_catalog() -> &'static Catalog {
    ES_CATALOG.get_or_init(|| {
        Catalog::from_json(ES_CATALOG_JSON)
            .expect("locales/es.json must parse as a message catalog")
    })
}

/// Normalize a locale tag for catalog lookup (`en-US` → `en`).
#[must_use]
pub fn normalize_locale(tag: &str) -> &str {
    let primary = tag.split(['-', '_']).next().unwrap_or(tag);
    if primary.eq_ignore_ascii_case(SOFT_LOCALE_ES) {
        SOFT_LOCALE_ES
    } else if primary.eq_ignore_ascii_case(DEFAULT_LOCALE) {
        DEFAULT_LOCALE
    } else {
        primary
    }
}

/// Resolve the active locale: explicit arg → `SL_LOCALE` → [`DEFAULT_LOCALE`].
#[must_use]
pub fn active_locale(explicit: Option<&str>) -> String {
    if let Some(tag) = explicit.filter(|s| !s.trim().is_empty()) {
        return normalize_locale(tag).to_string();
    }
    if let Ok(env_tag) = std::env::var("SL_LOCALE") {
        if !env_tag.trim().is_empty() {
            return normalize_locale(&env_tag).to_string();
        }
    }
    DEFAULT_LOCALE.to_string()
}

/// Translate `key` using the active catalog (`explicit` or `SL_LOCALE` or `en`).
///
/// Missing keys fall back to English, then to the key string.
#[must_use]
pub fn t(key: &str) -> &str {
    t_locale(key, None)
}

/// Translate `key` for an explicit locale override (still honors English fallback).
#[must_use]
pub fn t_locale<'a>(key: &'a str, locale: Option<&str>) -> &'a str {
    let tag = active_locale(locale);
    if let Some(cat) = try_catalog(&tag) {
        if let Some(msg) = cat.get(key) {
            return msg;
        }
    }
    en_catalog().get(key).unwrap_or(key)
}

/// Resolve a catalog for `locale` (`en` / `es` today).
///
/// Returns [`None`] for unknown locales so callers can fall back explicitly.
#[must_use]
pub fn try_catalog(locale: &str) -> Option<&'static Catalog> {
    match normalize_locale(locale) {
        DEFAULT_LOCALE => Some(en_catalog()),
        SOFT_LOCALE_ES => Some(es_catalog()),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn en_catalog_parses_and_has_core_keys() {
        let cat = en_catalog();
        assert_eq!(cat.locale(), "en");
        assert!(!cat.is_empty());
        assert_eq!(cat.t("viewer.app_title"), "SessionLedger");
        assert!(cat.get("cli.app_about").is_some());
        assert!(cat.get("viewer.empty_state").is_some());
    }

    #[test]
    fn es_catalog_shares_en_keys() {
        let es = es_catalog();
        assert_eq!(es.locale(), "es");
        for key in [
            "cli.app_about",
            "cli.serve_help",
            "viewer.app_title",
            "viewer.tab_sessions",
            "viewer.tab_unfinished",
            "viewer.empty_state",
            "viewer.search_placeholder",
        ] {
            assert!(es.get(key).is_some(), "es catalog missing en key {key}");
        }
        assert_eq!(es.len(), en_catalog().len());
    }

    #[test]
    fn missing_key_falls_back_to_key() {
        assert_eq!(t("does.not.exist"), "does.not.exist");
    }

    #[test]
    fn try_catalog_accepts_en_and_es() {
        assert!(try_catalog("en").is_some());
        assert!(try_catalog("en-US").is_some());
        assert!(try_catalog("es").is_some());
        assert!(try_catalog("es-MX").is_some());
        assert!(try_catalog("fr").is_none());
    }

    #[test]
    fn t_locale_selects_spanish() {
        let es_msg = t_locale("viewer.tab_sessions", Some("es"));
        assert_eq!(es_msg, "Sesiones");
    }
}
