//! HTTP server and dashboard for phenotype-health
//!
//! Provides axum-based HTTP endpoints for health monitoring
//! with a built-in dashboard UI.
//!
//! # Features
//!
//! - `/` - Interactive HTML dashboard with real-time metrics
//! - `/health` - Simple health check endpoint
//! - `/api/health` - Full health report (JSON)
//! - `/api/dashboard` - Dashboard data (JSON)
//! - `/api/scan` - Trigger new scan
//! - `/api/projects/:name` - Project details
//!
//! # Usage
//!
//! ```rust,ignore
//! use phenotype_health_axum::{start_server, HealthCache, HealthServerState};
//! use phenotype_health_cli::UnifiedHealthScanner;
//! use std::sync::Arc;
//! use tokio::sync::RwLock;
//!
//! let state = HealthServerState {
//!     scan_root: std::path::PathBuf::from("."),
//!     cache: Arc::new(RwLock::new(HealthCache::default())),
//!     scanner: Arc::new(RwLock::new(UnifiedHealthScanner::new())),
//! };
//!
//! start_server(state, "127.0.0.1:8080".parse().unwrap()).await?;
//! ```
//!
//! # Dashboard
//!
//! The dashboard provides:
//! - Overall health status with color-coded indicators
//! - Project metrics (total, healthy, degraded, unhealthy)
//! - Compliance score visualization with progress bars
//! - Finding counts by severity
//! - Auto-refresh every 30 seconds
//!
//! # API Examples
//!
//! ## Health Check
//! ```bash
//! curl http://localhost:8080/health
//! ```
//!
//! ## Trigger Scan
//! ```bash
//! curl -X POST http://localhost:8080/api/scan
//! ```
//!
//! ## Get Dashboard Data
//! ```bash
//! curl http://localhost:8080/api/dashboard
//! ```

use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::{Html, IntoResponse, Json},
    routing::{get, post},
    Router,
};
use chrono::{DateTime, Utc};
use phenotype_health::HealthStatus;
use phenotype_health_cli::{UnifiedHealthReport, UnifiedHealthScanner};
use serde::Serialize;
use std::net::SocketAddr;
use std::path::PathBuf;
use std::sync::Arc;
use tokio::sync::RwLock;
use tracing::info;

/// Server state shared across handlers
#[derive(Clone)]
pub struct HealthServerState {
    /// Root path to scan
    pub scan_root: PathBuf,
    /// Cached health data
    pub cache: Arc<RwLock<HealthCache>>,
    /// Scanner instance
    pub scanner: Arc<RwLock<UnifiedHealthScanner>>,
}

impl std::fmt::Debug for HealthServerState {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.debug_struct("HealthServerState")
            .field("scan_root", &self.scan_root)
            .field("cache", &self.cache)
            .finish_non_exhaustive()
    }
}

/// Cached health data with timestamp
#[derive(Debug, Clone, Default)]
pub struct HealthCache {
    /// Last scan result
    pub report: Option<UnifiedHealthReport>,
    /// When the cache was last updated
    pub last_updated: Option<DateTime<Utc>>,
    /// Whether a scan is in progress
    pub is_scanning: bool,
}

impl HealthCache {
    /// Check if cache is stale (older than 60 seconds)
    pub fn is_stale(&self) -> bool {
        match self.last_updated {
            None => true,
            Some(updated) => Utc::now().signed_duration_since(updated).num_seconds() > 60,
        }
    }
}

/// Health check response
#[derive(Debug, Serialize)]
struct HealthResponse {
    status: String,
    timestamp: String,
    version: String,
}

/// Dashboard data response
#[derive(Debug, Serialize)]
struct DashboardData {
    status: String,
    projects: Vec<ProjectData>,
    metrics: MetricsData,
    last_updated: String,
}

#[derive(Debug, Serialize)]
struct ProjectData {
    name: String,
    project_type: String,
    compliance_score: f32,
    status: String,
}

#[derive(Debug, Serialize, Default)]
struct MetricsData {
    total_projects: usize,
    healthy_projects: usize,
    degraded_projects: usize,
    unhealthy_projects: usize,
    critical_findings: usize,
    high_findings: usize,
}

/// Start the health dashboard server
pub async fn start_server(state: HealthServerState, addr: SocketAddr) -> anyhow::Result<()> {
    info!("Starting health dashboard server on {}", addr);

    let app = create_router(state);

    let listener = tokio::net::TcpListener::bind(addr).await?;
    info!("Dashboard available at http://{}", addr);

    axum::serve(listener, app).await?;
    Ok(())
}

/// Create the axum router with all routes
fn create_router(state: HealthServerState) -> Router {
    Router::new()
        .route("/", get(dashboard_handler))
        .route("/health", get(health_handler))
        .route("/api/health", get(api_health_handler))
        .route("/api/dashboard", get(api_dashboard_handler))
        .route("/api/scan", post(trigger_scan_handler))
        .route("/api/projects/:name", get(project_detail_handler))
        .with_state(state)
        .layer(tower_http::cors::CorsLayer::permissive())
        .layer(tower_http::trace::TraceLayer::new_for_http())
}

