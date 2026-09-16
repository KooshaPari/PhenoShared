package secrets

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

type staticTokenProvider struct {
	token accessToken
	err   error
	calls int32
}

func (s *staticTokenProvider) Token(ctx context.Context, scope string) (accessToken, error) {
	atomic.AddInt32(&s.calls, 1)
	if s.err != nil {
		return accessToken{}, s.err
	}
	return s.token, nil
}

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(req *http.Request) (*http.Response, error) {
	return f(req)
}

func newMockHTTPClient(handler roundTripFunc) *http.Client {
	return &http.Client{Transport: handler}
}

func jsonResponse(status int, payload any) *http.Response {
	data, _ := json.Marshal(payload)
	return &http.Response{
		StatusCode: status,
		Body:       io.NopCloser(bytes.NewReader(data)),
		Header:     make(http.Header),
	}
}

func TestAzureKeyVaultProvider_BasicOperations(t *testing.T) {
	ctx := context.Background()
	secrets := map[string]string{}

	mockTransport := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		if auth := req.Header.Get("Authorization"); !strings.HasPrefix(auth, "Bearer test-token") {
			return jsonResponse(http.StatusUnauthorized, map[string]any{"error": "unauthorized"}), nil
		}

		switch {
		case req.Method == http.MethodPut && strings.Contains(req.URL.Path, "/secrets/"):
			var payload map[string]string
			require.NoError(t, json.NewDecoder(req.Body).Decode(&payload))
			name := strings.TrimPrefix(req.URL.Path, "/secrets/")
			secrets[name] = payload["value"]
			return jsonResponse(http.StatusOK, map[string]string{"value": payload["value"]}), nil

		case req.Method == http.MethodGet && strings.HasPrefix(req.URL.Path, "/secrets/") && req.URL.Query().Get("api-version") == azureAPIVersion:
			name := strings.TrimPrefix(req.URL.Path, "/secrets/")
			val, ok := secrets[name]
			if !ok {
				return jsonResponse(http.StatusNotFound, map[string]string{"error": "not found"}), nil
			}
			return jsonResponse(http.StatusOK, map[string]string{"value": val}), nil

		case req.Method == http.MethodDelete && strings.HasPrefix(req.URL.Path, "/secrets/"):
			name := strings.TrimPrefix(req.URL.Path, "/secrets/")
			delete(secrets, name)
			return jsonResponse(http.StatusOK, map[string]any{}), nil

		case req.Method == http.MethodGet && strings.HasPrefix(req.URL.Path, "/secrets"):
			var list []map[string]string
			for name := range secrets {
				list = append(list, map[string]string{"id": "https://vault.local/secrets/" + name})
			}
			return jsonResponse(http.StatusOK, map[string]any{"value": list}), nil

		default:
			return jsonResponse(http.StatusBadRequest, map[string]string{"error": "unexpected"}), nil
		}
	})

	provider, err := NewAzureKeyVaultProvider(
		"https://vault.local",
		mockTransport,
		&staticTokenProvider{
			token: accessToken{
				Value:  "test-token",
				Expiry: time.Now().Add(time.Hour),
			},
		},
	)
	require.NoError(t, err)

	require.NoError(t, provider.SetSecret(ctx, "my-secret", "value"))

	value, err := provider.GetSecret(ctx, "my-secret")
	require.NoError(t, err)
	assert.Equal(t, "value", value)

	items, err := provider.ListSecrets(ctx)
	require.NoError(t, err)
	assert.Contains(t, items, "my-secret")

	require.NoError(t, provider.DeleteSecret(ctx, "my-secret"))

	_, err = provider.GetSecret(ctx, "my-secret")
	assert.Error(t, err)
}

func TestAzureKeyVaultProvider_TokenCaching(t *testing.T) {
	ctx := context.Background()
	tokenProvider := &staticTokenProvider{
		token: accessToken{Value: "token-1", Expiry: time.Now().Add(time.Hour)},
	}

	client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		return jsonResponse(http.StatusOK, map[string]string{"value": "cached"}), nil
	})

	provider, err := NewAzureKeyVaultProvider("https://vault.local", client, tokenProvider)
	require.NoError(t, err)

	for i := 0; i < 3; i++ {
		_, err := provider.GetSecret(ctx, "cached")
		require.NoError(t, err)
	}

	assert.Equal(t, int32(1), tokenProvider.calls)
}

