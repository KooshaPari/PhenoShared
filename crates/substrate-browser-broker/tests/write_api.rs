//! The daemon as the single lease authority: the mutation routes.
//!
//! Every test here talks real HTTP to a real `axum` server built from
//! `router_with`, so the thing under test is the router a `brokerd` process
//! actually serves. No browsers are required: leases are granted straight
//! through the authority, which is exactly the state a release, a reap or a
//! purge has to handle. The one test that does need a browser is named
//! `..._when_a_browser_is_available` and reports its skip instead of passing
//! silently.

use std::{
    collections::BTreeMap,
    sync::{
        atomic::{AtomicU64, Ordering},
        Arc,
    },
    time::Duration,
};

use serde_json::{json, Value};

use substrate_browser::{Clock, Lease};
use substrate_browser_broker::{router, router_with, Broker, Scope};

const TOKEN: &str = "correct-token";

/// A clock the test moves by hand, so expiry never needs a sleep.
#[derive(Clone)]
struct ManualClock(Arc<AtomicU64>);

impl ManualClock {
    fn new(now_unix_ms: u64) -> Self {
        Self(Arc::new(AtomicU64::new(now_unix_ms)))
    }

    fn set(&self, now_unix_ms: u64) {
        self.0.store(now_unix_ms, Ordering::SeqCst);
    }
}

impl Clock for ManualClock {
    fn now_unix_ms(&self) -> u64 {
        self.0.load(Ordering::SeqCst)
    }
}

/// Serve `app` on an ephemeral loopback port and return its base URL.
async fn serve(app: axum::Router) -> String {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .expect("bind an ephemeral port");
    let address = listener.local_addr().expect("local address");
    tokio::spawn(async move {
        let _ = axum::serve(listener, app).await;
    });
    format!("http://{address}")
}

/// POST `body` to `path`, optionally with a bearer token.
async fn post(
    base: &str,
    path: &str,
    token: Option<&str>,
    body: Value,
) -> (reqwest::StatusCode, Value) {
    let mut request = reqwest::Client::new()
        .post(format!("{base}{path}"))
        .json(&body);
    if let Some(token) = token {
        request = request.bearer_auth(token);
    }
    let response = request.send().await.expect("send the request");
    let status = response.status();
    let text = response.text().await.expect("read the body");
    (status, serde_json::from_str(&text).unwrap_or(Value::Null))
}

fn broker_in(dir: &tempfile::TempDir) -> Arc<Broker> {
    Arc::new(Broker::new(dir.path()).expect("broker"))
}

fn scope(principal: &str, profile: &str) -> Scope {
    Scope::new(principal, profile, "default").expect("valid scope")
}

/// Grant a lease straight through the authority: no browser is launched, which
/// is precisely the state a daemon restart leaves behind.
fn grant(broker: &Broker, principal: &str, profile: &str, ttl_ms: u64) -> Lease {
    broker
        .leases()
        .grant(
            &scope(principal, profile),
            "daemon-test",
            Duration::from_millis(ttl_ms),
        )
        .expect("grant a lease")
}

fn request_that_is_at_least_well_formed(lease: &Lease) -> Value {
    json!({ "fencing_token": lease.fencing_token })
}

