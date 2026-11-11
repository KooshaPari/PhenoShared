//! Lightweight Cmd+K / Ctrl+K command palette for power-user shortcuts.

use dioxus::prelude::*;

/// Actions the palette can dispatch into the viewer shell.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PaletteAction {
    FocusSearch,
    ToggleTheme,
    OpenHelp,
    OpenSettings,
    NextTab,
    PrevTab,
    ClearSearch,
}

/// One selectable command in the palette.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PaletteCommand {
    pub id: &'static str,
    pub label: &'static str,
    pub hint: &'static str,
    pub action: PaletteAction,
}

/// Power-user command set for Wave-29 C09 (L81.14), extended with
/// `OpenSettings` (FR-VIEWER-SETTINGS-1).
pub const COMMANDS: &[PaletteCommand] = &[
    PaletteCommand {
        id: "focus-search",
        label: "Focus search",
        hint: "Switch to Search and focus the first filter",
        action: PaletteAction::FocusSearch,
    },
    PaletteCommand {
        id: "open-settings",
        label: "Open settings",
        hint: "Switch to the Settings tab (theme, default tab, daemon)",
        action: PaletteAction::OpenSettings,
    },
    PaletteCommand {
        id: "open-help",
        label: "Open keyboard help",
        hint: "Show the shortcut reference overlay",
        action: PaletteAction::OpenHelp,
    },
    PaletteCommand {
        id: "next-tab",
        label: "Next view tab",
        hint: "Select and focus the next tab, wrapping at Settings",
        action: PaletteAction::NextTab,
    },
    PaletteCommand {
        id: "prev-tab",
        label: "Previous view tab",
        hint: "Select and focus the previous tab, wrapping at Bundles",
        action: PaletteAction::PrevTab,
    },
    PaletteCommand {
        id: "clear-search",
        label: "Clear search",
        hint: "Switch to Search and reset filters without moving focus",
        action: PaletteAction::ClearSearch,
    },
    PaletteCommand {
        id: "toggle-theme",
        label: "Toggle theme",
        hint: "Switch between light and dark theme",
        action: PaletteAction::ToggleTheme,
    },
];

/// Modal command palette (`role="dialog"` + `listbox` / `option`).
#[component]
pub fn CommandPalette(
    open: bool,
    on_close: EventHandler<()>,
    on_run: EventHandler<PaletteAction>,
) -> Element {
    let mut active_idx: Signal<usize> = use_signal(|| 0usize);

    if !open {
        return rsx! {};
    }

    let run_at = move |idx: usize| {
        if let Some(cmd) = COMMANDS.get(idx) {
            on_run.call(cmd.action);
        }
    };

    rsx! {
        div {
            class: "command-palette-backdrop",
            role: "presentation",
            onclick: move |_| on_close.call(()),
        }
        div {
            class: "command-palette",
            id: "command-palette-dialog",
            role: "dialog",
            "aria-modal": "true",
            "aria-labelledby": "command-palette-title",
            "data-testid": "command-palette-dialog",
            onkeydown: move |evt: Event<KeyboardData>| {
                match evt.key() {
                    Key::Escape => {
                        evt.prevent_default();
                        evt.stop_propagation();
                        on_close.call(());
                    }
                    Key::ArrowDown => {
                        evt.prevent_default();
                        let next = (active_idx() + 1) % COMMANDS.len();
                        active_idx.set(next);
                    }
                    Key::ArrowUp => {
                        evt.prevent_default();
                        let next = if active_idx() == 0 {
                            COMMANDS.len() - 1
                        } else {
                            active_idx() - 1
                        };
                        active_idx.set(next);
                    }
                    Key::Enter => {
                        evt.prevent_default();
                        run_at(active_idx());
                    }
                    _ => {}
                }
            },
            div { class: "command-palette-header",
                h2 {
                    id: "command-palette-title",
                    "Command palette"
                }
                button {
                    class: "command-palette-close",
                    r#type: "button",
                    "aria-label": "Close command palette",
                    onclick: move |_| on_close.call(()),
                    "Close"
                }
            }
            p { class: "command-palette-lede",
                "Press "
                kbd { "Ctrl+K" }
                " / "
                kbd { "Cmd+K" }
                " to toggle. Arrow keys move; Enter runs the selected command."
            }
            ul {
                class: "command-palette-list",
                role: "listbox",
                "aria-label": "Viewer commands",
                "aria-activedescendant": "{COMMANDS[active_idx().min(COMMANDS.len() - 1)].id}",
                for (i, cmd) in COMMANDS.iter().enumerate() {
                    li {
                        key: "{cmd.id}",
                        id: "{cmd.id}",
                        class: if active_idx() == i {
                            "command-palette-option is-active"
                        } else {
                            "command-palette-option"
                        },
                        role: "option",
                        "aria-label": "{cmd.label}",
                        "aria-selected": if active_idx() == i { "true" } else { "false" },
                        tabindex: if active_idx() == i { "0" } else { "-1" },
                        onclick: move |_| {
                            active_idx.set(i);
                            run_at(i);
                        },
                        span { class: "command-palette-option-label", "{cmd.label}" }
                        span { class: "command-palette-option-hint", "{cmd.hint}" }
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn commands_cover_viewer_shell_actions() {
        assert!(COMMANDS.iter().any(|c| c.action == PaletteAction::FocusSearch));
        assert!(COMMANDS.iter().any(|c| c.action == PaletteAction::ToggleTheme));
        assert!(COMMANDS.iter().any(|c| c.action == PaletteAction::OpenHelp));
        assert!(COMMANDS.iter().any(|c| c.action == PaletteAction::OpenSettings));
        assert!(COMMANDS.iter().any(|c| c.action == PaletteAction::NextTab));
        assert!(COMMANDS.iter().any(|c| c.action == PaletteAction::PrevTab));
        assert!(COMMANDS.iter().any(|c| c.action == PaletteAction::ClearSearch));
        assert_eq!(COMMANDS.len(), 7);
    }

    #[test]
    fn command_ids_are_stable() {
        assert_eq!(COMMANDS[0].id, "focus-search");
        assert_eq!(COMMANDS[1].id, "open-settings");
        assert_eq!(COMMANDS[2].id, "open-help");
        assert_eq!(COMMANDS[3].id, "next-tab");
        assert_eq!(COMMANDS[4].id, "prev-tab");
        assert_eq!(COMMANDS[5].id, "clear-search");
        assert_eq!(COMMANDS[6].id, "toggle-theme");
    }
}
