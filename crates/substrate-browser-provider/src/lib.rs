//! `substrate-browser-provider` - the broker as a normalized protocol provider.
//!
//! # Why
//!
//! `BROWSER_PROVIDER_PROTOCOL.md` describes one `browser` tool over many
//! providers, but only the Firefox bridge has ever implemented it, and the
//! document's own conformance suite was never written. This crate is both:
//!
//! - a provider that satisfies the required core over stdio NDJSON, backed by
//!   the lease-guarded broker, and
//! - the conformance harness the protocol asked for, exercised against a real
//!   browser in `tests/`.
//!
//! # What it is not
//!
//! Not a replacement for the Firefox bridge. A harness can only consume this
//! once its provider registry stops being hardcoded; until then this is a
//! conformant adapter that a client can drive directly, plus the conformance
//! evidence the protocol lacked.

#![deny(missing_docs)]

use std::sync::Arc;

use base64::Engine;
use serde_json::{json, Value};
use substrate_browser_broker::{Broker, Scope};

/// Protocol version implemented here.
pub const PROTOCOL_VERSION: &str = "0.1";

/// Provider identity returned by `provider.describe`.
pub const PROVIDER_ID: &str = "substrate_browser_broker";

fn ok(id: &Value, result: Value) -> Value {
    json!({ "protocol_version": PROTOCOL_VERSION, "id": id, "ok": true, "result": result, "warnings": [] })
}

fn err(id: &Value, code: &str, message: impl Into<String>) -> Value {
    json!({
        "protocol_version": PROTOCOL_VERSION,
        "id": id,
        "ok": false,
        "error": { "code": code, "message": message.into(), "retryable": false, "details": {} }
    })
}

/// One active session, keyed by the lease that authorises it.
struct Session {
    acquired: substrate_browser_broker::Acquired,
}

/// The provider itself.
pub struct Provider {
    broker: Arc<Broker>,
    session: Option<Session>,
}

impl Provider {
    /// Open a provider over `broker`.
    pub fn new(broker: Arc<Broker>) -> Self {
        Self {
            broker,
            session: None,
        }
    }

    /// Dispatch one request envelope and return one response envelope.
    pub async fn handle(&mut self, request: &Value) -> Value {
        let id = request.get("id").cloned().unwrap_or(Value::Null);
        let method = match request.get("method").and_then(Value::as_str) {
            Some(method) => method.to_string(),
            None => return err(&id, "invalid_request", "missing method"),
        };
        let params = request.get("params").cloned().unwrap_or_else(|| json!({}));

        match self.dispatch(&method, &params).await {
            Ok(result) => ok(&id, result),
            Err(Problem { code, message }) => err(&id, &code, message),
        }
    }

    async fn dispatch(
        &mut self,
        method: &str,
        params: &Value,
    ) -> std::result::Result<Value, Problem> {
        match method {
            "provider.describe" => Ok(self.describe()),
            "provider.status" => Ok(self.status()),
            "session.ensure" => self.ensure(params).await,
            "session.close" => self.close(),
            "page.open" => self.page_open(params).await,
            "page.snapshot" => self.page_snapshot().await,
            "page.click" => self.page_click(params).await,
            "page.type" => self.page_type(params).await,
            "page.wait" => self.page_wait(params).await,
            "page.screenshot" => self.page_screenshot().await,
            other => Err(Problem::unsupported(other)),
        }
    }

    fn describe(&self) -> Value {
        json!({
            "provider_id": PROVIDER_ID,
            "provider_label": "Substrate Browser Broker",
            "provider_version": env!("CARGO_PKG_VERSION"),
            "protocol_version": PROTOCOL_VERSION,
            "browser_families": ["chrome"],
            "transport": "stdio-json",
            "certification_tier": "candidate",
            "capabilities": {
                "core_methods": [
                    "provider.describe", "provider.status", "session.ensure", "session.close",
                    "page.open", "page.snapshot", "page.click", "page.type", "page.wait",
                    "page.screenshot"
                ],
                "optional_methods": [],
                "features": [
                    "element_refs", "a11y_snapshot", "isolated_contexts",
                    "persistent_profile", "lease_scoped_sessions"
                ],
                "custom_methods": []
            }
        })
    }

