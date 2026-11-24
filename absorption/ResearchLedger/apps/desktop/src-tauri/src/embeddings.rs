use serde::Deserialize;
use std::collections::HashSet;
use std::time::Duration;

#[derive(Debug, Deserialize)]
struct EmbedResponse {
    embeddings: Vec<Vec<f32>>,
}

#[derive(Debug, Clone)]
pub struct OllamaEmbedder {
    pub endpoint: String,
    pub model: String,
}

impl OllamaEmbedder {
    pub fn new(model: impl Into<String>) -> Self {
        Self {
            endpoint: "http://127.0.0.1:11434/api/embed".into(),
            model: model.into(),
        }
    }
    pub async fn embed_batch(&self, inputs: &[String]) -> Result<Vec<Vec<f32>>, String> {
        let response = reqwest::Client::new()
            .post(&self.endpoint)
            .json(&serde_json::json!({ "model": self.model, "input": inputs }))
            .send()
            .await
            .map_err(|error| format!("local embedding service unavailable: {error}"))?;
        if !response.status().is_success() {
            return Err(format!(
                "local embedding service returned {}",
                response.status()
            ));
        }
        Ok(response
            .json::<EmbedResponse>()
            .await
            .map_err(|error| error.to_string())?
            .embeddings)
    }
}

/// A score returned by an OpenAI-compatible local `/v1/rerank` endpoint.
#[derive(Debug, Clone, PartialEq)]
pub struct CrossEncoderScore {
    pub index: usize,
    pub relevance_score: f32,
}

/// Execution engine for a loopback cross-encoder. MLX is the native Apple Silicon choice;
/// TEI covers Linux CUDA/ROCm/CPU deployments, and ONNX covers Windows DirectML/CPU services.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RerankEngine {
    Mlx,
    Tei,
    Onnx,
}

impl RerankEngine {
    pub fn default_for_target(target_os: &str) -> Self {
        match target_os {
            "macos" => Self::Mlx,
            "windows" => Self::Onnx,
            _ => Self::Tei,
        }
    }

    fn for_current_target() -> Self {
        Self::default_for_target(std::env::consts::OS)
    }

    fn from_environment(value: &str) -> Result<Self, String> {
        match value.trim().to_ascii_lowercase().as_str() {
            "mlx" => Ok(Self::Mlx),
            "tei" => Ok(Self::Tei),
            "onnx" => Ok(Self::Onnx),
            other => Err(format!(
                "unsupported rerank engine {other:?}; expected `mlx`, `tei`, or `onnx`"
            )),
        }
    }
}

/// Wire contract exposed by the selected local serving engine.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum RerankProtocol {
    /// Cohere/Jina-compatible shape used by the dedicated MLX rerank service.
    CohereV1,
    /// Hugging Face Text Embeddings Inference's native cross-encoder endpoint.
    Tei,
}

#[derive(Debug, Clone)]
pub struct LocalCrossEncoder {
    endpoint: String,
    model: String,
    engine: RerankEngine,
}

#[derive(Debug, Deserialize)]
struct RerankResponse {
    results: Vec<RerankResponseItem>,
}

#[derive(Debug, Deserialize)]
struct RerankResponseItem {
    index: usize,
    relevance_score: f32,
}

#[derive(Debug, Deserialize)]
struct TeiRerankResponseItem {
    index: usize,
    score: f32,
}

impl LocalCrossEncoder {
    /// Creates a reranker that is strictly local. This prevents a user query or vault text
    /// from leaving the machine through a misconfigured endpoint.
    #[cfg(test)]
    pub fn new(endpoint: impl Into<String>, model: impl Into<String>) -> Result<Self, String> {
        Self::new_with_engine(RerankEngine::for_current_target(), endpoint, model)
    }

    /// Selects the request/response protocol explicitly. This is primarily useful for portable
    /// deployments and test fixtures; normal desktop configuration uses the host default.
    pub fn new_with_engine(
        engine: RerankEngine,
        endpoint: impl Into<String>,
        model: impl Into<String>,
    ) -> Result<Self, String> {
        let endpoint = endpoint.into();
        let url = url::Url::parse(&endpoint)
            .map_err(|error| format!("invalid rerank endpoint: {error}"))?;
        let local_host = match url.host() {
            Some(url::Host::Ipv4(address)) => address.is_loopback(),
            Some(url::Host::Ipv6(address)) => address.is_loopback(),
            _ => false,
        };
        if url.scheme() != "http"
            || !local_host
            || !url.username().is_empty()
            || url.password().is_some()
        {
            return Err(
                "rerank endpoint must be an http numeric loopback URL without credentials".into(),
            );
        }
        let model = model.into();
        if model.trim().is_empty() {
            return Err("rerank model must not be empty".into());
        }
        Ok(Self {
            endpoint,
            model,
            engine,
        })
    }

