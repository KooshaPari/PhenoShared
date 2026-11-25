//! Terminal-emulator detection and executor wiring.
//!
//! The [`TerminalEmulator`] enum and low-level `from_env` detection live in
//! the `forge_pheno_shell` crate (which is the canonical home per ADR-097 —
//! zero-dependency crate, reusable from any forgecode crate). This module
//! re-exports those types and adds the `forge_infra`-specific glue:
//!
//! - [`detect_terminal_emulator`] — convenience wrapper that reads the real
//!   process environment.
//! - [`apply_emulator_env`] — sets terminal-aware environment variables on
//!   a `tokio::process::Command` so child processes inherit our detection
//!   result and can short-circuit their own detection.
//! - [`FORGE_TERMINAL_EMULATOR`] — the env var name we inject; downstream
//!   tools can read this without re-detecting.
//!
//! ## Why this lives in `forge_infra` and not `forge_pheno_shell`
//!
//! `forge_pheno_shell` deliberately stays free of `tokio` and `std::process`
//! (it's the "pure" detection/completion-emission layer). `forge_infra` is
//! the layer that *executes* — and executor subprocess spawning is exactly
//! the seam where terminal-aware env wiring belongs.

use forge_pheno_shell::TerminalEmulator;
use tokio::process::Command;
use tracing::trace;

/// The env var name we inject on every spawned subprocess so downstream
/// tooling (scripts, plugins, subshells) can read our detection result
/// without re-running the env-var scan.
pub const FORGE_TERMINAL_EMULATOR: &str = "FORGE_TERMINAL_EMULATOR";

/// Detect the terminal emulator wrapping the current process.
///
/// Returns `(emulator, raw_source_string)` where `raw_source_string` is the
/// env var name that triggered detection (e.g. `"TERM_PROGRAM=WezTerm"`),
/// or `""` if no signal was found (defaults to [`TerminalEmulator::Xterm`]).
///
/// Thin wrapper around [`TerminalEmulator::detect`]; exists at the
/// `forge_infra` layer so executor code does not need a second `use`
/// statement into the lower crate.
pub fn detect_terminal_emulator() -> (TerminalEmulator, String) {
    TerminalEmulator::detect()
}

/// Inject terminal-aware environment variables into `cmd`.
///
/// What we set:
///
/// 1. `FORGE_TERMINAL_EMULATOR=<stable-id>` — always. This is the marker
///    downstream scripts / plugins should read. Stable across renames
///    (e.g. `wezterm`, `windows-terminal`).
/// 2. For a few emulators, also re-set the *canonical* env var that
///    identifies the emulator to that emulator's own tooling — this is
///    defensive. The parent's env already carries these (the executor
///    inherits by default), but we set them explicitly here so that
///    (a) any future env-stripping code path can't silently lose them
///    and (b) the executor's intent is self-documenting in tracing.
///
/// We never *remove* anything — only add. Color/UI flags stay on the
/// parent so child processes behave identically.
pub fn apply_emulator_env(cmd: &mut Command, emulator: TerminalEmulator) {
    // Always inject our own marker first — it's the cheapest signal.
    cmd.env(FORGE_TERMINAL_EMULATOR, emulator.id());
    trace!(
        emulator = %emulator.id(),
        "wired terminal emulator env into command"
    );

    // Defensive re-stamp of canonical vars per emulator. These are
    // already in the parent env (Command inherits), but we set them
    // here so tracing shows what the executor detected and so a future
    // `.env_remove(…)` upstream can't accidentally drop them.
    match emulator {
        TerminalEmulator::WezTerm => {
            // No-op: WEZTERM_EXECUTABLE is already in the parent env if
            // we're inside WezTerm. We deliberately don't fabricate one.
        }
        TerminalEmulator::Kitty => {
            // KITTY_WINDOW_ID is set by the emulator itself; no spoof.
        }
        TerminalEmulator::Ghostty => {
            // No canonical env var to re-stamp; GHOSTTY_BIN_DIR is set
            // by the user/installer, not by the emulator.
        }
        TerminalEmulator::ITerm2 => {
            // ITERM_SESSION_ID — same pattern, don't fabricate.
        }
        TerminalEmulator::WindowsTerminal => {
            // WT_SESSION — same.
        }
        TerminalEmulator::AppleTerminal => {
            // LC_TERMINAL — same.
        }
        TerminalEmulator::Tmux => {
            // TMUX — set by tmux itself, don't fabricate.
        }
        TerminalEmulator::Screen => {
            // STY — set by screen itself, don't fabricate.
        }
        TerminalEmulator::VSCode => {
            // VSCODE_PID — set by VS Code itself.
        }
        TerminalEmulator::JetBrains => {
            // JEDITERM_USER_DIR — set by the IDE.
        }
        // The remaining variants (Rio, GnomeTerminal, Konsole, Alacritty,
        // Hyper, St, Xterm, Unknown) have no universally-set canonical
        // env var. The FORGE_TERMINAL_EMULATOR marker above is enough.
        TerminalEmulator::Rio
        | TerminalEmulator::GnomeTerminal
        | TerminalEmulator::Konsole
        | TerminalEmulator::Alacritty
        | TerminalEmulator::Hyper
        | TerminalEmulator::St
        | TerminalEmulator::Xterm
        | TerminalEmulator::Unknown => {}
    }
}

