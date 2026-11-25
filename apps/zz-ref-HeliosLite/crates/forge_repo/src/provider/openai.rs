use std::sync::{Arc, LazyLock};

use anyhow::{Context as _, Result};
use forge_app::domain::{
    ChatCompletionMessage, Context as ChatContext, Model, ModelId, ProviderId, ResultStream,
    Transformer,
};
use forge_app::dto::openai::{
    COPILOT_AUTO_MODEL_ID, CopilotListModelResponse, ListModelResponse, ProviderPipeline, Request,
    Response, copilot_auto_model,
};
use forge_app::{EnvironmentInfra, HttpInfra};
use forge_domain::{ChatRepository, Provider};
use forge_infra::sanitize_headers;
use reqwest::header::AUTHORIZATION;
use tokio_stream::StreamExt;
use tracing::{debug, info};
use url::Url;

use crate::provider::event::into_chat_completion_message;
use crate::provider::retry::into_retry;
use crate::provider::utils::{create_headers, format_http_context, join_url};

/// Enhances error messages with provider-specific helpful information
fn enhance_error(error: anyhow::Error, provider_id: &ProviderId) -> anyhow::Error {
    // GitHub Copilot specific error enhancements
    if *provider_id == ProviderId::GITHUB_COPILOT {
        let error_string = format!("{:#}", error);

        // Check if this is a model_not_supported error
        if error_string.contains("model_not_supported")
            || error_string.contains("requested model is not supported")
        {
            return error.context(
                "This model may not be enabled for your GitHub Copilot subscription. Visit https://github.com/settings/copilot/features to check which models are available to you."
            );
        }
    }

    error
}

/// Prepares a request for GitHub Copilot's synthetic "auto" model.
///
/// Copilot's API has no `auto` model id; official clients implement "Auto"
/// by omitting the model so the service selects one server-side. Since the
/// served model is unknown, model-specific tuning must also be omitted or
/// the request fails (e.g. `invalid_reasoning_effort` when the service
/// selects a non-reasoning model).
fn prepare_copilot_auto_request(mut request: Request) -> Request {
    request.model = None;
    request.reasoning = None;
    request.reasoning_effort = None;
    request.thinking = None;
    request
}

#[derive(Clone)]
struct OpenAIProvider<H> {
    provider: Provider<Url>,
    http: Arc<H>,
}

impl<H: HttpInfra> OpenAIProvider<H> {
    pub fn new(provider: Provider<Url>, http: Arc<H>) -> Self {
        Self { provider, http }
    }

    // OpenRouter optional headers ref: https://openrouter.ai/docs/api-reference/overview#headers
    // - `HTTP-Referer`: Identifies your app on openrouter.ai
    // - `X-Title`: Sets/modifies your app's title
    fn get_headers(&self) -> Vec<(String, String)> {
        let mut headers = Vec::new();
        if let Some(api_key) =
            self.provider
                .credential
                .as_ref()
                .and_then(|c| match &c.auth_details {
                    forge_domain::AuthDetails::ApiKey(key) => Some(key.as_str()),
                    forge_domain::AuthDetails::OAuthWithApiKey { api_key, .. } => {
                        Some(api_key.as_str())
                    }
                    forge_domain::AuthDetails::OAuth { tokens, .. } => {
                        Some(tokens.access_token.as_str())
                    }
                    forge_domain::AuthDetails::GoogleAdc(token) => Some(token.as_str()),
                    forge_domain::AuthDetails::AwsProfile(_) => None,
                })
        {
            headers.push((AUTHORIZATION.to_string(), format!("Bearer {api_key}")));
        }
        self.provider
            .auth_methods
            .iter()
            .for_each(|method| match method {
                forge_domain::AuthMethod::ApiKey => {}
                forge_domain::AuthMethod::OAuthDevice(oauth_config) => {
                    if let Some(custom_headers) = &oauth_config.custom_headers {
                        custom_headers.iter().for_each(|(k, v)| {
                            headers.push((k.clone(), v.clone()));
                        });
                    }
                }
                forge_domain::AuthMethod::OAuthCode(oauth_config) => {
                    if let Some(custom_headers) = &oauth_config.custom_headers {
                        custom_headers.iter().for_each(|(k, v)| {
                            headers.push((k.clone(), v.clone()));
                        });
                    }
                }
                forge_domain::AuthMethod::CodexDevice(oauth_config) => {
                    if let Some(custom_headers) = &oauth_config.custom_headers {
                        custom_headers.iter().for_each(|(k, v)| {
                            headers.push((k.clone(), v.clone()));
                        });
                    }
                }
                forge_domain::AuthMethod::GoogleAdc => {}
                forge_domain::AuthMethod::AwsProfile => {}
            });
        // Append provider-level custom headers (from provider.json config)
        if let Some(custom_headers) = &self.provider.custom_headers {
            for (k, v) in custom_headers {
                headers.push((k.clone(), v.clone()));
            }
        }
        headers
    }

    /// Creates headers including provider-specific conversation session headers
    /// for zai, zai_coding, and OpenCode Go providers
    /// and GitHub Copilot optimization headers (x-initiator, Openai-Intent,
    /// Copilot-Vision-Request, anthropic-beta)
    #[cfg(test)]
    fn get_headers_with_request(&self, request: &Request) -> Vec<(String, String)> {
        self.get_headers_with_session_id(request, request.session_id.as_deref())
    }

