//! Scrollable session/bundle list with a live search filter.
//!
//! Renders a column of [`SessionItem`] rows from a slice of
//! [`BundleSummary`] values, tracks selection via `selected_idx`, and filters
//! rows by a case-insensitive substring match against the goal and source id.

use dioxus::prelude::*;

use crate::bundle_list::BundleSummary;

/// Props for [`SessionList`].
#[derive(Props, Clone, PartialEq)]
pub struct SessionListProps {
    /// All summaries to display, in their canonical order.
    pub items: Vec<BundleSummary>,
    /// Index (into `items`) of the currently selected row, if any.
    pub selected_idx: Option<usize>,
    /// Fires with the original `items` index when a row is clicked.
    pub on_select: EventHandler<usize>,
}

/// A scrollable, filterable list of session bundles.
#[component]
pub fn SessionList(props: SessionListProps) -> Element {
    let mut query = use_signal(String::new);

    let needle = query().to_lowercase();
    let filtered: Vec<(usize, BundleSummary)> = props
        .items
        .iter()
        .enumerate()
        .filter(|(_, s)| {
            needle.is_empty()
                || s.intent_goal.to_lowercase().contains(&needle)
                || s.source_id.to_lowercase().contains(&needle)
        })
        .map(|(i, s)| (i, s.clone()))
        .collect();

    let count = filtered.len();
    let plural = if count == 1 { "" } else { "s" };

    rsx! {
        div { class: "session-list",
            input {
                class: "search-input",
                "aria-label": "Filter sessions",
                placeholder: "Filter sessions...",
                value: "{query}",
                oninput: move |e| query.set(e.value()),
            }
            div { class: "session-count", "{count} session{plural}" }
            for (orig_idx, summary) in filtered.into_iter() {
                SessionItem {
                    key: "{orig_idx}",
                    summary: summary,
                    selected: props.selected_idx == Some(orig_idx),
                    on_click: move |_| props.on_select.call(orig_idx),
                }
            }
        }
    }
}

/// Props for a single [`SessionItem`] row.
#[derive(Props, Clone, PartialEq)]
struct SessionItemProps {
    summary: BundleSummary,
    selected: bool,
    on_click: EventHandler<()>,
}

/// One clickable row in the [`SessionList`].
#[component]
fn SessionItem(props: SessionItemProps) -> Element {
    let cls = if props.selected { "session-item selected" } else { "session-item" };
    let s = &props.summary;
    rsx! {
        div {
            class: "{cls}",
            onclick: move |_| props.on_click.call(()),
            div { class: "session-source", "{s.source_id}" }
            div { class: "session-goal", "{s.intent_goal}" }
            div { class: "session-meta",
                span { class: "meta-bundles", "{s.bundle_count} slices" }
                if s.has_acceptance {
                    span { class: "badge badge-ok", "✓ AC" }
                }
                if s.has_contract {
                    span { class: "badge badge-contract", "◎ CT" }
                }
            }
        }
    }
}
