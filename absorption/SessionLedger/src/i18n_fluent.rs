//! Optional Fluent catalog stub (C01 L16 Phase-1).
//!
//! When the `fluent-catalog` feature is enabled, loads embedded `.ftl` catalogs
//! via `fluent-bundle`. Otherwise [`t_fluent`] delegates to the JSON helper in
//! [`crate::i18n`] so default builds stay dependency-free.

use crate::i18n;

/// Convert a JSON catalog key (`viewer.app_title`) to a Fluent message id (`viewer-app_title`).
#[must_use]
pub fn json_key_to_fluent_id(key: &str) -> String {
    key.replace('.', "-")
}

/// Translate `key` for `locale` using Fluent when enabled, else JSON fallback.
///
/// `locale` may be `None` to honor `SL_LOCALE` / default English (same as [`i18n::t_locale`]).
#[must_use]
pub fn t_fluent(key: &str, locale: Option<&str>) -> String {
    #[cfg(feature = "fluent-catalog")]
    {
        if let Some(msg) = try_fluent_message(key, locale) {
            return msg;
        }
    }
    i18n::t_locale(key, locale).to_string()
}

#[cfg(feature = "fluent-catalog")]
mod fluent_impl {
    use super::json_key_to_fluent_id;
    use crate::i18n::{self, normalize_locale, SOFT_LOCALE_ES};
    use fluent_bundle::{FluentBundle, FluentResource};
    use std::cell::RefCell;
    use unic_langid::LanguageIdentifier;

    const EN_FTL: &str = include_str!("../locales/en.ftl");
    const ES_FTL: &str = include_str!("../locales/es.ftl");

    struct LocaleBundle {
        bundle: FluentBundle<FluentResource>,
    }

    impl LocaleBundle {
        fn from_ftl(ftl: &str, lang: LanguageIdentifier) -> Self {
            let resource =
                FluentResource::try_new(ftl.to_string()).expect("embedded FTL must parse");
            let mut bundle = FluentBundle::new(vec![lang]);
            bundle.add_resource(resource).expect("embedded FTL must attach to bundle");
            Self { bundle }
        }

        fn format(&self, message_id: &str) -> Option<String> {
            let msg = self.bundle.get_message(message_id)?;
            let pattern = msg.value()?;
            let mut errors = Vec::new();
            let formatted = self.bundle.format_pattern(pattern, None, &mut errors);
            if errors.is_empty() {
                Some(formatted.to_string())
            } else {
                None
            }
        }
    }

    thread_local! {
        static EN_BUNDLE: RefCell<Option<LocaleBundle>> = const { RefCell::new(None) };
        static ES_BUNDLE: RefCell<Option<LocaleBundle>> = const { RefCell::new(None) };
    }

    fn with_en_bundle<F, R>(f: F) -> R
    where
        F: FnOnce(&LocaleBundle) -> R,
    {
        EN_BUNDLE.with(|cell| {
            let mut slot = cell.borrow_mut();
            if slot.is_none() {
                *slot = Some(LocaleBundle::from_ftl(
                    EN_FTL,
                    "en".parse().expect("en is a valid langid"),
                ));
            }
            f(slot.as_ref().expect("en Fluent bundle initialized"))
        })
    }

    fn with_es_bundle<F, R>(f: F) -> R
    where
        F: FnOnce(&LocaleBundle) -> R,
    {
        ES_BUNDLE.with(|cell| {
            let mut slot = cell.borrow_mut();
            if slot.is_none() {
                *slot = Some(LocaleBundle::from_ftl(
                    ES_FTL,
                    "es".parse().expect("es is a valid langid"),
                ));
            }
            f(slot.as_ref().expect("es Fluent bundle initialized"))
        })
    }

    fn with_bundle_for<F, R>(locale: Option<&str>, f: F) -> R
    where
        F: FnOnce(&LocaleBundle) -> R,
    {
        let tag = i18n::active_locale(locale);
        match normalize_locale(&tag) {
            SOFT_LOCALE_ES => with_es_bundle(f),
            _ => with_en_bundle(f),
        }
    }

    pub(super) fn try_fluent_message(key: &str, locale: Option<&str>) -> Option<String> {
        let message_id = json_key_to_fluent_id(key);
        let primary = with_bundle_for(locale, |bundle| bundle.format(&message_id));
        if primary.is_some() || locale.is_some() {
            return primary;
        }
        with_en_bundle(|bundle| bundle.format(&message_id)).or(primary)
    }
}

#[cfg(feature = "fluent-catalog")]
use fluent_impl::try_fluent_message;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn json_key_to_fluent_id_replaces_dots() {
        assert_eq!(json_key_to_fluent_id("viewer.app_title"), "viewer-app_title");
        assert_eq!(json_key_to_fluent_id("cli.serve_help"), "cli-serve_help");
    }

    #[test]
    fn t_fluent_json_fallback_without_feature() {
        let msg = t_fluent("viewer.tab_sessions", Some("es"));
        assert_eq!(msg, "Sesiones");
    }

    #[test]
    fn t_fluent_missing_key_returns_key_string() {
        assert_eq!(t_fluent("does.not.exist", None), "does.not.exist");
    }

    #[cfg(feature = "fluent-catalog")]
    mod fluent_catalog {
        use super::*;

        #[test]
        fn fluent_catalog_loads_en_messages() {
            assert_eq!(t_fluent("viewer.app_title", Some("en")), "SessionLedger");
            assert_eq!(t_fluent("viewer.tab_sessions", Some("en")), "Sessions");
        }

        #[test]
        fn fluent_catalog_loads_es_messages() {
            assert_eq!(t_fluent("viewer.tab_sessions", Some("es")), "Sesiones");
            assert_eq!(
                t_fluent("viewer.empty_state", Some("es")),
                "Aún no hay sesiones. Apunte el daemon a un directorio vigilado para comenzar."
            );
        }
    }
}
