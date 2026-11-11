//! In-viewer keyboard help overlay (`?` / Help button, closed with Escape).

use dioxus::prelude::*;

/// One row in the keyboard shortcut reference.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct HelpShortcut {
    pub keys: &'static str,
    pub scope: &'static str,
    pub action: &'static str,
}

/// Shortcut table mirrored by [`docs/viewer-hotkeys.md`](../../../docs/viewer-hotkeys.md).
pub const SHORTCUTS: &[HelpShortcut] = &[
    HelpShortcut {
        keys: "?",
        scope: "Whole viewer",
        action: "Open or close this keyboard help overlay.",
    },
    HelpShortcut {
        keys: "Cmd+K / Ctrl+K",
        scope: "Whole viewer",
        action: "Open or close the command palette.",
    },
    HelpShortcut {
        keys: "Arrow keys + Enter",
        scope: "Command palette",
        action: "Move through commands and run focus search, open help, switch tabs, clear search, or toggle theme.",
    },
    HelpShortcut {
        keys: "Tab / Shift+Tab",
        scope: "Whole viewer",
        action: "Move through focus order. The active view tab is the only tab stop in the tablist before panel controls.",
    },
    HelpShortcut {
        keys: "ArrowRight / ArrowLeft",
        scope: "Focused view tab",
        action: "Select and focus the next or previous view tab, wrapping at the ends.",
    },
    HelpShortcut {
        keys: "Home / End",
        scope: "Focused view tab",
        action: "Jump to Bundles or Replay.",
    },
    HelpShortcut {
        keys: "Enter / Space",
        scope: "Focused view tab",
        action: "Activate the focused view tab.",
    },
    HelpShortcut {
        keys: "Escape",
        scope: "This help overlay",
        action: "Close the overlay and return focus to the Help control.",
    },
    HelpShortcut {
        keys: "Escape",
        scope: "Command palette",
        action: "Close the palette.",
    },
    HelpShortcut {
        keys: "Escape",
        scope: "Search view",
        action: "Clear search filters, results, and errors without moving focus.",
    },
    HelpShortcut {
        keys: "Escape",
        scope: "Replay view",
        action: "Clear replay output and return the replay panel to idle.",
    },
    HelpShortcut {
        keys: "Escape",
        scope: "Bundle comparison panel",
        action: "Close the comparison panel.",
    },
];

/// True when focus is in a field where `?` should type a character, not open help.
pub fn typing_focus_active() -> bool {
    #[cfg(feature = "web")]
    {
        use wasm_bindgen::JsCast;
        let Some(window) = web_sys::window() else {
            return false;
        };
        let Some(document) = window.document() else {
            return false;
        };
        let Some(element) = document.active_element() else {
            return false;
        };
        let tag = element.tag_name();
        if matches!(tag.as_str(), "INPUT" | "TEXTAREA" | "SELECT") {
            return true;
        }
        if let Ok(html) = element.dyn_into::<web_sys::HtmlElement>() {
            return html.is_content_editable();
        }
        false
    }
    #[cfg(not(feature = "web"))]
    {
        false
    }
}

/// Modal keyboard shortcut reference for the viewer.
#[component]
pub fn HelpOverlay(open: bool, on_close: EventHandler<()>) -> Element {
    if !open {
        return rsx! {};
    }

    rsx! {
        div {
            class: "help-overlay-backdrop",
            role: "presentation",
            onclick: move |_| on_close.call(()),
        }
        div {
            class: "help-overlay",
            id: "keyboard-help-dialog",
            role: "dialog",
            "aria-modal": "true",
            "aria-labelledby": "help-overlay-title",
            "data-testid": "keyboard-help-dialog",
            onkeydown: move |evt: Event<KeyboardData>| {
                if evt.key() == Key::Escape {
                    evt.prevent_default();
                    evt.stop_propagation();
                    on_close.call(());
                }
            },
            div { class: "help-overlay-header",
                h2 {
                    id: "help-overlay-title",
                    "Keyboard shortcuts"
                }
                button {
                    class: "help-overlay-close",
                    r#type: "button",
                    "aria-label": "Close keyboard help",
                    onclick: move |_| on_close.call(()),
                    "Close"
                }
            }
            p { class: "help-overlay-lede",
                "Press "
                kbd { "?" }
                " anywhere outside a text field, or use the Help button, to toggle this panel."
            }
            table { class: "help-overlay-table",
                thead {
                    tr {
                        th { scope: "col", "Shortcut" }
                        th { scope: "col", "Scope" }
                        th { scope: "col", "Action" }
                    }
                }
                tbody {
                    for row in SHORTCUTS {
                        tr { key: "{row.keys}-{row.scope}",
                            td { class: "help-overlay-keys",
                                kbd { "{row.keys}" }
                            }
                            td { "{row.scope}" }
                            td { "{row.action}" }
                        }
                    }
                }
            }
            p { class: "help-overlay-footer caption",
                "Full reference: docs/HELP.md and docs/viewer-hotkeys.md"
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    #[test]
    fn shortcuts_include_help_toggle() {
        assert!(SHORTCUTS.iter().any(|s| s.keys == "?"));
        assert!(SHORTCUTS.iter().any(|s| s.scope == "This help overlay"));
    }

    /// Golden snapshot for keyboard-help copy — auditors can diff this file.
    #[test]
    fn shortcuts_match_golden_snapshot() {
        let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
        let golden = manifest_dir
            .join("../../tests/fixtures/a11y/help_shortcuts.golden.tsv")
            .canonicalize()
            .expect("help shortcuts golden path");
        let expected = std::fs::read_to_string(&golden).expect("read help shortcuts golden");
        let normalize = |s: &str| s.replace("\r\n", "\n");
        let mut actual = String::new();
        for row in SHORTCUTS {
            actual.push_str(&format!("{}\t{}\t{}\n", row.keys, row.scope, row.action));
        }
        assert_eq!(
            normalize(actual.trim_end()),
            normalize(expected.trim_end()),
            "help overlay copy drifted from {}",
            golden.display()
        );
    }

    #[test]
    fn shortcut_actions_use_plain_language() {
        for row in SHORTCUTS {
            assert!(
                !row.action.contains("ERR_") && !row.action.contains("error code"),
                "shortcut {:?} should stay human-readable",
                row.keys
            );
            assert!(
                row.action.chars().any(|c| c.is_ascii_alphabetic()),
                "shortcut {:?} needs descriptive copy",
                row.keys
            );
        }
    }
}
