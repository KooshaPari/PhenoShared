//! Data Transfer Objects for Conversation Repository
//!
//! This module contains repository-specific record types that mirror their
//! `forge_domain` counterparts for compile-time safety while keeping the
//! storage layer independent from domain model changes.

use anyhow::Context as _;
use forge_domain::{Context, ConversationId};
use serde::{Deserialize, Serialize};

/// Repository-specific representation of ModelId
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(transparent)]
pub(super) struct ModelIdRecord(String);

impl From<&forge_domain::ModelId> for ModelIdRecord {
    fn from(id: &forge_domain::ModelId) -> Self {
        Self(id.to_string())
    }
}

impl From<ModelIdRecord> for forge_domain::ModelId {
    fn from(record: ModelIdRecord) -> Self {
        forge_domain::ModelId::from(record.0)
    }
}

/// Repository-specific representation of Image
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub(super) struct ImageRecord {
    url: String,
    mime_type: String,
}

impl From<&forge_domain::Image> for ImageRecord {
    fn from(image: &forge_domain::Image) -> Self {
        Self {
            url: image.url().to_string(),
            mime_type: image.mime_type().to_string(),
        }
    }
}

impl From<ImageRecord> for forge_domain::Image {
    fn from(record: ImageRecord) -> Self {
        forge_domain::Image::new_base64(
            record
                .url
                .strip_prefix(&format!("data:{};base64,", record.mime_type))
                .unwrap_or(&record.url)
                .to_string(),
            record.mime_type,
        )
    }
}

/// Repository-specific representation of ToolCallId
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(transparent)]
pub(super) struct ToolCallIdRecord(String);

impl From<&forge_domain::ToolCallId> for ToolCallIdRecord {
    fn from(id: &forge_domain::ToolCallId) -> Self {
        Self(id.as_str().to_string())
    }
}

impl From<ToolCallIdRecord> for forge_domain::ToolCallId {
    fn from(record: ToolCallIdRecord) -> Self {
        forge_domain::ToolCallId::new(record.0)
    }
}

/// Repository-specific representation of ToolCallArguments
/// Stored as raw JSON Value to handle both parsed and unparsed variants
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(transparent)]
pub(super) struct ToolCallArgumentsRecord(serde_json::Value);

impl From<&forge_domain::ToolCallArguments> for ToolCallArgumentsRecord {
    fn from(args: &forge_domain::ToolCallArguments) -> Self {
        // Serialize to JSON to capture both Parsed and Unparsed variants
        Self(serde_json::to_value(args).unwrap_or_default())
    }
}

impl From<ToolCallArgumentsRecord> for forge_domain::ToolCallArguments {
    fn from(record: ToolCallArgumentsRecord) -> Self {
        // Deserialize back to ToolCallArguments (always becomes Parsed variant)
        serde_json::from_value(record.0).unwrap_or_default()
    }
}

/// Repository-specific representation of ToolName
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(transparent)]
pub(super) struct ToolNameRecord(String);

impl From<&forge_domain::ToolName> for ToolNameRecord {
    fn from(name: &forge_domain::ToolName) -> Self {
        Self(name.to_string())
    }
}

impl From<ToolNameRecord> for forge_domain::ToolName {
    fn from(record: ToolNameRecord) -> Self {
        forge_domain::ToolName::new(record.0)
    }
}

/// Repository-specific representation of ToolCallFull
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(super) struct ToolCallFullRecord {
    name: ToolNameRecord,
    call_id: Option<ToolCallIdRecord>,
    arguments: ToolCallArgumentsRecord,
    #[serde(skip_serializing_if = "Option::is_none")]
    thought_signature: Option<String>,
}

impl From<&forge_domain::ToolCallFull> for ToolCallFullRecord {
    fn from(call: &forge_domain::ToolCallFull) -> Self {
        Self {
            name: ToolNameRecord::from(&call.name),
            call_id: call.call_id.as_ref().map(ToolCallIdRecord::from),
            arguments: ToolCallArgumentsRecord::from(&call.arguments),
            thought_signature: call.thought_signature.clone(),
        }
    }
}

impl From<ToolCallFullRecord> for forge_domain::ToolCallFull {
    fn from(record: ToolCallFullRecord) -> Self {
        forge_domain::ToolCallFull {
            name: record.name.into(),
            call_id: record.call_id.map(Into::into),
            arguments: record.arguments.into(),
            thought_signature: record.thought_signature,
        }
    }
}

/// Repository-specific representation of ReasoningFull (alias for
/// ReasoningDetail)
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub(super) struct ReasoningFullRecord {
    #[serde(skip_serializing_if = "Option::is_none")]
    text: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    signature: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    data: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    id: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    format: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    index: Option<i32>,
    #[serde(skip_serializing_if = "Option::is_none")]
    type_of: Option<String>,
}

impl From<&forge_domain::ReasoningFull> for ReasoningFullRecord {
    fn from(reasoning: &forge_domain::ReasoningFull) -> Self {
        Self {
            text: reasoning.text.clone(),
            signature: reasoning.signature.clone(),
            data: reasoning.data.clone(),
            id: reasoning.id.clone(),
            format: reasoning.format.clone(),
            index: reasoning.index,
            type_of: reasoning.type_of.clone(),
        }
    }
}

impl From<ReasoningFullRecord> for forge_domain::ReasoningFull {
    fn from(record: ReasoningFullRecord) -> Self {
        forge_domain::ReasoningFull {
            text: record.text,
            signature: record.signature,
            data: record.data,
            id: record.id,
            format: record.format,
            index: record.index,
            type_of: record.type_of,
        }
    }
}

/// Repository-specific representation of TokenCount
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(super) enum TokenCountRecord {
    #[serde(alias = "Actual")]
    Actual(usize),
    #[serde(alias = "Approx")]
    Approx(usize),
}

impl From<&forge_domain::TokenCount> for TokenCountRecord {
    fn from(count: &forge_domain::TokenCount) -> Self {
        match count {
            forge_domain::TokenCount::Actual(n) => Self::Actual(*n),
            forge_domain::TokenCount::Approx(n) => Self::Approx(*n),
        }
    }
}

impl From<TokenCountRecord> for forge_domain::TokenCount {
    fn from(record: TokenCountRecord) -> Self {
        match record {
            TokenCountRecord::Actual(n) => Self::Actual(n),
            TokenCountRecord::Approx(n) => Self::Approx(n),
        }
    }
}

/// Repository-specific representation of Usage
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(super) struct UsageRecord {
    prompt_tokens: TokenCountRecord,
    completion_tokens: TokenCountRecord,
    total_tokens: TokenCountRecord,
    cached_tokens: TokenCountRecord,
    #[serde(skip_serializing_if = "Option::is_none")]
    cost: Option<f64>,
}

