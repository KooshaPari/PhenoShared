//! CLIProxyAPI metrics adapter.
//!
//! Fetches granular runtime metrics from CLIProxyAPI management endpoints.
//! Provides 30+ metrics for routing optimization and analysis.
//!
//! Data sources:
//! - GET /v1/metrics/providers - Per-provider metrics
//! - GET /v1/metrics/models - Per-model metrics
//! - GET /v1/usage - Usage analytics
//! - GET /v1/rankings - Model rankings
//! - GET /health - System health

use chrono::{DateTime, Utc};
use reqwest::Client;
use serde::{Deserialize, Serialize};
use tracing::info;

const DEFAULT_BASE_URL: &str = "http://localhost:8317";

/// CLIProxyAPI metrics configuration
#[derive(Debug, Clone)]
pub struct CLIProxyMetricsConfig {
    /// Base URL for CLIProxyAPI
    pub base_url: String,
    /// API key for authentication
    pub api_key: Option<String>,
    /// Cache TTL in seconds
    pub cache_ttl_seconds: u64,
}

impl Default for CLIProxyMetricsConfig {
    fn default() -> Self {
        Self {
            base_url: DEFAULT_BASE_URL.to_string(),
            api_key: None,
            cache_ttl_seconds: 60, // 1 minute - metrics should be fresh
        }
    }
}

// =============================================================================
// COMPREHENSIVE METRICS STRUCTS (60+ metrics)
// =============================================================================

