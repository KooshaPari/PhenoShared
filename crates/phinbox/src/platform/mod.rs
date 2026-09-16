//! Platform detection and per-platform popup renderer modules.

pub mod detect;
pub mod tty;

#[cfg(target_os = "macos")]
pub mod macos;

#[cfg(target_os = "windows")]
pub mod windows;

#[cfg(target_os = "linux")]
pub mod linux;

pub use detect::{detect, detect_renderer, Platform, RendererKind};

use crate::error::ElicitError;
use crate::options::ElicitOptions;
use crate::spec::{ElicitResponse, PromptSpec};

/// Render a popup on the detected platform, dispatching to the right
/// platform-specific module.
///
/// Public for use by [`crate::render::dispatch`].
pub fn render_on_platform(
    spec: &PromptSpec,
    opts: &ElicitOptions,
) -> Result<ElicitResponse, ElicitError> {
    let kind = detect_renderer(opts.renderer);

    match kind {
        RendererKind::None => {
            if matches!(opts.renderer, crate::options::RendererPreference::ForceGui) {
                Err(ElicitError::NoRenderer)
            } else {
                tty::render(spec, opts)
            }
        }
        RendererKind::Tty => tty::render(spec, opts),
        RendererKind::Gui => {
            #[cfg(target_os = "macos")]
            {
                macos::render(spec, opts)
            }
            #[cfg(target_os = "windows")]
            {
                windows::render(spec, opts)
            }
            #[cfg(target_os = "linux")]
            {
                linux::render(spec, opts)
            }
            #[cfg(not(any(target_os = "macos", target_os = "windows", target_os = "linux")))]
            {
                let _ = (spec, opts);
                Err(ElicitError::NoRenderer)
            }
        }
    }
}