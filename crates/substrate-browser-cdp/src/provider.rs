//! A Chrome DevTools provider that satisfies the normalized browser contract.
//!
//! Every operation maps onto the DevTools Protocol: navigation on `Page`, reads
//! on `Accessibility` and `Runtime`, actions on `DOM` + `Runtime.callFunctionOn`,
//! captures on `Page.captureScreenshot`.

use std::{collections::BTreeMap, path::Path, sync::Arc, time::Duration};

use base64::Engine;
use serde_json::{json, Value};

use crate::{
    launch::{ChromeProcess, LaunchOptions},
    snapshot::{self, Snapshot},
    transport::Cdp,
    transport::FenceCheck,
    CdpError, Result,
};

/// A page inside a dedicated Chrome instance.
pub struct CdpProvider {
    process: ChromeProcess,
    cdp: Cdp,
    session: String,
    refs: BTreeMap<String, i64>,
    action_timeout: Duration,
}

impl std::fmt::Debug for CdpProvider {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("CdpProvider")
            .field("process", &self.process)
            .field("session", &self.session)
            .field("elements", &self.refs.len())
            .finish()
    }
}

impl CdpProvider {
    /// Launch Chrome against `user_data_dir` and attach to a fresh page.
    pub async fn launch(user_data_dir: impl AsRef<Path>, headless: bool) -> Result<Self> {
        let options = if headless {
            LaunchOptions::headless(user_data_dir.as_ref())
        } else {
            LaunchOptions::headed(user_data_dir.as_ref())
        };
        Self::with_options(options).await
    }

    /// Launch with explicit options.
    pub async fn with_options(options: LaunchOptions) -> Result<Self> {
        let process = ChromeProcess::launch(&options).await?;
        let mut cdp = Cdp::connect(process.ws_url())
            .await?
            .with_timeout(Duration::from_secs(30));

        let target = cdp
            .call("Target.createTarget", json!({ "url": "about:blank" }), None)
            .await?;
        let target_id = target
            .get("targetId")
            .and_then(Value::as_str)
            .ok_or_else(|| CdpError::Protocol("Target.createTarget returned no targetId".into()))?
            .to_string();

        let attached = cdp
            .call(
                "Target.attachToTarget",
                json!({ "targetId": target_id, "flatten": true }),
                None,
            )
            .await?;
        let session = attached
            .get("sessionId")
            .and_then(Value::as_str)
            .ok_or_else(|| {
                CdpError::Protocol("Target.attachToTarget returned no sessionId".into())
            })?
            .to_string();

        let mut provider = Self {
            process,
            cdp,
            session,
            refs: BTreeMap::new(),
            action_timeout: Duration::from_secs(20),
        };

        for domain in ["Page.enable", "Runtime.enable", "DOM.enable"] {
            provider.call(domain, json!({})).await?;
        }
        // Accessibility is optional: a missing domain should not fail launch.
        let _ = provider.call("Accessibility.enable", json!({})).await;

        Ok(provider)
    }

    /// The devtools session id of the attached page.
    pub fn session_id(&self) -> &str {
        &self.session
    }

    /// Install or clear the lease fence forwarded to the underlying transport.
    pub fn set_fence(&mut self, fence: Option<Arc<dyn FenceCheck>>) {
        self.cdp.set_fence(fence);
    }

    /// Operating system process id of the browser backing this provider.
    pub fn pid(&self) -> Option<u32> {
        self.process.pid()
    }

    /// The browser data directory in use.
    pub fn user_data_dir(&self) -> &Path {
        self.process.user_data_dir()
    }

    async fn call(&mut self, method: &str, params: Value) -> Result<Value> {
        let session = self.session.clone();
        self.cdp.call(method, params, Some(&session)).await
    }

    async fn evaluate(&mut self, expression: &str) -> Result<Value> {
        let result = self
            .call(
                "Runtime.evaluate",
                json!({
                    "expression": expression,
                    "returnByValue": true,
                    "awaitPromise": true,
                }),
            )
            .await?;

        if let Some(exception) = result.get("exceptionDetails") {
            let message = exception
                .get("text")
                .and_then(Value::as_str)
                .unwrap_or("evaluation failed");
            return Err(CdpError::Protocol(format!(
                "page evaluation failed: {message}"
            )));
        }

        Ok(result
            .get("result")
            .and_then(|inner| inner.get("value"))
            .cloned()
            .unwrap_or(Value::Null))
    }

    /// Page URL.
    pub async fn url(&mut self) -> Result<String> {
        Ok(self
            .evaluate("location.href")
            .await?
            .as_str()
            .unwrap_or_default()
            .to_string())
    }

    /// Document title.
    pub async fn title(&mut self) -> Result<String> {
        Ok(self
            .evaluate("document.title")
            .await?
            .as_str()
            .unwrap_or_default()
            .to_string())
    }

    /// Navigate and wait for `document.readyState === "complete"`.
    pub async fn open(&mut self, url: &str) -> Result<()> {
        self.call("Page.navigate", json!({ "url": url })).await?;
        self.wait_ready().await
    }