func TestAzureClientCredentialsProvider(t *testing.T) {
	client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		require.NoError(t, req.ParseForm())
		require.Equal(t, "test-client", req.FormValue("client_id"))
		require.Equal(t, "test-secret", req.FormValue("client_secret"))
		require.Equal(t, "client_credentials", req.FormValue("grant_type"))
		return jsonResponse(http.StatusOK, map[string]any{
			"access_token": "fetched-token",
			"expires_in":   3600,
		}), nil
	})

	cred := &azureClientCredentialsProvider{
		clientID:     "test-client",
		clientSecret: "test-secret",
		tokenURL:     "https://login.example/token",
		httpClient:   client,
		scope:        azureScopeDefault,
	}

	token, err := cred.Token(context.Background(), azureScopeDefault)
	require.NoError(t, err)
	assert.Equal(t, "fetched-token", token.Value)
}

func TestNewAzureKeyVaultProviderFromEnv(t *testing.T) {
	tokenClient := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		return jsonResponse(http.StatusOK, map[string]any{
			"access_token": "env-token",
			"expires_in":   3600,
		}), nil
	})

	t.Setenv("AZURE_KEY_VAULT_URL", "https://example.vault.azure.net")
	t.Setenv("AZURE_TENANT_ID", "tenant")
	t.Setenv("AZURE_CLIENT_ID", "client")
	t.Setenv("AZURE_CLIENT_SECRET", "secret")
	t.Setenv("AZURE_OAUTH_TOKEN_URL", "https://login.example/token")

	original := defaultHTTPClient
	defaultHTTPClient = func() *http.Client { return tokenClient }
	defer func() { defaultHTTPClient = original }()

	_, err := NewAzureKeyVaultProviderFromEnv()
	assert.NoError(t, err)
}

func TestNewAzureKeyVaultProviderValidation(t *testing.T) {
	t.Run("requires vault URL", func(t *testing.T) {
		_, err := NewAzureKeyVaultProvider("", nil, &staticTokenProvider{})
		assert.Error(t, err)
	})

	t.Run("requires token provider", func(t *testing.T) {
		_, err := NewAzureKeyVaultProvider("https://vault.local", nil, nil)
		assert.Error(t, err)
	})

	t.Run("trims trailing slash and defaults client", func(t *testing.T) {
		provider, err := NewAzureKeyVaultProvider("https://vault.local/", nil, &staticTokenProvider{
			token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)},
		})
		require.NoError(t, err)
		assert.Equal(t, "https://vault.local", provider.vaultURL)
		assert.NotNil(t, provider.httpClient)
	})

}

func TestNewAzureKeyVaultProviderFromEnvErrors(t *testing.T) {
	t.Run("missing vault url", func(t *testing.T) {
		t.Setenv("AZURE_KEY_VAULT_URL", "")
		_, err := NewAzureKeyVaultProviderFromEnv()
		assert.Error(t, err)
	})

	t.Run("missing client credentials", func(t *testing.T) {
		t.Setenv("AZURE_KEY_VAULT_URL", "https://vault.local")
		t.Setenv("AZURE_TENANT_ID", "")
		_, err := NewAzureKeyVaultProviderFromEnv()
		assert.Error(t, err)
	})

	t.Run("defaults token url when unset", func(t *testing.T) {
		t.Setenv("AZURE_KEY_VAULT_URL", "https://vault.local")
		t.Setenv("AZURE_TENANT_ID", "tenant")
		t.Setenv("AZURE_CLIENT_ID", "client")
		t.Setenv("AZURE_CLIENT_SECRET", "secret")
		t.Setenv("AZURE_OAUTH_TOKEN_URL", "")

		tokenClient := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusOK, map[string]any{
				"access_token": "env-token",
				"expires_in":   3600,
			}), nil
		})

		original := defaultHTTPClient
		defaultHTTPClient = func() *http.Client { return tokenClient }
		defer func() { defaultHTTPClient = original }()

		provider, err := NewAzureKeyVaultProviderFromEnv()
		require.NoError(t, err)

		cred, ok := provider.tokenProvider.(*azureClientCredentialsProvider)
		require.True(t, ok)
		assert.Equal(t, fmt.Sprintf(azureTokenURLTemplate, "tenant"), cred.tokenURL)
	})
}

