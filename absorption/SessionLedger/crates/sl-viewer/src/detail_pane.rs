use session_ledger::domain::bundle::{BundleKind, ContinuationBundle};
use session_ledger::domain::intent::IntentState;

/// Structured data extracted from a [`ContinuationBundle`] for the detail pane.
#[derive(Debug, Clone, PartialEq)]
pub struct BundleDetail {
    pub source_id: String,
    pub intent_goal: Option<String>,
    pub intent_state: IntentState,
    pub acceptance_signals: Vec<String>,
    pub constraints: Vec<String>,
    pub context_cwd: Option<String>,
    pub context_title: Option<String>,
    pub contract_criteria: Vec<String>,
    pub total_token_estimate: u32,
}

/// Extract a rich detail view from a bundle.
#[must_use]
pub fn extract_detail(bundle: &ContinuationBundle) -> BundleDetail {
    let intent = bundle.bundles.iter().find(|b| b.kind == BundleKind::Intent);
    let context = bundle.bundles.iter().find(|b| b.kind == BundleKind::Context);
    let contract = bundle.bundles.iter().find(|b| b.kind == BundleKind::Contract);

    BundleDetail {
        source_id: bundle.source_id.clone(),
        intent_goal: intent
            .and_then(|b| b.body.get("goal"))
            .and_then(|v| v.as_str())
            .map(String::from),
        intent_state: IntentState::Extracted,
        acceptance_signals: intent
            .map(|b| {
                b.body
                    .get("acceptance_signals")
                    .and_then(|v| v.as_array())
                    .map(|arr| {
                        arr.iter().filter_map(|v| v.as_str().map(String::from)).collect::<Vec<_>>()
                    })
                    .unwrap_or_default()
            })
            .unwrap_or_default(),
        constraints: intent
            .map(|b| {
                b.body
                    .get("constraints")
                    .and_then(|v| v.as_array())
                    .map(|arr| {
                        arr.iter().filter_map(|v| v.as_str().map(String::from)).collect::<Vec<_>>()
                    })
                    .unwrap_or_default()
            })
            .unwrap_or_default(),
        context_cwd: context
            .and_then(|b| b.body.get("cwd"))
            .and_then(|v| v.as_str())
            .map(String::from),
        context_title: context
            .and_then(|b| b.body.get("title"))
            .and_then(|v| v.as_str())
            .map(String::from),
        contract_criteria: contract
            .map(|b| {
                b.body
                    .get("skipped_by")
                    .or_else(|| b.body.get("watch_files"))
                    .and_then(|v| v.as_array())
                    .map(|arr| {
                        arr.iter().filter_map(|v| v.as_str().map(String::from)).collect::<Vec<_>>()
                    })
                    .unwrap_or_default()
            })
            .unwrap_or_default(),
        total_token_estimate: bundle.total_token_estimate(),
    }
}