impl From<&forge_domain::Usage> for UsageRecord {
    fn from(usage: &forge_domain::Usage) -> Self {
        Self {
            prompt_tokens: TokenCountRecord::from(&usage.prompt_tokens),
            completion_tokens: TokenCountRecord::from(&usage.completion_tokens),
            total_tokens: TokenCountRecord::from(&usage.total_tokens),
            cached_tokens: TokenCountRecord::from(&usage.cached_tokens),
            cost: usage.cost,
        }
    }
}

impl From<UsageRecord> for forge_domain::Usage {
    fn from(record: UsageRecord) -> Self {
        forge_domain::Usage {
            prompt_tokens: record.prompt_tokens.into(),
            completion_tokens: record.completion_tokens.into(),
            total_tokens: record.total_tokens.into(),
            cached_tokens: record.cached_tokens.into(),
            cost: record.cost,
        }
    }
}

/// Repository-specific representation of EventValue
/// Stored as raw JSON to avoid coupling with UserPrompt and UserCommand
/// structures
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(transparent)]
pub(super) struct EventValueRecord(serde_json::Value);

impl From<&forge_domain::EventValue> for EventValueRecord {
    fn from(event: &forge_domain::EventValue) -> Self {
        Self(serde_json::to_value(event).unwrap_or_default())
    }
}

impl TryFrom<EventValueRecord> for forge_domain::EventValue {
    type Error = anyhow::Error;

    fn try_from(record: EventValueRecord) -> anyhow::Result<Self> {
        Ok(serde_json::from_value(record.0)?)
    }
}

/// Repository-specific representation of Role
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
pub enum RoleRecord {
    System,
    User,
    Assistant,
    Tool,
}

impl From<&forge_domain::Role> for RoleRecord {
    fn from(role: &forge_domain::Role) -> Self {
        match role {
            forge_domain::Role::System => Self::System,
            forge_domain::Role::User => Self::User,
            forge_domain::Role::Assistant => Self::Assistant,
            forge_domain::Role::Tool => Self::Tool,
        }
    }
}

impl From<RoleRecord> for forge_domain::Role {
    fn from(record: RoleRecord) -> Self {
        match record {
            RoleRecord::System => Self::System,
            RoleRecord::User => Self::User,
            RoleRecord::Assistant => Self::Assistant,
            RoleRecord::Tool => Self::Tool,
        }
    }
}

/// Repository-specific representation of TextMessage
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(super) struct TextMessageRecord {
    role: RoleRecord,
    content: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    raw_content: Option<EventValueRecord>,
    #[serde(skip_serializing_if = "Option::is_none")]
    tool_calls: Option<Vec<ToolCallFullRecord>>,
    #[serde(skip_serializing_if = "Option::is_none")]
    thought_signature: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    model: Option<ModelIdRecord>,
    #[serde(skip_serializing_if = "Option::is_none")]
    reasoning_details: Option<Vec<ReasoningFullRecord>>,
    #[serde(default, skip_serializing_if = "is_false")]
    droppable: bool,
}

/// Helper function for serde to skip serializing false boolean values
fn is_false(value: &bool) -> bool {
    !value
}

impl From<&forge_domain::TextMessage> for TextMessageRecord {
    fn from(msg: &forge_domain::TextMessage) -> Self {
        Self {
            role: RoleRecord::from(&msg.role),
            content: msg.content.clone(),
            raw_content: msg.raw_content.as_ref().map(EventValueRecord::from),
            tool_calls: msg
                .tool_calls
                .as_ref()
                .map(|calls| calls.iter().map(ToolCallFullRecord::from).collect()),
            thought_signature: msg.thought_signature.clone(),
            model: msg.model.as_ref().map(ModelIdRecord::from),
            reasoning_details: msg
                .reasoning_details
                .as_ref()
                .map(|details| details.iter().map(ReasoningFullRecord::from).collect()),
            droppable: msg.droppable,
        }
    }
}

impl TryFrom<TextMessageRecord> for forge_domain::TextMessage {
    type Error = anyhow::Error;

    fn try_from(record: TextMessageRecord) -> anyhow::Result<Self> {
        Ok(forge_domain::TextMessage {
            role: record.role.into(),
            content: record.content,
            raw_content: record.raw_content.map(TryInto::try_into).transpose()?,
            tool_calls: record
                .tool_calls
                .map(|calls| calls.into_iter().map(Into::into).collect()),
            thought_signature: record.thought_signature,
            model: record.model.map(Into::into),
            reasoning_details: record
                .reasoning_details
                .map(|details| details.into_iter().map(Into::into).collect()),
            droppable: record.droppable,
            phase: None,
        })
    }
}

/// Repository-specific representation of ToolValue
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(super) enum ToolValueRecord {
    Text(String),
    AI {
        value: String,
        conversation_id: String,
    },
    Image(ImageRecord),
    Empty,
    // Legacy variants for backward compatibility with old conversations
    // These were removed from the domain model but may exist in stored data
    /// Legacy: Markdown-formatted text (now converted to Text)
    Markdown(String),
    /// Legacy: File diff information (now converted to Text summary)
    FileDiff(FileDiffRecord),
    /// Legacy: Paired value for LLM/display (now flattened to first element)
    Pair(Box<ToolValueRecord>, Box<ToolValueRecord>),
}

/// Legacy record for FileDiff - kept for backward compatibility
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(super) struct FileDiffRecord {
    pub path: String,
    pub old_text: Option<String>,
    pub new_text: String,
}

impl From<&forge_domain::ToolValue> for ToolValueRecord {
    fn from(value: &forge_domain::ToolValue) -> Self {
        match value {
            forge_domain::ToolValue::Text(text) => Self::Text(text.clone()),
            forge_domain::ToolValue::AI { value, conversation_id } => Self::AI {
                value: value.clone(),
                conversation_id: conversation_id.into_string(),
            },
            forge_domain::ToolValue::Image(img) => Self::Image(ImageRecord::from(img)),
            forge_domain::ToolValue::Empty => Self::Empty,
        }
    }
}

impl TryFrom<ToolValueRecord> for forge_domain::ToolValue {
    type Error = anyhow::Error;

    fn try_from(record: ToolValueRecord) -> anyhow::Result<Self> {
        Ok(match record {
            ToolValueRecord::Text(text) => Self::Text(text),
            ToolValueRecord::AI { value, conversation_id } => Self::AI {
                value,
                conversation_id: ConversationId::parse(conversation_id)?,
            },
            ToolValueRecord::Image(img) => Self::Image(img.into()),
            ToolValueRecord::Empty => Self::Empty,
            // Legacy variant migrations
            ToolValueRecord::Markdown(md) => Self::Text(md),
            ToolValueRecord::FileDiff(diff) => {
                // Convert FileDiff to a text summary
                Self::Text(format!("[File diff: {}]", diff.path))
            }
            ToolValueRecord::Pair(first, _second) => {
                // Take the first value (LLM-facing content) and convert it
                (*first).try_into()?
            }
        })
    }
}

/// Repository-specific representation of ToolOutput
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(crate) struct ToolOutputRecord {
    is_error: bool,
    values: Vec<ToolValueRecord>,
}