    /// Reranking is opt-in so an offline vault never causes a model download or a connection.
    /// macOS defaults to an MLX-native cross-encoder; Linux defaults to TEI and Windows to ONNX.
    pub fn from_environment() -> Result<Option<Self>, String> {
        let Ok(endpoint) = std::env::var("RESEARCHLEDGER_RERANK_ENDPOINT") else {
            return Ok(None);
        };
        let model = std::env::var("RESEARCHLEDGER_RERANK_MODEL")
            .unwrap_or_else(|_| "local-cross-encoder".into());
        let engine = std::env::var("RESEARCHLEDGER_RERANK_ENGINE")
            .map(|value| RerankEngine::from_environment(&value))
            .unwrap_or_else(|_| Ok(RerankEngine::for_current_target()))?;
        Self::new_with_engine(engine, endpoint, model).map(Some)
    }

    #[cfg(test)]
    pub fn engine(&self) -> RerankEngine {
        self.engine
    }

    pub fn protocol(&self) -> RerankProtocol {
        match self.engine {
            RerankEngine::Mlx => RerankProtocol::CohereV1,
            RerankEngine::Tei | RerankEngine::Onnx => RerankProtocol::Tei,
        }
    }

    fn request_body(&self, query: &str, documents: &[String]) -> serde_json::Value {
        match self.protocol() {
            RerankProtocol::CohereV1 => serde_json::json!({
                "model": self.model,
                "query": query,
                "documents": documents,
            }),
            RerankProtocol::Tei => serde_json::json!({
                "query": query,
                "texts": documents,
                "raw_scores": false,
                "truncate": true,
            }),
        }
    }

    pub async fn rerank(
        &self,
        query: &str,
        documents: &[String],
    ) -> Result<Vec<CrossEncoderScore>, String> {
        if documents.is_empty() {
            return Ok(Vec::new());
        }
        let response = reqwest::Client::builder()
            .timeout(Duration::from_secs(3))
            .no_proxy()
            .redirect(reqwest::redirect::Policy::none())
            .build()
            .map_err(|error| format!("could not initialize local reranker: {error}"))?
            .post(&self.endpoint)
            .json(&self.request_body(query, documents))
            .send()
            .await
            .map_err(|error| format!("local reranker unavailable: {error}"))?
            .error_for_status()
            .map_err(|error| format!("local reranker returned an error: {error}"))?
            .text()
            .await
            .map_err(|error| format!("could not read local reranker response: {error}"))?;
        self.parse_engine_response(&response, documents.len())
    }

    fn parse_engine_response(
        &self,
        body: &str,
        document_count: usize,
    ) -> Result<Vec<CrossEncoderScore>, String> {
        match self.protocol() {
            RerankProtocol::CohereV1 => Self::parse_response(body, document_count),
            RerankProtocol::Tei => Self::parse_tei_response(body, document_count),
        }
    }

    pub fn parse_response(
        body: &str,
        document_count: usize,
    ) -> Result<Vec<CrossEncoderScore>, String> {
        let response: RerankResponse = serde_json::from_str(body)
            .map_err(|error| format!("invalid local reranker response: {error}"))?;
        Self::validate_scores(
            response.results.into_iter().map(|item| CrossEncoderScore {
                index: item.index,
                relevance_score: item.relevance_score,
            }),
            document_count,
        )
    }

    pub fn parse_tei_response(
        body: &str,
        document_count: usize,
    ) -> Result<Vec<CrossEncoderScore>, String> {
        let response: Vec<TeiRerankResponseItem> = serde_json::from_str(body)
            .map_err(|error| format!("invalid TEI reranker response: {error}"))?;
        Self::validate_scores(
            response.into_iter().map(|item| CrossEncoderScore {
                index: item.index,
                relevance_score: item.score,
            }),
            document_count,
        )
    }

