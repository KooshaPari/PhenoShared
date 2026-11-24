package secrets

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"sync"
	"sync/atomic"
	"testing"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/credentials"
	"github.com/aws/aws-sdk-go-v2/service/secretsmanager"
	vault "github.com/hashicorp/vault/api"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

// mockProvider implements Provider for testing
type mockProvider struct {
	secrets map[string]string
	err     error
	failFor map[string]bool // Keys that should fail when accessed
}

func newMockProvider() *mockProvider {
	return &mockProvider{
		secrets: make(map[string]string),
		failFor: make(map[string]bool),
	}
}

type awsHandlerFunc func(target string, body []byte) (status int, payload []byte)

func newAWSProviderWithHandler(t *testing.T, handler awsHandlerFunc) (*AWSSecretsProvider, func()) {
	t.Helper()

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		body, err := io.ReadAll(r.Body)
		require.NoError(t, err)

		status, payload := handler(r.Header.Get("X-Amz-Target"), body)
		if status == 0 {
			status = http.StatusOK
		}
		if payload == nil {
			payload = []byte(`{}`)
		}

		w.Header().Set("Content-Type", "application/x-amz-json-1.1")
		w.WriteHeader(status)
		_, _ = w.Write(payload)
	}))

	cfg := aws.Config{
		Region: "us-east-1",
		Credentials: aws.NewCredentialsCache(credentials.NewStaticCredentialsProvider(
			"access", "secret", "",
		)),
		HTTPClient: server.Client(),
		EndpointResolverWithOptions: aws.EndpointResolverWithOptionsFunc(func(service, region string, options ...interface{}) (aws.Endpoint, error) {
			return aws.Endpoint{
				URL:               server.URL,
				SigningRegion:     region,
				HostnameImmutable: true,
			}, nil
		}),
	}

	client := secretsmanager.NewFromConfig(cfg, func(o *secretsmanager.Options) {
		o.BaseEndpoint = aws.String(server.URL)
	})

	provider := &AWSSecretsProvider{
		client: client,
		region: "us-east-1",
	}

	return provider, server.Close
}

func newVaultProviderWithServer(t *testing.T, handler http.HandlerFunc) (*VaultProvider, func()) {
	t.Helper()

	server := httptest.NewServer(handler)
	cfg := &vault.Config{
		Address:    server.URL,
		HttpClient: server.Client(),
	}

	client, err := vault.NewClient(cfg)
	require.NoError(t, err)
	client.SetToken("test-token")

	return &VaultProvider{
		client: client,
		path:   "secret",
	}, server.Close
}

func (m *mockProvider) GetSecret(_ context.Context, key string) (string, error) {
	if m.err != nil {
		return "", m.err
	}
	if m.failFor[key] {
		return "", fmt.Errorf("mock provider configured to fail for key '%s'", key)
	}
	if val, ok := m.secrets[key]; ok {
		return val, nil
	}
	return "", fmt.Errorf("secret '%s' not found", key)
}

func (m *mockProvider) SetSecret(_ context.Context, key string, value string) error {
	if m.err != nil {
		return m.err
	}
	m.secrets[key] = value
	return nil
}

func (m *mockProvider) DeleteSecret(_ context.Context, key string) error {
	if m.err != nil {
		return m.err
	}
	delete(m.secrets, key)
	return nil
}

func (m *mockProvider) ListSecrets(_ context.Context) ([]string, error) {
	if m.err != nil {
		return nil, m.err
	}
	keys := make([]string, 0, len(m.secrets))
	for k := range m.secrets {
		keys = append(keys, k)
	}
	return keys, nil
}

func TestManager_GetSecret(t *testing.T) {
	ctx := context.Background()
	manager := New(Config{CacheTTL: time.Second})

	mock1 := newMockProvider()
	mock1.secrets["key1"] = "value1"
	manager.RegisterProvider("mock1", mock1)

	mock2 := newMockProvider()
	mock2.secrets["key2"] = "value2"
	manager.RegisterProvider("mock2", mock2)

	// Test successful retrieval from first provider
	val, err := manager.GetSecret(ctx, "key1")
	require.NoError(t, err)
	assert.Equal(t, "value1", val)

	// Test successful retrieval from second provider
	val, err = manager.GetSecret(ctx, "key2")
	require.NoError(t, err)
	assert.Equal(t, "value2", val)

	// Test cache hit
	val, err = manager.GetSecret(ctx, "key1")
	require.NoError(t, err)
	assert.Equal(t, "value1", val)

	// Test cache expiry
	time.Sleep(2 * time.Second)
	mock1.secrets["key1"] = "newvalue1"
	val, err = manager.GetSecret(ctx, "key1")
	require.NoError(t, err)
	assert.Equal(t, "newvalue1", val)

	// Test not found in any provider
	_, err = manager.GetSecret(ctx, "nonexistent")
	assert.Error(t, err)
}

