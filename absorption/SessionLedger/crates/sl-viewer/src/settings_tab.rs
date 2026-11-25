//! Settings tab — persistence-backed user preferences (FR-VIEWER-SETTINGS-1).
//!
//! Three sub-sections:
//!
//! - **Appearance** — Light / Dark / System radio (persisted via
//!   [`crate::settings::Settings`]).
//! - **Behavior** — Default tab on launch (`<select>`).
//! - **About** — sl-daemon URL (with copy + health-check), version text,
//!   "Manage corpus paths" jump to Raw Sessions.
//!
//! The component receives a [`SettingsSignal`](crate::settings::Settings) via
//! context — the same context the root `App` reads to seed the initial tab
//! and theme. Persistence happens in an effect that watches the signal and
//! writes JSON to the platform settings directory.

use dioxus::prelude::*;

use crate::app::SettingsSignal;
use crate::cli_help::version_text;
use crate::daemon_url::{daemon_base_url, daemon_host_display};
use crate::settings::{DefaultTab, Settings};

/// DOM id used by the radio group so the Theme toggle button can focus it.
pub const THEME_RADIO_GROUP_ID: &str = "settings-theme-radios";

/// Status of the daemon `/healthz` probe.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum HealthStatus {
    Unknown,
    Healthy,
    Unreachable,
}

impl HealthStatus {
    /// Stable label used by the UI (`data-testid` etc.).
    pub fn label(self) -> &'static str {
        match self {
            Self::Unknown => "checking",
            Self::Healthy => "healthy",
            Self::Unreachable => "unreachable",
        }
    }
}

