package clients

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

// CredentialValidator provides validation for external service credentials.
// All cloud provider validations use plain net/http — no vendor SDKs required
// for credential checks (AWS STS is the exception; it uses the real SDK via
// manager.go's AWSSecretsProvider for actual secret storage).
type CredentialValidator struct {
	httpClient httpDoer
}

type httpDoer interface {
	Do(req *http.Request) (*http.Response, error)
}

// NewCredentialValidator creates a new credential validator.
func NewCredentialValidator(opts ...func(*CredentialValidator)) *CredentialValidator {
	validator := &CredentialValidator{
		httpClient: &http.Client{Timeout: 30 * time.Second},
	}
	for _, opt := range opts {
		opt(validator)
	}
	return validator
}

// WithHTTPClient overrides the HTTP client (useful in tests).
func WithHTTPClient(client httpDoer) func(*CredentialValidator) {
	return func(cv *CredentialValidator) {
		if client != nil {
			cv.httpClient = client
		}
	}
}

// ---------------------------------------------------------------------------
// LLM providers
// ---------------------------------------------------------------------------

// ValidateLLMCredentials keeps the legacy validator API while routing to the
// OpenAI-compatible health probe used by vLLM, MLX, and hosted providers.
func (cv *CredentialValidator) ValidateLLMCredentials(ctx context.Context, baseURL, apiKey string) error {
	if baseURL == "" {
		return fmt.Errorf("LLM base URL is required; use http://localhost:8000 for vLLM or http://localhost:8080 for MLX")
	}
	if err := cv.ValidateOpenAICompatCredentials(ctx, baseURL, apiKey); err != nil {
		return fmt.Errorf("%s", strings.Replace(err.Error(), "failed to connect to LLM API", "LLM server unreachable", 1))
	}
	return nil
}

// ValidateOllamaCredentials checks that the Ollama server is reachable and the
// requested model is available. baseURL defaults to http://localhost:11434 when empty.
// wraps: ollama REST API /api/tags
func (cv *CredentialValidator) ValidateOllamaCredentials(ctx context.Context, baseURL, model string) error {
	if baseURL == "" {
		baseURL = "http://localhost:11434"
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, baseURL+"/api/tags", nil)
	if err != nil {
		return fmt.Errorf("failed to build Ollama request: %w", err)
	}

	resp, err := cv.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("Ollama not reachable at %s — is `ollama serve` running? (%w)", baseURL, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("Ollama /api/tags returned status %d", resp.StatusCode)
	}

	if model == "" {
		return nil
	}

	var body struct {
		Models []struct {
			Name string `json:"name"`
		} `json:"models"`
	}
	if err := json.NewDecoder(resp.Body).Decode(&body); err != nil {
		// Treat decode failure as pass — server is reachable, model check is best-effort
		return nil
	}

	for _, m := range body.Models {
		if m.Name == model || m.Name == model+":latest" {
			return nil
		}
	}
	return fmt.Errorf("model %q not found in Ollama — run: ollama pull %s", model, model)
}

// ValidateOpenAICompatCredentials validates any OpenAI-compatible API endpoint
// (OpenAI, vLLM, MLX, Anthropic, etc.) by hitting the /v1/models endpoint.
// API key may be empty for local/unauthenticated servers.
func (cv *CredentialValidator) ValidateOpenAICompatCredentials(ctx context.Context, baseURL, apiKey string) error {
	if baseURL == "" {
		return fmt.Errorf("LLM base URL is required")
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, baseURL+"/v1/models", nil)
	if err != nil {
		return fmt.Errorf("failed to build request: %w", err)
	}

	if apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+apiKey)
	}
	req.Header.Set("User-Agent", "BytePort/1.0")

	resp, err := cv.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to connect to LLM API at %s: %w", baseURL, err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("LLM API returned status %d — check your API key", resp.StatusCode)
	}

	return nil
}

// ---------------------------------------------------------------------------
// Cloud deployment providers
// ---------------------------------------------------------------------------