impl From<&forge_domain::ToolOutput> for ToolOutputRecord {
    fn from(output: &forge_domain::ToolOutput) -> Self {
        Self {
            is_error: output.is_error,
            values: output.values.iter().map(ToolValueRecord::from).collect(),
        }
    }
}

impl TryFrom<ToolOutputRecord> for forge_domain::ToolOutput {
    type Error = anyhow::Error;

    fn try_from(record: ToolOutputRecord) -> anyhow::Result<Self> {
        let values: Result<Vec<_>, _> = record.values.into_iter().map(TryInto::try_into).collect();
        Ok(forge_domain::ToolOutput { is_error: record.is_error, values: values? })
    }
}

/// Repository-specific representation of ToolResult
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(super) struct ToolResultRecord {
    name: ToolNameRecord,
    call_id: Option<ToolCallIdRecord>,
    output: ToolOutputRecord,
}

impl From<&forge_domain::ToolResult> for ToolResultRecord {
    fn from(result: &forge_domain::ToolResult) -> Self {
        Self {
            name: ToolNameRecord::from(&result.name),
            call_id: result.call_id.as_ref().map(ToolCallIdRecord::from),
            output: ToolOutputRecord::from(&result.output),
        }
    }
}

impl TryFrom<ToolResultRecord> for forge_domain::ToolResult {
    type Error = anyhow::Error;

    fn try_from(record: ToolResultRecord) -> anyhow::Result<Self> {
        Ok(forge_domain::ToolResult {
            name: record.name.into(),
            call_id: record.call_id.map(Into::into),
            output: record.output.try_into()?,
        })
    }
}

/// Repository-specific representation of ContextMessageValue
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub(super) enum ContextMessageValueRecord {
    Text(TextMessageRecord),
    Tool(ToolResultRecord),
    Image(ImageRecord),
}

impl From<&forge_domain::ContextMessage> for ContextMessageValueRecord {
    fn from(value: &forge_domain::ContextMessage) -> Self {
        match value {
            forge_domain::ContextMessage::Text(msg) => Self::Text(TextMessageRecord::from(msg)),
            forge_domain::ContextMessage::Tool(result) => {
                Self::Tool(ToolResultRecord::from(result))
            }
            forge_domain::ContextMessage::Image(img) => Self::Image(ImageRecord::from(img)),
        }
    }
}

impl TryFrom<ContextMessageValueRecord> for forge_domain::ContextMessage {
    type Error = anyhow::Error;

    fn try_from(record: ContextMessageValueRecord) -> anyhow::Result<Self> {
        Ok(match record {
            ContextMessageValueRecord::Text(msg) => Self::Text(msg.try_into()?),
            ContextMessageValueRecord::Tool(result) => Self::Tool(result.try_into()?),
            ContextMessageValueRecord::Image(img) => Self::Image(img.into()),
        })
    }
}

/// Repository-specific representation of ContextMessage
#[derive(Debug, Clone, Serialize)]
pub(super) struct ContextMessageRecord {
    message: ContextMessageValueRecord,
    #[serde(skip_serializing_if = "Option::is_none")]
    usage: Option<UsageRecord>,
}

// TODO: Move this deserialization logic into Conversation repo
impl<'de> Deserialize<'de> for ContextMessageRecord {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: serde::Deserializer<'de>,
    {
        #[derive(Deserialize)]
        #[serde(untagged)]
        enum ContextMessageParser {
            // Try new format first (with message field)
            Wrapper {
                message: ContextMessageValueRecord,
                usage: Option<UsageRecord>,
            },
            // Fall back to old format (direct ContextMessage)
            Direct(ContextMessageValueRecord),
        }

        // Deserialize through `serde_json::Value` first so we can defensively
        // drop stray variant keys that would otherwise brick the entire
        // conversation. Past corruption has injected empty objects like
        // `,"text":{}` alongside a real `tool` variant, which made the
        // externally-tagged enum unable to choose a variant.
        let value = serde_json::Value::deserialize(deserializer)?;
        let cleaned = strip_stray_variant_keys(value);

        match ContextMessageParser::deserialize(cleaned).map_err(serde::de::Error::custom)? {
            ContextMessageParser::Wrapper { message, usage } => {
                Ok(ContextMessageRecord { message, usage })
            }
            ContextMessageParser::Direct(message) => {
                Ok(ContextMessageRecord { message, usage: None })
            }
        }
    }
}

/// Variant tags recognised by `ContextMessageValueRecord`. When more than one
/// of these appears in the same object we keep the first variant that is a
/// non-empty object and successfully deserializes, and drop the rest. This
/// recovers from corruption that historically injected `,"text":{}` next to
/// a real `tool` variant without allowing malformed data to displace it.
const MESSAGE_VARIANT_KEYS: &[&str] = &["text", "tool", "image"];

fn strip_stray_variant_keys(value: serde_json::Value) -> serde_json::Value {
    match value {
        serde_json::Value::Object(mut map) => {
            // Wrapper format: { message: { text|tool|image: ... }, usage: ... }
            if let Some(serde_json::Value::Object(msg)) = map.get_mut("message")
                && drop_stray_keys_in_place(msg)
            {
                tracing::warn!(
                    target: "forge_repo.conversation",
                    "dropped stray variant key(s) from corrupted message wrapper"
                );
            }
            // Direct format: root object is the variant itself.
            if drop_stray_keys_in_place(&mut map) {
                tracing::warn!(
                    target: "forge_repo.conversation",
                    "dropped stray variant key(s) from corrupted message"
                );
            }
            serde_json::Value::Object(map)
        }
        other => other,
    }
}

/// Returns true if any keys were removed.
///
/// If one of the recognised variant keys (`text` / `tool` / `image`) is present,
/// every *other* key in the object is dropped — the variant payload is the only
/// valid content of a `ContextMessage`. This defends against historical
/// corruption that injected extra fields such as `"role": "system"` at the same
/// nesting level as a real `"text"` variant; serde's externally-tagged enum
/// rejects any sibling key and previously bricked the whole conversation.
fn drop_stray_keys_in_place(map: &mut serde_json::Map<String, serde_json::Value>) -> bool {
    let valid_variants: Vec<&str> = MESSAGE_VARIANT_KEYS
        .iter()
        .copied()
        .filter(|k| is_valid_variant(map.get(*k), k))
        .collect();
    if valid_variants.is_empty() {
        return false;
    }
    // Pick the first valid variant in declaration order.
    let keep = valid_variants
        .first()
        .copied()
        .expect("valid_variants is non-empty");

    // When a variant key is recognised, the variant payload is the *only*
    // valid content — strip every other sibling key (role, usage, etc.) before
    // handing the object to the externally-tagged deserializer.
    let original_keys: Vec<String> = map.keys().cloned().collect();
    let mut removed = false;
    for k in original_keys {
        if k != keep {
            map.remove(&k);
            removed = true;
        }
    }
    removed
}

