package secrets

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"sync"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	awsconfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/secretsmanager"
	vault "github.com/hashicorp/vault/api"
)

// Manager provides production-ready secrets management with multiple backends
type Manager struct {
	providers map[string]Provider
	order     []string
	cache     map[string]*cachedSecret
	cacheMux  sync.RWMutex
	cacheTTL  time.Duration
}

// Provider defines the interface for secret storage backends
type Provider interface {
	GetSecret(ctx context.Context, key string) (string, error)
	SetSecret(ctx context.Context, key string, value string) error
	DeleteSecret(ctx context.Context, key string) error
	ListSecrets(ctx context.Context) ([]string, error)
}

// Config holds configuration for the secrets manager
type Config struct {
	CacheTTL time.Duration
}

// New creates a new secrets manager with the specified configuration
func New(config Config) *Manager {
	if config.CacheTTL == 0 {
		config.CacheTTL = 5 * time.Minute
	}

	return &Manager{
		providers: make(map[string]Provider),
		order:     make([]string, 0),
		cache:     make(map[string]*cachedSecret),
		cacheTTL:  config.CacheTTL,
	}
}

// RegisterProvider adds a new secret provider
func (m *Manager) RegisterProvider(name string, provider Provider) {
	if _, exists := m.providers[name]; !exists {
		m.order = append(m.order, name)
	}
	m.providers[name] = provider
}

// GetSecret retrieves a secret from the first available provider (with caching)
func (m *Manager) GetSecret(ctx context.Context, key string) (string, error) {
	// Check cache first
	m.cacheMux.RLock()
	if cached, exists := m.cache[key]; exists && time.Now().Before(cached.expiresAt) {
		m.cacheMux.RUnlock()
		return cached.value, nil
	}
	m.cacheMux.RUnlock()

	// Try providers in registration order
	for _, name := range m.order {
		provider := m.providers[name]
		value, err := provider.GetSecret(ctx, key)
		if err == nil {
			// Cache the result
			m.cacheMux.Lock()
			m.cache[key] = &cachedSecret{
				value:     value,
				expiresAt: time.Now().Add(m.cacheTTL),
			}
			m.cacheMux.Unlock()
			return value, nil
		}
	}

	return "", fmt.Errorf("secret '%s' not found in any provider", key)
}

// SetSecret stores a secret in the primary provider
func (m *Manager) SetSecret(ctx context.Context, key string, value string) error {
	// Use the first available provider as primary
	for _, name := range m.order {
		provider := m.providers[name]
		err := provider.SetSecret(ctx, key, value)
		if err == nil {
			// Invalidate cache
			m.cacheMux.Lock()
			delete(m.cache, key)
			m.cacheMux.Unlock()
			return nil
		}
	}
	return fmt.Errorf("failed to store secret '%s' in any provider", key)
}

// InvalidateCache removes a secret from cache
func (m *Manager) InvalidateCache(key string) {
	m.cacheMux.Lock()
	defer m.cacheMux.Unlock()
	delete(m.cache, key)
}

// ClearCache removes all cached secrets
func (m *Manager) ClearCache() {
	m.cacheMux.Lock()
	defer m.cacheMux.Unlock()
	m.cache = make(map[string]*cachedSecret)
}

// AWSSecretsProvider is a Provider backed by AWS Secrets Manager.
// wraps: github.com/aws/aws-sdk-go-v2/service/secretsmanager
type AWSSecretsProvider struct {
	client *secretsmanager.Client
	region string
}

// NewAWSSecretsProvider creates a new AWS Secrets Manager provider using the default
// credential chain (env vars, ~/.aws/credentials, IAM instance role, etc.).
// region defaults to "us-east-1" if empty.
func NewAWSSecretsProvider(ctx context.Context, region string) (*AWSSecretsProvider, error) {
	if region == "" {
		region = "us-east-1"
	}
	cfg, err := awsconfig.LoadDefaultConfig(ctx, awsconfig.WithRegion(region))
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config: %w", err)
	}
	return &AWSSecretsProvider{
		client: secretsmanager.NewFromConfig(cfg),
		region: region,
	}, nil
}