/// Complete metrics for a single request/response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RequestMetrics {
    // ===== IDENTITY (4) =====
    /// Unique request ID
    pub request_id: String,
    /// Session ID
    pub session_id: Option<String>,
    /// Model used
    pub model: String,
    /// Provider used
    pub provider: String,

    // ===== USAGE TOKENS (12) =====
    /// Input tokens sent
    pub input_tokens: u64,
    /// Output tokens received
    pub output_tokens: u64,
    /// Total tokens (input + output)
    pub total_tokens: u64,
    /// Cached tokens written
    pub cache_write_tokens: u64,
    /// Cached tokens read
    pub cache_read_tokens: u64,
    /// Tool input tokens
    pub tool_input_tokens: u64,
    /// Tool output tokens  
    pub tool_output_tokens: u64,
    /// Reasoning tokens (for reasoning models)
    pub reasoning_tokens: Option<u64>,
    /// Prompt tokens (prefill)
    pub prompt_tokens: Option<u64>,
    /// Tokens saved via caching
    pub cache_saved_tokens: Option<u64>,
    /// Native input tokens (before compression)
    pub native_input_tokens: Option<u64>,
    /// Native output tokens (before truncation)
    pub native_output_tokens: Option<u64>,

    // ===== PERFORMANCE (12) =====
    /// Time to first token (ms)
    pub time_to_first_token_ms: Option<f64>,
    /// Time to last token / total latency (ms)
    pub total_latency_ms: Option<f64>,
    /// Tokens per second (throughput)
    pub tokens_per_second: Option<f64>,
    /// Time to first token (seconds) - alternative unit
    pub ttft_seconds: Option<f64>,
    /// End-to-end latency for 500 tokens (ms)
    pub e2e_500_tokens_ms: Option<f64>,
    /// Time to first substantive token (excluding reasoning)
    pub time_to_first_answer_ms: Option<f64>,
    /// Inter-token latency (avg time between tokens)
    pub inter_token_latency_ms: Option<f64>,
    /// P99 latency
    pub latency_p99_ms: Option<f64>,
    /// Queueing time before processing (ms)
    pub queue_time_ms: Option<f64>,
    /// Time until context is processed (ms)
    pub context_processing_ms: Option<f64>,
    /// Time to first tool call
    pub time_to_first_tool_ms: Option<f64>,
    /// Time between tool calls (agentic)
    pub inter_tool_call_ms: Option<f64>,

    // ===== QUALITY/BEHAVIOR (14) ⚡ =====
    /// Number of conversation turns
    pub turn_count: u32,
    /// Number of tool calls made
    pub tool_call_count: u32,
    /// Verbosity score (output_tokens / expected_output_ratio)
    pub verbosity_score: Option<f64>,
    /// Average response length
    pub avg_response_length: Option<f64>,
    /// Number of images processed
    pub images_processed: Option<u32>,
    /// Number of audio segments processed
    pub audio_segments: Option<u32>,
    /// Number of code blocks in output
    pub code_blocks: Option<u32>,
    /// Output token density (unique tokens / total tokens)
    pub token_density: Option<f64>,
    /// Repetition score (higher = more repetitive)
    pub repetition_score: Option<f64>,
    /// Number of function calls
    pub function_call_count: u32,
    /// Number of parallel tool calls
    pub parallel_tool_calls: Option<u32>,
    /// Tool call success rate
    pub tool_success_rate: Option<f64>,
    /// Token efficiency (useful tokens / total)
    pub token_efficiency: Option<f64>,
    /// Output sentiment score
    pub sentiment_score: Option<f64>,

    // ===== ERROR/RELIABILITY (12) =====
    /// Whether request succeeded
    pub success: bool,
    /// Error message if failed
    pub error_message: Option<String>,
    /// Error code
    pub error_code: Option<String>,
    /// Error category (timeout, rate_limit, auth, etc)
    pub error_category: Option<String>,
    /// Number of retries attempted
    pub retry_count: u32,
    /// Whether rate limited
    pub rate_limited: bool,
    /// Whether truncated due to max tokens
    pub truncated: bool,
    /// Whether filtered (content policy)
    pub content_filtered: bool,
    /// Time spent waiting for rate limit (ms)
    pub rate_limit_wait_ms: Option<u64>,
    /// Error recovery time (ms)
    pub error_recovery_ms: Option<f64>,
    /// Partial failure flag
    pub partial_failure: bool,
    /// Timeout flag
    pub timed_out: bool,

    // ===== COST (8) =====
    /// Input cost in USD
    pub cost_input_usd: Option<f64>,
    /// Output cost in USD
    pub cost_output_usd: Option<f64>,
    /// Total cost in USD
    pub cost_total_usd: Option<f64>,
    /// Cost per 1K tokens
    pub cost_per_1k_tokens: Option<f64>,
    /// Cache discount (percent saved)
    pub cache_discount_percent: Option<f64>,
    /// Estimated cost before optimization
    pub cost_before_optimization: Option<f64>,
    /// Reasoning cost USD
    pub cost_reasoning_usd: Option<f64>,
    /// Tool cost USD
    pub cost_tool_usd: Option<f64>,

    // ===== ROUTING (7) =====
    /// Routing strategy used
    pub routing_strategy: Option<String>,
    /// Whether fallback provider was used
    pub used_fallback: bool,
    /// Latency improvement from routing (ms)
    pub routing_latency_savings_ms: Option<f64>,
    /// Cost improvement from routing
    pub routing_cost_savings_percent: Option<f64>,
    /// Number of providers tried
    pub providers_tried: u32,
    /// Primary provider latency
    pub primary_provider_latency_ms: Option<f64>,
    /// Fallback provider latency
    pub fallback_provider_latency_ms: Option<f64>,

    // ===== CONTEXT/WINDOW (6) =====
    /// Context window size
    pub context_window: Option<u64>,
    /// Context utilization (tokens / window)
    pub context_utilization: Option<f64>,
    /// Number of messages in context
    pub context_message_count: u32,
    /// Whether hit context limit
    pub hit_context_limit: bool,
    /// Context overflow tokens
    pub context_overflow_tokens: Option<u64>,
    /// Sliding window position
    pub sliding_window_position: Option<f64>,

    // ===== AGENTIC (10) ⚡ =====
    /// Whether this was an agentic request
    pub is_agentic: bool,
    /// Number of agent loops
    pub agent_loop_count: u32,
    /// Max depth of tool chain
    pub tool_chain_depth: Option<u32>,
    /// Whether used external tools
    pub used_external_tools: bool,
    /// Task completion status
    pub task_completed: Option<bool>,
    /// Task completion steps
    pub task_steps: Option<u32>,
    /// Self-correction count
    pub self_correction_count: u32,
    /// Reflection tokens used
    pub reflection_tokens: Option<u64>,
    /// Plan-then-execute flag
    pub used_planning: bool,
    /// Re-planning count
    pub replan_count: u32,

    // ===== TIMESTAMP =====
    /// When request started
    pub timestamp: DateTime<Utc>,
}
impl Default for RequestMetrics {
    fn default() -> Self {
        Self {
            // IDENTITY (4)
            request_id: String::new(),
            session_id: None,
            model: String::new(),
            provider: String::new(),

            // USAGE TOKENS (12)
            input_tokens: 0,
            output_tokens: 0,
            total_tokens: 0,
            cache_write_tokens: 0,
            cache_read_tokens: 0,
            tool_input_tokens: 0,
            tool_output_tokens: 0,
            reasoning_tokens: None,
            prompt_tokens: None,
            cache_saved_tokens: None,
            native_input_tokens: None,
            native_output_tokens: None,

            // PERFORMANCE (12)
            time_to_first_token_ms: None,
            total_latency_ms: None,
            tokens_per_second: None,
            ttft_seconds: None,
            e2e_500_tokens_ms: None,
            time_to_first_answer_ms: None,
            inter_token_latency_ms: None,
            latency_p99_ms: None,
            queue_time_ms: None,
            context_processing_ms: None,
            time_to_first_tool_ms: None,
            inter_tool_call_ms: None,

            // QUALITY/BEHAVIOR (14)
            turn_count: 1,
            tool_call_count: 0,
            verbosity_score: None,
            avg_response_length: None,
            images_processed: None,
            audio_segments: None,
            code_blocks: None,
            token_density: None,
            repetition_score: None,
            function_call_count: 0,
            parallel_tool_calls: None,
            tool_success_rate: None,
            token_efficiency: None,
            sentiment_score: None,

            // ERROR/RELIABILITY (12)
            success: true,
            error_message: None,
            error_code: None,
            error_category: None,
            retry_count: 0,
            rate_limited: false,
            truncated: false,
            content_filtered: false,
            rate_limit_wait_ms: None,
            error_recovery_ms: None,
            partial_failure: false,
            timed_out: false,

            // COST (8)
            cost_input_usd: None,
            cost_output_usd: None,
            cost_total_usd: None,
            cost_per_1k_tokens: None,
            cache_discount_percent: None,
            cost_before_optimization: None,
            cost_reasoning_usd: None,
            cost_tool_usd: None,

            // ROUTING (7)
            routing_strategy: None,
            used_fallback: false,
            routing_latency_savings_ms: None,
            routing_cost_savings_percent: None,
            providers_tried: 0,
            primary_provider_latency_ms: None,
            fallback_provider_latency_ms: None,

            // CONTEXT/WINDOW (6)
            context_window: None,
            context_utilization: None,
            context_message_count: 0,
            hit_context_limit: false,
            context_overflow_tokens: None,
            sliding_window_position: None,

            // AGENTIC (10)
            is_agentic: false,
            agent_loop_count: 0,
            tool_chain_depth: None,
            used_external_tools: false,
            task_completed: None,
            task_steps: None,
            self_correction_count: 0,
            reflection_tokens: None,
            used_planning: false,
            replan_count: 0,

            // TIMESTAMP
            timestamp: Utc::now(),
        }
    }
}

