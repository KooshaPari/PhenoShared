package middleware

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"testing"
	"time"

	"github.com/byteport/api/internal/infrastructure/auth"
	"github.com/byteport/api/internal/infrastructure/secrets"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func TestAuthMiddleware(t *testing.T) {
	gin.SetMode(gin.TestMode)

	t.Run("creates middleware using WorkOS auth service", func(t *testing.T) {
		// Create a mock auth service
		manager := setupMockSecretsManager()
		authService := auth.NewWorkOSAuthService(manager)
		ctx := context.Background()
		require.NoError(t, authService.Initialize(ctx))

		// Create middleware
		middleware := AuthMiddleware(authService)

		// Test that it's a valid middleware function
		assert.NotNil(t, middleware)

		// Test the middleware with a valid test token
		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "Bearer test-user123-test_at_example.com")
		c.Request = req

		middleware(c)

		// Should succeed with test token
		assert.Equal(t, http.StatusOK, w.Code)
		assert.False(t, c.IsAborted())
	})

	t.Run("handles invalid token", func(t *testing.T) {
		manager := setupMockSecretsManager()
		authService := auth.NewWorkOSAuthService(manager)
		ctx := context.Background()
		require.NoError(t, authService.Initialize(ctx))

		middleware := AuthMiddleware(authService)

		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "Bearer invalid-token")
		c.Request = req

		middleware(c)

		// Should fail with invalid token
		assert.Equal(t, http.StatusUnauthorized, w.Code)
		assert.True(t, c.IsAborted())
	})

	t.Run("handles missing authorization header", func(t *testing.T) {
		manager := setupMockSecretsManager()
		authService := auth.NewWorkOSAuthService(manager)
		ctx := context.Background()
		require.NoError(t, authService.Initialize(ctx))

		middleware := AuthMiddleware(authService)

		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		req := httptest.NewRequest("GET", "/test", nil)
		// No Authorization header
		c.Request = req

		middleware(c)

		// Should fail without authorization header
		assert.Equal(t, http.StatusUnauthorized, w.Code)
		assert.True(t, c.IsAborted())
	})
}

func TestLegacyOptionalAuthMiddleware(t *testing.T) {
	gin.SetMode(gin.TestMode)

	t.Run("allows requests without authorization header", func(t *testing.T) {
		middleware := LegacyOptionalAuthMiddleware()

		w := httptest.NewRecorder()
		_, router := gin.CreateTestContext(w)

		router.Use(middleware)
		router.GET("/test", func(c *gin.Context) {
			c.JSON(200, gin.H{"status": "ok"})
		})

		req := httptest.NewRequest("GET", "/test", nil)
		// No Authorization header
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
	})

	t.Run("handles valid authorization header", func(t *testing.T) {
		middleware := LegacyOptionalAuthMiddleware()

		w := httptest.NewRecorder()
		_, router := gin.CreateTestContext(w)

		router.Use(middleware)
		router.GET("/test", func(c *gin.Context) {
			userUUID, exists := c.Get("user_uuid")
			assert.True(t, exists)
			assert.Equal(t, "placeholder-user-uuid", userUUID)
			c.JSON(200, gin.H{"status": "ok"})
		})

		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "Bearer any-token")
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
	})

	t.Run("handles malformed authorization header gracefully", func(t *testing.T) {
		middleware := LegacyOptionalAuthMiddleware()

		w := httptest.NewRecorder()
		_, router := gin.CreateTestContext(w)

		router.Use(middleware)
		router.GET("/test", func(c *gin.Context) {
			c.JSON(200, gin.H{"status": "ok"})
		})

		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "InvalidFormat token")
		router.ServeHTTP(w, req)

		// Should continue without setting user context
		assert.Equal(t, http.StatusOK, w.Code)
	})

	t.Run("handles authorization header with only Bearer", func(t *testing.T) {
		middleware := LegacyOptionalAuthMiddleware()

		w := httptest.NewRecorder()
		_, router := gin.CreateTestContext(w)

		router.Use(middleware)
		router.GET("/test", func(c *gin.Context) {
			c.JSON(200, gin.H{"status": "ok"})
		})

		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "Bearer")
		router.ServeHTTP(w, req)

		// Should continue without setting user context
		assert.Equal(t, http.StatusOK, w.Code)
	})

	t.Run("handles empty authorization header", func(t *testing.T) {
		middleware := LegacyOptionalAuthMiddleware()

		w := httptest.NewRecorder()
		_, router := gin.CreateTestContext(w)

		router.Use(middleware)
		router.GET("/test", func(c *gin.Context) {
			c.JSON(200, gin.H{"status": "ok"})
		})

		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "")
		router.ServeHTTP(w, req)

		// Should continue without setting user context
		assert.Equal(t, http.StatusOK, w.Code)
	})
}

