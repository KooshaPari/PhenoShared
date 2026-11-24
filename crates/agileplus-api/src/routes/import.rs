//! HTTP import endpoints for AgilePlus bundle ingestion.

use axum::extract::State;
use axum::routing::post;
use axum::{Json, Router};

use agileplus_domain::ports::{
    observability::ObservabilityPort, storage::StoragePort, vcs::VcsPort,
};
use agileplus_import::{import_bundle, ImportBundle, ImportProject, ImportReport};

use crate::error::{ApiError, ApiResponse};
use crate::state::AppState;

pub fn routes<S, V, O>() -> Router<AppState<S, V, O>>
where
    S: StoragePort + Send + Sync + 'static,
    V: VcsPort + Send + Sync + 'static,
    O: ObservabilityPort + Send + Sync + 'static,
{
    Router::new()
        .route("/bundle", post(import_bundle_handler::<S, V, O>))
        .route("/batch-projects", post(batch_projects_handler::<S, V, O>))
}

async fn import_bundle_handler<S, V, O>(
    State(app): State<AppState<S, V, O>>,
    Json(bundle): Json<ImportBundle>,
) -> Result<Json<ImportReport>, ApiResponse>
where
    S: StoragePort + Send + Sync + 'static,
    V: VcsPort + Send + Sync + 'static,
    O: ObservabilityPort + Send + Sync + 'static,
{
    let report = import_bundle(bundle, app.storage.as_ref(), app.vcs.as_ref())
        .await
        .map_err(|e| ApiError::BadRequest(e.to_string()))?;
    Ok(Json(report))
}

/// Accept a list of projects (each optionally embedding features) and import them
/// via the standard bundle path, so all project/feature/work-package logic is reused.
async fn batch_projects_handler<S, V, O>(
    State(app): State<AppState<S, V, O>>,
    Json(projects): Json<Vec<ImportProject>>,
) -> Result<Json<ImportReport>, ApiResponse>
where
    S: StoragePort + Send + Sync + 'static,
    V: VcsPort + Send + Sync + 'static,
    O: ObservabilityPort + Send + Sync + 'static,
{
    let bundle = ImportBundle {
        projects,
        ..Default::default()
    };
    let report = import_bundle(bundle, app.storage.as_ref(), app.vcs.as_ref())
        .await
        .map_err(|e| ApiError::BadRequest(e.to_string()))?;
    Ok(Json(report))
}