    fn validate_scores(
        scores: impl IntoIterator<Item = CrossEncoderScore>,
        document_count: usize,
    ) -> Result<Vec<CrossEncoderScore>, String> {
        let mut seen = HashSet::new();
        let mut scores = scores.into_iter().collect::<Vec<_>>();
        for score in &scores {
            if score.index >= document_count {
                return Err("local reranker returned an out-of-range document index".into());
            }
            if !score.relevance_score.is_finite() {
                return Err("local reranker returned a non-finite relevance score".into());
            }
            if !seen.insert(score.index) {
                return Err("local reranker returned a duplicate document index".into());
            }
        }
        scores.sort_by(|left, right| {
            right
                .relevance_score
                .total_cmp(&left.relevance_score)
                .then(left.index.cmp(&right.index))
        });
        Ok(scores)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_to_local_ollama_endpoint() {
        let provider = OllamaEmbedder::new("embeddinggemma");
        assert_eq!(provider.endpoint, "http://127.0.0.1:11434/api/embed");
        assert_eq!(provider.model, "embeddinggemma");
    }

    #[test]
    fn cross_encoder_contract_fixture_preserves_provider_order() {
        let fixture: serde_json::Value = serde_json::from_str(include_str!(
            "../tests/fixtures/retrieval/cross_encoder_contract.json"
        ))
        .unwrap();
        let document_count = fixture["documents"].as_array().unwrap().len();
        let response = fixture["response"].to_string();

        let scores = LocalCrossEncoder::parse_response(&response, document_count).unwrap();
        let actual = scores
            .into_iter()
            .map(|score| score.index)
            .collect::<Vec<_>>();
        let expected = fixture["expected_order"]
            .as_array()
            .unwrap()
            .iter()
            .map(|value| value.as_u64().unwrap() as usize)
            .collect::<Vec<_>>();

        assert_eq!(actual, expected);
    }

    #[test]
    fn cross_encoder_rejects_a_remote_endpoint() {
        assert!(LocalCrossEncoder::new("https://rerank.example.com/v1/rerank", "model").is_err());
    }

    #[test]
    fn cross_encoder_requires_a_numeric_loopback_endpoint() {
        assert!(LocalCrossEncoder::new("http://127.0.0.1:8082/v1/rerank", "model").is_ok());
        assert!(LocalCrossEncoder::new("http://[::1]:8082/v1/rerank", "model").is_ok());
        assert!(LocalCrossEncoder::new("http://localhost:8082/v1/rerank", "model").is_err());
        assert!(LocalCrossEncoder::new("http://127.0.0.2:8082/v1/rerank", "model").is_ok());
        assert!(LocalCrossEncoder::new("http://192.168.1.2:8082/v1/rerank", "model").is_err());
        assert!(
            LocalCrossEncoder::new("http://user:pass@127.0.0.1:8082/v1/rerank", "model").is_err()
        );
    }

    #[test]
    fn selects_mlx_for_macos_and_tei_elsewhere() {
        assert_eq!(RerankEngine::default_for_target("macos"), RerankEngine::Mlx);
        assert_eq!(RerankEngine::default_for_target("linux"), RerankEngine::Tei);
        assert_eq!(
            RerankEngine::default_for_target("windows"),
            RerankEngine::Onnx
        );
    }

    #[test]
    fn mlx_adapter_keeps_the_cohere_v1_rerank_contract() {
        let reranker = LocalCrossEncoder::new_with_engine(
            RerankEngine::Mlx,
            "http://127.0.0.1:9000/v1/rerank",
            "local-qwen-reranker",
        )
        .unwrap();

        assert_eq!(reranker.engine(), RerankEngine::Mlx);
        assert_eq!(reranker.protocol(), RerankProtocol::CohereV1);
    }

    #[test]
    fn tei_adapter_uses_native_request_and_normalizes_rank_response() {
        let fixture: serde_json::Value = serde_json::from_str(include_str!(
            "../tests/fixtures/retrieval/cross_encoder_contract.json"
        ))
        .unwrap();
        let reranker = LocalCrossEncoder::new_with_engine(
            RerankEngine::Tei,
            fixture["tei"]["endpoint"].as_str().unwrap(),
            "BAAI/bge-reranker-large",
        )
        .unwrap();
        let documents = fixture["documents"]
            .as_array()
            .unwrap()
            .iter()
            .map(|document| document.as_str().unwrap().to_string())
            .collect::<Vec<_>>();

        assert_eq!(reranker.protocol(), RerankProtocol::Tei);
        assert_eq!(
            reranker.request_body(fixture["query"].as_str().unwrap(), &documents),
            serde_json::json!({
                "query": fixture["query"],
                "texts": documents,
                "raw_scores": false,
                "truncate": true,
            })
        );
        let scores = LocalCrossEncoder::parse_tei_response(
            &fixture["tei"]["response"].to_string(),
            fixture["documents"].as_array().unwrap().len(),
        )
        .unwrap();
        assert_eq!(
            scores
                .into_iter()
                .map(|score| score.index)
                .collect::<Vec<_>>(),
            fixture["expected_order"]
                .as_array()
                .unwrap()
                .iter()
                .map(|value| value.as_u64().unwrap() as usize)
                .collect::<Vec<_>>(),
        );
    }
}