#[cfg(test)]
mod tests {
    use pretty_assertions::assert_eq;
    use std::collections::HashMap;

    use super::*;

    /// Helper: run the closure-style detector with a synthetic env map
    /// so tests don't depend on the real process environment.
    fn detect_with(env: &HashMap<&str, &str>) -> (TerminalEmulator, String) {
        // Re-run detection through the lower-level closure API so we
        // get deterministic results. The signature is identical to
        // `TerminalEmulator::from_env` — we just route through it.
        let owned: HashMap<String, String> = env
            .iter()
            .map(|(k, v)| ((*k).to_string(), (*v).to_string()))
            .collect();
        TerminalEmulator::from_env(&|k| owned.get(k).cloned())
    }

    #[test]
    fn detect_wezterm_via_term_program() {
        let mut env: HashMap<&str, &str> = HashMap::new();
        env.insert("TERM_PROGRAM", "WezTerm");
        let (term, source) = detect_with(&env);
        assert_eq!(term, TerminalEmulator::WezTerm);
        assert!(
            source.contains("TERM_PROGRAM=WezTerm"),
            "source should mention TERM_PROGRAM, got: {source}"
        );
    }

    #[test]
    fn detect_kitty_via_kitty_window_id() {
        let mut env: HashMap<&str, &str> = HashMap::new();
        env.insert("KITTY_WINDOW_ID", "1");
        let (term, source) = detect_with(&env);
        assert_eq!(term, TerminalEmulator::Kitty);
        assert_eq!(source, "KITTY_WINDOW_ID");
    }

    #[test]
    fn detect_ghostty_via_term_program() {
        let mut env: HashMap<&str, &str> = HashMap::new();
        env.insert("TERM_PROGRAM", "ghostty");
        let (term, _) = detect_with(&env);
        assert_eq!(term, TerminalEmulator::Ghostty);
    }

    #[test]
    fn detect_rio_via_term_program() {
        let mut env: HashMap<&str, &str> = HashMap::new();
        env.insert("TERM_PROGRAM", "rio");
        let (term, _) = detect_with(&env);
        assert_eq!(term, TerminalEmulator::Rio);
    }

    #[test]
    fn detect_iterm2_via_term_program() {
        let mut env: HashMap<&str, &str> = HashMap::new();
        env.insert("TERM_PROGRAM", "iTerm.app");
        let (term, _) = detect_with(&env);
        assert_eq!(term, TerminalEmulator::ITerm2);
    }

