//! Timeline view — renders OKF bundles as a horizontal, day-grouped timeline.
//!
//! Pure helper functions (`group_by_day`, `normalize_widths`) are unit-tested
//! independently of Dioxus.

use dioxus::prelude::*;
use session_ledger::domain::bundle::BundleKind;
use session_ledger::domain::bundle::ContinuationBundle;

// ---------------------------------------------------------------------------
// Pure domain helpers (unit-testable)
// ---------------------------------------------------------------------------

/// Lightweight summary derived from a [`ContinuationBundle`] for the timeline.
#[derive(Debug, Clone, PartialEq)]
pub struct TimelineEntry {
    pub source_id: String,
    /// ISO-8601 date portion only: "YYYY-MM-DD".  Empty string if absent.
    pub day: String,
    /// Full ISO-8601 timestamp if available.
    pub created_at: String,
    /// Token count from the Intent bundle.
    pub token_count: u64,
    /// Model name from Context bundle.
    pub model: String,
    /// Primary goal string.
    pub goal: String,
    /// Message count (number of sub-bundles / slices).
    pub message_count: usize,
    /// Has an Acceptance slice.
    pub has_acceptance: bool,
    /// Has a Contract slice.
    pub has_contract: bool,
}

impl TimelineEntry {
    /// Derive a [`TimelineEntry`] from a compiled [`ContinuationBundle`].
    #[must_use]
    pub fn from_bundle(cb: &ContinuationBundle) -> Self {
        let intent = cb.bundles.iter().find(|b| b.kind == BundleKind::Intent);
        let context = cb.bundles.iter().find(|b| b.kind == BundleKind::Context);

        let token_count = intent
            .and_then(|b| b.body.get("user_turn_count"))
            .and_then(|v| v.as_u64())
            .unwrap_or(0);

        let goal = intent
            .and_then(|b| b.body.get("goal"))
            .and_then(|v| v.as_str())
            .unwrap_or("(no goal)")
            .to_owned();

        let created_at = context
            .and_then(|b| b.body.get("created_at"))
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_owned();

        let model = context
            .and_then(|b| b.body.get("model"))
            .and_then(|v| v.as_str())
            .unwrap_or("unknown")
            .to_owned();

        let day = if created_at.len() >= 10 { created_at[..10].to_owned() } else { String::new() };

        let has_acceptance = cb.bundles.iter().any(|b| b.kind == BundleKind::Acceptance);
        let has_contract = cb.bundles.iter().any(|b| b.kind == BundleKind::Contract);

        Self {
            source_id: cb.source_id.clone(),
            day,
            created_at,
            token_count,
            model,
            goal,
            message_count: cb.bundles.len(),
            has_acceptance,
            has_contract,
        }
    }
}

/// Group entries by their `day` field, sorted chronologically.
///
/// Returns a `Vec<(day_label, entries)>` sorted by day ascending.
/// Entries with an empty day are placed in a group labelled `"(unknown date)"`.
#[must_use]
pub fn group_by_day(entries: &[TimelineEntry]) -> Vec<(String, Vec<TimelineEntry>)> {
    let mut days: Vec<String> = {
        let mut seen = std::collections::HashSet::new();
        entries.iter().map(|e| e.day.clone()).filter(|d| seen.insert(d.clone())).collect()
    };
    days.sort();

    days.into_iter()
        .map(|day| {
            let group: Vec<TimelineEntry> =
                entries.iter().filter(|e| e.day == day).cloned().collect();
            let label = if day.is_empty() { "(unknown date)".to_owned() } else { day };
            (label, group)
        })
        .collect()
}

/// Normalise token counts to bar widths in the range `[MIN_PX, MAX_PX]` pixels.
///
/// If all counts are zero or the slice is empty, every entry gets `MIN_PX`.
pub const MIN_PX: u64 = 24;
pub const MAX_PX: u64 = 240;

#[must_use]
pub fn normalize_widths(entries: &[TimelineEntry]) -> Vec<u64> {
    let max = entries.iter().map(|e| e.token_count).max().unwrap_or(0);
    entries
        .iter()
        .map(|e| {
            if max == 0 {
                MIN_PX
            } else {
                let ratio = e.token_count as f64 / max as f64;
                (MIN_PX as f64 + ratio * (MAX_PX - MIN_PX) as f64).round() as u64
            }
        })
        .collect()
}

