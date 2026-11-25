use derive_more::derive::Display;
use derive_setters::Setters;
use fake::Dummy;
use schemars::JsonSchema;
use serde::{Deserialize, Serialize};
use strum_macros::EnumString;

/// Represents input modalities that a model can accept
#[derive(
    Debug, Clone, Serialize, Deserialize, PartialEq, Eq, Hash, EnumString, JsonSchema, Dummy,
)]
#[serde(rename_all = "lowercase")]
#[strum(serialize_all = "lowercase", ascii_case_insensitive)]
pub enum InputModality {
    /// Text input (all models support this)
    Text,
    /// Image input (vision-capable models)
    Image,
}

/// Default input modalities when not specified (text-only)
fn default_input_modalities() -> Vec<InputModality> {
    vec![InputModality::Text]
}

#[derive(Clone, Debug, PartialEq, Deserialize, Serialize, Setters, JsonSchema, Dummy)]
#[setters(strip_option)]
pub struct Model {
    pub id: ModelId,
    pub name: Option<String>,
    pub description: Option<String>,
    pub context_length: Option<u64>,
    // TODO: add provider information to the model
    pub tools_supported: Option<bool>,
    /// Whether the model supports parallel tool calls
    pub supports_parallel_tool_calls: Option<bool>,
    /// Whether the model supports reasoning
    pub supports_reasoning: Option<bool>,
    /// Input modalities supported by the model (defaults to text-only)
    #[serde(default = "default_input_modalities")]
    pub input_modalities: Vec<InputModality>,
}

#[derive(Default, Debug, Clone, Serialize, Deserialize)]
pub struct Parameters {
    pub tool_supported: bool,
}

impl Parameters {
    pub fn new(tool_supported: bool) -> Self {
        Self { tool_supported }
    }
}

#[derive(Clone, Debug, Deserialize, PartialEq, Serialize, Hash, Eq, Display, JsonSchema, Dummy)]
#[serde(transparent)]
pub struct ModelId(String);

impl ModelId {
    pub fn new<T: Into<String>>(id: T) -> Self {
        Self(id.into())
    }
}

impl Model {
    /// Creates a new `Model` with the given id and default values for all other
    /// fields.
    pub fn new(id: impl Into<ModelId>) -> Self {
        Self {
            id: id.into(),
            name: None,
            description: None,
            context_length: None,
            tools_supported: None,
            supports_parallel_tool_calls: None,
            supports_reasoning: None,
            input_modalities: default_input_modalities(),
        }
    }

    /// Merges live server-side models with curated metadata.
    ///
    /// Every live model produces an entry in the result, in the order the
    /// server returned them. Curated entries whose id matches a live entry
    /// **fill only the `None` gaps** on the live model — server-side values
    /// are authoritative for fields the server actually returned, and
    /// curated data only contributes when the server left a field unset
    /// (so callers that already know the metadata locally do not lose it
    /// just because the server omitted it).
    ///
    /// Curated entries whose id is **not** in the live list are appended
    /// after the live entries so metadata-only models (e.g. those gated by
    /// beta flags the provider does not advertise) remain selectable.
    ///
    /// Live entries with duplicate ids are deduplicated: the first-seen
    /// entry wins. The live-list boundary is therefore the single dedup
    /// point and the curated merge afterward only sees unique ids.
    pub fn merge_live(live: Vec<Model>, curated: Vec<Model>) -> Vec<Self> {
        // Deduplicate live entries by id, first-seen wins. Order in the
        // result list mirrors the order in which they appeared in `live`,
        // because SQLite (and the OpenAI/Anthropic/Google providers) all
        // stream models in recency order.
        let mut seen = std::collections::HashSet::new();
        let mut merged: Vec<Self> = live
            .into_iter()
            .filter(|m| seen.insert(m.id.clone()))
            .map(|mut live_model| {
                // Curated overlay: only fill None gaps on the live model.
                // Server-side values are authoritative.
                if let Some(curated_model) = curated.iter().find(|m| m.id == live_model.id) {
                    if live_model.name.is_none() {
                        live_model.name = curated_model.name.clone();
                    }
                    if live_model.description.is_none() {
                        live_model.description = curated_model.description.clone();
                    }
                    if live_model.context_length.is_none() {
                        live_model.context_length = curated_model.context_length;
                    }
                    if live_model.tools_supported.is_none() {
                        live_model.tools_supported = curated_model.tools_supported;
                    }
                    if live_model.supports_parallel_tool_calls.is_none() {
                        live_model.supports_parallel_tool_calls =
                            curated_model.supports_parallel_tool_calls;
                    }
                    if live_model.supports_reasoning.is_none() {
                        live_model.supports_reasoning = curated_model.supports_reasoning;
                    }
                    if live_model.input_modalities == default_input_modalities()
                        && !curated_model.input_modalities.is_empty()
                    {
                        live_model.input_modalities = curated_model.input_modalities.clone();
                    }
                }
                live_model
            })
            .collect();

        // Append curated entries not already in the live list.
        for curated_model in curated {
            if !merged.iter().any(|m| m.id == curated_model.id) {
                merged.push(curated_model);
            }
        }
        merged
    }
}

