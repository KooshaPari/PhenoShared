//! RPC handler and shared-state integration tests.

use phenotype_daemon::protocol::Request;
use phenotype_daemon::protocol::Response;
use phenotype_daemon::rpc::{BytesPool, RpcHandler, SharedState};
use phenotype_skills::{Skill, SkillDependency, SkillManifest};
use std::sync::Arc;

// ── Helper ──────────────────────────────────────────────────────────────────

fn make_skill(id: &str, deps: Vec<&str>) -> Skill {
    let manifest = SkillManifest::new(id, "1.0.0");
    let mut skill = Skill::new(id, manifest);
    for dep in deps {
        skill.manifest.dependencies.push(SkillDependency::new(dep));
    }
    skill
}

// ── SharedState ─────────────────────────────────────────────────────────────

#[tokio::test]
async fn shared_state_new_creates_valid_state() {
    let state = SharedState::new();
    assert!(state.registry.is_empty());
    assert!(!state.version_info.version.is_empty());
}

#[tokio::test]
async fn shared_state_buffer_pool_acquire_release() {
    let state = SharedState::new();
    let buf = state.acquire_buffer().await;
    assert!(buf.is_empty());
    state.release_buffer(buf).await;
}

// ── BytesPool ───────────────────────────────────────────────────────────────

#[test]
fn bytes_pool_acquire_and_release() {
    let mut pool = BytesPool::new(4);
    let buf = pool.acquire();
    assert!(buf.is_empty());
    pool.release(buf);
    let buf2 = pool.acquire();
    assert!(buf2.is_empty());
}

#[test]
fn bytes_pool_capacity_limit() {
    let mut pool = BytesPool::new(2);
    let b1 = pool.acquire();
    let b2 = pool.acquire();
    let b3 = pool.acquire();
    pool.release(b1);
    pool.release(b2);
    pool.release(b3); // dropped, pool full
    let _ = pool.acquire();
}

#[test]
fn bytes_pool_zero_capacity() {
    let mut pool = BytesPool::new(0);
    let buf = pool.acquire();
    pool.release(buf); // dropped
    let buf2 = pool.acquire();
    assert!(buf2.is_empty());
}

// ── RpcHandler: basic requests ──────────────────────────────────────────────

#[tokio::test]
async fn rpc_handle_ping() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));
    assert!(matches!(
        handler.handle_request(Request::Ping).await,
        Response::Pong
    ));
}

#[tokio::test]
async fn rpc_handle_version() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));
    match handler.handle_request(Request::Version).await {
        Response::VersionInfo {
            version,
            protocol_version,
            features,
        } => {
            assert!(!version.is_empty());
            assert_eq!(protocol_version, "1.0");
            assert!(features.contains(&"tcp".to_string()));
        }
        other => panic!("Expected VersionInfo, got {:?}", other),
    }
}

#[tokio::test]
async fn rpc_handle_stats_empty() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));
    match handler.handle_request(Request::Stats).await {
        Response::Stats {
            total_skills,
            active_sandboxes,
            ..
        } => {
            assert_eq!(total_skills, 0);
            assert_eq!(active_sandboxes, 0);
        }
        other => panic!("Expected Stats, got {:?}", other),
    }
}

#[tokio::test]
async fn rpc_handle_stats_after_register() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));
    handler
        .handle_request(Request::SkillRegister {
            skill: make_skill("s1", vec![]),
        })
        .await;
    match handler.handle_request(Request::Stats).await {
        Response::Stats { total_skills, .. } => assert_eq!(total_skills, 1),
        other => panic!("Expected Stats, got {:?}", other),
    }
}

// ── RpcHandler: skill CRUD ──────────────────────────────────────────────────

#[tokio::test]
async fn rpc_handle_skill_list_empty() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));
    match handler
        .handle_request(Request::SkillList {
            limit: None,
            offset: None,
        })
        .await
    {
        Response::SkillList { skills, total } => {
            assert!(skills.is_empty());
            assert_eq!(total, 0);
        }
        other => panic!("Expected SkillList, got {:?}", other),
    }
}

