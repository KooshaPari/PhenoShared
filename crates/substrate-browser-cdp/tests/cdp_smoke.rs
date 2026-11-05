//! Live conformance smoke test against a real headless Chrome.
//!
//! These tests are the point of the crate: they fail if the provider cannot
//! actually launch a browser, read a page, act on it, and capture it. They are
//! skipped only when no Chrome binary exists.

use std::time::Duration;

use substrate_browser_cdp::{chrome_binary, CdpProvider};
use tokio::{
    io::{AsyncReadExt, AsyncWriteExt},
    net::TcpListener,
};

const FIXTURE: &str = r#"<!doctype html>
<html><head><title>Fixture</title></head>
<body>
  <h1>Hello fixture</h1>
  <button id="go" onclick="document.getElementById('out').textContent='clicked'">Go</button>
  <p id="out">idle</p>
  <form onsubmit="event.preventDefault(); document.getElementById('result').textContent='submitted:'+document.getElementById('q').value;">
    <input id="q" aria-label="Query" />
    <button type="submit">Send</button>
  </form>
  <p id="result"></p>
</body></html>"#;

/// Serve the fixture page once per connection on a loopback port.
async fn serve(html: &'static str) -> std::net::SocketAddr {
    let listener = TcpListener::bind("127.0.0.1:0").await.expect("bind");
    let addr = listener.local_addr().expect("addr");
    tokio::spawn(async move {
        loop {
            let Ok((mut socket, _)) = listener.accept().await else {
                break;
            };
            tokio::spawn(async move {
                let mut buffer = [0u8; 4096];
                let _ = socket.read(&mut buffer).await;
                let response = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\
                     Content-Length: {}\r\nConnection: close\r\n\r\n{}",
                    html.len(),
                    html
                );
                let _ = socket.write_all(response.as_bytes()).await;
                let _ = socket.shutdown().await;
            });
        }
    });
    addr
}

fn skip_reason() -> Option<String> {
    match chrome_binary() {
        Ok(binary) => {
            println!("using browser: {}", binary.display());
            None
        },
        Err(err) => Some(format!("skipping: {err}")),
    }
}

#[tokio::test]
async fn drives_a_real_page_end_to_end() {
    if let Some(reason) = skip_reason() {
        eprintln!("{reason}");
        return;
    }

    let addr = serve(FIXTURE).await;
    let dir = tempfile::tempdir().expect("tempdir");
    let mut provider = CdpProvider::launch(dir.path(), true).await.expect("launch");

    provider
        .open(&format!("http://{addr}/"))
        .await
        .expect("navigate");

    assert_eq!(provider.title().await.unwrap(), "Fixture");
    assert!(provider
        .url()
        .await
        .unwrap()
        .contains(&addr.port().to_string()));

    // Read: the accessibility tree must surface the heading and the controls.
    let snapshot = provider.snapshot().await.expect("snapshot");
    assert_eq!(snapshot.format, "jcode.page_snapshot.v1");
    assert!(
        snapshot.text.contains("Hello fixture"),
        "text was {:?}",
        snapshot.text
    );
    assert!(
        !snapshot.elements.is_empty(),
        "no actionable elements found"
    );

    // Act: click the button by reference and observe the effect.
    let button = snapshot
        .elements
        .iter()
        .find(|node| node.role == "button" && node.name == "Go")
        .expect("Go button");
    provider
        .click(button.element_ref.as_deref().unwrap())
        .await
        .expect("click");
    assert!(
        provider
            .wait_for_text("clicked", Duration::from_secs(5))
            .await
            .expect("wait"),
        "click had no observable effect"
    );

    // Type and submit.
    let after_click = provider.snapshot().await.expect("second snapshot");
    let textbox = after_click
        .elements
        .iter()
        .find(|node| node.role == "textbox")
        .expect("textbox");
    provider
        .type_into(textbox.element_ref.as_deref().unwrap(), "abc", true)
        .await
        .expect("type");
    assert!(
        provider
            .wait_for_text("submitted:abc", Duration::from_secs(5))
            .await
            .expect("wait"),
        "submit had no observable effect"
    );

    // Evaluate and capture.
    assert_eq!(provider.eval("1+1").await.unwrap(), serde_json::json!(2));
    let png = provider.screenshot().await.expect("screenshot");
    assert!(png.len() > 100, "screenshot too small: {}", png.len());
    assert_eq!(&png[..8], b"\x89PNG\r\n\x1a\n", "not a PNG");

    provider.close().await.expect("close");
}

#[tokio::test]
async fn two_browsers_on_separate_data_dirs_do_not_share_storage() {
    if let Some(reason) = skip_reason() {
        eprintln!("{reason}");
        return;
    }

    let addr = serve("<html><head><title>Store</title></head><body>x</body></html>").await;
    let first_dir = tempfile::tempdir().expect("tempdir");
    let second_dir = tempfile::tempdir().expect("tempdir");

    let mut first = CdpProvider::launch(first_dir.path(), true)
        .await
        .expect("first");
    first.open(&format!("http://{addr}/")).await.expect("open");
    first
        .eval("localStorage.setItem('token','alice')")
        .await
        .expect("set");

    let mut second = CdpProvider::launch(second_dir.path(), true)
        .await
        .expect("second");
    second.open(&format!("http://{addr}/")).await.expect("open");
    let seen = second
        .eval("localStorage.getItem('token')")
        .await
        .expect("get");

    assert_eq!(
        seen,
        serde_json::Value::Null,
        "a second data directory must not observe the first profile's storage"
    );

    first.close().await.expect("close first");
    second.close().await.expect("close second");
}