    fn get_headers_with_session_id(
        &self,
        request: &Request,
        session_id: Option<&str>,
    ) -> Vec<(String, String)> {
        let mut headers = self.get_headers();
        // Add Session-Id header for zai and zai_coding providers
        if let Some(session_id) = session_id
            && (self.provider.id == ProviderId::ZAI || self.provider.id == ProviderId::ZAI_CODING)
        {
            headers.push(("Session-Id".to_string(), session_id.to_string()));
            debug!(
                provider = %self.provider.url,
                "Added Session-Id header for zai provider"
            );
        }

        if let Some(session_id) = session_id
            && self.provider.id == ProviderId::OPENCODE_GO
        {
            headers.push(("x-opencode-session".to_string(), session_id.to_string()));
            debug!(
                provider = %self.provider.url,
                "Added x-opencode-session header for OpenCode Go provider"
            );
        }

        // Add GitHub Copilot optimization headers only for github_copilot provider
        if self.provider.id == ProviderId::GITHUB_COPILOT {
            // Determine initiator: use request.initiator if available, otherwise detect
            // from messages
            let initiator = request.initiator.as_deref().unwrap_or_else(|| {
                // Fall back to detecting from last message role
                let is_agent_initiated = request.messages.as_ref().is_some_and(|messages| {
                    messages.last().is_some_and(|msg| {
                        // If last message role is not User, it's agent-initiated
                        !matches!(msg.role, forge_app::dto::openai::Role::User)
                    })
                });
                if is_agent_initiated { "agent" } else { "user" }
            });

            headers.push(("x-initiator".to_string(), initiator.to_string()));
            headers.push((
                "Openai-Intent".to_string(),
                "conversation-edits".to_string(),
            ));

            // Detect if request contains vision/image content
            let has_vision_content = request.messages.as_ref().is_some_and(|messages| {
                messages.iter().any(|msg| {
                    msg.content.as_ref().is_some_and(|content| match content {
                        forge_app::dto::openai::MessageContent::Text(_) => false,
                        forge_app::dto::openai::MessageContent::Parts(parts) => {
                            parts.iter().any(|part| {
                                matches!(part, forge_app::dto::openai::ContentPart::ImageUrl { .. })
                            })
                        }
                    })
                })
            });

            if has_vision_content {
                headers.push(("Copilot-Vision-Request".to_string(), "true".to_string()));
            }

            // When Copilot proxies an Anthropic Claude model, inject the beta flag
            let is_anthropic_model = request
                .model
                .as_ref()
                .is_some_and(|m| m.as_str().contains("claude"));

            if is_anthropic_model {
                headers.push((
                    "anthropic-beta".to_string(),
                    "interleaved-thinking-2025-05-14".to_string(),
                ));
            }

            debug!(
                provider = %self.provider.url,
                initiator = %initiator,
                has_vision = %has_vision_content,
                is_anthropic_model = %is_anthropic_model,
                "Added GitHub Copilot optimization headers"
            );
        }

        headers
    }

    fn transform_request_and_headers(
        &self,
        mut request: Request,
        merge_system_messages: bool,
    ) -> (Request, Vec<(String, String)>) {
        let session_id = request.session_id.clone();
        let mut pipeline = ProviderPipeline::new(&self.provider, merge_system_messages);
        request = pipeline.transform(request);

        if self.provider.id == ProviderId::GITHUB_COPILOT
            && request
                .model
                .as_ref()
                .is_some_and(|model| model.as_str() == COPILOT_AUTO_MODEL_ID)
        {
            request = prepare_copilot_auto_request(request);
        }

        let headers = self.get_headers_with_session_id(&request, session_id.as_deref());
        (request, headers)
    }

    async fn inner_chat(
        &self,
        model: &ModelId,
        context: ChatContext,
        merge_system_messages: bool,
    ) -> ResultStream<ChatCompletionMessage, anyhow::Error> {
        let request = Request::from(context).model(model.clone());
        let (request, header_values) =
            self.transform_request_and_headers(request, merge_system_messages);

        let url = self.provider.url.clone();
        let headers = create_headers(header_values);

        info!(
            url = %url,
            model = %model,
            headers = ?sanitize_headers(&headers),
            message_count = %request.message_count(),
            message_cache_count = %request.message_cache_count(),
            "Connecting Upstream"
        );

        let json_bytes =
            serde_json::to_vec(&request).with_context(|| "Failed to serialize request")?;

        let es = self
            .http
            .http_eventsource(&url, Some(headers), json_bytes.into())
            .await
            .with_context(|| format_http_context(None, "POST", &url))
            .map_err(|e| enhance_error(e, &self.provider.id))?;

        let stream = into_chat_completion_message::<Response>(url, es);

        Ok(Box::pin(stream))
    }

    async fn inner_models(&self) -> Result<Vec<forge_app::domain::Model>> {
        // For Vertex AI, load models from static JSON file using VertexProvider logic
        if self.provider.id == ProviderId::VERTEX_AI {
            debug!("Loading Vertex AI models from static JSON file");
            Ok(self.inner_vertex_models())
        } else {
            let models = self
                .provider
                .models()
                .ok_or_else(|| anyhow::anyhow!("Provider models configuration is required"))?;

            match models {
                forge_domain::ModelSource::Url(url) => {
                    debug!(url = %url, "Fetching models");
                    match self.fetch_models(url.as_str()).await {
                        Err(error) => {
                            tracing::error!(error = ?error, "Failed to fetch models");
                            anyhow::bail!(error)
                        }
                        Ok(response) => {
                            // GitHub Copilot's /models endpoint uses a different schema
                            // (capabilities, limits, policy) than the standard OpenAI
                            // models response and includes models the account cannot
                            // actually use
                            if self.provider.id == ProviderId::GITHUB_COPILOT {
                                let data: CopilotListModelResponse = serde_json::from_str(
                                    &response,
                                )
                                .with_context(|| format_http_context(None, "GET", url))
                                .with_context(
                                    || "Failed to deserialize GitHub Copilot models response",
                                )?;
                                // Offer the synthetic "auto" model first; it lets the
                                // service pick the model and is the included option on
                                // plans with limited premium requests
                                let models = std::iter::once(copilot_auto_model())
                                    .chain(
                                        data.data
                                            .into_iter()
                                            .filter(|model| model.is_usable())
                                            .map(Into::into),
                                    )
                                    .collect();
                                return Ok(models);
                            }
                            let data: ListModelResponse = serde_json::from_str(&response)
                                .with_context(|| format_http_context(None, "GET", url))
                                .with_context(|| "Failed to deserialize models response")?;
                            Ok(data.data.into_iter().map(Into::into).collect())
                        }
                    }
                }
                forge_domain::ModelSource::Hardcoded(models) => {
                    debug!("Using hardcoded models");
                    Ok(models.clone())
                }
                forge_domain::ModelSource::Dynamic { url, fallback } => {
                    debug!(url = %url, "Fetching dynamic models");
                    match self.fetch_models(url.as_str()).await {
                        Ok(response) => {
                            let data: ListModelResponse = serde_json::from_str(&response)
                                .with_context(|| format_http_context(None, "GET", url))
                                .with_context(|| "Failed to deserialize models response")?;
                            // Preserve server-side Model DTOs (OpenAI's
                            // /v1/models payload carries a `description`
                            // and other per-model metadata). The merge
                            // function now treats the server side as
                            // authoritative for fields it sets, with
                            // curated data filling only the None gaps.
                            Ok(forge_app::domain::Model::merge_live(
                                data.data
                                    .into_iter()
                                    .map(forge_domain::Model::from)
                                    .collect(),
                                fallback.clone(),
                            ))
                        }
                        Err(error) => {
                            tracing::warn!(
                                error = ?error,
                                provider = %self.provider.id,
                                "Dynamic model fetch failed; falling back to curated list"
                            );
                            Ok(fallback.clone())
                        }
                    }
                }
            }
        }
    }