// ---------------------------------------------------------------------------
// Colour helpers
// ---------------------------------------------------------------------------

/// Map a model name to a CSS HSL hue (0–359) via a simple hash.
#[must_use]
pub fn model_hue(model: &str) -> u16 {
    let hash: u32 =
        model.bytes().fold(5381u32, |acc, b| acc.wrapping_mul(31).wrapping_add(b as u32));
    (hash % 360) as u16
}

/// Return a CSS `hsl(hue, 60%, 55%)` colour string for a model name.
#[must_use]
pub fn model_color(model: &str) -> String {
    format!("hsl({}, 60%, 55%)", model_hue(model))
}

// ---------------------------------------------------------------------------
// Dioxus component
// ---------------------------------------------------------------------------

/// Timeline view component.
///
/// Renders bundles grouped by day as a horizontal scrollable lane.
/// Width of each bar is proportional to `token_count`.
/// Bar colour is derived from `model` name.
/// Clicking a bar selects it; metadata appears in a tooltip panel below.
#[component]
pub fn TimelineView(bundles: Vec<ContinuationBundle>) -> Element {
    let entries: Vec<TimelineEntry> = bundles.iter().map(TimelineEntry::from_bundle).collect();

    let mut selected: Signal<Option<usize>> = use_signal(|| None);

    // Build flat list with widths for rendering.
    let widths = normalize_widths(&entries);
    let groups = group_by_day(&entries);

    // Build a flat index mapping: (day_idx, entry_within_day) -> global idx
    // We need the global index from the `entries` vec for the tooltip.
    // Build a lookup: source_id -> global index.
    let id_to_global: std::collections::HashMap<String, usize> =
        entries.iter().enumerate().map(|(i, e)| (e.source_id.clone(), i)).collect();

    let selected_entry = selected().and_then(|i| entries.get(i)).cloned();

    rsx! {
        style {
            r#"
                .timeline-root {{ display: flex; flex-direction: column; height: 100%; }}
                .timeline-scroll {{ flex: 1; overflow-x: auto; overflow-y: auto; padding: 16px 20px; }}
                .timeline-day-group {{ margin-bottom: 24px; }}
                .timeline-day-label {{
                    font-size: 11px; font-weight: 700; text-transform: uppercase;
                    letter-spacing: 0.6px; color: #8b8fa3; margin-bottom: 10px;
                    padding-bottom: 4px; border-bottom: 1px solid #2a2d35;
                }}
                .timeline-lane {{ display: flex; flex-wrap: wrap; gap: 6px; align-items: flex-end; }}
                .tl-bar {{
                    height: 40px; border-radius: 4px; cursor: pointer;
                    transition: opacity 0.15s, transform 0.15s; opacity: 0.82;
                    flex-shrink: 0; position: relative;
                }}
                .tl-bar:hover {{ opacity: 1; transform: scaleY(1.08); }}
                .tl-bar.selected {{ opacity: 1; outline: 2px solid #ffffff44; }}
                .timeline-tooltip {{
                    flex-shrink: 0; background: #161822; border-top: 1px solid #2a2d35;
                    padding: 16px 20px; min-height: 120px;
                }}
                .tt-source {{ font-size: 14px; font-weight: 600; color: #c8cdd6; margin-bottom: 6px; }}
                .tt-goal {{ font-size: 13px; color: #8b8fa3; margin-bottom: 10px; line-height: 1.5; }}
                .tt-meta {{ display: flex; flex-wrap: wrap; gap: 12px; font-size: 11px; color: #8b8fa3; }}
                .tt-meta span {{ display: flex; gap: 4px; align-items: center; }}
                .tt-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
                .badge {{ display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; }}
                .badge-ok {{ background: #1a3a2a; color: #4ade80; }}
                .badge-contract {{ background: #2a1a3a; color: #c084fc; }}
                .tt-empty {{ display: flex; align-items: center; justify-content: center;
                    height: 120px; color: #8b8fa3; font-size: 13px; }}
            "#,
        }
        div { class: "timeline-root",
            div { class: "timeline-scroll",
                if entries.is_empty() {
                    div { class: "tt-empty", "No bundles to display" }
                } else {
                    for (day_label, group) in groups.iter() {
                        div { class: "timeline-day-group",
                            div { class: "timeline-day-label", "{day_label}" }
                            div { class: "timeline-lane",
                                for entry in group.iter() {
                                    {
                                        let global_idx = id_to_global.get(&entry.source_id).copied().unwrap_or(0);
                                        let width_px = widths.get(global_idx).copied().unwrap_or(MIN_PX);
                                        let color = model_color(&entry.model);
                                        let is_sel = selected() == Some(global_idx);
                                        let bar_cls = if is_sel { "tl-bar selected" } else { "tl-bar" };
                                        rsx! {
                                            div {
                                                class: "{bar_cls}",
                                                style: "width:{width_px}px; background:{color};",
                                                title: "{entry.goal}",
                                                onclick: move |_| {
                                                    if selected() == Some(global_idx) {
                                                        selected.set(None);
                                                    } else {
                                                        selected.set(Some(global_idx));
                                                    }
                                                },
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
            div { class: "timeline-tooltip",
                match selected_entry {
                    Some(e) => rsx! {
                        div { class: "tt-source", "{e.source_id}" }
                        div { class: "tt-goal", "{e.goal}" }
                        div { class: "tt-meta",
                            span {
                                div {
                                    class: "tt-dot",
                                    style: "background:{model_color(&e.model)};",
                                }
                                "{e.model}"
                            }
                            span { "󰆧 {e.message_count} slices" }
                            span { "{e.token_count} tokens" }
                            if !e.created_at.is_empty() {
                                span { "{e.created_at}" }
                            }
                            if e.has_acceptance {
                                span { class: "badge badge-ok", "✓ AC" }
                            }
                            if e.has_contract {
                                span { class: "badge badge-contract", "◎ CT" }
                            }
                        }
                    },
                    None => rsx! {
                        div { class: "tt-empty", "Click a bar to view bundle details" }
                    },
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Unit tests for pure functions
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_entry(source_id: &str, day: &str, token_count: u64, model: &str) -> TimelineEntry {
        TimelineEntry {
            source_id: source_id.into(),
            day: day.into(),
            created_at: if day.is_empty() { String::new() } else { format!("{day}T00:00:00Z") },
            token_count,
            model: model.into(),
            goal: "test goal".into(),
            message_count: 3,
            has_acceptance: false,
            has_contract: false,
        }
    }

    #[test]
    fn group_by_day_sorts_days_ascending() {
        let entries = vec![
            make_entry("b", "2024-03-15", 10, "gpt-4"),
            make_entry("a", "2024-01-01", 5, "claude"),
            make_entry("c", "2024-03-15", 7, "gemini"),
        ];
        let groups = group_by_day(&entries);
        assert_eq!(groups.len(), 2);
        assert_eq!(groups[0].0, "2024-01-01");
        assert_eq!(groups[1].0, "2024-03-15");
        assert_eq!(groups[1].1.len(), 2);
    }

    #[test]
    fn group_by_day_unknown_date_label() {
        let entries = vec![make_entry("x", "", 0, "model")];
        let groups = group_by_day(&entries);
        assert_eq!(groups[0].0, "(unknown date)");
    }

    #[test]
    fn normalize_widths_max_gets_max_px() {
        let entries =
            vec![make_entry("a", "2024-01-01", 100, "m"), make_entry("b", "2024-01-01", 0, "m")];
        let widths = normalize_widths(&entries);
        assert_eq!(widths[0], MAX_PX);
        assert_eq!(widths[1], MIN_PX);
    }

    #[test]
    fn normalize_widths_all_zero_returns_min() {
        let entries =
            vec![make_entry("a", "2024-01-01", 0, "m"), make_entry("b", "2024-01-01", 0, "m")];
        let widths = normalize_widths(&entries);
        assert!(widths.iter().all(|&w| w == MIN_PX));
    }

    #[test]
    fn model_hue_is_deterministic_and_in_range() {
        let h1 = model_hue("gpt-4");
        let h2 = model_hue("gpt-4");
        assert_eq!(h1, h2);
        assert!(h1 < 360);
        // Different models should (generally) produce different hues.
        assert_ne!(model_hue("gpt-4"), model_hue("claude-3-opus"));
    }
}