func TestManager_SetSecret(t *testing.T) {
	ctx := context.Background()
	manager := New(Config{CacheTTL: time.Second})

	mock := newMockProvider()
	manager.RegisterProvider("mock", mock)

	// Test successful set
	err := manager.SetSecret(ctx, "key", "value")
	require.NoError(t, err)

	// Verify value was set
	val, err := manager.GetSecret(ctx, "key")
	require.NoError(t, err)
	assert.Equal(t, "value", val)

	// Test set with no providers
	manager = New(Config{})
	err = manager.SetSecret(ctx, "key", "value")
	assert.Error(t, err)
}

func TestAWSSecretsProvider_Integration(t *testing.T) {
	ctx := context.Background()

	// Skip if AWS credentials not available
	if os.Getenv("AWS_ACCESS_KEY_ID") == "" || os.Getenv("AWS_SECRET_ACCESS_KEY") == "" {
		t.Skip("Skipping AWS tests - credentials not available")
	}

	provider, err := NewAWSSecretsProvider(ctx, "us-east-1")
	require.NoError(t, err)

	// Create a test secret
	err = provider.SetSecret(ctx, "test-secret", "test-value")
	require.NoError(t, err)

	// Get the secret
	val, err := provider.GetSecret(ctx, "test-secret")
	require.NoError(t, err)
	assert.Equal(t, "test-value", val)

	// List secrets
	secrets, err := provider.ListSecrets(ctx)
	require.NoError(t, err)
	assert.Contains(t, secrets, "test-secret")

	// Delete the secret
	err = provider.DeleteSecret(ctx, "test-secret")
	require.NoError(t, err)

	// Verify deletion
	_, err = provider.GetSecret(ctx, "test-secret")
	assert.Error(t, err)
}

func TestVaultProvider_Integration(t *testing.T) {
	// Skip if Vault not configured
	if os.Getenv("VAULT_ADDR") == "" || os.Getenv("VAULT_TOKEN") == "" {
		t.Skip("Skipping Vault tests - not configured")
	}

	provider, err := NewVaultProvider(os.Getenv("VAULT_ADDR"), os.Getenv("VAULT_TOKEN"), "secret")
	require.NoError(t, err)

	ctx := context.Background()

	// Create a test secret
	err = provider.SetSecret(ctx, "test-secret", "test-value")
	require.NoError(t, err)

	// Get the secret
	val, err := provider.GetSecret(ctx, "test-secret")
	require.NoError(t, err)
	assert.Equal(t, "test-value", val)

	// List secrets
	secrets, err := provider.ListSecrets(ctx)
	require.NoError(t, err)
	assert.Contains(t, secrets, "test-secret")

	// Delete the secret
	err = provider.DeleteSecret(ctx, "test-secret")
	require.NoError(t, err)

	// Verify deletion
	_, err = provider.GetSecret(ctx, "test-secret")
	assert.Error(t, err)
}

func TestEnvironmentProvider(t *testing.T) {
	provider := NewEnvironmentProvider()
	ctx := context.Background()

	// Set environment variable
	os.Setenv("TEST_SECRET", "test-value")
	defer os.Unsetenv("TEST_SECRET")

	// Get the secret
	val, err := provider.GetSecret(ctx, "TEST_SECRET")
	require.NoError(t, err)
	assert.Equal(t, "test-value", val)

	// List secrets
	secrets, err := provider.ListSecrets(ctx)
	require.NoError(t, err)
	assert.Contains(t, secrets, "TEST_SECRET")

	// Delete the secret
	err = provider.DeleteSecret(ctx, "TEST_SECRET")
	require.NoError(t, err)

	// Verify deletion
	_, err = provider.GetSecret(ctx, "TEST_SECRET")
	assert.Error(t, err)
}

func TestStructuredSecret(t *testing.T) {
	manager := New(Config{CacheTTL: time.Second})
	mock := newMockProvider()
	manager.RegisterProvider("mock", mock)

	structured := NewStructuredSecret(manager)
	ctx := context.Background()

	// Test JSON secret
	type testSecret struct {
		Field1 string `json:"field1"`
		Field2 int    `json:"field2"`
	}

	// Set JSON secret
	secret := testSecret{
		Field1: "value1",
		Field2: 42,
	}
	err := structured.SetJSONSecret(ctx, "json-secret", secret)
	require.NoError(t, err)

	// Get JSON secret
	var retrieved testSecret
	err = structured.GetJSONSecret(ctx, "json-secret", &retrieved)
	require.NoError(t, err)
	assert.Equal(t, secret.Field1, retrieved.Field1)
	assert.Equal(t, secret.Field2, retrieved.Field2)
}

func TestSecretRotation(t *testing.T) {
	manager := New(Config{CacheTTL: time.Second})
	mock := newMockProvider()
	manager.RegisterProvider("mock", mock)

	ctx, cancel := context.WithTimeout(context.Background(), time.Second)
	defer cancel()

	require.NoError(t, manager.SetSecret(ctx, "key1", "value1"))

	// Populate cache so that rotation clearing can be observed.
	_, err := manager.GetSecret(ctx, "key1")
	require.NoError(t, err)
	manager.cacheMux.RLock()
	_, ok := manager.cache["key1"]
	manager.cacheMux.RUnlock()
	require.True(t, ok, "expected cache entry before rotation")

	var runs int32
	rotation := NewSecretRotation(manager, 50*time.Millisecond)
	require.NoError(t, rotation.Register("key1", 50*time.Millisecond, func(ctx context.Context, m *Manager) error {
		atomic.AddInt32(&runs, 1)
		return nil
	}))

	go rotation.Start(ctx)
	time.Sleep(200 * time.Millisecond)
	rotation.Stop()

	manager.cacheMux.RLock()
	_, ok = manager.cache["key1"]
	manager.cacheMux.RUnlock()
	assert.False(t, ok, "cache should be cleared by rotation")
	assert.GreaterOrEqual(t, atomic.LoadInt32(&runs), int32(1))
}