#[tokio::test]
async fn rpc_handle_skill_list_with_pagination() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));
    for i in 0..5 {
        handler
            .handle_request(Request::SkillRegister {
                skill: make_skill(&format!("p{i}"), vec![]),
            })
            .await;
    }
    match handler
        .handle_request(Request::SkillList {
            limit: Some(2),
            offset: Some(1),
        })
        .await
    {
        Response::SkillList { skills, total } => {
            assert_eq!(total, 5);
            assert_eq!(skills.len(), 2);
        }
        other => panic!("Expected SkillList, got {:?}", other),
    }
}

#[tokio::test]
async fn rpc_handle_skill_get_nonexistent() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));
    match handler
        .handle_request(Request::SkillGet { id: "nope".into() })
        .await
    {
        Response::Error { code, message } => {
            assert_eq!(code, -32000);
            assert!(message.contains("not found"));
        }
        other => panic!("Expected Error, got {:?}", other),
    }
}

#[tokio::test]
async fn rpc_handle_skill_register_then_get() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));
    let skill = make_skill("reg-then-get", vec![]);
    let resp = handler
        .handle_request(Request::SkillRegister { skill })
        .await;
    assert!(matches!(resp, Response::Success));

    match handler
        .handle_request(Request::SkillGet {
            id: "reg-then-get".into(),
        })
        .await
    {
        Response::Skill { skill: got } => assert_eq!(got.id, "reg-then-get"),
        other => panic!("Expected Skill, got {:?}", other),
    }
}

#[tokio::test]
async fn rpc_handle_skill_unregister() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));
    let skill = make_skill("unreg", vec![]);
    handler
        .handle_request(Request::SkillRegister { skill })
        .await;

    let resp = handler
        .handle_request(Request::SkillUnregister { id: "unreg".into() })
        .await;
    assert!(matches!(resp, Response::Success));

    // Confirm gone
    assert!(matches!(
        handler
            .handle_request(Request::SkillGet { id: "unreg".into() })
            .await,
        Response::Error { .. }
    ));
}

#[tokio::test]
async fn rpc_handle_skill_exists() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));

    match handler
        .handle_request(Request::SkillExists { id: "chk".into() })
        .await
    {
        Response::SkillExists { exists } => assert!(!exists),
        other => panic!("Expected SkillExists, got {:?}", other),
    }

    handler
        .handle_request(Request::SkillRegister {
            skill: make_skill("chk", vec![]),
        })
        .await;

    match handler
        .handle_request(Request::SkillExists { id: "chk".into() })
        .await
    {
        Response::SkillExists { exists } => assert!(exists),
        other => panic!("Expected SkillExists, got {:?}", other),
    }
}

// ── RpcHandler: dependency operations ───────────────────────────────────────

#[tokio::test]
async fn rpc_handle_resolve() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));
    handler
        .handle_request(Request::SkillRegister {
            skill: make_skill("a", vec!["b"]),
        })
        .await;
    handler
        .handle_request(Request::SkillRegister {
            skill: make_skill("b", vec![]),
        })
        .await;

    match handler
        .handle_request(Request::Resolve {
            skill_ids: vec!["a".into()],
        })
        .await
    {
        Response::Resolved { skill_ids } => assert!(skill_ids.contains(&"b".to_string())),
        other => panic!("Expected Resolved, got {:?}", other),
    }
}

#[tokio::test]
async fn rpc_handle_check_circular_no_cycle() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));
    match handler
        .handle_request(Request::CheckCircular {
            skill_ids: vec!["solo".into()],
        })
        .await
    {
        Response::CircularCheck { has_cycle } => assert!(!has_cycle),
        other => panic!("Expected CircularCheck, got {:?}", other),
    }
}

#[tokio::test]
async fn rpc_handle_check_conflicts_empty() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));
    match handler.handle_request(Request::CheckConflicts).await {
        Response::ConflictCheck { conflicts } => assert!(conflicts.is_empty()),
        other => panic!("Expected ConflictCheck, got {:?}", other),
    }
}

#[tokio::test]
async fn rpc_handle_check_conflicts_missing_dep() {
    let handler = RpcHandler::new(Arc::new(SharedState::new()));
    handler
        .handle_request(Request::SkillRegister {
            skill: make_skill("ca", vec!["no-dep"]),
        })
        .await;

    match handler.handle_request(Request::CheckConflicts).await {
        Response::ConflictCheck { conflicts } => {
            assert!(!conflicts.is_empty());
            assert!(conflicts.iter().any(|c| c.contains("no-dep")));
        }
        other => panic!("Expected ConflictCheck, got {:?}", other),
    }
}
