//! Unit tests for eidolon-sandbox.
//!
//! Tests use `Arc<dyn SandboxAutomator>` to call trait methods on `SandboxClient`.
//!
//! # Two-layer test surface
//!
//! 1. The original 19 lifecycle / metadata / exec tests are kept (with
//!    `SandboxClient::new` updated to return `Result` and the
//!    `exec_empty_command` test rewritten to assert rejection — see
//!    [`validate_exec_cmd`](eidolon_core::security::validate_exec_cmd)
//!    for the rule).
//! 2. The new [`security`] module adds explicit rejection tests for
//!    shell metacharacter injection, NUL-byte injection, leading-dash
//!    argv confusion, oversized ids / commands, and shell-script-shaped
//!    strings — the L20 / L24 / L25 audit findings.

use eidolon_core::error::PhenoError;
use eidolon_core::security::{
    validate_exec_cmd, validate_sandbox_id, NetworkPolicy, SandboxPolicy, EXEC_CMD_MAX_LEN,
    SANDBOX_ID_MAX_LEN,
};
use eidolon_core::traits::SandboxAutomator;
use eidolon_core::AutomationEvent;
use eidolon_sandbox::SandboxClient;
use std::sync::Arc;

fn make_client(sandbox_id: &str) -> Arc<dyn SandboxAutomator> {
    Arc::new(SandboxClient::new(sandbox_id).expect("test sandbox_id must validate"))
}

#[tokio::test]
async fn get_metadata_returns_sandbox_metadata() {
    let client = make_client("test-sandbox");
    let meta = client.get_metadata().await.unwrap();
    assert_eq!(meta.id, "test-sandbox");
    assert_eq!(meta.image, "stub:latest");
    // Defaults now flow from `SandboxPolicy::default()` (2 vCPU / 512 MiB
    // RAM / 5120 MiB disk).
    assert_eq!(meta.cpu_limit, 2);
    assert_eq!(meta.memory_limit_mb, 512);
    assert!(meta.disk_limit_mb.is_some());
    assert_eq!(meta.disk_limit_mb.unwrap(), 5120);
}

#[tokio::test]
async fn get_metadata_id_matches_client() {
    for id in ["sbox-1", "nano-abc", "docker-xyz"] {
        let client = make_client(id);
        let meta = client.get_metadata().await.unwrap();
        assert_eq!(meta.id, id);
    }
}

#[tokio::test]
async fn get_metadata_disk_limit() {
    let client = make_client("test-disk");
    let meta = client.get_metadata().await.unwrap();
    assert!(meta.disk_limit_mb.is_some());
    assert!(*meta.disk_limit_mb.as_ref().unwrap() > 0);
}

#[tokio::test]
async fn get_metadata_reflects_explicit_policy() {
    let policy = SandboxPolicy {
        cpu_cores: 8,
        memory_mib: 4096,
        disk_mib: Some(20_480),
        network: NetworkPolicy::Allow,
    };
    let client = SandboxClient::with_policy("test-policy", policy.clone())
        .expect("with_policy must accept a valid id");
    let meta = client.get_metadata().await.unwrap();
    assert_eq!(meta.cpu_limit, 8);
    assert_eq!(meta.memory_limit_mb, 4096);
    assert_eq!(meta.disk_limit_mb, Some(20_480));
    assert_eq!(client.policy(), &policy);
}

