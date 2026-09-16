package secrets

import (
	"context"
	"testing"

	"github.com/stretchr/testify/assert"
)

// TestVaultProviderFunctionSignatures tests that Vault provider functions exist and have correct signatures
func TestVaultProviderFunctionSignatures(t *testing.T) {
	t.Run("VaultProvider function signatures", func(t *testing.T) {
		provider := &VaultProvider{
			path: "secret/test",
		}

		// Test that all functions exist and have correct signatures
		assert.NotNil(t, provider.GetSecret)
		assert.NotNil(t, provider.SetSecret)
		assert.NotNil(t, provider.DeleteSecret)
		assert.NotNil(t, provider.ListSecrets)

		// Test function types
		var getSecretFunc func(context.Context, string) (string, error) = provider.GetSecret
		var setSecretFunc func(context.Context, string, string) error = provider.SetSecret
		var deleteSecretFunc func(context.Context, string) error = provider.DeleteSecret
		var listSecretsFunc func(context.Context) ([]string, error) = provider.ListSecrets

		assert.NotNil(t, getSecretFunc)
		assert.NotNil(t, setSecretFunc)
		assert.NotNil(t, deleteSecretFunc)
		assert.NotNil(t, listSecretsFunc)
	})
}

// TestAWSSecretsProviderFunctionSignatures tests that AWS provider functions exist and have correct signatures
func TestAWSSecretsProviderFunctionSignatures(t *testing.T) {
	t.Run("AWSSecretsProvider function signatures", func(t *testing.T) {
		provider := &AWSSecretsProvider{
			region: "us-east-1",
		}

		// Test that all functions exist and have correct signatures
		assert.NotNil(t, provider.GetSecret)
		assert.NotNil(t, provider.SetSecret)
		assert.NotNil(t, provider.DeleteSecret)
		assert.NotNil(t, provider.ListSecrets)

		// Test function types
		var getSecretFunc func(context.Context, string) (string, error) = provider.GetSecret
		var setSecretFunc func(context.Context, string, string) error = provider.SetSecret
		var deleteSecretFunc func(context.Context, string) error = provider.DeleteSecret
		var listSecretsFunc func(context.Context) ([]string, error) = provider.ListSecrets

		assert.NotNil(t, getSecretFunc)
		assert.NotNil(t, setSecretFunc)
		assert.NotNil(t, deleteSecretFunc)
		assert.NotNil(t, listSecretsFunc)
	})
}

// TestEnvironmentProviderFunctionSignatures tests that Environment provider functions exist and have correct signatures
func TestEnvironmentProviderFunctionSignatures(t *testing.T) {
	t.Run("EnvironmentProvider function signatures", func(t *testing.T) {
		provider := &EnvironmentProvider{}

		// Test that all functions exist and have correct signatures
		assert.NotNil(t, provider.GetSecret)
		assert.NotNil(t, provider.SetSecret)
		assert.NotNil(t, provider.DeleteSecret)
		assert.NotNil(t, provider.ListSecrets)

		// Test function types
		var getSecretFunc func(context.Context, string) (string, error) = provider.GetSecret
		var setSecretFunc func(context.Context, string, string) error = provider.SetSecret
		var deleteSecretFunc func(context.Context, string) error = provider.DeleteSecret
		var listSecretsFunc func(context.Context) ([]string, error) = provider.ListSecrets

		assert.NotNil(t, getSecretFunc)
		assert.NotNil(t, setSecretFunc)
		assert.NotNil(t, deleteSecretFunc)
		assert.NotNil(t, listSecretsFunc)
	})
}

// TestManagerFunctionSignatures tests that Manager functions exist and have correct signatures
func TestManagerFunctionSignatures(t *testing.T) {
	t.Run("Manager function signatures", func(t *testing.T) {
		manager := &Manager{}

		// Test that all functions exist and have correct signatures
		assert.NotNil(t, manager.GetSecret)
		assert.NotNil(t, manager.SetSecret)
		assert.NotNil(t, manager.InvalidateCache)
		assert.NotNil(t, manager.ClearCache)
		assert.NotNil(t, manager.RegisterProvider)

		// Test function types
		var getSecretFunc func(context.Context, string) (string, error) = manager.GetSecret
		var setSecretFunc func(context.Context, string, string) error = manager.SetSecret
		var invalidateCacheFunc func(string) = manager.InvalidateCache
		var clearCacheFunc func() = manager.ClearCache
		var registerProviderFunc func(string, Provider) = manager.RegisterProvider

		assert.NotNil(t, getSecretFunc)
		assert.NotNil(t, setSecretFunc)
		assert.NotNil(t, invalidateCacheFunc)
		assert.NotNil(t, clearCacheFunc)
		assert.NotNil(t, registerProviderFunc)
	})
}

// TestProviderInterfaceCompliance tests that all providers implement the Provider interface
func TestProviderInterfaceCompliance(t *testing.T) {
	t.Run("VaultProvider implements Provider interface", func(t *testing.T) {
		var provider Provider = &VaultProvider{}
		assert.NotNil(t, provider)
	})

	t.Run("AWSSecretsProvider implements Provider interface", func(t *testing.T) {
		var provider Provider = &AWSSecretsProvider{}
		assert.NotNil(t, provider)
	})

	t.Run("EnvironmentProvider implements Provider interface", func(t *testing.T) {
		var provider Provider = &EnvironmentProvider{}
		assert.NotNil(t, provider)
	})
}