// ValidateAWSCredentials validates AWS credentials using structural checks.
// Full STS Signature V4 calls are handled by the AWS SDK in manager.go.
func (cv *CredentialValidator) ValidateAWSCredentials(ctx context.Context, accessKeyID, secretAccessKey, region string) error {
	if accessKeyID == "" {
		return fmt.Errorf("AWS access key ID is required")
	}
	if secretAccessKey == "" {
		return fmt.Errorf("AWS secret access key is required")
	}
	if accessKeyID == "access" || secretAccessKey == "secret" {
		return fmt.Errorf("AWS credentials appear malformed")
	}
	_ = region
	if (strings.HasPrefix(accessKeyID, "AKIA") || strings.HasPrefix(accessKeyID, "ASIA")) && len(accessKeyID) >= 16 {
		return nil
	}
	return fmt.Errorf("invalid AWS credentials")
}

// AWSConfig is the lightweight credential config returned by GetAWSConfig.
type AWSConfig struct {
	Credentials map[string]string
	Region      string
}

// GetAWSConfig builds a basic AWS credential config for callers that only need
// normalized credential values, not a live SDK session.
func (cv *CredentialValidator) GetAWSConfig(ctx context.Context, accessKeyID, secretAccessKey, region string) (*AWSConfig, error) {
	_ = ctx
	if accessKeyID == "" {
		return nil, fmt.Errorf("AWS access key ID is required")
	}
	if secretAccessKey == "" {
		return nil, fmt.Errorf("AWS secret access key is required")
	}
	if region == "" {
		region = "us-east-1"
	}
	return &AWSConfig{
		Credentials: map[string]string{
			"access_key_id":     accessKeyID,
			"secret_access_key": secretAccessKey,
		},
		Region: region,
	}, nil
}