fn is_valid_variant(value: Option<&serde_json::Value>, key: &str) -> bool {
    let Some(serde_json::Value::Object(payload)) = value else {
        return false;
    };
    if payload.is_empty() {
        return false;
    }

    let mut candidate = serde_json::Map::new();
    candidate.insert(key.to_owned(), serde_json::Value::Object(payload.clone()));
    serde_json::from_value::<ContextMessageValueRecord>(serde_json::Value::Object(candidate))
        .is_ok()
}

impl From<&forge_domain::MessageEntry> for ContextMessageRecord {
    fn from(msg: &forge_domain::MessageEntry) -> Self {
        Self {
            message: ContextMessageValueRecord::from(&msg.message),
            usage: msg.usage.as_ref().map(UsageRecord::from),
        }
    }
}

impl TryFrom<ContextMessageRecord> for forge_domain::MessageEntry {
    type Error = anyhow::Error;

    fn try_from(record: ContextMessageRecord) -> anyhow::Result<Self> {
        Ok(forge_domain::MessageEntry {
            message: record.message.try_into()?,
            usage: record.usage.map(Into::into),
        })
    }
}

/// Repository-specific representation of ToolDefinition
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(super) struct ToolDefinitionRecord {
    name: ToolNameRecord,
    description: String,
    input_schema: serde_json::Value,
}

impl From<&forge_domain::ToolDefinition> for ToolDefinitionRecord {
    fn from(def: &forge_domain::ToolDefinition) -> Self {
        Self {
            name: ToolNameRecord::from(&def.name),
            description: def.description.clone(),
            input_schema: serde_json::to_value(&def.input_schema).unwrap_or_default(),
        }
    }
}

impl TryFrom<ToolDefinitionRecord> for forge_domain::ToolDefinition {
    type Error = anyhow::Error;

    fn try_from(record: ToolDefinitionRecord) -> anyhow::Result<Self> {
        Ok(forge_domain::ToolDefinition {
            name: record.name.into(),
            description: record.description,
            input_schema: serde_json::from_value(record.input_schema)?,
        })
    }
}

/// Repository-specific representation of ToolChoice
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "PascalCase")]
pub(super) enum ToolChoiceRecord {
    None,
    Auto,
    Required,
    Call(ToolNameRecord),
}

impl From<&forge_domain::ToolChoice> for ToolChoiceRecord {
    fn from(choice: &forge_domain::ToolChoice) -> Self {
        match choice {
            forge_domain::ToolChoice::None => Self::None,
            forge_domain::ToolChoice::Auto => Self::Auto,
            forge_domain::ToolChoice::Required => Self::Required,
            forge_domain::ToolChoice::Call(name) => Self::Call(ToolNameRecord::from(name)),
        }
    }
}

impl From<ToolChoiceRecord> for forge_domain::ToolChoice {
    fn from(record: ToolChoiceRecord) -> Self {
        match record {
            ToolChoiceRecord::None => Self::None,
            ToolChoiceRecord::Auto => Self::Auto,
            ToolChoiceRecord::Required => Self::Required,
            ToolChoiceRecord::Call(name) => Self::Call(name.into()),
        }
    }
}

/// Repository-specific representation of Effort
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub(super) enum EffortRecord {
    None,
    Minimal,
    Low,
    Medium,
    High,
    XHigh,
    Max,
}

impl From<&forge_domain::Effort> for EffortRecord {
    fn from(effort: &forge_domain::Effort) -> Self {
        match effort {
            forge_domain::Effort::None => Self::None,
            forge_domain::Effort::Minimal => Self::Minimal,
            forge_domain::Effort::Low => Self::Low,
            forge_domain::Effort::Medium => Self::Medium,
            forge_domain::Effort::High => Self::High,
            forge_domain::Effort::XHigh => Self::XHigh,
            forge_domain::Effort::Max => Self::Max,
        }
    }
}

impl From<EffortRecord> for forge_domain::Effort {
    fn from(record: EffortRecord) -> Self {
        match record {
            EffortRecord::None => Self::None,
            EffortRecord::Minimal => Self::Minimal,
            EffortRecord::Low => Self::Low,
            EffortRecord::Medium => Self::Medium,
            EffortRecord::High => Self::High,
            EffortRecord::XHigh => Self::XHigh,
            EffortRecord::Max => Self::Max,
        }
    }
}

/// Repository-specific representation of ReasoningConfig
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(super) struct ReasoningConfigRecord {
    #[serde(skip_serializing_if = "Option::is_none")]
    effort: Option<EffortRecord>,
    #[serde(skip_serializing_if = "Option::is_none")]
    max_tokens: Option<usize>,
    #[serde(skip_serializing_if = "Option::is_none")]
    exclude: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    enabled: Option<bool>,
}

impl From<&forge_domain::ReasoningConfig> for ReasoningConfigRecord {
    fn from(config: &forge_domain::ReasoningConfig) -> Self {
        Self {
            effort: config.effort.as_ref().map(EffortRecord::from),
            max_tokens: config.max_tokens,
            exclude: config.exclude,
            enabled: config.enabled,
        }
    }
}

impl From<ReasoningConfigRecord> for forge_domain::ReasoningConfig {
    fn from(record: ReasoningConfigRecord) -> Self {
        forge_domain::ReasoningConfig {
            effort: record.effort.map(Into::into),
            max_tokens: record.max_tokens,
            exclude: record.exclude,
            enabled: record.enabled,
        }
    }
}

/// Repository-specific representation of Context
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(super) struct ContextRecord {
    #[serde(default, skip_serializing_if = "Option::is_none")]
    conversation_id: Option<String>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    initiator: Option<String>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    messages: Vec<ContextMessageRecord>,
    #[serde(default, skip_serializing_if = "Vec::is_empty")]
    tools: Vec<ToolDefinitionRecord>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    tool_choice: Option<ToolChoiceRecord>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    max_tokens: Option<usize>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    temperature: Option<f32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    top_p: Option<f32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    top_k: Option<u32>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    reasoning: Option<ReasoningConfigRecord>,
    #[serde(default, skip_serializing_if = "Option::is_none")]
    stream: Option<bool>,
}

impl From<&Context> for ContextRecord {
    fn from(context: &Context) -> Self {
        Self {
            conversation_id: context.conversation_id.as_ref().map(|id| id.into_string()),
            initiator: context.initiator.clone(),
            messages: context
                .messages
                .iter()
                .map(ContextMessageRecord::from)
                .collect(),
            tools: context
                .tools
                .iter()
                .map(ToolDefinitionRecord::from)
                .collect(),
            tool_choice: context.tool_choice.as_ref().map(ToolChoiceRecord::from),
            max_tokens: context.max_tokens,
            temperature: context.temperature.map(|t| t.value()),
            top_p: context.top_p.map(|t| t.value()),
            top_k: context.top_k.map(|t| t.value()),
            reasoning: context.reasoning.as_ref().map(ReasoningConfigRecord::from),
            stream: context.stream,
        }
    }
}

