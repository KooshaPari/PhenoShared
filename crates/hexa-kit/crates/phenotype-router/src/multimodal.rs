//! H14.5 — multimodal content detection + route-by-modality selection.
//!
//! OpenAI-format chat-completions requests may carry any combination of:
//!   - Plain text parts
//!   - Vision parts (`image_url`)
//!   - Audio parts (`input_audio`)
//!   - Tool calls (`tool_call` parts on assistant/tool messages)
//!
//! [`detect_modality`] classifies a [`MultipartMessage`] into one of the coarse
//! [`Modality`] buckets, and [`route_by_modality`] picks the first [`RouteHint`]
//! in the supplied routing table that can serve that modality. Tool calls are
//! passed through unchanged — the router does not execute them; it only flags
//! their presence so the upstream provider can be chosen appropriately.

use serde::{Deserialize, Serialize};

/// A single part of a chat message's `content` array.
///
/// Modelled on the OpenAI multimodal content-part schema. The `tool_call`
/// variant appears on assistant messages that request tool execution; we
/// surface it so the router can detect tool-bearing requests without
/// re-parsing the full message.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum ContentPart {
    /// Plain text part: `{"type": "text", "text": "..."}`.
    Text {
        /// The text payload.
        text: String,
    },
    /// Image URL part: `{"type": "image_url", "image_url": {...}}`.
    ImageUrl {
        /// The image URL object (http(s) or data: URI + detail hint).
        image_url: ImageRef,
    },
    /// Audio part: `{"type": "input_audio", "input_audio": {...}}`.
    InputAudio {
        /// The audio payload (base64 + format).
        input_audio: AudioRef,
    },
    /// Tool call part on an assistant message:
    /// `{"type": "tool_call", "tool_call": {"id": "...", "function": {...}}}`.
    ToolCall {
        /// The tool call payload.
        tool_call: ToolCallRef,
    },
}

/// Image URL reference inside a vision content part.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ImageRef {
    /// URL (http(s) or data: URI).
    pub url: String,
    /// Resolution hint sent to the model.
    #[serde(default)]
    pub detail: ImageDetail,
}

/// Resolution hint for an [`ImageRef`].
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum ImageDetail {
    /// Let the model decide.
    Auto,
    /// Low-resolution fast pass.
    Low,
    /// High-resolution detailed pass.
    High,
}

impl Default for ImageDetail {
    fn default() -> Self {
        Self::Auto
    }
}

/// Audio reference inside an audio content part.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct AudioRef {
    /// Base64-encoded audio bytes.
    pub data: String,
    /// Container format (e.g. `"wav"`, `"mp3"`).
    pub format: String,
}

/// Tool call reference inside a tool-call content part.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ToolCallRef {
    /// Stable identifier for this tool invocation.
    pub id: String,
    /// Function name + JSON-encoded arguments.
    pub function: ToolFunction,
}

/// Function descriptor inside a [`ToolCallRef`].
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ToolFunction {
    /// Tool/function name.
    pub name: String,
    /// JSON-encoded argument object.
    pub arguments: String,
}

/// A message composed of one or more [`ContentPart`]s plus an OpenAI-style
/// `role`.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct MultipartMessage {
    /// Role tag: `"system"`, `"user"`, `"assistant"`, or `"tool"`.
    pub role: String,
    /// Ordered content parts.
    pub parts: Vec<ContentPart>,
}

impl MultipartMessage {
    /// Convenience constructor.
    pub fn new(role: impl Into<String>, parts: Vec<ContentPart>) -> Self {
        Self {
            role: role.into(),
            parts,
        }
    }

    /// Convenience: build a text-only message.
    pub fn text(role: impl Into<String>, text: impl Into<String>) -> Self {
        Self::new(role, vec![ContentPart::Text { text: text.into() }])
    }
}