// NewAWSSecretsProviderWithCredentials creates an AWS Secrets Manager provider with explicit
// static credentials. Useful for configuration-file driven deployments.
// wraps: github.com/aws/aws-sdk-go-v2/credentials.NewStaticCredentialsProvider
func NewAWSSecretsProviderWithCredentials(ctx context.Context, accessKeyID, secretAccessKey, region string) (*AWSSecretsProvider, error) {
	if region == "" {
		region = "us-east-1"
	}
	cfg, err := awsconfig.LoadDefaultConfig(ctx,
		awsconfig.WithRegion(region),
		awsconfig.WithCredentialsProvider(
			credentials.NewStaticCredentialsProvider(accessKeyID, secretAccessKey, ""),
		),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to load AWS config with credentials: %w", err)
	}
	return &AWSSecretsProvider{
		client: secretsmanager.NewFromConfig(cfg),
		region: region,
	}, nil
}

func (p *AWSSecretsProvider) GetSecret(ctx context.Context, key string) (string, error) {
	out, err := p.client.GetSecretValue(ctx, &secretsmanager.GetSecretValueInput{
		SecretId: aws.String(key),
	})
	if err != nil {
		return "", fmt.Errorf("failed to get secret from AWS '%s': %w", key, err)
	}
	if out.SecretString != nil {
		return *out.SecretString, nil
	}
	return "", fmt.Errorf("failed to get secret from AWS '%s': no string value", key)
}

func (p *AWSSecretsProvider) SetSecret(ctx context.Context, key string, value string) error {
	// Try to update first; if the secret doesn't exist, create it.
	_, err := p.client.UpdateSecret(ctx, &secretsmanager.UpdateSecretInput{
		SecretId:     aws.String(key),
		SecretString: aws.String(value),
	})
	if err == nil {
		return nil
	}
	// Secret may not exist — attempt creation.
	_, createErr := p.client.CreateSecret(ctx, &secretsmanager.CreateSecretInput{
		Name:         aws.String(key),
		SecretString: aws.String(value),
	})
	if createErr != nil {
		return fmt.Errorf("failed to set secret in AWS '%s': update=%v, create=%v", key, err, createErr)
	}
	return nil
}

func (p *AWSSecretsProvider) DeleteSecret(ctx context.Context, key string) error {
	_, err := p.client.DeleteSecret(ctx, &secretsmanager.DeleteSecretInput{
		SecretId:                   aws.String(key),
		ForceDeleteWithoutRecovery: aws.Bool(true),
	})
	if err != nil {
		return fmt.Errorf("failed to delete secret from AWS '%s': %w", key, err)
	}
	return nil
}

func (p *AWSSecretsProvider) ListSecrets(ctx context.Context) ([]string, error) {
	var names []string
	paginator := secretsmanager.NewListSecretsPaginator(p.client, &secretsmanager.ListSecretsInput{})
	for paginator.HasMorePages() {
		page, err := paginator.NextPage(ctx)
		if err != nil {
			return nil, fmt.Errorf("failed to list secrets from AWS: %w", err)
		}
		for _, s := range page.SecretList {
			if s.Name != nil {
				names = append(names, *s.Name)
			}
		}
	}
	return names, nil
}

// HashiCorp Vault Provider
type VaultProvider struct {
	client *vault.Client
	path   string
}

// NewVaultProvider creates a new HashiCorp Vault provider
func NewVaultProvider(address, token, path string) (*VaultProvider, error) {
	client, err := vault.NewClient(&vault.Config{
		Address: address,
	})
	if err != nil {
		return nil, fmt.Errorf("failed to create Vault client: %w", err)
	}

	client.SetToken(token)

	return &VaultProvider{
		client: client,
		path:   path,
	}, nil
}