func TestHelper_GetConfigs(t *testing.T) {
	manager := New(Config{CacheTTL: time.Second})
	mock := newMockProvider()
	manager.RegisterProvider("mock", mock)

	ctx := context.Background()

	// Test WorkOS config
	mock.secrets[SecretWorkOSClientID] = "client-id"
	mock.secrets[SecretWorkOSClientSecret] = "client-secret"
	mock.secrets[SecretWorkOSAPIKey] = "api-key"

	clientID, clientSecret, apiKey, err := manager.GetWorkOSConfig(ctx)
	require.NoError(t, err)
	assert.Equal(t, "client-id", clientID)
	assert.Equal(t, "client-secret", clientSecret)
	assert.Equal(t, "api-key", apiKey)

	// Test AWS config
	mock.secrets[SecretAWSAccessKeyID] = "access-key"
	mock.secrets[SecretAWSSecretAccessKey] = "secret-key"
	mock.secrets[SecretAWSRegion] = "us-west-2"

	accessKey, secretKey, region, err := manager.GetAWSConfig(ctx)
	require.NoError(t, err)
	assert.Equal(t, "access-key", accessKey)
	assert.Equal(t, "secret-key", secretKey)
	assert.Equal(t, "us-west-2", region)

	// Test LLM config (vLLM/MLX)
	mock.secrets[SecretLLMBaseURL] = "http://localhost:8000"
	mock.secrets[SecretLLMModel] = "mistralai/Mistral-7B-v0.1"
	mock.secrets[SecretLLMAPIKey] = ""

	llmBaseURL, llmModel, llmAPIKey, err := manager.GetLLMConfig(ctx)
	require.NoError(t, err)
	assert.Equal(t, "http://localhost:8000", llmBaseURL)
	assert.Equal(t, "mistralai/Mistral-7B-v0.1", llmModel)
	assert.Empty(t, llmAPIKey)

	// Test Portfolio config
	mock.secrets[SecretPortfolioAPIKey] = "portfolio-key"
	mock.secrets[SecretPortfolioEndpoint] = "portfolio-endpoint"

	portfolioKey, portfolioEndpoint, err := manager.GetPortfolioConfig(ctx)
	require.NoError(t, err)
	assert.Equal(t, "portfolio-key", portfolioKey)
	assert.Equal(t, "portfolio-endpoint", portfolioEndpoint)
}

func TestHelper_GetConfigs_ErrorPaths(t *testing.T) {
	manager := New(Config{CacheTTL: time.Second})
	mock := newMockProvider()
	manager.RegisterProvider("mock", mock)

	ctx := context.Background()

	t.Run("WorkOS config missing client ID", func(t *testing.T) {
		mock.secrets = map[string]string{
			SecretWorkOSClientSecret: "secret",
			SecretWorkOSAPIKey:       "key",
		}
		_, _, _, err := manager.GetWorkOSConfig(ctx)
		assert.Error(t, err)
	})

	t.Run("AWS config missing access key", func(t *testing.T) {
		mock.secrets = map[string]string{
			SecretAWSSecretAccessKey: "secret",
		}
		_, _, _, err := manager.GetAWSConfig(ctx)
		assert.Error(t, err)
	})

	t.Run("Portfolio config missing endpoint", func(t *testing.T) {
		mock.secrets = map[string]string{
			SecretPortfolioAPIKey: "key",
		}
		_, _, err := manager.GetPortfolioConfig(ctx)
		assert.Error(t, err)
	})

	t.Run("Manager errors when all providers fail", func(t *testing.T) {
		// Create a new manager with only an error-prone provider
		errorManager := New(Config{CacheTTL: time.Second})
		errorMock := &mockProvider{
			secrets: make(map[string]string),
			err:     fmt.Errorf("provider error"),
		}
		errorManager.RegisterProvider("error", errorMock)

		_, _, _, err := errorManager.GetWorkOSConfig(ctx)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "not found in any provider")

		_, _, _, err = errorManager.GetAWSConfig(ctx)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "not found in any provider")

		// LLM config returns defaults when secrets are missing, so no error check here

		_, _, err = errorManager.GetPortfolioConfig(ctx)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "not found in any provider")
	})
}

