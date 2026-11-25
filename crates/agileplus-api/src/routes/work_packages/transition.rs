use agileplus_domain::domain::work_package::WpState;
use agileplus_domain::ports::observability::ObservabilityPort;
use agileplus_domain::ports::storage::StoragePort;
use agileplus_domain::ports::vcs::VcsPort;
use axum::extract::{Path, State};
use axum::Json;
use serde::{Deserialize, Serialize};

use crate::error::{domain_error, not_found, ApiError, ApiResponse};
use crate::state::AppState;

#[derive(Debug, Deserialize)]
pub struct WpTransitionRequest {
    pub target_state: String,
}

#[derive(Debug, Serialize)]
pub struct WpTransitionResponse {
    pub wp_id: i64,
    pub from_state: String,
    pub to_state: String,
}

/// `POST /api/v1/work-packages/:id/transition`
pub async fn transition_work_package<S, V, O>(
    State(app): State<AppState<S, V, O>>,
    Path(id): Path<i64>,
    Json(body): Json<WpTransitionRequest>,
) -> Result<Json<WpTransitionResponse>, ApiResponse>
where
    S: StoragePort + Send + Sync + 'static,
    V: VcsPort + Send + Sync + 'static,
    O: ObservabilityPort + Send + Sync + 'static,
{
    let wp = app
        .storage
        .get_work_package(id)
        .await
        .map_err(domain_error)?
        .ok_or_else(|| not_found("work-package", id.to_string()))?;

    let target = parse_wp_state(&body.target_state)?;
    if !wp.state.can_transition_to(target) {
        return Err(ApiResponse::from(ApiError::Conflict(format!(
            "invalid transition {:?} -> {:?}",
            wp.state, target
        ))));
    }

    let from_state = format!("{:?}", wp.state).to_lowercase();
    app.storage
        .update_wp_state(id, target)
        .await
        .map_err(domain_error)?;

    Ok(Json(WpTransitionResponse {
        wp_id: id,
        from_state,
        to_state: format!("{:?}", target).to_lowercase(),
    }))
}

fn parse_wp_state(s: &str) -> Result<WpState, ApiError> {
    match s.to_lowercase().as_str() {
        "planned" => Ok(WpState::Planned),
        "doing" => Ok(WpState::Doing),
        "review" => Ok(WpState::Review),
        "done" => Ok(WpState::Done),
        "blocked" => Ok(WpState::Blocked),
        other => Err(ApiError::BadRequest(format!("Unknown WP state: {other}"))),
    }
}