impl TryFrom<ContextRecord> for Context {
    type Error = anyhow::Error;

    fn try_from(record: ContextRecord) -> anyhow::Result<Self> {
        let conversation_id = record
            .conversation_id
            .map(ConversationId::parse)
            .transpose()?;

        tracing::debug!(
            "Deserializing context for conversation: {:?}",
            conversation_id
        );

        // Convert messages from repository records to domain types
        let messages: Result<Vec<_>, _> = record
            .messages
            .into_iter()
            .enumerate()
            .map(|(idx, v)| {
                v.try_into().map_err(|e: anyhow::Error| {
                    eprintln!(
                        "Failed to deserialize message {} for conversation {:?}: {}",
                        idx, conversation_id, e
                    );
                    e
                })
            })
            .collect();

        let tools: Result<Vec<_>, _> = record.tools.into_iter().map(TryInto::try_into).collect();

        Ok(Context {
            conversation_id,
            initiator: record.initiator,
            messages: messages?,
            tools: tools?,
            tool_choice: record.tool_choice.map(Into::into),
            max_tokens: record.max_tokens,
            temperature: record
                .temperature
                .map(forge_domain::Temperature::new_unchecked),
            top_p: record.top_p.map(forge_domain::TopP::new_unchecked),
            top_k: record.top_k.map(forge_domain::TopK::new_unchecked),
            reasoning: record.reasoning.map(Into::into),
            stream: record.stream,
            response_format: None,
        })
    }
}

/// Repository-specific representation of FileOperation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(super) struct FileChangeMetricsRecord {
    lines_added: u64,
    lines_removed: u64,
    #[serde(skip_serializing_if = "Option::is_none")]
    content_hash: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    tool: Option<forge_domain::ToolKind>,
}

impl From<&forge_domain::FileOperation> for FileChangeMetricsRecord {
    fn from(metrics: &forge_domain::FileOperation) -> Self {
        Self {
            lines_added: metrics.lines_added,
            lines_removed: metrics.lines_removed,
            content_hash: metrics.content_hash.clone(),
            tool: Some(metrics.tool),
        }
    }
}

impl From<FileChangeMetricsRecord> for forge_domain::FileOperation {
    fn from(record: FileChangeMetricsRecord) -> Self {
        // Use Write as default tool for old records without tool field
        let tool = record.tool.unwrap_or(forge_domain::ToolKind::Write);
        Self::new(tool)
            .lines_added(record.lines_added)
            .lines_removed(record.lines_removed)
            .content_hash(record.content_hash)
    }
}

/// Represents either a single file operation or array (for backward
/// compatibility)
#[derive(Debug, Clone, Serialize, Deserialize, derive_more::From)]
#[serde(untagged)]
pub(super) enum FileOperationOrArray {
    Single(FileChangeMetricsRecord),
    Array(Vec<FileChangeMetricsRecord>),
}

/// Repository-specific representation of Metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub(super) struct MetricsRecord {
    started_at: Option<chrono::DateTime<chrono::Utc>>,
    files_changed: std::collections::HashMap<String, FileOperationOrArray>,
    #[serde(default, skip_serializing_if = "std::collections::HashSet::is_empty")]
    files_accessed: std::collections::HashSet<String>,
}

impl From<&forge_domain::Metrics> for MetricsRecord {
    fn from(metrics: &forge_domain::Metrics) -> Self {
        Self {
            started_at: metrics.started_at,
            files_changed: metrics
                .file_operations
                .iter()
                .map(|(path, file_metrics)| {
                    (
                        path.clone(),
                        FileOperationOrArray::Single(file_metrics.into()),
                    )
                })
                .collect(),
            files_accessed: metrics.files_accessed.clone(),
        }
    }
}

impl From<MetricsRecord> for forge_domain::Metrics {
    fn from(record: MetricsRecord) -> Self {
        let file_operations: std::collections::HashMap<String, forge_domain::FileOperation> =
            record
                .files_changed
                .into_iter()
                .filter_map(|(path, file_record)| {
                    let operation = match file_record {
                        // If it's an array, take the last operation (most recent)
                        FileOperationOrArray::Array(mut arr) if !arr.is_empty() => {
                            arr.pop().unwrap().into()
                        }
                        // If it's a single object, use it directly
                        FileOperationOrArray::Single(record) => record.into(),
                        // If it's an empty array, skip this file
                        FileOperationOrArray::Array(_) => return None,
                    };
                    Some((path, operation))
                })
                .collect();

        // Use persisted files_accessed if available, otherwise build from Read
        // operations
        let files_accessed = if record.files_accessed.is_empty() {
            // Legacy data: build from Read operations
            file_operations
                .iter()
                .filter(|(_, op)| op.tool == forge_domain::ToolKind::Read)
                .map(|(path, _)| path.clone())
                .collect()
        } else {
            // Use persisted set
            record.files_accessed
        };

        Self {
            started_at: record.started_at,
            file_operations,
            files_accessed,
            todos: Vec::new(),
        }
    }
}

/// Database model for conversations table.
///
/// Column set mirrors `crate::database::schema::conversations` 1:1 so that
/// Diesel can `select(ConversationRecord::as_select())` / `as_changeset()`
/// against the table (or the read-only `conversations_all` view) without an
/// explicit column list. Fields added after P2.5 (`context_zstd`,
/// `is_compressed`, `cwd`, `parent_id`, `source`, `message_count`,
/// `intent_state`, `extracted_at`, `memory_id`, `intent_hash`) are
/// `Option<...>` so legacy rows written by older migrations deserialize
/// cleanly.
#[derive(
    Debug,
    Clone,
    diesel::Queryable,
    diesel::Selectable,
    diesel::Insertable,
    diesel::AsChangeset,
    diesel::QueryableByName,
)]
#[diesel(table_name = crate::database::schema::conversations)]
#[diesel(check_for_backend(diesel::sqlite::Sqlite))]
pub(super) struct ConversationRecord {
    pub conversation_id: String,
    pub title: Option<String>,
    /// Nullable so legacy rows from older `conversations` tables (which
    /// pre-date the `workspace_id` column) deserialize cleanly through the
    /// `conversations_all` VIEW. Local writes always populate this column.
    pub workspace_id: Option<i64>,
    pub context: Option<String>,
    pub created_at: chrono::NaiveDateTime,
    pub updated_at: Option<chrono::NaiveDateTime>,
    pub metrics: Option<String>,
    pub parent_id: Option<String>,
    pub source: Option<String>,
    #[diesel(column_name = cwd)]
    pub cwd: Option<String>,
    #[diesel(column_name = message_count)]
    pub message_count: Option<i32>,
    pub intent_state: String,
    pub extracted_at: Option<chrono::NaiveDateTime>,
    pub memory_id: Option<String>,
    pub intent_hash: Option<String>,
    pub context_zstd: Option<Vec<u8>>,
    pub is_compressed: i32,
}