/// Provider-level aggregated metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderMetrics {
    // ===== IDENTITY =====
    pub provider: String,

    // ===== USAGE (8 metrics) =====
    pub total_input_tokens: u64,
    pub total_output_tokens: u64,
    pub total_tokens: u64,
    pub total_cache_write_tokens: u64,
    pub total_cache_read_tokens: u64,
    pub total_tool_input_tokens: u64,
    pub total_tool_output_tokens: u64,
    pub total_reasoning_tokens: Option<u64>,

    // ===== PERFORMANCE (5 metrics) =====
    /// Average tokens per second (throughput)
    pub avg_tokens_per_second: Option<f64>,
    /// Median tokens per second
    pub median_tokens_per_second: Option<f64>,
    /// P95 tokens per second
    pub p95_tokens_per_second: Option<f64>,
    /// Average latency ms
    pub avg_latency_ms: Option<f64>,
    /// Median latency ms
    pub median_latency_ms: Option<f64>,

    // ===== RELIABILITY (4 metrics) =====
    pub total_requests: u64,
    pub successful_requests: u64,
    pub failed_requests: u64,
    pub success_rate: Option<f64>,
    pub rate_limited_requests: u64,

    // ===== COST (3 metrics) =====
    pub total_cost_usd: Option<f64>,
    pub avg_cost_per_request: Option<f64>,
    pub cost_per_1k_tokens: Option<f64>,

    // ===== QUALITY (2 metrics) =====
    pub total_turns: u64,
    pub total_tool_calls: u64,

    // ===== TIMESTAMP =====
    pub updated_at: DateTime<Utc>,
}

