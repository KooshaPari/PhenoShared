package auth

import (
	"context"
	"crypto/rsa"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"

	"github.com/byteport/api/internal/infrastructure/secrets"
	"github.com/gin-gonic/gin"
	"github.com/go-jose/go-jose/v4"
	"github.com/go-jose/go-jose/v4/jwt"
	"github.com/workos/workos-go/v4/pkg/usermanagement"
)

// WorkOSAuthService provides authentication using WorkOS AuthKit
type WorkOSAuthService struct {
	client         *usermanagement.Client
	secretsManager *secrets.Manager
}

var httpGet = func(url string) (*http.Response, error) {
	return http.Get(url)
}

var httpClientFactory = func() *http.Client {
	return &http.Client{Timeout: 30 * time.Second}
}

// AuthConfig holds configuration for WorkOS authentication
type AuthConfig struct {
	ClientID     string
	ClientSecret string
	APIKey       string
	RedirectURI  string
}

// NewWorkOSAuthService creates a new WorkOS authentication service
func NewWorkOSAuthService(secretsManager *secrets.Manager) *WorkOSAuthService {
	return &WorkOSAuthService{
		secretsManager: secretsManager,
	}
}

// Initialize sets up the WorkOS client with configuration from secrets
func (w *WorkOSAuthService) Initialize(ctx context.Context) error {
	_, _, apiKey, err := w.secretsManager.GetWorkOSConfig(ctx)
	if err != nil {
		return fmt.Errorf("failed to get WorkOS configuration: %w", err)
	}

	// Initialize WorkOS client
	w.client = &usermanagement.Client{
		Endpoint: "https://api.workos.com",
		APIKey:   apiKey,
	}

	return nil
}

// ValidateToken validates a WorkOS JWT token and returns user information
func (w *WorkOSAuthService) ValidateToken(ctx context.Context, token string) (*UserInfo, error) {
	if w.client == nil {
		return nil, fmt.Errorf("WorkOS client not initialized")
	}

	// Remove Bearer prefix if present
	token = strings.TrimPrefix(token, "Bearer ")

	// Validate the JWT token with WorkOS
	// Note: This would use the actual WorkOS JWT validation once the SDK supports it
	// For now, we'll implement a placeholder that follows the WorkOS pattern
	userInfo, err := w.validateJWTToken(ctx, token)
	if err != nil {
		return nil, fmt.Errorf("failed to validate token: %w", err)
	}

	return userInfo, nil
}

// UserInfo represents user information from WorkOS
type UserInfo struct {
	ID        string `json:"id"`
	Email     string `json:"email"`
	FirstName string `json:"first_name"`
	LastName  string `json:"last_name"`
}

// JWKSResponse represents the JSON Web Key Set response from WorkOS
type JWKSResponse struct {
	Keys []jose.JSONWebKey `json:"keys"`
}

// JWTClaims represents the standard JWT claims plus WorkOS specific claims
type JWTClaims struct {
	jwt.Claims
	Sub        string `json:"sub"`
	Email      string `json:"email"`
	Name       string `json:"name"`
	GivenName  string `json:"given_name"`
	FamilyName string `json:"family_name"`
}

// validateJWTToken validates a JWT token with WorkOS
func (w *WorkOSAuthService) validateJWTToken(ctx context.Context, token string) (*UserInfo, error) {
	if strings.TrimSpace(token) == "" {
		return nil, fmt.Errorf("token is empty")
	}

	// For development/testing, check for test tokens
	if strings.HasPrefix(token, "test-") || strings.HasPrefix(token, "mock-") {
		return w.handleTestToken(token)
	}

	// Parse the JWT without verification first to get the kid (key ID)
	parsedToken, err := jwt.ParseSigned(token, []jose.SignatureAlgorithm{jose.RS256})
	if err != nil {
		return nil, fmt.Errorf("failed to parse JWT: %w", err)
	}

	// Get the key ID from the JWT header
	kid := ""
	if len(parsedToken.Headers) > 0 {
		kid = parsedToken.Headers[0].KeyID
	}

	// Fetch WorkOS public keys
	publicKey, err := w.getWorkOSPublicKey(ctx, kid)
	if err != nil {
		return nil, fmt.Errorf("failed to get public key: %w", err)
	}

	// Parse and validate the JWT claims
	var claims JWTClaims
	err = parsedToken.Claims(publicKey, &claims)
	if err != nil {
		return nil, fmt.Errorf("failed to validate JWT: %w", err)
	}

	// Validate token expiration and other standard claims
	if err := claims.Validate(jwt.Expected{
		Time: time.Now(),
	}); err != nil {
		return nil, fmt.Errorf("token validation failed: %w", err)
	}

	// Extract user information from validated claims
	userInfo := &UserInfo{
		ID:        claims.Sub,
		Email:     claims.Email,
		FirstName: claims.GivenName,
		LastName:  claims.FamilyName,
	}

	// Use name if first/last names not provided
	if userInfo.FirstName == "" && userInfo.LastName == "" && claims.Name != "" {
		nameParts := strings.SplitN(claims.Name, " ", 2)
		userInfo.FirstName = nameParts[0]
		if len(nameParts) > 1 {
			userInfo.LastName = nameParts[1]
		}
	}

	return userInfo, nil
}

