use session_ledger::domain::bundle::{Bundle, BundleKind, ContinuationBundle};
use session_ledger::domain::session::{Corpus, Message, Role, Session};

/// Build a set of sample compiled bundles for development / demo purposes.
#[must_use]
pub fn sample_bundles() -> Vec<ContinuationBundle> {
    vec![
        ContinuationBundle {
            source_id: "forge-session-001".into(),
            bundles: vec![
                Bundle::new(
                    BundleKind::Acceptance,
                    serde_json::json!({
                        "ready": true,
                        "scope_sized": true,
                        "user_turns": 5,
                    }),
                ),
                Bundle::new(
                    BundleKind::Intent,
                    serde_json::json!({
                        "goal": "Fix login timeout regression after auth refactor",
                        "acceptance_signals": [
                            "all existing auth tests pass",
                            "session expiry extends beyond 30 min",
                            "user story AC-417 verified",
                        ],
                        "constraints": ["must not touch password reset flow", "must preserve MFA"],
                        "user_turn_count": 5,
                    }),
                ),
                Bundle::new(
                    BundleKind::Context,
                    serde_json::json!({
                        "cwd": "/home/dev/auth-service",
                        "title": "Login timeout fix",
                    }),
                ),
                Bundle::new(
                    BundleKind::Contract,
                    serde_json::json!({
                        "skipped_by": ["existing auth tests pass"],
                        "watch_files": ["src/auth/session.rs"],
                    }),
                ),
            ],
        },
        ContinuationBundle {
            source_id: "codex-session-003".into(),
            bundles: vec![
                Bundle::new(
                    BundleKind::Acceptance,
                    serde_json::json!({
                        "ready": true,
                        "scope_sized": true,
                        "user_turns": 12,
                    }),
                ),
                Bundle::new(
                    BundleKind::Intent,
                    serde_json::json!({
                        "goal": "Add usage-based billing to the API proxy layer",
                        "acceptance_signals": [
                            "stripe integration complete",
                            "rate limit headers reflect remaining quota",
                            "billing dashboard renders for admin users",
                        ],
                        "constraints": ["no credit card required for dev tier", "must log all billing events"],
                        "user_turn_count": 12,
                    }),
                ),
                Bundle::new(
                    BundleKind::Context,
                    serde_json::json!({
                        "cwd": "/home/dev/api-gateway",
                        "title": "Usage billing",
                    }),
                ),
                Bundle::new(
                    BundleKind::Contract,
                    serde_json::json!({
                        "skipped_by": ["existing billing tests pass"],
                        "watch_files": ["src/middleware/usage.rs", "src/billing/"],
                    }),
                ),
            ],
        },
        ContinuationBundle {
            source_id: "claude-session-007".into(),
            bundles: vec![
                Bundle::new(
                    BundleKind::Acceptance,
                    serde_json::json!({
                        "ready": true,
                        "scope_sized": true,
                        "user_turns": 3,
                    }),
                ),
                Bundle::new(
                    BundleKind::Intent,
                    serde_json::json!({
                        "goal": "Update CI pipeline to use self-hosted runner for ARM builds",
                        "acceptance_signals": [
                            "ARM artifacts publish to GHCR",
                            "build time under 15 min",
                            "x86_64 builds unaffected",
                        ],
                        "constraints": ["do not modify existing x86_64 workflow matrix", "runner must be ephemeral"],
                        "user_turn_count": 3,
                    }),
                ),
                Bundle::new(
                    BundleKind::Context,
                    serde_json::json!({
                        "cwd": "/home/dev/infra",
                        "title": "ARM CI runner",
                    }),
                ),
            ],
        },
    ]
}

