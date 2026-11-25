use serde::{Deserialize, Serialize};

/// Pointer (mouse/touch) input action.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PointerInput {
    /// X coordinate.
    pub x: i32,
    /// Y coordinate.
    pub y: i32,
    /// Button: "left", "right", "middle", or None for movement.
    pub button: Option<String>,
    /// Action: "press", "release", "move", "tap", "long_press".
    pub action: String,
    /// Duration in milliseconds for long press / hold.
    pub duration_ms: Option<u32>,
}

/// Text input action.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TextInput {
    /// Text to input.
    pub text: String,
    /// Type of input: "keystroke", "paste", "clear".
    pub input_type: String,
    /// Delay between keystrokes (ms).
    pub delay_ms: Option<u32>,
}

impl PointerInput {
    pub fn click(x: i32, y: i32) -> Self {
        Self {
            x,
            y,
            button: Some("left".to_string()),
            action: "press".to_string(),
            duration_ms: None,
        }
    }

    pub fn move_to(x: i32, y: i32) -> Self {
        Self {
            x,
            y,
            button: None,
            action: "move".to_string(),
            duration_ms: None,
        }
    }
}

impl TextInput {
    pub fn keystroke(text: impl Into<String>) -> Self {
        Self {
            text: text.into(),
            input_type: "keystroke".to_string(),
            delay_ms: None,
        }
    }

    pub fn paste(text: impl Into<String>) -> Self {
        Self {
            text: text.into(),
            input_type: "paste".to_string(),
            delay_ms: None,
        }
    }
}