#[tokio::test]
async fn every_mutation_route_requires_the_configured_token() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = broker_in(&dir);
    let lease = grant(&broker, "alice", "work", 60_000);
    broker
        .profiles()
        .ensure("alice", "work")
        .expect("materialise the profile");
    let profile_dir = broker.profiles().profile_dir("alice", "work");

    let base = serve(router(Arc::clone(&broker), Some(TOKEN.to_string()))).await;
    let acquired_id = lease.id.clone();
    let cases = [
        (
            "/v1/leases".to_string(),
            json!({ "principal": "alice", "profile": "work" }),
        ),
        (
            format!("/v1/leases/{acquired_id}/release"),
            request_that_is_at_least_well_formed(&lease),
        ),
        ("/v1/leases/reap".to_string(), json!({})),
        (
            "/v1/profiles/purge".to_string(),
            json!({ "principal": "alice", "profile": "work", "confirm": true }),
        ),
    ];

    for (path, body) in cases {
        let (status, payload) = post(&base, &path, None, body.clone()).await;
        assert_eq!(
            status,
            reqwest::StatusCode::UNAUTHORIZED,
            "{path} without a token must be 401, got {status}: {payload}"
        );
        assert_eq!(payload["error"], "unauthorised", "{path}: {payload}");

        let (status, payload) = post(&base, &path, Some("wrong-token"), body).await;
        assert_eq!(
            status,
            reqwest::StatusCode::UNAUTHORIZED,
            "{path} with the wrong token must be 401, got {status}: {payload}"
        );
        assert_eq!(payload["error"], "unauthorised", "{path}: {payload}");
    }

    // Nothing was mutated by any of the rejected calls.
    assert!(
        broker
            .leases()
            .validate(&lease.id, lease.fencing_token)
            .is_ok(),
        "the lease must survive unauthenticated release attempts"
    );
    assert!(
        profile_dir.exists(),
        "the profile must survive unauthenticated purge attempts"
    );
}

#[tokio::test]
async fn a_malformed_body_is_rejected_only_after_the_credential() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = broker_in(&dir);
    let base = serve(router(broker, Some(TOKEN.to_string()))).await;

    // No credential: 401, even though the body is nonsense. Parsing must never
    // happen before authentication.
    let (status, payload) = post(&base, "/v1/leases", None, json!({ "nonsense": 1 })).await;
    assert_eq!(status, reqwest::StatusCode::UNAUTHORIZED, "{payload}");

    // Credential valid: now the body is the problem, and the answer says so.
    let (status, payload) = post(&base, "/v1/leases", Some(TOKEN), json!({ "nonsense": 1 })).await;
    assert_eq!(status, reqwest::StatusCode::BAD_REQUEST, "{payload}");
    assert_eq!(payload["error"], "invalid");
}

#[tokio::test]
async fn release_with_the_right_fence_revokes_the_lease() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = broker_in(&dir);
    let lease = grant(&broker, "alice", "work", 60_000);
    let base = serve(router(Arc::clone(&broker), Some(TOKEN.to_string()))).await;

    let (status, payload) = post(
        &base,
        &format!("/v1/leases/{}/release", lease.id),
        Some(TOKEN),
        request_that_is_at_least_well_formed(&lease),
    )
    .await;

    assert_eq!(status, reqwest::StatusCode::OK, "{payload}");
    assert_eq!(payload["released"], true);
    assert_eq!(
        payload["teardown"], "no live session in this daemon; lease record revoked",
        "the daemon must say exactly what it tore down: {payload}"
    );
    assert!(
        broker.leases().list().expect("list leases").is_empty(),
        "the lease record must be gone"
    );
}

#[tokio::test]
async fn release_with_a_stale_fence_is_refused_and_tears_down_nothing() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = broker_in(&dir);
    let lease = grant(&broker, "alice", "work", 60_000);
    let base = serve(router(Arc::clone(&broker), Some(TOKEN.to_string()))).await;

    let (status, payload) = post(
        &base,
        &format!("/v1/leases/{}/release", lease.id),
        Some(TOKEN),
        json!({ "fencing_token": lease.fencing_token + 1 }),
    )
    .await;

    assert_eq!(
        status,
        reqwest::StatusCode::CONFLICT,
        "a wrong fence is a refusal, not a release: {payload}"
    );
    assert_eq!(payload["error"], "stale_fence", "{payload}");
    assert!(
        broker
            .leases()
            .validate(&lease.id, lease.fencing_token)
            .is_ok(),
        "the lease must still validate after a refused release"
    );
}