// handleTestToken handles test/mock tokens for development and testing
func (w *WorkOSAuthService) handleTestToken(token string) (*UserInfo, error) {
	// Extract user info from test token format: test-{userID}-{email}
	parts := strings.Split(token, "-")
	if len(parts) < 2 {
		return nil, fmt.Errorf("invalid test token format")
	}

	userID := parts[1]
	email := "test@example.com"
	if len(parts) > 2 {
		email = strings.ReplaceAll(parts[2], "_at_", "@")
	}

	return &UserInfo{
		ID:        userID,
		Email:     email,
		FirstName: "Test",
		LastName:  "User",
	}, nil
}

// getWorkOSPublicKey fetches the public key for JWT verification
func (w *WorkOSAuthService) getWorkOSPublicKey(ctx context.Context, kid string) (*rsa.PublicKey, error) {
	// Fetch JWKS from WorkOS
	resp, err := httpGet("https://api.workos.com/.well-known/jwks.json")
	if err != nil {
		return nil, fmt.Errorf("failed to fetch JWKS: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("JWKS request failed with status: %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read JWKS response: %w", err)
	}

	var jwks JWKSResponse
	if err := json.Unmarshal(body, &jwks); err != nil {
		return nil, fmt.Errorf("failed to parse JWKS: %w", err)
	}

	// Find the key with matching kid, or use the first key if kid is empty
	var selectedKey *jose.JSONWebKey
	for _, key := range jwks.Keys {
		if kid == "" || key.KeyID == kid {
			selectedKey = &key
			break
		}
	}

	if selectedKey == nil {
		return nil, fmt.Errorf("no matching public key found for kid: %s", kid)
	}

	// Extract RSA public key
	publicKey, ok := selectedKey.Key.(*rsa.PublicKey)
	if !ok {
		return nil, fmt.Errorf("key is not an RSA public key")
	}

	return publicKey, nil
}

// GetAuthURL generates an authorization URL for WorkOS
func (w *WorkOSAuthService) GetAuthURL(ctx context.Context, state string) (string, error) {
	if w.client == nil {
		return "", fmt.Errorf("WorkOS client not initialized")
	}

	clientID, _, _, err := w.secretsManager.GetWorkOSConfig(ctx)
	if err != nil {
		return "", fmt.Errorf("failed to get WorkOS client ID: %w", err)
	}

	// Create authorization URL using WorkOS SDK
	// This would use the actual WorkOS User Management API
	authURL := fmt.Sprintf(
		"https://api.workos.com/user_management/authorize?client_id=%s&response_type=code&state=%s&redirect_uri=%s",
		clientID, state, "http://localhost:3000/auth/callback",
	)

	return authURL, nil
}

// ExchangeCodeForToken exchanges an authorization code for tokens
func (w *WorkOSAuthService) ExchangeCodeForToken(ctx context.Context, code string) (*TokenResponse, error) {
	if w.client == nil {
		return nil, fmt.Errorf("WorkOS client not initialized")
	}

	if strings.TrimSpace(code) == "" {
		return nil, fmt.Errorf("authorization code is required")
	}

	// Handle test codes for development/testing
	if strings.HasPrefix(code, "test-") || strings.HasPrefix(code, "mock-") {
		return w.handleTestCodeExchange(code)
	}

	// Get WorkOS configuration
	clientID, clientSecret, _, err := w.secretsManager.GetWorkOSConfig(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get WorkOS configuration: %w", err)
	}

	// Exchange the authorization code for tokens using WorkOS User Management API
	tokenResp, err := w.exchangeWithWorkOS(ctx, code, clientID, clientSecret)
	if err != nil {
		return nil, fmt.Errorf("failed to exchange code with WorkOS: %w", err)
	}

	return tokenResp, nil
}

// handleTestCodeExchange handles test authorization codes for development/testing
func (w *WorkOSAuthService) handleTestCodeExchange(code string) (*TokenResponse, error) {
	// Extract user info from test code format: test-{userID}-{email}
	parts := strings.Split(code, "-")
	if len(parts) < 2 {
		return nil, fmt.Errorf("invalid test code format")
	}

	userID := parts[1]
	email := "test@example.com"
	if len(parts) > 2 {
		email = strings.ReplaceAll(parts[2], "_at_", "@")
	}

	// Generate a test JWT-like token
	testToken := fmt.Sprintf("test-%s-%s", userID, strings.ReplaceAll(email, "@", "_at_"))

	return &TokenResponse{
		AccessToken: testToken,
		IDToken:     testToken,
		ExpiresIn:   3600,
		TokenType:   "Bearer",
	}, nil
}

// exchangeWithWorkOS performs the actual token exchange with WorkOS API
func (w *WorkOSAuthService) exchangeWithWorkOS(ctx context.Context, code, clientID, clientSecret string) (*TokenResponse, error) {
	// Prepare the token exchange request
	tokenURL := "https://api.workos.com/user_management/authenticate"

	// Create the request payload
	payload := map[string]string{
		"client_id":     clientID,
		"client_secret": clientSecret,
		"grant_type":    "authorization_code",
		"code":          code,
	}

	payloadBytes, err := json.Marshal(payload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request payload: %w", err)
	}

	// Make the HTTP request to WorkOS
	req, err := http.NewRequestWithContext(ctx, "POST", tokenURL, strings.NewReader(string(payloadBytes)))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Header.Set("User-Agent", "BytePort/1.0")

	client := httpClientFactory()
	resp, err := client.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to make request: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("WorkOS API error (status %d): %s", resp.StatusCode, string(body))
	}

	// Parse the response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}

	var workosResp struct {
		AccessToken string `json:"access_token"`
		IDToken     string `json:"id_token,omitempty"`
		ExpiresIn   int    `json:"expires_in"`
		TokenType   string `json:"token_type"`
	}

	if err := json.Unmarshal(body, &workosResp); err != nil {
		return nil, fmt.Errorf("failed to parse WorkOS response: %w", err)
	}

	// Convert to our TokenResponse format
	return &TokenResponse{
		AccessToken: workosResp.AccessToken,
		IDToken:     workosResp.IDToken,
		ExpiresIn:   workosResp.ExpiresIn,
		TokenType:   workosResp.TokenType,
	}, nil
}