    async fn fetch_models(&self, url: &str) -> Result<String, anyhow::Error> {
        let headers = create_headers(self.get_headers());
        let url = join_url(url, "")?;
        info!(method = "GET", url = %url, headers = ?sanitize_headers(&headers), "Fetching Models");

        let response = self
            .http
            .http_get(&url, Some(headers))
            .await
            .with_context(|| format_http_context(None, "GET", &url))
            .with_context(|| "Failed to fetch the models")?;

        let status = response.status();
        let ctx_message = format_http_context(Some(status), "GET", &url);

        let response_text = response
            .text()
            .await
            .with_context(|| ctx_message.clone())
            .with_context(|| "Failed to decode response into text")?;

        if status.is_success() {
            Ok(response_text)
        } else {
            Err(anyhow::anyhow!(response_text))
                .with_context(|| ctx_message)
                .with_context(|| "Failed to fetch the models")
        }
    }

    /// Load Vertex AI models from static JSON file
    fn inner_vertex_models(&self) -> Vec<forge_app::domain::Model> {
        static VERTEX_MODELS: LazyLock<Vec<forge_app::domain::Model>> = LazyLock::new(|| {
            let models = include_str!(concat!(env!("CARGO_MANIFEST_DIR"), "/../../vertex.json"));
            serde_json::from_str(models).unwrap()
        });
        VERTEX_MODELS.clone()
    }
}

impl<T: HttpInfra> OpenAIProvider<T> {
    pub async fn chat(
        &self,
        model: &ModelId,
        context: ChatContext,
        merge_system_messages: bool,
    ) -> ResultStream<ChatCompletionMessage, anyhow::Error> {
        self.inner_chat(model, context, merge_system_messages).await
    }

    pub async fn models(&self) -> Result<Vec<forge_app::domain::Model>> {
        self.inner_models().await
    }
}

/// Repository for OpenAI-compatible provider responses
///
/// Handles providers that use OpenAI's API format including:
/// - OpenAI
/// - Azure OpenAI
/// - Vertex AI
/// - OpenRouter
/// - DeepSeek
/// - Groq
pub struct OpenAIResponseRepository<F> {
    infra: Arc<F>,
}

impl<F> OpenAIResponseRepository<F> {
    pub fn new(infra: Arc<F>) -> Self {
        Self { infra }
    }
}

#[async_trait::async_trait]
impl<F: HttpInfra + EnvironmentInfra<Config = forge_config::ForgeConfig> + 'static> ChatRepository
    for OpenAIResponseRepository<F>
{
    async fn chat(
        &self,
        model_id: &ModelId,
        context: ChatContext,
        provider: Provider<Url>,
    ) -> ResultStream<ChatCompletionMessage, anyhow::Error> {
        let config = self.infra.get_config()?;

        let retry_config = config.retry.unwrap_or_default();
        let merge_system_messages = config.merge_system_messages;
        let provider_id = provider.id.clone();
        let provider_client = OpenAIProvider::new(provider, self.infra.clone());
        let stream = provider_client
            .chat(model_id, context, merge_system_messages)
            .await
            .map_err(|e| into_retry(e, &retry_config))?;

        Ok(Box::pin(stream.map(move |item| {
            item.map_err(|e| enhance_error(into_retry(e, &retry_config), &provider_id))
        })))
    }

    async fn models(&self, provider: Provider<Url>) -> anyhow::Result<Vec<Model>> {
        let retry_config = self.infra.get_config()?.retry.unwrap_or_default();
        let provider_client = OpenAIProvider::new(provider, self.infra.clone());
        provider_client
            .models()
            .await
            .map_err(|e| into_retry(e, &retry_config))
            .context("Failed to fetch models from OpenAI-compatible provider")
    }
}

#[cfg(test)]
mod tests {

    use std::collections::HashMap;

    use anyhow::Context;
    use bytes::Bytes;
    use forge_app::HttpInfra;
    use forge_app::domain::{Provider, ProviderId, ProviderResponse};
    use forge_app::dto::openai::{ContentPart, ImageUrl, Message, MessageContent, Role};
    use forge_eventsource::EventSource;
    use reqwest::header::HeaderMap;
    use url::Url;

    use super::*;
    use crate::provider::mock_server::{MockServer, normalize_ports};

    // Test helper functions
    fn make_credential(provider_id: ProviderId, key: &str) -> Option<forge_domain::AuthCredential> {
        Some(forge_domain::AuthCredential {
            id: provider_id,
            auth_details: forge_domain::AuthDetails::ApiKey(forge_domain::ApiKey::from(
                key.to_string(),
            )),
            url_params: HashMap::new(),
        })
    }

    fn openai(key: &str) -> Provider<Url> {
        Provider {
            id: ProviderId::OPENAI,
            provider_type: forge_domain::ProviderType::Llm,
            response: Some(ProviderResponse::OpenAI),
            url: Url::parse("https://api.openai.com/v1/chat/completions").unwrap(),
            credential: make_credential(ProviderId::OPENAI, key),
            custom_headers: None,
            auth_methods: vec![forge_domain::AuthMethod::ApiKey],
            url_params: vec![],
            models: Some(forge_domain::ModelSource::Url(
                Url::parse("https://api.openai.com/v1/models").unwrap(),
            )),
        }
    }

