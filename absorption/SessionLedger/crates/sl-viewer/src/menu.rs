//! macOS / desktop menu bar wiring for the `sl-viewer` window.
//!
//! The menu is registered on the [`dioxus::desktop::Config`] via
//! [`Config::with_menu`] (see `main.rs`). Menu events arrive on the
//! main thread through the dioxus runtime — `App` installs a single
//! muda event handler that dispatches by [`MenuId`] to the same DOM
//! controls the keyboard shortcuts already trigger. Reusing the
//! existing onclick handlers keeps a single source of truth for state
//! transitions (palette, help, theme) and avoids duplicating effects.
//!
//! The `web` build never links muda, so this module is compiled only
//! when the `desktop` feature is on.

#![cfg(feature = "desktop")]

use dioxus::desktop::muda::{
    accelerator::{Accelerator, Code, Modifiers},
    Menu, MenuItem, PredefinedMenuItem, Submenu,
};

// ---------------------------------------------------------------------------
// Menu item identifiers
//
// Kept as `&'static str` so the event handler in `app.rs` can match on
// `event.id().0.as_str()` without depending on muda from the UI module.
// ---------------------------------------------------------------------------

pub const ID_APP_ABOUT: &str = "sl-viewer.app.about";
pub const ID_APP_SETTINGS: &str = "sl-viewer.app.settings";

pub const ID_FILE_RELOAD_DISCOVERY: &str = "sl-viewer.file.reload-discovery";
pub const ID_FILE_SETTINGS: &str = "sl-viewer.file.settings";

pub const ID_EDIT_FIND: &str = "sl-viewer.edit.find";

pub const ID_VIEW_RELOAD: &str = "sl-viewer.view.reload";
pub const ID_VIEW_TOGGLE_THEME: &str = "sl-viewer.view.toggle-theme";
pub const ID_VIEW_COMMAND_PALETTE: &str = "sl-viewer.view.command-palette";

pub const ID_HELP_TOGGLE: &str = "sl-viewer.help.toggle";

// ---------------------------------------------------------------------------
// Accelerators
//
// Use `SUPER` (Cmd) on macOS so shortcuts match platform expectations.
// muda's `Accelerator` only supports the standard modifier+key combo, so
// `?` is bound as Shift+Slash. The keyboard hotkey bridge in `app.rs`
// already accepts `?` / Shift+Slash, so the menu shortcut round-trips
// to the same DOM button click.
// ---------------------------------------------------------------------------

#[cfg(target_os = "macos")]
const META: Modifiers = Modifiers::SUPER;
#[cfg(not(target_os = "macos"))]
const META: Modifiers = Modifiers::CONTROL;

fn acc(mods: Modifiers, key: Code) -> Accelerator {
    Accelerator::new(Some(mods), key)
}

