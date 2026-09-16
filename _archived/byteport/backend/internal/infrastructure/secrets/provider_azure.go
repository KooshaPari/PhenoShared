package secrets

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
	"sync"
	"time"
)

const (
	azureScopeDefault     = "https://vault.azure.net/.default"
	azureAPIVersion       = "7.3"
	azureTokenURLTemplate = "https://login.microsoftonline.com/%s/oauth2/v2.0/token"
)

// AzureKeyVaultProvider implements the secrets.Provider interface backed by Azure Key Vault.
type AzureKeyVaultProvider struct {
	vaultURL      string
	httpClient    httpClient
	tokenProvider tokenProvider

	mu    sync.Mutex
	token accessToken
}

// NewAzureKeyVaultProvider constructs an Azure Key Vault provider using the supplied HTTP client
// and token provider. The token provider is responsible for returning tokens scoped to the
// Key Vault resource (https://vault.azure.net/.default).
func NewAzureKeyVaultProvider(vaultURL string, client httpClient, provider tokenProvider) (*AzureKeyVaultProvider, error) {
	if vaultURL == "" {
		return nil, fmt.Errorf("vault URL is required")
	}
	if client == nil {
		client = defaultHTTPClient()
	}
	if provider == nil {
		return nil, fmt.Errorf("token provider is required")
	}

	return &AzureKeyVaultProvider{
		vaultURL:      strings.TrimSuffix(vaultURL, "/"),
		httpClient:    client,
		tokenProvider: provider,
	}, nil
}

// NewAzureKeyVaultProviderFromEnv constructs an Azure provider using the standard client credentials
// environment variables:
//
//	AZURE_KEY_VAULT_URL      - the Key Vault URL (e.g., https://example.vault.azure.net)
//	AZURE_TENANT_ID          - Azure AD tenant ID
//	AZURE_CLIENT_ID          - application client ID
//	AZURE_CLIENT_SECRET      - application client secret
func NewAzureKeyVaultProviderFromEnv() (*AzureKeyVaultProvider, error) {
	vaultURL := os.Getenv("AZURE_KEY_VAULT_URL")
	tenantID := os.Getenv("AZURE_TENANT_ID")
	clientID := os.Getenv("AZURE_CLIENT_ID")
	clientSecret := os.Getenv("AZURE_CLIENT_SECRET")

	if vaultURL == "" {
		return nil, fmt.Errorf("AZURE_KEY_VAULT_URL is not configured")
	}
	if tenantID == "" || clientID == "" || clientSecret == "" {
		return nil, fmt.Errorf("AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET must be configured")
	}

	tokenURL := os.Getenv("AZURE_OAUTH_TOKEN_URL")
	if tokenURL == "" {
		tokenURL = fmt.Sprintf(azureTokenURLTemplate, tenantID)
	}

	tokenFetcher := &azureClientCredentialsProvider{
		tenantID:     tenantID,
		clientID:     clientID,
		clientSecret: clientSecret,
		httpClient:   defaultHTTPClient(),
		tokenURL:     tokenURL,
		scope:        azureScopeDefault,
	}

	return NewAzureKeyVaultProvider(vaultURL, defaultHTTPClient(), tokenFetcher)
}

func (p *AzureKeyVaultProvider) GetSecret(ctx context.Context, key string) (string, error) {
	endpoint := fmt.Sprintf("%s/secrets/%s?api-version=%s", p.vaultURL, url.PathEscape(key), azureAPIVersion)
	body, err := p.doAzureRequest(ctx, http.MethodGet, endpoint, nil)
	if err != nil {
		return "", fmt.Errorf("azure get secret: %w", err)
	}

	var resp struct {
		Value *string `json:"value"`
	}
	if err := json.Unmarshal(body, &resp); err != nil {
		return "", fmt.Errorf("failed to decode Azure secret response: %w", err)
	}
	if resp.Value == nil {
		return "", fmt.Errorf("secret '%s' has no value", key)
	}
	return *resp.Value, nil
}

func (p *AzureKeyVaultProvider) SetSecret(ctx context.Context, key string, value string) error {
	endpoint := fmt.Sprintf("%s/secrets/%s?api-version=%s", p.vaultURL, url.PathEscape(key), azureAPIVersion)
	payload := map[string]string{"value": value}
	data, err := jsonMarshal(payload)
	if err != nil {
		return fmt.Errorf("failed to marshal Azure secret payload: %w", err)
	}

	_, err = p.doAzureRequest(ctx, http.MethodPut, endpoint, bytes.NewReader(data))
	if err != nil {
		return fmt.Errorf("azure set secret: %w", err)
	}
	return nil
}