// TestNewFunctions tests that all New functions exist and return correct types
func TestNewFunctions(t *testing.T) {
	t.Run("New function exists and returns correct type", func(t *testing.T) {
		config := Config{}
		manager := New(config)
		assert.NotNil(t, manager)
		assert.IsType(t, &Manager{}, manager)
	})

	t.Run("NewAWSSecretsProvider function exists", func(t *testing.T) {
		// Test that the function exists and can be called
		// We can't actually call it without AWS credentials
		assert.NotNil(t, NewAWSSecretsProvider)
		
		// Test that it's a function type
		funcType := func(context.Context, string) (*AWSSecretsProvider, error) { return nil, nil }
		assert.IsType(t, funcType, NewAWSSecretsProvider)
	})

	t.Run("NewVaultProvider function exists", func(t *testing.T) {
		// Test that the function exists and can be called
		// We can't actually call it without Vault server
		assert.NotNil(t, NewVaultProvider)
		
		// Test that it's a function type
		funcType := func(string, string, string) (*VaultProvider, error) { return nil, nil }
		assert.IsType(t, funcType, NewVaultProvider)
	})

	t.Run("NewEnvironmentProvider function exists", func(t *testing.T) {
		// Test that the function exists and can be called
		provider := NewEnvironmentProvider()
		assert.NotNil(t, provider)
		assert.IsType(t, &EnvironmentProvider{}, provider)
	})
}

// TestEdgeCases tests various edge cases and error conditions
func TestEdgeCases(t *testing.T) {
	t.Run("Manager with nil provider", func(t *testing.T) {
		manager := &Manager{
			providers: make(map[string]Provider),
		}

		// Test GetSecret with non-existent provider
		_, err := manager.GetSecret(context.Background(), "nonexistent:key")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "not found in any provider")

		// Test SetSecret with non-existent provider
		err = manager.SetSecret(context.Background(), "nonexistent:key", "value")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "failed to store secret")
	})

	t.Run("Manager with empty key", func(t *testing.T) {
		manager := &Manager{
			providers: make(map[string]Provider),
		}

		// Test GetSecret with empty key
		_, err := manager.GetSecret(context.Background(), "")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "not found in any provider")

		// Test SetSecret with empty key
		err = manager.SetSecret(context.Background(), "", "value")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "failed to store secret")
	})

	t.Run("Manager with invalid key format", func(t *testing.T) {
		manager := &Manager{
			providers: make(map[string]Provider),
		}

		// Test GetSecret with invalid key format (no colon)
		_, err := manager.GetSecret(context.Background(), "invalid-key")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "not found in any provider")

		// Test SetSecret with invalid key format
		err = manager.SetSecret(context.Background(), "invalid-key", "value")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "failed to store secret")
	})

	t.Run("Manager cache operations", func(t *testing.T) {
		manager := &Manager{
			providers: make(map[string]Provider),
			cache:     make(map[string]*cachedSecret),
		}

		// Test InvalidateCache with empty key
		assert.NotPanics(t, func() {
			manager.InvalidateCache("")
		})

		// Test InvalidateCache with non-existent key
		assert.NotPanics(t, func() {
			manager.InvalidateCache("nonexistent:key")
		})

		// Test ClearCache
		assert.NotPanics(t, func() {
			manager.ClearCache()
		})
	})

	t.Run("Manager RegisterProvider", func(t *testing.T) {
		manager := &Manager{
			providers: make(map[string]Provider),
		}

		// Test RegisterProvider with nil provider
		assert.NotPanics(t, func() {
			manager.RegisterProvider("test", nil)
		})

		// Test RegisterProvider with valid provider
		envProvider := &EnvironmentProvider{}
		assert.NotPanics(t, func() {
			manager.RegisterProvider("env", envProvider)
		})

		// Verify provider was registered
		assert.NotNil(t, manager.providers["env"])
	})
}

// TestContextHandling tests context handling in various scenarios
func TestContextHandling(t *testing.T) {
	t.Run("Context cancellation", func(t *testing.T) {
		manager := &Manager{
			providers: make(map[string]Provider),
		}

		// Test with cancelled context
		ctx, cancel := context.WithCancel(context.Background())
		cancel()

		_, err := manager.GetSecret(ctx, "test:key")
		assert.Error(t, err)

		err = manager.SetSecret(ctx, "test:key", "value")
		assert.Error(t, err)
	})

	t.Run("Context timeout", func(t *testing.T) {
		manager := &Manager{
			providers: make(map[string]Provider),
		}

		// Test with timeout context
		ctx, cancel := context.WithTimeout(context.Background(), 0)
		defer cancel()

		_, err := manager.GetSecret(ctx, "test:key")
		assert.Error(t, err)

		err = manager.SetSecret(ctx, "test:key", "value")
		assert.Error(t, err)
	})
}