//! Plugin lifecycle states and transitions.
//!
//! A plugin moves through a small state machine: it is *registered*
//! (declared but not yet running), *initialized* (configuration applied
//! and resources acquired), *running* (accepting host calls), and
//! eventually *stopped* (resources released).
//!
//! The state machine is deliberately strict: any transition not in
//! [`PluginState::can_transition_to`] returns an error. This makes
//! incorrect shutdown order a build/test-detectable bug rather than a
//! silent resource leak.

use serde::{Deserialize, Serialize};

use crate::error::{PluginError, PluginResult};

/// Lifecycle state of a plugin instance.
///
/// The default state is [`PluginState::Registered`]. Plugins start
/// there, move through [`PluginState::Initialized`] →
/// [`PluginState::Running`] in normal use, and end at
/// [`PluginState::Stopped`]. [`PluginState::Failed`] is reachable from
/// any non-terminal state.
#[derive(
    Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub enum PluginState {
    /// Plugin is registered but not yet initialized.
    Registered,
    /// Plugin's `initialize()` has been called and succeeded.
    Initialized,
    /// Plugin is actively serving host calls.
    Running,
    /// Plugin has been stopped and its resources released.
    Stopped,
    /// Plugin entered an unrecoverable error state.
    Failed,
}

impl PluginState {
    /// Stable string identifier for logging and serialization.
    pub fn as_str(self) -> &'static str {
        match self {
            PluginState::Registered => "registered",
            PluginState::Initialized => "initialized",
            PluginState::Running => "running",
            PluginState::Stopped => "stopped",
            PluginState::Failed => "failed",
        }
    }

    /// Whether this state is a terminal state (no further transitions).
    pub fn is_terminal(self) -> bool {
        matches!(self, PluginState::Stopped | PluginState::Failed)
    }

    /// Whether a transition from `self` to `next` is allowed.
    ///
    /// The allowed graph is:
    /// - `Registered` → `Initialized`, `Failed`
    /// - `Initialized` → `Running`, `Stopped`, `Failed`
    /// - `Running` → `Stopped`, `Failed`
    /// - `Stopped` → `Registered` (re-registration for restart)
    /// - `Failed` → `Registered` (manual reset)
    pub fn can_transition_to(self, next: PluginState) -> bool {
        use PluginState::*;
        matches!(
            (self, next),
            (Registered, Initialized)
                | (Registered, Failed)
                | (Initialized, Running)
                | (Initialized, Stopped)
                | (Initialized, Failed)
                | (Running, Stopped)
                | (Running, Failed)
                | (Stopped, Registered)
                | (Failed, Registered)
        )
    }

    /// Transition to a new state, returning an error for illegal
    /// transitions. The error message includes both states for easier
    /// log triage.
    pub fn transition(self, next: PluginState) -> PluginResult<PluginState> {
        if self.can_transition_to(next) {
            Ok(next)
        } else {
            Err(PluginError::Validation(format!(
                "illegal state transition: {} -> {}",
                self.as_str(),
                next.as_str()
            )))
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use PluginState::*;

    #[test]
    fn test_state_as_str() {
        assert_eq!(Registered.as_str(), "registered");
        assert_eq!(Initialized.as_str(), "initialized");
        assert_eq!(Running.as_str(), "running");
        assert_eq!(Stopped.as_str(), "stopped");
        assert_eq!(Failed.as_str(), "failed");
    }

    #[test]
    fn test_terminal_states() {
        assert!(Stopped.is_terminal());
        assert!(Failed.is_terminal());
        assert!(!Registered.is_terminal());
        assert!(!Initialized.is_terminal());
        assert!(!Running.is_terminal());
    }

    #[test]
    fn test_happy_path_transitions() {
        assert!(Registered.can_transition_to(Initialized));
        assert!(Initialized.can_transition_to(Running));
        assert!(Running.can_transition_to(Stopped));
    }

    #[test]
    fn test_failure_path_transitions() {
        // Failed is reachable from any non-terminal state.
        assert!(Registered.can_transition_to(Failed));
        assert!(Initialized.can_transition_to(Failed));
        assert!(Running.can_transition_to(Failed));
    }

    #[test]
    fn test_stopped_to_registered_allowed_for_restart() {
        assert!(Stopped.can_transition_to(Registered));
        assert!(Failed.can_transition_to(Registered));
    }

    #[test]
    fn test_illegal_transitions_rejected() {
        // Skipping states.
        assert!(!Registered.can_transition_to(Running));
        assert!(!Registered.can_transition_to(Stopped));
        assert!(!Initialized.can_transition_to(Registered));
        // Going backwards.
        assert!(!Running.can_transition_to(Initialized));
        assert!(!Running.can_transition_to(Registered));
        // Self-loops are illegal.
        assert!(!Registered.can_transition_to(Registered));
        assert!(!Running.can_transition_to(Running));
        // Terminal states don't transition forward (other than to Registered).
        assert!(!Stopped.can_transition_to(Running));
        assert!(!Stopped.can_transition_to(Initialized));
        assert!(!Failed.can_transition_to(Running));
    }

    #[test]
    fn test_transition_returns_next_on_ok() {
        let next = Registered.transition(Initialized).unwrap();
        assert_eq!(next, Initialized);
    }

    #[test]
    fn test_transition_returns_error_on_illegal() {
        let err = Registered.transition(Running);
        assert!(err.is_err());
        let msg = err.unwrap_err().to_string();
        assert!(msg.contains("registered"));
        assert!(msg.contains("running"));
    }

    #[test]
    fn test_serde_roundtrip() {
        for s in [Registered, Initialized, Running, Stopped, Failed] {
            let json = serde_json::to_string(&s).unwrap();
            let parsed: PluginState = serde_json::from_str(&json).unwrap();
            assert_eq!(parsed, s);
        }
    }

    #[test]
    fn test_serde_snake_case() {
        assert_eq!(
            serde_json::to_string(&Running).unwrap(),
            "\"running\""
        );
    }

    #[test]
    fn test_full_lifecycle() {
        // Registered → Initialized → Running → Stopped → Registered (restart)
        let s = Registered;
        let s = s.transition(Initialized).unwrap();
        let s = s.transition(Running).unwrap();
        let s = s.transition(Stopped).unwrap();
        let s = s.transition(Registered).unwrap();
        assert_eq!(s, Registered);
    }

    #[test]
    fn test_failure_recovery() {
        // Registered → Failed → Registered (manual reset)
        let s = Registered;
        let s = s.transition(Failed).unwrap();
        let s = s.transition(Registered).unwrap();
        assert_eq!(s, Registered);
    }

    #[test]
    fn test_hash_eq_consistent() {
        use std::collections::HashSet;
        let mut set = HashSet::new();
        set.insert(Registered);
        set.insert(Registered);
        set.insert(Running);
        assert_eq!(set.len(), 2);
    }
}