#[tokio::test]
async fn release_of_an_expired_lease_is_refused_and_keeps_the_record() {
    let dir = tempfile::tempdir().expect("temp dir");
    let clock = ManualClock::new(1_000_000);
    let broker = Arc::new(
        Broker::with_clock(dir.path(), Arc::new(clock.clone())).expect("broker with a clock"),
    );
    let lease = grant(&broker, "alice", "work", 1_000);
    // Past the 1 s TTL granted above.
    clock.set(1_001_001);
    let base = serve(router(Arc::clone(&broker), Some(TOKEN.to_string()))).await;

    let (status, payload) = post(
        &base,
        &format!("/v1/leases/{}/release", lease.id),
        Some(TOKEN),
        request_that_is_at_least_well_formed(&lease),
    )
    .await;

    assert_eq!(status, reqwest::StatusCode::CONFLICT, "{payload}");
    assert_eq!(payload["error"], "lease_unusable", "{payload}");
    assert_eq!(
        broker.leases().list().expect("list leases").len(),
        1,
        "an expired lease is reaped, never released"
    );
}

#[tokio::test]
async fn release_of_another_principals_lease_is_not_permitted() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = broker_in(&dir);
    let lease = grant(&broker, "alice", "work", 60_000);
    let tokens: BTreeMap<String, String> = [
        ("alice".to_string(), "tok-alice".to_string()),
        ("bob".to_string(), "tok-bob".to_string()),
    ]
    .into_iter()
    .collect();
    let base = serve(router_with(Arc::clone(&broker), None, tokens)).await;

    // Bob knows the lease id and the *correct* fence, and still may not release
    // it: the credential decides, not the token.
    let (status, payload) = post(
        &base,
        &format!("/v1/leases/{}/release", lease.id),
        Some("tok-bob"),
        request_that_is_at_least_well_formed(&lease),
    )
    .await;
    assert_eq!(
        status,
        reqwest::StatusCode::NOT_FOUND,
        "a cross-principal release must be 404, never 403: {payload}"
    );
    assert_eq!(
        payload["error"], "unknown_lease",
        "the refusal must not reveal that another principal's lease exists: {payload}"
    );
    assert!(
        broker
            .leases()
            .validate(&lease.id, lease.fencing_token)
            .is_ok(),
        "alice's lease must survive bob's attempt"
    );

    // Alice can.
    let (status, payload) = post(
        &base,
        &format!("/v1/leases/{}/release", lease.id),
        Some("tok-alice"),
        request_that_is_at_least_well_formed(&lease),
    )
    .await;
    assert_eq!(status, reqwest::StatusCode::OK, "{payload}");
    assert_eq!(payload["released"], true);
}

#[tokio::test]
async fn purge_without_confirm_is_refused() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = broker_in(&dir);
    broker
        .profiles()
        .ensure("alice", "work")
        .expect("materialise the profile");
    let profile_dir = broker.profiles().profile_dir("alice", "work");
    let base = serve(router(Arc::clone(&broker), Some(TOKEN.to_string()))).await;

    // Explicit false, and omitted entirely: both are "not confirmed".
    for body in [
        json!({ "principal": "alice", "profile": "work", "confirm": false }),
        json!({ "principal": "alice", "profile": "work" }),
    ] {
        let (status, payload) = post(&base, "/v1/profiles/purge", Some(TOKEN), body).await;
        assert_eq!(
            status,
            reqwest::StatusCode::BAD_REQUEST,
            "purge without confirmation must be refused: {payload}"
        );
        assert!(
            payload["detail"]
                .as_str()
                .is_some_and(|detail| detail.contains("confirm")),
            "the refusal must name the confirmation: {payload}"
        );
        assert!(profile_dir.exists(), "a refused purge must delete nothing");
    }
}