func (p *VaultProvider) GetSecret(ctx context.Context, key string) (string, error) {
	secret, err := p.client.KVv2(p.path).Get(ctx, key)
	if err != nil {
		return "", fmt.Errorf("failed to get secret from Vault: %w", err)
	}

	if value, ok := secret.Data["value"].(string); ok {
		return value, nil
	}

	return "", fmt.Errorf("secret '%s' has no string value", key)
}

func (p *VaultProvider) SetSecret(ctx context.Context, key string, value string) error {
	data := map[string]interface{}{
		"value": value,
	}

	_, err := p.client.KVv2(p.path).Put(ctx, key, data)
	if err != nil {
		return fmt.Errorf("failed to set secret in Vault: %w", err)
	}

	return nil
}

func (p *VaultProvider) DeleteSecret(ctx context.Context, key string) error {
	err := p.client.KVv2(p.path).Delete(ctx, key)
	if err != nil {
		return fmt.Errorf("failed to delete secret from Vault: %w", err)
	}

	return nil
}

func (p *VaultProvider) ListSecrets(ctx context.Context) ([]string, error) {
	// Use Logical().List() for listing secrets
	secret, err := p.client.Logical().List(p.path)
	if err != nil {
		return nil, fmt.Errorf("failed to list secrets from Vault: %w", err)
	}

	// Extract the list of keys
	var secrets []string
	if secret != nil && secret.Data != nil {
		if keysRaw, ok := secret.Data["keys"]; ok {
			if keys, ok := keysRaw.([]interface{}); ok {
				for _, key := range keys {
					if keyStr, ok := key.(string); ok {
						secrets = append(secrets, keyStr)
					}
				}
			}
		}
	}

	return secrets, nil
}

// Environment Provider (fallback)
type EnvironmentProvider struct{}

func NewEnvironmentProvider() *EnvironmentProvider {
	return &EnvironmentProvider{}
}

func (e *EnvironmentProvider) GetSecret(ctx context.Context, key string) (string, error) {
	value := os.Getenv(key)
	if value == "" {
		return "", fmt.Errorf("environment variable '%s' not found", key)
	}
	return value, nil
}

func (e *EnvironmentProvider) SetSecret(ctx context.Context, key string, value string) error {
	return os.Setenv(key, value)
}

func (e *EnvironmentProvider) DeleteSecret(ctx context.Context, key string) error {
	return os.Unsetenv(key)
}

func (e *EnvironmentProvider) ListSecrets(ctx context.Context) ([]string, error) {
	env := os.Environ()
	secrets := make([]string, len(env))
	for i, pair := range env {
		// Extract key from "KEY=VALUE" format
		for j, char := range pair {
			if char == '=' {
				secrets[i] = pair[:j]
				break
			}
		}
	}
	return secrets, nil
}

// Common secret keys
const (
	SecretWorkOSClientID     = "WORKOS_CLIENT_ID"
	SecretWorkOSClientSecret = "WORKOS_CLIENT_SECRET"
	SecretWorkOSAPIKey       = "WORKOS_API_KEY"
	SecretAWSAccessKeyID     = "AWS_ACCESS_KEY_ID"
	SecretAWSSecretAccessKey = "AWS_SECRET_ACCESS_KEY"
	SecretAWSRegion          = "AWS_REGION"
	SecretPortfolioAPIKey    = "PORTFOLIO_API_KEY"
	SecretPortfolioEndpoint  = "PORTFOLIO_ROOT_ENDPOINT"
	SecretDatabaseURL        = "DATABASE_URL"
	// LLM backend secrets — vLLM (Linux/prod) or MLX (macOS/Apple Silicon).
	// Both expose an OpenAI-compatible API; the same env vars cover both.
	// vLLM default port: 8000 — start with: vllm serve <model>
	// MLX default port:  8080 — start with: mlx_lm.server --model <model>
	SecretLLMBaseURL = "LLM_BASE_URL"
	SecretLLMModel   = "LLM_MODEL"
	SecretLLMAPIKey  = "LLM_API_KEY"

	// Azure deployment target secrets
	SecretAzureTenantID       = "AZURE_TENANT_ID"
	SecretAzureClientID       = "AZURE_CLIENT_ID"
	SecretAzureClientSecret   = "AZURE_CLIENT_SECRET"
	SecretAzureSubscriptionID = "AZURE_SUBSCRIPTION_ID"

	// GCP deployment target secrets
	SecretGCPProjectID          = "GCP_PROJECT_ID"
	SecretGCPServiceAccountKey  = "GCP_SERVICE_ACCOUNT_KEY"

	// Vercel deployment target secrets
	SecretVercelToken = "VERCEL_TOKEN"

	// Netlify deployment target secrets
	SecretNetlifyToken = "NETLIFY_TOKEN"

	// Railway deployment target secrets
	SecretRailwayToken = "RAILWAY_TOKEN"

	// Fly.io deployment target secrets
	SecretFlyIOToken = "FLY_API_TOKEN"

	// Supabase deployment target secrets
	SecretSupabaseProjectID        = "SUPABASE_PROJECT_ID"
	SecretSupabaseAPIKey           = "SUPABASE_API_KEY"
	SecretSupabaseManagementToken  = "SUPABASE_MANAGEMENT_TOKEN"
)

