//! `ReplayView` — Dioxus component that streams OKF entity events from the
//! daemon's `GET /api/replay/:bundle_id` SSE endpoint and renders them in a
//! terminal-style scrolling pane with play/pause and speed controls.

use dioxus::prelude::*;

use crate::async_states::{ContentSkeleton, ErrorState, SkeletonLayout};
use crate::daemon_url::daemon_base_url;
use crate::fixture::query_fixture_active;

use futures_util::StreamExt;

const MIN_SPEED: f64 = 0.1;
const MAX_SPEED: f64 = 10.0;

fn normalize_speed(value: f64) -> f64 {
    if value.is_finite() {
        value.clamp(MIN_SPEED, MAX_SPEED)
    } else {
        1.0
    }
}

/// An entity event received from the SSE replay stream.
#[derive(Debug, Clone, PartialEq)]
struct ReplayEntry {
    /// Position in the stream (0-based).
    event_index: usize,
    /// Total number of events in this bundle.
    total_events: usize,
    /// The entity type string (e.g. `"intent"`, `"gate"`).
    entity_type: String,
    /// The entity id string.
    entity_id: String,
    /// The entity label (used as the human-readable line).
    label: String,
}

impl ReplayEntry {
    #[allow(dead_code)] // reserved for desktop SSE JSON decode path
    fn from_json(v: &serde_json::Value) -> Option<Self> {
        let idx = v.get("event_index")?.as_u64()? as usize;
        let total = v.get("total_events")?.as_u64()? as usize;
        let entity = v.get("entity")?;
        let entity_type = entity.get("type")?.as_str()?.to_owned();
        let entity_id = entity.get("id")?.as_str()?.to_owned();
        let label = entity.get("label").and_then(|l| l.as_str()).unwrap_or("").to_owned();
        Some(Self { event_index: idx, total_events: total, entity_type, entity_id, label })
    }

    /// Format as a terminal-style line: `[HH:MM:SS] <type>/<id>: <label>`.
    fn display_line(&self) -> String {
        let secs = self.event_index as u64;
        let h = secs / 3600;
        let m = (secs % 3600) / 60;
        let s = secs % 60;
        let ts = format!("{h:02}:{m:02}:{s:02}");
        let label = if self.label.chars().count() > 80 {
            let cut: String = self.label.chars().take(79).collect();
            format!("{cut}\u{2026}")
        } else {
            self.label.clone()
        };
        format!("[{ts}] {}/{}: {label}", self.entity_type, self.entity_id)
    }
}

/// Parse one SSE `data:` payload into a replay entry. Kept separate from the
/// transport so malformed events are ignored without killing the stream.
fn parse_replay_event(line: &str) -> Option<ReplayEntry> {
    let payload = line.trim().strip_prefix("data:")?.trim();
    if payload.is_empty() || payload == "{}" {
        return None;
    }
    serde_json::from_str::<serde_json::Value>(payload)
        .ok()
        .and_then(|value| ReplayEntry::from_json(&value))
}

/// The replay state machine.
#[derive(Debug, Clone, PartialEq)]
enum ReplayState {
    /// Waiting for the user to enter a bundle ID and press Play.
    Idle,
    /// Actively streaming events from the daemon.
    Playing,
    /// User paused the stream mid-replay.
    Paused,
    /// All events have been received.
    Done,
    /// An error occurred.
    Error(String),
}

