package secrets

import (
	"context"
	"crypto"
	"crypto/rand"
	"crypto/rsa"
	"crypto/sha256"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"
)

const (
	gcpSecretManagerHost      = "https://secretmanager.googleapis.com"
	gcpSecretManagerAPIVer    = "v1"
	gcpDefaultScope           = "https://www.googleapis.com/auth/cloud-platform"
	serviceAccountJSONEnv     = "GOOGLE_APPLICATION_CREDENTIALS_JSON"
	serviceAccountScopeEnv    = "GOOGLE_SECRET_MANAGER_SCOPE"
	serviceAccountTokenURIEnv = "GOOGLE_OAUTH_TOKEN_URI"
)

// GoogleSecretManagerProvider implements the secrets.Provider backed by Google Secret Manager.
type GoogleSecretManagerProvider struct {
	projectID     string
	baseURL       string
	httpClient    httpClient
	tokenProvider tokenProvider

	mu    sync.Mutex
	token accessToken
}

// NewGoogleSecretManagerProvider constructs a provider with the given HTTP client and token provider.
func NewGoogleSecretManagerProvider(projectID string, client httpClient, provider tokenProvider) (*GoogleSecretManagerProvider, error) {
	if projectID == "" {
		return nil, fmt.Errorf("project ID is required")
	}
	if client == nil {
		client = defaultHTTPClient()
	}
	if provider == nil {
		return nil, fmt.Errorf("token provider is required")
	}

	return &GoogleSecretManagerProvider{
		projectID:     projectID,
		baseURL:       fmt.Sprintf("%s/%s", gcpSecretManagerHost, gcpSecretManagerAPIVer),
		httpClient:    client,
		tokenProvider: provider,
	}, nil
}

// NewGoogleSecretManagerProviderFromEnv constructs a provider using a service account JSON stored in the
// GOOGLE_APPLICATION_CREDENTIALS_JSON environment variable. The project ID is loaded from GCP_PROJECT_ID.
func NewGoogleSecretManagerProviderFromEnv() (*GoogleSecretManagerProvider, error) {
	projectID := os.Getenv("GCP_PROJECT_ID")
	if projectID == "" {
		return nil, fmt.Errorf("GCP_PROJECT_ID is not configured")
	}

	serviceAccountJSON := os.Getenv(serviceAccountJSONEnv)
	if serviceAccountJSON == "" {
		return nil, fmt.Errorf("%s environment variable must contain service account JSON", serviceAccountJSONEnv)
	}

	scope := os.Getenv(serviceAccountScopeEnv)
	if scope == "" {
		scope = gcpDefaultScope
	}

	tokenProvider, err := newGoogleServiceAccountTokenProvider(serviceAccountJSON, scope)
	if err != nil {
		return nil, err
	}

	return NewGoogleSecretManagerProvider(projectID, defaultHTTPClient(), tokenProvider)
}

func (p *GoogleSecretManagerProvider) GetSecret(ctx context.Context, key string) (string, error) {
	endpoint := fmt.Sprintf("%s/projects/%s/secrets/%s/versions/latest:access", p.baseURL, p.projectID, url.PathEscape(key))
	body, err := p.doGoogleRequest(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return "", fmt.Errorf("gcp get secret: %w", err)
	}

	var resp struct {
		Payload struct {
			Data string `json:"data"`
		} `json:"payload"`
	}
	if err := json.Unmarshal(body, &resp); err != nil {
		return "", fmt.Errorf("failed to decode GCP secret response: %w", err)
	}
	if resp.Payload.Data == "" {
		return "", fmt.Errorf("secret '%s' has no payload", key)
	}

	decoded, err := base64.StdEncoding.DecodeString(resp.Payload.Data)
	if err != nil {
		return "", fmt.Errorf("failed to decode GCP secret payload: %w", err)
	}
	return string(decoded), nil
}

func (p *GoogleSecretManagerProvider) SetSecret(ctx context.Context, key string, value string) error {
	if err := p.ensureSecretExists(ctx, key); err != nil {
		return err
	}

	endpoint := fmt.Sprintf("%s/projects/%s/secrets/%s:addVersion", p.baseURL, p.projectID, url.PathEscape(key))
	payload := map[string]map[string]string{
		"payload": {
			"data": base64.StdEncoding.EncodeToString([]byte(value)),
		},
	}
	data, err := jsonMarshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal GCP add version payload: %w", err)
	}

	_, err = p.doGoogleRequest(ctx, http.MethodPost, endpoint, strings.NewReader(string(data)))
	if err != nil {
		return fmt.Errorf("gcp add secret version: %w", err)
	}
	return nil
}