// Service configuration helpers
func (m *Manager) GetWorkOSConfig(ctx context.Context) (clientID, clientSecret, apiKey string, err error) {
	clientID, err = m.GetSecret(ctx, SecretWorkOSClientID)
	if err != nil {
		return "", "", "", err
	}

	clientSecret, err = m.GetSecret(ctx, SecretWorkOSClientSecret)
	if err != nil {
		return "", "", "", err
	}

	apiKey, err = m.GetSecret(ctx, SecretWorkOSAPIKey)
	if err != nil {
		return "", "", "", err
	}

	return clientID, clientSecret, apiKey, nil
}

func (m *Manager) GetAWSConfig(ctx context.Context) (accessKey, secretKey, region string, err error) {
	accessKey, err = m.GetSecret(ctx, SecretAWSAccessKeyID)
	if err != nil {
		return "", "", "", err
	}

	secretKey, err = m.GetSecret(ctx, SecretAWSSecretAccessKey)
	if err != nil {
		return "", "", "", err
	}

	region, err = m.GetSecret(ctx, SecretAWSRegion)
	if err != nil {
		// Default to us-east-1 if not specified
		region = "us-east-1"
	}

	return accessKey, secretKey, region, nil
}

// GetLLMConfig returns the LLM base URL, model, and optional API key.
// Supports vLLM (Linux/prod, default port 8000) and MLX (macOS/Apple Silicon, default port 8080).
// Defaults to http://localhost:8000 and mistralai/Mistral-7B-v0.1 when not configured.
func (m *Manager) GetLLMConfig(ctx context.Context) (baseURL, model, apiKey string, err error) {
	baseURL, err = m.GetSecret(ctx, SecretLLMBaseURL)
	if err != nil || baseURL == "" {
		baseURL = "http://localhost:8000"
	}
	model, err = m.GetSecret(ctx, SecretLLMModel)
	if err != nil || model == "" {
		model = "mistralai/Mistral-7B-v0.1"
	}
	apiKey, _ = m.GetSecret(ctx, SecretLLMAPIKey) // optional — empty is fine for local servers
	return baseURL, model, apiKey, nil
}

func (m *Manager) GetPortfolioConfig(ctx context.Context) (apiKey, endpoint string, err error) {
	apiKey, err = m.GetSecret(ctx, SecretPortfolioAPIKey)
	if err != nil {
		return "", "", err
	}

	endpoint, err = m.GetSecret(ctx, SecretPortfolioEndpoint)
	if err != nil {
		return "", "", err
	}

	return apiKey, endpoint, nil
}

// GetOpenAIConfig returns the OpenAI-compatible API key (alias for the LLM API key).
// This supports both cloud OpenAI and local vLLM/MLX inference servers.
func (m *Manager) GetOpenAIConfig(ctx context.Context) (apiKey string, err error) {
	apiKey, err = m.GetSecret(ctx, SecretLLMAPIKey)
	if err != nil {
		return "", err
	}
	return apiKey, nil
}