func TestManager_InvalidateCache(t *testing.T) {
	manager := New(Config{CacheTTL: time.Second})
	mock := newMockProvider()
	mock.secrets["key1"] = "value1"
	manager.RegisterProvider("mock", mock)

	ctx := context.Background()

	// Get secret to populate cache
	val, err := manager.GetSecret(ctx, "key1")
	require.NoError(t, err)
	assert.Equal(t, "value1", val)

	// Verify it's cached
	_, exists := manager.cache["key1"]
	assert.True(t, exists)

	// Invalidate cache
	manager.InvalidateCache("key1")

	// Verify it's no longer cached
	_, exists = manager.cache["key1"]
	assert.False(t, exists)
}

func TestEnvironmentProvider_SetSecret(t *testing.T) {
	provider := NewEnvironmentProvider()
	ctx := context.Background()

	// Test setting a secret
	err := provider.SetSecret(ctx, "TEST_SET_SECRET", "test-value")
	require.NoError(t, err)

	// Verify it was set
	val, err := provider.GetSecret(ctx, "TEST_SET_SECRET")
	require.NoError(t, err)
	assert.Equal(t, "test-value", val)

	// Cleanup
	os.Unsetenv("TEST_SET_SECRET")
}

func TestJSONSecret_ErrorPaths(t *testing.T) {
	manager := New(Config{CacheTTL: time.Second})
	mock := newMockProvider()
	manager.RegisterProvider("mock", mock)

	structured := NewStructuredSecret(manager)
	ctx := context.Background()

	t.Run("GetJSONSecret with invalid JSON", func(t *testing.T) {
		mock.secrets["invalid-json"] = "not valid json"

		var result map[string]interface{}
		err := structured.GetJSONSecret(ctx, "invalid-json", &result)
		assert.Error(t, err)
	})

	t.Run("GetJSONSecret with missing secret", func(t *testing.T) {
		var result map[string]interface{}
		err := structured.GetJSONSecret(ctx, "nonexistent", &result)
		assert.Error(t, err)
	})

	t.Run("SetJSONSecret with invalid value", func(t *testing.T) {
		// Create a value that can't be marshaled to JSON
		invalidValue := make(chan int)

		err := structured.SetJSONSecret(ctx, "invalid-value", invalidValue)
		assert.Error(t, err)
	})
}

func TestAWSSecretsProvider_Unit(t *testing.T) {
	ctx := context.Background()

	t.Run("NewAWSSecretsProvider with invalid region", func(t *testing.T) {
		// Skip if running in environment where AWS SDK might interfere
		if os.Getenv("AWS_PROFILE") != "" || os.Getenv("AWS_ACCESS_KEY_ID") != "" {
			t.Skip("Skipping AWS provider test - AWS credentials present")
		}

		// Test with an empty context that should fail config loading
		provider, err := NewAWSSecretsProvider(ctx, "invalid-region")
		// The provider creation might succeed but operations will fail
		if err != nil {
			assert.Error(t, err)
			assert.Contains(t, err.Error(), "failed to load AWS config")
		} else {
			// If provider creation succeeds, operations should fail without credentials
			assert.NotNil(t, provider)

			// Test operations that should fail without proper credentials
			_, err = provider.GetSecret(ctx, "test-secret")
			assert.Error(t, err)

			err = provider.SetSecret(ctx, "test-secret", "test-value")
			assert.Error(t, err)

			err = provider.DeleteSecret(ctx, "test-secret")
			assert.Error(t, err)

			_, err = provider.ListSecrets(ctx)
			assert.Error(t, err)
		}
	})
}

func TestVaultProvider_Unit(t *testing.T) {
	ctx := context.Background()

	t.Run("NewVaultProvider with invalid address", func(t *testing.T) {
		// Test with invalid Vault address - Vault client creation might succeed
		// but operations will fail
		provider, err := NewVaultProvider("invalid-address", "test-token", "secret")
		if err != nil {
			// If creation fails, that's acceptable
			assert.Error(t, err)
			assert.Nil(t, provider)
		} else {
			// If creation succeeds, operations should fail
			assert.NotNil(t, provider)

			// Test operations that should fail with invalid address
			_, err = provider.GetSecret(ctx, "test-secret")
			assert.Error(t, err)
		}
	})

	t.Run("NewVaultProvider with valid address but operations fail", func(t *testing.T) {
		// Test with a valid-looking but non-existent Vault address
		provider, err := NewVaultProvider("http://localhost:18200", "test-token", "secret")
		if err != nil {
			// If creation fails due to unreachable address, that's expected
			assert.Error(t, err)
			return
		}

		assert.NotNil(t, provider)

		// Test operations that should fail with unreachable Vault
		_, err = provider.GetSecret(ctx, "test-secret")
		assert.Error(t, err)

		err = provider.SetSecret(ctx, "test-secret", "test-value")
		assert.Error(t, err)

		err = provider.DeleteSecret(ctx, "test-secret")
		assert.Error(t, err)

		_, err = provider.ListSecrets(ctx)
		assert.Error(t, err)
	})
}

