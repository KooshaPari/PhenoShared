//! Axum route handlers for the dashboard. (T077)
//!
//! This module provides HTTP request handlers for the AgilePlus dashboard,
//! organized into per-domain submodules:
//! - **pages**: Root, home, features, events, settings, hub pages
//! - **dashboard**: Kanban board, work packages, SSE streams
//! - **features**: Feature detail, transitions, events, media
//! - **evidence**: Evidence bundles, artifacts, generation
//! - **agents**: Agent activity detection
//! - **health**: Service health monitoring and management
//! - **settings**: Configuration pages and persistence
//! - **helpers**: Shared utility functions and types
//!
//! Pattern: if the request carries `HX-Request: true`, return only the
//! relevant partial; otherwise return the full page layout.

use std::sync::Arc;

use axum::{
    extract::State,
    routing::{get, post},
    Json, Router,
};
use serde::Serialize;

use crate::app_state::SharedState;

pub mod agents;
pub mod dashboard;
pub mod evidence;
pub mod features;
pub mod health;
pub mod helpers;
pub mod pages;
pub mod settings;

// ── Route Handler Re-exports ──────────────────────────────────────────────
// Exported for backward compatibility with call sites like routes::feature_detail

// From pages
pub use pages::{
    dashboard_page, events_page, features_page, home, hub_page, root, settings_page,
};

// From dashboard
pub use dashboard::{
    kanban_board, wp_list, all_work_packages_json, epics_stories_json,
    project_switcher, switch_project, time_footer, sse_stream,
    WorkPackageJson,
};

// From features
pub use features::{
    feature_detail, feature_page, feature_transition, feature_events, feature_media,
    FeatureTransitionForm,
};

// From evidence
pub use evidence::{
    evidence_content, evidence_preview, feature_evidence_list,
    feature_evidence_generate, feature_evidence_json,
    EvidenceGalleryJson, EvidenceArtifactJson,
};

// From agents
pub use agents::{
    agent_activity, agents_json, test_agent_connection,
};

// From health
pub use health::{
    health_panel, health_json, health_page, restart_service,
    toggle_service, patch_service_config,
    HealthStatus, ServiceHealthJson,
};

// From settings
pub use settings::{
    plane_settings_page, agent_settings_page, services_settings_page,
    save_plane_settings, save_agent_settings, save_dashboard_settings,
    save_services_settings, test_service_connection, test_plane_connection,
    // Types
    Config, PlaneConfig, AgentConfig, ServiceConfig, DashboardConfig,
    PlaneSettingsForm, AgentSettingsForm, ServiceSettingsForm, DashboardSettingsForm,
    SingleServiceTestForm,
};

// ── Event Timeline Handler ─────────────────────────────────────────────

pub async fn event_timeline(axum::extract::State(_state): axum::extract::State<SharedState>) -> axum::response::Response {
    use crate::templates::EventTimelinePartial;
    helpers::render(EventTimelinePartial {
        feature_id: 0,
        events: vec![],
    })
}

// ── Router builder ───────────────────────────────────────────────────────

