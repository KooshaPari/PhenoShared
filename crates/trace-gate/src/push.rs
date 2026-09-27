//! Tracera ingest push stub.
//!
//! Posts the coverage summary to a Tracera ingest endpoint.
//! This is best-effort: failures are logged but do NOT affect the gate exit code.
//!
//! Ingest endpoint shape (from Tracera `routers/traceability.py`):
//! ```
//! POST <url>/api/v1/coverage/ingest
//! Content-Type: application/json
//! { "links": [ { "source_id": "FR-001", "target_id": "<file>:<line>",
//!               "relationship": "implements", "confidence": 1.0 } ] }
//! ```
//!
//! The stub prints the payload when no HTTP client is available (feature-gated).
//! Consumer repos that want real pushes should enable the `push` feature flag
//! (reqwest) once the Tracera ingest endpoint is stable post-#754.

use crate::coverage::CoverageSummary;

/// Push coverage summary to Tracera ingest (stub).
///
/// Currently **prints** the would-be payload to stdout. Wire up reqwest
/// behind a `push` feature flag when Tracera/#754 lands.
// FR: FR-GATE-003
pub fn push_to_tracera(url: &str, summary: &CoverageSummary) {
    // Build a TraceLinkInput-shaped payload per the Tracera REST schema.
    let links: Vec<serde_json::Value> = summary
        .requirements
        .iter()
        .flat_map(|req| {
            if req.found_at.is_empty() {
                // No coverage — skip (gate already reports missing).
                vec![]
            } else {
                req.found_at
                    .iter()
                    .map(|loc| {
                        serde_json::json!({
                            "source_id": req.fr_id,
                            "target_id": format!("{}:{}", loc.file, loc.line),
                            "relationship": "implements",
                            "confidence": 1.0
                        })
                    })
                    .collect()
            }
        })
        .collect();

    let payload = serde_json::json!({ "links": links });
    eprintln!(
        "trace-gate: would push {} trace-link(s) to {url}",
        links.len()
    );
    eprintln!(
        "trace-gate: push payload preview:\n{}",
        serde_json::to_string_pretty(&payload).unwrap_or_default()
    );
    // TODO(#754): replace with reqwest::blocking::Client::new().post(url).json(&payload).send()
}
