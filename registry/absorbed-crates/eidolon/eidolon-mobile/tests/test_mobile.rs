//! Unit tests for eidolon-mobile.
//!
//! Tests use `Arc<dyn MobileAutomator>` to call trait methods on `MobileClient`.

use eidolon_core::traits::MobileAutomator;
use eidolon_core::AutomationEvent;
use eidolon_mobile::MobileClient;
use std::sync::Arc;

fn make_client(platform: &str) -> Arc<dyn MobileAutomator> {
    Arc::new(MobileClient::new(platform))
}

#[tokio::test]
async fn get_viewport_mobile_fhd() {
    let client = make_client("ios");
    let viewport = client.get_viewport().await.unwrap();
    assert_eq!(viewport.width, 1080);
    assert_eq!(viewport.height, 1920);
    assert_eq!(viewport.dpr, 2.0);
    assert_eq!(viewport.orientation, "portrait");
}

#[tokio::test]
async fn get_viewport_cross_platform() {
    for platform in ["ios", "android"] {
        let client = make_client(platform);
        let viewport = client.get_viewport().await.unwrap();
        assert_eq!(viewport.width, 1080);
        assert_eq!(viewport.height, 1920);
        assert_eq!(viewport.dpr, 2.0);
    }
}

#[tokio::test]
async fn screenshot_returns_ok() {
    let client = make_client("ios");
    let result = client.screenshot("/tmp/mobile-screen.png").await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn screenshot_different_paths() {
    let client = make_client("android");
    for path in ["/dcim/screen.png", "/Pictures/s.png", "screen.png"] {
        let result = client.screenshot(path).await;
        assert!(result.is_ok(), "screenshot({path}) should succeed");
    }
}

#[tokio::test]
async fn tap_returns_ok() {
    let client = make_client("ios");
    let result = client.tap(540, 960).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn tap_corner_coordinates() {
    let client = make_client("ios");
    assert!(client.tap(0, 0).await.is_ok());
    assert!(client.tap(1079, 0).await.is_ok());
    assert!(client.tap(0, 1919).await.is_ok());
    assert!(client.tap(1079, 1919).await.is_ok());
}

#[tokio::test]
async fn swipe_returns_ok() {
    let client = make_client("ios");
    let result = client.swipe(540, 960, 600, 1000).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn swipe_horizontal() {
    let client = make_client("android");
    assert!(client.swipe(100, 960, 980, 960).await.is_ok());
}

#[tokio::test]
async fn swipe_vertical() {
    let client = make_client("ios");
    assert!(client.swipe(540, 100, 540, 1820).await.is_ok());
}

#[tokio::test]
async fn swipe_short_vs_long() {
    let client = make_client("android");
    assert!(client.swipe(540, 960, 545, 965).await.is_ok());
    assert!(client.swipe(540, 960, 100, 1900).await.is_ok());
}

#[tokio::test]
async fn input_text_returns_ok() {
    let client = make_client("ios");
    let result = client.input_text("hello").await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn input_text_unicode() {
    let client = make_client("android");
    let result = client.input_text("こんにちは世界 🌍").await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn input_text_empty() {
    let client = make_client("ios");
    let result = client.input_text("").await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn input_text_long_text() {
    let client = make_client("android");
    let long_text = "a".repeat(10000);
    let result = client.input_text(&long_text).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn record_event_returns_ok() {
    let client = make_client("ios");
    let event = AutomationEvent::screenshot("mobile", "/tmp/screen.png");
    let result = client.record_event(event).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn all_methods_chained() {
    let client = make_client("ios");
    assert!(client.get_viewport().await.is_ok());
    assert!(client.screenshot("/tmp/s.png").await.is_ok());
    assert!(client.tap(100, 200).await.is_ok());
    assert!(client.swipe(100, 200, 300, 400).await.is_ok());
    assert!(client.input_text("test").await.is_ok());
    assert!(client
        .record_event(AutomationEvent::screenshot("ios", "/s.png"))
        .await
        .is_ok());
}

#[tokio::test]
async fn viewport_dimensions_positive() {
    let client = make_client("ios");
    let v = client.get_viewport().await.unwrap();
    assert!(v.width > 0);
    assert!(v.height > 0);
    assert!(v.dpr > 0.0);
}

#[tokio::test]
async fn mobile_client_is_send_sync() {
    fn assert_send_sync<T: Send + Sync>() {}
    assert_send_sync::<MobileClient>();
}