/// Coarse-grained classification of a multipart message.
///
/// `detect_modality` picks exactly one bucket per call. If the message mixes
/// two or more of Vision/Audio/Tool, the priority order is
/// Tool > Vision > Audio > Text — the router biases toward the capability
/// that is hardest to satisfy downstream.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Modality {
    /// Plain text only (no images, no audio, no tool calls).
    Text,
    /// At least one image part and no tool/audio parts.
    Vision,
    /// At least one audio part and no tool/vision parts.
    Audio,
    /// At least one tool-call part present.
    Tool,
}

/// Capability tags a downstream route can advertise.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub struct RouteCapabilities {
    /// Can serve plain text.
    pub text: bool,
    /// Can serve vision parts.
    pub vision: bool,
    /// Can serve audio parts.
    pub audio: bool,
    /// Can serve (or execute) tool calls.
    pub tool: bool,
}

impl RouteCapabilities {
    /// All modalities supported.
    pub fn all() -> Self {
        Self {
            text: true,
            vision: true,
            audio: true,
            tool: true,
        }
    }

    /// Text-only route.
    pub fn text_only() -> Self {
        Self {
            text: true,
            vision: false,
            audio: false,
            tool: false,
        }
    }

    /// True if `self` can serve `modality`.
    pub fn serves(self, modality: Modality) -> bool {
        match modality {
            Modality::Text => self.text,
            Modality::Vision => self.vision && self.text,
            Modality::Audio => self.audio && self.text,
            Modality::Tool => self.tool,
        }
    }
}

impl Default for RouteCapabilities {
    fn default() -> Self {
        Self::text_only()
    }
}

/// One entry in the routing table — the router picks the first entry whose
/// [`RouteCapabilities`] can serve the detected modality.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RouteHint {
    /// Stable identifier used in logs / metrics (e.g. `"cliproxy-vision"`).
    pub target: String,
    /// What this route can serve.
    pub capabilities: RouteCapabilities,
    /// Optional priority weight — higher wins on ties. Default 0.
    #[serde(default)]
    pub priority: i32,
}

impl RouteHint {
    /// Convenience constructor.
    pub fn new(target: impl Into<String>, capabilities: RouteCapabilities) -> Self {
        Self {
            target: target.into(),
            capabilities,
            priority: 0,
        }
    }
}

/// Detect the modality of a single [`MultipartMessage`].
///
/// Classification rules:
/// - Any tool-call part → [`Modality::Tool`] (highest priority).
/// - Else any image part → [`Modality::Vision`].
/// - Else any audio part → [`Modality::Audio`].
/// - Else → [`Modality::Text`] (empty message also counts as text).
///
/// Tool wins over Vision/Audio because tool-bearing requests almost always
/// require a separate upstream, while Vision/Audio parts can frequently be
/// served by the same multimodal endpoint.
pub fn detect_modality(parts: &[ContentPart]) -> Modality {
    let mut has_vision = false;
    let mut has_audio = false;
    let mut has_tool = false;
    for p in parts {
        match p {
            ContentPart::Text { .. } => {}
            ContentPart::ImageUrl { .. } => has_vision = true,
            ContentPart::InputAudio { .. } => has_audio = true,
            ContentPart::ToolCall { .. } => has_tool = true,
        }
    }
    if has_tool {
        Modality::Tool
    } else if has_vision {
        Modality::Vision
    } else if has_audio {
        Modality::Audio
    } else {
        Modality::Text
    }
}

/// Detect the modality of a whole [`MultipartMessage`] (uses its `parts`).
pub fn detect_message_modality(msg: &MultipartMessage) -> Modality {
    detect_modality(&msg.parts)
}

/// Pick the first [`RouteHint`] in `routing_table` whose capabilities serve
/// the modality detected from `msg`. Tool calls are passed through unchanged
/// — this function does not execute or transform them.
///
/// Tie-breaking: among hints that can serve the modality, the one with the
/// highest `priority` wins; ties are broken by first-appearance order.
///
/// Returns `None` when no hint can serve the detected modality or when the
/// routing table is empty.
pub fn route_by_modality<'a>(
    msg: &MultipartMessage,
    routing_table: &'a [RouteHint],
) -> Option<&'a RouteHint> {
    let m = detect_message_modality(msg);
    let mut best: Option<&RouteHint> = None;
    for hint in routing_table {
        if hint.capabilities.serves(m) {
            match best {
                None => best = Some(hint),
                Some(cur) if hint.priority > cur.priority => best = Some(hint),
                _ => {}
            }
        }
    }
    best
}

