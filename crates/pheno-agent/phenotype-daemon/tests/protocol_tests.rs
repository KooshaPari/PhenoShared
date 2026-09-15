//! Protocol-level integration tests: BufferPool, ConnectionStats,
//! VersionInfo, Request/Response serialization roundtrips.

use bytes::BytesMut;
use phenotype_daemon::protocol::{BufferPool, ConnectionStats, Request, Response, VersionInfo};
use phenotype_skills::{Skill, SkillDependency, SkillManifest};

// ── Helper ──────────────────────────────────────────────────────────────────

fn make_skill(id: &str, deps: Vec<&str>) -> Skill {
    let manifest = SkillManifest::new(id, "1.0.0");
    let mut skill = Skill::new(id, manifest);
    for dep in deps {
        skill.manifest.dependencies.push(SkillDependency::new(dep));
    }
    skill
}

// ── BufferPool ──────────────────────────────────────────────────────────────

#[test]
fn buffer_pool_acquire_and_release() {
    let pool = BufferPool::new(4, 1024);
    let buf = pool.acquire(0).expect("should acquire");
    assert_eq!(buf.capacity(), 1024);
    pool.release(0, buf);
    assert!(pool.acquire(0).is_some());
}

#[test]
fn buffer_pool_capacity_limit() {
    let pool = BufferPool::new(4, 512);
    for _ in 0..65 {
        pool.release(0, BytesMut::with_capacity(512));
    }
    assert!(pool.acquire(0).is_some());
}

#[test]
fn buffer_pool_empty_returns_none() {
    let pool = BufferPool::new(0, 256);
    assert!(pool.acquire(0).is_none());
}

// ── ConnectionStats ─────────────────────────────────────────────────────────

#[test]
fn connection_stats_default_values() {
    let s = ConnectionStats::default();
    assert_eq!(s.requests_processed, 0);
    assert_eq!(s.bytes_received, 0);
    assert_eq!(s.bytes_sent, 0);
    assert_eq!(s.avg_response_time_us, 0);
    assert_eq!(s.active_connections, 0);
}

// ── VersionInfo ─────────────────────────────────────────────────────────────

#[test]
fn version_info_current_returns_valid_data() {
    let vi = VersionInfo::current();
    assert!(!vi.version.is_empty());
    assert_eq!(vi.protocol_version, "1.0");
    assert!(vi.features.contains(&"unix-socket".to_string()));
    assert!(vi.features.contains(&"tcp".to_string()));
    assert!(vi.features.contains(&"jsonrpc".to_string()));
}

// ── Request JSON roundtrips ─────────────────────────────────────────────────

fn assert_json_roundtrip<T: serde::Serialize + for<'de> serde::Deserialize<'de>>(val: &T) {
    let json = serde_json::to_string(val).unwrap();
    let back: T = serde_json::from_str(&json).unwrap();
    let json2 = serde_json::to_string(&back).unwrap();
    assert_eq!(json, json2);
}

fn assert_msgpack_roundtrip<T: serde::Serialize + for<'de> serde::Deserialize<'de>>(val: &T) {
    let bytes = rmp_serde::to_vec_named(val).unwrap();
    let back: T = rmp_serde::from_slice(&bytes).unwrap();
    let bytes2 = rmp_serde::to_vec_named(&back).unwrap();
    assert_eq!(bytes, bytes2);
}

#[test]
fn request_json_roundtrips() {
    let skill = make_skill("rj", vec![]);
    let cases: Vec<Request> = vec![
        Request::Ping,
        Request::Version,
        Request::Stats,
        Request::SkillList {
            limit: Some(10),
            offset: Some(5),
        },
        Request::SkillGet { id: "x".into() },
        Request::SkillRegister { skill },
        Request::SkillUnregister { id: "y".into() },
        Request::SkillExists { id: "z".into() },
        Request::Resolve {
            skill_ids: vec!["a".into()],
        },
        Request::CheckCircular {
            skill_ids: vec!["b".into()],
        },
        Request::CheckConflicts,
    ];
    for v in cases {
        assert_json_roundtrip(&v);
    }
}

#[test]
fn request_msgpack_roundtrips() {
    let skill = make_skill("rm", vec!["dep-a"]);
    let cases: Vec<Request> = vec![
        Request::Ping,
        Request::Version,
        Request::Stats,
        Request::SkillList {
            limit: None,
            offset: None,
        },
        Request::SkillGet { id: "x".into() },
        Request::SkillRegister { skill },
        Request::SkillUnregister { id: "y".into() },
        Request::SkillExists { id: "z".into() },
        Request::Resolve {
            skill_ids: vec!["a".into()],
        },
        Request::CheckCircular {
            skill_ids: vec!["b".into()],
        },
        Request::CheckConflicts,
    ];
    for v in cases {
        assert_msgpack_roundtrip(&v);
    }
}

// ── Response JSON roundtrips ────────────────────────────────────────────────

#[test]
fn response_json_roundtrips() {
    let skill = make_skill("rj-resp", vec![]);
    let cases: Vec<Response> = vec![
        Response::Success,
        Response::Error {
            code: -1,
            message: "err".into(),
        },
        Response::Pong,
        Response::VersionInfo {
            version: "1".into(),
            protocol_version: "1".into(),
            features: vec![],
        },
        Response::Stats {
            total_skills: 5,
            active_sandboxes: 2,
            buffer_pool_available: 32,
            uptime_seconds: 100,
        },
        Response::SkillList {
            skills: vec![skill.clone()],
            total: 1,
        },
        Response::Skill { skill },
        Response::SkillExists { exists: true },
        Response::Resolved {
            skill_ids: vec!["a".into()],
        },
        Response::ConflictCheck {
            conflicts: vec!["d".into()],
        },
        Response::CircularCheck { has_cycle: true },
    ];
    for v in cases {
        assert_json_roundtrip(&v);
    }
}

#[test]
fn response_msgpack_roundtrips() {
    let skill = make_skill("rm-resp", vec![]);
    let cases: Vec<Response> = vec![
        Response::Success,
        Response::Error {
            code: -1,
            message: "e".into(),
        },
        Response::Pong,
        Response::VersionInfo {
            version: "1".into(),
            protocol_version: "1".into(),
            features: vec![],
        },
        Response::Stats {
            total_skills: 0,
            active_sandboxes: 0,
            buffer_pool_available: 0,
            uptime_seconds: 0,
        },
        Response::SkillList {
            skills: vec![skill.clone()],
            total: 1,
        },
        Response::Skill { skill },
        Response::SkillExists { exists: false },
        Response::Resolved { skill_ids: vec![] },
        Response::ConflictCheck { conflicts: vec![] },
        Response::CircularCheck { has_cycle: false },
    ];
    for v in cases {
        assert_msgpack_roundtrip(&v);
    }
}