func (p *GoogleSecretManagerProvider) DeleteSecret(ctx context.Context, key string) error {
	endpoint := fmt.Sprintf("%s/projects/%s/secrets/%s", p.baseURL, p.projectID, url.PathEscape(key))
	_, err := p.doGoogleRequest(ctx, http.MethodDelete, endpoint, nil)
	if err != nil {
		return fmt.Errorf("gcp delete secret: %w", err)
	}
	return nil
}

func (p *GoogleSecretManagerProvider) ListSecrets(ctx context.Context) ([]string, error) {
	endpoint := fmt.Sprintf("%s/projects/%s/secrets", p.baseURL, p.projectID)
	var secrets []string

	for endpoint != "" {
		body, err := p.doGoogleRequest(ctx, http.MethodGet, endpoint, nil)
		if err != nil {
			return nil, fmt.Errorf("gcp list secrets: %w", err)
		}

		var resp struct {
			Secrets []struct {
				Name string `json:"name"`
			} `json:"secrets"`
			NextToken string `json:"nextPageToken"`
		}

		if err := json.Unmarshal(body, &resp); err != nil {
			return nil, fmt.Errorf("failed to decode GCP secrets list: %w", err)
		}

		for _, s := range resp.Secrets {
			parts := strings.Split(s.Name, "/secrets/")
			if len(parts) == 2 {
				secrets = append(secrets, parts[1])
			}
		}

		if resp.NextToken == "" {
			break
		}
		endpoint = fmt.Sprintf("%s/projects/%s/secrets?pageToken=%s", p.baseURL, p.projectID, url.QueryEscape(resp.NextToken))
	}

	return secrets, nil
}

func (p *GoogleSecretManagerProvider) ensureSecretExists(ctx context.Context, key string) error {
	endpoint := fmt.Sprintf("%s/projects/%s/secrets/%s", p.baseURL, p.projectID, url.PathEscape(key))
	_, err := p.doGoogleRequest(ctx, http.MethodGet, endpoint, nil)
	if err == nil {
		return nil
	}
	if !isNotFoundError(err) {
		return err
	}

	createEndpoint := fmt.Sprintf("%s/projects/%s/secrets?secretId=%s", p.baseURL, p.projectID, url.QueryEscape(key))
	payload := map[string]any{
		"replication": map[string]any{
			"automatic": map[string]any{},
		},
	}
	data, err := jsonMarshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal GCP create secret payload: %w", err)
	}

	_, err = p.doGoogleRequest(ctx, http.MethodPost, createEndpoint, strings.NewReader(string(data)))
	if err != nil {
		return fmt.Errorf("gcp create secret: %w", err)
	}
	return nil
}

func (p *GoogleSecretManagerProvider) doGoogleRequest(ctx context.Context, method, endpoint string, body io.Reader) ([]byte, error) {
	req, err := http.NewRequestWithContext(ctx, method, endpoint, body)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %w", err)
	}
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}

	token, err := p.getToken(ctx)
	if err != nil {
		return nil, err
	}
	req.Header.Set("Authorization", "Bearer "+token.Value)

	resp, err := p.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("gcp request failed: %w", err)
	}

	responseBody, err := readResponseBody(resp)
	if err != nil {
		return nil, err
	}
	if resp.StatusCode == http.StatusNotFound {
		return nil, fmt.Errorf("not found: %s", string(responseBody))
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return nil, fmt.Errorf("gcp request failed with status %d: %s", resp.StatusCode, string(responseBody))
	}

	return responseBody, nil
}

func (p *GoogleSecretManagerProvider) getToken(ctx context.Context) (accessToken, error) {
	p.mu.Lock()
	defer p.mu.Unlock()

	if p.token.Value != "" && time.Until(p.token.Expiry) > time.Minute {
		return p.token, nil
	}

	token, err := p.tokenProvider.Token(ctx, gcpDefaultScope)
	if err != nil {
		return accessToken{}, fmt.Errorf("failed to fetch Google access token: %w", err)
	}
	p.token = token
	return token, nil
}

// googleServiceAccountTokenProvider implements JWT bearer token flow for service accounts.
type googleServiceAccountTokenProvider struct {
	clientEmail string
	privateKey  *rsa.PrivateKey
	tokenURI    string
	httpClient  httpClient
	scope       string
}

