//! Coverage computation: maps scanned [`ScanTraceLink`]s against manifest FRs.

use std::collections::{HashMap, HashSet};

use serde::{Deserialize, Serialize};
use traceability_core::CoverageState;

use crate::manifest::ManifestRequirement;

/// Coverage status for a single FR in the gate run.
///
/// Uses [`traceability_core::CoverageState`] vocabulary where it fits;
/// adds `Missing` as the gate-failure sentinel.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FrCoverage {
    /// The FR id.
    pub fr_id: String,
    /// Optional spec reference from the manifest.
    pub spec_id: String,
    /// Human description from the manifest.
    pub description: String,
    /// Coverage state derived from the scan.
    pub state: CoverageState,
    /// Files + line numbers where this FR was found (empty ⟹ Missing).
    pub found_at: Vec<FoundAt>,
}

/// One scan hit location.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct FoundAt {
    pub file: String,
    pub line: usize,
    pub symbol: String,
}

/// Full coverage summary for a gate run.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoverageSummary {
    pub requirements: Vec<FrCoverage>,
    pub covered_count: usize,
    pub missing_count: usize,
    /// `true` when all FRs are covered (gate passes).
    pub all_covered: bool,
}

impl CoverageSummary {
    /// Build a summary from scanned links and the manifest.
    pub fn build(
        requirements: &[ManifestRequirement],
        scan_links: &[traceability_decorators::patterns::ScanTraceLink],
    ) -> Self {
        // Index scan results by fr_id → list of hits.
        let mut hits: HashMap<String, Vec<&traceability_decorators::patterns::ScanTraceLink>> =
            HashMap::new();
        for link in scan_links {
            hits.entry(link.fr_id.clone()).or_default().push(link);
        }

        let mut covered_count = 0;
        let mut missing_count = 0;

        let fr_coverages: Vec<FrCoverage> = requirements
            .iter()
            .map(|req| {
                let found = hits.get(&req.fr_id).cloned().unwrap_or_default();
                let state = if found.is_empty() {
                    missing_count += 1;
                    CoverageState::Missing
                } else {
                    covered_count += 1;
                    CoverageState::Covered
                };
                let found_at = found
                    .into_iter()
                    .map(|l| FoundAt {
                        file: l.file.clone(),
                        line: l.line,
                        symbol: l.symbol.clone(),
                    })
                    .collect();
                FrCoverage {
                    fr_id: req.fr_id.clone(),
                    spec_id: req.spec_id.clone(),
                    description: req.description.clone(),
                    state,
                    found_at,
                }
            })
            .collect();

        // Also report any FRs found in source that weren't in the manifest
        // (informational — they don't affect the gate).
        let manifest_ids: HashSet<&str> = requirements.iter().map(|r| r.fr_id.as_str()).collect();
        let extra: Vec<&str> = hits
            .keys()
            .filter(|id| !manifest_ids.contains(id.as_str()))
            .map(|s| s.as_str())
            .collect();
        if !extra.is_empty() {
            // Print informational note; not a failure.
            eprintln!(
                "trace-gate: FRs found in source but not in manifest (informational): {extra:?}"
            );
        }

        let all_covered = missing_count == 0 && !requirements.is_empty();
        CoverageSummary {
            requirements: fr_coverages,
            covered_count,
            missing_count,
            all_covered,
        }
    }
}
