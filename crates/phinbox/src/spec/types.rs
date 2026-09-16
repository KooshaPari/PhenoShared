//! The agent-authored prompt spec and the human-returned response.
//!
//! These types are the **contract** between the agent and the popup.
//! Both surfaces serialize via serde; the JSON Schema is exported by
//! [`crate::schema`] for the MCP server's `inputSchema` / `outputSchema`.

use schemars::JsonSchema;
use serde::{Deserialize, Serialize};

/// The agent's authored prompt for a single popup.
///
/// The schema is designed so the agent can compose any UI surface from
/// primitive building blocks (text field, choice, boolean, etc.) without
/// the MCP surface needing to grow.
///
/// # Example (serde JSON)
///
/// ```json
/// {
///   "title": "Approve deployment?",
///   "question": "The diff touches 14 files. Continue with rollout?",
///   "field": {
///     "kind": "boolean",
///     "label": "Proceed?",
///     "default": true
///   },
///   "notes": {
///     "label": "Why? (optional)",
///     "required": false
///   },
///   "urgency": "warning",
///   "timeout_secs": 60
/// }
/// ```
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct PromptSpec {
    /// One-line title shown in the popup window title bar.
    /// Max 80 chars.
    pub title: String,

    /// Multi-line body explaining context. Plain text only (no markdown —
    /// native chrome has no renderer). Max 2000 chars.
    pub question: String,

    /// The input field configuration.
    pub field: FieldSpec,

    /// Optional notes / free-text box shown below the field.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub notes: Option<NotesSpec>,

    /// Button labels. Default: `{"cancel": "Cancel", "confirm": "OK"}`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub buttons: Option<ButtonSpec>,

    /// Urgency hint — affects icon + sound.
    #[serde(default)]
    pub urgency: Urgency,

    /// Timeout in seconds. After this, the response is `TimedOut`.
    /// Default: 600 (10 min). Set to 0 for no timeout (CI only).
    #[serde(default = "default_timeout_secs")]
    pub timeout_secs: u32,

    /// Request ID for correlation when multiple prompts are queued.
    /// If omitted, the library auto-generates a `UUIDv4`.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub request_id: Option<String>,
}

pub(crate) const fn default_timeout_secs() -> u32 {
    600
}

/// The input field configuration.
///
/// Tagged enum over six primitive kinds. Each kind carries only the
/// fields relevant to it; serde's `tag = "kind"` gives clean JSON,
/// and schemars' matching `tag = "kind"` produces a discriminated
/// schema in JSON Schema 2020-12 style.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[schemars(tag = "kind", rename_all = "snake_case")]
#[serde(tag = "kind", rename_all = "snake_case", deny_unknown_fields)]
pub enum FieldSpec {
    /// Single-line text input.
    Text {
        /// Label shown above the input.
        label: String,
        /// Default value (pre-filled).
        #[serde(default, skip_serializing_if = "Option::is_none")]
        default: Option<String>,
        /// Placeholder text (shown when empty).
        #[serde(default, skip_serializing_if = "Option::is_none")]
        placeholder: Option<String>,
        /// Maximum input length.
        #[serde(default, skip_serializing_if = "Option::is_none")]
        max_length: Option<u32>,
        /// If true, render as password field (• mask).
        #[serde(default)]
        secret: bool,
        /// Regex the value must match before OK is enabled.
        #[serde(default, skip_serializing_if = "Option::is_none")]
        pattern: Option<String>,
    },

    /// Long-form multi-line text.
    LongText {
        label: String,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        default: Option<String>,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        max_length: Option<u32>,
    },

    /// Integer in `[min, max]`.
    Integer {
        label: String,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        min: Option<i64>,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        max: Option<i64>,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        default: Option<i64>,
    },

    /// Choice from a fixed list (radio buttons on GUI, select prompt on TUI).
    Choice {
        label: String,
        options: Vec<ChoiceOption>,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        default_index: Option<usize>,
    },

    /// Boolean yes/no. Renders as 2 buttons.
    Boolean {
        label: String,
        #[serde(default, skip_serializing_if = "Option::is_none")]
        default: Option<bool>,
    },

    /// Date / time picker.
    DateTime {
        label: String,
        /// RFC3339 default.
        #[serde(default, skip_serializing_if = "Option::is_none")]
        default: Option<String>,
        /// Which picker to render — date, time, or both.
        #[serde(default = "default_datetime_kind")]
        picker_kind: DateTimeKind,
    },
}

const fn default_datetime_kind() -> DateTimeKind {
    DateTimeKind::DateTime
}