#[cfg(test)]
mod tests {
    use super::*;

    fn img() -> ContentPart {
        ContentPart::ImageUrl {
            image_url: ImageRef {
                url: "https://example.com/cat.png".to_string(),
                detail: ImageDetail::Auto,
            },
        }
    }

    fn aud() -> ContentPart {
        ContentPart::InputAudio {
            input_audio: AudioRef {
                data: "AAAA".to_string(),
                format: "wav".to_string(),
            },
        }
    }

    fn tool() -> ContentPart {
        ContentPart::ToolCall {
            tool_call: ToolCallRef {
                id: "call_1".to_string(),
                function: ToolFunction {
                    name: "get_weather".to_string(),
                    arguments: "{}".to_string(),
                },
            },
        }
    }

    #[test]
    fn text_only_message_is_text() {
        let msg = MultipartMessage::text("user", "hello");
        assert_eq!(detect_message_modality(&msg), Modality::Text);
    }

    #[test]
    fn empty_parts_is_text() {
        let msg = MultipartMessage::new("user", vec![]);
        assert_eq!(detect_message_modality(&msg), Modality::Text);
    }

    #[test]
    fn mixed_text_and_image_is_vision() {
        let msg = MultipartMessage::new(
            "user",
            vec![
                ContentPart::Text {
                    text: "what is this?".to_string(),
                },
                img(),
            ],
        );
        assert_eq!(detect_message_modality(&msg), Modality::Vision);
    }

    #[test]
    fn audio_part_is_audio() {
        let msg = MultipartMessage::new("user", vec![aud()]);
        assert_eq!(detect_message_modality(&msg), Modality::Audio);
    }

    #[test]
    fn tool_call_part_is_tool_even_with_other_parts() {
        let msg = MultipartMessage::new(
            "assistant",
            vec![
                ContentPart::Text {
                    text: "calling tool".to_string(),
                },
                tool(),
                img(),
            ],
        );
        // Tool has highest priority per the documented rules.
        assert_eq!(detect_message_modality(&msg), Modality::Tool);
    }

    #[test]
    fn tool_call_passthrough_does_not_mutate_parts() {
        let original = vec![
            ContentPart::Text {
                text: "use weather".to_string(),
            },
            tool(),
        ];
        let msg = MultipartMessage::new("assistant", original.clone());
        // route_by_modality must not mutate the message.
        let table = vec![RouteHint::new("cliproxy", RouteCapabilities::all())];
        let picked = route_by_modality(&msg, &table).expect("route present");
        assert_eq!(picked.target, "cliproxy");
        assert_eq!(msg.parts, original);
    }

    #[test]
    fn route_text_picks_first_text_capable_hint() {
        let msg = MultipartMessage::text("user", "hi");
        let table = vec![
            RouteHint::new("a", RouteCapabilities::text_only()),
            RouteHint::new("b", RouteCapabilities::all()),
        ];
        let picked = route_by_modality(&msg, &table).unwrap();
        assert_eq!(picked.target, "a");
    }

    #[test]
    fn route_vision_skips_text_only_hints() {
        let msg = MultipartMessage::new("user", vec![img()]);
        let table = vec![
            RouteHint::new("text-a", RouteCapabilities::text_only()),
            RouteHint::new(
                "vision",
                RouteCapabilities {
                    text: true,
                    vision: true,
                    audio: false,
                    tool: false,
                },
            ),
            RouteHint::new(
                "vision-b",
                RouteCapabilities {
                    text: true,
                    vision: true,
                    audio: false,
                    tool: false,
                },
            ),
        ];
        let picked = route_by_modality(&msg, &table).unwrap();
        assert_eq!(picked.target, "vision");
    }