// GetAzureConfig returns Azure service principal credentials for deployment targets.
func (m *Manager) GetAzureConfig(ctx context.Context) (tenantID, clientID, clientSecret, subscriptionID string, err error) {
	tenantID, err = m.GetSecret(ctx, SecretAzureTenantID)
	if err != nil {
		return "", "", "", "", err
	}
	clientID, err = m.GetSecret(ctx, SecretAzureClientID)
	if err != nil {
		return "", "", "", "", err
	}
	clientSecret, err = m.GetSecret(ctx, SecretAzureClientSecret)
	if err != nil {
		return "", "", "", "", err
	}
	subscriptionID, _ = m.GetSecret(ctx, SecretAzureSubscriptionID) // optional
	return tenantID, clientID, clientSecret, subscriptionID, nil
}

// GetGCPConfig returns GCP credentials for deployment targets.
func (m *Manager) GetGCPConfig(ctx context.Context) (projectID, serviceAccountKey string, err error) {
	projectID, err = m.GetSecret(ctx, SecretGCPProjectID)
	if err != nil {
		return "", "", err
	}
	serviceAccountKey, err = m.GetSecret(ctx, SecretGCPServiceAccountKey)
	if err != nil {
		return "", "", err
	}
	return projectID, serviceAccountKey, nil
}

// GetVercelConfig returns the Vercel API token.
func (m *Manager) GetVercelConfig(ctx context.Context) (token string, err error) {
	return m.GetSecret(ctx, SecretVercelToken)
}

// GetNetlifyConfig returns the Netlify API token.
func (m *Manager) GetNetlifyConfig(ctx context.Context) (token string, err error) {
	return m.GetSecret(ctx, SecretNetlifyToken)
}

// GetRailwayConfig returns the Railway API token.
func (m *Manager) GetRailwayConfig(ctx context.Context) (token string, err error) {
	return m.GetSecret(ctx, SecretRailwayToken)
}

// GetFlyIOConfig returns the Fly.io API token.
func (m *Manager) GetFlyIOConfig(ctx context.Context) (token string, err error) {
	return m.GetSecret(ctx, SecretFlyIOToken)
}

// GetSupabaseConfig returns Supabase credentials.
func (m *Manager) GetSupabaseConfig(ctx context.Context) (projectID, apiKey, managementToken string, err error) {
	projectID, _ = m.GetSecret(ctx, SecretSupabaseProjectID)
	apiKey, _ = m.GetSecret(ctx, SecretSupabaseAPIKey)
	managementToken, err = m.GetSecret(ctx, SecretSupabaseManagementToken)
	if err != nil {
		return "", "", "", err
	}
	return projectID, apiKey, managementToken, nil
}

// SecretRotation handles automatic secret rotation
type rotationTask struct {
	key      string
	interval time.Duration
	rotator  func(context.Context, *Manager) error
	lastRun  time.Time
}

// SecretRotation coordinates background rotation for secrets along with cache invalidation.
type SecretRotation struct {
	manager    *Manager
	interval   time.Duration
	stopCh     chan struct{}
	mu         sync.RWMutex
	tasks      map[string]*rotationTask
	onError    func(string, error)
	tickerFunc func(time.Duration) *time.Ticker
}

// NewSecretRotation creates a new secret rotation manager.
func NewSecretRotation(manager *Manager, interval time.Duration) *SecretRotation {
	if interval <= 0 {
		interval = 5 * time.Minute
	}
	return &SecretRotation{
		manager:    manager,
		interval:   interval,
		stopCh:     make(chan struct{}),
		tasks:      make(map[string]*rotationTask),
		tickerFunc: time.NewTicker,
	}
}

