use std::net::SocketAddr;
use axum::{routing::get, Router};
use tower_http::services::ServeDir;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    tracing_subscriber::fmt().init();

    let port = std::env::var("AGILEPLUS_DASHBOARD_PORT")
        .ok()
        .and_then(|p| p.parse::<u16>().ok())
        .unwrap_or(3000);

    let app = Router::new()
        .route("/", get(|| async {
            r#"<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>AgilePlus Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0a0c0f; color: #e0e0e0; }
        .container { max-width: 1200px; margin: 0 auto; padding: 2rem; }
        header { border-bottom: 1px solid #333; padding-bottom: 1rem; margin-bottom: 2rem; }
        h1 { color: #7ebab5; font-size: 2rem; margin-bottom: 0.5rem; }
        .subtitle { color: #888; font-size: 0.9rem; }
        .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; margin-top: 2rem; }
        .card { background: #1a1d21; border: 1px solid #333; border-radius: 8px; padding: 1.5rem; }
        .card h2 { color: #7ebab5; font-size: 1.1rem; margin-bottom: 0.5rem; }
        .card p { color: #aaa; font-size: 0.95rem; line-height: 1.5; }
        .status { color: #4ade80; font-size: 0.85rem; margin-top: 1rem; }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>AgilePlus Dashboard</h1>
            <p class="subtitle">Spec-first project management platform</p>
        </header>
        <div class="grid">
            <div class="card">
                <h2>Features</h2>
                <p>Track features, work packages, and cycles with full spec-to-shipped traceability.</p>
                <div class="status">Ready to connect</div>
            </div>
            <div class="card">
                <h2>Workspace</h2>
                <p>Manage projects, modules, and cross-team dependencies.</p>
                <div class="status">Ready to connect</div>
            </div>
            <div class="card">
                <h2>Services</h2>
                <p>Monitor health and performance of connected services.</p>
                <div class="status">Ready to connect</div>
            </div>
            <div class="card">
                <h2>Settings</h2>
                <p>Configure dashboard views, notifications, and integrations.</p>
                <div class="status">Ready to connect</div>
            </div>
        </div>
        <p style="margin-top: 3rem; color: #666; text-align: center; font-size: 0.85rem;">
            AgilePlus Dashboard · Running on localhost:{{ port }}
        </p>
    </div>
</body>
</html>"#
        }))
        .fallback(get(|| async { "404 Not Found" }));

    let addr = SocketAddr::from(([127, 0, 0, 1], port));
    let listener = tokio::net::TcpListener::bind(addr).await?;
    println!("AgilePlus Dashboard listening on http://127.0.0.1:{}", port);
    axum::serve(listener, app).await?;
    Ok(())
}