func (p *AzureKeyVaultProvider) DeleteSecret(ctx context.Context, key string) error {
	endpoint := fmt.Sprintf("%s/secrets/%s?api-version=%s", p.vaultURL, url.PathEscape(key), azureAPIVersion)
	_, err := p.doAzureRequest(ctx, http.MethodDelete, endpoint, nil)
	if err != nil {
		return fmt.Errorf("azure delete secret: %w", err)
	}
	return nil
}

func (p *AzureKeyVaultProvider) ListSecrets(ctx context.Context) ([]string, error) {
	endpoint := fmt.Sprintf("%s/secrets?api-version=%s", p.vaultURL, azureAPIVersion)
	var secrets []string

	for endpoint != "" {
		body, err := p.doAzureRequest(ctx, http.MethodGet, endpoint, nil)
		if err != nil {
			return nil, fmt.Errorf("azure list secrets: %w", err)
		}

		var resp struct {
			Value []struct {
				ID string `json:"id"`
			} `json:"value"`
			NextLink string `json:"nextLink"`
		}
		if err := json.Unmarshal(body, &resp); err != nil {
			return nil, fmt.Errorf("failed to decode Azure secrets list: %w", err)
		}

		for _, v := range resp.Value {
			if v.ID == "" {
				continue
			}
			parts := strings.Split(v.ID, "/secrets/")
			if len(parts) == 2 {
				secretName := parts[1]
				if idx := strings.Index(secretName, "/"); idx != -1 {
					secretName = secretName[:idx]
				}
				secrets = append(secrets, secretName)
			}
		}

		if resp.NextLink == "" {
			break
		}
		endpoint = resp.NextLink
	}

	return secrets, nil
}

func (p *AzureKeyVaultProvider) doAzureRequest(ctx context.Context, method, endpoint string, body io.Reader) ([]byte, error) {
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
		return nil, fmt.Errorf("azure request failed: %w", err)
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		respBody, readErr := readResponseBody(resp)
		if readErr != nil {
			return nil, fmt.Errorf("azure request failed with status %d and unreadable body: %w", resp.StatusCode, readErr)
		}
		return nil, fmt.Errorf("azure request failed with status %d: %s", resp.StatusCode, string(respBody))
	}

	return readResponseBody(resp)
}

func (p *AzureKeyVaultProvider) getToken(ctx context.Context) (accessToken, error) {
	p.mu.Lock()
	defer p.mu.Unlock()

	if p.token.Value != "" && time.Until(p.token.Expiry) > time.Minute {
		return p.token, nil
	}

	token, err := p.tokenProvider.Token(ctx, azureScopeDefault)
	if err != nil {
		return accessToken{}, fmt.Errorf("failed to fetch Azure access token: %w", err)
	}
	p.token = token
	return token, nil
}

// azureClientCredentialsProvider implements token retrieval via the OAuth2 client credentials flow.
type azureClientCredentialsProvider struct {
	tenantID     string
	clientID     string
	clientSecret string
	httpClient   httpClient
	tokenURL     string
	scope        string
}

func (p *azureClientCredentialsProvider) Token(ctx context.Context, scope string) (accessToken, error) {
	values := url.Values{}
	values.Set("client_id", p.clientID)
	values.Set("client_secret", p.clientSecret)
	values.Set("scope", p.scope)
	if scope != "" && scope != p.scope {
		values.Set("scope", scope)
	}
	values.Set("grant_type", "client_credentials")

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, p.tokenURL, strings.NewReader(values.Encode()))
	if err != nil {
		return accessToken{}, fmt.Errorf("failed to create Azure token request: %w", err)
	}
	req.Header.Set("Content-Type", "application/x-www-form-urlencoded")

	client := p.httpClient
	if client == nil {
		client = defaultHTTPClient()
	}

	resp, err := client.Do(req)
	if err != nil {
		return accessToken{}, fmt.Errorf("failed to execute Azure token request: %w", err)
	}

	body, err := readResponseBody(resp)
	if err != nil {
		return accessToken{}, err
	}

	if resp.StatusCode < 200 || resp.StatusCode >= 300 {
		return accessToken{}, fmt.Errorf("azure token endpoint returned %d: %s", resp.StatusCode, string(body))
	}

	var tokenResp struct {
		AccessToken string `json:"access_token"`
		ExpiresIn   int64  `json:"expires_in"`
	}
	if err := json.Unmarshal(body, &tokenResp); err != nil {
		return accessToken{}, fmt.Errorf("failed to decode Azure token response: %w", err)
	}
	if tokenResp.AccessToken == "" {
		return accessToken{}, fmt.Errorf("azure token response missing access_token")
	}

	expiry := time.Now().Add(time.Duration(tokenResp.ExpiresIn) * time.Second)
	return accessToken{
		Value:  tokenResp.AccessToken,
		Expiry: expiry,
	}, nil
}