/// Build the menu bar for the desktop window.
///
/// `dioxus::desktop::Config::with_menu` swaps this in for the default
/// (which only ships Edit + Window). The structure follows the macOS
/// HIG: the first submenu is treated as the application menu and is
/// auto-renamed to the bundle name by AppKit, so we tag it with
/// `SessionLedger` even though AppKit rewrites it.
pub fn build_menu() -> Menu {
    let menu = Menu::new();

    // ---- Application menu (macOS only renames it to the bundle name) -----
    let app_menu = Submenu::new("SessionLedger", true);
    app_menu
        .append_items(&[
            &MenuItem::with_id(ID_APP_ABOUT, "About SessionLedger", true, None::<Accelerator>),
            &PredefinedMenuItem::separator(),
            &MenuItem::with_id(
                ID_APP_SETTINGS,
                "Settings\u{2026}",
                true,
                Some(acc(META, Code::Comma)),
            ),
            &PredefinedMenuItem::separator(),
            // muda wires ⌘Q on macOS / Ctrl+Q on Win/Linux automatically.
            &PredefinedMenuItem::quit(Some("Quit SessionLedger")),
        ])
        .expect("append app menu items");

    // ---- File ----------------------------------------------------------------
    let file_menu = Submenu::new("File", true);
    file_menu
        .append_items(&[
            &MenuItem::with_id(
                ID_FILE_RELOAD_DISCOVERY,
                "Reload discovery",
                true,
                None::<Accelerator>,
            ),
            &MenuItem::with_id(
                ID_FILE_SETTINGS,
                "Settings\u{2026}",
                true,
                Some(acc(META, Code::Comma)),
            ),
            &PredefinedMenuItem::separator(),
            // The Predefined quit item already lives under the app menu on
            // macOS; duplicating it under File would be redundant.
            #[cfg(not(target_os = "macos"))]
            &PredefinedMenuItem::quit(Some("Quit")),
        ])
        .expect("append file menu items");

    // ---- Edit ----------------------------------------------------------------
    // Predefined cut/copy/paste/select-all are pre-bound to the OS shortcuts
    // (⌘X/⌘C/⌘V/⌘A on macOS). We layer a "Find" item on top so the existing
    // keyboard hotkey bridge in `app.rs` gets a click on the search tab
    // button (the Search tab is mounted but there is no dedicated focusable
    // search input today; ⌘F just routes to that tab).
    let edit_menu = Submenu::new("Edit", true);
    edit_menu
        .append_items(&[
            &PredefinedMenuItem::undo(Some("Undo")),
            &PredefinedMenuItem::redo(Some("Redo")),
            &PredefinedMenuItem::separator(),
            &PredefinedMenuItem::cut(Some("Cut")),
            &PredefinedMenuItem::copy(Some("Copy")),
            &PredefinedMenuItem::paste(Some("Paste")),
            &PredefinedMenuItem::select_all(Some("Select All")),
            &PredefinedMenuItem::separator(),
            &MenuItem::with_id(ID_EDIT_FIND, "Find\u{2026}", true, Some(acc(META, Code::KeyF))),
        ])
        .expect("append edit menu items");

    // ---- View ----------------------------------------------------------------
    let view_menu = Submenu::new("View", true);
    view_menu
        .append_items(&[
            &MenuItem::with_id(ID_VIEW_RELOAD, "Reload", true, Some(acc(META, Code::KeyR))),
            &MenuItem::with_id(ID_VIEW_TOGGLE_THEME, "Toggle Theme", true, None::<Accelerator>),
            &PredefinedMenuItem::separator(),
            &MenuItem::with_id(
                ID_VIEW_COMMAND_PALETTE,
                "Open Command Palette",
                true,
                Some(acc(META, Code::KeyK)),
            ),
        ])
        .expect("append view menu items");

    // ---- Window --------------------------------------------------------------
    // Minimize / Zoom / Fullscreen are platform-predefined so the OS owns
    // their behavior (correct focus handling, AppKit integration on macOS).
    let window_menu = Submenu::new("Window", true);
    window_menu
        .append_items(&[
            &PredefinedMenuItem::minimize(Some("Minimize")),
            &PredefinedMenuItem::maximize(Some("Zoom")),
            &PredefinedMenuItem::fullscreen(Some("Enter Full Screen")),
        ])
        .expect("append window menu items");

    // ---- Help ----------------------------------------------------------------
    let help_menu = Submenu::new("Help", true);
    help_menu
        .append_items(&[&MenuItem::with_id(
            ID_HELP_TOGGLE,
            "Toggle Help overlay",
            true,
            Some(acc(Modifiers::SHIFT, Code::Slash)),
        )])
        .expect("append help menu items");

    // Note: `set_as_help_menu_for_nsapp()` / `set_as_windows_menu_for_nsapp()`
    // intentionally NOT called here — muda's contract is that those run after
    // `Menu::init_for_nsapp()` (which `dioxus-desktop` calls once it has
    // attached the menu to the NSApp). At build-time the submenu's `ns_menu`
    // field is still `None`; calling those now would `unwrap()` and panic.
    // macOS still finds the Help menu by title ("Help") per AppKit convention,
    // and the Window menu is decorative for a single-window viewer.

    menu.append_items(&[&app_menu, &file_menu, &edit_menu, &view_menu, &window_menu, &help_menu])
        .expect("append top-level menus to menu bar");

    menu
}