/// Dashboard HTML page handler
async fn dashboard_handler(State(state): State<HealthServerState>) -> impl IntoResponse {
    let cache = state.cache.read().await;
    let report = cache.report.as_ref();

    let html = format!(
        r#"<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Phenotype Health Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            line-height: 1.6;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 2rem; }}
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid #334155;
        }}
        h1 {{ font-size: 1.875rem; font-weight: 700; color: #f8fafc; }}
        .status-badge {{
            padding: 0.5rem 1rem;
            border-radius: 9999px;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.875rem;
        }}
        .status-healthy {{ background: #22c55e; color: #064e3b; }}
        .status-degraded {{ background: #eab308; color: #713f12; }}
        .status-unhealthy {{ background: #ef4444; color: #7f1d1d; }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }}
        .metric-card {{
            background: #1e293b;
            padding: 1.5rem;
            border-radius: 0.75rem;
            border: 1px solid #334155;
        }}
        .metric-label {{ font-size: 0.875rem; color: #94a3b8; margin-bottom: 0.5rem; }}
        .metric-value {{ font-size: 2rem; font-weight: 700; color: #f8fafc; }}
        .projects-table {{
            background: #1e293b;
            border-radius: 0.75rem;
            overflow: hidden;
            border: 1px solid #334155;
        }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{
            text-align: left;
            padding: 1rem;
            font-size: 0.875rem;
            font-weight: 600;
            color: #94a3b8;
            background: #0f172a;
            border-bottom: 1px solid #334155;
        }}
        td {{ padding: 1rem; border-bottom: 1px solid #334155; }}
        tr:last-child td {{ border-bottom: none; }}
        tr:hover {{ background: #252f47; }}
        .score-bar {{
            width: 100%;
            height: 0.5rem;
            background: #334155;
            border-radius: 9999px;
            overflow: hidden;
        }}
        .score-fill {{
            height: 100%;
            border-radius: 9999px;
            transition: width 0.3s ease;
        }}
        .score-good {{ background: #22c55e; }}
        .score-warn {{ background: #eab308; }}
        .score-bad {{ background: #ef4444; }}
        .refresh-btn {{
            padding: 0.75rem 1.5rem;
            background: #3b82f6;
            color: white;
            border: none;
            border-radius: 0.5rem;
            font-weight: 600;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .refresh-btn:hover {{ background: #2563eb; }}
        .last-updated {{ font-size: 0.875rem; color: #64748b; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div>
                <h1>Health Dashboard</h1>
                <p class="last-updated">Last updated: {}</p>
            </div>
            <div style="display: flex; gap: 1rem; align-items: center;">
                <span class="status-badge status-{}">{}</span>
                <button class="refresh-btn" onclick="location.reload()">Refresh</button>
            </div>
        </header>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Total Projects</div>
                <div class="metric-value">{}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Healthy</div>
                <div class="metric-value" style="color: #22c55e;">{}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Degraded</div>
                <div class="metric-value" style="color: #eab308;">{}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">Critical Findings</div>
                <div class="metric-value" style="color: #ef4444;">{}</div>
            </div>
        </div>
        
        <div class="projects-table">
            <table>
                <thead>
                    <tr>
                        <th>Project</th>
                        <th>Type</th>
                        <th>Compliance Score</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {}
                </tbody>
            </table>
        </div>
    </div>
    <script>
        // Auto-refresh every 30 seconds
        setTimeout(() => location.reload(), 30000);
    </script>
</body>
</html>"#,
        cache
            .last_updated
            .map(|d| d.to_rfc3339())
            .unwrap_or_else(|| "Never".to_string()),
        report
            .map(|r| format!("{:?}", r.status).to_lowercase())
            .unwrap_or_default(),
        report
            .map(|r| format!("{:?}", r.status))
            .unwrap_or_else(|| "Unknown".to_string()),
        report.map(|r| r.metrics.total_projects).unwrap_or(0),
        report.map(|r| r.metrics.healthy_projects).unwrap_or(0),
        report.map(|r| r.metrics.degraded_projects).unwrap_or(0),
        report.map(|r| r.metrics.critical_findings).unwrap_or(0),
        generate_project_rows(report)
    );

    Html(html)
}

fn generate_project_rows(report: Option<&UnifiedHealthReport>) -> String {
    match report {
        None => String::new(),
        Some(r) => r
            .projects
            .iter()
            .map(|p| {
                let score_class = if p.compliance_score >= 90.0 {
                    "score-good"
                } else if p.compliance_score >= 70.0 {
                    "score-warn"
                } else {
                    "score-bad"
                };
                let status_class = match p.status {
                    HealthStatus::Healthy => "status-healthy",
                    HealthStatus::Degraded => "status-degraded",
                    HealthStatus::Unhealthy => "status-unhealthy",
                };
                format!(
                    r#"<tr>
                        <td>{}</td>
                        <td>{:?}</td>
                        <td>
                            <div style="display: flex; align-items: center; gap: 0.75rem;">
                                <div class="score-bar" style="flex: 1;">
                                    <div class="score-fill {}" style="width: {}%;"></div>
                                </div>
                                <span style="font-weight: 600; min-width: 3rem;">{:.0}%</span>
                            </div>
                        </td>
                        <td><span class="status-badge {}">{:?}</span></td>
                    </tr>"#,
                    p.name,
                    p.project_type,
                    score_class,
                    p.compliance_score,
                    p.compliance_score,
                    status_class,
                    p.status
                )
            })
            .collect(),
    }
}

/// Simple health check endpoint
async fn health_handler() -> impl IntoResponse {
    let response = HealthResponse {
        status: "healthy".to_string(),
        timestamp: Utc::now().to_rfc3339(),
        version: env!("CARGO_PKG_VERSION").to_string(),
    };
    (StatusCode::OK, Json(response))
}

/// API health endpoint returning full health report
async fn api_health_handler(State(state): State<HealthServerState>) -> impl IntoResponse {
    let cache = state.cache.read().await;

    match &cache.report {
        Some(report) => {
            let json_value = serde_json::to_value(report)
                .unwrap_or(serde_json::json!({"error": "serialization failed"}));
            (StatusCode::OK, Json(json_value))
        }
        None => {
            let response = serde_json::json!({
                "status": "unknown",
                "message": "No scan completed yet"
            });
            (StatusCode::SERVICE_UNAVAILABLE, Json(response))
        }
    }
}

/// Dashboard data API endpoint
async fn api_dashboard_handler(State(state): State<HealthServerState>) -> impl IntoResponse {
    let cache = state.cache.read().await;

    let data = match &cache.report {
        Some(report) => DashboardData {
            status: format!("{:?}", report.status),
            projects: report
                .projects
                .iter()
                .map(|p| ProjectData {
                    name: p.name.clone(),
                    project_type: format!("{:?}", p.project_type),
                    compliance_score: p.compliance_score,
                    status: format!("{:?}", p.status),
                })
                .collect(),
            metrics: MetricsData {
                total_projects: report.metrics.total_projects,
                healthy_projects: report.metrics.healthy_projects,
                degraded_projects: report.metrics.degraded_projects,
                unhealthy_projects: report.metrics.unhealthy_projects,
                critical_findings: report.metrics.critical_findings,
                high_findings: report.metrics.high_findings,
            },
            last_updated: cache
                .last_updated
                .map(|d| d.to_rfc3339())
                .unwrap_or_default(),
        },
        None => DashboardData {
            status: "unknown".to_string(),
            projects: vec![],
            metrics: MetricsData::default(),
            last_updated: "Never".to_string(),
        },
    };

    Json(data)
}

/// Trigger a new scan
async fn trigger_scan_handler(State(state): State<HealthServerState>) -> impl IntoResponse {
    let mut cache = state.cache.write().await;

    if cache.is_scanning {
        return (
            StatusCode::CONFLICT,
            Json(serde_json::json!({
                "status": "error",
                "message": "Scan already in progress"
            })),
        );
    }

    cache.is_scanning = true;
    drop(cache);

    // Run scan in background
    let scan_root = state.scan_root.clone();
    let cache = state.cache.clone();

    tokio::spawn(async move {
        let mut scanner = UnifiedHealthScanner::new();
        let report = scanner.scan_workspace(&scan_root).await;

        let mut cache = cache.write().await;
        cache.report = Some(report);
        cache.last_updated = Some(Utc::now());
        cache.is_scanning = false;
        info!("Health scan completed");
    });

    (
        StatusCode::ACCEPTED,
        Json(serde_json::json!({
            "status": "accepted",
            "message": "Scan started"
        })),
    )
}

/// Get project details
async fn project_detail_handler(
    State(state): State<HealthServerState>,
    Path(name): Path<String>,
) -> impl IntoResponse {
    let cache = state.cache.read().await;

    match &cache.report {
        Some(report) => match report.projects.iter().find(|p| p.name == name) {
            Some(project) => {
                let response = serde_json::json!({
                    "name": project.name,
                    "type": format!("{:?}", project.project_type),
                    "compliance_score": project.compliance_score,
                    "status": format!("{:?}", project.status),
                    "path": project.path,
                    "has_health_config": project.has_health_config,
                });
                (StatusCode::OK, Json(response))
            }
            None => {
                let response = serde_json::json!({
                    "status": "error",
                    "message": format!("Project '{}' not found", name)
                });
                (StatusCode::NOT_FOUND, Json(response))
            }
        },
        None => {
            let response = serde_json::json!({
                "status": "error",
                "message": "No scan completed yet"
            });
            (StatusCode::SERVICE_UNAVAILABLE, Json(response))
        }
    }
}