func TestSecretRotation_EdgeCases(t *testing.T) {
	t.Run("Start with cancelled context", func(t *testing.T) {
		manager := New(Config{CacheTTL: time.Second})
		rotation := NewSecretRotation(manager, 50*time.Millisecond)

		ctx, cancel := context.WithCancel(context.Background())
		cancel() // Cancel immediately

		// Start should return immediately due to cancelled context
		done := make(chan struct{})
		go func() {
			rotation.Start(ctx)
			close(done)
		}()

		// Should complete quickly
		select {
		case <-done:
			// Expected behavior
		case <-time.After(100 * time.Millisecond):
			t.Fatal("Start should have returned immediately with cancelled context")
		}
	})

	t.Run("Stop before start", func(t *testing.T) {
		manager := New(Config{CacheTTL: time.Second})
		rotation := NewSecretRotation(manager, 50*time.Millisecond)
		// Should not panic when stopping before starting
		rotation.Stop()
	})
}

func TestSecretRotation_RegisterAndErrorHandling(t *testing.T) {
	manager := New(Config{CacheTTL: time.Second})
	mock := newMockProvider()
	manager.RegisterProvider("mock", mock)

	var (
		errCount int32
		runCount int32
	)

	rotation := NewSecretRotation(manager, 10*time.Millisecond)
	rotation.SetErrorHandler(func(key string, err error) {
		atomic.AddInt32(&errCount, 1)
	})

	require.NoError(t, rotation.Register("rotate-ok", 10*time.Millisecond, func(ctx context.Context, m *Manager) error {
		atomic.AddInt32(&runCount, 1)
		return nil
	}))

	require.NoError(t, rotation.Register("rotate-fail", 10*time.Millisecond, func(ctx context.Context, m *Manager) error {
		return fmt.Errorf("expected failure")
	}))

	ctx, cancel := context.WithTimeout(context.Background(), 100*time.Millisecond)
	defer cancel()

	go rotation.Start(ctx)
	time.Sleep(60 * time.Millisecond)
	rotation.Stop()

	assert.GreaterOrEqual(t, atomic.LoadInt32(&runCount), int32(1))
	assert.GreaterOrEqual(t, atomic.LoadInt32(&errCount), int32(1))
}

func TestSecretRotation_RegisterValidation(t *testing.T) {
	manager := New(Config{})
	rotation := NewSecretRotation(manager, 0) // verify defaulting behaviour

	assert.Equal(t, 5*time.Minute, rotation.interval)

	err := rotation.Register("", time.Second, func(context.Context, *Manager) error { return nil })
	assert.Error(t, err)

	err = rotation.Register("valid", time.Second, nil)
	assert.Error(t, err)

	err = rotation.Register("valid", 0, func(context.Context, *Manager) error { return nil })
	assert.NoError(t, err)
	rotation.mu.RLock()
	task, ok := rotation.tasks["valid"]
	rotation.mu.RUnlock()
	require.True(t, ok)
	assert.Equal(t, rotation.interval, task.interval)
}

func TestSecretRotation_RunOnceAndUnregister(t *testing.T) {
	ctx := context.Background()
	manager := New(Config{CacheTTL: time.Minute})
	mock := newMockProvider()
	manager.RegisterProvider("mock", mock)
	require.NoError(t, manager.SetSecret(ctx, "cached-secret", "value"))

	// prime cache so we can verify it gets purged
	_, err := manager.GetSecret(ctx, "cached-secret")
	require.NoError(t, err)

	var runs int32
	rotation := NewSecretRotation(manager, time.Hour)
	require.NoError(t, rotation.Register("cached-secret", 10*time.Millisecond, func(context.Context, *Manager) error {
		atomic.AddInt32(&runs, 1)
		return nil
	}))

	rotation.RunOnce(ctx)
	assert.Equal(t, int32(1), atomic.LoadInt32(&runs))

	rotation.Unregister("cached-secret")
	rotation.mu.RLock()
	_, exists := rotation.tasks["cached-secret"]
	rotation.mu.RUnlock()
	assert.False(t, exists)

	manager.cacheMux.RLock()
	_, cached := manager.cache["cached-secret"]
	manager.cacheMux.RUnlock()
	assert.False(t, cached, "RunOnce should clear cached values before rotating")
}

func TestAWSProvider_ComprehensiveErrorPaths(t *testing.T) {
	ctx := context.Background()

	// Skip if running with actual AWS credentials to avoid interference
	if os.Getenv("AWS_PROFILE") != "" || os.Getenv("AWS_ACCESS_KEY_ID") != "" {
		t.Skip("Skipping AWS provider error tests - real credentials present")
	}

	// Test provider creation with different regions
	provider, err := NewAWSSecretsProvider(ctx, "invalid-region-name")
	if err != nil {
		// Provider creation might fail with invalid region
		assert.Contains(t, err.Error(), "failed to load AWS config")
	} else {
		// If provider created, operations should fail
		assert.NotNil(t, provider)

		// Test GetSecret with non-existent secret
		_, err = provider.GetSecret(ctx, "non-existent-secret")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "failed to get secret from AWS")

		// Test SetSecret without proper credentials
		err = provider.SetSecret(ctx, "test-secret", "test-value")
		assert.Error(t, err)

		// Test DeleteSecret without proper credentials
		err = provider.DeleteSecret(ctx, "test-secret")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "failed to delete secret from AWS")

		// Test ListSecrets without proper credentials
		_, err = provider.ListSecrets(ctx)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "failed to list secrets from AWS")
	}
}