#[tokio::test]
async fn start_returns_ok() {
    let client = make_client("test-start");
    let result = client.start().await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn start_idempotent() {
    let client = make_client("test-idempotent");
    assert!(client.start().await.is_ok());
    assert!(client.start().await.is_ok());
    assert!(client.start().await.is_ok());
}

#[tokio::test]
async fn stop_returns_ok() {
    let client = make_client("test-stop");
    let result = client.stop().await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn stop_idempotent() {
    let client = make_client("test-stop-idempotent");
    assert!(client.stop().await.is_ok());
    assert!(client.stop().await.is_ok());
}

#[tokio::test]
async fn start_stop_sequence() {
    let client = make_client("test-seq");
    assert!(client.start().await.is_ok());
    assert!(client.stop().await.is_ok());
}

#[tokio::test]
async fn exec_returns_output() {
    let client = make_client("test-exec");
    let output = client.exec("echo hello").await.unwrap();
    assert_eq!(output, "stub output");
}

#[tokio::test]
async fn exec_different_commands() {
    let client = make_client("test-exec2");
    for cmd in ["ls -la", "cat /etc/hostname", "whoami", "pwd", "date"] {
        let result = client.exec(cmd).await;
        assert!(result.is_ok(), "exec({cmd}) should succeed");
        assert_eq!(result.unwrap(), "stub output");
    }
}

#[tokio::test]
async fn exec_empty_command_is_rejected() {
    // Post-validation contract: an empty cmd is malformed input and
    // must surface as `PhenoError::BadRequest`. The previous (pre-p3)
    // impl accepted it silently — that was the L20 audit finding.
    let client = make_client("test-empty-cmd");
    let err = client.exec("").await.unwrap_err();
    assert!(
        matches!(err, PhenoError::BadRequest(_)),
        "empty exec must be BadRequest, got {err:?}"
    );
}

#[tokio::test]
async fn exec_long_command() {
    // 1005 bytes — under the 4096-byte cap, so still accepted.
    let client = make_client("test-long-cmd");
    let long_cmd = "echo ".to_string() + &"x".repeat(1000);
    let result = client.exec(&long_cmd).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn exec_over_limit_command_is_rejected() {
    let client = make_client("test-over-limit");
    let cmd = "a".repeat(EXEC_CMD_MAX_LEN + 1);
    let err = client.exec(&cmd).await.unwrap_err();
    assert!(matches!(err, PhenoError::BadRequest(_)));
}

#[tokio::test]
async fn exec_rejects_nul_byte() {
    let client = make_client("test-nul");
    let err = client.exec("echo\0hello").await.unwrap_err();
    assert!(
        matches!(err, PhenoError::BadRequest(_)),
        "NUL byte must be BadRequest, got {err:?}"
    );
}

#[tokio::test]
async fn exec_rejects_newline() {
    let client = make_client("test-newline");
    let err = client.exec("echo hi\necho bye").await.unwrap_err();
    assert!(matches!(err, PhenoError::BadRequest(_)));
}

#[tokio::test]
async fn exec_rejects_shell_injection_as_forbidden() {
    // All four of these are the canonical "shell injection through a
    // stringly-typed API" shapes; they must be rejected with
    // `Forbidden` (policy), not `BadRequest` (malformed).
    let client = make_client("test-inject");
    for cmd in [
        "echo hi && rm -rf /",
        "cat /etc/passwd > out.txt",
        "echo $(reboot)",
        "echo `id`",
        "echo a; echo b",
        "echo a || echo b",
        "echo a | grep b",
    ] {
        let err = client.exec(cmd).await.unwrap_err();
        assert!(
            matches!(err, PhenoError::Forbidden(_)),
            "injection {cmd:?} must be Forbidden, got {err:?}"
        );
    }
}

#[tokio::test]
async fn resource_usage_returns_usage() {
    let client = make_client("test-resource");
    let usage = client.resource_usage().await.unwrap();
    assert_eq!(usage.cpu_percent, 0.0);
    assert_eq!(usage.memory_mb, 128);
    assert!(usage.disk_mb.is_some());
    assert_eq!(usage.disk_mb.unwrap(), 512);
}

#[tokio::test]
async fn resource_usage_stub_values() {
    let client = make_client("test-resource2");
    let usage = client.resource_usage().await.unwrap();
    assert_eq!(usage.cpu_percent, 0.0_f64);
    assert_eq!(usage.memory_mb, 128);
    assert_eq!(usage.disk_mb, Some(512));
}

#[tokio::test]
async fn resource_usage_positive_values() {
    let client = make_client("test-res-pos");
    let usage = client.resource_usage().await.unwrap();
    assert!(usage.memory_mb > 0);
    assert!(usage.disk_mb.is_none() || *usage.disk_mb.as_ref().unwrap() > 0);
}

#[tokio::test]
async fn record_event_returns_ok() {
    let client = make_client("test-record");
    let event = AutomationEvent::screenshot("sandbox", "/sandbox/screen.png");
    let result = client.record_event(event).await;
    assert!(result.is_ok());
}

#[tokio::test]
async fn full_lifecycle() {
    let client = make_client("test-lifecycle");
    assert!(client.get_metadata().await.is_ok());
    assert!(client.start().await.is_ok());
    assert!(client.exec("ls").await.is_ok());
    assert!(client.resource_usage().await.is_ok());
    assert!(client.stop().await.is_ok());
    let end_event = AutomationEvent::screenshot("sandbox", "/end.png");
    assert!(client.record_event(end_event).await.is_ok());
}

#[tokio::test]
async fn multiple_clients_independent() {
    let client1 = make_client("sandbox-1");
    let client2 = make_client("sandbox-2");
    assert!(client1.start().await.is_ok());
    assert!(client2.start().await.is_ok());
    // Verify they are distinct instances by checking metadata differs
    let meta1 = client1.get_metadata().await.unwrap();
    let meta2 = client2.get_metadata().await.unwrap();
    assert_ne!(meta1.id, meta2.id);
}

#[tokio::test]
async fn sandbox_client_is_send_sync() {
    fn assert_send_sync<T: Send + Sync>() {}
    assert_send_sync::<SandboxClient>();
}

// ---------------------------------------------------------------------------
// L20 / L24 / L25 — sandbox_id validation at the constructor boundary
// ---------------------------------------------------------------------------

#[test]
fn new_rejects_empty_sandbox_id() {
    let err = SandboxClient::new("").unwrap_err();
    assert!(
        matches!(err, PhenoError::BadRequest(_)),
        "empty id must be BadRequest, got {err:?}"
    );
}

#[test]
fn new_rejects_oversized_sandbox_id() {
    let id = "a".repeat(SANDBOX_ID_MAX_LEN + 1);
    let err = SandboxClient::new(&id).unwrap_err();
    assert!(matches!(err, PhenoError::BadRequest(_)));
}

#[test]
fn new_rejects_leading_dash() {
    // Classic argv-confusion guard: `--rm` / `-rf` style ids would be
    // misinterpreted by a CLI wrapper, so the validator refuses.
    let err = SandboxClient::new("--flag").unwrap_err();
    assert!(matches!(err, PhenoError::BadRequest(_)));
}

#[test]
fn new_rejects_shell_metachars_in_id() {
    for bad in [
        "a;b", "a&b", "a|b", "a$b", "a`b", "a/b", "a\\b", "a:b", "a*b",
    ] {
        let err = SandboxClient::new(bad).unwrap_err();
        assert!(
            matches!(err, PhenoError::BadRequest(_)),
            "id {bad:?} must be BadRequest, got {err:?}"
        );
    }
}

#[test]
fn with_policy_rejects_invalid_id() {
    // The same id gate must apply regardless of the policy argument.
    let err = SandboxClient::with_policy("", SandboxPolicy::default()).unwrap_err();
    assert!(matches!(err, PhenoError::BadRequest(_)));
}

// ---------------------------------------------------------------------------
// Direct tests against the security primitives (no SandboxClient involved)
// ---------------------------------------------------------------------------

#[test]
fn validate_sandbox_id_round_trip_smoke() {
    assert!(validate_sandbox_id("docker-7c9f").is_ok());
}

#[test]
fn validate_exec_cmd_round_trip_smoke() {
    assert!(validate_exec_cmd("ls -la /tmp").is_ok());
}