#[tokio::test]
async fn purge_while_the_profile_is_leased_is_refused() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = broker_in(&dir);
    broker
        .profiles()
        .ensure("alice", "work")
        .expect("materialise the profile");
    let profile_dir = broker.profiles().profile_dir("alice", "work");
    let lease = grant(&broker, "alice", "work", 60_000);
    let base = serve(router(Arc::clone(&broker), Some(TOKEN.to_string()))).await;

    let (status, payload) = post(
        &base,
        "/v1/profiles/purge",
        Some(TOKEN),
        json!({ "principal": "alice", "profile": "work", "confirm": true }),
    )
    .await;
    assert_eq!(
        status,
        reqwest::StatusCode::CONFLICT,
        "purging a leased profile must be refused: {payload}"
    );
    assert!(
        payload["detail"]
            .as_str()
            .is_some_and(|detail| detail.contains("leased")),
        "{payload}"
    );
    assert!(
        profile_dir.exists(),
        "a refused purge must delete nothing, including under an active lease"
    );

    // Once the lease is gone the same request succeeds.
    broker.leases().revoke(&lease.id).expect("revoke the lease");
    let (status, payload) = post(
        &base,
        "/v1/profiles/purge",
        Some(TOKEN),
        json!({ "principal": "alice", "profile": "work", "confirm": true }),
    )
    .await;
    assert_eq!(status, reqwest::StatusCode::OK, "{payload}");
    assert_eq!(payload["purged"], true, "{payload}");
    assert_eq!(payload["existed"], true, "{payload}");
    assert!(!profile_dir.exists(), "the profile data must be gone");
}

#[tokio::test]
async fn purge_of_a_missing_profile_reports_nothing_removed() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = broker_in(&dir);
    let base = serve(router(broker, Some(TOKEN.to_string()))).await;

    let (status, payload) = post(
        &base,
        "/v1/profiles/purge",
        Some(TOKEN),
        json!({ "principal": "nobody", "profile": "nothing", "confirm": true }),
    )
    .await;
    assert_eq!(status, reqwest::StatusCode::OK, "{payload}");
    assert_eq!(payload["purged"], false, "{payload}");
    assert_eq!(payload["existed"], false, "{payload}");
}

#[tokio::test]
async fn purge_of_another_principals_profile_is_not_permitted() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = broker_in(&dir);
    broker
        .profiles()
        .ensure("alice", "work")
        .expect("materialise the profile");
    let profile_dir = broker.profiles().profile_dir("alice", "work");
    let tokens: BTreeMap<String, String> = [
        ("alice".to_string(), "tok-alice".to_string()),
        ("bob".to_string(), "tok-bob".to_string()),
    ]
    .into_iter()
    .collect();
    let base = serve(router_with(Arc::clone(&broker), None, tokens)).await;

    let (status, payload) = post(
        &base,
        "/v1/profiles/purge",
        Some("tok-bob"),
        json!({ "principal": "alice", "profile": "work", "confirm": true }),
    )
    .await;
    assert_eq!(status, reqwest::StatusCode::NOT_FOUND, "{payload}");
    assert_eq!(payload["error"], "unknown_profile", "{payload}");
    assert!(profile_dir.exists(), "bob must not delete alice's profile");
}

#[tokio::test]
async fn reap_sweeps_expired_leases_and_reports_counts() {
    let dir = tempfile::tempdir().expect("temp dir");
    let clock = ManualClock::new(2_000_000);
    let broker = Arc::new(
        Broker::with_clock(dir.path(), Arc::new(clock.clone())).expect("broker with a clock"),
    );
    grant(&broker, "alice", "work", 1_000);
    grant(&broker, "bob", "work", 1_000);
    // Past the 1 s TTLs granted above.
    clock.set(2_001_001);
    let base = serve(router(Arc::clone(&broker), Some(TOKEN.to_string()))).await;

    let (status, payload) = post(&base, "/v1/leases/reap", Some(TOKEN), json!({})).await;
    assert_eq!(status, reqwest::StatusCode::OK, "{payload}");
    assert_eq!(payload["leases_reaped"], 2, "{payload}");
    assert_eq!(payload["reaped"], 0, "no browser sessions in this process");
    assert_eq!(payload["live_sessions_after"], 0, "{payload}");
    assert!(broker.leases().list().expect("list leases").is_empty());
}