    fn zai(key: &str) -> Provider<Url> {
        Provider {
            id: ProviderId::ZAI,
            provider_type: forge_domain::ProviderType::Llm,
            response: Some(ProviderResponse::OpenAI),
            url: Url::parse("https://api.z.ai/api/paas/v4/chat/completions").unwrap(),
            credential: make_credential(ProviderId::ZAI, key),
            custom_headers: None,
            auth_methods: vec![forge_domain::AuthMethod::ApiKey],
            url_params: vec![],
            models: Some(forge_domain::ModelSource::Url(
                Url::parse("https://api.z.ai/api/paas/v4/models").unwrap(),
            )),
        }
    }

    fn zai_coding(key: &str) -> Provider<Url> {
        Provider {
            id: ProviderId::ZAI_CODING,
            provider_type: forge_domain::ProviderType::Llm,
            response: Some(ProviderResponse::OpenAI),
            url: Url::parse("https://api.z.ai/api/coding/paas/v4/chat/completions").unwrap(),
            credential: make_credential(ProviderId::ZAI_CODING, key),
            custom_headers: None,
            auth_methods: vec![forge_domain::AuthMethod::ApiKey],
            url_params: vec![],
            models: Some(forge_domain::ModelSource::Url(
                Url::parse("https://api.z.ai/api/paas/v4/models").unwrap(),
            )),
        }
    }

    fn opencode_go(key: &str) -> Provider<Url> {
        Provider {
            id: ProviderId::OPENCODE_GO,
            provider_type: forge_domain::ProviderType::Llm,
            response: Some(ProviderResponse::OpenAI),
            url: Url::parse("https://api.opencode.com/v1/chat/completions").unwrap(),
            credential: make_credential(ProviderId::OPENCODE_GO, key),
            custom_headers: None,
            auth_methods: vec![forge_domain::AuthMethod::ApiKey],
            url_params: vec![],
            models: Some(forge_domain::ModelSource::Url(
                Url::parse("https://api.opencode.com/v1/models").unwrap(),
            )),
        }
    }

    fn anthropic(key: &str) -> Provider<Url> {
        Provider {
            id: ProviderId::ANTHROPIC,
            provider_type: forge_domain::ProviderType::Llm,
            response: Some(ProviderResponse::Anthropic),
            url: Url::parse("https://api.anthropic.com/v1/messages").unwrap(),
            credential: make_credential(ProviderId::ANTHROPIC, key),
            custom_headers: None,
            auth_methods: vec![forge_domain::AuthMethod::ApiKey],
            url_params: vec![],
            models: Some(forge_domain::ModelSource::Url(
                Url::parse("https://api.anthropic.com/v1/models").unwrap(),
            )),
        }
    }

    // Mock implementation of HttpInfra for testing
    #[derive(Clone)]
    struct MockHttpClient {
        client: reqwest::Client,
    }

    impl MockHttpClient {
        fn new() -> Self {
            Self { client: reqwest::Client::new() }
        }
    }

    #[async_trait::async_trait]
    impl HttpInfra for MockHttpClient {
        async fn http_get(
            &self,
            url: &Url,
            _headers: Option<HeaderMap>,
        ) -> anyhow::Result<reqwest::Response> {
            let mut request = self.client.get(url.clone());
            if let Some(headers) = _headers {
                request = request.headers(headers);
            }
            Ok(request.send().await?)
        }

        async fn http_post(
            &self,
            url: &Url,
            headers: Option<HeaderMap>,
            body: Bytes,
        ) -> anyhow::Result<reqwest::Response> {
            let mut request = self.client.post(url.clone()).body(body);
            if let Some(headers) = headers {
                request = request.headers(headers);
            }
            Ok(request.send().await?)
        }

        async fn http_delete(&self, url: &Url) -> anyhow::Result<reqwest::Response> {
            Ok(self.client.delete(url.clone()).send().await?)
        }

        async fn http_eventsource(
            &self,
            url: &Url,
            headers: Option<HeaderMap>,
            body: Bytes,
        ) -> anyhow::Result<EventSource> {
            let mut request = self.client.post(url.clone()).body(body);
            if let Some(headers) = headers {
                request = request.headers(headers);
            }
            Ok(EventSource::new(request).map_err(|e| anyhow::anyhow!(e))?)
        }
    }

    fn create_provider(base_url: &str) -> anyhow::Result<OpenAIProvider<MockHttpClient>> {
        let provider = Provider {
            id: ProviderId::OPENAI,
            provider_type: forge_domain::ProviderType::Llm,
            response: Some(ProviderResponse::OpenAI),
            url: reqwest::Url::parse(base_url)?,
            credential: make_credential(ProviderId::OPENAI, "test-api-key"),
            custom_headers: None,
            auth_methods: vec![forge_domain::AuthMethod::ApiKey],
            url_params: vec![],
            models: Some(forge_domain::ModelSource::Url(
                reqwest::Url::parse(base_url)?.join("models")?,
            )),
        };

        Ok(OpenAIProvider::new(
            provider,
            Arc::new(MockHttpClient::new()),
        ))
    }

    fn create_provider_with_dynamic(
        base_url: &str,
        dynamic_url: reqwest::Url,
        fallback: Vec<forge_app::domain::Model>,
    ) -> anyhow::Result<OpenAIProvider<MockHttpClient>> {
        let provider = Provider {
            id: ProviderId::OPENAI,
            provider_type: forge_domain::ProviderType::Llm,
            response: Some(ProviderResponse::OpenAI),
            url: reqwest::Url::parse(base_url)?,
            credential: make_credential(ProviderId::OPENAI, "test-api-key"),
            custom_headers: None,
            auth_methods: vec![forge_domain::AuthMethod::ApiKey],
            url_params: vec![],
            models: Some(forge_domain::ModelSource::Dynamic { url: dynamic_url, fallback }),
        };

        Ok(OpenAIProvider::new(
            provider,
            Arc::new(MockHttpClient::new()),
        ))
    }

    fn create_mock_models_response() -> serde_json::Value {
        serde_json::json!({
            "data": [
                {
                    "id": "model-1",
                    "name": "Test Model 1",
                    "description": "A test model",
                    "context_length": 4096,
                    "supported_parameters": ["tools", "supports_parallel_tool_calls"]
                },
                {
                    "id": "model-2",
                    "name": "Test Model 2",
                    "description": "Another test model",
                    "context_length": 8192,
                    "supported_parameters": ["tools"]
                }
            ]
        })
    }

    fn create_error_response(message: &str, code: u16) -> serde_json::Value {
        serde_json::json!({
            "error": {
                "code": code,
                "message": message
            }
        })
    }

