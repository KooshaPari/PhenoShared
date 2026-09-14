//! Sentry configuration for Apisync
//!
//! Traces to: FR-APISYNC-SENTRY-001
//!
//! Error tracking for API toolkit with REST/GraphQL/WebSocket support

use std::env;

/// Initialize Sentry for API server
pub fn init() -> Option<sentry::ClientInitGuard> {
    let dsn = env::var("SENTRY_DSN").ok()?;
    let environment = env::var("SENTRY_ENVIRONMENT").unwrap_or_else(|_| "development".to_string());
    let release = format!("{}@{}", env!("CARGO_PKG_NAME"), env!("CARGO_PKG_VERSION"));

    Some(sentry::init((
        dsn,
        sentry::ClientOptions {
            environment: Some(environment.into()),
            release: Some(release.into()),
            attach_stacktrace: true,
            debug: cfg!(debug_assertions),
            
            // Before send to filter out common API noise
            before_send: Some(std::sync::Arc::new(|mut event| {
                // Filter out validation errors (400s)
                if let Some(ref exc) = event.exception.values.first() {
                    if exc.ty == "ValidationError" || exc.ty == "BadRequest" {
                        return None;
                    }
                }
                Some(event)
            })),
            
            ..Default::default()
        },
    )))
}

/// Capture API error with request context
pub fn capture_api_error(
    error: &impl std::error::Error,
    endpoint: &str,
    method: &str,
    status_code: u16,
) {
    sentry::with_scope(
        |scope| {
            scope.set_tag("api.endpoint", endpoint);
            scope.set_tag("api.method", method);
            scope.set_tag("api.status_code", &status_code.to_string());
            scope.set_extra("api.context", format!("{} {}", method, endpoint).into());
        },
        || sentry::capture_error(error),
    );
}

/// Set request context for all subsequent events
pub fn set_request_context(request_id: &str, user_id: Option<&str>) {
    sentry::configure_scope(|scope| {
        scope.set_tag("request.id", request_id);
        if let Some(uid) = user_id {
            scope.set_user(Some(sentry::User {
                id: Some(uid.into()),
                ..Default::default()
            }));
        }
    });
}

#[cfg(test)]
mod tests {
    use super::*;

    // Traces to: FR-APISYNC-SENTRY-001
    #[test]
    fn test_sentry_init_respects_environment() {
        let guard = init();
        // Without SENTRY_DSN, should return None
        assert!(guard.is_none());
    }
}