    /// Wait until the document has finished loading.
    pub async fn wait_ready(&mut self) -> Result<()> {
        let deadline = tokio::time::Instant::now() + self.action_timeout;
        let mut last_error: Option<CdpError> = None;

        while tokio::time::Instant::now() < deadline {
            match self.evaluate("document.readyState").await {
                Ok(value) if value.as_str() == Some("complete") => return Ok(()),
                Ok(_) => {},
                Err(err) => last_error = Some(err),
            }
            tokio::time::sleep(Duration::from_millis(50)).await;
        }

        Err(last_error.unwrap_or_else(|| {
            CdpError::Timeout(format!(
                "page did not reach readyState=complete within {}s",
                self.action_timeout.as_secs()
            ))
        }))
    }

    /// Capture a normalized snapshot and refresh the element reference table.
    pub async fn snapshot(&mut self) -> Result<Snapshot> {
        let tree = self
            .call("Accessibility.getFullAXTree", json!({}))
            .await?
            .get("nodes")
            .and_then(Value::as_array)
            .cloned()
            .unwrap_or_default();

        let normalized = snapshot::normalize(&tree);
        self.refs = normalized.backend_ids.clone();

        let url = self.url().await.unwrap_or_default();
        let title = self.title().await.unwrap_or_default();
        Ok(snapshot::snapshot_from(normalized, url, title))
    }

    fn backend_id(&self, element_ref: &str) -> Result<i64> {
        self.refs.get(element_ref).copied().ok_or_else(|| {
            CdpError::Protocol(format!(
                "unknown element reference {element_ref}; take a fresh snapshot first"
            ))
        })
    }

    async fn object_id(&mut self, element_ref: &str) -> Result<String> {
        let backend = self.backend_id(element_ref)?;
        let resolved = self
            .call("DOM.resolveNode", json!({ "backendNodeId": backend }))
            .await?;
        resolved
            .get("object")
            .and_then(|object| object.get("objectId"))
            .and_then(Value::as_str)
            .map(str::to_string)
            .ok_or_else(|| CdpError::Protocol("could not resolve a live element".into()))
    }

    async fn call_on(
        &mut self,
        element_ref: &str,
        function: &str,
        arguments: Value,
    ) -> Result<Value> {
        let object_id = self.object_id(element_ref).await?;
        self.call(
            "Runtime.callFunctionOn",
            json!({
                "objectId": object_id,
                "functionDeclaration": function,
                "arguments": arguments,
                "returnByValue": true,
            }),
        )
        .await
    }

    /// Click the element behind `element_ref`.
    ///
    /// The element is scrolled into view first so a click in a long page is not
    /// silently a no-op.
    pub async fn click(&mut self, element_ref: &str) -> Result<()> {
        const CLICK: &str = "function(){ this.scrollIntoView({block:'center'}); \
                             this.click(); return true; }";
        self.call_on(element_ref, CLICK, json!([])).await?;
        Ok(())
    }

    /// Focus the element, set its value, and fire input/change events.
    ///
    /// `submit` additionally submits the owning form, which is what a caller
    /// means by "type and press enter" for a search box.
    pub async fn type_into(&mut self, element_ref: &str, text: &str, submit: bool) -> Result<()> {
        let function = format!(
            "function(t){{ this.focus(); \
             if ('value' in this) {{ this.value = t; }} else {{ this.textContent = t; }} \
             this.dispatchEvent(new Event('input',{{bubbles:true}})); \
             this.dispatchEvent(new Event('change',{{bubbles:true}})); \
             if ({submit} && this.form && this.form.requestSubmit) {{ this.form.requestSubmit(); }} \
             return true; }}"
        );
        self.call_on(element_ref, &function, json!([{ "value": text }]))
            .await?;
        Ok(())
    }

    /// Poll until the page text contains `needle`, or the timeout elapses.
    pub async fn wait_for_text(&mut self, needle: &str, timeout: Duration) -> Result<bool> {
        let expression = format!(
            "(document.body ? document.body.innerText : '').includes({})",
            serde_json::to_string(needle)?
        );
        let deadline = tokio::time::Instant::now() + timeout;
        while tokio::time::Instant::now() < deadline {
            if self
                .evaluate(&expression)
                .await
                .unwrap_or(Value::Bool(false))
                == Value::Bool(true)
            {
                return Ok(true);
            }
            tokio::time::sleep(Duration::from_millis(100)).await;
        }
        Ok(false)
    }

    /// Capture a PNG of the full page.
    pub async fn screenshot(&mut self) -> Result<Vec<u8>> {
        let result = self
            .call(
                "Page.captureScreenshot",
                json!({ "format": "png", "captureBeyondViewport": true }),
            )
            .await?;
        let encoded = result
            .get("data")
            .and_then(Value::as_str)
            .ok_or_else(|| CdpError::Protocol("screenshot returned no data".into()))?;
        base64::engine::general_purpose::STANDARD
            .decode(encoded)
            .map_err(|err| CdpError::Protocol(format!("screenshot was not valid base64: {err}")))
    }

    /// Evaluate a JavaScript expression and return its value.
    pub async fn eval(&mut self, expression: &str) -> Result<Value> {
        self.evaluate(expression).await
    }

    /// Close the page and terminate the browser.
    pub async fn close(self) -> Result<()> {
        self.process.shutdown().await
    }
}