/// Settings view — three sub-sections + About.
#[component]
pub fn SettingsTab(on_open_corpus_paths: EventHandler<()>) -> Element {
    let settings = use_context::<SettingsSignal>();
    #[cfg(feature = "desktop")]
    let mut health: Signal<HealthStatus> = use_signal(|| HealthStatus::Unknown);
    #[cfg(not(feature = "desktop"))]
    let health: Signal<HealthStatus> = use_signal(|| HealthStatus::Unknown);

    // Probe the daemon once when the tab mounts. Failures leave the
    // indicator on "unreachable" so the operator knows the daemon is
    // not the cause of any data staleness downstream.
    #[cfg(feature = "desktop")]
    use_effect(move || {
        spawn(async move {
            let url = format!("{}/healthz", daemon_base_url().trim_end_matches('/'));
            let status = match reqwest::Client::new()
                .get(&url)
                .timeout(std::time::Duration::from_secs(2))
                .send()
                .await
            {
                Ok(resp) if resp.status().is_success() => HealthStatus::Healthy,
                _ => HealthStatus::Unreachable,
            };
            health.set(status);
        });
    });

    let copy_label = if cfg!(feature = "desktop") { "Copy" } else { "Copy URL" };

    let health_label = match health() {
        HealthStatus::Healthy => "healthy",
        HealthStatus::Unreachable => "unreachable",
        HealthStatus::Unknown => "checking…",
    };

    let on_copy = move |_| {
        let url = daemon_base_url().to_owned();
        spawn(async move {
            let script = format!(
                r#"
                (async () => {{
                  const value = {value:?};
                  try {{
                    if (navigator?.clipboard?.writeText) {{
                      await navigator.clipboard.writeText(value);
                    }} else {{
                      const ta = document.createElement('textarea');
                      ta.value = value;
                      ta.style.position = 'fixed';
                      ta.style.opacity = '0';
                      document.body.appendChild(ta);
                      ta.select();
                      document.execCommand('copy');
                      ta.remove();
                    }}
                  }} catch (err) {{
                    console.warn('copy failed', err);
                  }}
                }})();
                "#,
                value = url
            );
            let _ = document::eval(&script);
        });
    };

    let settings_signal: Signal<Settings> = settings.0;
    let current_theme = settings_signal.read().theme;
    let current_default_tab = settings_signal.read().default_tab;
    let mut settings_signal = settings_signal;

    rsx! {
        style { r#"
            .settings-view {{
                display: flex;
                flex-direction: column;
                height: 100%;
                overflow-y: auto;
                padding: var(--sl-space-xl) var(--sl-space-2xl);
                box-sizing: border-box;
                gap: var(--sl-space-xl);
                max-width: 760px;
            }}
            .settings-section {{
                display: flex;
                flex-direction: column;
                gap: var(--sl-space-md);
                padding-bottom: var(--sl-space-lg);
                border-bottom: 1px solid var(--sl-border);
            }}
            .settings-section:last-of-type {{
                border-bottom: none;
                padding-bottom: 0;
            }}
            .settings-section h2 {{
                margin: 0;
                font-family: var(--font-ui);
                font-size: 13px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                color: var(--sl-accent);
            }}
            .settings-section p {{
                margin: 0;
                font-size: 13px;
                line-height: 1.5;
                color: var(--sl-text-muted);
                max-width: var(--sl-measure-max);
            }}
            .settings-field {{
                display: flex;
                flex-direction: column;
                gap: var(--sl-space-xs);
            }}
            .settings-field label {{
                font-family: var(--font-ui);
                font-size: 12px;
                font-weight: 600;
                color: var(--sl-text);
            }}
            .settings-radios {{
                display: flex;
                gap: var(--sl-space-md);
                flex-wrap: wrap;
            }}
            .settings-radio {{
                display: flex;
                align-items: center;
                gap: var(--sl-space-xs);
                padding: 6px 12px;
                border: 1px solid var(--sl-border);
                border-radius: var(--sl-radius-md);
                background: var(--sl-surface-muted);
                cursor: pointer;
                font-size: 13px;
                color: var(--sl-text);
            }}
            .settings-radio:hover {{
                border-color: var(--sl-accent);
            }}
            .settings-radio input {{
                margin: 0;
                accent-color: var(--sl-accent);
            }}
            .settings-radio input:focus-visible {{
                outline: 2px solid var(--sl-accent);
                outline-offset: 2px;
            }}
            .settings-select {{
                padding: 6px 10px;
                font-size: 13px;
                border: 1px solid var(--sl-border);
                border-radius: var(--sl-radius-md);
                background: var(--sl-surface-muted);
                color: var(--sl-text);
                min-width: 220px;
                max-width: 320px;
            }}
            .settings-select:focus-visible {{
                outline: 2px solid var(--sl-accent);
                outline-offset: 2px;
                border-color: var(--sl-accent);
            }}
            .settings-row {{
                display: flex;
                align-items: center;
                gap: var(--sl-space-md);
                flex-wrap: wrap;
            }}
            .settings-url {{
                font-family: var(--font-mono);
                font-size: 12px;
                color: var(--sl-text);
                background: var(--sl-surface-muted);
                border: 1px solid var(--sl-border);
                border-radius: var(--sl-radius-md);
                padding: 6px 10px;
                word-break: break-all;
                flex: 1 1 240px;
                min-width: 0;
            }}
            .settings-btn {{
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
                border-radius: var(--sl-radius-md);
                border: 1px solid var(--sl-border);
                background: var(--sl-surface-muted);
                color: var(--sl-text);
                cursor: pointer;
            }}
            .settings-btn:hover {{
                border-color: var(--sl-accent);
                color: var(--sl-accent);
            }}
            .settings-btn:focus-visible {{
                outline: 2px solid var(--sl-accent);
                outline-offset: 2px;
            }}
            .settings-health {{
                display: inline-flex;
                align-items: center;
                gap: var(--sl-space-xs);
                padding: 4px 10px;
                border-radius: 999px;
                font-size: 11px;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.05em;
            }}
            .settings-health[data-status="healthy"] {{
                background: color-mix(in srgb, var(--sl-accent-secondary) 20%, transparent);
                color: var(--sl-accent-secondary);
            }}
            .settings-health[data-status="unreachable"] {{
                background: color-mix(in srgb, var(--sl-danger) 18%, transparent);
                color: var(--sl-danger);
            }}
            .settings-health[data-status="checking"] {{
                background: color-mix(in srgb, var(--sl-accent-warning) 18%, transparent);
                color: var(--sl-accent-warning);
            }}
            .settings-health-dot {{
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: currentColor;
            }}
            .settings-version {{
                font-family: var(--font-mono);
                font-size: 12px;
                color: var(--sl-text-muted);
                white-space: pre-wrap;
                word-break: break-word;
            }}
            .settings-actions {{
                display: flex;
                gap: var(--sl-space-md);
                flex-wrap: wrap;
            }}
        "# }
        section {
            class: "settings-view",
            "aria-labelledby": "settings-heading",
            "data-testid": "settings-tab",
            h1 {
                id: "settings-heading",
                style: "margin:0;font-family:var(--font-display);font-size:1.25rem;font-weight:600;color:var(--sl-text);",
                "Settings"
            }

            // ----- Appearance -----
            div {
                class: "settings-section",
                role: "group",
                "aria-labelledby": "settings-appearance-heading",
                h2 { id: "settings-appearance-heading", "Appearance" }
                p {
                    "Choose how the viewer renders. \"System\" defers to your OS / browser preference when one is available."
                }
                fieldset {
                    id: "{THEME_RADIO_GROUP_ID}",
                    class: "settings-radios",
                    "data-testid": "settings-theme-radios",
                    "aria-label": "Theme preference",
                    style: "border:none;padding:0;margin:0;",
                    for variant in [Settings::THEME_LIGHT, Settings::THEME_DARK, Settings::THEME_SYSTEM].iter().copied() {
                        {render_theme_radio(variant, current_theme, settings_signal)}
                    }
                }
            }

            // ----- Behavior -----
            div {
                class: "settings-section",
                role: "group",
                "aria-labelledby": "settings-behavior-heading",
                h2 { id: "settings-behavior-heading", "Behavior" }
                div {
                    class: "settings-field",
                    label {
                        r#for: "settings-default-tab",
                        "Default tab on launch"
                    }
                    p {
                        "The viewer lands on this tab each time it opens. The choice is persisted across launches."
                    }
                    select {
                        id: "settings-default-tab",
                        class: "settings-select",
                        "data-testid": "settings-default-tab",
                        value: "{current_default_tab.value_attr()}",
                        onchange: move |e| {
                            if let Some(tab) = parse_default_tab(&e.value()) {
                                settings_signal.with_mut(|s| s.default_tab = tab);
                            }
                        },
                        for variant in DefaultTab::ALL {
                            option {
                                key: "{variant.value_attr()}",
                                value: "{variant.value_attr()}",
                                selected: variant == current_default_tab,
                                "{variant.label()}"
                            }
                        }
                    }
                }
            }

            // ----- About -----
            div {
                class: "settings-section",
                role: "group",
                "aria-labelledby": "settings-about-heading",
                h2 { id: "settings-about-heading", "About" }
                div {
                    class: "settings-field",
                    span {
                        style: "font-family:var(--font-ui);font-size:12px;font-weight:600;color:var(--sl-text);",
                        "sl-daemon URL"
                    }
                    div { class: "settings-row",
                        span {
                            class: "settings-url",
                            "data-testid": "settings-daemon-url",
                            title: "{daemon_base_url()}",
                            "{daemon_base_url()}"
                        }
                        button {
                            class: "settings-btn",
                            r#type: "button",
                            "data-testid": "settings-daemon-copy",
                            "aria-label": "Copy sl-daemon URL to clipboard",
                            onclick: on_copy,
                            "{copy_label}"
                        }
                        span {
                            class: "settings-health",
                            "data-testid": "settings-daemon-health",
                            "data-status": "{health().label()}",
                            role: "status",
                            "aria-live": "polite",
                            span { class: "settings-health-dot", "aria-hidden": "true" }
                            "{health_label}"
                        }
                    }
                    p { "Host: {daemon_host_display()}" }
                }

                div {
                    class: "settings-field",
                    span {
                        style: "font-family:var(--font-ui);font-size:12px;font-weight:600;color:var(--sl-text);",
                        "Version"
                    }
                    pre {
                        class: "settings-version",
                        "data-testid": "settings-version",
                        "{version_text()}"
                    }
                }

                div {
                    class: "settings-field",
                    span {
                        style: "font-family:var(--font-ui);font-size:12px;font-weight:600;color:var(--sl-text);",
                        "Corpus paths"
                    }
                    p { "Choose which session directories the viewer scans." }
                    div { class: "settings-actions",
                        button {
                            class: "settings-btn",
                            r#type: "button",
                            "data-testid": "settings-manage-corpus",
                            onclick: move |_| on_open_corpus_paths.call(()),
                            "Manage corpus paths"
                        }
                    }
                }
            }
        }
    }
}

impl Settings {
    // Sentinel string constants used by `value=` attrs on the theme radios.
    pub(crate) const THEME_LIGHT: &'static str = "light";
    pub(crate) const THEME_DARK: &'static str = "dark";
    pub(crate) const THEME_SYSTEM: &'static str = "system";
}

fn render_theme_radio(
    variant: &'static str,
    current: crate::theme::Theme,
    mut settings: Signal<Settings>,
) -> Element {
    let theme_value = match variant {
        Settings::THEME_LIGHT => crate::theme::Theme::Light,
        Settings::THEME_DARK => crate::theme::Theme::Dark,
        _ => crate::theme::Theme::System,
    };
    let is_checked = current == theme_value;
    let id = format!("settings-theme-{variant}");
    rsx! {
        label {
            key: "{variant}",
            class: "settings-radio",
            r#for: "{id}",
            input {
                id: "{id}",
                r#type: "radio",
                name: "settings-theme",
                value: "{variant}",
                checked: is_checked,
                "data-testid": "settings-theme-{variant}",
                onchange: move |_| {
                    settings.with_mut(|s| s.theme = theme_value);
                    let _ = document::eval(&format!(
                        r#"
                        const desired = {variant:?};
                        const resolved = desired === 'system'
                            ? (window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark')
                            : desired;
                        document.documentElement.dataset.theme = resolved;
                        window.localStorage.setItem('sl-viewer-theme', desired);
                        "#,
                    ));
                },
            }
            span { "{theme_label(theme_value)}" }
        }
    }
}

fn theme_label(theme: crate::theme::Theme) -> &'static str {
    match theme {
        crate::theme::Theme::Light => "Light",
        crate::theme::Theme::Dark => "Dark",
        crate::theme::Theme::System => "System",
    }
}

fn parse_default_tab(value: &str) -> Option<DefaultTab> {
    DefaultTab::ALL.into_iter().find(|t| t.value_attr() == value)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn theme_radio_values_are_stable() {
        assert_eq!(Settings::THEME_LIGHT, "light");
        assert_eq!(Settings::THEME_DARK, "dark");
        assert_eq!(Settings::THEME_SYSTEM, "system");
    }

    #[test]
    fn parse_default_tab_round_trips_value_attrs() {
        for tab in DefaultTab::ALL {
            assert_eq!(parse_default_tab(tab.value_attr()), Some(tab));
        }
        assert_eq!(parse_default_tab("not-a-tab"), None);
    }

    #[test]
    fn health_status_labels_are_stable_strings() {
        assert_eq!(HealthStatus::Unknown.label(), "checking");
        assert_eq!(HealthStatus::Healthy.label(), "healthy");
        assert_eq!(HealthStatus::Unreachable.label(), "unreachable");
    }
}