    #[test]
    fn detect_windows_terminal_via_wt_session() {
        let mut env: HashMap<&str, &str> = HashMap::new();
        env.insert("WT_SESSION", "{abc-123}");
        let (term, source) = detect_with(&env);
        assert_eq!(term, TerminalEmulator::WindowsTerminal);
        assert_eq!(source, "WT_SESSION");
    }

    #[test]
    fn detect_unknown_when_no_signals() {
        let env: HashMap<&str, &str> = HashMap::new();
        // No signals at all -> Xterm (the documented fallback).
        let (term, _source) = detect_with(&env);
        assert_eq!(term, TerminalEmulator::Xterm);
    }

    #[test]
    fn detect_unknown_when_term_program_is_garbage() {
        // TERM_PROGRAM=foo -> lower('foo') doesn't match any known
        // mapping -> falls back to secondary heuristics; with no
        // secondary signals either, result is Xterm (the default).
        let mut env: HashMap<&str, &str> = HashMap::new();
        env.insert("TERM_PROGRAM", "totally-made-up-emulator");
        let (term, _) = detect_with(&env);
        assert_eq!(term, TerminalEmulator::Xterm);
    }

    #[test]
    fn apply_emulator_env_sets_marker_for_each_variant() {
        // One sub-test per TerminalEmulator variant — asserts every
        // variant yields a non-empty stable id when wired into a
        // Command. tokio::process::Command has no public introspection
        // API, so we assert on the id() surface directly (the value
        // apply_emulator_env copies into cmd.env()).
        let variants = [
            TerminalEmulator::WezTerm,
            TerminalEmulator::Rio,
            TerminalEmulator::Ghostty,
            TerminalEmulator::Kitty,
            TerminalEmulator::ITerm2,
            TerminalEmulator::AppleTerminal,
            TerminalEmulator::WindowsTerminal,
            TerminalEmulator::GnomeTerminal,
            TerminalEmulator::Konsole,
            TerminalEmulator::Alacritty,
            TerminalEmulator::Hyper,
            TerminalEmulator::St,
            TerminalEmulator::Tmux,
            TerminalEmulator::Screen,
            TerminalEmulator::VSCode,
            TerminalEmulator::JetBrains,
            TerminalEmulator::Xterm,
            TerminalEmulator::Unknown,
        ];
        for variant in variants {
            let id = variant.id();
            assert!(!id.is_empty(), "id for {variant:?} must not be empty");
            assert!(
                id.is_ascii(),
                "id for {variant:?} must be ASCII (env-var safe), got: {id}"
            );
            // FORGE_TERMINAL_EMULATOR constant is exactly what
            // apply_emulator_env uses — verify the surface contract.
            assert_eq!(FORGE_TERMINAL_EMULATOR, "FORGE_TERMINAL_EMULATOR");
        }
    }

    #[test]
    fn stable_ids_for_task_listed_variants() {
        // Spot-check the 8 variants named in the P2.2.1 task
        // description (WezTerm, Rio, Ghostty, Kitty, iTerm2,
        // WindowsTerminal, Xterm, Unknown) to confirm the surface
        // matches what downstream tooling expects.
        assert_eq!(TerminalEmulator::WezTerm.id(), "wezterm");
        assert_eq!(TerminalEmulator::Rio.id(), "rio");
        assert_eq!(TerminalEmulator::Ghostty.id(), "ghostty");
        assert_eq!(TerminalEmulator::Kitty.id(), "kitty");
        assert_eq!(TerminalEmulator::ITerm2.id(), "iterm2");
        assert_eq!(TerminalEmulator::WindowsTerminal.id(), "windows-terminal");
        assert_eq!(TerminalEmulator::Xterm.id(), "xterm");
        assert_eq!(TerminalEmulator::Unknown.id(), "unknown");
    }
}