    fn create_empty_response() -> serde_json::Value {
        serde_json::json!({ "data": [] })
    }

    #[tokio::test]
    async fn test_fetch_models_success() -> anyhow::Result<()> {
        let mut fixture = MockServer::new().await;
        let mock = fixture
            .mock_models(create_mock_models_response(), 200)
            .await;
        let provider = create_provider(&fixture.url())?;
        let actual = provider.models().await?;

        mock.assert_async().await;
        insta::assert_json_snapshot!(actual);
        Ok(())
    }

    #[tokio::test]
    async fn test_fetch_models_http_error_status() -> anyhow::Result<()> {
        let mut fixture = MockServer::new().await;
        let mock = fixture
            .mock_models(create_error_response("Invalid API key", 401), 401)
            .await;

        let provider = create_provider(&fixture.url())?;
        let actual = provider.models().await;

        mock.assert_async().await;

        // Verify that we got an error
        assert!(actual.is_err());
        insta::assert_snapshot!(normalize_ports(format!("{:#?}", actual.unwrap_err())));
        Ok(())
    }

    #[tokio::test]
    async fn test_fetch_models_server_error() -> anyhow::Result<()> {
        let mut fixture = MockServer::new().await;
        let mock = fixture
            .mock_models(create_error_response("Internal Server Error", 500), 500)
            .await;

        let provider = create_provider(&fixture.url())?;
        let actual = provider.models().await;

        mock.assert_async().await;

        // Verify that we got an error
        assert!(actual.is_err());
        insta::assert_snapshot!(normalize_ports(format!("{:#?}", actual.unwrap_err())));
        Ok(())
    }

    #[tokio::test]
    async fn test_fetch_models_empty_response() -> anyhow::Result<()> {
        let mut fixture = MockServer::new().await;
        let mock = fixture.mock_models(create_empty_response(), 200).await;

        let provider = create_provider(&fixture.url())?;
        let actual = provider.models().await?;

        mock.assert_async().await;
        assert!(actual.is_empty());
        Ok(())
    }

    #[tokio::test]
    async fn test_dynamic_models_success_overlays_curated_metadata() -> anyhow::Result<()> {
        let mut fixture = MockServer::new().await;
        let mock = fixture
            .mock_models(create_mock_models_response(), 200)
            .await;

        let curated = vec![forge_app::domain::Model {
            id: forge_app::domain::ModelId::new("model-1"),
            name: Some("Model One Curated".to_string()),
            description: Some("Curated override".to_string()),
            context_length: Some(16384),
            tools_supported: Some(true),
            supports_parallel_tool_calls: Some(false),
            supports_reasoning: Some(true),
            input_modalities: vec![forge_app::domain::InputModality::Text],
        }];

        let dynamic_url = reqwest::Url::parse(&fixture.url())?.join("/models")?;
        let provider = create_provider_with_dynamic(&fixture.url(), dynamic_url, curated)?;
        let actual = provider.models().await?;

        mock.assert_async().await;

        // Live fetch returns 2 ids; merge should produce 2 entries.
        assert_eq!(
            actual.len(),
            2,
            "expected 2 merged models, got {}",
            actual.len()
        );
        let model_1 = actual
            .iter()
            .find(|m| m.id.as_str() == "model-1")
            .expect("model-1 should be present");
        // Server-provided metadata wins; curated values that match what
        // the server also provided are simply ignored (server is
        // authoritative). Curated data fills None gaps (e.g. when the
        // server returns `description` but the curated entry added
        // extra fields, like `supports_reasoning`, the server's None
        // for that field would be filled by curated — but in this
        // particular test the server provided everything populated).
        assert_eq!(
            model_1.name.as_deref(),
            Some("Test Model 1"),
            "server-provided name wins over curated"
        );
        assert_eq!(model_1.context_length, Some(4096));
        Ok(())
    }

    #[tokio::test]
    async fn test_dynamic_models_failure_falls_back_to_curated() -> anyhow::Result<()> {
        let mut fixture = MockServer::new().await;
        // Mock a 401 — fetch_models errors, Dynamic arm must catch and return
        // the curated fallback list instead of bubbling up.
        let mock = fixture
            .mock_models(create_error_response("Invalid API key", 401), 401)
            .await;

        let curated = vec![
            forge_app::domain::Model {
                id: forge_app::domain::ModelId::new("curated-a"),
                name: Some("Curated A".to_string()),
                ..forge_app::domain::Model::new("curated-a")
            },
            forge_app::domain::Model {
                id: forge_app::domain::ModelId::new("curated-b"),
                name: Some("Curated B".to_string()),
                ..forge_app::domain::Model::new("curated-b")
            },
        ];

        let dynamic_url = reqwest::Url::parse(&fixture.url())?.join("/models")?;
        let provider = create_provider_with_dynamic(&fixture.url(), dynamic_url, curated)?;
        let actual = provider.models().await?;

        mock.assert_async().await;
        assert_eq!(actual.len(), 2);
        let ids: Vec<&str> = actual.iter().map(|m| m.id.as_str()).collect();
        assert!(ids.contains(&"curated-a"));
        assert!(ids.contains(&"curated-b"));
        Ok(())
    }

    #[tokio::test]
    async fn test_dynamic_models_appends_curated_extras_missing_from_live() -> anyhow::Result<()> {
        let mut fixture = MockServer::new().await;
        let mock = fixture
            .mock_models(create_mock_models_response(), 200)
            .await;

        let curated = vec![forge_app::domain::Model {
            id: forge_app::domain::ModelId::new("beta-only-model"),
            name: Some("Beta only".to_string()),
            ..forge_app::domain::Model::new("beta-only-model")
        }];

        let dynamic_url = reqwest::Url::parse(&fixture.url())?.join("/models")?;
        let provider = create_provider_with_dynamic(&fixture.url(), dynamic_url, curated)?;
        let actual = provider.models().await?;

        mock.assert_async().await;
        // Live fetch returns 2 ids; merge appends the curated extras that are
        // not in the live list, so total should be 3.
        assert_eq!(actual.len(), 3);
        assert!(actual.iter().any(|m| m.id.as_str() == "beta-only-model"));
        Ok(())
    }