func TestAzureKeyVaultProvider_GetSecretEdgeCases(t *testing.T) {
	tokenProvider := &staticTokenProvider{
		token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)},
	}

	t.Run("missing value returns error", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusOK, map[string]any{"value": nil}), nil
		})
		provider, err := NewAzureKeyVaultProvider("https://vault.local", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.GetSecret(context.Background(), "missing")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "has no value")
	})

	t.Run("invalid json", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return &http.Response{
				StatusCode: http.StatusOK,
				Body:       io.NopCloser(strings.NewReader("{invalid")),
				Header:     make(http.Header),
			}, nil
		})
		provider, err := NewAzureKeyVaultProvider("https://vault.local", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.GetSecret(context.Background(), "bad")
		assert.Error(t, err)
	})
}

func TestAzureKeyVaultProvider_MutationErrors(t *testing.T) {
	tokenProvider := &staticTokenProvider{
		token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)},
	}

	client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		return jsonResponse(http.StatusInternalServerError, map[string]string{"error": "whoops"}), nil
	})

	provider, err := NewAzureKeyVaultProvider("https://vault.local", client, tokenProvider)
	require.NoError(t, err)

	assert.Error(t, provider.SetSecret(context.Background(), "key", "value"))
	assert.Error(t, provider.DeleteSecret(context.Background(), "key"))
}

func TestAzureKeyVaultProvider_ListSecretsEdgeCases(t *testing.T) {
	tokenProvider := &staticTokenProvider{
		token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)},
	}

	t.Run("paginates through next links", func(t *testing.T) {
		var calls int
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			calls++
			if calls == 1 {
				return jsonResponse(http.StatusOK, map[string]any{
					"value":    []map[string]string{{"id": "https://vault.local/secrets/first/versions/1"}},
					"nextLink": "https://vault.local/secrets?api-version=" + azureAPIVersion + "&page=2",
				}), nil
			}
			return jsonResponse(http.StatusOK, map[string]any{
				"value": []map[string]string{{"id": "https://vault.local/secrets/second"}},
			}), nil
		})

		provider, err := NewAzureKeyVaultProvider("https://vault.local", client, tokenProvider)
		require.NoError(t, err)

		secrets, err := provider.ListSecrets(context.Background())
		require.NoError(t, err)
		assert.ElementsMatch(t, []string{"first", "second"}, secrets)
	})

	t.Run("invalid list payload", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return &http.Response{
				StatusCode: http.StatusOK,
				Body:       io.NopCloser(strings.NewReader("{bad json")),
				Header:     make(http.Header),
			}, nil
		})

		provider, err := NewAzureKeyVaultProvider("https://vault.local", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.ListSecrets(context.Background())
		assert.Error(t, err)
	})
}

func TestAzureKeyVaultProvider_doAzureRequestErrors(t *testing.T) {
	tokenProvider := &staticTokenProvider{
		token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)},
	}

	t.Run("http client failure", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return nil, fmt.Errorf("network down")
		})
		provider, err := NewAzureKeyVaultProvider("https://vault.local", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.doAzureRequest(context.Background(), http.MethodGet, ":", nil)
		assert.Error(t, err)
	})

	t.Run("non success status", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusBadGateway, map[string]string{"error": "bad"}), nil
		})
		provider, err := NewAzureKeyVaultProvider("https://vault.local", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.doAzureRequest(context.Background(), http.MethodGet, "https://vault.local", nil)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "failed with status")
	})

	t.Run("read body error", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return &http.Response{
				StatusCode: http.StatusOK,
				Body:       &errorReadCloser{err: errors.New("read failed")},
				Header:     make(http.Header),
			}, nil
		})
		provider, err := NewAzureKeyVaultProvider("https://vault.local", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.doAzureRequest(context.Background(), http.MethodGet, "https://vault.local", nil)
		assert.Error(t, err)
	})

	t.Run("token fetch error", func(t *testing.T) {
		provider, err := NewAzureKeyVaultProvider("https://vault.local", newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusOK, map[string]any{}), nil
		}), &staticTokenProvider{err: fmt.Errorf("boom")})
		require.NoError(t, err)

		_, err = provider.doAzureRequest(context.Background(), http.MethodGet, "https://vault.local", nil)
		assert.Error(t, err)
	})

	t.Run("non-success with unreadable body", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return &http.Response{
				StatusCode: http.StatusBadGateway,
				Body:       &errorReadCloser{err: errors.New("boom")},
				Header:     make(http.Header),
			}, nil
		})
		provider, err := NewAzureKeyVaultProvider("https://vault.local", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.doAzureRequest(context.Background(), http.MethodGet, "https://vault.local", nil)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "unreadable body")
	})
}