/// Model-level aggregated metrics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelMetrics {
    // ===== IDENTITY =====
    pub model: String,
    pub provider: String,

    // ===== USAGE (8 metrics) =====
    pub total_input_tokens: u64,
    pub total_output_tokens: u64,
    pub total_tokens: u64,
    pub total_cache_write_tokens: u64,
    pub total_cache_read_tokens: u64,
    pub total_tool_input_tokens: u64,
    pub total_tool_output_tokens: u64,
    pub total_reasoning_tokens: Option<u64>,

    // ===== PERFORMANCE (5 metrics) =====
    pub avg_tokens_per_second: Option<f64>,
    pub median_tokens_per_second: Option<f64>,
    pub p95_tokens_per_second: Option<f64>,
    pub avg_latency_ms: Option<f64>,
    pub median_latency_ms: Option<f64>,

    // ===== VERBOSITY (2 metrics) =====
    /// Average verbosity (output tokens per request)
    pub avg_verbosity: Option<f64>,
    /// Median verbosity
    pub median_verbosity: Option<f64>,

    // ===== RELIABILITY (5 metrics) =====
    pub total_requests: u64,
    pub successful_requests: u64,
    pub failed_requests: u64,
    pub success_rate: Option<f64>,
    pub avg_turns_per_request: Option<f64>,
    pub avg_tool_calls_per_request: Option<f64>,

    // ===== COST (3 metrics) =====
    pub total_cost_usd: Option<f64>,
    pub avg_cost_per_request: Option<f64>,
    pub cost_per_1k_tokens: Option<f64>,

    // ===== TIMESTAMP =====
    pub updated_at: DateTime<Utc>,
}

/// Rankings data from CLIProxyAPI
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelRanking {
    pub rank: u32,
    pub model_id: String,
    pub provider: String,
    pub quality_score: Option<f64>,
    pub estimated_cost: Option<f64>,
    pub latency_ms: Option<u32>,
    pub weekly_tokens: Option<u64>,
    pub market_share_percent: Option<f64>,
    pub category: Option<String>,
}

// =============================================================================
// API CLIENT
// =============================================================================

/// CLIProxyAPI metrics client
pub struct CLIProxyMetricsClient {
    http_client: Client,
    config: CLIProxyMetricsConfig,
}

impl CLIProxyMetricsClient {
    pub fn new(config: CLIProxyMetricsConfig) -> Self {
        Self {
            http_client: Client::new(),
            config,
        }
    }

    /// Fetch provider-level metrics
    pub async fn get_provider_metrics(&self) -> Result<Vec<ProviderMetrics>, reqwest::Error> {
        let url = format!("{}/v1/metrics/providers", self.config.base_url);

        let mut request = self.http_client.get(&url);
        if let Some(ref key) = self.config.api_key {
            request = request.header("Authorization", format!("Bearer {}", key));
        }

        let response = request.send().await?;
        let metrics: Vec<ProviderMetrics> = response.json().await?;

        info!("Fetched provider metrics for {} providers", metrics.len());
        Ok(metrics)
    }

    /// Fetch model-level metrics
    pub async fn get_model_metrics(&self) -> Result<Vec<ModelMetrics>, reqwest::Error> {
        let url = format!("{}/v1/metrics/models", self.config.base_url);

        let mut request = self.http_client.get(&url);
        if let Some(ref key) = self.config.api_key {
            request = request.header("Authorization", format!("Bearer {}", key));
        }

        let response = request.send().await?;
        let metrics: Vec<ModelMetrics> = response.json().await?;

        info!("Fetched model metrics for {} models", metrics.len());
        Ok(metrics)
    }

    /// Fetch rankings
    pub async fn get_rankings(
        &self,
        category: Option<&str>,
        limit: Option<u32>,
    ) -> Result<Vec<ModelRanking>, reqwest::Error> {
        let mut url = format!("{}/v1/rankings", self.config.base_url);

        let mut params = Vec::new();
        if let Some(cat) = category {
            params.push(format!("category={}", cat));
        }
        if let Some(l) = limit {
            params.push(format!("limit={}", l));
        }
        if !params.is_empty() {
            url = format!("{}?{}", url, params.join("&"));
        }

        let mut request = self.http_client.get(&url);
        if let Some(ref key) = self.config.api_key {
            request = request.header("Authorization", format!("Bearer {}", key));
        }

        let response = request.send().await?;
        #[derive(Deserialize)]
        struct RankingsResponse {
            rankings: Vec<ModelRanking>,
        }
        let result: RankingsResponse = response.json().await?;

        info!("Fetched {} rankings", result.rankings.len());
        Ok(result.rankings)
    }