func TestVaultProvider_ComprehensiveErrorPaths(t *testing.T) {
	ctx := context.Background()

	// Test with unreachable Vault address
	provider, err := NewVaultProvider("http://localhost:18200", "test-token", "secret")
	if err != nil {
		// Provider creation failed - that's expected
		assert.Contains(t, err.Error(), "failed to create Vault client")
	} else {
		// If provider created, operations should fail with unreachable Vault
		assert.NotNil(t, provider)

		// Test GetSecret with unreachable Vault
		_, err = provider.GetSecret(ctx, "test-secret")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "failed to get secret from Vault")

		// Test SetSecret with unreachable Vault
		err = provider.SetSecret(ctx, "test-secret", "test-value")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "failed to set secret in Vault")

		// Test DeleteSecret with unreachable Vault
		err = provider.DeleteSecret(ctx, "test-secret")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "failed to delete secret from Vault")

		// Test ListSecrets with unreachable Vault
		_, err = provider.ListSecrets(ctx)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "failed to list secrets from Vault")
	}
}

func TestProvider_EdgeCaseSecretValues(t *testing.T) {
	ctx := context.Background()

	// Test with environment provider for predictable behavior
	provider := NewEnvironmentProvider()

	// Test empty secret value
	os.Setenv("EMPTY_SECRET", "")
	defer os.Unsetenv("EMPTY_SECRET")

	// Environment provider treats empty strings as "not found"
	_, err := provider.GetSecret(ctx, "EMPTY_SECRET")
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "not found")

	// Test secret with special characters
	specialValue := "secret!@#$%^&*(){}[]|\\:;\"'<>?,./_+-="
	os.Setenv("SPECIAL_SECRET", specialValue)
	defer os.Unsetenv("SPECIAL_SECRET")

	val, err := provider.GetSecret(ctx, "SPECIAL_SECRET")
	require.NoError(t, err)
	assert.Equal(t, specialValue, val)

	// Test very long secret value
	longValue := strings.Repeat("a", 10000)
	os.Setenv("LONG_SECRET", longValue)
	defer os.Unsetenv("LONG_SECRET")

	val, err = provider.GetSecret(ctx, "LONG_SECRET")
	require.NoError(t, err)
	assert.Equal(t, longValue, val)
}

func TestSecretManager_ProviderFallbackBehavior(t *testing.T) {
	ctx := context.Background()
	manager := New(Config{CacheTTL: time.Second})

	// Register multiple providers
	mock1 := newMockProvider()
	mock2 := newMockProvider()

	// mock1 fails for certain keys
	mock1.failFor = map[string]bool{
		"failing-key": true,
	}
	mock1.secrets["working-key"] = "value-from-mock1"

	// mock2 has the failing key
	mock2.secrets["failing-key"] = "value-from-mock2"
	mock2.secrets["working-key"] = "value-from-mock2"

	manager.RegisterProvider("mock1", mock1)
	manager.RegisterProvider("mock2", mock2)

	// Should get from mock1 for working-key (first provider)
	val, err := manager.GetSecret(ctx, "working-key")
	require.NoError(t, err)
	assert.Equal(t, "value-from-mock1", val)

	// Should fallback to mock2 for failing-key
	val, err = manager.GetSecret(ctx, "failing-key")
	require.NoError(t, err)
	assert.Equal(t, "value-from-mock2", val)

	// Should fail if no provider has the key
	_, err = manager.GetSecret(ctx, "non-existent-key")
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "not found in any provider")
}

func TestGetConfigs_RemainingErrorPaths(t *testing.T) {
	ctx := context.Background()

	t.Run("GetWorkOSConfig missing client secret", func(t *testing.T) {
		manager := New(Config{CacheTTL: time.Second})
		mock := newMockProvider()
		mock.secrets = map[string]string{
			SecretWorkOSClientID: "client-id",
			// Missing client secret
			SecretWorkOSAPIKey: "api-key",
		}
		manager.RegisterProvider("mock", mock)

		_, _, _, err := manager.GetWorkOSConfig(ctx)
		assert.Error(t, err)
	})

	t.Run("GetWorkOSConfig missing API key", func(t *testing.T) {
		manager := New(Config{CacheTTL: time.Second})
		mock := newMockProvider()
		mock.secrets = map[string]string{
			SecretWorkOSClientID:     "client-id",
			SecretWorkOSClientSecret: "client-secret",
			// Missing API key
		}
		manager.RegisterProvider("mock", mock)

		_, _, _, err := manager.GetWorkOSConfig(ctx)
		assert.Error(t, err)
	})

	t.Run("GetAWSConfig missing secret key", func(t *testing.T) {
		manager := New(Config{CacheTTL: time.Second})
		mock := newMockProvider()
		mock.secrets = map[string]string{
			SecretAWSAccessKeyID: "access-key",
			// Missing secret access key
		}
		manager.RegisterProvider("mock", mock)

		_, _, _, err := manager.GetAWSConfig(ctx)
		assert.Error(t, err)
	})

	t.Run("GetAWSConfig with default region", func(t *testing.T) {
		manager := New(Config{CacheTTL: time.Second})
		mock := newMockProvider()
		mock.secrets = map[string]string{
			SecretAWSAccessKeyID:     "access-key",
			SecretAWSSecretAccessKey: "secret-key",
			// No region specified - should default to us-east-1
		}
		manager.RegisterProvider("mock", mock)

		accessKey, secretKey, region, err := manager.GetAWSConfig(ctx)
		require.NoError(t, err)
		assert.Equal(t, "access-key", accessKey)
		assert.Equal(t, "secret-key", secretKey)
		assert.Equal(t, "us-east-1", region) // Default region
	})
}

