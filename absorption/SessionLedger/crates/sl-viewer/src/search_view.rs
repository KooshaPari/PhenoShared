//! Search / filter view for the sl-viewer.
//!
//! Renders a form that calls `GET /api/search` on the sl-daemon HTTP API and
//! displays results in the same card style used by the Bundles tab.

use dioxus::prelude::*;
use serde::{Deserialize, Serialize};

use crate::async_states::{ContentSkeleton, ErrorState, SkeletonLayout};
use crate::daemon_url::daemon_api_url;
use crate::fixture::query_fixture_active;

/// Slim bundle metadata returned by `GET /api/search`.
#[derive(Debug, Clone, PartialEq, Deserialize, Serialize)]
pub struct SearchResult {
    #[serde(default)]
    pub session_id: String,
    #[serde(default)]
    pub created_at: String,
    #[serde(default)]
    pub model: String,
    #[serde(default)]
    pub token_count: u64,
    #[serde(default)]
    pub message_count: u64,
    #[serde(default)]
    pub user_turn_count: u64,
    #[serde(default)]
    pub duration_ms: u64,
    #[serde(default)]
    pub tags: Vec<String>,
}

/// Build the `/api/search` query string from form values.
///
/// This is a pure function exposed for unit-testing.
pub fn build_query(
    since: &str,
    until: &str,
    model: &str,
    min_tokens: &str,
    tags: &str,
    limit: &str,
) -> String {
    let mut parts: Vec<String> = Vec::new();

    let since = since.trim();
    if !since.is_empty() {
        parts.push(format!("since={}", urlencoding(since)));
    }
    let until = until.trim();
    if !until.is_empty() {
        parts.push(format!("until={}", urlencoding(until)));
    }
    let model = model.trim();
    if !model.is_empty() {
        parts.push(format!("model={}", urlencoding(model)));
    }
    let min_tokens = min_tokens.trim();
    if !min_tokens.is_empty() {
        parts.push(format!("min_tokens={}", urlencoding(min_tokens)));
    }
    let tags = tags.trim();
    if !tags.is_empty() {
        // Comma-separated tags; passed as single `tags` query param and split
        // by the daemon.
        parts.push(format!("tags={}", urlencoding(tags)));
    }
    let limit = limit.trim();
    let limit_val = limit.parse::<usize>().unwrap_or(50);
    parts.push(format!("limit={limit_val}"));

    parts.join("&")
}

/// Minimal percent-encoder — encodes the characters that break query strings.
fn urlencoding(s: &str) -> String {
    s.chars()
        .flat_map(|c| match c {
            ' ' => vec!['%', '2', '0'],
            ',' => vec!['%', '2', 'C'],
            '#' => vec!['%', '2', '3'],
            '&' => vec!['%', '2', '6'],
            '=' => vec!['%', '3', 'D'],
            '+' => vec!['%', '2', 'B'],
            _ => vec![c],
        })
        .collect()
}

fn user_turn_label(user_turn_count: u64) -> &'static str {
    if user_turn_count == 1 {
        "user turn"
    } else {
        "user turns"
    }
}

/// Stable id for search fetch errors — paired with `aria-errormessage` on fields.
const SEARCH_ERROR_ID: &str = "search-error-message";

/// Region id for the collapsible advanced-filter panel (`aria-controls`).
const SEARCH_ADVANCED_ID: &str = "search-advanced-filters";

/// Count of advanced filters that differ from defaults (recognition cue).
pub fn advanced_filter_active_count(min_tokens: &str, tags: &str, limit: &str) -> usize {
    let mut n = 0;
    if !min_tokens.trim().is_empty() {
        n += 1;
    }
    if !tags.trim().is_empty() {
        n += 1;
    }
    if limit.trim() != "50" {
        n += 1;
    }
    n
}

