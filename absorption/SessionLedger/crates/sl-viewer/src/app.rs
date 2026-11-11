use dioxus::prelude::*;
use session_ledger::domain::{
    bundle::{Bundle, BundleKind, ContinuationBundle},
    session::{Role, Session},
};

use crate::async_states::{
    ContentSkeleton, ErrorColorFixture, ErrorState, FirstRunEmpty, LoadingState, SkeletonLayout,
};
use crate::bundle_diff::{BundleDiff, OkfBundle};
use crate::bundle_list::{summarize, BundleSummary};
#[cfg(feature = "desktop")]
use crate::cli_help;
use crate::command_palette::{CommandPalette, PaletteAction};
use crate::corpus_loader::{load_sessions_with_custom, CustomCorpusPath, DataSource};
use crate::corpus_tab::CorpusTab;
use crate::detail_pane::{extract_detail, BundleDetail};
use crate::fixture::visual_fixture_active;
use crate::fixture::{query_fixture_active, splash_hold_fixture_active};
use crate::help_overlay::HelpOverlay;
use crate::history_tab::HistoryTimeline;
use crate::live_feed::LiveFeed;
use crate::memory_tab::MemoryWiki;
use crate::replay_view::ReplayView;
use crate::search_view::SearchView;
use crate::session_transcript::SessionTranscript;
use crate::settings::{DefaultTab, Settings};
use crate::settings_tab::SettingsTab;
use crate::theme::{Theme, ThemeColors};
use crate::timeline::TimelineView;
use crate::tokens::{TOKENS_CSS, VIEWER_COLOR_SCHEME};
use crate::unfinished_tab::UnfinishedWork;

/// Tab identifiers for the viewer.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Tab {
    Bundles,
    History,
    Unfinished,
    Memory,
    LiveFeed,
    Search,
    Timeline,
    Replay,
    /// Raw sessions view — exposes the underlying `Vec<Session>` that every
    /// other tab derives from, so users can see what was discovered and reload
    /// discovery on demand. (FR-RAW-1)
    Corpus,
    /// Persistent user preferences (theme, default tab, daemon URL, version).
    /// (FR-VIEWER-SETTINGS-1)
    Settings,
}

#[cfg(all(feature = "desktop", not(feature = "web")))]
fn splash_dismiss_delay() -> std::time::Duration {
    std::time::Duration::from_millis(1800)
}

/// Monotonic token that lets a discovery task reject an obsolete completion.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
struct DiscoveryGeneration(u64);

impl DiscoveryGeneration {
    fn next(&mut self) -> u64 {
        self.0 = self.0.wrapping_add(1);
        self.0
    }

    fn is_current(self, request: u64) -> bool {
        self.0 == request
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[cfg(all(feature = "desktop", not(feature = "web")))]
    #[test]
    fn splash_dismiss_delay_matches_the_launch_transition() {
        assert_eq!(splash_dismiss_delay(), std::time::Duration::from_millis(1800));
    }

    #[test]
    fn discovery_generation_rejects_obsolete_requests() {
        let mut generation = DiscoveryGeneration::default();
        let first = generation.next();
        let second = generation.next();

        assert!(!generation.is_current(first));
        assert!(generation.is_current(second));
    }
}

impl Tab {
    const ALL: [Tab; 10] = [
        Tab::Bundles,
        Tab::History,
        Tab::Unfinished,
        Tab::Memory,
        Tab::LiveFeed,
        Tab::Search,
        Tab::Timeline,
        Tab::Replay,
        Tab::Corpus,
        Tab::Settings,
    ];

    fn label(self) -> &'static str {
        match self {
            Tab::Bundles => "Bundles",
            Tab::History => "History",
            Tab::Unfinished => "Unfinished",
            Tab::Memory => "Memory",
            Tab::LiveFeed => "Live Feed",
            Tab::Search => "Search",
            Tab::Timeline => "Timeline",
            Tab::Replay => "Replay",
            Tab::Corpus => "Raw Sessions",
            Tab::Settings => "Settings",
        }
    }

    fn id(self) -> &'static str {
        match self {
            Tab::Bundles => "tab-bundles",
            Tab::History => "tab-history",
            Tab::Unfinished => "tab-unfinished",
            Tab::Memory => "tab-memory",
            Tab::LiveFeed => "tab-live-feed",
            Tab::Search => "tab-search",
            Tab::Timeline => "tab-timeline",
            Tab::Replay => "tab-replay",
            Tab::Corpus => "tab-corpus",
            Tab::Settings => "tab-settings",
        }
    }

    fn panel_id(self) -> &'static str {
        match self {
            Tab::Bundles => "panel-bundles",
            Tab::History => "panel-history",
            Tab::Unfinished => "panel-unfinished",
            Tab::Memory => "panel-memory",
            Tab::LiveFeed => "panel-live-feed",
            Tab::Search => "panel-search",
            Tab::Timeline => "panel-timeline",
            Tab::Replay => "panel-replay",
            Tab::Corpus => "panel-corpus",
            Tab::Settings => "panel-settings",
        }
    }

    fn index(self) -> usize {
        Self::ALL.iter().position(|&t| t == self).unwrap_or(0)
    }

    /// Return the SVG icon name for this tab.
    fn icon(&self) -> &'static str {
        match self {
            Self::Bundles => "bundles",
            Self::History => "history",
            Self::Unfinished => "unfinished",
            Self::Memory => "memory",
            Self::LiveFeed => "live",
            Self::Search => "search",
            Self::Timeline => "timeline",
            Self::Replay => "replay",
            Self::Corpus => "corpus",
            Self::Settings => "settings",
        }
    }

    fn from_index(i: usize) -> Tab {
        Self::ALL[i % Self::ALL.len()]
    }
}

/// Map a persisted [`DefaultTab`] to its runtime [`Tab`] counterpart.
///
/// [`DefaultTab`] deliberately omits [`Tab::Settings`] (we never auto-launch
/// into settings), so every variant maps cleanly.
fn default_tab_to_tab(t: DefaultTab) -> Tab {
    match t {
        DefaultTab::Bundles => Tab::Bundles,
        DefaultTab::History => Tab::History,
        DefaultTab::Unfinished => Tab::Unfinished,
        DefaultTab::Memory => Tab::Memory,
        DefaultTab::LiveFeed => Tab::LiveFeed,
        DefaultTab::Search => Tab::Search,
        DefaultTab::Timeline => Tab::Timeline,
        DefaultTab::Replay => Tab::Replay,
        DefaultTab::Corpus => Tab::Corpus,
    }
}

/// Shared session data provided at the root of the component tree.
///
/// Consumers call `use_context::<SessionContext>()` to access the loaded sessions.
#[derive(Clone, Debug, PartialEq)]
pub struct SessionContext(pub Signal<Vec<Session>>);

/// Counter the Corpus tab increments to re-run [`App`]'s discovery effect.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct ReloadTrigger(pub Signal<u32>);

/// User-supplied corpus directories, persisted across launches.
///
/// The wrapped signal is mutated by the Raw Sessions tab when the user
/// picks a new folder or resets to defaults. The discovery effect reads
/// the latest value on every re-run, so a pick immediately triggers a
/// reload without restarting the app.
#[derive(Clone, Debug, PartialEq)]
pub struct CustomCorpusPaths(pub Signal<CustomCorpusPath>);

impl CustomCorpusPaths {
    /// Read the current custom paths snapshot.
    pub fn snapshot(&self) -> CustomCorpusPath {
        self.0.cloned()
    }

    /// Replace the current custom paths (used by the Raw Sessions toolbar).
    pub fn set(&mut self, paths: CustomCorpusPath) {
        self.0.set(paths);
    }

    /// Clear the override and revert to the default discovery set.
    pub fn clear(&mut self) {
        self.0.set(CustomCorpusPath::default());
    }
}

/// Persisted user settings, exposed at the root so [`SettingsTab`] and
/// other consumers can read and update them. The settings are persisted
/// to disk by an effect that watches this signal.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct SettingsSignal(pub Signal<Settings>);

/// Discovery status published at the root so every tab can render a
/// loading / error / ready state without the App's spawn_blocking effect
/// having to thread the status through props. The corpus scan can take
/// minutes on a large local corpus (Codex alone has 10k+ files), so a
/// dedicated loading indicator is the difference between "the app is
/// frozen" and "the app is working".
#[derive(Clone, Debug, PartialEq)]
pub struct DiscoveryState {
    pub loading: Signal<bool>,
    pub error: Signal<Option<String>>,
}

/// Resolve the active [`DataSource`].
///
/// Resolution order:
/// 1. `SL_VIEWER_DEMO=1` enables explicit in-memory demo data.
/// 2. `FORGE_DB` loads a Forge SQLite corpus when the sqlite feature is enabled.
/// 3. Default: discover native local session stores.
///
/// The WASM launch path interprets the default as the local daemon API,
/// because a browser cannot read native corpus directories directly.
fn resolve_data_source() -> DataSource {
    if std::env::var("SL_VIEWER_DEMO").as_deref() == Ok("1") || visual_fixture_active() {
        return DataSource::Mock;
    }
    #[cfg(feature = "sqlite")]
    if let Ok(path) = std::env::var("FORGE_DB") {
        let p = std::path::PathBuf::from(path);
        return DataSource::ForgeDb(p);
    }
    DataSource::Auto
}

/// Load the persisted custom corpus paths at startup.
///
/// Missing or unreadable files degrade silently to an empty
/// [`CustomCorpusPath`] — the viewer must always be able to launch, even
/// if the config directory is locked down. Parse errors are logged to
/// stderr so the operator notices but the UI does not break.
fn initial_custom_corpus_paths() -> CustomCorpusPath {
    match crate::corpus_paths::load_config() {
        Ok(config) => CustomCorpusPath::from(config.custom_paths),
        Err(error) => {
            eprintln!("[sl-viewer] custom corpus paths unavailable: {error}");
            CustomCorpusPath::default()
        }
    }
}