impl ConversationRecord {
    /// Creates a new ConversationRecord from a Conversation domain object.
    ///
    /// The context is **compressed** via `crate::codec::compress` and stored
    /// in `context_zstd` with `is_compressed = 1`; the plain-text `context`
    /// column is left NULL. This matches the on-disk format expected by
    /// the search / picker paths, which decompress on demand. Callers that
    /// want a plain-text row (e.g. snapshot export) can overwrite the fields
    /// after construction.
    ///
    /// Fields the domain `Conversation` does not carry (`parent_id`, `source`,
    /// `cwd`, `intent_state`, etc.) default to safe on-disk values: NULL /
    /// empty / "pending". Callers that need to persist richer state can
    /// populate them directly on the returned struct.
    pub fn new(
        conversation: forge_domain::Conversation,
        workspace_id: forge_domain::WorkspaceHash,
    ) -> Self {
        let created_at = conversation.metadata.created_at.naive_utc();
        let message_count = conversation
            .context
            .as_ref()
            .map(|ctx| ctx.messages.len() as i32);

        let (context, context_zstd, is_compressed, updated_at) =
            Self::encode_context(conversation.context.as_ref());
        let metrics_record = MetricsRecord::from(&conversation.metrics);
        let metrics = serde_json::to_string(&metrics_record).ok();

        Self {
            conversation_id: conversation.id.into_string(),
            title: conversation.title.clone(),
            context,
            created_at,
            updated_at,
            workspace_id: Some(workspace_id.id() as i64),
            metrics,
            parent_id: None,
            source: None,
            cwd: None,
            message_count,
            intent_state: "pending".to_string(),
            extracted_at: None,
            memory_id: None,
            intent_hash: None,
            context_zstd,
            is_compressed,
        }
    }

    /// Compress the conversation context to the on-disk wire format.
    ///
    /// Returns `(plaintext_column, zstd_blob, is_compressed_flag, updated_at)`.
    /// Empty contexts (no messages, no initiator) compress to `(None, None, 0,
    /// None)` so existing rows stay NULL. Non-empty contexts are serialized
    /// to the record DTO and stored **only** in `context_zstd` with
    /// `is_compressed = 1`. The plain `context` column stays NULL so search /
    /// picker paths can rely on the compressed-or-empty signal without
    /// cross-checking two columns.
    fn encode_context(
        context: Option<&forge_domain::Context>,
    ) -> (
        Option<String>,
        Option<Vec<u8>>,
        i32,
        Option<chrono::NaiveDateTime>,
    ) {
        let Some(ctx) = context else {
            return (None, None, 0, None);
        };
        if ctx.messages.is_empty() && ctx.initiator.is_none() {
            return (None, None, 0, None);
        }
        let record = ContextRecord::from(ctx);
        let Ok(json) = serde_json::to_string(&record) else {
            return (None, None, 0, None);
        };
        match crate::codec::compress(&json) {
            Ok(zstd_bytes) => (
                None,
                Some(zstd_bytes),
                1,
                Some(chrono::Utc::now().naive_utc()),
            ),
            Err(_) => (Some(json), None, 0, Some(chrono::Utc::now().naive_utc())),
        }
    }

    /// Creates a "ref" record used by `upsert_conversation_ref`.
    ///
    /// Unlike `ConversationRecord::new`, the ref path **does** propagate the
    /// incoming conversation's context payload (compressed via the same
    /// `encode_context` helper). The "ref" name is historical — it stems from
    /// a pre-P2.5 era when this method only carried the conversation id /
    /// title for shell-style reference rows. After P2.5 the path is used as
    /// the "incoming context wins over existing row" upsert: callers
    /// expecting plain-text semantics pass an empty `Context`; callers
    /// expecting compressed semantics let `encode_context` do the work.
    ///
    /// Tests like `ref_upsert_replaces_existing_plain_context_with_incoming_compressed_context`
    /// assert this contract — the ref upsert **replaces** any existing
    /// context with the incoming payload (compressed or empty).
    pub fn new_ref(
        conversation: &forge_domain::Conversation,
        workspace_id: forge_domain::WorkspaceHash,
    ) -> Self {
        let (context, context_zstd, is_compressed, updated_at) =
            Self::encode_context(conversation.context.as_ref());
        let metrics_record = MetricsRecord::from(&conversation.metrics);
        let metrics = serde_json::to_string(&metrics_record).ok();
        let message_count = conversation
            .context
            .as_ref()
            .map(|ctx| ctx.messages.len() as i32);

        Self {
            conversation_id: conversation.id.into_string(),
            title: conversation.title.clone(),
            workspace_id: Some(workspace_id.id() as i64),
            context,
            created_at: conversation.metadata.created_at.naive_utc(),
            updated_at,
            metrics,
            parent_id: None,
            source: None,
            cwd: None,
            message_count,
            intent_state: "pending".to_string(),
            extracted_at: None,
            memory_id: None,
            intent_hash: None,
            context_zstd,
            is_compressed,
        }
    }
}

/// Slim projection of `ConversationRecord` for the picker / recent-list path.
///
/// `get_parent_conversations_lite` only needs columns that summarise a
/// conversation for display: id, title, workspace, updated_at, plus the
/// compressed-context hints that the search code reuses for LIKE fallback.
/// Defining a dedicated Diesel-deserializable struct keeps the picker query
/// free of unused columns (context JSON can be megabytes per row) without
/// forcing the full `ConversationRecord` to be loaded.
///
/// `table_name` points at the read-only `conversations_all` view (not the
/// local `conversations` table) because the picker query reads through
/// `conversations_all::table` — the VIEW that UNIONs the local table with
/// the legacy DB ATTACH. Diesel ties `Selectable` impls to a single table,
/// so the picker query reads via `ConversationRecordLite::as_select()`
/// against `conversations_all::table`.
#[derive(Debug, diesel::Queryable, diesel::Selectable, Clone)]
#[diesel(table_name = crate::database::schema::conversations_all)]
#[diesel(check_for_backend(diesel::sqlite::Sqlite))]
pub(super) struct ConversationRecordLite {
    pub conversation_id: String,
    pub title: Option<String>,
    /// Nullable on disk; the picker filters rows via SQL `WHERE workspace_id
    /// = ?` rather than reading this column into Rust.
    #[allow(dead_code)]
    pub workspace_id: Option<i64>,
    pub updated_at: Option<chrono::NaiveDateTime>,
    #[diesel(column_name = cwd)]
    pub cwd: Option<String>,
    #[diesel(column_name = message_count)]
    pub message_count: Option<i32>,
    pub parent_id: Option<String>,
    /// Read from the DB; consumed by SQL `WHERE` filters but not by the
    /// picker projection itself.
    #[allow(dead_code)]
    pub source: Option<String>,
    /// Read from the DB; consumed by SQL `WHERE` filters but not by the
    /// picker projection itself.
    #[allow(dead_code)]
    pub intent_state: String,
    pub created_at: chrono::NaiveDateTime,
}