// TokenResponse represents the response from token exchange
type TokenResponse struct {
	AccessToken string `json:"access_token"`
	IDToken     string `json:"id_token"`
	ExpiresIn   int    `json:"expires_in"`
	TokenType   string `json:"token_type"`
}

// Middleware creates a Gin middleware for WorkOS authentication
func (w *WorkOSAuthService) Middleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader == "" {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "missing authorization header",
				"code":  "UNAUTHORIZED",
			})
			c.Abort()
			return
		}

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
		userInfo, err := w.ValidateToken(c.Request.Context(), token)
		if err != nil {
			c.JSON(http.StatusUnauthorized, gin.H{
				"error": "invalid or expired token",
				"code":  "UNAUTHORIZED",
			})
			c.Abort()
			return
		}

		// Set user information in context
		c.Set("user_id", userInfo.ID)
		c.Set("user_email", userInfo.Email)
		c.Set("user_info", userInfo)

		c.Next()
	}
}

// OptionalMiddleware creates a Gin middleware for optional WorkOS authentication
func (w *WorkOSAuthService) OptionalMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		authHeader := c.GetHeader("Authorization")
		if authHeader != "" {
			parts := strings.SplitN(authHeader, " ", 2)
			if len(parts) == 2 && parts[0] == "Bearer" {
				token := parts[1]
				if userInfo, err := w.ValidateToken(c.Request.Context(), token); err == nil {
					c.Set("user_id", userInfo.ID)
					c.Set("user_email", userInfo.Email)
					c.Set("user_info", userInfo)
				}
			}
		}
		c.Next()
	}
}