fn initial_tab_for_viewer() -> Tab {
    if query_fixture_active("history-empty") {
        Tab::History
    } else if query_fixture_active("search-empty") || query_fixture_active("search-error") {
        Tab::Search
    } else if query_fixture_active("replay-error") {
        Tab::Replay
    } else if query_fixture_active("stream-skeleton") {
        Tab::LiveFeed
    } else {
        // Honour the persisted default tab so a user who lands on Search
        // every time does not have to click into it on every launch.
        let persisted = Settings::load();
        default_tab_to_tab(persisted.default_tab)
    }
}

/// Root application component.
///
/// Multi-view layout:
/// - **Bundles** — browse compiled continuation bundles (the original view)
/// - **History** — session history timeline (renders real Forge sessions when
///   `FORGE_DB` env var points at a Forge SQLite database)
/// - **Memory** — wiki/docs view of distilled memories
///
/// Real corpus data is loaded once at startup and injected via Dioxus context
/// so every child component can access it without prop-drilling.
/// Derive `ContinuationBundle`s from real session data.
///
/// One `ContinuationBundle` per session (`source_id = session.id`).
/// First Bundle is `BundleKind::Context` (title + corpus) if a title exists.
/// Then one `Bundle` per message with `BundleKind` derived from `Role`.
fn build_bundles_from_sessions(sessions: &[Session]) -> Vec<ContinuationBundle> {
    let mut out: Vec<ContinuationBundle> = Vec::with_capacity(sessions.len());
    for s in sessions {
        let mut cb = ContinuationBundle::new(s.id.clone());
        if let Some(title) = &s.title {
            cb.bundles.push(Bundle::new(
                BundleKind::Context,
                serde_json::json!({
                    "title": title,
                    "corpus": format!("{:?}", s.corpus),
                }),
            ));
        }
        for msg in &s.messages {
            let kind = match msg.role {
                Role::User | Role::Subagent => BundleKind::Intent,
                Role::Assistant => BundleKind::Worklog,
                Role::Tool => BundleKind::Contract,
                Role::System => BundleKind::Provenance,
            };
            cb.bundles.push(Bundle::new(
                kind,
                serde_json::json!({
                    "role": format!("{:?}", msg.role),
                    "content": msg.content,
                }),
            ));
        }
        out.push(cb);
    }
    out
}

// `App` is a Dioxus component (mounted by name from main.rs / web entry).
/// Inline SVG icons for each tab (loaded at compile time).
const ICON_SVG_BUNDLES: &str = include_str!("../../../assets/icons/line/bundles.svg");
const ICON_SVG_HISTORY: &str = include_str!("../../../assets/icons/line/history.svg");
const ICON_SVG_MEMORY: &str = include_str!("../../../assets/icons/line/memory.svg");
const ICON_SVG_UNFINISHED: &str = include_str!("../../../assets/icons/line/unfinished.svg");
const ICON_SVG_TIMELINE: &str = include_str!("../../../assets/icons/line/timeline.svg");
const ICON_SVG_LIVE: &str = include_str!("../../../assets/icons/line/live.svg");
const ICON_SVG_SEARCH: &str = include_str!("../../../assets/icons/line/search.svg");
const ICON_SVG_REPLAY: &str = include_str!("../../../assets/icons/line/replay.svg");
const ICON_SVG_CORPUS: &str = include_str!("../../../assets/icons/line/corpus.svg");
const ICON_SVG_SETTINGS: &str = include_str!("../../../assets/icons/line/settings.svg");

/// Brand mascot (Getta) for the launch splash. Embedded at compile time so
/// the splash renders even before the assets server is reachable. The 2.5D
/// line-art "listening" pose matches the always-on default — happy /
/// thinking variants can be swapped in later via a runtime selector if
/// the launch state needs to surface.
const SPLASH_MASCOT_SVG: &str = include_str!("../../../assets/brand/mascot/getta-base.svg");

/// Lookup table for tab icon SVGs.
fn icon_svg(tab_icon: &str) -> &'static str {
    match tab_icon {
        "bundles" => ICON_SVG_BUNDLES,
        "history" => ICON_SVG_HISTORY,
        "memory" => ICON_SVG_MEMORY,
        "unfinished" => ICON_SVG_UNFINISHED,
        "timeline" => ICON_SVG_TIMELINE,
        "live" => ICON_SVG_LIVE,
        "search" => ICON_SVG_SEARCH,
        "replay" => ICON_SVG_REPLAY,
        "corpus" => ICON_SVG_CORPUS,
        "settings" => ICON_SVG_SETTINGS,
        _ => ICON_SVG_BUNDLES,
    }
}

