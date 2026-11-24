//! OIDC header validation helper.
//!
//! Validates and extracts `X-OIDC-*` headers from HTTP requests.
//! Feature-gated behind `oidc` (default off — zero cost to consumers
//! that don't need OIDC header parsing).

#[cfg(feature = "oidc")]
use http::HeaderMap;

/// Validated OIDC claims extracted from headers.
#[derive(Clone, Debug, PartialEq)]
pub struct OidcClaims {
    /// The `X-OIDC-Subject` header value (required).
    pub subject: String,
    /// The `X-OIDC-Email` header value (optional).
    pub email: Option<String>,
    /// The `X-OIDC-Name` header value (optional).
    pub name: Option<String>,
    /// The `X-OIDC-Roles` header value, comma-separated (optional).
    pub roles: Vec<String>,
}

/// Errors from OIDC header validation.
#[derive(Debug, thiserror::Error)]
pub enum OidcError {
    /// Required `X-OIDC-Subject` header was missing.
    #[error("missing X-OIDC-Subject header")]
    MissingSubject,
}

#[cfg(feature = "oidc")]
impl OidcClaims {
    /// Extract OIDC claims from HTTP headers.
    ///
    /// Required: `X-OIDC-Subject`
    /// Optional: `X-OIDC-Email`, `X-OIDC-Name`, `X-OIDC-Roles`
    pub fn from_headers(headers: &HeaderMap) -> Result<Self, OidcError> {
        let subject = headers
            .get("X-OIDC-Subject")
            .and_then(|v| v.to_str().ok())
            .map(String::from)
            .ok_or(OidcError::MissingSubject)?;

        let email = headers
            .get("X-OIDC-Email")
            .and_then(|v| v.to_str().ok())
            .map(String::from);

        let name = headers
            .get("X-OIDC-Name")
            .and_then(|v| v.to_str().ok())
            .map(String::from);

        let roles = headers
            .get("X-OIDC-Roles")
            .and_then(|v| v.to_str().ok())
            .map(|s| s.split(',').map(|r| r.trim().to_string()).collect())
            .unwrap_or_default();

        Ok(Self {
            subject,
            email,
            name,
            roles,
        })
    }

    /// Check whether this identity has a specific role.
    pub fn has_role(&self, role: &str) -> bool {
        self.roles.iter().any(|r| r == role)
    }
}

#[cfg(feature = "oidc")]
#[cfg(test)]
mod tests {
    use http::HeaderValue;

    use super::*;

    #[test]
    fn extracts_all_fields() {
        let mut headers = HeaderMap::new();
        headers.insert("X-OIDC-Subject", HeaderValue::from_static("user-42"));
        headers.insert("X-OIDC-Email", HeaderValue::from_static("user@example.com"));
        headers.insert("X-OIDC-Name", HeaderValue::from_static("Alice"));
        headers.insert("X-OIDC-Roles", HeaderValue::from_static("admin,editor"));

        let claims = OidcClaims::from_headers(&headers).unwrap();
        assert_eq!(claims.subject, "user-42");
        assert_eq!(claims.email, Some("user@example.com".to_string()));
        assert_eq!(claims.name, Some("Alice".to_string()));
        assert_eq!(
            claims.roles,
            vec!["admin".to_string(), "editor".to_string()]
        );
    }

    #[test]
    fn missing_subject_returns_error() {
        let headers = HeaderMap::new();
        let err = OidcClaims::from_headers(&headers).unwrap_err();
        assert!(matches!(err, OidcError::MissingSubject));
    }

    #[test]
    fn has_role_checks() {
        let mut headers = HeaderMap::new();
        headers.insert("X-OIDC-Subject", HeaderValue::from_static("user-42"));
        headers.insert("X-OIDC-Roles", HeaderValue::from_static("admin,viewer"));

        let claims = OidcClaims::from_headers(&headers).unwrap();
        assert!(claims.has_role("admin"));
        assert!(claims.has_role("viewer"));
        assert!(!claims.has_role("editor"));
    }
}