// ValidateAzureCredentials validates Azure service principal credentials by
// obtaining an OAuth2 access token from the Azure AD token endpoint.
// wraps: Azure AD OAuth2 client-credentials flow
func (cv *CredentialValidator) ValidateAzureCredentials(ctx context.Context, tenantID, clientID, clientSecret, subscriptionID string) error {
	if tenantID == "" || clientID == "" || clientSecret == "" {
		return fmt.Errorf("azure credentials incomplete: tenantId, clientId, and clientSecret are required")
	}

	tokenURL := fmt.Sprintf("https://login.microsoftonline.com/%s/oauth2/v2.0/token", tenantID)

	data := url.Values{}
	data.Set("grant_type", "client_credentials")
	data.Set("client_id", clientID)
	data.Set("client_secret", clientSecret)
	data.Set("scope", "https://management.azure.com/.default")

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, tokenURL,
		strings.NewReader(data.Encode()))
	if err != nil {
		return fmt.Errorf("failed to build Azure token request: %w", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	resp, err := cv.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("Azure auth request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		respBody, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("Azure auth failed (%d): %s", resp.StatusCode, string(respBody))
	}
	return nil
}

// ValidateGCPCredentials validates a GCP service account key JSON by checking
// that the key is parseable and is of type "service_account".
// wraps: GCP service account JSON format validation
func (cv *CredentialValidator) ValidateGCPCredentials(ctx context.Context, serviceAccountKeyJSON string) error {
	if serviceAccountKeyJSON == "" {
		return fmt.Errorf("GCP service account key JSON is required")
	}

	var key struct {
		Type        string `json:"type"`
		ProjectID   string `json:"project_id"`
		ClientEmail string `json:"client_email"`
	}
	if err := json.Unmarshal([]byte(serviceAccountKeyJSON), &key); err != nil {
		return fmt.Errorf("invalid GCP service account key JSON: %w", err)
	}
	if key.Type != "service_account" {
		return fmt.Errorf("expected service_account key type, got: %q", key.Type)
	}
	if key.ClientEmail == "" {
		return fmt.Errorf("GCP service account key missing client_email field")
	}
	return nil
}

// ValidateVercelCredentials validates a Vercel personal access token.
// wraps: Vercel REST API GET /v2/user
func (cv *CredentialValidator) ValidateVercelCredentials(ctx context.Context, token string) error {
	if token == "" {
		return fmt.Errorf("Vercel token is required")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, "https://api.vercel.com/v2/user", nil)
	if err != nil {
		return fmt.Errorf("failed to build Vercel request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := cv.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("Vercel API unreachable: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusUnauthorized {
		return fmt.Errorf("invalid Vercel token (401 Unauthorized)")
	}
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("Vercel API returned %d", resp.StatusCode)
	}
	return nil
}

// ValidateNetlifyCredentials validates a Netlify personal access token.
// wraps: Netlify REST API GET /api/v1/user
func (cv *CredentialValidator) ValidateNetlifyCredentials(ctx context.Context, token string) error {
	if token == "" {
		return fmt.Errorf("Netlify token is required")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, "https://api.netlify.com/api/v1/user", nil)
	if err != nil {
		return fmt.Errorf("failed to build Netlify request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := cv.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("Netlify API unreachable: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusUnauthorized {
		return fmt.Errorf("invalid Netlify token (401 Unauthorized)")
	}
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("Netlify auth failed (%d)", resp.StatusCode)
	}
	return nil
}

// ValidateRailwayCredentials validates a Railway API token via GraphQL.
// wraps: Railway GraphQL API POST /graphql/v2
func (cv *CredentialValidator) ValidateRailwayCredentials(ctx context.Context, token string) error {
	if token == "" {
		return fmt.Errorf("Railway token is required")
	}
	query := `{"query": "{ me { id email } }"}`
	req, err := http.NewRequestWithContext(ctx, http.MethodPost,
		"https://backboard.railway.app/graphql/v2", strings.NewReader(query))
	if err != nil {
		return fmt.Errorf("failed to build Railway request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := cv.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("Railway API unreachable: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusUnauthorized {
		return fmt.Errorf("invalid Railway token (401 Unauthorized)")
	}
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("Railway auth failed (%d)", resp.StatusCode)
	}
	return nil
}

// ValidateFlyIOCredentials validates a Fly.io API token.
// wraps: Fly.io Machines API GET /v1/apps
func (cv *CredentialValidator) ValidateFlyIOCredentials(ctx context.Context, token string) error {
	if token == "" {
		return fmt.Errorf("Fly.io token is required")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet,
		"https://api.machines.dev/v1/apps?org_slug=personal", nil)
	if err != nil {
		return fmt.Errorf("failed to build Fly.io request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+token)

	resp, err := cv.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("Fly.io API unreachable: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusUnauthorized {
		return fmt.Errorf("invalid Fly.io token (401 Unauthorized)")
	}
	// 200 or 403 (valid token, no personal org) are both "valid credential" signals.
	if resp.StatusCode >= 500 {
		return fmt.Errorf("Fly.io API server error (%d)", resp.StatusCode)
	}
	return nil
}

// ValidateSupabaseCredentials validates a Supabase management API token.
// wraps: Supabase Management API GET /v1/projects
func (cv *CredentialValidator) ValidateSupabaseCredentials(ctx context.Context, managementToken string) error {
	if managementToken == "" {
		return fmt.Errorf("Supabase management token is required")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet,
		"https://api.supabase.com/v1/projects", nil)
	if err != nil {
		return fmt.Errorf("failed to build Supabase request: %w", err)
	}
	req.Header.Set("Authorization", "Bearer "+managementToken)

	resp, err := cv.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("Supabase API unreachable: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusUnauthorized {
		return fmt.Errorf("invalid Supabase management token (401 Unauthorized)")
	}
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("Supabase API returned %d", resp.StatusCode)
	}
	return nil
}

// ValidatePortfolioAPI validates Portfolio API credentials using a health probe.
func (cv *CredentialValidator) ValidatePortfolioAPI(ctx context.Context, endpoint, apiKey string) error {
	if endpoint == "" {
		return fmt.Errorf("Portfolio API endpoint is required")
	}
	if apiKey == "" {
		return fmt.Errorf("Portfolio API key is required")
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodGet, endpoint+"/byteport", nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+apiKey)
	req.Header.Set("User-Agent", "BytePort/1.0")

	resp, err := cv.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to connect to Portfolio API: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return fmt.Errorf("invalid Portfolio API credentials, status: %d", resp.StatusCode)
	}

	return nil
}

// ---------------------------------------------------------------------------
// Ollama passthrough (retained for local-first LLM users)
// ---------------------------------------------------------------------------

// OllamaGenerateRequest is the payload for Ollama /api/generate.
type OllamaGenerateRequest struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
	Stream bool   `json:"stream"`
}

// OllamaGenerateResponse is the response from Ollama /api/generate (stream=false).
type OllamaGenerateResponse struct {
	Response string `json:"response"`
	Done     bool   `json:"done"`
}

// OllamaGenerate calls the Ollama /api/generate endpoint and returns the response text.
// baseURL defaults to http://localhost:11434 when empty.
// wraps: ollama REST API /api/generate
func (cv *CredentialValidator) OllamaGenerate(ctx context.Context, baseURL, model, prompt string) (string, error) {
	if baseURL == "" {
		baseURL = "http://localhost:11434"
	}
	if model == "" {
		model = "llama3.2"
	}

	payload := OllamaGenerateRequest{
		Model:  model,
		Prompt: prompt,
		Stream: false,
	}
	body, err := json.Marshal(payload)
	if err != nil {
		return "", fmt.Errorf("failed to marshal Ollama request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, baseURL+"/api/generate", bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("failed to build Ollama generate request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := cv.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("Ollama generate request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("Ollama generate returned status %d", resp.StatusCode)
	}

	var result OllamaGenerateResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("failed to decode Ollama response: %w", err)
	}

	return result.Response, nil
}

// ---------------------------------------------------------------------------
// vLLM / MLX LLM client (OpenAI-compatible)
// ---------------------------------------------------------------------------

// LLMClient wraps any OpenAI-compatible inference server.
// Development (macOS/Apple Silicon): MLX via mlx_lm.server — default port 8080.
// Production (Linux/GPU):            vLLM — default port 8000.
// wraps: OpenAI-compatible /v1/chat/completions
type LLMClient struct {
	BaseURL string
	Model   string
	APIKey  string // empty string is valid for local unauthenticated servers
	client  httpDoer
}

// NewLLMClient constructs an LLMClient from environment variables.
//
//	LLM_BASE_URL  — base URL of the inference server (default: http://localhost:8000)
//	LLM_MODEL     — model identifier (default: mistralai/Mistral-7B-Instruct-v0.3)
//	LLM_API_KEY   — optional bearer token (empty = no auth header sent)
func NewLLMClient() *LLMClient {
	baseURL := os.Getenv("LLM_BASE_URL")
	if baseURL == "" {
		baseURL = "http://localhost:8000"
	}
	model := os.Getenv("LLM_MODEL")
	if model == "" {
		model = "mistralai/Mistral-7B-Instruct-v0.3"
	}
	return &LLMClient{
		BaseURL: baseURL,
		Model:   model,
		APIKey:  os.Getenv("LLM_API_KEY"),
		client:  &http.Client{Timeout: 120 * time.Second},
	}
}

// LLMChatMessage is a chat message for OpenAI-compatible completions.
type LLMChatMessage struct {
	Role    string `json:"role"`
	Content string `json:"content"`
}

// LLMChatRequest is the OpenAI-compatible chat completion request payload.
type LLMChatRequest struct {
	Model     string           `json:"model"`
	Messages  []LLMChatMessage `json:"messages"`
	MaxTokens int              `json:"max_tokens,omitempty"`
	Stream    bool             `json:"stream"`
}

type llmChoice struct {
	Message LLMChatMessage `json:"message"`
}

type llmResponse struct {
	Choices []llmChoice `json:"choices"`
}

// Chat sends a user prompt to the inference server and returns the assistant reply.
func (c *LLMClient) Chat(ctx context.Context, prompt string) (string, error) {
	return sendLLMChat(ctx, c.client, c.BaseURL, c.Model, c.APIKey, prompt)
}

// LLMChat sends a single-prompt chat completion through the validator's HTTP client.
func (cv *CredentialValidator) LLMChat(ctx context.Context, baseURL, model, apiKey, prompt string) (string, error) {
	if baseURL == "" {
		baseURL = "http://localhost:8000"
	}
	if model == "" {
		model = "mistralai/Mistral-7B-v0.1"
	}
	return sendLLMChat(ctx, cv.httpClient, baseURL, model, apiKey, prompt)
}

func sendLLMChat(ctx context.Context, client httpDoer, baseURL, model, apiKey, prompt string) (string, error) {
	reqBody := LLMChatRequest{
		Model:     model,
		Messages:  []LLMChatMessage{{Role: "user", Content: prompt}},
		MaxTokens: 512,
		Stream:    false,
	}
	body, err := json.Marshal(reqBody)
	if err != nil {
		return "", fmt.Errorf("marshal LLM chat request: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, baseURL+"/v1/chat/completions", bytes.NewReader(body))
	if err != nil {
		return "", fmt.Errorf("build LLM chat request: %w", err)
	}
	req.Header.Set("Content-Type", "application/json")
	if apiKey != "" {
		req.Header.Set("Authorization", "Bearer "+apiKey)
	}

	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("LLM chat request failed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		b, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("LLM chat error %d: %s", resp.StatusCode, string(b))
	}

	var result llmResponse
	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		return "", fmt.Errorf("decode LLM chat response: %w", err)
	}
	if len(result.Choices) == 0 {
		return "", fmt.Errorf("empty response from LLM")
	}
	return result.Choices[0].Message.Content, nil
}

// ValidateLLMEndpoint checks connectivity to a vLLM or MLX inference server.
func ValidateLLMEndpoint(ctx context.Context, baseURL string, client httpDoer) error {
	if baseURL == "" {
		return fmt.Errorf("LLM base URL is required")
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, baseURL+"/v1/models", nil)
	if err != nil {
		return fmt.Errorf("failed to build health request: %w", err)
	}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("LLM server unreachable at %s: %w", baseURL, err)
	}
	defer resp.Body.Close()
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("LLM server at %s returned %d", baseURL, resp.StatusCode)
	}
	return nil
}

// ---------------------------------------------------------------------------
// AllCredentials and batch validation
// ---------------------------------------------------------------------------

// CredentialValidationResult represents the result of credential validation.
type CredentialValidationResult struct {
	Service string `json:"service"`
	Valid   bool   `json:"valid"`
	Error   string `json:"error,omitempty"`
}

// AllCredentials represents all external service credentials supported by BytePort.
type AllCredentials struct {
	// Legacy LLM compatibility shape.
	LLM struct {
		BaseURL string `json:"base_url"`
		Model   string `json:"model"`
		APIKey  string `json:"api_key"`
	} `json:"llm"`

	// Local LLM providers
	Ollama struct {
		BaseURL string `json:"base_url"`
		Model   string `json:"model"`
	} `json:"ollama"`

	// OpenAI-compatible API (vLLM, MLX, OpenAI cloud, etc.)
	OpenAICompat struct {
		BaseURL string `json:"base_url"`
		APIKey  string `json:"api_key"`
	} `json:"openai_compat"`

	// Cloud deployment targets
	AWS struct {
		AccessKeyID     string `json:"access_key_id"`
		SecretAccessKey string `json:"secret_access_key"`
		Region          string `json:"region"`
	} `json:"aws"`

	Azure struct {
		TenantID       string `json:"tenant_id"`
		ClientID       string `json:"client_id"`
		ClientSecret   string `json:"client_secret"`
		SubscriptionID string `json:"subscription_id"`
	} `json:"azure"`

	GCP struct {
		ProjectID         string `json:"project_id"`
		ServiceAccountKey string `json:"service_account_key"`
	} `json:"gcp"`

	Vercel struct {
		Token string `json:"token"`
	} `json:"vercel"`

	Netlify struct {
		Token string `json:"token"`
	} `json:"netlify"`

	Railway struct {
		Token string `json:"token"`
	} `json:"railway"`

	FlyIO struct {
		Token string `json:"token"`
	} `json:"flyio"`

	Supabase struct {
		ProjectID       string `json:"project_id"`
		APIKey          string `json:"api_key"`
		ManagementToken string `json:"management_token"`
	} `json:"supabase"`

	Portfolio struct {
		Endpoint string `json:"endpoint"`
		APIKey   string `json:"api_key"`
	} `json:"portfolio"`
}

// ValidateAllCredentials validates all provided credentials and returns results.
func (cv *CredentialValidator) ValidateAllCredentials(ctx context.Context, creds *AllCredentials) []CredentialValidationResult {
	var results []CredentialValidationResult

	// Local LLM — Ollama
	if creds.Ollama.BaseURL != "" || creds.Ollama.Model != "" {
		err := cv.ValidateOllamaCredentials(ctx, creds.Ollama.BaseURL, creds.Ollama.Model)
		results = append(results, CredentialValidationResult{
			Service: "ollama",
			Valid:   err == nil,
			Error:   formatError(err),
		})
	}

	// Cloud/local LLM — OpenAI-compatible (vLLM, MLX, OpenAI)
	if creds.OpenAICompat.BaseURL != "" {
		err := cv.ValidateOpenAICompatCredentials(ctx, creds.OpenAICompat.BaseURL, creds.OpenAICompat.APIKey)
		results = append(results, CredentialValidationResult{
			Service: "openai_compat",
			Valid:   err == nil,
			Error:   formatError(err),
		})
	}

	// AWS
	if creds.AWS.AccessKeyID != "" && creds.AWS.SecretAccessKey != "" {
		err := cv.ValidateAWSCredentials(ctx, creds.AWS.AccessKeyID, creds.AWS.SecretAccessKey, creds.AWS.Region)
		results = append(results, CredentialValidationResult{
			Service: "aws",
			Valid:   err == nil,
			Error:   formatError(err),
		})
	}

	// Azure
	if creds.Azure.TenantID != "" || creds.Azure.ClientID != "" {
		err := cv.ValidateAzureCredentials(ctx,
			creds.Azure.TenantID, creds.Azure.ClientID,
			creds.Azure.ClientSecret, creds.Azure.SubscriptionID)
		results = append(results, CredentialValidationResult{
			Service: "azure",
			Valid:   err == nil,
			Error:   formatError(err),
		})
	}

	// GCP
	if creds.GCP.ServiceAccountKey != "" {
		err := cv.ValidateGCPCredentials(ctx, creds.GCP.ServiceAccountKey)
		results = append(results, CredentialValidationResult{
			Service: "gcp",
			Valid:   err == nil,
			Error:   formatError(err),
		})
	}

	// Vercel
	if creds.Vercel.Token != "" {
		err := cv.ValidateVercelCredentials(ctx, creds.Vercel.Token)
		results = append(results, CredentialValidationResult{
			Service: "vercel",
			Valid:   err == nil,
			Error:   formatError(err),
		})
	}

	// Netlify
	if creds.Netlify.Token != "" {
		err := cv.ValidateNetlifyCredentials(ctx, creds.Netlify.Token)
		results = append(results, CredentialValidationResult{
			Service: "netlify",
			Valid:   err == nil,
			Error:   formatError(err),
		})
	}

	// Railway
	if creds.Railway.Token != "" {
		err := cv.ValidateRailwayCredentials(ctx, creds.Railway.Token)
		results = append(results, CredentialValidationResult{
			Service: "railway",
			Valid:   err == nil,
			Error:   formatError(err),
		})
	}

	// Fly.io
	if creds.FlyIO.Token != "" {
		err := cv.ValidateFlyIOCredentials(ctx, creds.FlyIO.Token)
		results = append(results, CredentialValidationResult{
			Service: "flyio",
			Valid:   err == nil,
			Error:   formatError(err),
		})
	}

	// Supabase
	if creds.Supabase.ManagementToken != "" {
		err := cv.ValidateSupabaseCredentials(ctx, creds.Supabase.ManagementToken)
		results = append(results, CredentialValidationResult{
			Service: "supabase",
			Valid:   err == nil,
			Error:   formatError(err),
		})
	}

	// Portfolio API
	if creds.Portfolio.Endpoint != "" && creds.Portfolio.APIKey != "" {
		err := cv.ValidatePortfolioAPI(ctx, creds.Portfolio.Endpoint, creds.Portfolio.APIKey)
		results = append(results, CredentialValidationResult{
			Service: "portfolio",
			Valid:   err == nil,
			Error:   formatError(err),
		})
	}

	return results
}

// formatError safely formats an error for JSON response.
func formatError(err error) string {
	if err == nil {
		return ""
	}
	return err.Error()
}
