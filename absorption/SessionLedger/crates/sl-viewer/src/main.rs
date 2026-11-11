//! `sl-viewer` platform entry points.
//!
//! Desktop  : `cargo run -p sl-viewer`             (default feature)
//! Web WASM : `dx serve --platform web -p sl-viewer`  (requires `web` feature)

#[cfg(feature = "desktop")]
use sl_viewer::cli_help;
#[cfg(feature = "desktop")]
use sl_viewer::menu;
use sl_viewer::App;

/// Human-readable window title — surfaced via the OS window chrome on
/// desktop and the browser tab label on web (via the `[web.title]` field
/// in `Dioxus.toml`).
const VIEWER_TITLE: &str = "Session Ledger Viewer";

#[cfg(any(feature = "desktop", not(feature = "web")))]
fn main() {
    use dioxus::desktop::{Config, WindowBuilder};

    if let Some(argument) = std::env::args().nth(1) {
        match argument.as_str() {
            "--version" | "-V" => {
                println!("{}", cli_help::version_text());
                return;
            }
            "--help" | "-h" => {
                print!("{}", cli_help::help_text());
                return;
            }
            _ => {}
        }
    }

    dioxus::LaunchBuilder::desktop()
        .with_cfg(
            Config::new()
                .with_window(WindowBuilder::new().with_title(VIEWER_TITLE))
                // Custom menu bar (File / Edit / View / Window / Help) — see
                // `sl_viewer::menu::build_menu` for the structure. The default
                // dioxus menu only ships Edit + Window on desktop, so we
                // override it to surface the viewer-specific shortcuts
                // (Reload, Command Palette, Toggle Help, etc.) in the
                // platform menu bar.
                .with_menu(menu::build_menu()),
        )
        .launch(App);
}

#[cfg(all(feature = "web", not(feature = "desktop")))]
fn main() {
    // The web launcher reads the title from `Dioxus.toml` (see
    // `app_title()` in `dioxus_cli_config`); if we ever need to set it
    // programmatically we can switch to a wrapper component that emits a
    // `<Title>` element from `dioxus::document`.
    let _ = VIEWER_TITLE;
    dioxus::LaunchBuilder::web().with_cfg(dioxus::web::Config::default()).launch(App);
}