func TestAuthMiddlewareWithFallback_EdgeCases(t *testing.T) {
	gin.SetMode(gin.TestMode)

	t.Run("handles nil auth service", func(t *testing.T) {
		middleware := AuthMiddlewareWithFallback(nil)

		w := httptest.NewRecorder()
		_, router := gin.CreateTestContext(w)

		router.Use(middleware)
		router.GET("/test", func(c *gin.Context) {
			userUUID, exists := c.Get("user_uuid")
			assert.True(t, exists)
			assert.Equal(t, "user", userUUID)
			c.JSON(200, gin.H{"status": "ok"})
		})

		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "Bearer test-user-test_at_example.com")
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
	})

	t.Run("handles missing authorization header with nil auth service", func(t *testing.T) {
		middleware := AuthMiddlewareWithFallback(nil)

		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		req := httptest.NewRequest("GET", "/test", nil)
		// No Authorization header
		c.Request = req

		middleware(c)

		assert.Equal(t, http.StatusUnauthorized, w.Code)
		assert.True(t, c.IsAborted())

		// Check response body
		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		assert.Equal(t, "missing authorization header", response["error"])
		assert.Equal(t, "UNAUTHORIZED", response["code"])
	})

	t.Run("handles invalid authorization header format with nil auth service", func(t *testing.T) {
		middleware := AuthMiddlewareWithFallback(nil)

		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "InvalidFormat token")
		c.Request = req

		middleware(c)

		assert.Equal(t, http.StatusUnauthorized, w.Code)
		assert.True(t, c.IsAborted())

		// Check response body
		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		assert.Equal(t, "invalid authorization header format", response["error"])
		assert.Equal(t, "UNAUTHORIZED", response["code"])
	})

	t.Run("handles invalid token with nil auth service", func(t *testing.T) {
		middleware := AuthMiddlewareWithFallback(nil)

		w := httptest.NewRecorder()
		c, _ := gin.CreateTestContext(w)
		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "Bearer invalid-token")
		c.Request = req

		middleware(c)

		assert.Equal(t, http.StatusUnauthorized, w.Code)
		assert.True(t, c.IsAborted())

		// Check response body
		var response map[string]interface{}
		err := json.Unmarshal(w.Body.Bytes(), &response)
		require.NoError(t, err)
		assert.Equal(t, "invalid or expired token", response["error"])
		assert.Equal(t, "UNAUTHORIZED", response["code"])
	})
}

func TestOptionalAuthMiddleware_EdgeCases(t *testing.T) {
	gin.SetMode(gin.TestMode)

	t.Run("handles nil auth service", func(t *testing.T) {
		middleware := OptionalAuthMiddleware(nil)

		w := httptest.NewRecorder()
		_, router := gin.CreateTestContext(w)

		router.Use(middleware)
		router.GET("/test", func(c *gin.Context) {
			userUUID, exists := c.Get("user_uuid")
			assert.True(t, exists)
			assert.Equal(t, "user", userUUID)
			c.JSON(200, gin.H{"status": "ok"})
		})

		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "Bearer test-user-test_at_example.com")
		router.ServeHTTP(w, req)

		assert.Equal(t, http.StatusOK, w.Code)
	})

	t.Run("handles malformed authorization header with nil auth service", func(t *testing.T) {
		middleware := OptionalAuthMiddleware(nil)

		w := httptest.NewRecorder()
		_, router := gin.CreateTestContext(w)

		router.Use(middleware)
		router.GET("/test", func(c *gin.Context) {
			c.JSON(200, gin.H{"status": "ok"})
		})

		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "InvalidFormat token")
		router.ServeHTTP(w, req)

		// Should continue without setting user context
		assert.Equal(t, http.StatusOK, w.Code)
	})

	t.Run("handles authorization header with only Bearer with nil auth service", func(t *testing.T) {
		middleware := OptionalAuthMiddleware(nil)

		w := httptest.NewRecorder()
		_, router := gin.CreateTestContext(w)

		router.Use(middleware)
		router.GET("/test", func(c *gin.Context) {
			c.JSON(200, gin.H{"status": "ok"})
		})

		req := httptest.NewRequest("GET", "/test", nil)
		req.Header.Set("Authorization", "Bearer")
		router.ServeHTTP(w, req)

		// Should continue without setting user context
		assert.Equal(t, http.StatusOK, w.Code)
	})
}

// Helper function to set up mock secrets manager
func setupMockSecretsManager() *secrets.Manager {
	manager := secrets.New(secrets.Config{CacheTTL: time.Minute})
	mock := &mockProvider{
		secrets: map[string]string{
			secrets.SecretWorkOSClientID:     "test-client-id",
			secrets.SecretWorkOSClientSecret: "test-client-secret",
			secrets.SecretWorkOSAPIKey:       "test-api-key",
		},
	}
	manager.RegisterProvider("mock", mock)
	return manager
}

// mockProvider implements the secrets.Provider interface for testing
type mockProvider struct {
	secrets map[string]string
}

func (m *mockProvider) GetSecret(ctx context.Context, key string) (string, error) {
	if secret, exists := m.secrets[key]; exists {
		return secret, nil
	}
	return "", fmt.Errorf("secret not found: %s", key)
}

func (m *mockProvider) SetSecret(ctx context.Context, key, value string) error {
	if m.secrets == nil {
		m.secrets = make(map[string]string)
	}
	m.secrets[key] = value
	return nil
}

func (m *mockProvider) DeleteSecret(ctx context.Context, key string) error {
	delete(m.secrets, key)
	return nil
}

func (m *mockProvider) ListSecrets(ctx context.Context) ([]string, error) {
	keys := make([]string, 0, len(m.secrets))
	for key := range m.secrets {
		keys = append(keys, key)
	}
	return keys, nil
}