    // The `test_dynamic_models_*` tests above use the project's `MockServer`
    // helper, which internally wraps `mockito::Server` with a real TCP socket —
    // so they already exercise the wire path end-to-end. The next test uses
    // `mockito::Server` directly (no helper wrapper) to make the
    // wire-level integration scope explicit.

    #[tokio::test]
    async fn test_dynamic_models_mockito_direct_wire_integration() -> anyhow::Result<()> {
        use mockito::Server;

        let mut server = Server::new_async().await;
        let _mock = server
            .mock("GET", "/v1/models")
            .match_header("authorization", "Bearer test-api-key")
            .with_status(200)
            .with_header("content-type", "application/json")
            .with_body(
                serde_json::json!({
                    "data": [
                        { "id": "live-only-model", "name": "Live Only", "context_length": 4096 },
                        { "id": "merged-model", "name": "Live Curated", "context_length": 8192 }
                    ]
                })
                .to_string(),
            )
            .create_async()
            .await;

        // Direct re-build of Provider with ModelSource::Dynamic, mirroring the
        // crate-wide dispatch path but bypassing OpenAIProvider::new so we can
        // assert the wire request shape independently.
        let base_url = format!("{}/v1/chat/completions", server.url());
        let dynamic_url = reqwest::Url::parse(&format!("{}/v1/models", server.url()))?;
        let fallback = vec![forge_app::domain::Model {
            id: forge_app::domain::ModelId::new("merged-model"),
            name: Some("Curated Override".to_string()),
            description: Some("Server metadata should win where present.".to_string()),
            context_length: Some(16384),
            tools_supported: Some(true),
            supports_parallel_tool_calls: Some(false),
            supports_reasoning: Some(true),
            input_modalities: vec![forge_app::domain::InputModality::Text],
        }];

        let provider = Provider {
            id: ProviderId::OPENAI,
            provider_type: forge_domain::ProviderType::Llm,
            response: Some(ProviderResponse::OpenAI),
            url: reqwest::Url::parse(&base_url)?,
            credential: make_credential(ProviderId::OPENAI, "test-api-key"),
            custom_headers: None,
            auth_methods: vec![forge_domain::AuthMethod::ApiKey],
            url_params: vec![],
            models: Some(forge_domain::ModelSource::Dynamic { url: dynamic_url, fallback }),
        };
        let openai_provider = OpenAIProvider::new(provider, Arc::new(MockHttpClient::new()));

        let actual = openai_provider.models().await?;

        _mock.assert_async().await;

        // 2 live + 0 fallback extras (both curated ids are covered by live) = 2.
        assert_eq!(
            actual.len(),
            2,
            "live ids (live-only-model, merged-model) should produce 2 entries"
        );
        let merged = actual
            .iter()
            .find(|m| m.id.as_str() == "merged-model")
            .expect("merged-model should be present");
        // Server-side metadata is authoritative for fields the server
        // populated. Curated data only fills None gaps.
        assert_eq!(
            merged.name.as_deref(),
            Some("Live Curated"),
            "server-provided name wins; curated is ignored for fields the server populated"
        );
        assert_eq!(merged.context_length, Some(8192));
        Ok(())
    }

    #[test]
    fn test_error_deserialization() -> Result<()> {
        let content = serde_json::to_string(&serde_json::json!({
          "error": {
            "message": "This endpoint's maximum context length is 16384 tokens",
            "code": 400
          }
        }))
        .unwrap();
        let message = serde_json::from_str::<Response>(&content)
            .with_context(|| "Failed to parse response")?;
        let message = ChatCompletionMessage::try_from(message.clone());

        assert!(message.is_err());
        Ok(())
    }

    #[tokio::test]
    async fn test_detailed_error_message_included() -> anyhow::Result<()> {
        let mut fixture = MockServer::new().await;
        let detailed_error = create_error_response(
            "Authentication failed: API key is invalid or expired. Please check your API key.",
            401,
        );
        let mock = fixture.mock_models(detailed_error, 401).await;

        let provider = create_provider(&fixture.url())?;
        let actual = provider.models().await;

        mock.assert_async().await;
        assert!(actual.is_err());
        insta::assert_snapshot!(normalize_ports(format!("{:#?}", actual.unwrap_err())));
        Ok(())
    }