// `App` is the Dioxus entry point — main.rs and the web launcher mount it
// by name, so the upper-case identifier is part of the public surface.
#[allow(non_snake_case)]
pub fn App() -> Element {
    #[cfg(feature = "web")]
    use_effect(|| {
        let script = if query_fixture_active("launch-splash-light") {
            r#"
            document.documentElement.lang = 'en';
            document.documentElement.dataset.theme = 'light';
            window.localStorage.setItem('sl-viewer-theme', 'light');
            "#
        } else {
            r#"
            document.documentElement.lang = 'en';
            const stored = window.localStorage.getItem('sl-viewer-theme');
            const prefersLight = window.matchMedia?.('(prefers-color-scheme: light)').matches;
            const theme = stored === 'light' || stored === 'dark'
                ? stored
                : (prefersLight ? 'light' : 'dark');
            document.documentElement.dataset.theme = theme;
            "#
        };
        let _ = document::eval(script);
    });

    #[cfg(feature = "web")]
    use_effect(|| {
        // Other visual fixtures strip the splash so empty/error goldens stay clean.
        // Splash hold fixtures keep it pinned for S1 capture.
        if visual_fixture_active() && !splash_hold_fixture_active() {
            let _ = document::eval("document.querySelector('.launch-splash')?.remove();");
        }
    });

    // Load sessions once at the root; propagate the live signal via context.
    // Desktop corpus discovery runs on Tokio's blocking pool so the window
    // renders immediately. The web build keeps its synchronous mock path and
    // does not enable the optional Tokio dependency.
    let mut sessions_signal = use_signal(Vec::<Session>::new);
    let mut error_signal: Signal<Option<String>> = use_signal(|| None);
    let mut loading_signal: Signal<bool> = use_signal(|| true);
    let reload_trigger: Signal<u32> = use_signal(|| 0u32);
    let mut discovery_generation = use_signal(DiscoveryGeneration::default);
    let custom_paths_signal: Signal<CustomCorpusPath> = use_signal(initial_custom_corpus_paths);
    use_context_provider(|| ReloadTrigger(reload_trigger));
    use_context_provider(|| CustomCorpusPaths(custom_paths_signal));
    use_context_provider(|| DiscoveryState { loading: loading_signal, error: error_signal });
    use_effect(move || {
        let _ = reload_trigger();
        let _ = custom_paths_signal();
        let request_generation = discovery_generation.with_mut(DiscoveryGeneration::next);
        loading_signal.set(true);
        error_signal.set(None);

        #[cfg(all(feature = "web", not(feature = "desktop")))]
        {
            let source = resolve_data_source();
            let custom_snapshot = custom_paths_signal.cloned();
            spawn(async move {
                let result = if matches!(&source, DataSource::Mock) {
                    load_sessions_with_custom(&source, &custom_snapshot)
                } else {
                    crate::daemon_source::fetch_daemon_sessions().await
                };
                if !discovery_generation
                    .with(|generation| generation.is_current(request_generation))
                {
                    return;
                }
                loading_signal.set(false);
                match result {
                    Ok(sessions) => sessions_signal.set(sessions),
                    Err(error) => error_signal.set(Some(error)),
                }
            });
        }

        #[cfg(not(all(feature = "web", not(feature = "desktop"))))]
        {
            let source = resolve_data_source();
            let custom_snapshot = custom_paths_signal.cloned();
            spawn(async move {
                let result: std::result::Result<Result<Vec<Session>, String>, String> = {
                    #[cfg(feature = "desktop")]
                    {
                        tokio::task::spawn_blocking(move || {
                            load_sessions_with_custom(&source, &custom_snapshot)
                        })
                        .await
                        .map_err(|error| error.to_string())
                    }
                    #[cfg(not(feature = "desktop"))]
                    {
                        Ok(load_sessions_with_custom(&source, &custom_snapshot))
                    }
                };
                if !discovery_generation
                    .with(|generation| generation.is_current(request_generation))
                {
                    return;
                }
                loading_signal.set(false);
                match result {
                    Ok(Ok(sessions)) => {
                        sessions_signal.set(sessions);
                    }
                    Ok(Err(e)) => {
                        error_signal.set(Some(e));
                    }
                    Err(e) => {
                        error_signal.set(Some(format!("Internal error: {e}")));
                    }
                }
            });
        }
    });
    use_context_provider(|| SessionContext(sessions_signal));

    // Desktop menu bar wiring: dispatch each `muda::MenuEvent` to the same
    // DOM controls the keyboard hotkeys already use, so a single source of
    // truth owns state (palette, help, theme, reload). File → Reload
    // Discovery is the one case that mutates Rust state directly because
    // it triggers a fresh `tokio::spawn_blocking(load_sessions)` from the
    // `use_effect` above.
    #[cfg(feature = "desktop")]
    {
        let mut reload_trigger_for_menu = reload_trigger;
        use dioxus::desktop::use_muda_event_handler;
        use_muda_event_handler(move |event| {
            use crate::menu::{
                ID_APP_ABOUT, ID_APP_SETTINGS, ID_EDIT_FIND, ID_FILE_RELOAD_DISCOVERY,
                ID_FILE_SETTINGS, ID_HELP_TOGGLE, ID_VIEW_COMMAND_PALETTE, ID_VIEW_RELOAD,
                ID_VIEW_TOGGLE_THEME,
            };
            match event.id().0.as_str() {
                ID_VIEW_COMMAND_PALETTE => {
                    let _ = document::eval(
                        "document.getElementById('viewer-palette-button')?.click();",
                    );
                }
                ID_HELP_TOGGLE => {
                    let _ =
                        document::eval("document.getElementById('viewer-help-button')?.click();");
                }
                ID_VIEW_TOGGLE_THEME => {
                    let _ =
                        document::eval("document.getElementById('viewer-theme-toggle')?.click();");
                }
                ID_VIEW_RELOAD => {
                    // Cmd+R: re-fetch the corpus (same effect as the Raw
                    // Sessions tab's "Reload discovery" button).
                    reload_trigger_for_menu.with_mut(|t| *t = t.wrapping_add(1));
                }
                ID_FILE_RELOAD_DISCOVERY => {
                    reload_trigger_for_menu.with_mut(|t| *t = t.wrapping_add(1));
                }
                ID_EDIT_FIND => {
                    // Stub: focus the existing Search tab button so keyboard
                    // ⌘F opens the search pane. A dedicated search input
                    // focus is a follow-up; today the Search tab body owns
                    // its own keyboard listener.
                    let _ = document::eval("document.getElementById('tab-search')?.click();");
                }
                ID_APP_SETTINGS | ID_FILE_SETTINGS => {
                    // Settings dialog is not implemented yet; surface a
                    // discoverable stub so users (and the visual-fixture
                    // suites) see the menu item work end-to-end.
                    let _ = document::eval(
                        "window.alert('SessionLedger settings are coming soon.\\n\\nSee docs/functional_requirements.md for the roadmap.');",
                    );
                }
                ID_APP_ABOUT => {
                    let payload = cli_help::version_text().replace('\'', "\\'");
                    let script = format!(
                        "window.alert('SessionLedger Viewer\\n\\n{}\\n\\nA hexagonal session-bundle compiler + viewer for OKF streams.');",
                        payload
                    );
                    let _ = document::eval(&script);
                }
                _ => {}
            }
        });
    }

    // Persisted user settings (theme + default tab). Loaded once at mount;
    // mutations propagate through `SettingsSignal` and the effect below
    // persists them back to `settings.json`.
    let initial_settings = Settings::load();
    let mut settings_signal = use_signal(|| initial_settings);
    use_context_provider(|| SettingsSignal(settings_signal));
    let settings_for_persist = settings_signal;
    use_effect(move || {
        let snapshot = settings_for_persist();
        // Best-effort write — failures here should not crash the viewer.
        if let Err(err) = snapshot.save() {
            eprintln!("[sl-viewer] could not persist settings: {err}");
        }
    });
    let mut help_open: Signal<bool> = use_signal(|| false);
    let mut palette_open: Signal<bool> = use_signal(|| false);
    #[cfg(feature = "web")]
    let mut splash_visible: Signal<bool> = use_signal(|| true);
    #[cfg(all(feature = "desktop", not(feature = "web")))]
    let mut splash_visible: Signal<bool> = use_signal(|| true);
    #[cfg(not(any(feature = "web", feature = "desktop")))]
    let splash_visible: Signal<bool> = use_signal(|| true);
    let mut active_tab: Signal<Tab> = use_signal(initial_tab_for_viewer);
    let colors = ThemeColors::dark();

    #[cfg(feature = "web")]
    use_effect(move || {
        if !splash_hold_fixture_active() {
            spawn(async move {
                let _ = document::eval(
                    "await new Promise((resolve) => window.setTimeout(resolve, 1800));",
                )
                .await;
                splash_visible.set(false);
            });
        }
    });

    #[cfg(all(feature = "desktop", not(feature = "web")))]
    use_effect(move || {
        if !splash_hold_fixture_active() {
            spawn(async move {
                tokio::time::sleep(splash_dismiss_delay()).await;
                splash_visible.set(false);
            });
        }
    });

    let mut close_help = move || {
        help_open.set(false);
        let _ = document::eval("document.getElementById('viewer-help-button')?.focus();");
    };

    let mut open_help = move || {
        palette_open.set(false);
        help_open.set(true);
        let _ = document::eval(
            "window.requestAnimationFrame(() => document.querySelector('.help-overlay-close')?.focus());",
        );
    };

    let mut toggle_help = move || {
        if help_open() {
            close_help();
        } else {
            open_help();
        }
    };

    let mut close_palette = move || {
        palette_open.set(false);
        let _ = document::eval("document.getElementById('viewer-palette-button')?.focus();");
    };

    let mut open_palette = move || {
        help_open.set(false);
        palette_open.set(true);
        let _ = document::eval(
            "window.requestAnimationFrame(() => document.querySelector('.command-palette-option.is-active')?.focus());",
        );
    };

    let mut toggle_palette = move || {
        if palette_open() {
            close_palette();
        } else {
            open_palette();
        }
    };

    // Global `?` / Cmd+K / Escape: click existing controls so Dioxus onclick
    // handlers own state (avoids wasm Closure / eval bridge re-render gaps).
    #[cfg(feature = "web")]
    use_effect(|| {
        let script = r#"
            if (!window.__slHelpKeyClickBridge) {
              window.__slHelpKeyClickBridge = true;
              document.addEventListener('keydown', (e) => {
                // Cmd+K / Ctrl+K — open palette even while typing in fields.
                if ((e.metaKey || e.ctrlKey) && (e.key === 'k' || e.key === 'K')) {
                  e.preventDefault();
                  document.getElementById('viewer-palette-button')?.click();
                  return;
                }

                // Modal overlays close on Escape before the typing guard so focus
                // in a text field cannot trap the user behind help or the palette.
                if (e.key === 'Escape') {
                  const paletteClose = document.querySelector('.command-palette-close');
                  if (paletteClose) {
                    e.preventDefault();
                    paletteClose.click();
                    return;
                  }
                  const closeBtn = document.querySelector('.help-overlay-close');
                  if (closeBtn) {
                    e.preventDefault();
                    closeBtn.click();
                    return;
                  }
                  const clearCancel = document.querySelector('[data-testid="search-clear-cancel-btn"]');
                  if (clearCancel) {
                    e.preventDefault();
                    clearCancel.click();
                    return;
                  }
                }

                const el = document.activeElement;
                const tag = (el && el.tagName) || '';
                const typing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(tag) || (el && el.isContentEditable);

                if (typing) {
                  return;
                }
                const isHelp = e.key === '?' || (e.code === 'Slash' && e.shiftKey);
                if (isHelp) {
                  e.preventDefault();
                  document.getElementById('viewer-help-button')?.click();
                  return;
                }
              }, true);
            }

            // Visual and browser harnesses must not send global shortcuts until
            // the document-level bridge above exists.  Publish readiness only
            // after installing (or confirming) that listener.
            document.documentElement.dataset.slHotkeysReady = 'true';
            window.dispatchEvent(new Event('sl-viewer-hotkeys-ready'));
            "#;
        let _ = document::eval(script);
    });

    let mut activate = move |tab: Tab| {
        active_tab.set(tab);
        let _ = document::eval(&format!("document.getElementById('{}')?.focus();", tab.id()));
    };

    let tab_body = match active_tab() {
        Tab::Bundles => rsx! { BundlesTab {} },
        Tab::History => rsx! { HistoryTimeline {} },
        Tab::Unfinished => rsx! { UnfinishedWork {} },
        Tab::Memory => rsx! { MemoryWiki {} },
        Tab::LiveFeed => rsx! { LiveFeed {} },
        Tab::Search => rsx! { SearchView {} },
        Tab::Timeline => {
            let bundles = build_bundles_from_sessions(&sessions_signal.read());
            rsx! { TimelineView { bundles } }
        }
        Tab::Replay => rsx! { ReplayView {} },
        Tab::Corpus => rsx! { CorpusTab {} },
        Tab::Settings => {
            let on_open_corpus = move |_| {
                active_tab.set(Tab::Corpus);
                let _ = document::eval("document.getElementById('tab-corpus')?.focus();");
            };
            rsx! { SettingsTab { on_open_corpus_paths: on_open_corpus } }
        }
    };

    let run_palette_action = move |action: PaletteAction| {
        palette_open.set(false);
        match action {
            PaletteAction::FocusSearch => {
                active_tab.set(Tab::Search);
                let _ = document::eval(
                    r#"
                    window.requestAnimationFrame(() => {
                      const el = document.getElementById('search-since')
                        || document.getElementById('search-since-fixture');
                      el?.focus();
                    });
                    "#,
                );
            }
            PaletteAction::OpenHelp => {
                open_help();
            }
            PaletteAction::NextTab => {
                let idx = active_tab().index();
                activate(Tab::from_index(idx + 1));
            }
            PaletteAction::PrevTab => {
                let idx = active_tab().index();
                let len = Tab::ALL.len();
                activate(Tab::from_index(idx + len - 1));
            }
            PaletteAction::ClearSearch => {
                active_tab.set(Tab::Search);
                let _ = document::eval(
                    r#"
                    window.requestAnimationFrame(() => {
                      const panel = document.getElementById('panel-search');
                      const view = panel?.querySelector('.search-view');
                      if (view) {
                        view.dispatchEvent(
                          new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }),
                        );
                      }
                      const el = document.getElementById('search-since')
                        || document.getElementById('search-since-fixture');
                      el?.focus();
                    });
                    "#,
                );
            }
            PaletteAction::ToggleTheme => {
                // Legacy command: route through the Settings tab so the
                // user's choice persists via the new settings store.
                active_tab.set(Tab::Settings);
                let _ = document::eval(
                    r#"
                    window.requestAnimationFrame(() => {
                      const themeInput = document.querySelector(
                        'input[name="settings-theme"]:not(:checked)'
                      );
                      themeInput?.focus();
                    });
                    "#,
                );
            }
            PaletteAction::OpenSettings => {
                activate(Tab::Settings);
            }
        }
    };

    rsx! {
        style {
            // Design tokens: assets/tokens.css via crate::tokens (C09 L81.8 SSOT).
            "{TOKENS_CSS}{VIEWER_COLOR_SCHEME}
                html, body {{ margin: 0; max-width: 100%; overflow-x: clip; }}
                body {{ font-family: var(--font-body); background: var(--sl-bg); color: var(--sl-text); }}
                .app {{ position: relative; display: flex; flex-direction: column; height: 100vh; width: 100%; max-width: 100vw; overflow: hidden; }}
                .app > .sidebar {{
                    width: 100%;
                    min-width: 0;
                    max-width: 100%;
                    border-right: none;
                    overflow-y: auto;
                    overflow-x: clip;
                    background: var(--sl-surface);
                    display: flex;
                    flex-direction: column;
                    flex: 1;
                    min-height: 0;
                }}
                .viewer-main .sidebar {{
                    width: 100%;
                    min-width: 0;
                    max-width: 100%;
                    border-right: none;
                }}
                .sidebar h2 {{ padding: 16px 20px; margin: 0; font-family: var(--font-ui); font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--sl-text-muted); border-bottom: 1px solid var(--sl-border); }}
                .bundle-entry {{ padding: var(--sl-space-md) var(--sl-space-xl); cursor: pointer; border-bottom: 1px solid var(--sl-border); transition: background var(--sl-motion-fast) var(--sl-ease-out); }}
                .bundle-entry:hover {{ background: var(--sl-surface-muted); }}
                .bundle-entry.selected {{ background: var(--sl-surface-muted); border-left: 3px solid var(--sl-accent); }}
                .bundle-entry .source {{ font-size: 13px; font-weight: 600; color: var(--sl-text); }}
                .bundle-entry .goal {{ font-size: 12px; color: var(--sl-text-muted); margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
                .bundle-entry .meta {{ font-size: 11px; color: var(--sl-text-muted); margin-top: 6px; display: flex; gap: 8px; }}
                .bundle-entry .badge {{ display: inline-block; padding: 1px 8px; border-radius: 4px; font-size: 10px; font-weight: 600; text-transform: uppercase; }}
                .badge-acceptance {{ background: color-mix(in srgb, var(--sl-accent-secondary) 18%, transparent); color: var(--sl-accent-secondary); }}
                .badge-contract {{ background: color-mix(in srgb, var(--sl-accent) 16%, transparent); color: var(--sl-accent); }}
                .detail {{ flex: 1; overflow-y: auto; padding: 32px 40px; }}
                .detail h1 {{ font-family: var(--font-display); font-size: 18px; font-weight: 600; margin: 0 0 24px 0; color: var(--sl-text); }}
                .detail-section {{ margin-bottom: 24px; }}
                .detail-section h3 {{ font-family: var(--font-ui); font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--sl-accent); margin: 0 0 8px 0; }}
                .detail-section p {{ font-size: 14px; line-height: 1.6; margin: 0; color: var(--sl-text); max-width: var(--sl-measure-max); }}
                .detail-section ul {{ margin: 4px 0 0 0; padding-left: 20px; max-width: var(--sl-measure-max); }}
                .detail-section li {{ font-size: 13px; line-height: 1.7; color: var(--sl-text-muted); }}
                .session-transcript {{ display: flex; flex-direction: column; gap: var(--sl-space-md); max-width: 760px; }}
                .transcript-header {{ display: flex; align-items: baseline; justify-content: space-between; gap: var(--sl-space-md); border-bottom: 1px solid var(--sl-border); padding-bottom: var(--sl-space-sm); }}
                .transcript-header h3 {{ margin: 0; font-family: var(--font-ui); font-size: 13px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--sl-accent); }}
                .transcript-count {{ color: var(--sl-text-muted); font-size: 12px; }}
                .transcript-message {{ padding: var(--sl-space-md) var(--sl-space-lg); border: 1px solid var(--sl-border); border-left: 3px solid var(--sl-accent); border-radius: var(--sl-radius-md); background: var(--sl-surface-muted); }}
                .transcript-message p {{ margin: var(--sl-space-xs) 0 0; white-space: pre-wrap; overflow-wrap: anywhere; font-size: 14px; line-height: 1.6; color: var(--sl-text); }}
                .transcript-role {{ font-size: 11px; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase; color: var(--sl-accent); }}
                .transcript-user {{ border-left-color: #6c8cff; }}
                .transcript-assistant {{ border-left-color: #c084fc; }}
                .transcript-subagent {{ border-left-color: #4ade80; }}
                .transcript-tool {{ border-left-color: #fb923c; }}
                .transcript-system {{ border-left-color: #8b8fa3; }}
                .transcript-empty {{ padding: var(--sl-space-md); border: 1px dashed var(--sl-border); color: var(--sl-text-muted); font-size: 13px; }}
                .caption {{ font-family: var(--sl-font-caption); font-size: var(--sl-font-size-caption); line-height: var(--sl-line-height-caption); color: var(--sl-text-muted); }}
                .launch-splash {{
                    position: fixed;
                    inset: 0;
                    z-index: 1000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: var(--sl-bg);
                    animation: splash-dismiss var(--sl-motion-medium) var(--sl-ease-out) forwards;
                    animation-delay: 1.2s;
                }}
                .launch-splash.launch-splash-hold {{
                    animation: none;
                    opacity: 1;
                    visibility: visible;
                    pointer-events: auto;
                }}
                .launch-splash-inner {{ text-align: center; display: flex; flex-direction: column; align-items: center; gap: var(--sl-space-md); }}
                .launch-splash-mascot {{
                    width: 96px;
                    height: 96px;
                    margin: 0 auto var(--sl-space-sm);
                    display: block;
                    filter: drop-shadow(0 4px 14px color-mix(in srgb, var(--sl-accent) 18%, transparent));
                    animation: splash-mascot-float 2.4s ease-in-out infinite;
                }}
                .launch-splash-mascot svg {{ width: 100%; height: 100%; display: block; }}
                .launch-splash-spinner {{
                    display: inline-flex;
                    gap: 6px;
                    margin-top: var(--sl-space-sm);
                }}
                .launch-splash-spinner-dot {{
                    width: 8px;
                    height: 8px;
                    border-radius: 50%;
                    background: var(--sl-accent);
                    opacity: 0.35;
                    animation: splash-spinner-bounce 1.1s ease-in-out infinite;
                }}
                .launch-splash-spinner-dot:nth-child(2) {{ animation-delay: 0.18s; }}
                .launch-splash-spinner-dot:nth-child(3) {{ animation-delay: 0.36s; }}
                .launch-splash-mark {{
                    display: block;
                    font-family: var(--font-display);
                    font-size: 1.75rem;
                    font-weight: 600;
                    color: var(--sl-accent);
                    letter-spacing: -0.02em;
                }}
                .launch-splash-caption {{
                    display: block;
                    margin-top: var(--sl-space-sm);
                    font-family: var(--sl-font-caption);
                    font-size: var(--sl-font-size-caption);
                    line-height: var(--sl-line-height-caption);
                    color: var(--sl-text-muted);
                    text-transform: uppercase;
                    letter-spacing: 0.12em;
                }}
                @keyframes splash-dismiss {{
                    to {{ opacity: 0; visibility: hidden; pointer-events: none; }}
                }}
                @keyframes splash-mascot-float {{
                    0%, 100% {{ transform: translateY(0); }}
                    50% {{ transform: translateY(-6px); }}
                }}
                @keyframes splash-spinner-bounce {{
                    0%, 80%, 100% {{ opacity: 0.35; transform: scale(0.8); }}
                    40% {{ opacity: 1; transform: scale(1); }}
                }}
                .empty-state {{ display: flex; align-items: center; justify-content: center; height: 100%; color: var(--sl-text-muted); font-size: 14px; }}
                .sl-content-skeleton {{ display: flex; flex: 1; min-height: 0; overflow: hidden; }}
                .sl-content-skeleton-bundles {{ flex-direction: row; }}
                .sl-content-skeleton-list {{ flex-direction: column; }}
                .sl-content-skeleton-stream {{ flex-direction: column; flex: 1; padding: var(--sl-space-md) var(--sl-space-lg); box-sizing: border-box; }}
                .sl-skeleton-stream-lines {{ display: flex; flex-direction: column; gap: var(--sl-space-sm); width: 100%; font-family: var(--font-mono); }}
                .sl-skeleton-stream-line-wrap {{ min-height: 16px; }}
                .sl-skeleton-stream-line {{ height: 12px; }}
                .sl-skeleton-list {{ width: 340px; min-width: 340px; max-width: 340px; border-right: 1px solid var(--sl-border); padding: var(--sl-space-sm) 0; box-sizing: border-box; }}
                .sl-skeleton-row {{ padding: var(--sl-space-md) var(--sl-space-xl); border-bottom: 1px solid var(--sl-border); min-height: 72px; box-sizing: border-box; }}
                .sl-skeleton-block {{ border-radius: var(--sl-radius-sm); background: linear-gradient(90deg, var(--sl-skeleton-base) 0%, var(--sl-skeleton-highlight) 50%, var(--sl-skeleton-base) 100%); background-size: 200% 100%; animation: sl-skeleton-shimmer var(--sl-motion-slow) var(--sl-ease-in-out) infinite; }}
                .sl-skeleton-block-title {{ height: 13px; width: 62%; margin-bottom: var(--sl-space-sm); }}
                .sl-skeleton-block-subtitle {{ height: 12px; width: 84%; margin-bottom: var(--sl-space-sm); }}
                .sl-skeleton-block-meta {{ height: 10px; width: 38%; }}
                .sl-skeleton-detail {{ flex: 1; padding: var(--sl-space-2xl) 40px; box-sizing: border-box; }}
                .sl-skeleton-block-heading {{ height: 18px; width: 48%; margin-bottom: var(--sl-space-xl); }}
                .sl-skeleton-block-line {{ height: 14px; width: 100%; max-width: var(--sl-measure-max); margin-bottom: var(--sl-space-md); }}
                .sl-skeleton-block-line-short {{ width: 72%; }}
                @keyframes sl-skeleton-shimmer {{
                    0% {{ background-position: 100% 0; }}
                    100% {{ background-position: -100% 0; }}
                }}
                @media (max-width: 600px) {{
                    .sl-skeleton-list {{ width: 100%; min-width: 0; max-width: 100%; border-right: none; }}
                    .sl-content-skeleton-bundles {{ flex-direction: column; }}
                    .sl-skeleton-detail {{ padding: var(--sl-space-lg); }}
                }}
                .tab-bar {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-bottom: 1px solid var(--sl-border); background: var(--sl-surface-muted); }}
                .tab {{ flex: 1; padding: var(--sl-space-md) var(--sl-space-md); text-align: center; cursor: pointer; font-family: var(--font-ui); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; color: var(--sl-text-muted); border: none; border-bottom: 2px solid transparent; background: transparent; transition: all var(--sl-motion-fast) var(--sl-ease-out); }}
                .tab:hover {{ color: var(--sl-text); background: color-mix(in srgb, var(--sl-accent) 8%, transparent); }}
                .tab.active {{ color: var(--sl-accent); border-bottom-color: var(--sl-accent); background: var(--sl-surface); }}
                .tab:focus {{ outline: none; }}
                .tab:focus-visible {{ outline: 2px solid {colors.focus}; outline-offset: -2px; color: {colors.focus}; }}
                .theme-toggle {{ width: calc(100% - 32px); margin: 10px 16px; padding: 7px 12px; border: 1px solid var(--sl-border); border-radius: 6px; background: var(--sl-surface-muted); color: var(--sl-text); cursor: pointer; font-family: var(--font-ui); font-size: 12px; font-weight: 600; }}
                .theme-toggle:hover {{ border-color: var(--sl-accent); color: var(--sl-accent); }}
                .theme-toggle:focus-visible {{ outline: 2px solid {colors.focus}; outline-offset: 2px; }}
                .viewer-utilities {{ position: absolute; z-index: 2; left: 0; bottom: 0; width: 340px; padding-bottom: var(--sl-space-sm); background: var(--sl-surface); }}
                .help-toggle {{ width: calc(100% - 32px); margin: 10px 16px 0; padding: 7px 12px; border: 1px solid var(--sl-border); border-radius: 6px; background: var(--sl-surface-muted); color: var(--sl-text); cursor: pointer; font-family: var(--font-ui); font-size: 12px; font-weight: 600; }}
                .help-toggle:hover {{ border-color: var(--sl-accent); color: var(--sl-accent); }}
                .help-toggle:focus-visible {{ outline: 2px solid {colors.focus}; outline-offset: 2px; }}
                .help-overlay-backdrop {{ position: fixed; inset: 0; z-index: 1100; background: color-mix(in srgb, var(--sl-bg) 35%, transparent); }}
                .help-overlay {{ position: fixed; z-index: 1101; top: 50%; left: 50%; transform: translate(-50%, -50%); width: min(640px, calc(100vw - 32px)); max-height: min(80vh, 720px); overflow: auto; margin: 0; padding: var(--sl-space-lg) var(--sl-space-xl); box-sizing: border-box; border: 1px solid var(--sl-border); border-radius: var(--sl-radius-lg); background: var(--sl-surface); color: var(--sl-text); box-shadow: 0 16px 48px color-mix(in srgb, var(--sl-bg) 55%, transparent); }}
                .help-overlay-header {{ display: flex; align-items: center; justify-content: space-between; gap: var(--sl-space-md); margin-bottom: var(--sl-space-md); }}
                .help-overlay-header h2 {{ margin: 0; font-family: var(--font-ui); font-size: 1rem; font-weight: 600; }}
                .help-overlay-close {{ padding: 6px 12px; border: 1px solid var(--sl-border); border-radius: var(--sl-radius-sm); background: var(--sl-surface-muted); color: var(--sl-text); cursor: pointer; font-family: var(--font-ui); font-size: 12px; font-weight: 600; }}
                .help-overlay-close:hover {{ border-color: var(--sl-accent); color: var(--sl-accent); }}
                .help-overlay-close:focus-visible {{ outline: 2px solid {colors.focus}; outline-offset: 2px; }}
                .help-overlay-lede {{ margin: 0 0 var(--sl-space-md); font-size: 13px; line-height: 1.5; color: var(--sl-text-muted); max-width: var(--sl-measure-max); }}
                .help-overlay-table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
                .help-overlay-table th, .help-overlay-table td {{ padding: 8px 10px; border-bottom: 1px solid var(--sl-border); text-align: left; vertical-align: top; }}
                .help-overlay-table th {{ font-size: 11px; text-transform: uppercase; letter-spacing: 0.4px; color: var(--sl-text-muted); }}
                .help-overlay-keys kbd {{ display: inline-block; padding: 2px 6px; border: 1px solid var(--sl-border); border-radius: var(--sl-radius-sm); background: var(--sl-surface-muted); font-family: var(--font-mono); font-size: 12px; }}
                .help-overlay-footer {{ margin: var(--sl-space-md) 0 0; }}
                .command-palette-backdrop {{ position: fixed; inset: 0; z-index: 1200; background: color-mix(in srgb, var(--sl-bg) 35%, transparent); }}
                .command-palette {{ position: fixed; z-index: 1201; top: 18%; left: 50%; transform: translateX(-50%); width: min(480px, calc(100vw - 32px)); max-height: min(70vh, 420px); overflow: auto; margin: 0; padding: var(--sl-space-lg) var(--sl-space-xl); box-sizing: border-box; border: 1px solid var(--sl-border); border-radius: var(--sl-radius-lg); background: var(--sl-surface); color: var(--sl-text); box-shadow: 0 16px 48px color-mix(in srgb, var(--sl-bg) 55%, transparent); }}
                .command-palette-header {{ display: flex; align-items: center; justify-content: space-between; gap: var(--sl-space-md); margin-bottom: var(--sl-space-sm); }}
                .command-palette-header h2 {{ margin: 0; font-family: var(--font-ui); font-size: 1rem; font-weight: 600; }}
                .command-palette-close {{ padding: 6px 12px; border: 1px solid var(--sl-border); border-radius: var(--sl-radius-sm); background: var(--sl-surface-muted); color: var(--sl-text); cursor: pointer; font-family: var(--font-ui); font-size: 12px; font-weight: 600; }}
                .command-palette-close:hover {{ border-color: var(--sl-accent); color: var(--sl-accent); }}
                .command-palette-close:focus-visible {{ outline: 2px solid {colors.focus}; outline-offset: 2px; }}
                .command-palette-lede {{ margin: 0 0 var(--sl-space-md); font-size: 13px; line-height: 1.5; color: var(--sl-text-muted); }}
                .command-palette-lede kbd {{ display: inline-block; padding: 2px 6px; border: 1px solid var(--sl-border); border-radius: var(--sl-radius-sm); background: var(--sl-surface-muted); font-family: var(--font-mono); font-size: 12px; }}
                .command-palette-list {{ list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 4px; }}
                .command-palette-option {{ display: flex; flex-direction: column; gap: 2px; padding: 10px 12px; border: 1px solid transparent; border-radius: var(--sl-radius-sm); cursor: pointer; }}
                .command-palette-option.is-active, .command-palette-option:hover {{ border-color: var(--sl-accent); background: color-mix(in srgb, var(--sl-accent) 10%, transparent); }}
                .command-palette-option:focus-visible {{ outline: 2px solid {colors.focus}; outline-offset: 2px; }}
                .command-palette-option-label {{ font-size: 14px; font-weight: 600; }}
                .command-palette-option-hint {{ font-size: 12px; color: var(--sl-text-muted); }}
                .palette-trigger {{ position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0; }}
                .search-input:focus-visible, .search-btn:focus-visible, .search-advanced-toggle:focus-visible, .retry-btn:focus-visible, .btn:focus-visible, .replay-input:focus-visible, .speed-input:focus-visible, .compare-btn:focus-visible, .sl-error-retry:focus-visible {{ outline: 2px solid {colors.focus}; outline-offset: 2px; }}
                .session-item:focus-visible, .feed-entry:focus-visible {{ outline: 2px solid {colors.focus}; outline-offset: -2px; }}
                .session-list {{ display: flex; flex-direction: column; height: 100%; }}
                .search-input {{ width: 100%; padding: 10px 16px; background: var(--sl-surface-muted); border: 1px solid var(--sl-border); border-radius: 6px; color: var(--sl-text); font-size: 13px; box-sizing: border-box; margin-bottom: 4px; }}
                .session-count {{ padding: 6px 20px; font-size: 11px; color: var(--sl-text-muted); }}
                .session-item {{ padding: var(--sl-space-md) var(--sl-space-xl); cursor: pointer; border-bottom: 1px solid var(--sl-border); transition: background var(--sl-motion-fast) var(--sl-ease-out); }}
                .session-item:hover {{ background: var(--sl-surface-muted); }}
                .session-item.selected {{ background: var(--sl-surface-muted); border-left: 3px solid var(--sl-accent); }}
                .session-source {{ font-size: 13px; font-weight: 600; color: var(--sl-text); }}
                .session-goal {{ font-size: 12px; color: var(--sl-text-muted); margin-top: 4px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
                .session-meta {{ font-size: 11px; color: var(--sl-text-muted); margin-top: 6px; display: flex; gap: 8px; align-items: center; }}
                .meta-bundles {{ color: var(--sl-accent); }}
                .badge {{ display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; }}
                .badge-ok {{ background: color-mix(in srgb, var(--sl-accent-secondary) 18%, transparent); color: var(--sl-accent-secondary); }}
                .badge-contract {{ background: color-mix(in srgb, var(--sl-accent) 16%, transparent); color: var(--sl-accent); }}
                .search-view {{ display: flex; flex-direction: column; height: 100%; overflow-y: auto; }}
                .search-form {{ padding: 0 0 8px 0; border-bottom: 1px solid var(--sl-border); }}
                .search-form-title {{ padding: var(--sl-space-lg) var(--sl-space-xl); margin: 0; font-size: 14px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: var(--sl-text-muted); border-bottom: 1px solid var(--sl-border); }}
                .search-form-hint {{ margin: 0; padding: var(--sl-space-sm) var(--sl-space-xl) 0; font-size: 12px; line-height: 1.45; color: var(--sl-text-muted); }}
                .search-fields {{ display: flex; flex-direction: column; gap: 4px; padding: 10px 16px; }}
                .search-label {{ font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; color: var(--sl-text-muted); }}
                .search-advanced-toggle {{ display: inline-flex; align-items: center; gap: var(--sl-space-sm); margin: var(--sl-space-sm) 0 0; padding: var(--sl-space-sm) var(--sl-space-md); min-height: 44px; border: 1px solid var(--sl-border); border-radius: var(--sl-radius-sm); background: var(--sl-surface-muted); color: var(--sl-accent); font-size: 12px; font-weight: 600; cursor: pointer; transition: background var(--sl-motion-fast) var(--sl-ease-out), border-color var(--sl-motion-fast) var(--sl-ease-out); }}
                .search-advanced-toggle:hover {{ background: color-mix(in srgb, var(--sl-accent) 10%, transparent); border-color: var(--sl-accent); }}
                .search-advanced-toggle:focus-visible {{ outline: 2px solid {colors.focus}; outline-offset: 2px; }}
                .search-advanced-chevron {{ display: inline-block; width: 0.85em; color: var(--sl-text-muted); }}
                .search-advanced-badge {{ margin-left: var(--sl-space-xs); padding: 1px 6px; border-radius: var(--sl-radius-sm); background: color-mix(in srgb, var(--sl-accent-secondary) 18%, transparent); color: var(--sl-accent-secondary); font-size: 10px; font-weight: 700; letter-spacing: 0.02em; }}
                .search-advanced-panel {{ display: flex; flex-direction: column; gap: 4px; margin-top: var(--sl-space-sm); padding-top: var(--sl-space-sm); border-top: 1px solid var(--sl-border); }}
                .search-advanced-panel.is-collapsed {{ display: none; }}
                .search-actions {{ display: flex; gap: 8px; padding: 8px 16px 10px; flex-wrap: wrap; align-items: center; }}
                .search-btn {{ padding: 6px 16px; font-size: 12px; font-weight: 600; border-radius: 5px; cursor: pointer; border: 1px solid var(--sl-border); background: var(--sl-surface-muted); color: var(--sl-text-muted); }}
                .search-btn:hover {{ background: color-mix(in srgb, var(--sl-accent) 8%, transparent); color: var(--sl-text); }}
                .search-btn-primary {{ background: color-mix(in srgb, var(--sl-accent) 16%, transparent); color: var(--sl-accent); border-color: var(--sl-accent); }}
                .search-btn-primary:hover {{ background: color-mix(in srgb, var(--sl-accent) 24%, transparent); color: var(--sl-accent); }}
                .search-clear-title {{ margin: 0 0 4px; font-size: 12px; font-weight: 600; color: var(--sl-text); }}
                .search-clear-desc {{ margin: 0 0 8px; font-size: 12px; color: var(--sl-text-muted); max-width: 22rem; }}
                .session-meta-muted {{ color: var(--sl-text-muted); }}
                .search-results {{ flex: 1; overflow-y: auto; }}
                .search-error {{ padding: 10px 16px; font-size: 13px; color: var(--sl-danger); background: var(--sl-danger-surface); border-bottom: 1px solid var(--sl-border); }}
                .search-empty {{ padding: var(--sl-space-lg) var(--sl-space-xl); font-size: 13px; color: var(--sl-text-muted); }}
                .live-feed {{ display: flex; flex-direction: column; height: 100%; }}
                .live-feed-header {{ display: flex; align-items: center; gap: var(--sl-space-md); padding: var(--sl-space-md) var(--sl-space-lg); border-bottom: 1px solid var(--sl-border); background: var(--sl-bg); }}
                .live-feed-title {{ font-size: 13px; font-weight: 600; color: var(--sl-text); flex: 1; }}
                .feed-status {{ font-size: 11px; font-weight: 600; }}
                .feed-status.live {{ color: var(--sl-accent-secondary); }}
                .feed-status.disconnected {{ color: var(--sl-danger); }}
                .feed-status.connecting {{ color: var(--sl-accent-warning); }}
                .retry-btn {{ padding: var(--sl-space-xs) var(--sl-space-md); font-size: 11px; font-weight: 600; background: var(--sl-surface-muted); border: 1px solid var(--sl-border); border-radius: var(--sl-radius-sm); color: var(--sl-text-muted); cursor: pointer; transition: background var(--sl-motion-fast) var(--sl-ease-out), color var(--sl-motion-fast) var(--sl-ease-out); }}
                .retry-btn:hover {{ background: color-mix(in srgb, var(--sl-accent) 8%, var(--sl-surface-muted)); color: var(--sl-text); }}
                .live-feed-list {{ flex: 1; overflow-y: auto; padding: var(--sl-space-sm) 0; }}
                .feed-empty {{ padding: var(--sl-space-lg) var(--sl-space-xl); font-size: 13px; color: var(--sl-text-muted); }}
                .feed-entry {{ display: flex; gap: var(--sl-space-md); align-items: baseline; padding: var(--sl-space-sm) var(--sl-space-lg); border-bottom: 1px solid var(--sl-border); font-family: var(--font-mono); transition: background var(--sl-motion-fast) var(--sl-ease-out); }}
                .feed-entry:hover {{ background: var(--sl-surface-muted); }}
                .feed-ts {{ font-size: 11px; color: var(--sl-text-muted); white-space: nowrap; }}
                .feed-path {{ font-size: 12px; color: var(--sl-accent); word-break: break-all; }}
                .compare-btn {{ padding: 2px var(--sl-space-sm); font-size: 10px; font-weight: 600; background: var(--sl-surface-muted); border: 1px solid var(--sl-border); border-radius: var(--sl-radius-sm); color: var(--sl-text-muted); cursor: pointer; margin-left: var(--sl-space-sm); transition: background var(--sl-motion-fast) var(--sl-ease-out), color var(--sl-motion-fast) var(--sl-ease-out); }}
                .compare-btn:hover {{ background: color-mix(in srgb, var(--sl-accent) 8%, var(--sl-surface-muted)); color: var(--sl-text); }}
                .compare-btn.active {{ background: color-mix(in srgb, var(--sl-accent) 16%, transparent); color: var(--sl-accent); border-color: var(--sl-accent); }}
                .diff-panel {{ border-top: 2px solid var(--sl-accent); background: var(--sl-bg); padding: 0; flex-shrink: 0; max-height: 340px; overflow-y: auto; }}
                .diff-header {{ display: flex; align-items: center; padding: var(--sl-space-md) var(--sl-space-lg); border-bottom: 1px solid var(--sl-border); background: var(--sl-bg); }}
                .diff-title {{ flex: 1; font-size: 13px; font-weight: 600; color: var(--sl-text); }}
                .diff-badge {{ display: inline-block; margin-left: var(--sl-space-sm); padding: 1px var(--sl-space-sm); border-radius: var(--sl-radius-pill); font-size: 11px; font-weight: 600; background: var(--sl-danger-surface); color: var(--sl-danger); }}
                .diff-badge-same {{ background: color-mix(in srgb, var(--sl-accent-secondary) 18%, transparent); color: var(--sl-accent-secondary); }}
                .diff-close {{ cursor: pointer; font-size: 14px; color: var(--sl-text-muted); padding: 2px var(--sl-space-sm); border-radius: var(--sl-radius-sm); transition: background var(--sl-motion-fast) var(--sl-ease-out), color var(--sl-motion-fast) var(--sl-ease-out); }}
                .diff-close:hover {{ background: var(--sl-surface-muted); color: var(--sl-text); }}
                .diff-col-headers {{ display: grid; grid-template-columns: 160px 1fr 1fr; padding: var(--sl-space-sm) var(--sl-space-lg); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; color: var(--sl-text-muted); border-bottom: 1px solid var(--sl-border); background: var(--sl-bg); }}
                .diff-rows {{ display: flex; flex-direction: column; }}
                .diff-row {{ display: grid; grid-template-columns: 160px 1fr 1fr; padding: var(--sl-space-sm) var(--sl-space-lg); font-size: 12px; border-bottom: 1px solid var(--sl-border); font-family: var(--font-mono); align-items: start; }}
                .diff-row-changed {{ background: color-mix(in srgb, var(--sl-danger) 6%, var(--sl-surface)); }}
                .diff-row-changed .diff-col-a {{ color: var(--sl-danger); }}
                .diff-row-changed .diff-col-b {{ color: var(--sl-accent-secondary); }}
                .diff-field-label {{ color: var(--sl-text-muted); font-weight: 600; font-family: var(--font-ui); font-size: 11px; padding-top: 1px; }}
                .diff-col-a {{ color: var(--sl-text); overflow-wrap: break-word; }}
                .diff-col-b {{ color: var(--sl-text); overflow-wrap: break-word; }}
                .main-content {{ flex: 1; min-width: 0; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }}
                .main-upper {{ flex: 1 1 auto; min-width: 0; min-height: 0; overflow-y: auto; overscroll-behavior: contain; }}
                .bundles-view {{ display: flex; flex-direction: column; height: 100%; min-height: 0; overflow: hidden; }}
                .bundles-view > h2 {{ flex: 0 0 auto; margin: 0; padding: var(--sl-space-xl) var(--sl-space-xl) var(--sl-space-lg); }}
                .bundles-workspace {{ display: flex; flex: 1; min-height: 0; overflow: hidden; }}
                .bundles-workspace > .session-list {{ flex: 0 0 360px; width: 360px; min-width: 280px; overflow-y: auto; border-right: 1px solid var(--sl-border); background: var(--sl-surface); }}
                .bundles-workspace > .main-content {{ background: var(--sl-bg); }}
                .viewer-main {{ flex: 1; min-width: 0; min-height: 0; width: 100%; overflow: hidden; }}
                .corpus-error-banner {{ padding: 0 8px; }}
                .corpus-error-banner .caption {{ display: block; margin-top: var(--sl-space-xs); }}
                @media (max-width: 600px) {{
                    .app > .sidebar {{ flex: 0 0 auto; max-height: 46vh; }}
                    .viewer-main {{ min-height: 0; }}
                    .viewer-utilities {{ position: static; width: 100%; flex: 0 0 auto; }}
                    .bundles-workspace {{ flex-direction: column; overflow-y: auto; }}
                    .bundles-workspace > .session-list {{ flex: 0 0 auto; width: 100%; min-width: 0; max-height: 42%; border-right: none; border-bottom: 1px solid var(--sl-border); }}
                    .tab {{
                        min-height: 44px;
                        min-width: 44px;
                        padding: 12px 8px;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                        box-sizing: border-box;
                    }}
                    .theme-toggle, .help-toggle {{
                        min-height: 44px;
                        padding: 12px 16px;
                        box-sizing: border-box;
                    }}
                    .search-btn, .retry-btn, .search-advanced-toggle {{
                        min-height: 44px;
                        min-width: 44px;
                        padding: 10px 16px;
                        box-sizing: border-box;
                    }}
                    .detail, .timeline-detail, .wiki-page {{
                        padding: 16px;
                        max-width: 100%;
                        box-sizing: border-box;
                    }}
                    .diff-col-headers, .diff-row {{
                        grid-template-columns: minmax(72px, 96px) minmax(0, 1fr) minmax(0, 1fr);
                    }}
                    .replay-controls .btn {{
                        min-height: 44px;
                        min-width: 44px;
                        padding: 10px 16px;
                        box-sizing: border-box;
                    }}
                }}
                @media (min-width: 601px) {{
                    .app {{ flex-direction: row; }}
                    .app > .sidebar {{
                        width: 340px;
                        min-width: 340px;
                        max-width: 340px;
                        flex: 0 0 340px;
                        height: 100%;
                        border-right: 1px solid var(--sl-border);
                    }}
                    .main-content {{ min-width: 0; min-height: 0; }}
                }}
                .sl-loading-spinner {{
                    animation: sl-spin 0.8s linear infinite;
                }}
                @keyframes sl-spin {{
                    to {{ transform: rotate(360deg); }}
                }}
                @media (prefers-reduced-motion: reduce) {{
                    *, *::before, *::after {{
                        animation-duration: 0.01ms !important;
                        animation-iteration-count: 1 !important;
                        transition-duration: 0.01ms !important;
                        scroll-behavior: auto !important;
                    }}
                    .launch-splash:not(.launch-splash-hold) {{
                        animation: none;
                        opacity: 0;
                        visibility: hidden;
                        pointer-events: none;
                    }}
                    .launch-splash.launch-splash-hold {{
                        animation: none !important;
                        opacity: 1 !important;
                        visibility: visible !important;
                        pointer-events: auto !important;
                    }}
                    .sl-loading-spinner {{
                        animation: none !important;
                    }}
                }}
            ",
        }
        div {
            class: "app",
            {
                if splash_visible() {
                    let splash_hold = splash_hold_fixture_active();
                    let splash_class = if splash_hold {
                        "launch-splash launch-splash-hold"
                    } else {
                        "launch-splash"
                    };
                    rsx! {
                        div {
                            class: "{splash_class}",
                            role: "presentation",
                            "data-testid": "launch-splash",
                            div { class: "launch-splash-inner",
                                div {
                                    class: "launch-splash-mascot",
                                    "data-testid": "launch-splash-mascot",
                                    "aria-hidden": "true",
                                    dangerous_inner_html: "{SPLASH_MASCOT_SVG}"
                                }
                                span { class: "launch-splash-mark", "SessionLedger" }
                                span { class: "launch-splash-caption", "Viewer" }
                                div {
                                    class: "launch-splash-spinner",
                                    "data-testid": "launch-splash-spinner",
                                    role: "progressbar",
                                    "aria-label": "Loading viewer",
                                    div { class: "launch-splash-spinner-dot" }
                                    div { class: "launch-splash-spinner-dot" }
                                    div { class: "launch-splash-spinner-dot" }
                                }
                            }
                        }
                    }
                } else {
                    rsx! {}
                }
            }
            div { class: "sidebar",
                nav {
                    "aria-label": "Primary viewer navigation",
                    div {
                        class: "tab-bar",
                        role: "tablist",
                        "aria-label": "SessionLedger views",
                        for tab in Tab::ALL {
                            {
                                let is_active = active_tab() == tab;
                                let cls = if is_active { "tab active" } else { "tab" };
                                let selected = if is_active { "true" } else { "false" };
                                let tab_index = if is_active { "0" } else { "-1" };
                                rsx! {
                                    button {
                                        key: "{tab.id()}",
                                        id: "{tab.id()}",
                                        class: "{cls}",
                                        role: "tab",
                                        r#type: "button",
                                        tabindex: "{tab_index}",
                                        "aria-selected": "{selected}",
                                        "aria-controls": "{tab.panel_id()}",
                                        onclick: move |_| activate(tab),
                                        onkeydown: move |evt: Event<KeyboardData>| {
                                            let len = Tab::ALL.len();
                                            let idx = tab.index();
                                            match evt.key() {
                                                Key::Enter => {
                                                    evt.prevent_default();
                                                    activate(tab);
                                                }
                                                Key::Character(ref ch) if ch == " " => {
                                                    evt.prevent_default();
                                                    activate(tab);
                                                }
                                                Key::ArrowRight => {
                                                    evt.prevent_default();
                                                    let next = Tab::from_index(idx + 1);
                                                    activate(next);
                                                    let _ = document::eval(&format!(
                                                        "document.getElementById('{}')?.focus();",
                                                        next.id()
                                                    ));
                                                }
                                                Key::ArrowLeft => {
                                                    evt.prevent_default();
                                                    let next = Tab::from_index(idx + len - 1);
                                                    activate(next);
                                                    let _ = document::eval(&format!(
                                                        "document.getElementById('{}')?.focus();",
                                                        next.id()
                                                    ));
                                                }
                                                Key::Home => {
                                                    evt.prevent_default();
                                                    activate(Tab::Bundles);
                                                    let _ = document::eval(
                                                        "document.getElementById('tab-bundles')?.focus();",
                                                    );
                                                }
                                                Key::End => {
                                                    evt.prevent_default();
                                                    activate(Tab::Replay);
                                                    let _ = document::eval(
                                                        "document.getElementById('tab-replay')?.focus();",
                                                    );
                                                }
                                                _ => {}
                                            }
                                        },
                                        span {
                                            class: "tab-icon",
                                            dangerous_inner_html: "{icon_svg(tab.icon())}"
                                        }
                                        span { class: "tab-label", "{tab.label()}" }
                                    }
                                }
                            }
                        }
                    }
                }
                if active_tab() == Tab::Bundles {
                    if let Some(ref err) = *error_signal.read() {
                    div { class: "corpus-error-banner",
                        ErrorState {
                            message: format!("Corpus load failed ({err}); no sessions are available."),
                        }
                    }
                    }
                }
            }
            main {
                class: "viewer-main",
                div {
                    id: "{active_tab().panel_id()}",
                    role: "tabpanel",
                    "aria-labelledby": "{active_tab().id()}",
                    {tab_body}
                }
            }
            // Keep utility controls after the active panel so keyboard focus moves
            // from the selected tab into the panel before reaching chrome actions.
            div { class: "viewer-utilities",
                button {
                    id: "viewer-help-button",
                    class: "help-toggle",
                    r#type: "button",
                    "aria-haspopup": "dialog",
                    "aria-expanded": if help_open() { "true" } else { "false" },
                    "aria-controls": "keyboard-help-dialog",
                    onclick: move |_| toggle_help(),
                    "Help (?)"
                }
                button {
                    id: "viewer-palette-button",
                    class: "palette-trigger",
                    r#type: "button",
                    "aria-haspopup": "dialog",
                    "aria-expanded": if palette_open() { "true" } else { "false" },
                    "aria-controls": "command-palette-dialog",
                    "aria-label": "Open command palette",
                    onclick: move |_| toggle_palette(),
                    "Command palette (Ctrl+K)"
                }
                button {
                    id: "viewer-theme-toggle",
                    class: "theme-toggle",
                    r#type: "button",
                    "aria-label": "Toggle light and dark theme",
                    onclick: move |_| {
                        let next_theme = match settings_signal().theme {
                            Theme::Light => Theme::Dark,
                            Theme::Dark | Theme::System => Theme::Light,
                        };
                        settings_signal.with_mut(|settings| {
                            settings.theme = next_theme;
                        });
                        let resolved = match next_theme {
                            Theme::Light => "light",
                            Theme::Dark => "dark",
                            Theme::System => "dark",
                        };
                        let _ = document::eval(&format!(
                            "document.documentElement.dataset.theme = '{resolved}'; window.localStorage.setItem('sl-viewer-theme', '{resolved}');"
                        ));
                    },
                    "Theme"
                }
                button {
                    id: "viewer-settings-button",
                    class: "help-toggle",
                    r#type: "button",
                    onclick: move |_| activate(Tab::Settings),
                    "Settings"
                }
            }
            HelpOverlay {
                open: help_open(),
                on_close: move |_| close_help(),
            }
            CommandPalette {
                open: palette_open(),
                on_close: move |_| close_palette(),
                on_run: run_palette_action,
            }
        }
    }
}

// ---------------------------------------------------------------------------
// Bundles tab (original compiled-bundles view)
// ---------------------------------------------------------------------------

/// The compiled-bundles tab — the original sidebar + detail panel.
#[component]
fn BundlesTab() -> Element {
    let ctx = use_context::<SessionContext>();
    let discovery = use_context::<DiscoveryState>();
    let mut reload = use_context::<ReloadTrigger>();
    let mut selected_idx: Signal<Option<usize>> = use_signal(|| Some(0));
    let mut compare_idx: Signal<Option<usize>> = use_signal(|| None);

    // Compute bundles directly from the session context. Reading `ctx.0` is
    // a reactive read in Dioxus 0.6 — the function body re-runs whenever
    // the async corpus loader updates the signal. Earlier revisions used
    // `use_effect` + a separate `bundles` signal, but the effect ran only
    // once at mount (when sessions were empty), so the tab stayed frozen
    // on "No bundles" forever even after discovery finished.
    let bundles = build_bundles_from_sessions(&ctx.0.read());
    let loading = discovery.loading.cloned();
    let load_error = discovery.error.cloned();

    if query_fixture_active("first-run") {
        return rsx! {
            h2 { "Compiled Bundles" }
            FirstRunEmpty {}
        };
    }

    if query_fixture_active("error-color") {
        return rsx! {
            h2 { "Compiled Bundles" }
            ErrorColorFixture {}
        };
    }

    if query_fixture_active("loading-long") {
        return rsx! {
            h2 { "Compiled Bundles" }
            LoadingState {
                message: "Loading bundles…".to_string(),
                patience_hint: true,
            }
        };
    }
    if query_fixture_active("skeleton") {
        return rsx! {
            h2 { "Compiled Bundles" }
            ContentSkeleton { layout: SkeletonLayout::Bundles, list_rows: 4 }
        };
    }
    // Discovery is still running — show the same skeleton the visual
    // fixture path uses so the operator knows the app is working, not
    // frozen. Full codex+claude+cursor scans can take minutes.
    if loading && bundles.is_empty() {
        return rsx! {
            h2 { "Compiled Bundles" }
            LoadingState {
                message: "Discovering local session corpus…".to_string(),
                patience_hint: true,
            }
        };
    }
    if let Some(err) = load_error.as_ref() {
        return rsx! {
            h2 { "Compiled Bundles" }
            ErrorState {
                message: err.clone(),
                retryable: true,
                on_retry: move |_| reload.0.with_mut(|t| *t += 1),
            }
        };
    }
    if bundles.is_empty() {
        return rsx! {
            h2 { "Compiled Bundles" }
            FirstRunEmpty {}
        };
    }

    let summaries: Vec<BundleSummary> = bundles.iter().map(summarize).collect();
    let detail = selected_idx().and_then(|idx| bundles.get(idx)).map(extract_detail);

    // Determine if we should show the diff panel.
    let diff_pair: Option<(OkfBundle, OkfBundle)> =
        selected_idx().zip(compare_idx()).and_then(|(ia, ib)| {
            let a = bundles.get(ia).as_ref().map(|b| OkfBundle::from_bundle(b))?;
            let c = bundles.get(ib).as_ref().map(|b| OkfBundle::from_bundle(b))?;
            Some((a, c))
        });

    rsx! {
        div {
            class: "bundles-view",
            onkeydown: move |evt: Event<KeyboardData>| {
                if evt.key() == Key::Escape && compare_idx().is_some() {
                    evt.prevent_default();
                    compare_idx.set(None);
                }
            },
            h2 { "Compiled Bundles" }
            div { class: "bundles-workspace",
                SessionListWithCompare {
                    items: summaries,
                    selected_idx: selected_idx(),
                    compare_idx: compare_idx(),
                    on_select: move |idx| selected_idx.set(Some(idx)),
                    on_compare: move |idx| {
                        // Toggle: clicking same row again clears compare slot.
                        if compare_idx() == Some(idx) {
                            compare_idx.set(None);
                        } else {
                            compare_idx.set(Some(idx));
                        }
                    },
                }
                div { class: "main-content",
                    div { class: "main-upper", tabindex: "0",
                        match detail {
                            Some(d) => rsx! { DetailView { detail: d.clone() } },
                            None => rsx! {
                                div { class: "empty-state", "Select a bundle from the inbox to view its conversation" }
                            },
                        }
                    }
                    if let Some((a, b)) = diff_pair {
                        BundleDiff {
                            bundle_a: a,
                            bundle_b: b,
                            on_close: move |_| compare_idx.set(None),
                        }
                    }
                }
            }
        }
    }
}

// ---------------------------------------------------------------------------
// SessionList variant with a per-row "Compare" button
// ---------------------------------------------------------------------------

#[derive(Props, Clone, PartialEq)]
struct SessionListWithCompareProps {
    items: Vec<BundleSummary>,
    selected_idx: Option<usize>,
    compare_idx: Option<usize>,
    on_select: EventHandler<usize>,
    on_compare: EventHandler<usize>,
}

#[component]
fn SessionListWithCompare(props: SessionListWithCompareProps) -> Element {
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
            div { class: "session-count",
                "{count} session{plural}"
                if props.compare_idx.is_some() {
                    span { style: "color:var(--sl-accent); margin-left:var(--sl-space-sm);", "compare slot active" }
                }
            }
            for (orig_idx, summary) in filtered.into_iter() {
                {
                    let is_selected = props.selected_idx == Some(orig_idx);
                    let is_compare = props.compare_idx == Some(orig_idx);
                    let cls = if is_selected { "session-item selected" } else { "session-item" };
                    let compare_cls = if is_compare { "compare-btn active" } else { "compare-btn" };
                    let s = summary.clone();
                    rsx! {
                        div {
                            class: "{cls}",
                            role: "button",
                            tabindex: "0",
                            onclick: move |_| props.on_select.call(orig_idx),
                            onkeydown: move |evt: Event<KeyboardData>| {
                                let activate = match evt.key() {
                                    Key::Enter => true,
                                    Key::Character(ref ch) => ch == " ",
                                    _ => false,
                                };
                                if activate {
                                    evt.prevent_default();
                                    props.on_select.call(orig_idx);
                                }
                            },
                            div { class: "session-source",
                                "{s.source_id}"
                                span {
                                    class: "{compare_cls}",
                                    title: "Compare this bundle",
                                    "aria-label": "Compare this bundle",
                                    onclick: move |evt| {
                                        evt.stop_propagation();
                                        props.on_compare.call(orig_idx);
                                    },
                                    "Compare"
                                }
                            }
                            div { class: "session-goal", "{s.intent_goal}" }
                            div { class: "session-meta",
                                span { class: "meta-bundles", "{s.bundle_count} slices" }
                                if s.has_acceptance {
                                    span { class: "badge badge-ok", "AC" }
                                }
                                if s.has_contract {
                                    span { class: "badge badge-contract", "◎ CT" }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

/// The right-hand detail panel showing full bundle contents.
#[component]
fn DetailView(detail: BundleDetail) -> Element {
    rsx! {
        // The pane owns vertical scrolling at narrow widths.  Make that
        // region keyboard-focusable so keyboard and assistive-tech users can
        // reach its content without relying on pointer-wheel scrolling.
        div {
            class: "detail",
            tabindex: "0",
            role: "region",
            aria_label: "Session bundle details",
            h1 { "Bundle: {detail.source_id}" }

            // --- Intent section ---
            div { class: "detail-section",
                h3 { "Intent" }
                if let Some(ref goal) = detail.intent_goal {
                    p { "{goal}" }
                } else {
                    p { "(no goal)" }
                }
            }

            div { class: "detail-section transcript-section",
                SessionTranscript { session_id: detail.source_id.clone() }
            }

            // --- Acceptance signals ---
            if !detail.acceptance_signals.is_empty() {
                div { class: "detail-section",
                    h3 { "Acceptance Signals" }
                    ul {
                        for sig in &detail.acceptance_signals {
                            li { "{sig}" }
                        }
                    }
                }
            }

            // --- Constraints ---
            if !detail.constraints.is_empty() {
                div { class: "detail-section",
                    h3 { "Constraints" }
                    ul {
                        for c in &detail.constraints {
                            li { "{c}" }
                        }
                    }
                }
            }

            // --- Context ---
            div { class: "detail-section",
                h3 { "Context" }
                if let Some(ref cwd) = detail.context_cwd {
                    p { "cwd: {cwd}" }
                }
                if let Some(ref title) = detail.context_title {
                    p { "title: {title}" }
                }
                if detail.context_cwd.is_none() && detail.context_title.is_none() {
                    p { "(no context data)" }
                }
            }

            // --- Contract criteria ---
            if !detail.contract_criteria.is_empty() {
                div { class: "detail-section",
                    h3 { "Contract Criteria" }
                    ul {
                        for crit in &detail.contract_criteria {
                            li { "{crit}" }
                        }
                    }
                }
            }

            // --- Token estimate ---
            div { class: "detail-section",
                h3 { "Token Budget" }
                p { "{detail.total_token_estimate} tokens across all slices" }
            }
        }
    }
}
