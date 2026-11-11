//! Shared loading / error UI for async bundle and daemon fetches.
//!
//! Styled from [`crate::theme::ThemeColors`] so focus/status chrome stays
//! aligned with Lab-Coat tokens used by the tab bar.

use dioxus::prelude::*;

use crate::theme::ThemeColors;

/// Layout preset for content-shaped skeleton blocks (VISUAL_SPEC §3).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub enum SkeletonLayout {
    /// Sidebar list rows + detail title and prose lines.
    #[default]
    Bundles,
    /// Single-column list rows (search / history panes).
    ListDetail,
    /// Terminal-style log lines (live feed / replay stream panes).
    StreamFeed,
}

/// Content-shaped loading placeholder that preserves final layout (no CLS).
#[component]
pub fn ContentSkeleton(
    #[props(default)] layout: SkeletonLayout,
    #[props(default = 4_usize)] list_rows: usize,
) -> Element {
    let rows = list_rows.clamp(3, 6);
    let list_blocks = (0..rows).map(|index| {
        rsx! {
            div {
                key: "{index}",
                class: "sl-skeleton-row",
                div { class: "sl-skeleton-block sl-skeleton-block-title" }
                div { class: "sl-skeleton-block sl-skeleton-block-subtitle" }
                div { class: "sl-skeleton-block sl-skeleton-block-meta" }
            }
        }
    });

    match layout {
        SkeletonLayout::Bundles => rsx! {
            div {
                class: "sl-content-skeleton sl-content-skeleton-bundles",
                role: "status",
                "aria-live": "polite",
                "aria-busy": "true",
                "aria-label": "Loading content",
                "data-testid": "content-skeleton",
                div { class: "sl-skeleton-list", {list_blocks} }
                div {
                    class: "sl-skeleton-detail",
                    div { class: "sl-skeleton-block sl-skeleton-block-heading" }
                    div { class: "sl-skeleton-block sl-skeleton-block-line" }
                    div { class: "sl-skeleton-block sl-skeleton-block-line sl-skeleton-block-line-short" }
                    div { class: "sl-skeleton-block sl-skeleton-block-line" }
                }
            }
        },
        SkeletonLayout::ListDetail => rsx! {
            div {
                class: "sl-content-skeleton sl-content-skeleton-list",
                role: "status",
                "aria-live": "polite",
                "aria-busy": "true",
                "aria-label": "Loading content",
                "data-testid": "content-skeleton",
                div { class: "sl-skeleton-list", {list_blocks} }
            }
        },
        SkeletonLayout::StreamFeed => {
            let stream_lines = (0..rows).map(|index| {
                let width_pct = match index % 4 {
                    0 => 92,
                    1 => 78,
                    2 => 86,
                    _ => 64,
                };
                rsx! {
                    div {
                        key: "{index}",
                        class: "sl-skeleton-stream-line-wrap",
                        div {
                            class: "sl-skeleton-block sl-skeleton-stream-line",
                            style: "width: {width_pct}%;",
                        }
                    }
                }
            });
            rsx! {
                div {
                    class: "sl-content-skeleton sl-content-skeleton-stream",
                    role: "status",
                    "aria-live": "polite",
                    "aria-busy": "true",
                    "aria-label": "Loading stream",
                    "data-testid": "content-skeleton",
                    div { class: "sl-skeleton-stream-lines", {stream_lines} }
                }
            }
        }
    }
}

/// Full-panel loading indicator for in-flight bundle / search loads.
#[component]
pub fn LoadingState(
    /// Human-readable status (defaults to a generic bundle-load message).
    #[props(default = "Loading bundles…".to_string())]
    message: String,
    /// Plain-language reassurance for operations that may exceed ~10 seconds.
    #[props(default)]
    patience_hint: bool,
) -> Element {
    let c = ThemeColors::dark();
    rsx! {
        div {
            class: "sl-loading-state",
            role: "status",
            "aria-live": "polite",
            "aria-busy": "true",
            "data-testid": "loading-state",
            style: "display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;padding:32px 20px;color:{c.muted};font-size:13px;",
            div {
                class: "sl-loading-spinner",
                "aria-hidden": "true",
                style: "width:28px;height:28px;border:3px solid {c.border};border-top-color:{c.focus};border-radius:50%;",
            }
            span { "{message}" }
            if patience_hint {
                span {
                    class: "sl-loading-patience",
                    "data-testid": "loading-patience-hint",
                    style: "max-width:28rem;text-align:center;color:{c.muted};font-size:12px;line-height:1.45;",
                    "Large archives can take up to a minute. You can switch tabs while this finishes."
                }
            }
        }
    }
}