    #[test]
    fn route_audio_requires_audio_capable_hint() {
        let msg = MultipartMessage::new("user", vec![aud()]);
        let table = vec![
            RouteHint::new("text", RouteCapabilities::text_only()),
            RouteHint::new(
                "vision",
                RouteCapabilities {
                    text: true,
                    vision: true,
                    audio: false,
                    tool: false,
                },
            ),
            RouteHint::new(
                "audio",
                RouteCapabilities {
                    text: true,
                    vision: false,
                    audio: true,
                    tool: false,
                },
            ),
        ];
        let picked = route_by_modality(&msg, &table).unwrap();
        assert_eq!(picked.target, "audio");
    }

    #[test]
    fn route_tool_requires_tool_capable_hint() {
        let msg = MultipartMessage::new("assistant", vec![tool()]);
        let table = vec![
            RouteHint::new("text", RouteCapabilities::text_only()),
            RouteHint::new(
                "vision",
                RouteCapabilities {
                    text: true,
                    vision: true,
                    audio: false,
                    tool: false,
                },
            ),
            RouteHint::new(
                "tools",
                RouteCapabilities {
                    text: true,
                    vision: false,
                    audio: false,
                    tool: true,
                },
            ),
        ];
        let picked = route_by_modality(&msg, &table).unwrap();
        assert_eq!(picked.target, "tools");
    }

    #[test]
    fn route_returns_none_when_no_hint_serves() {
        let msg = MultipartMessage::new("user", vec![img()]);
        let table = vec![RouteHint::new("text", RouteCapabilities::text_only())];
        assert!(route_by_modality(&msg, &table).is_none());
    }

    #[test]
    fn route_returns_none_for_empty_table() {
        let msg = MultipartMessage::text("user", "hi");
        let table: Vec<RouteHint> = vec![];
        assert!(route_by_modality(&msg, &table).is_none());
    }

    #[test]
    fn priority_breaks_ties_in_route_selection() {
        let msg = MultipartMessage::text("user", "hi");
        let table = vec![
            RouteHint {
                target: "low".into(),
                capabilities: RouteCapabilities::all(),
                priority: 0,
            },
            RouteHint {
                target: "high".into(),
                capabilities: RouteCapabilities::all(),
                priority: 10,
            },
        ];
        let picked = route_by_modality(&msg, &table).unwrap();
        assert_eq!(picked.target, "high");
    }

    #[test]
    fn serves_predicate_matches_each_modality() {
        let caps = RouteCapabilities::all();
        assert!(caps.serves(Modality::Text));
        assert!(caps.serves(Modality::Vision));
        assert!(caps.serves(Modality::Audio));
        assert!(caps.serves(Modality::Tool));

        let text_only = RouteCapabilities::text_only();
        assert!(text_only.serves(Modality::Text));
        assert!(!text_only.serves(Modality::Vision));
        assert!(!text_only.serves(Modality::Audio));
        assert!(!text_only.serves(Modality::Tool));
    }

    #[test]
    fn content_part_round_trips_via_serde() {
        let cases = vec![
            ContentPart::Text { text: "hi".into() },
            ContentPart::ImageUrl {
                image_url: ImageRef {
                    url: "https://x/i.png".into(),
                    detail: ImageDetail::High,
                },
            },
            ContentPart::InputAudio {
                input_audio: AudioRef {
                    data: "AAAA".into(),
                    format: "wav".into(),
                },
            },
            ContentPart::ToolCall {
                tool_call: ToolCallRef {
                    id: "call_1".into(),
                    function: ToolFunction {
                        name: "f".into(),
                        arguments: "{}".into(),
                    },
                },
            },
        ];
        for p in cases {
            let v = serde_json::to_value(&p).unwrap();
            let back: ContentPart = serde_json::from_value(v).unwrap();
            assert_eq!(back, p);
        }
    }

    #[test]
    fn multipart_message_round_trips_via_serde() {
        let msg = MultipartMessage::new(
            "user",
            vec![
                ContentPart::Text {
                    text: "what?".into(),
                },
                img(),
            ],
        );
        let v = serde_json::to_value(&msg).unwrap();
        let back: MultipartMessage = serde_json::from_value(v).unwrap();
        assert_eq!(back, msg);
    }
}
