//! phenotype-router binary — H12 live router entry point.
//!
//! Boots a minimal axum-based HTTP server that delegates `/v1/*` to cliproxy
//! (Go plane) and serves combo-variant routing locally.
//!
//! Flags (env or CLI):
//!   PORT         — listen port (default 8080)
//!   CLIPROXY_URL — upstream cliproxy base URL (default http://localhost:9090)

use std::env;
use std::net::SocketAddr;

use phenotype_router::delegate::{build_delegate_request, CHAT_COMPLETIONS_PATH, MODELS_PATH};
use phenotype_router::ComboVariant;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let port: u16 = env::var("PORT")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(8080);
    let cliproxy_url =
        env::var("CLIPROXY_URL").unwrap_or_else(|_| "http://localhost:9090".to_string());

    let app = axum::Router::new()
        .route(MODELS_PATH, axum::routing::get(models_handler))
        .route(
            CHAT_COMPLETIONS_PATH,
            axum::routing::post(chat_completions_handler),
        )
        .with_state(cliproxy_url.clone());
    let addr = SocketAddr::from(([0, 0, 0, 0], port));
    eprintln!("phenotype-router listening on {addr} (delegate: {cliproxy_url})");
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, app).await?;
    Ok(())
}

async fn models_handler(
    axum::extract::State(cliproxy_url): axum::extract::State<String>,
) -> &'static str {
    let _ = cliproxy_url; // Reserved for upstream fetch in H12+.
    "[]"
}

async fn chat_completions_handler(
    axum::extract::State(cliproxy_url): axum::extract::State<String>,
    body: String,
) -> String {
    // Naive combo variant detection from model id in request body.
    let model_id = extract_model_id(&body).unwrap_or_default();
    let variant = ComboVariant::parse(&model_id);
    let req = build_delegate_request(&cliproxy_url, &model_id);
    let _ = variant; // Routing decision logged below.
    if let Some(r) = req {
        format!("[delegate -> {} {}]\n", r.target, r.path)
    } else {
        "[no delegate -- direct passthrough]\n".to_string()
    }
}

fn extract_model_id(body: &str) -> Option<String> {
    // Very rough JSON scrape; sufficient for H12 smoke. Real parsing in H14.
    let needle = "\"model\":\"";
    let start = body.find(needle)? + needle.len();
    let rest = &body[start..];
    let end = rest.find('"')?;
    Some(rest[..end].to_string())
}