// Register adds a rotation task for the specified secret key. The provided rotator will be invoked
// at the supplied interval. If interval is zero, the rotation manager's base interval is used.
func (sr *SecretRotation) Register(key string, interval time.Duration, rotator func(context.Context, *Manager) error) error {
	if key == "" {
		return fmt.Errorf("rotation key cannot be empty")
	}
	if rotator == nil {
		return fmt.Errorf("rotation function cannot be nil")
	}
	if interval <= 0 {
		interval = sr.interval
	}

	sr.mu.Lock()
	defer sr.mu.Unlock()
	sr.tasks[key] = &rotationTask{
		key:      key,
		interval: interval,
		rotator:  rotator,
	}
	return nil
}

// Unregister removes a rotation task by key.
func (sr *SecretRotation) Unregister(key string) {
	sr.mu.Lock()
	defer sr.mu.Unlock()
	delete(sr.tasks, key)
}

// SetErrorHandler allows callers to observe rotation errors.
func (sr *SecretRotation) SetErrorHandler(handler func(key string, err error)) {
	sr.mu.Lock()
	defer sr.mu.Unlock()
	sr.onError = handler
}

// Start begins the automatic secret rotation process.
func (sr *SecretRotation) Start(ctx context.Context) {
	ticker := sr.tickerFunc(sr.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return
		case <-sr.stopCh:
			return
		case <-ticker.C:
			sr.rotateSecrets(ctx)
		}
	}
}

// Stop stops the automatic secret rotation.
func (sr *SecretRotation) Stop() {
	select {
	case <-sr.stopCh:
		// already closed
	default:
		close(sr.stopCh)
	}
}

// RunOnce triggers a rotation cycle immediately. Useful for tests.
func (sr *SecretRotation) RunOnce(ctx context.Context) {
	sr.rotateSecrets(ctx)
}

func (sr *SecretRotation) rotateSecrets(ctx context.Context) {
	// Always clear cache so subsequent reads fetch fresh values.
	sr.manager.ClearCache()

	sr.mu.RLock()
	tasks := make([]*rotationTask, 0, len(sr.tasks))
	for _, task := range sr.tasks {
		tasks = append(tasks, &rotationTask{
			key:      task.key,
			interval: task.interval,
			rotator:  task.rotator,
			lastRun:  task.lastRun,
		})
	}
	handler := sr.onError
	sr.mu.RUnlock()

	for _, task := range tasks {
		if time.Since(task.lastRun) < task.interval {
			continue
		}
		if err := task.rotator(ctx, sr.manager); err != nil {
			if handler != nil {
				handler(task.key, err)
			}
			continue
		}
		// Persist last run timestamp.
		sr.mu.Lock()
		if liveTask, ok := sr.tasks[task.key]; ok {
			liveTask.lastRun = time.Now()
		}
		sr.mu.Unlock()
	}
}

// Secret represents a structured secret with metadata
type Secret struct {
	Key       string            `json:"key"`
	Value     string            `json:"value"`
	Metadata  map[string]string `json:"metadata,omitempty"`
	CreatedAt time.Time         `json:"created_at"`
	UpdatedAt time.Time         `json:"updated_at"`
	ExpiresAt *time.Time        `json:"expires_at,omitempty"`
}

// StructuredSecret handles complex secret structures
type StructuredSecret struct {
	manager *Manager
}

// NewStructuredSecret creates a structured secret handler
func NewStructuredSecret(manager *Manager) *StructuredSecret {
	return &StructuredSecret{manager: manager}
}

// GetJSONSecret retrieves and unmarshals a JSON secret
func (ss *StructuredSecret) GetJSONSecret(ctx context.Context, key string, dest interface{}) error {
	secretStr, err := ss.manager.GetSecret(ctx, key)
	if err != nil {
		return err
	}

	return json.Unmarshal([]byte(secretStr), dest)
}

// SetJSONSecret marshals and stores a JSON secret
func (ss *StructuredSecret) SetJSONSecret(ctx context.Context, key string, value interface{}) error {
	secretBytes, err := json.Marshal(value)
	if err != nil {
		return fmt.Errorf("failed to marshal secret: %w", err)
	}

	return ss.manager.SetSecret(ctx, key, string(secretBytes))
}

type cachedSecret struct {
	value     string
	expiresAt time.Time
}