/// `ReplayView` — terminal-style session replay panel.
///
/// The user enters a bundle ID, optionally adjusts the speed multiplier,
/// and presses **Play**.  The component connects to the running `sl-daemon`
/// SSE endpoint and renders each entity event as a scrolling log line.
#[component]
pub fn ReplayView() -> Element {
    let mut bundle_id: Signal<String> = use_signal(String::new);
    let mut speed: Signal<f64> = use_signal(|| 1.0_f64);
    let mut entries: Signal<Vec<ReplayEntry>> = use_signal(Vec::new);
    let mut state: Signal<ReplayState> = use_signal(|| ReplayState::Idle);
    let mut progress: Signal<(usize, usize)> = use_signal(|| (0, 0));
    let mut generation: Signal<u64> = use_signal(|| 0);

    // A single owned coroutine gives Play a real, cancellable transport path.
    // Sending another request replaces the prior stream logically; stale
    // events are harmless because the UI is reset before each request.
    let replay_task = use_coroutine({
        #[cfg(all(feature = "desktop", not(target_arch = "wasm32")))]
        let mut entries = entries;
        #[cfg(not(all(feature = "desktop", not(target_arch = "wasm32"))))]
        let entries = entries;
        let mut state = state;
        #[cfg(all(feature = "desktop", not(target_arch = "wasm32")))]
        let mut progress = progress;
        #[cfg(not(all(feature = "desktop", not(target_arch = "wasm32"))))]
        let progress = progress;
        move |mut rx: UnboundedReceiver<(String, f64, String, u64)>| async move {
            while let Some((id, spd, daemon_url, token)) = rx.next().await {
                #[cfg(all(not(target_arch = "wasm32"), feature = "desktop"))]
                {
                    use tokio::io::{AsyncBufReadExt, BufReader};
                    use tokio_util::io::StreamReader;

                    let url = format!("{daemon_url}/api/replay/{id}?speed={spd}");
                    let response = match reqwest::Client::new().get(url).send().await {
                        Ok(response) if response.status().is_success() => response,
                        Ok(_) | Err(_) => {
                            state.set(ReplayState::Error("replay stream unavailable".into()));
                            continue;
                        }
                    };
                    let stream =
                        response.bytes_stream().map(|result| result.map_err(std::io::Error::other));
                    let mut lines = BufReader::new(StreamReader::new(stream)).lines();
                    let mut saw_done = false;
                    while let Ok(Some(line)) = lines.next_line().await {
                        if generation() != token {
                            break;
                        }
                        if line.starts_with("event: done") {
                            saw_done = true;
                            continue;
                        }
                        if let Some(entry) = parse_replay_event(&line) {
                            progress.set((entry.event_index + 1, entry.total_events));
                            entries.with_mut(|items| items.push(entry));
                        }
                    }
                    if generation() == token {
                        state.set(if saw_done {
                            ReplayState::Done
                        } else {
                            ReplayState::Error("replay stream ended before completion".into())
                        });
                    }
                }
                #[cfg(any(target_arch = "wasm32", not(feature = "desktop")))]
                {
                    #[cfg(target_arch = "wasm32")]
                    {
                        use wasm_bindgen::{closure::Closure, JsCast};
                        use web_sys::{Event, EventSource, MessageEvent};

                        let url = format!("{daemon_url}/api/replay/{id}?speed={spd}");
                        let source = match EventSource::new(&url) {
                            Ok(source) => source,
                            Err(_) => {
                                state.set(ReplayState::Error("replay stream unavailable".into()));
                                continue;
                            }
                        };
                        let onopen = Closure::wrap(Box::new({
                            let mut state = state;
                            move || state.set(ReplayState::Playing)
                        }) as Box<dyn FnMut()>);
                        source.set_onopen(Some(onopen.as_ref().unchecked_ref()));
                        let onmessage = Closure::wrap(Box::new({
                            let mut entries = entries;
                            let mut progress = progress;
                            move |event: MessageEvent| {
                                let data = event.data().as_string().unwrap_or_default();
                                if let Some(entry) = parse_replay_event(&format!("data: {data}")) {
                                    progress.set((entry.event_index + 1, entry.total_events));
                                    entries.with_mut(|items| items.push(entry));
                                }
                            }
                        })
                            as Box<dyn FnMut(MessageEvent)>);
                        source.set_onmessage(Some(onmessage.as_ref().unchecked_ref()));
                        let ondone = Closure::wrap(Box::new({
                            let mut state = state;
                            move |_event: Event| state.set(ReplayState::Done)
                        })
                            as Box<dyn FnMut(Event)>);
                        let _ = source.add_event_listener_with_callback(
                            "done",
                            ondone.as_ref().unchecked_ref(),
                        );
                        let onerror = Closure::wrap(Box::new({
                            let mut state = state;
                            move |_event: Event| {
                                state.set(ReplayState::Error(
                                    "replay stream disconnected before completion".into(),
                                ))
                            }
                        })
                            as Box<dyn FnMut(Event)>);
                        source.set_onerror(Some(onerror.as_ref().unchecked_ref()));
                        // Keep the EventSource and callbacks alive for the stream lifetime.
                        std::future::pending::<()>().await;
                        drop((source, onopen, onmessage, ondone, onerror, token));
                    }
                    #[cfg(not(target_arch = "wasm32"))]
                    {
                        let _ = (id, spd, daemon_url, token);
                        state.set(ReplayState::Error(
                            "replay streaming requires the desktop target".into(),
                        ));
                    }
                }
            }
        }
    });

    let daemon_url = daemon_base_url();

    if query_fixture_active("replay-error") {
        return rsx! {
            style {
                r#"
                .replay-view {{ display: flex; flex-direction: column; height: 100%; padding: 16px 20px; box-sizing: border-box; }}
                .replay-controls {{ display: flex; gap: 10px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }}
                .replay-input {{ flex: 1; min-width: 180px; padding: 8px 12px; background: #1c1f2b; border: 1px solid #2a2d35; border-radius: 6px; color: #e1e4ea; font-size: 13px; font-family: monospace; }}
                .btn {{ padding: 8px 16px; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; }}
                .btn-play {{ background: #2563eb; color: #fff; }}
                .status-error {{ color: #f87171; font-size: 13px; padding: 8px 0; }}
                "#
            }
            div {
                class: "replay-view",
                "data-testid": "replay-error-fixture",
                div { class: "replay-controls",
                    input {
                        class: "replay-input",
                        r#type: "text",
                        "aria-label": "Bundle ID",
                        value: "sess-visual-fixture",
                        readonly: true,
                    }
                    button { class: "btn btn-play", disabled: true, "Play" }
                }
                p {
                    class: "status-error",
                    "data-testid": "replay-status-error",
                    "Replay stream disconnected before completion."
                }
                ErrorState {
                    message: "daemon closed the SSE replay stream (visual fixture)".to_owned(),
                    retryable: true,
                    on_retry: move |_| {},
                }
            }
        };
    }

    rsx! {
        style {
            r#"
            .replay-view {{ display: flex; flex-direction: column; height: 100%; padding: 16px 20px; box-sizing: border-box; }}
            .replay-controls {{ display: flex; gap: 10px; align-items: center; margin-bottom: 12px; flex-wrap: wrap; }}
            .replay-input {{ flex: 1; min-width: 180px; padding: 8px 12px; background: #1c1f2b; border: 1px solid #2a2d35; border-radius: 6px; color: #e1e4ea; font-size: 13px; font-family: monospace; }}
            .replay-input::placeholder {{ color: #8b8fa3; }}
            .speed-label {{ font-size: 12px; color: #8b8fa3; }}
            .speed-input {{ width: 60px; padding: 8px; background: #1c1f2b; border: 1px solid #2a2d35; border-radius: 6px; color: #e1e4ea; font-size: 13px; text-align: center; }}
            .btn {{ padding: 8px 16px; border: none; border-radius: 6px; cursor: pointer; font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; }}
            .btn-play {{ background: #2563eb; color: #fff; }}
            .btn-play:hover {{ background: #1d4ed8; }}
            .btn-stop {{ background: #3a2a2a; color: #f87171; }}
            .btn-stop:hover {{ background: #4a2a2a; }}
            .btn-clear {{ background: #2a2d35; color: #c8cdd6; }}
            .btn-clear:hover {{ background: #343744; }}
            .progress-bar-wrap {{ height: 4px; background: #2a2d35; border-radius: 2px; margin-bottom: 12px; }}
            .progress-bar-fill {{ height: 4px; background: #6c8cff; border-radius: 2px; transition: width 0.3s; }}
            .terminal {{ flex: 1; overflow-y: auto; background: #0a0c12; border: 1px solid #2a2d35; border-radius: 8px; padding: 12px 16px; font-family: "SF Mono", "Menlo", "Consolas", monospace; font-size: 12px; line-height: 1.7; }}
            .terminal-line {{ color: #c8cdd6; }}
            .terminal-line .ts {{ color: #8b8fa3; }}
            .terminal-line .type-intent {{ color: #6c8cff; }}
            .terminal-line .type-gate {{ color: #4ade80; }}
            .terminal-line .type-acceptance {{ color: #4ade80; }}
            .terminal-line .type-constraint {{ color: #f59e0b; }}
            .terminal-line .type-other {{ color: #a1a6b5; }}
            .status-idle {{ color: #8b8fa3; font-size: 13px; padding: 8px 0; }}
            .status-error {{ color: #f87171; font-size: 13px; padding: 8px 0; }}
            .status-done {{ color: #4ade80; font-size: 13px; padding: 8px 0; }}
            "#
        }

        div {
            class: "replay-view",
            onkeydown: move |evt: Event<KeyboardData>| {
                if evt.key() == Key::Escape {
                    evt.prevent_default();
                    entries.set(vec![]);
                    progress.set((0, 0));
                    state.set(ReplayState::Idle);
                }
            },
            // Controls bar
            div { class: "replay-controls",
                input {
                    class: "replay-input",
                    r#type: "text",
                    "aria-label": "Bundle ID",
                    placeholder: "Bundle ID (e.g. sess-abc)",
                    value: "{bundle_id}",
                    oninput: move |evt| bundle_id.set(evt.value()),
                }
                span { class: "speed-label", "Speed:" }
                input {
                    id: "replay-speed",
                    class: "speed-input",
                    r#type: "number",
                    "aria-label": "Replay speed multiplier",
                    min: "0.1",
                    max: "10.0",
                    step: "0.5",
                    value: "{speed}",
                    oninput: move |evt| {
                            if let Ok(v) = evt.value().parse::<f64>() {
                            speed.set(normalize_speed(v));
                        }
                    },
                }

                if *state.read() == ReplayState::Idle || *state.read() == ReplayState::Done {
                    button {
                        class: "btn btn-play",
                        onclick: {
                            let id = bundle_id.read().clone();
                            let spd = *speed.read();
                            move |_| {
                                if id.trim().is_empty() {
                                    state.set(ReplayState::Error("enter a bundle ID first".into()));
                                    return;
                                }
                                entries.set(vec![]);
                                progress.set((0, 0));
                                state.set(ReplayState::Playing);
                                generation.set(generation() + 1);
                                replay_task.send((id.clone(), normalize_speed(spd), daemon_url.to_string(), generation()));
                            }
                        },
                        "Play"
                    }
                }

                if *state.read() == ReplayState::Playing {
                    button {
                        class: "btn btn-stop",
                        onclick: move |_| {
                            generation.set(generation() + 1);
                            state.set(ReplayState::Paused)
                        },
                        "Pause"
                    }
                }

                if *state.read() == ReplayState::Paused {
                    button {
                        class: "btn btn-play",
                        onclick: move |_| {
                            let id = bundle_id.read().clone();
                            entries.set(vec![]);
                            progress.set((0, 0));
                            generation.set(generation() + 1);
                            state.set(ReplayState::Playing);
                            replay_task.send((id, normalize_speed(*speed.read()), daemon_url.to_string(), generation()));
                        },
                        "Resume"
                    }
                    button {
                        class: "btn btn-stop",
                        onclick: move |_| {
                            generation.set(generation() + 1);
                            state.set(ReplayState::Idle)
                        },
                        "Stop"
                    }
                }

                button {
                    class: "btn btn-clear",
                    onclick: move |_| {
                        generation.set(generation() + 1);
                        entries.set(vec![]);
                        progress.set((0, 0));
                        state.set(ReplayState::Idle);
                    },
                    "Clear"
                }
            }

            // Progress bar
            {
                let (done, total) = *progress.read();
                let pct = (done * 100).checked_div(total).unwrap_or(0).min(100);
                rsx! {
                    div { class: "progress-bar-wrap",
                        div { class: "progress-bar-fill", style: "width: {pct}%;" }
                    }
                }
            }

            // Status line
            match &*state.read() {
                ReplayState::Idle => rsx! {
                    p { class: "status-idle", "Enter a bundle ID and press Play to start replay." }
                },
                ReplayState::Playing => rsx! {
                    ContentSkeleton { layout: SkeletonLayout::StreamFeed, list_rows: 6 }
                },
                ReplayState::Paused => rsx! {
                    p { class: "status-idle", "Paused." }
                },
                ReplayState::Done => rsx! {
                    p { class: "status-done", "Replay complete." }
                },
                ReplayState::Error(msg) => {
                    let m = msg.clone();
                    rsx! {
                        ErrorState { message: m }
                    }
                },
            }

            // Terminal output
            div { class: "terminal",
                if entries.read().is_empty() {
                    span { class: "status-idle", "No events yet." }
                }
                for entry in entries.read().iter() {
                    {
                        let line = entry.display_line();
                        let type_class = match entry.entity_type.as_str() {
                            "intent" => "type-intent",
                            "gate" | "acceptance" => "type-acceptance",
                            "constraint" => "type-constraint",
                            _ => "type-other",
                        };
                        rsx! {
                            div { class: "terminal-line",
                                span { class: "{type_class}", "{line}" }
                            }
                        }
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{normalize_speed, parse_replay_event, ReplayEntry};

    #[test]
    fn speed_is_finite_and_bounded() {
        assert_eq!(normalize_speed(f64::NAN), 1.0);
        assert_eq!(normalize_speed(0.0), 0.1);
        assert_eq!(normalize_speed(99.0), 10.0);
        assert_eq!(normalize_speed(2.0), 2.0);
    }

    #[test]
    fn parses_entity_sse_payload() {
        let entry = parse_replay_event(
            r#"data: {"event_index":1,"total_events":3,"entity":{"type":"gate","id":"g-1","label":"Approved"}}"#,
        )
        .expect("entity event");
        assert_eq!(entry.event_index, 1);
        assert_eq!(entry.total_events, 3);
        assert_eq!(entry.entity_type, "gate");
        assert_eq!(entry.display_line(), "[00:00:01] gate/g-1: Approved");
    }

    #[test]
    fn ignores_done_and_malformed_sse_lines() {
        assert!(parse_replay_event("event: done").is_none());
        assert!(parse_replay_event("data: {}").is_none());
        assert!(parse_replay_event("data: not-json").is_none());
    }

    #[test]
    fn truncates_long_labels_without_panicking() {
        let entry = ReplayEntry {
            event_index: 0,
            total_events: 1,
            entity_type: "intent".into(),
            entity_id: "i-1".into(),
            label: "x".repeat(100),
        };
        assert!(entry.display_line().ends_with('…'));
        assert_eq!(entry.display_line().chars().count(), 103);
    }
}
