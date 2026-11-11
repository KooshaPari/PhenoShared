//! Raw Sessions tab — exposes the underlying `Vec<Session>` that every other
//! tab derives from, so users can see exactly what corpus discovery found
//! and reload discovery on demand.
//!
//! The toolbar holds three controls:
//! - **Reload discovery** — re-runs the existing Auto discovery with no
//!   overrides.
//! - **Pick folder…** — opens a native folder picker; the picked path is
//!   persisted to the platform config directory and added to the next
//!   discovery pass in addition to the defaults.
//! - **Reset to default** — appears whenever a custom path is set; clicking
//!   clears the persisted override and reverts to native-only discovery.

use dioxus::prelude::*;
use session_ledger::domain::session::{Corpus, Session};

use crate::app::{CustomCorpusPaths, DiscoveryState, ReloadTrigger, SessionContext};
use crate::corpus_cta::pick_corpus_folder;
use crate::corpus_loader::CustomCorpusPath;

/// Stable, human-readable label for a [`Corpus`].
fn corpus_label(corpus: Corpus) -> &'static str {
    match corpus {
        Corpus::Forge => "forge",
        Corpus::Codex => "codex",
        Corpus::ClaudeCode => "claude",
        Corpus::Cursor => "cursor",
        Corpus::FactoryDroid => "droid",
        Corpus::ChatGptWeb => "chatgpt",
        Corpus::ClaudeWeb => "claude web",
        Corpus::GeminiWeb => "gemini",
    }
}

/// Wall-clock timestamp (ms since epoch) of the most recent message in the
/// session, or `None` if the session has no messages or none are timestamped.
fn last_activity_ms(session: &Session) -> Option<i64> {
    session.messages.iter().filter_map(|m| m.ts_ms).max()
}

/// Format a millisecond timestamp as a short ISO-ish local date string,
/// falling back to "(no timestamp)" when the value is missing.
fn format_ms(ms: Option<i64>) -> String {
    match ms {
        Some(value) if value > 0 => {
            // Cheap, allocation-light format: YYYY-MM-DD HH:MM derived from
            // a naive UTC→local conversion. The viewer is a developer tool;
            // perfect locale handling isn't required here.
            let secs = value / 1000;
            let (y, mo, d, h, mi) = epoch_to_ymdhm(secs);
            format!("{y:04}-{mo:02}-{d:02} {h:02}:{mi:02}")
        }
        _ => "(no timestamp)".to_owned(),
    }
}

/// Pure UTC→calendar conversion (Gregorian, proleptic). Returns
/// (year, month_1_12, day_1_31, hour_0_23, minute_0_59) for the given epoch
/// seconds. Avoids pulling in a chrono dependency just for one date format.
fn epoch_to_ymdhm(secs: i64) -> (i32, u32, u32, u32, u32) {
    let days = secs.div_euclid(86_400);
    let rem = secs.rem_euclid(86_400);
    let h = (rem / 3600) as u32;
    let mi = ((rem % 3600) / 60) as u32;
    // Civil-from-days algorithm by Howard Hinnant (public domain).
    let z = days + 719_468;
    let era = if z >= 0 { z } else { z - 146_096 } / 146_097;
    let doe = (z - era * 146_097) as u64;
    let yoe = (doe - doe / 1460 + doe / 36_524 - doe / 146_096) / 365;
    let y = (yoe as i64) + era * 400;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let d = (doy - (153 * mp + 2) / 5 + 1) as u32;
    let m = if mp < 10 { mp + 3 } else { mp - 9 } as u32;
    let y = if m <= 2 { y + 1 } else { y } as i32;
    (y, m, d, h, mi)
}

