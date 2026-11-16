use std::time::Duration;

#[tokio::test]
async fn probe() {
    let tok = std::env::var("PROBE_TOKEN").unwrap_or_default();
    std::env::set_var("BROKERD_URL", "http://127.0.0.1:8788");
    std::env::set_var("BROKERD_TOKEN", &tok);
    let cfg = substrate_browser_mcp::RemoteConfig::from_env();
    match cfg {
        Some(c) => println!("PROBE config present base_url={:?}", c),
        None => println!("PROBE config is None - BROKERD_URL not seen"),
    }
    // Raw reqwest with the SAME builder, for comparison.
    let c = reqwest::Client::builder()
        .connect_timeout(Duration::from_secs(3))
        .timeout(Duration::from_secs(10))
        .build().unwrap();
    match c.get("http://127.0.0.1:8788/healthz").send().await {
        Ok(r) => println!("PROBE raw GET status={}", r.status()),
        Err(e) => {
            println!("PROBE raw GET ERR {e}");
            let mut s: Option<&(dyn std::error::Error + 'static)> = std::error::Error::source(&e);
            while let Some(x) = s { println!("PROBE raw GET  src={x}"); s = x.source(); }
        }
    }
}
