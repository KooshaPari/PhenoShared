//! Scope: who is acting, on which profile, in which session and tab.

use std::fmt;
use thiserror::Error;

/// Maximum accepted length of a single scope component.
const MAX_COMPONENT: usize = 64;

/// A validation failure for a [`Scope`] component.
#[derive(Debug, Error, PartialEq, Eq)]
pub enum ScopeError {
    /// A component was empty.
    #[error("scope component `{0}` must not be empty")]
    Empty(&'static str),

    /// A component exceeded the length limit.
    #[error("scope component `{field}` exceeds {max} characters")]
    TooLong {
        /// Which component failed.
        field: &'static str,
        /// Maximum accepted length.
        max: usize,
    },

    /// A component contained a character outside the safe set.
    #[error(
        "scope component `{field}` contains unsafe character {ch:?}; \
         allowed are a-z, 0-9, '.', '_' and '-'"
    )]
    UnsupportedChar {
        /// Which component failed.
        field: &'static str,
        /// The offending character.
        ch: char,
    },

    /// A component looked like a path traversal or path separator.
    #[error("scope component `{field}` must not contain a path separator or `..`")]
    PathTraversal {
        /// Which component failed.
        field: &'static str,
    },

    /// The textual form had the wrong number of segments.
    #[error("scope `{0}` must have 2 to 4 `/`-separated segments")]
    Shape(String),
}

fn check(field: &'static str, value: &str) -> Result<(), ScopeError> {
    if value.is_empty() {
        return Err(ScopeError::Empty(field));
    }
    if value.chars().count() > MAX_COMPONENT {
        return Err(ScopeError::TooLong {
            field,
            max: MAX_COMPONENT,
        });
    }
    if value == "." || value == ".." || value.contains('/') || value.contains('\\') {
        return Err(ScopeError::PathTraversal { field });
    }
    for ch in value.chars() {
        let ok = ch.is_ascii_lowercase() || ch.is_ascii_digit() || matches!(ch, '.' | '_' | '-');
        if !ok {
            return Err(ScopeError::UnsupportedChar { field, ch });
        }
    }
    Ok(())
}

/// Identifies one actor's claim on one browser profile.
///
/// Components are deliberately restricted to a lowercase safe set so a scope can
/// be used directly as a filesystem path segment without escaping the store root.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Scope {
    principal: String,
    profile: String,
    session: String,
    tab: Option<String>,
}

impl Scope {
    /// Build a scope for a principal and profile operating in a session.
    pub fn new(
        principal: impl Into<String>,
        profile: impl Into<String>,
        session: impl Into<String>,
    ) -> Result<Self, ScopeError> {
        let scope = Self {
            principal: principal.into(),
            profile: profile.into(),
            session: session.into(),
            tab: None,
        };
        scope.validate()?;
        Ok(scope)
    }

    /// Build a scope additionally pinned to one tab.
    pub fn with_tab(mut self, tab: impl Into<String>) -> Result<Self, ScopeError> {
        let tab = tab.into();
        check("tab", &tab)?;
        self.tab = Some(tab);
        Ok(self)
    }

    /// Parse `principal/profile`, `principal/profile/session`,
    /// `principal/profile/session:tab` or `principal/profile/session/tab`.
    ///
    /// A two-segment form means "the default session for this profile".
    pub fn parse(text: &str) -> Result<Self, ScopeError> {
        let text = text.trim();
        let parts: Vec<&str> = text.split('/').collect();
        if !(2..=4).contains(&parts.len()) {
            return Err(ScopeError::Shape(text.to_string()));
        }
        let (session, tab) = match parts.len() {
            4 => (parts[2], Some(parts[3])),
            3 => match parts[2].split_once(':') {
                Some((session, tab)) => (session, Some(tab)),
                None => (parts[2], None),
            },
            _ => ("default", None),
        };
        let scope = Self::new(parts[0], parts[1], session)?;
        match tab {
            Some(tab) => scope.with_tab(tab),
            None => Ok(scope),
        }
    }

    /// The principal (human, agent identity, tenant).
    pub fn principal(&self) -> &str {
        &self.principal
    }

    /// The named browser profile owned by the principal.
    pub fn profile(&self) -> &str {
        &self.profile
    }

    /// The logical session using the profile.
    pub fn session(&self) -> &str {
        &self.session
    }

    /// The tab, when the caller pinned one.
    pub fn tab(&self) -> Option<&str> {
        self.tab.as_deref()
    }

    /// `principal/profile`, the unit that exclusivity is enforced on.
    ///
    /// Storage isolation is a property of a profile, not of a window, so two
    /// holders are mutually exclusive whenever they name the same profile.
    pub fn profile_key(&self) -> String {
        format!("{}/{}", self.principal, self.profile)
    }

    fn validate(&self) -> Result<(), ScopeError> {
        check("principal", &self.principal)?;
        check("profile", &self.profile)?;
        check("session", &self.session)?;
        if let Some(tab) = &self.tab {
            check("tab", tab)?;
        }
        Ok(())
    }
}

impl fmt::Display for Scope {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}/{}/{}", self.principal, self.profile, self.session)?;
        if let Some(tab) = &self.tab {
            write!(f, ":{}", tab)?;
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn builds_and_displays() {
        let s = Scope::new("alice", "work", "s1")
            .unwrap()
            .with_tab("t2")
            .unwrap();
        assert_eq!(s.to_string(), "alice/work/s1:t2");
        assert_eq!(s.profile_key(), "alice/work");
    }

    #[test]
    fn parses_three_and_four_segments() {
        assert_eq!(Scope::parse("a/b/c").unwrap().session(), "c");
        assert_eq!(Scope::parse("a/b/c:d").unwrap().tab(), Some("d"));
        assert_eq!(Scope::parse("a/b/c/d").unwrap().tab(), Some("d"));
    }

    #[test]
    fn rejects_path_traversal() {
        assert!(matches!(
            Scope::new("../etc", "p", "s"),
            Err(ScopeError::PathTraversal { .. })
        ));
        assert!(Scope::new("a", "p", "s").is_ok());
        assert!(Scope::parse("a/b").is_ok());
        assert!(matches!(Scope::parse("a"), Err(ScopeError::Shape(_))));
    }

    #[test]
    fn rejects_uppercase_and_separators() {
        assert!(matches!(
            Scope::new("Alice", "p", "s"),
            Err(ScopeError::UnsupportedChar { ch: 'A', .. })
        ));
        assert!(matches!(
            Scope::new("a", "p", "s/1"),
            Err(ScopeError::PathTraversal { .. })
        ));
    }

    #[test]
    fn rejects_overlong_component() {
        let long = "x".repeat(MAX_COMPONENT + 1);
        assert!(matches!(
            Scope::new("a", long, "s"),
            Err(ScopeError::TooLong { .. })
        ));
    }
}