    /// Fetch usage analytics
    pub async fn get_usage(&self) -> Result<UsageAnalytics, reqwest::Error> {
        let url = format!("{}/v1/usage", self.config.base_url);

        let mut request = self.http_client.get(&url);
        if let Some(ref key) = self.config.api_key {
            request = request.header("Authorization", format!("Bearer {}", key));
        }

        let response = request.send().await?;
        let usage: UsageAnalytics = response.json().await?;

        Ok(usage)
    }

    /// Check health
    pub async fn health_check(&self) -> Result<HealthStatus, reqwest::Error> {
        let url = format!("{}/health", self.config.base_url);

        let response = self.http_client.get(&url).send().await?;
        let health: HealthStatus = response.json().await?;

        Ok(health)
    }
}

/// Usage analytics response
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UsageAnalytics {
    pub period: String,
    pub total_requests: u64,
    pub total_tokens: u64,
    pub total_cost_usd: Option<f64>,
    pub by_provider: Vec<ProviderUsage>,
    pub by_model: Vec<ModelUsage>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderUsage {
    pub provider: String,
    pub requests: u64,
    pub tokens: u64,
    pub cost_usd: Option<f64>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ModelUsage {
    pub model: String,
    pub provider: String,
    pub requests: u64,
    pub tokens: u64,
    pub cost_usd: Option<f64>,
}

/// Health status
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HealthStatus {
    pub status: String,
    pub version: Option<String>,
    pub uptime_seconds: Option<u64>,
    pub providers: Vec<ProviderHealth>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProviderHealth {
    pub name: String,
    pub healthy: bool,
    pub latency_ms: Option<u32>,
    pub error_rate: Option<f64>,
}

// =============================================================================
// DERIVED METRICS CALCULATIONS
// =============================================================================

impl RequestMetrics {
    /// Calculate verbosity score (how verbose the response was)
    pub fn calculate_verbosity(&mut self) {
        if self.output_tokens > 0 && self.input_tokens > 0 {
            // Ratio of output to input - higher means more verbose
            self.verbosity_score = Some(self.output_tokens as f64 / self.input_tokens as f64);
        }
    }

    /// Calculate tokens per second
    pub fn calculate_tps(&mut self) {
        if let Some(latency) = self.total_latency_ms {
            if latency > 0.0 {
                self.tokens_per_second = Some(self.output_tokens as f64 / (latency / 1000.0));
            }
        }
    }

    /// Calculate cost based on pricing (requires pricing data)
    pub fn calculate_cost(&mut self, input_price_per_1m: f64, output_price_per_1m: f64) {
        self.cost_input_usd = Some(self.input_tokens as f64 * input_price_per_1m / 1_000_000.0);
        self.cost_output_usd = Some(self.output_tokens as f64 * output_price_per_1m / 1_000_000.0);
        self.cost_total_usd = self
            .cost_input_usd
            .map(|i| i + self.cost_output_usd.unwrap_or(0.0));

        if self.total_tokens > 0 {
            self.cost_per_1k_tokens = self
                .cost_total_usd
                .map(|c| c * 1000.0 / self.total_tokens as f64);
        }
    }
}

// =============================================================================
// TEST
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_request_metrics_calculations() {
        let mut metrics = RequestMetrics {
            request_id: "test-123".to_string(),
            model: "gpt-4o".to_string(),
            provider: "openai".to_string(),
            input_tokens: 1000,
            output_tokens: 500,
            total_tokens: 1500,
            ..Default::default()
        };

        // Set latency
        metrics.total_latency_ms = Some(1000.0); // 1 second

        // Calculate derived metrics
        metrics.calculate_verbosity();
        metrics.calculate_tps();
        metrics.calculate_cost(2.0, 8.0); // $2/1M input, $8/1M output

        assert_eq!(metrics.verbosity_score, Some(0.5)); // 500/1000
        assert_eq!(metrics.tokens_per_second, Some(500.0)); // 500 tokens in 1 second
        assert_eq!(metrics.cost_input_usd, Some(0.002)); // 1000 * 2 / 1M
        assert_eq!(metrics.cost_output_usd, Some(0.004)); // 500 * 8 / 1M
        assert_eq!(metrics.cost_total_usd, Some(0.006));
    }
}