/// The Raw Sessions component.
#[component]
pub fn CorpusTab() -> Element {
    let ctx = use_context::<SessionContext>();
    let discovery = use_context::<DiscoveryState>();
    let mut reload = use_context::<ReloadTrigger>();
    let custom_paths = use_context::<CustomCorpusPaths>();
    // Clone the context wrapper once per button so each `move` closure
    // owns its own copy — Dioxus `onclick` handlers are `FnOnce + Send`
    // and we have three of them touching the same context.
    let mut custom_paths_pick = custom_paths.clone();
    let mut custom_paths_reset = custom_paths.clone();

    // Reactive read: rebuilt on every render that sees a sessions signal
    // change (or a manual Reload click). Sorted newest-first so the user
    // sees the most recently active sessions at the top.
    let mut sessions_sorted: Vec<Session> = ctx.0.read().clone();
    sessions_sorted.sort_by_key(|s| std::cmp::Reverse(last_activity_ms(s).unwrap_or(i64::MIN)));

    let total = sessions_sorted.len();
    let by_corpus = corpus_breakdown(&sessions_sorted);
    let plural = if total == 1 { "session" } else { "sessions" };
    let loading = discovery.loading.cloned();
    let load_error = discovery.error.cloned();

    let current_custom_paths = custom_paths.snapshot();
    let custom_paths_display: Vec<String> =
        current_custom_paths.iter().map(|path| path.display().to_string()).collect();

    rsx! {
        style { r#"
            .corpus-view {{
                display: flex;
                flex-direction: column;
                height: 100%;
                overflow: hidden;
            }}
            .corpus-toolbar {{
                display: flex;
                align-items: center;
                gap: var(--sl-space-md);
                padding: var(--sl-space-md) var(--sl-space-xl);
                border-bottom: 1px solid var(--sl-border);
                background: var(--sl-surface-muted);
                flex-wrap: wrap;
            }}
            .corpus-title {{
                font-family: var(--font-ui);
                font-size: 14px;
                font-weight: 600;
                color: var(--sl-text);
                margin: 0;
            }}
            .corpus-count {{
                font-family: var(--font-ui);
                font-size: 12px;
                color: var(--sl-text-muted);
            }}
            .corpus-breakdown {{
                display: flex;
                gap: var(--sl-space-sm);
                flex-wrap: wrap;
                font-family: var(--font-ui);
                font-size: 11px;
                color: var(--sl-text-muted);
            }}
            .corpus-breakdown .badge {{
                padding: 2px 8px;
                border-radius: 999px;
                background: color-mix(in srgb, var(--sl-accent) 14%, transparent);
                color: var(--sl-accent);
            }}
            .corpus-toolbar-actions {{
                margin-left: auto;
                display: flex;
                gap: var(--sl-space-sm);
                flex-wrap: wrap;
            }}
            .corpus-reload-btn,
            .corpus-pick-btn,
            .corpus-reset-btn {{
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
                border-radius: var(--sl-radius-md);
                border: 1px solid var(--sl-border);
                background: var(--sl-surface);
                color: var(--sl-text);
                cursor: pointer;
            }}
            .corpus-reload-btn:hover,
            .corpus-pick-btn:hover,
            .corpus-reset-btn:hover {{
                border-color: var(--sl-accent);
                color: var(--sl-accent);
            }}
            .corpus-pick-btn:focus-visible,
            .corpus-reload-btn:focus-visible,
            .corpus-reset-btn:focus-visible {{
                outline: 2px solid var(--sl-accent);
                outline-offset: 2px;
            }}
            .corpus-reset-btn {{
                border-color: color-mix(in srgb, var(--sl-danger) 40%, var(--sl-border));
                color: var(--sl-danger);
            }}
            .corpus-reset-btn:hover {{
                border-color: var(--sl-danger);
                color: var(--sl-danger);
            }}
            .corpus-custom-paths {{
                flex-basis: 100%;
                font-family: var(--font-mono);
                font-size: 11px;
                color: var(--sl-text-muted);
                padding: 4px 0;
                word-break: break-all;
            }}
            .corpus-custom-paths-label {{
                font-family: var(--font-ui);
                font-weight: 600;
                color: var(--sl-accent);
                margin-right: 6px;
            }}
            .corpus-list {{
                flex: 1;
                overflow-y: auto;
                padding: 0;
            }}
            .corpus-row {{
                display: grid;
                grid-template-columns: 110px 1fr 90px 130px;
                gap: var(--sl-space-md);
                align-items: baseline;
                padding: 10px var(--sl-space-xl);
                border-bottom: 1px solid var(--sl-border);
                font-size: 13px;
            }}
            .corpus-row:hover {{
                background: var(--sl-surface-muted);
            }}
            .corpus-row .corpus-badge {{
                font-family: var(--font-ui);
                font-size: 10px;
                font-weight: 600;
                text-transform: uppercase;
                padding: 2px 8px;
                border-radius: var(--sl-radius-pill);
                background: color-mix(in srgb, var(--sl-accent) 18%, transparent);
                color: var(--sl-accent);
                text-align: center;
                letter-spacing: 0.5px;
            }}
            .corpus-row .corpus-id {{
                font-family: var(--font-mono);
                font-size: 12px;
                color: var(--sl-text-muted);
            }}
            .corpus-row .corpus-title-text {{
                color: var(--sl-text);
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }}
            .corpus-row .corpus-meta {{
                font-family: var(--font-ui);
                font-size: 11px;
                color: var(--sl-text-muted);
                text-align: right;
            }}
            .corpus-empty {{
                padding: var(--sl-space-2xl);
                text-align: center;
                color: var(--sl-text-muted);
                font-size: 13px;
            }}
        "# }
        section {
            class: "corpus-view",
            "aria-labelledby": "corpus-heading",
            header {
                class: "corpus-toolbar",
                h2 {
                    id: "corpus-heading",
                    class: "corpus-title",
                    "Raw Sessions"
                }
                span {
                    class: "corpus-count",
                    "data-testid": "corpus-count",
                    "{total} {plural} discovered"
                }
                div {
                    class: "corpus-breakdown",
                    "data-testid": "corpus-breakdown",
                    for entry in &by_corpus {
                        span {
                            class: "badge",
                            "data-corpus": "{entry.0}",
                            "{entry.0}: {entry.1}"
                        }
                    }
                }
                div {
                    class: "corpus-toolbar-actions",
                    button {
                        class: "corpus-pick-btn",
                        r#type: "button",
                        "data-testid": "corpus-pick",
                        title: "Pick a folder to scan in addition to the default session stores",
                        onclick: move |_| {
                            // Snapshot the latest value at click time so a
                            // second pick in the same session sees the
                            // first pick rather than the stale render-time
                            // copy captured by this closure.
                            let mut next = custom_paths_pick.snapshot();
                            if let Some(path) = pick_corpus_folder() {
                                let path_str = path.display().to_string();
                                next.0.retain(|existing| existing.display().to_string() != path_str);
                                next.0.push(path);
                                persist_custom_corpus_paths(&next);
                                custom_paths_pick.set(next);
                                reload.0.with_mut(|t| *t += 1);
                            }
                        },
                        "Pick folder…"
                    }
                    button {
                        class: "corpus-reload-btn",
                        r#type: "button",
                        "data-testid": "corpus-reload",
                        onclick: move |_| reload.0.with_mut(|t| *t += 1),
                        "Reload discovery"
                    }
                    if !current_custom_paths.is_empty() {
                        button {
                            class: "corpus-reset-btn",
                            r#type: "button",
                            "data-testid": "corpus-reset",
                            title: "Clear the custom folder override and use only the default session stores",
                            onclick: move |_| {
                                custom_paths_reset.clear();
                                persist_custom_corpus_paths(&CustomCorpusPath::default());
                                reload.0.with_mut(|t| *t += 1);
                            },
                            "Reset to default"
                        }
                    }
                }
                if !custom_paths_display.is_empty() {
                    div {
                        class: "corpus-custom-paths",
                        "data-testid": "corpus-custom-paths",
                        span {
                            class: "corpus-custom-paths-label",
                            "Custom corpus path:"
                        }
                        for (idx, path) in custom_paths_display.iter().enumerate() {
                            if idx > 0 {
                                span { " · " }
                            }
                            span { "{path}" }
                        }
                    }
                }
            }
            if sessions_sorted.is_empty() {
                if let Some(err) = load_error.as_ref() {
                    div {
                        class: "corpus-empty",
                        role: "status",
                        "Corpus load failed: {err}. Use Reload discovery to retry."
                    }
                } else if loading {
                    div {
                        class: "corpus-empty",
                        role: "status",
                        "Discovering local session corpus… (Codex + Claude + Cursor + custom)"
                    }
                } else {
                    div {
                        class: "corpus-empty",
                        role: "status",
                        "No sessions loaded yet. Reload discovery, pick a custom folder, or check that one of $HOME/.codex/sessions, $HOME/.claude/projects, $HOME/.cursor/projects exists."
                    }
                }
            } else {
                div {
                    class: "corpus-list",
                    "data-testid": "corpus-list",
                    for session in sessions_sorted.iter() {
                        CorpusRow { session: session.clone() }
                    }
                }
            }
        }
    }
}

/// Persist the current custom-paths selection to the platform config dir.
///
/// Thin wrapper around [`crate::corpus_paths::save_config`] so the
/// `onclick` handler above can stay declarative. Logs to stderr on error
/// (the user is already looking at the toolbar; the picker must never
/// crash the click handler).
fn persist_custom_corpus_paths(paths: &CustomCorpusPath) {
    use crate::corpus_paths::CorpusPathConfig;
    let config = CorpusPathConfig { custom_paths: paths.0.clone() };
    if let Err(error) = crate::corpus_paths::save_config(&config) {
        eprintln!("[sl-viewer] could not persist custom corpus path: {error}");
    }
}

/// One row of the corpus table — corpus, id, title, message count, last activity.
#[component]
fn CorpusRow(session: Session) -> Element {
    let id = session.id.clone();
    let title = session.title.clone().unwrap_or_else(|| "(untitled)".to_owned());
    let corpus = corpus_label(session.corpus);
    let count = session.messages.len();
    let last = format_ms(last_activity_ms(&session));

    rsx! {
        div {
            class: "corpus-row",
            "data-testid": "corpus-row",
            "data-corpus": "{corpus}",
            span { class: "corpus-badge", "{corpus}" }
            span {
                class: "corpus-title-text",
                "{title}"
                span {
                    class: "corpus-id",
                    style: "display:block;margin-top:2px;",
                    "{id}"
                }
            }
            span { class: "corpus-meta", "{count} msgs" }
            span { class: "corpus-meta", "{last}" }
        }
    }
}

/// Count sessions per corpus, returned as a stable ordering (insertion order
/// derived from the iteration order of the [`Corpus`] enum).
fn corpus_breakdown(sessions: &[Session]) -> Vec<(&'static str, usize)> {
    let mut counts: Vec<(&'static str, usize)> = Vec::new();
    for s in sessions {
        let label = corpus_label(s.corpus);
        if let Some(entry) = counts.iter_mut().find(|(l, _)| *l == label) {
            entry.1 += 1;
        } else {
            counts.push((label, 1));
        }
    }
    counts
}

#[cfg(test)]
mod tests {
    use super::*;
    use session_ledger::domain::session::{Message, Role, Session};

    fn make_session(id: &str, corpus: Corpus, ts: Option<i64>) -> Session {
        let mut session = Session::new(id, corpus);
        if let Some(value) = ts {
            let mut message = Message::new(Role::User, format!("hello from {id}"));
            message.ts_ms = Some(value);
            session.messages.push(message);
        }
        session
    }

    #[test]
    fn corpus_breakdown_groups_by_corpus() {
        let sessions = vec![
            make_session("a", Corpus::Codex, Some(10)),
            make_session("b", Corpus::Codex, Some(20)),
            make_session("c", Corpus::ClaudeCode, Some(30)),
            make_session("d", Corpus::Cursor, None),
        ];
        let counts = corpus_breakdown(&sessions);
        let map: std::collections::HashMap<&str, usize> = counts.into_iter().collect();
        assert_eq!(map.get("codex"), Some(&2));
        assert_eq!(map.get("claude"), Some(&1));
        assert_eq!(map.get("cursor"), Some(&1));
    }

    #[test]
    fn last_activity_picks_max_timestamp() {
        let mut session = make_session("a", Corpus::Cursor, Some(100));
        let mut message = Message::new(Role::Assistant, "response".to_owned());
        message.ts_ms = Some(500);
        session.messages.push(message);
        assert_eq!(last_activity_ms(&session), Some(500));
    }

    #[test]
    fn format_ms_returns_placeholder_when_missing() {
        assert_eq!(format_ms(None), "(no timestamp)");
        assert_eq!(format_ms(Some(0)), "(no timestamp)");
    }

    #[test]
    fn epoch_to_ymdhm_handles_known_dates() {
        // 2000-01-01 00:00:00 UTC (Y2K midnight, well-known anchor)
        let secs = 946_684_800;
        let (y, m, d, h, mi) = epoch_to_ymdhm(secs);
        assert_eq!((y, m, d, h, mi), (2000, 1, 1, 0, 0));
        // 1970-01-01 00:00:00 UTC (Unix epoch)
        let (y, m, d, h, mi) = epoch_to_ymdhm(0);
        assert_eq!((y, m, d, h, mi), (1970, 1, 1, 0, 0));
    }
}
