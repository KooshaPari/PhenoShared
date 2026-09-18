//! Platform detection and per-platform popup renderer modules.

pub mod detect;
pub mod tty;

#[cfg(target_os = "macos")]
pub mod macos;

// The Windows renderer's script builder and output parser are pure and
// platform-independent, so compile them under `test` on every host to keep
// them covered from a macOS/Linux checkout.
#[cfg(any(target_os = "windows", test))]
pub mod windows;

#[cfg(target_os = "linux")]
pub mod linux;

pub use detect::{detect, detect_renderer, Platform, RendererKind};

use crate::error::ElicitError;
use crate::options::ElicitOptions;
use crate::spec::{ElicitResponse, PromptSpec};
use std::time::Duration;

/// Resolve the wall-clock deadline for a popup, if any.
///
/// `PromptSpec::timeout_secs` documents `0` as "no timeout" and
/// `phinbox ask --help` says the same, so `0` must mean *wait indefinitely*
/// rather than "expire on the first poll". Every renderer previously did
/// `start.elapsed() >= timeout`, which made `0` fire immediately.
/// Returns `None` when there is no deadline.
#[must_use]
pub(crate) fn deadline_for(spec: &PromptSpec, opts: &ElicitOptions) -> Option<Duration> {
    let t = opts
        .timeout
        .unwrap_or_else(|| Duration::from_secs(u64::from(spec.timeout_secs)));
    if t.is_zero() {
        None
    } else {
        Some(t)
    }
}

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
#[cfg(test)]
mod tests {
    use super::*;
    use crate::spec::{FieldSpec, Urgency};

    fn spec_with_timeout(secs: u32) -> PromptSpec {
        PromptSpec {
            details: None,
            title: "t".into(),
            question: "q".into(),
            field: FieldSpec::Boolean {
                label: "?".into(),
                default: None,
            },
            notes: None,
            buttons: None,
            urgency: Urgency::Info,
            timeout_secs: secs,
            request_id: None,
        }
    }

    #[test]
    fn zero_timeout_means_no_deadline() {
        // Documented as "set to 0 for no timeout"; used to fire instantly.
        let spec = spec_with_timeout(0);
        assert!(
            deadline_for(&spec, &ElicitOptions::default()).is_none(),
            "timeout_secs 0 must mean no deadline, not an instant one"
        );
    }

    #[test]
    fn spec_timeout_is_used_when_no_override() {
        let spec = spec_with_timeout(600);
        assert_eq!(
            deadline_for(&spec, &ElicitOptions::default()),
            Some(Duration::from_secs(600))
        );
    }

    #[test]
    fn explicit_override_wins_and_zero_override_disables() {
        let spec = spec_with_timeout(600);
        let override_some = ElicitOptions {
            timeout: Some(Duration::from_secs(5)),
            ..Default::default()
        };
        assert_eq!(
            deadline_for(&spec, &override_some),
            Some(Duration::from_secs(5))
        );

        let override_zero = ElicitOptions {
            timeout: Some(Duration::ZERO),
            ..Default::default()
        };
        assert!(deadline_for(&spec, &override_zero).is_none());
    }
}