impl From<ConversationRecordLite> for forge_domain::ConversationSummary {
    fn from(record: ConversationRecordLite) -> Self {
        let id = forge_domain::ConversationId::parse(record.conversation_id)
            .unwrap_or_else(|_| forge_domain::ConversationId::generate());
        let parent_id = record
            .parent_id
            .as_deref()
            .and_then(|raw| forge_domain::ConversationId::parse(raw).ok());
        Self {
            id,
            title: record.title,
            parent_id,
            created_at: record.created_at.and_utc(),
            updated_at: record.updated_at.map(|updated_at| updated_at.and_utc()),
            message_count: record.message_count,
            cwd: record.cwd,
        }
    }
}

impl TryFrom<ConversationRecord> for forge_domain::Conversation {
    type Error = anyhow::Error;

    fn try_from(record: ConversationRecord) -> anyhow::Result<Self> {
        let conversation_id = record.conversation_id.clone();
        let id = ConversationId::parse(conversation_id.clone())
            .with_context(|| format!("Failed to parse conversation ID: {}", conversation_id))?;

        let context = if record.is_compressed == 1 {
            // Compressed on-disk format: context lives in `context_zstd`.
            let Some(bytes) = record.context_zstd.as_ref() else {
                anyhow::bail!(
                    "Conversation {} marked compressed but has no context_zstd blob",
                    conversation_id
                );
            };
            let json = crate::codec::decompress(bytes).with_context(|| {
                format!(
                    "Failed to decompress context for conversation {}",
                    conversation_id
                )
            })?;
            let record = serde_json::from_str::<ContextRecord>(&json).with_context(|| {
                format!(
                    "Failed to deserialize decompressed context for conversation {}",
                    conversation_id
                )
            })?;
            Some(record.try_into().with_context(|| {
                format!(
                    "Failed to convert context record to domain type for conversation {}",
                    conversation_id
                )
            })?)
        } else if let Some(context_str) = record.context {
            // Legacy plain-text format (rows written before P2.5).
            Some(
                serde_json::from_str::<ContextRecord>(&context_str)
                    .with_context(|| {
                        format!(
                            "Failed to deserialize context for conversation {}",
                            conversation_id
                        )
                    })?
                    .try_into()
                    .with_context(|| {
                        format!(
                            "Failed to convert context record to domain type for conversation {}",
                            conversation_id
                        )
                    })?,
            )
        } else {
            None
        };

        // Deserialize metrics using MetricsRecord for compile-time safety
        let metrics = record
            .metrics
            .and_then(|m| serde_json::from_str::<MetricsRecord>(&m).ok())
            .map(forge_domain::Metrics::from)
            .unwrap_or_else(|| {
                forge_domain::Metrics::default().started_at(record.created_at.and_utc())
            });

        let parent_id = record
            .parent_id
            .as_deref()
            .and_then(|raw| forge_domain::ConversationId::parse(raw).ok());

        Ok(forge_domain::Conversation::new(id)
            .context(context)
            .title(record.title)
            .metrics(metrics)
            .parent_id(parent_id)
            .metadata(
                forge_domain::MetaData::new(record.created_at.and_utc())
                    .updated_at(record.updated_at.map(|updated_at| updated_at.and_utc())),
            ))
    }
}

#[cfg(test)]
mod tests {
    use pretty_assertions::assert_eq;

    use super::*;