/// A single option in a [`FieldSpec::Choice`].
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ChoiceOption {
    /// Machine-readable value returned in the response.
    pub value: String,
    /// Human-readable label shown in the popup.
    pub label: String,
    /// Optional longer description (shown as help text on GUI).
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub description: Option<String>,
}

/// The optional notes / free-text box.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct NotesSpec {
    /// Label shown above the notes box.
    pub label: String,
    /// Pre-filled notes.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub default: Option<String>,
    /// Maximum notes length.
    #[serde(default, skip_serializing_if = "Option::is_none")]
    pub max_length: Option<u32>,
    /// If true, the OK button is disabled until notes are non-empty.
    #[serde(default)]
    pub required: bool,
}

/// Custom button labels.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[serde(deny_unknown_fields)]
pub struct ButtonSpec {
    /// Cancel button label. Default: "Cancel".
    pub cancel: String,
    /// Confirm button label. Default: "OK".
    pub confirm: String,
    /// If true, swap which button is the default (Enter-key target).
    #[serde(default)]
    pub default_is_cancel: bool,
}

impl Default for ButtonSpec {
    fn default() -> Self {
        Self {
            cancel: "Cancel".to_string(),
            confirm: "OK".to_string(),
            default_is_cancel: false,
        }
    }
}

/// Urgency hint — affects icon and sound on GUI popups.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq, Serialize, Deserialize, JsonSchema)]
#[schemars(rename_all = "lowercase")]
#[serde(rename_all = "lowercase")]
pub enum Urgency {
    /// Informational (no sound, blue icon).
    #[default]
    Info,
    /// Warning (system sound, yellow icon).
    Warning,
    /// Error / critical (alert sound, red icon).
    Error,
    /// Treat as secret input (mask field, no logging).
    Secret,
}

/// What kind of date/time picker to render.
#[derive(Debug, Clone, Copy, Serialize, Deserialize, JsonSchema)]
#[schemars(rename_all = "lowercase")]
#[serde(rename_all = "lowercase")]
pub enum DateTimeKind {
    /// Date only (YYYY-MM-DD).
    Date,
    /// Time only (HH:MM).
    Time,
    /// Both (RFC3339).
    DateTime,
}

/// The value the human entered. Tagged enum mirrors [`FieldSpec`]'s kinds.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[schemars(tag = "kind", content = "value", rename_all = "snake_case")]
#[serde(tag = "kind", content = "value", rename_all = "snake_case")]
pub enum FieldValue {
    /// Text field value.
    Text(String),
    /// Long-text field value.
    LongText(String),
    /// Integer field value.
    Integer(i64),
    /// Choice field value (returns both the value and the index).
    Choice { value: String, index: usize },
    /// Boolean field value.
    Boolean(bool),
    /// Date/time field value (RFC3339).
    DateTime(String),
}

/// The popup's response — either an answer, a cancel, a timeout, or a failure.
#[derive(Debug, Clone, Serialize, Deserialize, JsonSchema)]
#[schemars(tag = "status", rename_all = "snake_case")]
#[serde(tag = "status", rename_all = "snake_case")]
pub enum ElicitResponse {
    /// User clicked OK and entered a value.
    Answered {
        value: FieldValue,
        /// Notes if a notes box was rendered and filled.
        #[serde(default, skip_serializing_if = "Option::is_none")]
        notes: Option<String>,
    },
    /// User clicked Cancel. Notes may be populated if they typed some.
    Cancelled {
        #[serde(default, skip_serializing_if = "Option::is_none")]
        notes: Option<String>,
    },
    /// Popup timed out without a response.
    TimedOut {
        /// Seconds elapsed before the timeout fired.
        elapsed_secs: f64,
    },
    /// Popup failed to render. The agent should fall back to a different
    /// strategy (e.g., inline question, or retry with `--renderer=force-tty`).
    Failed {
        /// Human-readable failure reason.
        reason: String,
    },
}

impl Default for ElicitResponse {
    fn default() -> Self {
        Self::Cancelled { notes: None }
    }
}

impl ElicitResponse {
    /// Returns `true` if the user provided an answer (vs cancelling, timing
    /// out, or the popup failing).
    #[must_use]
    pub fn is_answered(&self) -> bool {
        matches!(self, Self::Answered { .. })
    }

    /// Returns `true` if the user cancelled.
    #[must_use]
    pub fn is_cancelled(&self) -> bool {
        matches!(self, Self::Cancelled { .. })
    }

    /// Returns `true` if the popup timed out.
    #[must_use]
    pub fn is_timed_out(&self) -> bool {
        matches!(self, Self::TimedOut { .. })
    }

    /// Returns `true` if the popup failed to render.
    #[must_use]
    pub fn is_failed(&self) -> bool {
        matches!(self, Self::Failed { .. })
    }
}