pub fn router(
    state: SharedState,
    governance: Option<Arc<agileplus_governance::client::GovernanceClient>>,
    plane: Option<Arc<agileplus_plane::client::PlaneClient>>,
) -> Router {
    let api = Router::new()
        .route("/api/dashboard/kanban", get(kanban))
        .route("/api/dashboard/features", get(features))
        .route("/api/dashboard/agents", get(agents::agents))
        .route("/api/dashboard/agents/sessions", get(agents::sessions))
        .route("/api/dashboard/agents/test", post(agents::test_agent))
        .route("/api/dashboard/agents/poll", post(agents::poll))
        .route("/api/dashboard/plane/test", post(test_plane_connection))
        .route("/api/dashboard/plane/sync", post(plane_sync))
        .route("/api/dashboard/plane/status", get(plane_status))
        .route("/api/dashboard/governance/status", get(governance_status))
        .route("/api/dashboard/evidence", get(evidence))
        .route("/api/dashboard/events", get(events))
        .route("/api/dashboard/health", get(health))
        .route("/api/dashboard/modules", get(modules))
        .route("/api/dashboard/cycles", get(cycles))
        .route("/api/dashboard/worklog", get(worklog))
        .route("/api/dashboard/metrics", get(metrics))
        .route("/api/dashboard/exec", post(exec_command))
        .route("/api/dashboard/planify-shim/start", post(planify_shim::start_planify_shim))
        .route("/api/dashboard/planify-shim/stop", post(planify_shim::stop_planify_shim))
        .route("/api/dashboard/planify-shim/status", get(planify_shim::planify_shim_status))
        .with_state((state, governance, plane));

    let pages = Router::new()
        .route("/", get(home))
        .route("/home", get(home))
        .route("/dashboard", get(dashboard))
        .route("/hub", get(hub))
        .route("/features", get(features_page))
        .route("/features/:id", get(feature_detail))
        .route("/cycles", get(cycles_page))
        .route("/cycles/:id", get(cycle_detail))
        .route("/modules", get(modules_page))
        .route("/events", get(events_page))
        .route("/evidence", get(evidence_page))
        .route("/settings", get(settings))
        .route("/settings/plane", get(plane_settings_page))
        .route("/settings/agents", get(agent_settings_page))
        .route("/settings/services", get(settings_services_page))
        .with_state(state);

    Router::new().merge(api).merge(pages)
}
            post(test_agent_connection),
        )
        .route("/api/settings/dashboard", post(save_dashboard_settings))
        .route(
            "/api/dashboard/services/{name}/restart",
            post(restart_service),
        )
        .route(
            "/api/dashboard/services/{name}/config",
            axum::routing::patch(patch_service_config),
        )
        .route(
            "/api/dashboard/services/{name}/toggle",
            post(toggle_service),
        )
        .route("/api/dashboard/kanban", get(kanban_board))
        .route("/api/dashboard/features/{id}", get(feature_detail))
        .route("/api/dashboard/features/{id}/work-packages", get(wp_list))
        .route("/api/dashboard/features/{id}/events", get(feature_events))
        .route("/api/dashboard/features/{id}/media", get(feature_media))
        // HTML partial endpoints (HTMX-compatible)
        .route("/api/dashboard/health", get(health_panel))
        .route("/api/dashboard/events", get(event_timeline))
        .route("/api/dashboard/agents", get(agent_activity))
        // JSON API endpoints (for polling from JavaScript templates)
        .route("/api/dashboard/agents.json", get(agents_json))
        .route("/api/dashboard/health.json", get(health_json))
        .route(
            "/api/dashboard/work-packages.json",
            get(all_work_packages_json),
        )
        .route("/api/dashboard/epics-stories.json", get(epics_stories_json))
        .route("/api/dashboard/projects", get(project_switcher))
        .route(
            "/api/dashboard/projects/{id}/activate",
            post(switch_project),
        )
        .route("/api/time", get(time_footer))
        .route("/api/stream", get(sse_stream))
        // NOTE: /api/v1/stream is owned by agileplus-api (router.rs, T069).
        // Previously this crate registered an alias (#334), but that caused a
        // route conflict panic when build_router merged the two routers.
        .route("/api/stream-placeholder", get(sse_stream))
        .route(
            "/api/evidence/{feature_id}/{artifact_id}/content",
            get(evidence_content),
        )
        .route(
            "/api/evidence/{feature_id}/{artifact_id}/preview",
            get(evidence_preview),
        )
        .route("/api/features/{id}/evidence", get(feature_evidence_list))
        .route(
            "/api/features/{id}/evidence/generate",
            post(feature_evidence_generate),
        )
        .route(
            "/api/dashboard/features/{id}/evidence.json",
            get(feature_evidence_json),
        )
        .route("/api/features/{id}/transition", post(feature_transition))
        .with_state(state)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::app_state::{default_health, DashboardStore};
    use std::sync::Arc;
    use tokio::sync::RwLock;
    use tower::util::ServiceExt;

    fn make_state() -> SharedState {
        let store = DashboardStore {
            health: default_health(),
            ..Default::default()
        };
        Arc::new(RwLock::new(store))
    }

    #[tokio::test]
    async fn toggle_service_updates_store_and_responds() {
        let state = make_state();
        let app = router(state.clone());

        let request_body = serde_json::json!({ "enabled": false }).to_string();
        let request = axum::http::Request::builder()
            .method("POST")
            .uri("/api/dashboard/services/NATS/toggle")
            .header("content-type", "application/json")
            .body(axum::body::Body::from(request_body))
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), axum::http::StatusCode::OK);

        let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .unwrap();
        let body_text = String::from_utf8(body_bytes.to_vec()).unwrap();
        assert!(body_text.contains("\"status\":\"ok\""));
        assert!(body_text.contains("\"enabled\":false"));

        let store = state.read().await;
        let health = store.health.iter().find(|s| s.name == "NATS").unwrap();
        assert!(!health.healthy);
        assert!(health.degraded);
    }

    #[tokio::test]
    async fn restart_service_executes_command() {
        let state = make_state();
        let app = router(state.clone());

        unsafe {
            std::env::set_var("AGILEPLUS_SERVICE_RESTART_CMD", "echo restarted {}");
        }

        let request = axum::http::Request::builder()
            .method("POST")
            .uri("/api/dashboard/services/NATS/restart")
            .body(axum::body::Body::empty())
            .unwrap();

        let response = app.oneshot(request).await.unwrap();
        assert_eq!(response.status(), axum::http::StatusCode::OK);

        let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .unwrap();
        let body_text = String::from_utf8(body_bytes.to_vec()).unwrap();
        assert!(body_text.contains("\"status\":\"ok\""));
        assert!(body_text.contains("\"service\":\"NATS\""));
        assert!(body_text.contains("restarted NATS"));
    }

    #[test]
    fn test_html_escape_ampersand() {
        assert_eq!(helpers::html_escape("a & b"), "a &amp; b");
    }

    #[test]
    fn test_html_escape_angle_brackets() {
        assert_eq!(helpers::html_escape("<script>"), "&lt;script&gt;");
    }

    #[test]
    fn test_html_escape_quotes() {
        assert_eq!(helpers::html_escape("say \"hello\""), "say &quot;hello&quot;");
        assert_eq!(helpers::html_escape("it's"), "it&#39;s");
    }

    #[test]
    fn test_is_htmx_true() {
        let mut headers = axum::http::HeaderMap::new();
        headers.insert("HX-Request", "true".parse().unwrap());
        assert!(helpers::is_htmx(&headers));
    }

    #[test]
    fn test_is_htmx_false_absent() {
        let headers = axum::http::HeaderMap::new();
        assert!(!helpers::is_htmx(&headers));
    }

    #[test]
    fn test_is_htmx_false_wrong_value() {
        let mut headers = axum::http::HeaderMap::new();
        headers.insert("HX-Request", "1".parse().unwrap());
        assert!(!helpers::is_htmx(&headers));
    }

    #[tokio::test]
    async fn json_endpoints_integrated_agents_in_router() {
        let state = make_state();
        let app = router(state);

        let request = axum::http::Request::builder()
            .method("GET")
            .uri("/api/dashboard/agents.json")
            .body(axum::body::Body::empty())
            .unwrap();

        let response = app.clone().oneshot(request).await.unwrap();
        assert_eq!(response.status(), axum::http::StatusCode::OK);

        let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .unwrap();
        let body_text = String::from_utf8(body_bytes.to_vec()).unwrap();

        let json: serde_json::Value = serde_json::from_str(&body_text).expect("valid JSON");
        assert!(json.get("agents").is_some());
        assert!(json.get("count").is_some());
        assert!(json.get("timestamp").is_some());
    }

    #[tokio::test]
    async fn json_endpoints_integrated_health_in_router() {
        let state = make_state();
        let app = router(state);

        let request = axum::http::Request::builder()
            .method("GET")
            .uri("/api/dashboard/health.json")
            .body(axum::body::Body::empty())
            .unwrap();

        let response = app.clone().oneshot(request).await.unwrap();
        assert_eq!(response.status(), axum::http::StatusCode::OK);

        let body_bytes = axum::body::to_bytes(response.into_body(), usize::MAX)
            .await
            .unwrap();
        let body_text = String::from_utf8(body_bytes.to_vec()).unwrap();

        let json: serde_json::Value = serde_json::from_str(&body_text).expect("valid JSON");
        assert!(json.get("services").is_some());
        assert!(json.get("timestamp").is_some());
        assert!(json.get("all_healthy").is_some());
    }
}
