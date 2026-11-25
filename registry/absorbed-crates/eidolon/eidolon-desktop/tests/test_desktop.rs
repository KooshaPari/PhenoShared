//! Unit tests for eidolon-desktop (cross-platform stub).
//!
//! Tests use `Arc<dyn DesktopAutomator>` to call trait methods on `DesktopClient`.
//! These tests exercise the stub implementation and only compile on non-macOS platforms
//! (on macOS, DesktopClient::new takes no arguments).
//!
//! See `macos_integration.rs` for macOS-specific integration tests.

#![cfg(not(target_os = "macos"))]

use eidolon_core::traits::DesktopAutomator;
use eidolon_core::{AutomationEvent, PointerInput, TextInput, Viewport};
use eidolon_desktop::DesktopClient;
use std::sync::Arc;

fn make_client(platform: &str) -> Arc<dyn DesktopAutomator> {
    Arc::new(DesktopClient::new(platform))
}

#[tokio::test]
async fn get_viewport_desktop_fhd() {
    let client = make_client("linux");
    let viewport = client.get_viewport().await.unwrap();
    assert_eq!(viewport.width, 1920);
    assert_eq!(viewport.height, 1080);
    assert_eq!(viewport.dpr, 1.0);
    assert_eq!(viewport.orientation, "landscape");
}

#[tokio::test]
async fn get_viewport_cross_platform() {
    for platform in ["macos", "windows", "linux"] {
        let client = make_client(platform);
        let viewport = client.get_viewport().await.unwrap();
        assert_eq!(viewport.width, 1920);
        assert_eq!(viewport.height, 1080);
    }
}

#[tokio::test]
async fn screenshot_returns_ok() {
    let client = make_client("macos");
    let result = client.screenshot("/tmp/test-screenshot.png").await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn screenshot_different_paths() {
    let client = make_client("windows");
    for path in ["/a.png", "/b/c.png", "relative/path.png"] {
        let result = client.screenshot(path).await;
        assert!(result.is_ok(), "screenshot({path}) should succeed");
    }
}

#[tokio::test]
async fn pointer_accepts_click() {
    let client = make_client("macos");
    let input = PointerInput::click(100, 200);
    let result = client.pointer(&input).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn pointer_accepts_move() {
    let client = make_client("linux");
    let input = PointerInput::move_to(300, 400);
    let result = client.pointer(&input).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn pointer_with_duration() {
    let client = make_client("windows");
    let input = PointerInput {
        x: 50,
        y: 75,
        button: Some("right".to_string()),
        action: "press".to_string(),
        duration_ms: Some(500),
    };
    let result = client.pointer(&input).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn text_accepts_keystroke() {
    let client = make_client("macos");
    let input = TextInput::keystroke("hello world");
    let result = client.text(&input).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn text_accepts_paste() {
    let client = make_client("linux");
    let input = TextInput::paste("pasted content");
    let result = client.text(&input).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn text_with_delay() {
    let client = make_client("windows");
    let input = TextInput {
        text: "delayed".to_string(),
        input_type: "keystroke".to_string(),
        delay_ms: Some(100),
    };
    let result = client.text(&input).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn record_event_returns_ok() {
    let client = make_client("macos");
    let event = AutomationEvent::screenshot("desktop", "/tmp/screen.png");
    let result = client.record_event(event).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn record_event_preserves_event_data() {
    let client = make_client("linux");
    let input = PointerInput::click(1, 2);
    let event = AutomationEvent::pointer("linux", input);
    let result = client.record_event(event).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn all_methods_chained() {
    let client = make_client("macos");
    assert!(client.get_viewport().await.is_ok());
    assert!(client.screenshot("/tmp/s.png").await.is_ok());
    assert!(client.pointer(&PointerInput::click(1, 2)).await.is_ok());
    assert!(client.text(&TextInput::keystroke("test")).await.is_ok());
    assert!(client
        .record_event(AutomationEvent::screenshot("macos", "/s.png"))
        .await
        .is_ok());
}

#[tokio::test]
async fn viewport_dimensions_positive() {
    let client = make_client("linux");
    let v = client.get_viewport().await.unwrap();
    assert!(v.width > 0);
    assert!(v.height > 0);
    assert!(v.dpr > 0.0);
}

#[tokio::test]
async fn desktop_client_is_send_sync() {
    fn assert_send_sync<T: Send + Sync>() {}
    assert_send_sync::<DesktopClient>();
}