func TestNewAWSSecretsProvider_ErrorPath(t *testing.T) {
	t.Setenv("AWS_SDK_LOAD_CONFIG", "1")
	t.Setenv("AWS_PROFILE", "nonexistent-profile")

	_, err := NewAWSSecretsProvider(context.Background(), "us-east-1")
	assert.Error(t, err)
}

func TestAWSSecretsProvider_GetSecretCases(t *testing.T) {
	ctx := context.Background()

	t.Run("success", func(t *testing.T) {
		provider, cleanup := newAWSProviderWithHandler(t, func(target string, body []byte) (int, []byte) {
			require.Equal(t, "secretsmanager.GetSecretValue", target)
			return http.StatusOK, []byte(`{"SecretString":"value"}`)
		})
		defer cleanup()

		value, err := provider.GetSecret(ctx, "test")
		require.NoError(t, err)
		assert.Equal(t, "value", value)
	})

	t.Run("missing secret string", func(t *testing.T) {
		provider, cleanup := newAWSProviderWithHandler(t, func(target string, body []byte) (int, []byte) {
			return http.StatusOK, []byte(`{"SecretString":null}`)
		})
		defer cleanup()

		val, err := provider.GetSecret(ctx, "test")
		assert.Error(t, err)
		assert.Empty(t, val)
	})

	t.Run("service error", func(t *testing.T) {
		provider, cleanup := newAWSProviderWithHandler(t, func(target string, body []byte) (int, []byte) {
			return http.StatusBadGateway, []byte(`{"message":"boom"}`)
		})
		defer cleanup()

		_, err := provider.GetSecret(ctx, "test")
		assert.Error(t, err)
	})
}

func TestAWSSecretsProvider_SetSecretCases(t *testing.T) {
	ctx := context.Background()

	t.Run("update succeeds", func(t *testing.T) {
		provider, cleanup := newAWSProviderWithHandler(t, func(target string, body []byte) (int, []byte) {
			require.Equal(t, "secretsmanager.UpdateSecret", target)
			return http.StatusOK, []byte(`{}`)
		})
		defer cleanup()

		err := provider.SetSecret(ctx, "key", "value")
		assert.NoError(t, err)
	})

	t.Run("update fallback to create", func(t *testing.T) {
		var updateCalls int
		provider, cleanup := newAWSProviderWithHandler(t, func(target string, body []byte) (int, []byte) {
			switch target {
			case "secretsmanager.UpdateSecret":
				updateCalls++
				return http.StatusBadRequest, []byte(`{"message":"not found"}`)
			case "secretsmanager.CreateSecret":
				return http.StatusOK, []byte(`{}`)
			default:
				return http.StatusOK, []byte(`{}`)
			}
		})
		defer cleanup()

		err := provider.SetSecret(ctx, "key", "value")
		assert.NoError(t, err)
		assert.Equal(t, 1, updateCalls)
	})

	t.Run("both update and create fail", func(t *testing.T) {
		provider, cleanup := newAWSProviderWithHandler(t, func(target string, body []byte) (int, []byte) {
			return http.StatusInternalServerError, []byte(`{"message":"boom"}`)
		})
		defer cleanup()

		err := provider.SetSecret(ctx, "key", "value")
		assert.Error(t, err)
	})
}

func TestAWSSecretsProvider_DeleteSecretCases(t *testing.T) {
	ctx := context.Background()

	t.Run("delete succeeds", func(t *testing.T) {
		provider, cleanup := newAWSProviderWithHandler(t, func(target string, body []byte) (int, []byte) {
			require.Equal(t, "secretsmanager.DeleteSecret", target)
			return http.StatusOK, []byte(`{}`)
		})
		defer cleanup()

		err := provider.DeleteSecret(ctx, "key")
		assert.NoError(t, err)
	})

	t.Run("delete fails", func(t *testing.T) {
		provider, cleanup := newAWSProviderWithHandler(t, func(target string, body []byte) (int, []byte) {
			return http.StatusBadGateway, []byte(`{"message":"boom"}`)
		})
		defer cleanup()

		err := provider.DeleteSecret(ctx, "key")
		assert.Error(t, err)
	})
}