    #[tokio::test]
    async fn test_get_headers_with_request_zai_provider() -> anyhow::Result<()> {
        let provider = zai("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);

        // Create a request with session_id
        let request = Request {
            session_id: Some("test-conversation-id".to_string()),
            ..Default::default()
        };

        let headers = openai_provider.get_headers_with_request(&request);

        // Should have Authorization and Session-Id headers
        assert_eq!(headers.len(), 2);
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "authorization" && v == "Bearer test-key")
        );
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "Session-Id" && v == "test-conversation-id")
        );
        Ok(())
    }

    #[tokio::test]
    async fn test_get_headers_with_request_zai_coding_provider() -> anyhow::Result<()> {
        let provider = zai_coding("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);

        // Create a request with session_id
        let request = Request {
            session_id: Some("test-conversation-id".to_string()),
            ..Default::default()
        };

        let headers = openai_provider.get_headers_with_request(&request);

        // Should have Authorization and Session-Id headers
        assert_eq!(headers.len(), 2);
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "authorization" && v == "Bearer test-key")
        );
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "Session-Id" && v == "test-conversation-id")
        );
        Ok(())
    }

    #[tokio::test]
    async fn test_get_headers_with_request_opencode_go_reuses_conversation_session_id()
    -> anyhow::Result<()> {
        let provider = opencode_go("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);
        let request = Request {
            session_id: Some("stable-conversation-id".to_string()),
            ..Default::default()
        };

        let actual_first = openai_provider.get_headers_with_request(&request);
        let actual_second = openai_provider.get_headers_with_request(&request);
        let expected = (
            "x-opencode-session".to_string(),
            "stable-conversation-id".to_string(),
        );

        assert!(actual_first.contains(&expected));
        assert!(actual_second.contains(&expected));
        Ok(())
    }

    #[test]
    fn test_transform_request_and_headers_keeps_opencode_go_session_out_of_body() {
        let provider = opencode_go("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);
        let fixture = Request {
            session_id: Some("stable-conversation-id".to_string()),
            ..Default::default()
        };

        let (actual_request, actual_headers) =
            openai_provider.transform_request_and_headers(fixture, false);
        let expected_header = (
            "x-opencode-session".to_string(),
            "stable-conversation-id".to_string(),
        );

        assert_eq!(actual_request.session_id, None);
        assert!(actual_headers.contains(&expected_header));
    }

    #[tokio::test]
    async fn test_get_headers_with_request_openai_provider() -> anyhow::Result<()> {
        let provider = openai("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);

        // Create a request with session_id
        let request = Request {
            session_id: Some("test-conversation-id".to_string()),
            ..Default::default()
        };

        let headers = openai_provider.get_headers_with_request(&request);

        // Should only have Authorization header (no Session-Id for non-zai providers)
        assert_eq!(headers.len(), 1);
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "authorization" && v == "Bearer test-key")
        );
        assert!(!headers.iter().any(|(k, _)| k == "Session-Id"));
        assert!(!headers.iter().any(|(k, _)| k == "x-opencode-session"));
        Ok(())
    }

    #[tokio::test]
    async fn test_get_headers_with_request_zai_provider_no_session_id() -> anyhow::Result<()> {
        let provider = zai("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);

        // Create a request without session_id
        let request = Request::default();

        let headers = openai_provider.get_headers_with_request(&request);

        // Should only have Authorization header (no Session-Id when session_id is None)
        assert_eq!(headers.len(), 1);
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "authorization" && v == "Bearer test-key")
        );
        assert!(!headers.iter().any(|(k, _)| k == "Session-Id"));
        Ok(())
    }

    #[tokio::test]
    async fn test_get_headers_with_request_anthropic_provider() -> anyhow::Result<()> {
        let provider = anthropic("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);

        // Create a request with session_id
        let request = Request {
            session_id: Some("test-conversation-id".to_string()),
            ..Default::default()
        };

        let headers = openai_provider.get_headers_with_request(&request);

        // Should only have Authorization header (no Session-Id for Anthropic providers)
        assert_eq!(headers.len(), 1);
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "authorization" && v == "Bearer test-key")
        );
        assert!(!headers.iter().any(|(k, _)| k == "Session-Id"));
        Ok(())
    }

    #[test]
    fn test_get_headers_fallback() -> anyhow::Result<()> {
        let provider = zai("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);

        let headers = openai_provider.get_headers();

        // Should only have Authorization header (fallback method doesn't add
        // Session-Id)
        assert_eq!(headers.len(), 1);
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "authorization" && v == "Bearer test-key")
        );
        assert!(!headers.iter().any(|(k, _)| k == "Session-Id"));
        Ok(())
    }

    #[test]
    fn test_enhance_error_github_copilot_model_not_supported() {
        use crate::provider::openai::enhance_error;
        // Setup - simulate the actual error from GitHub Copilot
        let fixture = anyhow::anyhow!(
            "400 Bad Request Reason: {{\"error\":{{\"message\":\"The requested model is not supported.\",\"code\":\"model_not_supported\"}}}}"
        );

        // Execute
        let actual = enhance_error(fixture, &ProviderId::GITHUB_COPILOT);
        let error_string = format!("{:#}", actual);
        insta::assert_snapshot!(error_string);
    }

    #[test]
    fn test_prepare_copilot_auto_request_strips_model_and_tuning() {
        let fixture = Request::default()
            .model(forge_app::domain::ModelId::new("auto"))
            .reasoning_effort("low".to_string())
            .messages(vec![Message {
                role: Role::User,
                content: Some(MessageContent::Text("Hello".to_string())),
                name: None,
                tool_call_id: None,
                tool_calls: None,
                reasoning_details: None,
                reasoning_text: None,
                reasoning_opaque: None,
                reasoning_content: None,
                extra_content: None,
            }]);

        let actual = prepare_copilot_auto_request(fixture);

        assert_eq!(actual.model, None);
        assert_eq!(actual.reasoning_effort, None);
        assert!(actual.reasoning.is_none());
        assert!(actual.thinking.is_none());
        // Messages must be preserved
        assert_eq!(actual.message_count(), 1);
    }

    #[test]
    fn test_get_headers_includes_custom_headers() {
        let mut provider = openai("test-key");
        let mut custom = std::collections::HashMap::new();
        custom.insert("User-Agent".to_string(), "KimiCLI/1.0.0".to_string());
        custom.insert("X-Custom".to_string(), "custom-value".to_string());
        provider.custom_headers = Some(custom);

        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);
        let headers = openai_provider.get_headers();

        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "User-Agent" && v == "KimiCLI/1.0.0")
        );
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "X-Custom" && v == "custom-value")
        );
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "authorization" && v == "Bearer test-key")
        );
    }

    #[test]
    fn test_get_headers_no_custom_headers() {
        let provider = openai("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);
        let headers = openai_provider.get_headers();

        // Only authorization header should be present
        assert_eq!(headers.len(), 1);
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "authorization" && v == "Bearer test-key")
        );
    }

    // Test helper for creating a GitHub Copilot provider
    fn github_copilot(key: &str) -> Provider<Url> {
        Provider {
            id: ProviderId::GITHUB_COPILOT,
            provider_type: forge_domain::ProviderType::Llm,
            response: Some(ProviderResponse::OpenAI),
            url: Url::parse("https://api.githubcopilot.com/chat/completions").unwrap(),
            credential: make_credential(ProviderId::GITHUB_COPILOT, key),
            custom_headers: None,
            auth_methods: vec![forge_domain::AuthMethod::ApiKey],
            url_params: vec![],
            models: Some(forge_domain::ModelSource::Url(
                Url::parse("https://api.githubcopilot.com/models").unwrap(),
            )),
        }
    }

    #[tokio::test]
    async fn test_get_headers_with_request_github_copilot_user_initiated() -> anyhow::Result<()> {
        let provider = github_copilot("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);

        // Create a request with last message from user
        let request = Request {
            messages: Some(vec![Message {
                role: Role::User,
                content: Some(MessageContent::Text("Hello".to_string())),
                name: None,
                tool_call_id: None,
                tool_calls: None,
                reasoning_details: None,
                reasoning_text: None,
                reasoning_opaque: None,
                reasoning_content: None,
                extra_content: None,
            }]),
            ..Default::default()
        };

        let headers = openai_provider.get_headers_with_request(&request);

        // Should have Authorization, x-initiator (user), and Openai-Intent headers
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "authorization" && v == "Bearer test-key")
        );
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "x-initiator" && v == "user")
        );
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "Openai-Intent" && v == "conversation-edits")
        );
        // Should NOT have Copilot-Vision-Request header (no vision content)
        assert!(!headers.iter().any(|(k, _)| k == "Copilot-Vision-Request"));
        Ok(())
    }

    #[tokio::test]
    async fn test_get_headers_with_request_github_copilot_agent_initiated() -> anyhow::Result<()> {
        let provider = github_copilot("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);

        // Create a request with last message from assistant (agent-initiated)
        let request = Request {
            messages: Some(vec![
                Message {
                    role: Role::User,
                    content: Some(MessageContent::Text("Hello".to_string())),
                    name: None,
                    tool_call_id: None,
                    tool_calls: None,
                    reasoning_details: None,
                    reasoning_text: None,
                    reasoning_opaque: None,
                    reasoning_content: None,
                    extra_content: None,
                },
                Message {
                    role: Role::Assistant,
                    content: Some(MessageContent::Text("Response".to_string())),
                    name: None,
                    tool_call_id: None,
                    tool_calls: None,
                    reasoning_details: None,
                    reasoning_text: None,
                    reasoning_opaque: None,
                    reasoning_content: None,
                    extra_content: None,
                },
            ]),
            ..Default::default()
        };

        let headers = openai_provider.get_headers_with_request(&request);

        // Should have Authorization and x-initiator (agent) headers
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "authorization" && v == "Bearer test-key")
        );
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "x-initiator" && v == "agent")
        );
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "Openai-Intent" && v == "conversation-edits")
        );
        Ok(())
    }

    #[tokio::test]
    async fn test_get_headers_with_request_github_copilot_vision_content() -> anyhow::Result<()> {
        let provider = github_copilot("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);

        // Create a request with image content
        let request = Request {
            messages: Some(vec![Message {
                role: Role::User,
                content: Some(MessageContent::Parts(vec![ContentPart::ImageUrl {
                    image_url: ImageUrl {
                        url: "https://example.com/image.png".to_string(),
                        detail: None,
                    },
                    cache_control: None,
                }])),
                name: None,
                tool_call_id: None,
                tool_calls: None,
                reasoning_details: None,
                reasoning_text: None,
                reasoning_opaque: None,
                reasoning_content: None,
                extra_content: None,
            }]),
            ..Default::default()
        };

        let headers = openai_provider.get_headers_with_request(&request);

        // Should have all GitHub Copilot headers including vision
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "authorization" && v == "Bearer test-key")
        );
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "x-initiator" && v == "user")
        );
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "Openai-Intent" && v == "conversation-edits")
        );
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "Copilot-Vision-Request" && v == "true")
        );
        Ok(())
    }

    #[tokio::test]
    async fn test_get_headers_with_request_non_github_copilot_no_extra_headers()
    -> anyhow::Result<()> {
        // Verify that non-GitHub Copilot providers don't get the optimization headers
        let provider = openai("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);

        let request = Request {
            messages: Some(vec![Message {
                role: Role::User,
                content: Some(MessageContent::Text("Hello".to_string())),
                name: None,
                tool_call_id: None,
                tool_calls: None,
                reasoning_details: None,
                reasoning_text: None,
                reasoning_opaque: None,
                reasoning_content: None,
                extra_content: None,
            }]),
            ..Default::default()
        };

        let headers = openai_provider.get_headers_with_request(&request);

        // Should only have Authorization header (no GitHub Copilot headers)
        assert_eq!(headers.len(), 1);
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "authorization" && v == "Bearer test-key")
        );
        assert!(!headers.iter().any(|(k, _)| k == "x-initiator"));
        assert!(!headers.iter().any(|(k, _)| k == "Openai-Intent"));
        assert!(!headers.iter().any(|(k, _)| k == "Copilot-Vision-Request"));
        Ok(())
    }

    #[tokio::test]
    async fn test_get_headers_with_request_github_copilot_claude_model_adds_anthropic_beta()
    -> anyhow::Result<()> {
        let provider = github_copilot("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);

        // Request targeting a Copilot-proxied Claude model
        let request = Request {
            model: Some(forge_app::domain::ModelId::new("claude-sonnet-4-5")),
            messages: Some(vec![Message {
                role: Role::User,
                content: Some(MessageContent::Text("Hello".to_string())),
                name: None,
                tool_call_id: None,
                tool_calls: None,
                reasoning_details: None,
                reasoning_text: None,
                reasoning_opaque: None,
                reasoning_content: None,
                extra_content: None,
            }]),
            ..Default::default()
        };

        let headers = openai_provider.get_headers_with_request(&request);

        // anthropic-beta must be present for Claude models via Copilot
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "anthropic-beta" && v == "interleaved-thinking-2025-05-14")
        );
        // Standard Copilot headers must also be present
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "x-initiator" && v == "user")
        );
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "Openai-Intent" && v == "conversation-edits")
        );
        Ok(())
    }

    #[tokio::test]
    async fn test_get_headers_with_request_github_copilot_non_claude_model_no_anthropic_beta()
    -> anyhow::Result<()> {
        let provider = github_copilot("test-key");
        let http_client = Arc::new(MockHttpClient::new());
        let openai_provider = OpenAIProvider::new(provider, http_client);

        // Request targeting a non-Claude model (e.g. GPT-4o)
        let request = Request {
            model: Some(forge_app::domain::ModelId::new("gpt-4o")),
            messages: Some(vec![Message {
                role: Role::User,
                content: Some(MessageContent::Text("Hello".to_string())),
                name: None,
                tool_call_id: None,
                tool_calls: None,
                reasoning_details: None,
                reasoning_text: None,
                reasoning_opaque: None,
                reasoning_content: None,
                extra_content: None,
            }]),
            ..Default::default()
        };

        let headers = openai_provider.get_headers_with_request(&request);

        // anthropic-beta must NOT be present for non-Claude models
        assert!(!headers.iter().any(|(k, _)| k == "anthropic-beta"));
        // Standard Copilot headers must still be present
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "x-initiator" && v == "user")
        );
        assert!(
            headers
                .iter()
                .any(|(k, v)| k == "Openai-Intent" && v == "conversation-edits")
        );
        Ok(())
    }
}