func TestAzureKeyVaultProvider_SetSecretMarshalError(t *testing.T) {
	original := jsonMarshal
	jsonMarshal = func(v interface{}) ([]byte, error) {
		return nil, fmt.Errorf("marshal failure")
	}
	defer func() { jsonMarshal = original }()

	provider, err := NewAzureKeyVaultProvider("https://vault.local", newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		return jsonResponse(http.StatusOK, map[string]any{}), nil
	}), &staticTokenProvider{
		token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)},
	})
	require.NoError(t, err)

	err = provider.SetSecret(context.Background(), "key", "value")
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "marshal")
}

func TestAzureKeyVaultProvider_ListSecretsSkipsEmptyID(t *testing.T) {
	tokenProvider := &staticTokenProvider{
		token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)},
	}

	client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		return jsonResponse(http.StatusOK, map[string]any{
			"value": []map[string]string{
				{"id": ""},
				{"id": "https://vault.local/secrets/valid"},
			},
		}), nil
	})

	provider, err := NewAzureKeyVaultProvider("https://vault.local", client, tokenProvider)
	require.NoError(t, err)

	secrets, err := provider.ListSecrets(context.Background())
	require.NoError(t, err)
	assert.Equal(t, []string{"valid"}, secrets)
}

func TestAzureClientCredentialsProvider_DefaultHTTPClient(t *testing.T) {
	original := defaultHTTPClient
	defer func() { defaultHTTPClient = original }()

	called := false
	defaultHTTPClient = func() *http.Client {
		called = true
		return newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusOK, map[string]any{
				"access_token": "token",
				"expires_in":   120,
			}), nil
		})
	}

	cred := &azureClientCredentialsProvider{
		clientID:     "client",
		clientSecret: "secret",
		tokenURL:     "https://login.example/token",
		scope:        azureScopeDefault,
	}

	token, err := cred.Token(context.Background(), "")
	require.NoError(t, err)
	assert.Equal(t, "token", token.Value)
	assert.True(t, called)
}

func TestAzureClientCredentialsProvider_EdgeCases(t *testing.T) {
	t.Run("scope override", func(t *testing.T) {
		var scopes []string
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			if err := req.ParseForm(); err == nil {
				scopes = append(scopes, req.FormValue("scope"))
			}
			return jsonResponse(http.StatusOK, map[string]any{
				"access_token": "token",
				"expires_in":   3600,
			}), nil
		})

		cred := &azureClientCredentialsProvider{
			clientID:     "client",
			clientSecret: "secret",
			tokenURL:     "https://login",
			httpClient:   client,
			scope:        azureScopeDefault,
		}

		_, err := cred.Token(context.Background(), "custom-scope")
		require.NoError(t, err)
		require.Len(t, scopes, 1)
		assert.Equal(t, "custom-scope", scopes[0])
	})

	t.Run("http error", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return nil, fmt.Errorf("network error")
		})

		cred := &azureClientCredentialsProvider{
			clientID:     "client",
			clientSecret: "secret",
			tokenURL:     "https://login",
			httpClient:   client,
			scope:        azureScopeDefault,
		}

		_, err := cred.Token(context.Background(), azureScopeDefault)
		assert.Error(t, err)
	})

	t.Run("non-success status", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusBadRequest, map[string]string{"error": "bad request"}), nil
		})

		cred := &azureClientCredentialsProvider{
			clientID:     "client",
			clientSecret: "secret",
			tokenURL:     "https://login",
			httpClient:   client,
			scope:        azureScopeDefault,
		}

		_, err := cred.Token(context.Background(), azureScopeDefault)
		assert.Error(t, err)
	})

	t.Run("invalid json", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return &http.Response{
				StatusCode: http.StatusOK,
				Body:       io.NopCloser(strings.NewReader("{bad json")),
				Header:     make(http.Header),
			}, nil
		})

		cred := &azureClientCredentialsProvider{
			clientID:     "client",
			clientSecret: "secret",
			tokenURL:     "https://login",
			httpClient:   client,
			scope:        azureScopeDefault,
		}

		_, err := cred.Token(context.Background(), azureScopeDefault)
		assert.Error(t, err)
	})

	t.Run("missing access token", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusOK, map[string]any{"expires_in": 3600}), nil
		})

		cred := &azureClientCredentialsProvider{
			clientID:     "client",
			clientSecret: "secret",
			tokenURL:     "https://login",
			httpClient:   client,
			scope:        azureScopeDefault,
		}

		_, err := cred.Token(context.Background(), azureScopeDefault)
		assert.Error(t, err)
	})
}