    fn status(&self) -> Value {
        let available = substrate_browser_broker::browser_available();
        json!({
            "availability": if available { "ready" } else { "unavailable" },
            "browser_detected": available,
            "browser_running": self.session.is_some(),
            "setup_state": if available { "complete" } else { "broken" },
            "requires_manual_setup": !available,
            "recommended_browser": "chrome",
            "manual_steps": if available { json!([]) } else { json!(["Install Chrome or Chromium, or set CHROME_BIN"]) },
            "diagnostics": []
        })
    }

    async fn ensure(&mut self, params: &Value) -> std::result::Result<Value, Problem> {
        if let Some(session) = &self.session {
            return Ok(json!({
                "session_id": session.acquired.lease.id,
                "browser_family": "chrome",
                "browser_label": "Chrome",
                "attached_to_existing_browser": false,
                "isolation": "per_jcode_session",
                "default_page_id": "page_1"
            }));
        }

        let principal = params
            .get("principal")
            .and_then(Value::as_str)
            .ok_or_else(|| Problem::invalid("session.ensure requires principal"))?;
        let profile = params
            .get("profile")
            .and_then(Value::as_str)
            .unwrap_or("default");
        let session_name = params
            .get("client_session_id")
            .and_then(Value::as_str)
            .unwrap_or("provider");
        let ttl_secs = params
            .get("ttl_secs")
            .and_then(Value::as_u64)
            .unwrap_or(900);

        let scope = Scope::new(principal, profile, session_name)
            .map_err(|e| Problem::invalid(e.to_string()))?;

        let acquired = self
            .broker
            .acquire(
                &scope,
                PROVIDER_ID,
                std::time::Duration::from_secs(ttl_secs),
            )
            .await
            .map_err(|e| Problem {
                code: "not_ready".to_string(),
                message: e.to_string(),
            })?;

        let session_id = acquired.lease.id.clone();
        self.session = Some(Session { acquired });

        Ok(json!({
            "session_id": session_id,
            "browser_family": "chrome",
            "browser_label": "Chrome",
            "attached_to_existing_browser": false,
            "isolation": "per_jcode_session",
            "default_page_id": "page_1"
        }))
    }

    fn close(&mut self) -> std::result::Result<Value, Problem> {
        let session = self
            .session
            .take()
            .ok_or_else(|| Problem::invalid("no session to close"))?;
        let broker = self.broker.clone();
        // Release runs on a detached task because closing the browser is async
        // and the request loop must stay responsive.
        tokio::spawn(async move {
            let _ = broker.release(session.acquired).await;
        });
        Ok(json!({ "closed": true }))
    }

    fn session(&self) -> std::result::Result<&substrate_browser_broker::Acquired, Problem> {
        self.session
            .as_ref()
            .map(|s| &s.acquired)
            .ok_or_else(|| Problem::invalid("session.ensure must be called first"))
    }

    async fn page_open(&mut self, params: &Value) -> std::result::Result<Value, Problem> {
        let url = params
            .get("url")
            .and_then(Value::as_str)
            .ok_or_else(|| Problem::invalid("page.open requires url"))?
            .to_string();
        let session = self.session()?;
        session.browser.open(&url).await.map_err(browser_problem)?;
        Ok(json!({ "page_id": "page_1", "url": url, "navigation_state": "load" }))
    }

