//! Router for OmniRoute Core
//!
//! Handles routing of LLM requests to appropriate providers based on model selection.

use crate::error::{Error, Result};
use crate::providers::MockProvider;
use crate::types::{ModelList, ProviderConfig};
use std::collections::HashMap;
use std::sync::Arc;
use tracing::{debug, info, instrument};

/// Main router for handling LLM requests
#[derive(Clone)]
pub struct Router {
    /// Registered providers mapped by name
    providers: HashMap<String, Arc<dyn crate::providers::LLMProvider>>,
    /// Configuration for each provider
    configs: HashMap<String, ProviderConfig>,
    /// Model prefix mappings (e.g., "gpt-4" -> "openai")
    model_mappings: HashMap<String, String>,
}

impl Default for Router {
    fn default() -> Self {
        Self::new()
    }
}

impl Router {
    /// Create a new empty router
    pub fn new() -> Self {
        Self {
            providers: HashMap::new(),
            configs: HashMap::new(),
            model_mappings: HashMap::new(),
        }
    }

    /// Create a router with the mock provider pre-registered
    pub fn with_mock() -> Self {
        Self::new()
            .register_provider(
                "mock",
                Arc::new(MockProvider::new()) as Arc<dyn crate::providers::LLMProvider>,
                ProviderConfig::new("mock"),
            )
            .expect("Failed to register mock provider")
    }

    /// Register a new provider
    #[instrument(skip(self, provider), fields(provider = %config.name))]
    pub fn register_provider(
        mut self,
        name: &str,
        provider: Arc<dyn crate::providers::LLMProvider>,
        config: ProviderConfig,
    ) -> Result<Self> {
        if self.providers.contains_key(name) {
            return Err(Error::Configuration(format!(
                "Provider '{}' is already registered",
                name
            )));
        }

        info!(provider = %name, "Registering provider");
        self.providers.insert(name.to_string(), provider);
        self.configs.insert(name.to_string(), config);

        Ok(self)
    }

    /// Add a model mapping (model prefix -> provider name)
    ///
    /// For example, `router.add_model_mapping("gpt-", "openai")` will route
    /// all models starting with "gpt-" to the "openai" provider.
    pub fn add_model_mapping(mut self, model_prefix: &str, provider_name: &str) -> Self {
        if !self.providers.contains_key(provider_name) {
            tracing::warn!(
                model_prefix = %model_prefix,
                provider = %provider_name,
                "Provider not registered yet"
            );
        }
        self.model_mappings
            .insert(model_prefix.to_string(), provider_name.to_string());
        self
    }

    /// Auto-detect and register providers based on available API keys
    ///
    /// This is a convenience method that checks environment variables
    /// and registers common providers.
    #[allow(unused_variables)]
    pub fn auto_register(mut self) -> Result<Self> {
        // Check for OpenAI API key
        if let Ok(api_key) = std::env::var("OPENAI_API_KEY") {
            if !api_key.is_empty() {
                info!("Auto-registering OpenAI provider");
                let config = ProviderConfig::new("openai").with_api_key(&api_key);
                if let Ok(provider) =
                    crate::providers::openai::OpenAIProvider::new(config.clone())
                {
                    self = self.register_provider(
                        "openai",
                        Arc::new(provider) as Arc<dyn crate::providers::LLMProvider>,
                        config,
                    )?;
                    self = self.add_model_mapping("gpt-", "openai");
                }
            }
        }

        // Check for Anthropic API key
        if let Ok(api_key) = std::env::var("ANTHROPIC_API_KEY") {
            if !api_key.is_empty() {
                info!("Auto-registering Anthropic provider");
                let config = ProviderConfig::new("anthropic").with_api_key(&api_key);
                if let Ok(provider) =
                    crate::providers::anthropic::AnthropicProvider::new(config.clone())
                {
                    self = self.register_provider(
                        "anthropic",
                        Arc::new(provider) as Arc<dyn crate::providers::LLMProvider>,
                        config,
                    )?;
                    self = self.add_model_mapping("claude-", "anthropic");
                }
            }
        }

        Ok(self)
    }

    /// Get the provider for a specific model
    #[instrument(skip(self), fields(model = %model))]
    pub fn get_provider_for_model(&self, model: &str) -> Result<Arc<dyn crate::providers::LLMProvider>> {
        // First, check explicit model mappings
        for (prefix, provider_name) in &self.model_mappings {
            if model.starts_with(prefix) {
                debug!(
                    model = %model,
                    provider = %provider_name,
                    "Using model mapping"
                );
                return self
                    .providers
                    .get(provider_name)
                    .cloned()
                    .ok_or_else(|| Error::NoProvider(model.to_string()));
            }
        }

        // Fall back to checking each provider's supported models
        for (name, provider) in &self.providers {
            if provider.supports_model(model) {
                debug!(
                    model = %model,
                    provider = %name,
                    "Provider supports model"
                );
                return Ok(provider.clone());
            }
        }

        Err(Error::NoProvider(model.to_string()))
    }

    /// Get all registered provider names
    pub fn provider_names(&self) -> Vec<&str> {
        self.providers.keys().map(|s| s.as_str()).collect()
    }

    /// Check if a model is supported by any provider
    pub fn supports_model(&self, model: &str) -> bool {
        self.get_provider_for_model(model).is_ok()
    }

    /// Get the provider configuration
    pub fn get_config(&self, name: &str) -> Option<&ProviderConfig> {
        self.configs.get(name)
    }

    /// List all available models across all providers
    pub async fn list_all_models(&self) -> Result<Vec<(String, ModelList)>> {
        let mut results = Vec::new();
        for (name, provider) in &self.providers {
            match provider.list_models().await {
                Ok(models) => results.push((name.clone(), models)),
                Err(e) => {
                    tracing::warn!(provider = %name, error = %e, "Failed to list models");
                }
            }
        }
        Ok(results)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_router_creation() {
        let router = Router::new();
        assert!(router.providers.is_empty());
        assert!(router.provider_names().is_empty());
    }

    #[test]
    fn test_router_with_mock() {
        let router = Router::with_mock();
        assert_eq!(router.provider_names(), vec!["mock"]);
    }

    #[test]
    fn test_model_mapping() {
        let router = Router::with_mock().add_model_mapping("mock-", "mock");

        assert!(router.supports_model("mock-gpt-4"));
        assert!(!router.supports_model("unknown-model"));
    }

    #[test]
    fn test_register_provider() {
        let router = Router::new()
            .register_provider(
                "test",
                Arc::new(MockProvider::new()) as Arc<dyn crate::providers::LLMProvider>,
                ProviderConfig::new("test"),
            )
            .unwrap();

        assert_eq!(router.provider_names(), vec!["test"]);
    }

    #[test]
    fn test_duplicate_provider_error() {
        let router = Router::new()
            .register_provider(
                "test",
                Arc::new(MockProvider::new()) as Arc<dyn crate::providers::LLMProvider>,
                ProviderConfig::new("test"),
            )
            .unwrap();

        let result = router.register_provider(
            "test",
            Arc::new(MockProvider::new()) as Arc<dyn crate::providers::LLMProvider>,
            ProviderConfig::new("test"),
        );

        assert!(result.is_err());
    }

    #[tokio::test]
    async fn test_list_all_models() {
        let router = Router::with_mock();
        let models = router.list_all_models().await.unwrap();
        assert!(!models.is_empty());
        assert_eq!(models[0].0, "mock");
    }
}