#[tokio::test]
async fn reap_with_a_principal_scoped_token_is_refused() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = broker_in(&dir);
    let tokens: BTreeMap<String, String> = [("alice".to_string(), "tok-alice".to_string())]
        .into_iter()
        .collect();
    let base = serve(router_with(Arc::clone(&broker), None, tokens)).await;

    let (status, payload) = post(&base, "/v1/leases/reap", Some("tok-alice"), json!({})).await;
    assert_eq!(
        status,
        reqwest::StatusCode::FORBIDDEN,
        "reap is a global sweep, so a principal-scoped token may not run it: {payload}"
    );
    assert_eq!(payload["error"], "refused", "{payload}");
}

#[tokio::test]
async fn acquire_refuses_a_zero_ttl_and_a_leased_profile() {
    let dir = tempfile::tempdir().expect("temp dir");
    let broker = broker_in(&dir);
    let base = serve(router(Arc::clone(&broker), Some(TOKEN.to_string()))).await;

    let (status, payload) = post(
        &base,
        "/v1/leases",
        Some(TOKEN),
        json!({ "principal": "alice", "profile": "work", "ttl_ms": 0 }),
    )
    .await;
    assert_eq!(status, reqwest::StatusCode::BAD_REQUEST, "{payload}");
    assert!(
        payload["detail"]
            .as_str()
            .is_some_and(|detail| detail.contains("ttl_ms")),
        "{payload}"
    );

    // A profile already leased cannot be acquired twice, browser or not: the
    // exclusivity check runs before anything is launched.
    let lease = grant(&broker, "alice", "work", 60_000);
    let (status, payload) = post(
        &base,
        "/v1/leases",
        Some(TOKEN),
        json!({ "principal": "alice", "profile": "work" }),
    )
    .await;
    assert_eq!(status, reqwest::StatusCode::CONFLICT, "{payload}");
    assert_eq!(payload["error"], "refused", "{payload}");
    assert!(
        payload["detail"]
            .as_str()
            .is_some_and(|detail| detail.contains("already leased")),
        "{payload}"
    );
    assert_eq!(
        broker
            .leases()
            .validate(&lease.id, lease.fencing_token)
            .expect("the original lease is untouched")
            .holder,
        "daemon-test"
    );
}

#[tokio::test]
async fn acquire_then_release_over_http_when_a_browser_is_available() {
    if !substrate_browser_broker::browser_available() {
        eprintln!("skipping: no browser");
        return;
    }

    let dir = tempfile::tempdir().expect("temp dir");
    let broker = broker_in(&dir);
    let base = serve(router(Arc::clone(&broker), Some(TOKEN.to_string()))).await;

    let (status, payload) = post(
        &base,
        "/v1/leases",
        Some(TOKEN),
        json!({ "principal": "alice", "profile": "work", "ttl_ms": 120_000 }),
    )
    .await;
    assert_eq!(status, reqwest::StatusCode::OK, "{payload}");
    let lease_id = payload["id"].as_str().expect("lease id").to_string();
    let fencing_token = payload["fencing_token"].as_u64().expect("fence");
    assert!(
        payload["data_dir"]
            .as_str()
            .is_some_and(|dir| !dir.is_empty()),
        "the daemon must report where it put the browser: {payload}"
    );
    assert_eq!(
        broker.live().await.len(),
        1,
        "the daemon owns the session, not the caller"
    );

    let (status, payload) = post(
        &base,
        &format!("/v1/leases/{lease_id}/release"),
        Some(TOKEN),
        json!({ "fencing_token": fencing_token }),
    )
    .await;
    assert_eq!(status, reqwest::StatusCode::OK, "{payload}");
    assert_eq!(
        payload["teardown"], "browser closed; lease revoked; generation sealed",
        "{payload}"
    );
    assert!(
        broker.live().await.is_empty(),
        "release must leave no live session behind"
    );
}
