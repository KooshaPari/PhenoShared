//! # forge_paste
//!
//! Input pipeline for forge. Handles everything between "user pressed enter" and
//! "we have a string of natural-language instructions to send to the model".
//!
//! Sub-modules (all additive — nothing existing is replaced):
//!
//! * [`paste_event`]    — bracketed paste mode (CSI ?2004h/l), classifier (path/url/code/text/image)
//! * [`image_protocol`] — OSC52 / Kitty graphics / Sixel / iTerm2 inline image (feature-gated)
//! * [`clipboard`]      — read/write platform clipboard via `arboard` (feature-gated)
//! * [`mention`]        — `@path`, `@dir`, `@file:line`, `@agent`, `@git`, `@web` parsing
//! * [`classifier`]     — heuristic classifier (MIME sniff, code-detect, url-detect)
//! * [`collapse`]       — large-paste collapse: replace big pastes with `@[collapsed:N chars]`
//! * [`shell`]          — shell-specific wrap helpers (extends existing `forge_pheno_shell`)
//!
//! See `plans/2026-09-02-helioslite-p0.3-p0.4-plan-spec-adr.md` §5 for design rationale.

#![allow(clippy::result_large_err)]
// Parser crate: we operate on byte indices that are derived from
// `char_indices()`/`chars()`, so the panicking index/slice lints are
// inappropriate at crate scope. Individual benchmark-lines still use
// `.get()` where the index is not provably safe.
#![allow(clippy::indexing_slicing)]
#![allow(clippy::string_slice)]

pub mod classifier;
pub mod collapse;
pub mod mention;
pub mod paste_event;
pub mod shell;

#[cfg(feature = "clipboard")]
pub mod clipboard;
#[cfg(feature = "image")]
pub mod image_protocol;

/// Re-export the most-used types at the crate root for ergonomics.
pub use classifier::{classify, ClassifierResult, ClassifierSignal, PasteKind};
pub use collapse::{collapse_paste, CollapseConfig, CollapseOutcome};
pub use mention::{Mention, MentionKind, MentionSet};
pub use paste_event::{PasteEvent, PasteSource};
pub use shell::{
    has_paste_end, has_paste_start, negotiate_bracketed_paste, strip_bracketed_sentinels,
    BRACKETED_PASTE_DISABLE, BRACKETED_PASTE_ENABLE, PASTE_END_SENTINEL, PASTE_START_SENTINEL,
};

/// Crate version — matches the workspace `forge-paste` package.
pub const VERSION: &str = env!("CARGO_PKG_VERSION");