func TestAWSSecretsProvider_ListSecretsCases(t *testing.T) {
	ctx := context.Background()

	t.Run("lists secrets across pages", func(t *testing.T) {
		var calls int
		provider, cleanup := newAWSProviderWithHandler(t, func(target string, body []byte) (int, []byte) {
			require.Equal(t, "secretsmanager.ListSecrets", target)
			calls++
			if calls == 1 {
				return http.StatusOK, []byte(`{"SecretList":[{"Name":"first"}],"NextToken":"token"}`)
			}
			return http.StatusOK, []byte(`{"SecretList":[{"Name":"second"}]}`)
		})
		defer cleanup()

		secrets, err := provider.ListSecrets(ctx)
		require.NoError(t, err)
		assert.ElementsMatch(t, []string{"first", "second"}, secrets)
	})

	t.Run("list failure surfaces error", func(t *testing.T) {
		provider, cleanup := newAWSProviderWithHandler(t, func(target string, body []byte) (int, []byte) {
			return http.StatusInternalServerError, []byte(`{"message":"boom"}`)
		})
		defer cleanup()

		_, err := provider.ListSecrets(ctx)
		assert.Error(t, err)
	})
}

func TestNewVaultProvider_InvalidAddress(t *testing.T) {
	_, err := NewVaultProvider("://bad", "token", "secret")
	assert.Error(t, err)
}

func TestVaultProvider_SuccessOperations(t *testing.T) {
	secrets := map[string]string{}
	var mu sync.Mutex

	handler := func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.Method == http.MethodGet && strings.HasPrefix(r.URL.Path, "/v1/secret/data/"):
			key := strings.TrimPrefix(r.URL.Path, "/v1/secret/data/")
			mu.Lock()
			value, ok := secrets[key]
			mu.Unlock()
			if key == "bad" {
				resp := map[string]any{
					"data": map[string]any{
						"data": map[string]any{"value": 123},
					},
				}
				w.WriteHeader(http.StatusOK)
				require.NoError(t, json.NewEncoder(w).Encode(resp))
				return
			}
			if !ok {
				w.WriteHeader(http.StatusNotFound)
				fmt.Fprint(w, `{"errors":["not found"]}`)
				return
			}
			resp := map[string]any{
				"data": map[string]any{
					"data": map[string]any{"value": value},
				},
			}
			w.WriteHeader(http.StatusOK)
			require.NoError(t, json.NewEncoder(w).Encode(resp))
		case (r.Method == http.MethodPost || r.Method == http.MethodPut) && strings.HasPrefix(r.URL.Path, "/v1/secret/data/"):
			key := strings.TrimPrefix(r.URL.Path, "/v1/secret/data/")
			var payload struct {
				Data map[string]string `json:"data"`
			}
			require.NoError(t, json.NewDecoder(r.Body).Decode(&payload))
			mu.Lock()
			secrets[key] = payload.Data["value"]
			mu.Unlock()
			w.WriteHeader(http.StatusOK)
			fmt.Fprint(w, `{}`)
		case r.Method == http.MethodDelete && strings.HasPrefix(r.URL.Path, "/v1/secret/data/"):
			key := strings.TrimPrefix(r.URL.Path, "/v1/secret/data/")
			mu.Lock()
			delete(secrets, key)
			mu.Unlock()
			w.WriteHeader(http.StatusOK)
			fmt.Fprint(w, `{}`)
		case r.Method == "LIST" && strings.HasPrefix(r.URL.Path, "/v1/secret/metadata"),
			(r.Method == http.MethodGet && strings.HasPrefix(r.URL.Path, "/v1/secret") && r.URL.Query().Get("list") == "true"):
			mu.Lock()
			keys := make([]string, 0, len(secrets))
			for key := range secrets {
				keys = append(keys, key)
			}
			mu.Unlock()
			resp := map[string]any{
				"data": map[string]any{
					"keys": keys,
				},
			}
			w.WriteHeader(http.StatusOK)
			require.NoError(t, json.NewEncoder(w).Encode(resp))
		default:
			w.WriteHeader(http.StatusBadRequest)
			fmt.Fprint(w, `{"errors":["unexpected request"]}`)
		}
	}

	provider, cleanup := newVaultProviderWithServer(t, handler)
	defer cleanup()

	ctx := context.Background()
	require.NoError(t, provider.SetSecret(ctx, "demo", "value"))

	value, err := provider.GetSecret(ctx, "demo")
	require.NoError(t, err)
	assert.Equal(t, "value", value)

	list, err := provider.ListSecrets(ctx)
	require.NoError(t, err)
	assert.Contains(t, list, "demo")

	require.NoError(t, provider.DeleteSecret(ctx, "demo"))

	_, err = provider.GetSecret(ctx, "bad")
	assert.Error(t, err)
}

func TestVaultProvider_ErrorResponses(t *testing.T) {
	handler := func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusInternalServerError)
		fmt.Fprint(w, `{"errors":["boom"]}`)
	}
	provider, cleanup := newVaultProviderWithServer(t, handler)
	defer cleanup()

	ctx := context.Background()

	_, err := provider.GetSecret(ctx, "key")
	assert.Error(t, err)

	err = provider.SetSecret(ctx, "key", "value")
	assert.Error(t, err)

	err = provider.DeleteSecret(ctx, "key")
	assert.Error(t, err)

	_, err = provider.ListSecrets(ctx)
	assert.Error(t, err)
}