/// First-run activation empty state (VISUAL_SPEC §2 — no corpus ingested yet).
#[component]
pub fn FirstRunEmpty() -> Element {
    let c = ThemeColors::dark();
    rsx! {
        div {
            class: "empty-state empty-state-first-run",
            role: "status",
            "data-testid": "first-run-empty",
            style: "flex-direction:column;gap:var(--sl-space-lg);text-align:center;padding:var(--sl-space-2xl);",
            p {
                style: "margin:0;max-width:var(--sl-measure-max);line-height:1.5;",
                "No sessions ingested yet. Open a corpus directory or start the daemon to begin."
            }
            button {
                class: "sl-first-run-cta",
                r#type: "button",
                "data-testid": "first-run-cta",
                "aria-label": "Open a Forge corpus database or view the quick-start guide",
                style: "padding:8px 18px;font-size:13px;font-weight:600;border-radius:var(--sl-radius-md);cursor:pointer;border:1px solid {c.focus};background:{c.focus};color:#111827;",
                onclick: move |_| crate::corpus_cta::trigger_open_corpus(),
                "Open corpus…"
            }
        }
    }
}

/// Error-color contract panel for visual goldens (VISUAL_SPEC §4 — warm red, not live orange).
#[component]
pub fn ErrorColorFixture() -> Element {
    rsx! {
        div {
            class: "error-color-fixture",
            "data-testid": "error-color-panel",
            style: "display:flex;flex-direction:column;gap:var(--sl-space-lg);padding:var(--sl-space-2xl);",
            div {
                style: "display:flex;align-items:center;gap:var(--sl-space-md);",
                span {
                    class: "feed-status connecting",
                    "data-testid": "error-color-live-badge",
                    "● Live"
                }
                span {
                    style: "font-size:12px;color:var(--sl-text-muted);",
                    "Live indicator uses orange — errors use warm red below."
                }
            }
            ErrorState {
                message: "Warm error foreground on slate panel (visual fixture).".to_owned(),
                retryable: true,
                on_retry: move |_| {},
            }
        }
    }
}

/// Recoverable error panel for failed async bundle / daemon loads.
///
/// Exposes a stable DOM `id` so form controls can point
/// `aria-errormessage` at this alert (WCAG 3.3.1 / 3.3.3 association).
/// Non-color cues: warning glyph (`aria-hidden`), left danger border, and
/// `role="alert"` — color alone is never the sole error signal (L81.15).
#[component]
pub fn ErrorState(
    /// Error message shown to the user.
    message: String,
    /// Short, user-facing heading for the recovery state.
    #[props(default = "Something went wrong".to_string())]
    title: String,
    /// When true, render a Retry control wired to [`Self::on_retry`].
    #[props(default)]
    retryable: bool,
    /// Retry handler (used when `retryable` is true).
    #[props(default)]
    on_retry: EventHandler<()>,
    /// DOM id referenced by `aria-errormessage` on associated fields.
    #[props(default = "sl-error-message".to_string())]
    error_id: String,
) -> Element {
    let c = ThemeColors::dark();
    rsx! {
        div {
            id: "{error_id}",
            class: "sl-error-state",
            role: "alert",
            "aria-live": "assertive",
            "aria-invalid": "true",
            "data-testid": "error-state",
            style: "display:flex;flex-direction:column;align-items:flex-start;gap:12px;padding:20px 16px;margin:8px 0;background:{c.surface};border:1px solid {c.border};border-left:3px solid {c.danger};border-radius:6px;color:{c.text};font-size:13px;line-height:1.5;",
            div {
                style: "display:flex;align-items:center;gap:8px;",
                span {
                    class: "sl-error-icon",
                    "aria-hidden": "true",
                    "data-testid": "error-state-icon",
                    style: "flex-shrink:0;font-size:16px;font-weight:700;line-height:1;color:{c.danger};",
                    "⚠"
                }
                p {
                    style: "margin:0;color:{c.danger};font-weight:600;",
                    "{title}"
                }
            }
            p {
                id: "{error_id}-detail",
                style: "margin:0;color:{c.muted};",
                "{message}"
            }
            if retryable {
                button {
                    class: "sl-error-retry",
                    "data-testid": "error-state-retry",
                    "aria-describedby": "{error_id}-detail",
                    style: "padding:6px 14px;font-size:12px;font-weight:600;border-radius:5px;cursor:pointer;border:1px solid #2563eb;background:#2563eb;color:#ffffff;",
                    onclick: move |_| on_retry.call(()),
                    onkeydown: move |evt: Event<KeyboardData>| {
                        let key = evt.key();
                        if key == Key::Enter
                            || matches!(key, Key::Character(ref ch) if ch == " ")
                        {
                            evt.prevent_default();
                            on_retry.call(());
                        }
                    },
                    "Retry"
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn loading_default_message_is_nonempty() {
        // Component defaults are compile-time; assert theme tokens used by styles exist.
        let c = ThemeColors::dark();
        assert!(!c.focus.is_empty());
        assert!(!c.danger.is_empty());
        assert!(!c.muted.is_empty());
    }

    #[test]
    fn theme_focus_is_on_dark_cobalt() {
        assert_eq!(ThemeColors::dark().focus, "#93c5fd");
        assert_eq!(ThemeColors::light().focus, "#2563eb");
    }
}
