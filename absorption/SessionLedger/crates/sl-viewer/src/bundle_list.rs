use session_ledger::domain::bundle::{BundleKind, ContinuationBundle};

/// A lightweight summary derived from a [`ContinuationBundle`] for list display.
#[derive(Debug, Clone, PartialEq)]
pub struct BundleSummary {
    pub source_id: String,
    pub intent_goal: String,
    pub bundle_count: usize,
    pub has_acceptance: bool,
    pub has_contract: bool,
}

/// Extract a row summary from a bundle for the list view.
#[must_use]
pub fn summarize(bundle: &ContinuationBundle) -> BundleSummary {
    let intent_goal = bundle
        .bundles
        .iter()
        .find(|b| b.kind == BundleKind::Intent)
        .and_then(|b| b.body.get("goal"))
        .and_then(|v| v.as_str())
        .filter(|goal| !goal.trim().is_empty())
        .unwrap_or("(no goal)")
        .to_owned();

    BundleSummary {
        source_id: bundle.source_id.clone(),
        intent_goal,
        bundle_count: bundle.bundles.len(),
        has_acceptance: bundle.has(BundleKind::Acceptance),
        has_contract: bundle.has(BundleKind::Contract),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use session_ledger::domain::bundle::Bundle;

    #[test]
    fn blank_intent_goal_uses_nonempty_fallback() {
        let bundle = ContinuationBundle {
            source_id: "blank-goal".to_owned(),
            bundles: vec![Bundle::new(BundleKind::Intent, serde_json::json!({ "goal": "" }))],
        };

        assert_eq!(summarize(&bundle).intent_goal, "(no goal)");
    }
}
