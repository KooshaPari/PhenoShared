package middleware

import (
	"context"
	"fmt"
	"net/http"
	"strings"

	"github.com/byteport/api/internal/infrastructure/auth"
	"github.com/gin-gonic/gin"
)

// AuthMiddleware validates JWT tokens and sets user context
// This is a wrapper that creates middleware using a WorkOS auth service
func AuthMiddleware(authService *auth.WorkOSAuthService) gin.HandlerFunc {
	return authService.Middleware()
}

// AuthMiddlewareWithFallback creates middleware that falls back to placeholder validation
// when no auth service is provided (for backward compatibility)
func AuthMiddlewareWithFallback(authService *auth.WorkOSAuthService) gin.HandlerFunc {
	if authService != nil {
		return authService.Middleware()
	}

	// Fallback to basic validation for cases where WorkOS service is not available
	return func(c *gin.Context) {
		// Extract token from Authorization header
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "missing authorization header",
				"code":  "UNAUTHORIZED",
			})
			c.Abort()
			return
		}

		// Extract Bearer token
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "invalid authorization header format",
				"code":  "UNAUTHORIZED",
			})
			c.Abort()
			return
		}

		token := parts[1]

		// Validate JWT token with basic validation
		userInfo, err := validateTokenWithFallback(c.Request.Context(), token)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "invalid or expired token",
				"code":  "UNAUTHORIZED",
			})
			c.Abort()
			return
		}

		// Set user information in context for downstream handlers
		c.Set("user_uuid", userInfo.ID)
		c.Set("user_id", userInfo.ID)
		c.Set("user_email", userInfo.Email)
		c.Set("user_info", userInfo)

		c.Next()
	}
}

// LegacyAuthMiddleware provides the original placeholder-based middleware
// for backward compatibility with existing tests
func LegacyAuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		// Extract token from Authorization header
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "missing authorization header",
				"code":  "UNAUTHORIZED",
			})
			c.Abort()
			return
		}

		// Extract Bearer token
		parts := strings.SplitN(authHeader, " ", 2)
		if len(parts) != 2 || parts[0] != "Bearer" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "invalid authorization header format",
				"code":  "UNAUTHORIZED",
			})
			c.Abort()
			return
		}

		token := parts[1]

		// Legacy placeholder validation
		userUUID, err := validateTokenLegacy(token)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "invalid or expired token",
				"code":  "UNAUTHORIZED",
			})
			c.Abort()
			return
		}

		// Set user UUID in context for downstream handlers
		c.Set("user_uuid", userUUID)

		c.Next()
	}
}

// validateTokenWithFallback validates tokens with fallback logic
func validateTokenWithFallback(ctx context.Context, token string) (*auth.UserInfo, error) {
	// Handle test tokens for development/testing
	if strings.HasPrefix(token, "test-") || strings.HasPrefix(token, "mock-") {
		return handleFallbackTestToken(token)
	}

	// For non-test tokens, return an error to force proper WorkOS integration
	return nil, fmt.Errorf("token validation requires WorkOS auth service")
}

// handleFallbackTestToken handles test tokens in fallback mode
func handleFallbackTestToken(token string) (*auth.UserInfo, error) {
	parts := strings.Split(token, "-")
	if len(parts) < 2 {
		return nil, fmt.Errorf("invalid test token format")
	}

	userID := parts[1]
	email := "test@example.com"
	if len(parts) > 2 {
		email = strings.ReplaceAll(parts[2], "_at_", "@")
	}

	return &auth.UserInfo{
		ID:        userID,
		Email:     email,
		FirstName: "Test",
		LastName:  "User",
	}, nil
}

// validateTokenLegacy provides the original placeholder validation
func validateTokenLegacy(token string) (string, error) {
	// Placeholder implementation for backward compatibility
	return "placeholder-user-uuid", nil
}

// OptionalAuthMiddleware allows requests with or without authentication
func OptionalAuthMiddleware(authService *auth.WorkOSAuthService) gin.HandlerFunc {
	if authService != nil {
		return authService.OptionalMiddleware()
	}

	// Fallback for when no auth service is provided
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader != "" {
			parts := strings.SplitN(authHeader, " ", 2)
			if len(parts) == 2 && parts[0] == "Bearer" {
				token := parts[1]
				if userInfo, err := validateTokenWithFallback(c.Request.Context(), token); err == nil {
					c.Set("user_uuid", userInfo.ID)
					c.Set("user_id", userInfo.ID)
					c.Set("user_email", userInfo.Email)
					c.Set("user_info", userInfo)
				}
			}
		}
		c.Next()
	}
}

// LegacyOptionalAuthMiddleware provides the original optional middleware
func LegacyOptionalAuthMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader != "" {
			parts := strings.SplitN(authHeader, " ", 2)
			if len(parts) == 2 && parts[0] == "Bearer" {
				token := parts[1]
				if userUUID, err := validateTokenLegacy(token); err == nil {
					c.Set("user_uuid", userUUID)
				}
			}
		}
		c.Next()
	}
}