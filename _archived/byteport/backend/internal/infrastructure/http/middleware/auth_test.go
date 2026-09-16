package middleware

import (
	"context"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func setupTestRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	return gin.New()
}

func TestLegacyAuthMiddleware_SetsUUID(t *testing.T) {
	router := setupTestRouter()
	router.Use(LegacyAuthMiddleware())

	var captured string
	router.GET("/test", func(c *gin.Context) {
		if uuid, ok := c.Get("user_uuid"); ok {
			captured = uuid.(string)
		}
		c.Status(http.StatusOK)
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Authorization", "Bearer token")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "placeholder-user-uuid", captured)
}

func TestLegacyAuthMiddleware_MissingHeader(t *testing.T) {
	router := setupTestRouter()
	router.Use(LegacyAuthMiddleware())
	router.GET("/test", func(c *gin.Context) {})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusUnauthorized, w.Code)
	assert.Contains(t, w.Body.String(), "missing authorization header")
	assert.Contains(t, w.Body.String(), "UNAUTHORIZED")
}

func TestLegacyAuthMiddleware_InvalidHeader(t *testing.T) {
	cases := []string{"Invalid", "Basic token", "Bearer"}
	for _, header := range cases {
		t.Run(header, func(t *testing.T) {
			router := setupTestRouter()
			router.Use(LegacyAuthMiddleware())
			router.GET("/test", func(c *gin.Context) {})

			req := httptest.NewRequest(http.MethodGet, "/test", nil)
			req.Header.Set("Authorization", header)
			w := httptest.NewRecorder()

			router.ServeHTTP(w, req)
			assert.Equal(t, http.StatusUnauthorized, w.Code)
		})
	}
}

func TestAuthMiddlewareWithFallback_TestToken(t *testing.T) {
	router := setupTestRouter()
	router.Use(AuthMiddlewareWithFallback(nil))

	var capturedEmail string
	router.GET("/test", func(c *gin.Context) {
		if email, ok := c.Get("user_email"); ok {
			capturedEmail = email.(string)
		}
		c.Status(http.StatusOK)
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Authorization", "Bearer test-123-user_at_example.com")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)

	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "user@example.com", capturedEmail)
}

func TestAuthMiddlewareWithFallback_InvalidTestToken(t *testing.T) {
	router := setupTestRouter()
	router.Use(AuthMiddlewareWithFallback(nil))
	router.GET("/test", func(c *gin.Context) {})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Authorization", "Bearer invalid")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
}

func TestAuthMiddlewareWithFallback_RealTokenUnsupported(t *testing.T) {
	router := setupTestRouter()
	router.Use(AuthMiddlewareWithFallback(nil))
	router.GET("/test", func(c *gin.Context) {})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Authorization", "Bearer real-token")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusUnauthorized, w.Code)
	assert.Contains(t, w.Body.String(), "UNAUTHORIZED")
}

func TestOptionalAuthMiddleware_FallbackSetsContext(t *testing.T) {
	router := setupTestRouter()
	router.Use(OptionalAuthMiddleware(nil))

	var userID string
	router.GET("/test", func(c *gin.Context) {
		if id, ok := c.Get("user_id"); ok {
			userID = id.(string)
		}
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Authorization", "Bearer test-123")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
	assert.Equal(t, "123", userID)
}

func TestOptionalAuthMiddleware_FallbackIgnoresInvalid(t *testing.T) {
	router := setupTestRouter()
	router.Use(OptionalAuthMiddleware(nil))

	router.GET("/test", func(c *gin.Context) {
		_, exists := c.Get("user_id")
		assert.False(t, exists)
		c.Status(http.StatusOK)
	})

	req := httptest.NewRequest(http.MethodGet, "/test", nil)
	req.Header.Set("Authorization", "Bearer invalid")
	w := httptest.NewRecorder()

	router.ServeHTTP(w, req)
	assert.Equal(t, http.StatusOK, w.Code)
}

func TestHandleFallbackTestToken(t *testing.T) {
	info, err := handleFallbackTestToken("test-abc-user_at_example.com")
	require.NoError(t, err)
	assert.Equal(t, "abc", info.ID)
	assert.Equal(t, "user@example.com", info.Email)

	_, err = handleFallbackTestToken("malformed")
	require.Error(t, err)
}

func TestValidateTokenWithFallback(t *testing.T) {
	ctx := context.Background()
	info, err := validateTokenWithFallback(ctx, "test-xyz")
	require.NoError(t, err)
	assert.Equal(t, "xyz", info.ID)

	_, err = validateTokenWithFallback(ctx, "real-token")
	require.Error(t, err)
}

func contains(s, substr string) bool {
	return strings.Contains(s, substr)
}