    #[test]
    fn deserialize_drops_stray_empty_text_alongside_tool() {
        // Reproduces the corruption that caused
        // `data did not match any variant of untagged enum ContextMessageParser`:
        // a real tool message wrapper with an injected `,"text":{}` field.
        let corrupted = r#"{
            "message": {
                "tool": {
                    "name": "shell",
                    "call_id": "call_abc",
                    "output": { "is_error": false, "values": [{"text": "ok"}] }
                },
                "text": {}
            }
        }"#;
        let record: ContextMessageRecord = serde_json::from_str(corrupted)
            .expect("deserializer should drop stray text key and recover");
        match record.message {
            ContextMessageValueRecord::Tool(_) => {}
            other => panic!("expected Tool variant, got {other:?}"),
        }
    }

    #[test]
    fn deserialize_drops_stray_empty_tool_alongside_text() {
        // Mirror of the above: real text variant with stray empty tool key.
        let corrupted = r#"{
            "message": {
                "text": { "role": "Assistant", "content": "hi" },
                "tool": {}
            }
        }"#;
        let record: ContextMessageRecord = serde_json::from_str(corrupted)
            .expect("deserializer should drop stray tool key and recover");
        match record.message {
            ContextMessageValueRecord::Text(_) => {}
            other => panic!("expected Text variant, got {other:?}"),
        }
    }

    #[test]
    fn deserialize_keeps_non_empty_variant() {
        // When both variant objects are non-empty, prefer the first one
        // declared in `MESSAGE_VARIANT_KEYS`.
        let corrupted = r#"{
            "message": {
                "text": { "role": "Assistant", "content": "real" },
                "tool": {
                    "name": "shell",
                    "call_id": "call_abc",
                    "output": { "is_error": false, "values": [{"text": "should-be-dropped"}] }
                }
            }
        }"#;
        let record: ContextMessageRecord =
            serde_json::from_str(corrupted).expect("deserializer should keep text variant");
        match record.message {
            ContextMessageValueRecord::Text(_) => {}
            other => panic!("expected Text variant, got {other:?}"),
        }
    }

    #[test]
    fn deserialize_clean_message_still_works() {
        let clean = r#"{
            "message": {
                "tool": {
                    "name": "shell",
                    "call_id": "call_abc",
                    "output": { "is_error": false, "values": [{"text": "ok"}] }
                }
            }
        }"#;
        let record: ContextMessageRecord =
            serde_json::from_str(clean).expect("clean message must still deserialize");
        match record.message {
            ContextMessageValueRecord::Tool(_) => {}
            other => panic!("expected Tool variant, got {other:?}"),
        }
    }

    #[test]
    fn deserialize_ignores_null_variant_when_tool_is_valid() {
        let corrupted = r#"{
            "message": {
                "text": null,
                "tool": {
                    "name": "shell",
                    "call_id": "call_abc",
                    "output": { "is_error": false, "values": [{"text": "ok"}] }
                }
            }
        }"#;
        let actual: ContextMessageRecord = serde_json::from_str(corrupted).unwrap();
        assert!(matches!(actual.message, ContextMessageValueRecord::Tool(_)));
    }

    #[test]
    fn deserialize_ignores_scalar_variant_when_tool_is_valid() {
        let corrupted = r#"{
            "message": {
                "text": "invalid",
                "tool": {
                    "name": "shell",
                    "call_id": "call_abc",
                    "output": { "is_error": false, "values": [{"text": "ok"}] }
                }
            }
        }"#;
        let actual: ContextMessageRecord = serde_json::from_str(corrupted).unwrap();
        assert!(matches!(actual.message, ContextMessageValueRecord::Tool(_)));
    }

    #[test]
    fn deserialize_ignores_malformed_non_empty_variant_when_tool_is_valid() {
        let corrupted = r#"{
            "message": {
                "text": { "role": "not-a-role", "content": 42 },
                "tool": {
                    "name": "shell",
                    "call_id": "call_abc",
                    "output": { "is_error": false, "values": [{"text": "ok"}] }
                }
            }
        }"#;
        let actual: ContextMessageRecord = serde_json::from_str(corrupted).unwrap();
        assert!(matches!(actual.message, ContextMessageValueRecord::Tool(_)));
    }

    #[test]
    fn deserialize_drops_stray_role_alongside_text() {
        // Reproduces the corruption seen on 48 system messages where the
        // outer `message` wrapper contains both `"role": "system"` and a real
        // `"text"` variant. Serde's externally-tagged enum rejects any sibling
        // key inside the variant payload, so without recovery the entire
        // conversation fails to deserialize.
        let corrupted = r#"{
            "message": {
                "role": "system",
                "text": {
                    "role": "System",
                    "content": "you are a helpful assistant"
                }
            }
        }"#;
        let record: ContextMessageRecord = serde_json::from_str(corrupted)
            .expect("deserializer should drop stray role key and recover text message");
        match record.message {
            ContextMessageValueRecord::Text(msg) => {
                assert_eq!(msg.role, RoleRecord::System);
                assert!(msg.content.contains("helpful"));
            }
            other => panic!("expected Text variant, got {other:?}"),
        }
    }

    #[test]
    fn deserialize_drops_stray_role_alongside_tool() {
        // Same class of corruption but on a tool message wrapper.
        let corrupted = r#"{
            "message": {
                "role": "system",
                "tool": {
                    "name": "shell",
                    "call_id": "call_abc",
                    "output": { "is_error": false, "values": [{"text": "ok"}] }
                }
            }
        }"#;
        let record: ContextMessageRecord = serde_json::from_str(corrupted)
            .expect("deserializer should drop stray role key on tool messages");
        match record.message {
            ContextMessageValueRecord::Tool(_) => {}
            other => panic!("expected Tool variant, got {other:?}"),
        }
    }

    #[test]
    fn deserialize_drops_multiple_stray_keys_alongside_variant() {
        // Real corruption had several extra fields next to the variant;
        // ensure the hardener drops them all and keeps only the variant.
        let corrupted = r#"{
            "message": {
                "role": "system",
                "model": "openrouter/free",
                "text": {
                    "role": "System",
                    "content": "summary",
                    "model": "openrouter/free"
                }
            }
        }"#;
        let record: ContextMessageRecord = serde_json::from_str(corrupted)
            .expect("deserializer should drop role+model siblings of the text variant");
        match record.message {
            ContextMessageValueRecord::Text(msg) => {
                assert_eq!(msg.role, RoleRecord::System);
            }
            other => panic!("expected Text variant, got {other:?}"),
        }
    }

    #[test]
    fn deserialize_full_corrupted_context_recovers() {
        // Verifies the deserializer recovers the original on-disk corruption
        // that produced
        //     `data did not match any variant of untagged enum
        //      ContextMessageParser at line 1 column 30753`
        // for conversation 2edac8f2-359e-4157-946c-df4c98bbe534. The fixture
        // is a snippet with multiple tool messages each carrying an injected
        // `,"text":{}` field.
        let fixture = r#"{
            "messages": [
                {"message": {"text": {"role": "User", "content": "hi"}}},
                {"message": {"tool": {
                    "name": "shell",
                    "call_id": "call_1",
                    "output": {"is_error": false, "values": [{"text": "first"}]}
                }, "text": {}}},
                {"message": {"tool": {
                    "name": "shell",
                    "call_id": "call_2",
                    "output": {"is_error": false, "values": [{"text": "second"}]}
                }, "text": {}}},
                {"message": {"text": {"role": "Assistant", "content": "done"}}}
            ],
            "tools": []
        }"#;
        let record: ContextRecord = serde_json::from_str(fixture)
            .expect("full context with multiple stray text keys must recover");
        assert_eq!(record.messages.len(), 4);
        // Spot-check: tool messages round-tripped as Tool variants, not Text.
        assert!(matches!(
            record.messages[1].message,
            ContextMessageValueRecord::Tool(_)
        ));
        assert!(matches!(
            record.messages[2].message,
            ContextMessageValueRecord::Tool(_)
        ));
    }

    #[test]
    fn deserialize_real_on_disk_corruption_recovers() {
        // End-to-end check against the actual corrupted conversation snapshot
        // salvaged from `~/.forge/.forge.db.bak-pre-ctxparserfix-20260903-180015`.
        // The fixture path is configurable via the `FORGE_CORRUPTION_FIXTURE`
        // env var; the test is skipped when the file isn't present so CI
        // environments without the artifact don't fail.
        let path = std::env::var("FORGE_CORRUPTION_FIXTURE")
            .unwrap_or_else(|_| "/tmp/orig_corrupted_ctx.txt".to_string());
        if !std::path::Path::new(&path).exists() {
            eprintln!("skipping: fixture not found at {path}");
            return;
        }

        let raw =
            std::fs::read_to_string(&path).unwrap_or_else(|e| panic!("failed to read {path}: {e}"));

        // Sanity: the on-disk corruption is still present.
        let compact = raw.split_whitespace().collect::<String>();
        assert!(
            compact.contains("\"tool\":{"),
            "fixture should contain tool messages"
        );
        let stray = compact.matches("\"text\":{}").count();
        assert!(
            stray >= 1,
            "fixture should still contain at least one stray `\"text\": {{}}` \
             (got {stray}); re-create it from the .bak-pre-ctxparserfix-* DB"
        );

        // This is the call that used to fail with
        //   `data did not match any variant of untagged enum ContextMessageParser
        //    at line 1 column 30753`.
        let record: ContextRecord = serde_json::from_str(&raw).unwrap_or_else(|e| {
            panic!("hardened deserializer must recover real on-disk corruption, got: {e}");
        });

        // Conversation 2edac8f2-... had 20 messages: 11 text + 9 tool.
        assert_eq!(
            record.messages.len(),
            20,
            "expected 20 messages after recovery, got {}",
            record.messages.len()
        );

        let mut n_text = 0usize;
        let mut n_tool = 0usize;
        for m in &record.messages {
            match m.message {
                ContextMessageValueRecord::Text(_) => n_text += 1,
                ContextMessageValueRecord::Tool(_) => n_tool += 1,
                ContextMessageValueRecord::Image(_) => {}
            }
        }
        assert_eq!(n_text + n_tool, 20);
        assert!(n_tool >= 1, "at least one tool message must round-trip");

        eprintln!(
            "recovered {n_text} text + {n_tool} tool messages from {path} ({} bytes)",
            raw.len()
        );
    }
}