/// Build sample normalized sessions for the history timeline.
#[must_use]
pub fn sample_sessions() -> Vec<Session> {
    vec![
        {
            let mut s = Session::new("forge-session-001", Corpus::Forge);
            s.cwd = Some("/home/dev/auth-service".into());
            s.title = Some("Login timeout fix".into());
            s.messages = vec![
                Message {
                    role: Role::User,
                    content:
                        "The login session keeps expiring after 5 minutes, we need to fix this."
                            .into(),
                    ts_ms: Some(1_716_000_000_000),
                },
                Message {
                    role: Role::Assistant,
                    content: "Let me trace the auth middleware to find where the TTL is set."
                        .into(),
                    ts_ms: Some(1_716_000_030_000),
                },
                Message {
                    role: Role::Assistant,
                    content:
                        "Found it — the session TTL is hardcoded to 300s in src/auth/session.rs."
                            .into(),
                    ts_ms: Some(1_716_000_060_000),
                },
                Message {
                    role: Role::User,
                    content: "Increase it to 1800s and make sure MFA is preserved.".into(),
                    ts_ms: Some(1_716_000_090_000),
                },
                Message {
                    role: Role::Assistant,
                    content: "Done. TTL bumped, all existing auth tests pass.".into(),
                    ts_ms: Some(1_716_000_150_000),
                },
                Message {
                    role: Role::User,
                    content: "Looks good, tests pass. Ship it.".into(),
                    ts_ms: Some(1_716_000_200_000),
                },
            ];
            s
        },
        {
            let mut s = Session::new("codex-session-003", Corpus::Codex);
            s.cwd = Some("/home/dev/api-gateway".into());
            s.title = Some("Usage billing".into());
            s.messages = vec![
                Message {
                    role: Role::User,
                    content: "We need usage-based billing in the API proxy layer.".into(),
                    ts_ms: Some(1_717_000_000_000),
                },
                Message {
                    role: Role::Assistant,
                    content: "I'll design the middleware pipeline — rate limiter + counter.".into(),
                    ts_ms: Some(1_717_000_030_000),
                },
                Message {
                    role: Role::User,
                    content:
                        "Integrate Stripe for payments but no credit card required for dev tier."
                            .into(),
                    ts_ms: Some(1_717_000_080_000),
                },
                Message {
                    role: Role::Assistant,
                    content: "Stripe integration done. Dev tier exempted.".into(),
                    ts_ms: Some(1_717_000_150_000),
                },
                Message {
                    role: Role::User,
                    content: "Make sure rate limit headers reflect remaining quota.".into(),
                    ts_ms: Some(1_717_000_200_000),
                },
                Message {
                    role: Role::Assistant,
                    content: "Headers added. Billing dashboard renders for admins.".into(),
                    ts_ms: Some(1_717_000_280_000),
                },
                Message {
                    role: Role::User,
                    content: "Approved, ship it.".into(),
                    ts_ms: Some(1_717_000_350_000),
                },
            ];
            s
        },
        {
            let mut s = Session::new("claude-session-007", Corpus::ClaudeCode);
            s.cwd = Some("/home/dev/infra".into());
            s.title = Some("ARM CI runner".into());
            s.messages = vec![
                Message {
                    role: Role::User,
                    content: "Can we add ARM builds to the CI pipeline?".into(),
                    ts_ms: Some(1_718_000_000_000),
                },
                Message {
                    role: Role::Assistant,
                    content: "I'll set up a self-hosted ARM runner via GitHub Actions.".into(),
                    ts_ms: Some(1_718_000_025_000),
                },
                Message {
                    role: Role::User,
                    content: "Make sure x86_64 builds are unaffected and runner is ephemeral."
                        .into(),
                    ts_ms: Some(1_718_000_060_000),
                },
                Message {
                    role: Role::Assistant,
                    content: "Done. ARM artifacts now publish to GHCR. Build time under 10 min."
                        .into(),
                    ts_ms: Some(1_718_000_110_000),
                },
                Message {
                    role: Role::User,
                    content: "All good, thanks.".into(),
                    ts_ms: Some(1_718_000_140_000),
                },
            ];
            s
        },
    ]
}