impl From<String> for ModelId {
    fn from(value: String) -> Self {
        ModelId(value)
    }
}

impl From<&str> for ModelId {
    fn from(value: &str) -> Self {
        ModelId(value.to_string())
    }
}

impl ModelId {
    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl std::str::FromStr for ModelId {
    type Err = std::convert::Infallible;

    fn from_str(s: &str) -> Result<Self, Self::Err> {
        Ok(ModelId(s.to_string()))
    }
}

#[cfg(test)]
mod merge_live_tests {
    use super::*;

    #[test]
    fn merge_live_emits_one_entry_per_live_id_with_default_metadata() {
        let live = vec![Model::new("a"), Model::new("b")];
        let merged = Model::merge_live(live, vec![]);

        assert_eq!(merged.len(), 2);
        assert_eq!(merged[0].id.as_str(), "a");
        assert_eq!(merged[1].id.as_str(), "b");
        assert_eq!(merged[0].context_length, None);
        assert_eq!(merged[0].tools_supported, None);
        assert_eq!(merged[0].input_modalities, vec![InputModality::Text]);
    }

    #[test]
    fn merge_live_preserves_server_metadata_and_fills_curated_gaps() {
        // Live model has a server-provided name; curated has its own name.
        // Server-side value wins.
        let live = Model::new("a").name("Live Name".to_string());
        // Curated has description + tools_supported but no name field.
        let curated = Model::new("a")
            .name("Curated Name".to_string())
            .description("Live-free descriptor".to_string())
            .tools_supported(true);

        let merged = Model::merge_live(vec![live], vec![curated]);

        assert_eq!(merged.len(), 1);
        assert_eq!(
            merged[0].name.as_deref(),
            Some("Live Name"),
            "server-side name is authoritative, curated is ignored"
        );
        assert_eq!(
            merged[0].description.as_deref(),
            Some("Live-free descriptor"),
            "curated description fills the None gap"
        );
        assert_eq!(
            merged[0].tools_supported,
            Some(true),
            "curated tools_supported fills the None gap"
        );
    }

    #[test]
    fn merge_live_overlays_curated_metadata_onto_matching_live_id() {
        let curated = Model::new("a")
            .name("Alpha".to_string())
            .context_length(131072)
            .tools_supported(true)
            .supports_reasoning(true)
            .input_modalities(vec![InputModality::Text, InputModality::Image]);

        let merged = Model::merge_live(vec![Model::new("a")], vec![curated]);

        assert_eq!(merged.len(), 1);
        assert_eq!(merged[0].id.as_str(), "a");
        assert_eq!(merged[0].name.as_deref(), Some("Alpha"));
        assert_eq!(merged[0].context_length, Some(131072));
        assert_eq!(merged[0].tools_supported, Some(true));
        assert_eq!(merged[0].supports_reasoning, Some(true));
        assert_eq!(
            merged[0].input_modalities,
            vec![InputModality::Text, InputModality::Image]
        );
    }

    #[test]
    fn merge_live_appends_curated_entries_missing_from_live_list() {
        let curated_beta = Model::new("beta-only")
            .name("Beta".to_string())
            .context_length(8192);

        let merged = Model::merge_live(vec![Model::new("a")], vec![curated_beta]);

        assert_eq!(merged.len(), 2);
        assert_eq!(merged[0].id.as_str(), "a");
        assert_eq!(merged[1].id.as_str(), "beta-only");
        assert_eq!(merged[1].context_length, Some(8192));
    }

    #[test]
    fn merge_live_deduplicates_curated_entries_that_already_match_live_ids() {
        let curated = Model::new("a").name("Alpha".to_string());

        let merged = Model::merge_live(vec![Model::new("a")], vec![curated]);

        // "a" appears once in the merged result, not twice.
        assert_eq!(merged.len(), 1);
        assert_eq!(merged[0].id.as_str(), "a");
    }

    #[test]
    fn merge_live_dedupes_duplicate_live_ids_first_seen_wins() {
        // Real provider responses occasionally include the same id twice
        // (e.g. across regional endpoints). Server-side dedup happens here.
        let live = vec![
            Model::new("alpha").name("Alpha v1".to_string()),
            Model::new("alpha").name("Alpha v2".to_string()),
        ];
        let merged = Model::merge_live(live, vec![]);
        assert_eq!(merged.len(), 1, "duplicate live ids collapsed to one");
        assert_eq!(
            merged[0].name.as_deref(),
            Some("Alpha v1"),
            "first-seen live entry wins"
        );
    }
}