    async fn page_snapshot(&mut self) -> std::result::Result<Value, Problem> {
        let session = self.session()?;
        let snapshot = session.browser.snapshot().await.map_err(browser_problem)?;
        let elements: Vec<Value> = snapshot
            .elements
            .iter()
            .map(|node| {
                json!({
                    "element_ref": node.element_ref,
                    "role": node.role,
                    "name": node.name,
                    "actionable": node.actionable,
                    "enabled": true
                })
            })
            .collect();
        Ok(json!({
            "page_id": "page_1",
            "url": snapshot.url,
            "title": snapshot.title,
            "text": snapshot.text,
            "elements": elements
        }))
    }

    async fn page_click(&mut self, params: &Value) -> std::result::Result<Value, Problem> {
        let reference = params
            .get("element_ref")
            .and_then(Value::as_str)
            .ok_or_else(|| Problem::invalid("page.click requires element_ref"))?
            .to_string();
        let session = self.session()?;
        session
            .browser
            .click(&reference)
            .await
            .map_err(browser_problem)?;
        Ok(json!({ "page_id": "page_1", "clicked": true }))
    }

    async fn page_type(&mut self, params: &Value) -> std::result::Result<Value, Problem> {
        let reference = params
            .get("element_ref")
            .and_then(Value::as_str)
            .ok_or_else(|| Problem::invalid("page.type requires element_ref"))?
            .to_string();
        let text = params
            .get("text")
            .and_then(Value::as_str)
            .ok_or_else(|| Problem::invalid("page.type requires text"))?
            .to_string();
        let submit = params
            .get("submit")
            .and_then(Value::as_bool)
            .unwrap_or(false);
        let session = self.session()?;
        session
            .browser
            .type_into(&reference, &text, submit)
            .await
            .map_err(browser_problem)?;
        Ok(json!({ "page_id": "page_1", "typed": true }))
    }

    async fn page_wait(&mut self, params: &Value) -> std::result::Result<Value, Problem> {
        let needle = params
            .get("text_present")
            .and_then(Value::as_str)
            .ok_or_else(|| Problem::invalid("page.wait requires text_present"))?
            .to_string();
        let timeout_ms = params
            .get("timeout_ms")
            .and_then(Value::as_u64)
            .unwrap_or(10_000);
        let session = self.session()?;
        let satisfied = session
            .browser
            .wait_for_text(&needle, std::time::Duration::from_millis(timeout_ms))
            .await
            .map_err(browser_problem)?;
        Ok(json!({ "satisfied": satisfied, "matched_condition": "text_present" }))
    }

    async fn page_screenshot(&mut self) -> std::result::Result<Value, Problem> {
        let session = self.session()?;
        let png = session
            .browser
            .screenshot()
            .await
            .map_err(browser_problem)?;
        Ok(json!({
            "page_id": "page_1",
            "image": base64::engine::general_purpose::STANDARD.encode(png),
            "media_type": "image/png"
        }))
    }
}

fn browser_problem(err: substrate_browser_broker::BrokerError) -> Problem {
    let code = match &err {
        substrate_browser_broker::BrokerError::State(_) => "not_ready",
        substrate_browser_broker::BrokerError::NoSession(_) => "session_not_found",
        substrate_browser_broker::BrokerError::Released { .. } => "session_not_found",
        substrate_browser_broker::BrokerError::Busy { .. } => "not_ready",
        substrate_browser_broker::BrokerError::NotHolder { .. } => "permission_denied",
        substrate_browser_broker::BrokerError::ProfileBusy { .. } => "not_ready",
        substrate_browser_broker::BrokerError::Browser(_) => "internal_error",
    };
    Problem {
        code: code.to_string(),
        message: err.to_string(),
    }
}

/// A protocol error.
#[derive(Debug, Clone)]
pub struct Problem {
    /// Protocol error code.
    pub code: String,
    /// Human-readable message.
    pub message: String,
}

impl Problem {
    fn invalid(message: impl Into<String>) -> Self {
        Self {
            code: "invalid_request".to_string(),
            message: message.into(),
        }
    }

    fn unsupported(method: &str) -> Self {
        Self {
            code: "unsupported_method".to_string(),
            message: format!("this provider does not implement {method}"),
        }
    }
}