/// Search / filter panel.
///
/// Primary fields (`since`, `until`, `model`) stay visible. Advanced filters
/// (`min_tokens`, `tags`, `limit`) live behind a progressive-disclosure
/// control so operators recognize common actions without recalling every
/// query parameter. Clicking **Search** fires `GET /api/search` on the
/// sl-daemon and renders results as bundle cards. **Clear** asks for a
/// lightweight confirmation before wiping filters, results, and errors.
#[component]
pub fn SearchView() -> Element {
    let mut since = use_signal(String::new);
    let mut until = use_signal(String::new);
    let mut model = use_signal(String::new);
    let mut min_tokens = use_signal(String::new);
    let mut tags = use_signal(String::new);
    let mut limit = use_signal(|| "50".to_string());

    let mut results: Signal<Vec<SearchResult>> = use_signal(Vec::new);
    let mut error: Signal<Option<String>> = use_signal(|| None);
    let loading = use_signal(|| false);
    let mut selected_idx: Signal<Option<usize>> = use_signal(|| None);

    let mut search_tick: Signal<u32> = use_signal(|| 0u32);
    let mut zero_match: Signal<bool> = use_signal(|| false);
    let mut clear_pending: Signal<bool> = use_signal(|| false);
    let mut advanced_open: Signal<bool> = use_signal(|| false);

    if query_fixture_active("search-empty") {
        return rsx! {
            SearchFixtureChrome { invalid: false }
            div { class: "search-results",
                div {
                    class: "search-empty",
                    "data-testid": "search-zero-match",
                    "No bundles matched your filters. Adjust the fields above or choose Clear."
                }
            }
        };
    }

    if query_fixture_active("search-error") {
        let mut show_error = use_signal(|| true);
        return rsx! {
            div {
                class: "search-view",
                onkeydown: move |evt: Event<KeyboardData>| {
                    if evt.key() == Key::Escape && show_error() {
                        evt.prevent_default();
                        show_error.set(false);
                    }
                },
                SearchFixtureChrome { invalid: show_error() }
                div { class: "search-results",
                    if show_error() {
                        ErrorState {
                            message: "daemon not reachable: connection refused (visual fixture)".to_owned(),
                            retryable: true,
                            on_retry: move |_| {},
                            error_id: SEARCH_ERROR_ID.to_owned(),
                        }
                    }
                }
            }
        };
    }

    // Shared Search / Retry path — bump `search_tick` to fire a fetch.
    use_effect(move || {
        let tick = search_tick();
        if tick == 0 {
            return;
        }
        let qs = build_query(&since(), &until(), &model(), &min_tokens(), &tags(), &limit());
        let url = format!("{}?{qs}", daemon_api_url("/api/search"));
        let mut results = results;
        let mut error = error;
        let mut loading = loading;
        let mut zero_match = zero_match;
        let mut clear_pending = clear_pending;

        loading.set(true);
        error.set(None);
        clear_pending.set(false);

        spawn(async move {
            match reqwest_search(&url).await {
                Ok(data) => {
                    let empty = data.is_empty();
                    results.set(data);
                    error.set(None);
                    zero_match.set(empty);
                }
                Err(e) => {
                    error.set(Some(e));
                    zero_match.set(false);
                }
            }
            loading.set(false);
        });
    });

    let on_clear_request = move |_| {
        let clearable = !since().is_empty()
            || !until().is_empty()
            || !model().is_empty()
            || !min_tokens().is_empty()
            || !tags().is_empty()
            || limit() != "50"
            || !results.is_empty()
            || error().is_some()
            || zero_match();
        if clearable {
            clear_pending.set(true);
        }
    };

    let on_clear_confirm = move |_| {
        since.set(String::new());
        until.set(String::new());
        model.set(String::new());
        min_tokens.set(String::new());
        tags.set(String::new());
        limit.set("50".to_string());
        results.set(Vec::new());
        error.set(None);
        selected_idx.set(None);
        zero_match.set(false);
        clear_pending.set(false);
        advanced_open.set(false);
    };

    let on_clear_cancel = move |_| {
        clear_pending.set(false);
    };

    let result_count = results.len();
    let plural = if result_count == 1 { "" } else { "s" };
    let has_error = error().is_some();
    let invalid_attr = if has_error { "true" } else { "false" };
    let errormessage_attr = if has_error { SEARCH_ERROR_ID } else { "" };

    let advanced_count = advanced_filter_active_count(&min_tokens(), &tags(), &limit());
    let advanced_expanded = advanced_open();
    let toggle_label =
        if advanced_expanded { "Hide advanced filters" } else { "Show advanced filters" };
    let chevron = if advanced_expanded { "▾" } else { "▸" };

    rsx! {
        div {
            class: "search-view",
            onkeydown: move |evt: Event<KeyboardData>| {
                if evt.key() == Key::Escape {
                    evt.prevent_default();
                    if clear_pending() {
                        clear_pending.set(false);
                        return;
                    }
                    since.set(String::new());
                    until.set(String::new());
                    model.set(String::new());
                    min_tokens.set(String::new());
                    tags.set(String::new());
                    limit.set("50".to_string());
                    results.set(Vec::new());
                    error.set(None);
                    selected_idx.set(None);
                    zero_match.set(false);
                    advanced_open.set(false);
                }
            },
            // ---- Filter form ----
            div { class: "search-form",
                h2 { class: "search-form-title",
                    "Search Bundles"
                }
                p { class: "search-form-hint",
                    "Date and model stay visible. Open advanced filters only when you need tokens, tags, or limit."
                }
                div { class: "search-fields",
                    label { class: "search-label", r#for: "search-since", "Since (YYYY-MM-DD)" }
                    input {
                        id: "search-since",
                        class: "search-input",
                        placeholder: "2024-01-01",
                        value: "{since}",
                        "aria-invalid": "{invalid_attr}",
                        "aria-errormessage": "{errormessage_attr}",
                        oninput: move |e| since.set(e.value()),
                    }
                    label { class: "search-label", r#for: "search-until", "Until (YYYY-MM-DD)" }
                    input {
                        id: "search-until",
                        class: "search-input",
                        placeholder: "2024-12-31",
                        value: "{until}",
                        "aria-invalid": "{invalid_attr}",
                        "aria-errormessage": "{errormessage_attr}",
                        oninput: move |e| until.set(e.value()),
                    }
                    label { class: "search-label", r#for: "search-model", "Model (substring)" }
                    input {
                        id: "search-model",
                        class: "search-input",
                        placeholder: "claude",
                        value: "{model}",
                        "aria-invalid": "{invalid_attr}",
                        "aria-errormessage": "{errormessage_attr}",
                        oninput: move |e| model.set(e.value()),
                    }
                    button {
                        class: "search-advanced-toggle",
                        r#type: "button",
                        "data-testid": "search-advanced-toggle",
                        "aria-expanded": if advanced_expanded { "true" } else { "false" },
                        "aria-controls": SEARCH_ADVANCED_ID,
                        onclick: move |_| advanced_open.with_mut(|open| *open = !*open),
                        span { class: "search-advanced-chevron", "aria-hidden": "true", "{chevron}" }
                        span { "{toggle_label}" }
                        if advanced_count > 0 {
                            span {
                                class: "search-advanced-badge",
                                "data-testid": "search-advanced-badge",
                                "{advanced_count} active"
                            }
                        }
                    }
                    div {
                        id: SEARCH_ADVANCED_ID,
                        class: if advanced_expanded {
                            "search-advanced-panel"
                        } else {
                            "search-advanced-panel is-collapsed"
                        },
                        "data-testid": "search-advanced-panel",
                        role: "group",
                        "aria-label": "Advanced search filters",
                        hidden: !advanced_expanded,
                        label { class: "search-label", r#for: "search-min-tokens", "Min Tokens" }
                        input {
                            id: "search-min-tokens",
                            class: "search-input",
                            r#type: "number",
                            placeholder: "1000",
                            value: "{min_tokens}",
                            "aria-invalid": "{invalid_attr}",
                            "aria-errormessage": "{errormessage_attr}",
                            tabindex: if advanced_expanded { "0" } else { "-1" },
                            oninput: move |e| min_tokens.set(e.value()),
                        }
                        label { class: "search-label", r#for: "search-tags", "Tags (comma-separated)" }
                        input {
                            id: "search-tags",
                            class: "search-input",
                            placeholder: "rust, ml",
                            value: "{tags}",
                            "aria-invalid": "{invalid_attr}",
                            "aria-errormessage": "{errormessage_attr}",
                            tabindex: if advanced_expanded { "0" } else { "-1" },
                            oninput: move |e| tags.set(e.value()),
                        }
                        label { class: "search-label", r#for: "search-limit", "Limit" }
                        input {
                            id: "search-limit",
                            class: "search-input",
                            r#type: "number",
                            value: "{limit}",
                            "aria-invalid": "{invalid_attr}",
                            "aria-errormessage": "{errormessage_attr}",
                            tabindex: if advanced_expanded { "0" } else { "-1" },
                            oninput: move |e| limit.set(e.value()),
                        }
                    }
                }
                div { class: "search-actions",
                    button {
                        class: "search-btn search-btn-primary",
                        onclick: move |_| search_tick.with_mut(|t| *t += 1),
                        if loading() { "Searching…" } else { "Search" }
                    }
                    if clear_pending() {
                        div {
                            class: "search-clear-confirm",
                            role: "alertdialog",
                            "aria-modal": "false",
                            "aria-labelledby": "search-clear-title",
                            "aria-describedby": "search-clear-desc",
                            "data-testid": "search-clear-confirm",
                            p {
                                id: "search-clear-title",
                                class: "search-clear-title",
                                "Clear search?"
                            }
                            p {
                                id: "search-clear-desc",
                                class: "search-clear-desc",
                                "This removes filters, results, and any error message."
                            }
                            button {
                                class: "search-btn search-btn-primary",
                                "data-testid": "search-clear-confirm-btn",
                                onclick: on_clear_confirm,
                                "Confirm clear"
                            }
                            button {
                                class: "search-btn",
                                "data-testid": "search-clear-cancel-btn",
                                onclick: on_clear_cancel,
                                "Cancel"
                            }
                        }
                    } else {
                        button {
                            class: "search-btn",
                            "data-testid": "search-clear-btn",
                            onclick: on_clear_request,
                            "Clear"
                        }
                    }
                }
            }

            // ---- Results ----
            div { class: "search-results",
                if let Some(ref msg) = error() {
                    ErrorState {
                        message: msg.clone(),
                        retryable: true,
                        on_retry: move |_| search_tick.with_mut(|t| *t += 1),
                        error_id: SEARCH_ERROR_ID.to_owned(),
                    }
                }
                if loading() {
                    ContentSkeleton { layout: SkeletonLayout::ListDetail, list_rows: 5 }
                }
                if zero_match() && !loading() && error().is_none() {
                    div {
                        class: "search-empty",
                        "data-testid": "search-zero-match",
                        "No bundles matched your filters. Adjust the fields above or choose Clear."
                    }
                }
                if !results.is_empty() && !loading() {
                    div { class: "session-count",
                        "{result_count} result{plural}"
                    }
                }
                for (idx, result) in results.iter().enumerate() {
                    {
                        let is_selected = selected_idx() == Some(idx);
                        let cls = if is_selected { "session-item selected" } else { "session-item" };
                        let r = result.clone();
                        let tags_display = r.tags.join(", ");
                        let user_turn_label = user_turn_label(r.user_turn_count);
                        rsx! {
                            div {
                                key: "{r.session_id}-{idx}",
                                class: "{cls}",
                                onclick: move |_| selected_idx.set(Some(idx)),
                                div { class: "session-source", "{r.session_id}" }
                                div { class: "session-goal", "model: {r.model}" }
                                div { class: "session-meta",
                                    span { class: "meta-bundles", "{r.token_count} tokens" }
                                    if r.user_turn_count > 0 {
                                        span { class: "session-meta-muted", "{r.user_turn_count} {user_turn_label}" }
                                    }
                                    span { class: "session-meta-muted", "{r.created_at}" }
                                    if !tags_display.is_empty() {
                                        span { class: "badge badge-ok", "{tags_display}" }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

/// Static search chrome shared by visual fixture routes.
#[component]
fn SearchFixtureChrome(invalid: bool) -> Element {
    let invalid_attr = if invalid { "true" } else { "false" };
    let errormessage_attr = if invalid { SEARCH_ERROR_ID } else { "" };
    rsx! {
        div { class: "search-form",
            h2 { class: "search-form-title",
                "Search Bundles"
            }
            p { class: "search-form-hint",
                "Date and model stay visible. Open advanced filters only when you need tokens, tags, or limit."
            }
            div { class: "search-fields",
                label { class: "search-label", r#for: "search-since-fixture", "Since (YYYY-MM-DD)" }
                input {
                    id: "search-since-fixture",
                    class: "search-input",
                    placeholder: "2024-01-01",
                    readonly: true,
                    "aria-invalid": "{invalid_attr}",
                    "aria-errormessage": "{errormessage_attr}",
                }
                label { class: "search-label", r#for: "search-model-fixture", "Model (substring)" }
                input {
                    id: "search-model-fixture",
                    class: "search-input",
                    placeholder: "claude",
                    readonly: true,
                    "aria-invalid": "{invalid_attr}",
                    "aria-errormessage": "{errormessage_attr}",
                }
                button {
                    class: "search-advanced-toggle",
                    r#type: "button",
                    "data-testid": "search-advanced-toggle",
                    "aria-expanded": "false",
                    "aria-controls": SEARCH_ADVANCED_ID,
                    disabled: true,
                    span { class: "search-advanced-chevron", "aria-hidden": "true", "▸" }
                    span { "Show advanced filters" }
                }
            }
            div { class: "search-actions",
                button { class: "search-btn search-btn-primary", disabled: true, "Search" }
                button { class: "search-btn", disabled: true, "Clear" }
            }
        }
    }
}

/// Cross-platform HTTP fetch used by the desktop and WASM renderers.
///
/// Returns the parsed results or an error string.
async fn reqwest_search(url: &str) -> Result<Vec<SearchResult>, String> {
    let client = reqwest::Client::new();
    let resp = client.get(url).send().await.map_err(|e| format!("daemon not reachable: {e}"))?;

    if !resp.status().is_success() {
        let status = resp.status();
        let body = resp.text().await.unwrap_or_default();
        return Err(format!("daemon returned {status}: {body}"));
    }

    resp.json::<Vec<SearchResult>>().await.map_err(|e| format!("failed to parse response: {e}"))
}

// ---------------------------------------------------------------------------
// Unit tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn build_query_all_fields() {
        let q = build_query("2024-01-01", "2024-12-31", "claude", "500", "rust,ml", "10");
        assert!(q.contains("since=2024-01-01"), "since present");
        assert!(q.contains("until=2024-12-31"), "until present");
        assert!(q.contains("model=claude"), "model present");
        assert!(q.contains("min_tokens=500"), "min_tokens present");
        assert!(q.contains("tags=rust"), "tags present");
        assert!(q.contains("limit=10"), "limit present");
    }

    #[test]
    fn build_query_empty_fields_omitted() {
        let q = build_query("", "", "", "", "", "50");
        assert!(!q.contains("since="), "since absent");
        assert!(!q.contains("until="), "until absent");
        assert!(!q.contains("model="), "model absent");
        assert!(!q.contains("min_tokens="), "min_tokens absent");
        assert!(!q.contains("tags="), "tags absent");
        assert!(q.contains("limit=50"), "default limit present");
    }

    #[test]
    fn build_query_invalid_limit_defaults_to_50() {
        let q = build_query("", "", "", "", "", "not_a_number");
        assert!(q.contains("limit=50"), "falls back to 50");
    }

    #[test]
    fn build_query_spaces_encoded() {
        let q = build_query("", "", "claude 3", "", "", "50");
        assert!(q.contains("model=claude%203"), "space encoded");
    }

    #[test]
    fn build_query_comma_in_tags_encoded() {
        let q = build_query("", "", "", "", "rust,ml", "50");
        // Comma is encoded as %2C in the tag list.
        assert!(q.contains("tags=rust%2Cml"), "comma encoded in tags");
    }

    #[test]
    fn advanced_filter_count_defaults_to_zero() {
        assert_eq!(advanced_filter_active_count("", "", "50"), 0);
    }

    #[test]
    fn advanced_filter_count_sums_non_defaults() {
        assert_eq!(advanced_filter_active_count("1000", "rust", "10"), 3);
        assert_eq!(advanced_filter_active_count("", "rust", "50"), 1);
        assert_eq!(advanced_filter_active_count(" ", "  ", "50"), 0);
    }

    #[test]
    fn user_turn_label_handles_singular_and_plural() {
        assert_eq!(user_turn_label(1), "user turn");
        assert_eq!(user_turn_label(2), "user turns");
    }
}