func newGoogleServiceAccountTokenProvider(jsonData string, scope string) (*googleServiceAccountTokenProvider, error) {
	var sa struct {
		ClientEmail string `json:"client_email"`
		PrivateKey  string `json:"private_key"`
		TokenURI    string `json:"token_uri"`
	}

	if err := json.Unmarshal([]byte(jsonData), &sa); err != nil {
		return nil, fmt.Errorf("failed to parse service account JSON: %w", err)
	}
	if sa.ClientEmail == "" || sa.PrivateKey == "" || sa.TokenURI == "" {
		return nil, fmt.Errorf("service account JSON missing required fields")
	}

	block, _ := pem.Decode([]byte(sa.PrivateKey))
	if block == nil {
		return nil, fmt.Errorf("failed to decode service account private key")
	}

	key, err := parsePrivateKey(block.Bytes)
	if err != nil {
		return nil, fmt.Errorf("failed to parse service account private key: %w", err)
	}

	if scope == "" {
		scope = gcpDefaultScope
	}

	return &googleServiceAccountTokenProvider{
		clientEmail: sa.ClientEmail,
		privateKey:  key,
		tokenURI:    sa.TokenURI,
		httpClient:  defaultHTTPClient(),
		scope:       scope,
	}, nil
}

func (p *googleServiceAccountTokenProvider) Token(ctx context.Context, scope string) (accessToken, error) {
	if scope == "" {
		scope = p.scope
	}

	now := time.Now()
	claims := map[string]any{
		"iss":   p.clientEmail,
		"scope": scope,
		"aud":   p.tokenURI,
		"exp":   now.Add(time.Hour).Unix(),
		"iat":   now.Unix(),
	}

	payload, err := jsonMarshal(claims)
	if err != nil {
		return accessToken{}, fmt.Errorf("failed to marshal service account claims: %w", err)
	}

	header := base64.RawURLEncoding.EncodeToString([]byte(`{"alg":"RS256","typ":"JWT"}`))
	claim := base64.RawURLEncoding.EncodeToString(payload)
	signingInput := header + "." + claim

	hash := sha256.Sum256([]byte(signingInput))
	signature, err := rsa.SignPKCS1v15(rand.Reader, p.privateKey, crypto.SHA256, hash[:])
	if err != nil {
		return accessToken{}, fmt.Errorf("failed to sign JWT: %w", err)
	}

	jwtAssertion := signingInput + "." + base64.RawURLEncoding.EncodeToString(signature)

	form := url.Values{}
	form.Set("grant_type", "urn:ietf:params:oauth:grant-type:jwt-bearer")
	form.Set("assertion", jwtAssertion)

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, p.tokenURI, strings.NewReader(form.Encode()))
	if err != nil {
		return accessToken{}, fmt.Errorf("failed to create service account token request: %w", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	client := p.httpClient
	if client == nil {
		client = defaultHTTPClient()
	}

	resp, err := client.Do(req)
	if err != nil {
		return accessToken{}, fmt.Errorf("failed to execute service account token request: %w", err)
	}

	body, err := readResponseBody(resp)
	if err != nil {
		return accessToken{}, err
	}
	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return accessToken{}, fmt.Errorf("service account token endpoint returned %d: %s", resp.StatusCode, string(body))
	}

	var tokenResp struct {
		AccessToken string `json:"access_token"`
		ExpiresIn   int64  `json:"expires_in"`
	}
	if err := json.Unmarshal(body, &tokenResp); err != nil {
		return accessToken{}, fmt.Errorf("failed to decode service account token response: %w", err)
	}
	if tokenResp.AccessToken == "" {
		return accessToken{}, fmt.Errorf("service account token response missing access_token")
	}

	return accessToken{
		Value:  tokenResp.AccessToken,
		Expiry: time.Now().Add(time.Duration(tokenResp.ExpiresIn) * time.Second),
	}, nil
}

func parsePrivateKey(der []byte) (*rsa.PrivateKey, error) {
	if key, err := x509.ParsePKCS8PrivateKey(der); err == nil {
		if rsaKey, ok := key.(*rsa.PrivateKey); ok {
			return rsaKey, nil
		}
		return nil, fmt.Errorf("pkcs8 key is not RSA")
	}
	if key, err := x509.ParsePKCS1PrivateKey(der); err == nil {
		return key, nil
	}
	return nil, fmt.Errorf("unsupported private key format")
}

func isNotFoundError(err error) bool {
	if err == nil {
		return false
	}
	return strings.Contains(strings.ToLower(err.Error()), "not found")
}
