package secrets

import (
	"bytes"
	"context"
	"crypto/ecdsa"
	"crypto/elliptic"
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"encoding/pem"
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

func TestGoogleSecretManagerProvider_BasicOperations(t *testing.T) {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)

	keyBytes, err := x509.MarshalPKCS8PrivateKey(key)
	require.NoError(t, err)

	var pemBuf bytes.Buffer
	require.NoError(t, pem.Encode(&pemBuf, &pem.Block{Type: "PRIVATE KEY", Bytes: keyBytes}))

	projectID := "test-project"
	secretsStore := map[string]string{}
	var tokenRequests int32

	secretClient := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		switch {
		case req.Method == http.MethodGet && strings.HasSuffix(req.URL.Path, "/secrets"):
			var list []map[string]string
			for name := range secretsStore {
				list = append(list, map[string]string{
					"name": "projects/" + projectID + "/secrets/" + name,
				})
			}
			return jsonResponse(http.StatusOK, map[string]any{"secrets": list}), nil

		case req.Method == http.MethodGet && strings.Contains(req.URL.Path, "/secrets/") && strings.HasSuffix(req.URL.Path, ":access"):
			name := extractSecretName(req.URL.Path)
			val, ok := secretsStore[name]
			if !ok {
				return jsonResponse(http.StatusNotFound, map[string]string{"error": "not found"}), nil
			}
			payload := map[string]any{
				"payload": map[string]string{
					"data": base64.StdEncoding.EncodeToString([]byte(val)),
				},
			}
			return jsonResponse(http.StatusOK, payload), nil

		case req.Method == http.MethodGet && strings.Contains(req.URL.Path, "/secrets/"):
			name := extractSecretName(req.URL.Path)
			if _, ok := secretsStore[name]; !ok {
				return jsonResponse(http.StatusNotFound, map[string]string{"error": "not found"}), nil
			}
			return jsonResponse(http.StatusOK, map[string]any{}), nil

		case req.Method == http.MethodPost && strings.HasSuffix(req.URL.Path, ":addVersion"):
			var payload struct {
				Payload struct {
					Data string `json:"data"`
				} `json:"payload"`
			}
			require.NoError(t, json.NewDecoder(req.Body).Decode(&payload))
			name := extractSecretName(strings.TrimSuffix(req.URL.Path, ":addVersion"))
			decoded, err := base64.StdEncoding.DecodeString(payload.Payload.Data)
			require.NoError(t, err)
			secretsStore[name] = string(decoded)
			return jsonResponse(http.StatusOK, map[string]any{}), nil

		case req.Method == http.MethodPost && strings.HasSuffix(req.URL.Path, "/secrets"):
			return jsonResponse(http.StatusOK, map[string]any{}), nil

		case req.Method == http.MethodDelete && strings.Contains(req.URL.Path, "/secrets/"):
			name := extractSecretName(req.URL.Path)
			delete(secretsStore, name)
			return jsonResponse(http.StatusOK, map[string]any{}), nil
		}

		return jsonResponse(http.StatusBadRequest, map[string]string{"error": "unexpected"}), nil
	})

	tokenClient := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		atomic.AddInt32(&tokenRequests, 1)
		return jsonResponse(http.StatusOK, map[string]any{
			"access_token": "gcp-token",
			"expires_in":   3600,
		}), nil
	})

	serviceAccount := map[string]string{
		"client_email": "svc@test-project.iam.gserviceaccount.com",
		"private_key":  pemBuf.String(),
		"token_uri":    "https://oauth2.googleapis.com/token",
	}
	saJSON, err := json.Marshal(serviceAccount)
	require.NoError(t, err)

	tokenProvider, err := newGoogleServiceAccountTokenProvider(string(saJSON), gcpDefaultScope)
	require.NoError(t, err)
	tokenProvider.httpClient = tokenClient

	provider, err := NewGoogleSecretManagerProvider(projectID, secretClient, tokenProvider)
	require.NoError(t, err)

	// Override base URL to match our mock client expectations.
	provider.baseURL = "https://secretmanager.googleapis.com/v1"

	ctx := context.Background()

	require.NoError(t, provider.SetSecret(ctx, "my-secret", "value"))

	val, err := provider.GetSecret(ctx, "my-secret")
	require.NoError(t, err)
	assert.Equal(t, "value", val)

	list, err := provider.ListSecrets(ctx)
	require.NoError(t, err)
	assert.Contains(t, list, "my-secret")

	require.NoError(t, provider.DeleteSecret(ctx, "my-secret"))

	_, err = provider.GetSecret(ctx, "my-secret")
	assert.Error(t, err)

	assert.GreaterOrEqual(t, atomic.LoadInt32(&tokenRequests), int32(1))
}

func TestGoogleServiceAccountTokenProvider(t *testing.T) {
	key, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)

	keyBytes, err := x509.MarshalPKCS8PrivateKey(key)
	require.NoError(t, err)

	var pemBuf bytes.Buffer
	require.NoError(t, pem.Encode(&pemBuf, &pem.Block{Type: "PRIVATE KEY", Bytes: keyBytes}))

	tokenCalls := int32(0)
	client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		atomic.AddInt32(&tokenCalls, 1)
		return jsonResponse(http.StatusOK, map[string]any{
			"access_token": "sa-token",
			"expires_in":   3600,
		}), nil
	})

	serviceAccount := map[string]string{
		"client_email": "svc@example.com",
		"private_key":  pemBuf.String(),
		"token_uri":    "https://oauth2.googleapis.com/token",
	}

	data, err := json.Marshal(serviceAccount)
	require.NoError(t, err)

	provider, err := newGoogleServiceAccountTokenProvider(string(data), gcpDefaultScope)
	require.NoError(t, err)
	provider.httpClient = client

	token, err := provider.Token(context.Background(), gcpDefaultScope)
	require.NoError(t, err)
	assert.Equal(t, "sa-token", token.Value)
	assert.True(t, token.Expiry.After(time.Now()))
	assert.Equal(t, int32(1), atomic.LoadInt32(&tokenCalls))
}

func extractSecretName(path string) string {
	parts := strings.Split(path, "/secrets/")
	if len(parts) != 2 {
		return ""
	}
	name := parts[1]
	name = strings.TrimPrefix(name, "projects/")
	name = strings.TrimPrefix(name, "test-project/")
	if idx := strings.Index(name, "/"); idx != -1 {
		name = name[:idx]
	}
	name = strings.TrimSuffix(name, ":access")
	name = strings.TrimSuffix(name, ":addVersion")
	return strings.Trim(name, "/")
}

func TestNewGoogleSecretManagerProviderValidation(t *testing.T) {
	t.Run("requires project id", func(t *testing.T) {
		_, err := NewGoogleSecretManagerProvider("", nil, &staticTokenProvider{})
		assert.Error(t, err)
	})

	t.Run("requires token provider", func(t *testing.T) {
		_, err := NewGoogleSecretManagerProvider("project", nil, nil)
		assert.Error(t, err)
	})

	t.Run("defaults http client", func(t *testing.T) {
		provider, err := NewGoogleSecretManagerProvider("project", nil, &staticTokenProvider{
			token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)},
		})
		require.NoError(t, err)
		assert.NotNil(t, provider.httpClient)
	})
}

func TestNewGoogleSecretManagerProviderFromEnvErrors(t *testing.T) {
	t.Run("missing project id", func(t *testing.T) {
		t.Setenv("GCP_PROJECT_ID", "")
		_, err := NewGoogleSecretManagerProviderFromEnv()
		assert.Error(t, err)
	})

	t.Run("missing service account json", func(t *testing.T) {
		t.Setenv("GCP_PROJECT_ID", "project")
		t.Setenv(serviceAccountJSONEnv, "")
		_, err := NewGoogleSecretManagerProviderFromEnv()
		assert.Error(t, err)
	})

	t.Run("invalid service account json", func(t *testing.T) {
		t.Setenv("GCP_PROJECT_ID", "project")
		t.Setenv(serviceAccountJSONEnv, "{bad json")
		_, err := NewGoogleSecretManagerProviderFromEnv()
		assert.Error(t, err)
	})

	t.Run("missing required fields", func(t *testing.T) {
		t.Setenv("GCP_PROJECT_ID", "project")
		t.Setenv(serviceAccountJSONEnv, `{"client_email":"a"}`)
		_, err := NewGoogleSecretManagerProviderFromEnv()
		assert.Error(t, err)
	})
}

func TestNewGoogleSecretManagerProviderFromEnvCustomScope(t *testing.T) {
	saJSON, _ := generateServiceAccountJSON(t)

	t.Setenv("GCP_PROJECT_ID", "project")
	t.Setenv(serviceAccountJSONEnv, saJSON)
	t.Setenv(serviceAccountScopeEnv, "custom-scope")

	provider, err := NewGoogleSecretManagerProviderFromEnv()
	require.NoError(t, err)

	cred, ok := provider.tokenProvider.(*googleServiceAccountTokenProvider)
	require.True(t, ok)
	assert.Equal(t, "custom-scope", cred.scope)
}

func TestGoogleSecretManagerProvider_GetSecretEdgeCases(t *testing.T) {
	tokenProvider := &staticTokenProvider{token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)}}

	t.Run("missing payload", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusOK, map[string]any{
				"payload": map[string]string{"data": ""},
			}), nil
		})
		provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.GetSecret(context.Background(), "key")
		assert.Error(t, err)
	})

	t.Run("invalid base64 payload", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusOK, map[string]any{
				"payload": map[string]string{"data": "%%%"},
			}), nil
		})
		provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.GetSecret(context.Background(), "key")
		assert.Error(t, err)
	})

	t.Run("invalid json response", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return &http.Response{
				StatusCode: http.StatusOK,
				Body:       io.NopCloser(strings.NewReader("{bad json")),
				Header:     make(http.Header),
			}, nil
		})
		provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.GetSecret(context.Background(), "key")
		assert.Error(t, err)
	})
}

func TestGoogleSecretManagerProvider_SetSecretEdgeCases(t *testing.T) {
	tokenProvider := &staticTokenProvider{token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)}}

	t.Run("ensure secret exists propagates non not found error", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusInternalServerError, map[string]string{"error": "boom"}), nil
		})
		provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
		require.NoError(t, err)

		err = provider.SetSecret(context.Background(), "key", "value")
		assert.Error(t, err)
	})
}

func TestGoogleSecretManagerProvider_SetSecretMarshalErrors(t *testing.T) {
	tokenProvider := &staticTokenProvider{token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)}}
	original := jsonMarshal
	jsonMarshal = func(v interface{}) ([]byte, error) {
		if _, ok := v.(map[string]map[string]string); ok {
			return nil, fmt.Errorf("marshal failure")
		}
		return original(v)
	}
	defer func() { jsonMarshal = original }()

	provider, err := NewGoogleSecretManagerProvider("project", newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		return jsonResponse(http.StatusOK, map[string]any{}), nil
	}), tokenProvider)
	require.NoError(t, err)

	err = provider.SetSecret(context.Background(), "key", "value")
	assert.Error(t, err)
}

func TestGoogleSecretManagerProvider_SetSecretWithoutCreate(t *testing.T) {
	tokenProvider := &staticTokenProvider{token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)}}

	client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		switch {
		case req.Method == http.MethodGet && strings.Contains(req.URL.Path, "/secrets/"):
			return jsonResponse(http.StatusOK, map[string]any{}), nil
		case req.Method == http.MethodPost && strings.HasSuffix(req.URL.Path, ":addVersion"):
			return jsonResponse(http.StatusOK, map[string]any{}), nil
		default:
			return jsonResponse(http.StatusOK, map[string]any{}), nil
		}
	})

	provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
	require.NoError(t, err)

	err = provider.SetSecret(context.Background(), "key", "value")
	assert.NoError(t, err)
}

func TestGoogleSecretManagerProvider_DeleteSecretError(t *testing.T) {
	tokenProvider := &staticTokenProvider{token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)}}

	client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		return jsonResponse(http.StatusInternalServerError, map[string]string{"error": "boom"}), nil
	})

	provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
	require.NoError(t, err)

	err = provider.DeleteSecret(context.Background(), "key")
	assert.Error(t, err)
}

func TestGoogleSecretManagerProvider_ListSecretsSkipsInvalid(t *testing.T) {
	tokenProvider := &staticTokenProvider{token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)}}

	client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		return jsonResponse(http.StatusOK, map[string]any{
			"secrets": []map[string]string{
				{"name": "projects/project/other"},
				{"name": "projects/project/secrets/valid"},
			},
		}), nil
	})

	provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
	require.NoError(t, err)

	secrets, err := provider.ListSecrets(context.Background())
	require.NoError(t, err)
	assert.Equal(t, []string{"valid"}, secrets)
}

func TestGoogleSecretManagerProvider_EnsureSecretExistsCreateError(t *testing.T) {
	tokenProvider := &staticTokenProvider{token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)}}

	client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		switch {
		case req.Method == http.MethodGet && strings.Contains(req.URL.Path, "/secrets/"):
			return jsonResponse(http.StatusNotFound, map[string]string{"error": "not found"}), nil
		case req.Method == http.MethodPost && strings.Contains(req.URL.Path, "/secrets") && req.URL.Query().Get("secretId") != "":
			return jsonResponse(http.StatusInternalServerError, map[string]string{"error": "boom"}), nil
		default:
			return jsonResponse(http.StatusOK, map[string]any{}), nil
		}
	})

	provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
	require.NoError(t, err)

	err = provider.ensureSecretExists(context.Background(), "key")
	assert.Error(t, err)
}

func TestGoogleSecretManagerProvider_EnsureSecretExistsMarshalError(t *testing.T) {
	tokenProvider := &staticTokenProvider{token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)}}
	original := jsonMarshal
	jsonMarshal = func(v interface{}) ([]byte, error) {
		if _, ok := v.(map[string]any); ok {
			return nil, fmt.Errorf("marshal failure")
		}
		return original(v)
	}
	defer func() { jsonMarshal = original }()

	client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		return jsonResponse(http.StatusNotFound, map[string]string{"error": "not found"}), nil
	})

	provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
	require.NoError(t, err)

	err = provider.ensureSecretExists(context.Background(), "key")
	assert.Error(t, err)
}

func TestGoogleSecretManagerProvider_ListSecretsInvalidJSON(t *testing.T) {
	tokenProvider := &staticTokenProvider{token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)}}
	client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		return &http.Response{
			StatusCode: http.StatusOK,
			Body:       io.NopCloser(strings.NewReader("{bad json")),
			Header:     make(http.Header),
		}, nil
	})

	provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
	require.NoError(t, err)

	_, err = provider.ListSecrets(context.Background())
	assert.Error(t, err)
}

func TestGoogleSecretManagerProvider_doGoogleRequestErrors(t *testing.T) {
	tokenProvider := &staticTokenProvider{token: accessToken{Value: "tok", Expiry: time.Now().Add(time.Hour)}}

	t.Run("http client error", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return nil, fmt.Errorf("network down")
		})
		provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.doGoogleRequest(context.Background(), http.MethodGet, "://bad", nil)
		assert.Error(t, err)
	})

	t.Run("not found error", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusNotFound, map[string]string{"error": "missing"}), nil
		})
		provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.doGoogleRequest(context.Background(), http.MethodGet, "https://host", nil)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "not found")
	})

	t.Run("non-success status", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusBadGateway, map[string]string{"error": "boom"}), nil
		})
		provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.doGoogleRequest(context.Background(), http.MethodGet, "https://host", nil)
		assert.Error(t, err)
	})

	t.Run("read body error", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return &http.Response{
				StatusCode: http.StatusOK,
				Body:       &errorReadCloser{err: errors.New("read failed")},
				Header:     make(http.Header),
			}, nil
		})
		provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.doGoogleRequest(context.Background(), http.MethodGet, "https://host", nil)
		assert.Error(t, err)
	})

	t.Run("request creation failure", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusOK, map[string]any{}), nil
		})
		provider, err := NewGoogleSecretManagerProvider("project", client, tokenProvider)
		require.NoError(t, err)

		_, err = provider.doGoogleRequest(context.Background(), http.MethodGet, ":", nil)
		assert.Error(t, err)
	})
}

func TestGoogleSecretManagerProvider_getTokenError(t *testing.T) {
	client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
		return jsonResponse(http.StatusOK, map[string]string{}), nil
	})

	provider, err := NewGoogleSecretManagerProvider("project", client, &staticTokenProvider{err: fmt.Errorf("token fail")})
	require.NoError(t, err)

	_, err = provider.ListSecrets(context.Background())
	assert.Error(t, err)
}

func TestNewGoogleServiceAccountTokenProviderErrors(t *testing.T) {
	t.Run("invalid json", func(t *testing.T) {
		_, err := newGoogleServiceAccountTokenProvider("{bad json", gcpDefaultScope)
		assert.Error(t, err)
	})

	t.Run("missing fields", func(t *testing.T) {
		_, err := newGoogleServiceAccountTokenProvider(`{"client_email":"a"}`, gcpDefaultScope)
		assert.Error(t, err)
	})

	t.Run("invalid key encoding", func(t *testing.T) {
		data := map[string]string{
			"client_email": "svc@test",
			"private_key":  "-----BEGIN PRIVATE KEY-----\ninvalid\n-----END PRIVATE KEY-----",
			"token_uri":    "https://token",
		}
		payload, _ := json.Marshal(data)
		_, err := newGoogleServiceAccountTokenProvider(string(payload), gcpDefaultScope)
		assert.Error(t, err)
	})
}

func generateServiceAccountJSON(t *testing.T) (string, *rsa.PrivateKey) {
	t.Helper()

	key, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)
	keyBytes, err := x509.MarshalPKCS8PrivateKey(key)
	require.NoError(t, err)

	var buf bytes.Buffer
	require.NoError(t, pem.Encode(&buf, &pem.Block{Type: "PRIVATE KEY", Bytes: keyBytes}))

	data := map[string]string{
		"client_email": "svc@example.com",
		"private_key":  buf.String(),
		"token_uri":    "https://oauth.example/token",
	}
	payload, err := json.Marshal(data)
	require.NoError(t, err)
	return string(payload), key
}

func TestGoogleServiceAccountTokenProvider_EdgeCases(t *testing.T) {
	saJSON, _ := generateServiceAccountJSON(t)

	t.Run("scope override", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			require.NoError(t, req.ParseForm())
			assert.Equal(t, "urn:ietf:params:oauth:grant-type:jwt-bearer", req.FormValue("grant_type"))
			assert.NotEmpty(t, req.FormValue("assertion"))
			return jsonResponse(http.StatusOK, map[string]any{"access_token": "tok", "expires_in": 120}), nil
		})

		provider, err := newGoogleServiceAccountTokenProvider(saJSON, "")
		require.NoError(t, err)
		provider.httpClient = client

		token, err := provider.Token(context.Background(), "custom-scope")
		require.NoError(t, err)
		assert.Equal(t, "tok", token.Value)
	})

	t.Run("default http client fallback", func(t *testing.T) {
		original := defaultHTTPClient
		defer func() { defaultHTTPClient = original }()

		called := false
		defaultHTTPClient = func() *http.Client {
			called = true
			return newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
				return jsonResponse(http.StatusOK, map[string]any{"access_token": "tok", "expires_in": 60}), nil
			})
		}

		provider, err := newGoogleServiceAccountTokenProvider(saJSON, gcpDefaultScope)
		require.NoError(t, err)
		provider.httpClient = nil

		token, err := provider.Token(context.Background(), "")
		require.NoError(t, err)
		assert.Equal(t, "tok", token.Value)
		assert.True(t, called)
	})

	t.Run("marshal failure", func(t *testing.T) {
		originalMarshal := jsonMarshal
		jsonMarshal = func(v interface{}) ([]byte, error) {
			if _, ok := v.(map[string]any); ok {
				return nil, fmt.Errorf("marshal failure")
			}
			return originalMarshal(v)
		}
		defer func() { jsonMarshal = originalMarshal }()

		provider, err := newGoogleServiceAccountTokenProvider(saJSON, gcpDefaultScope)
		require.NoError(t, err)
		provider.httpClient = newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusOK, map[string]any{"access_token": "tok", "expires_in": 60}), nil
		})

		_, err = provider.Token(context.Background(), "")
		assert.Error(t, err)
	})

	t.Run("http error", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return nil, fmt.Errorf("network")
		})
		provider, err := newGoogleServiceAccountTokenProvider(saJSON, gcpDefaultScope)
		require.NoError(t, err)
		provider.httpClient = client

		_, err = provider.Token(context.Background(), "")
		assert.Error(t, err)
	})

	t.Run("non-success status", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusBadRequest, map[string]string{"error": "bad"}), nil
		})
		provider, err := newGoogleServiceAccountTokenProvider(saJSON, gcpDefaultScope)
		require.NoError(t, err)
		provider.httpClient = client

		_, err = provider.Token(context.Background(), "")
		assert.Error(t, err)
	})

	t.Run("invalid json response", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return &http.Response{
				StatusCode: http.StatusOK,
				Body:       io.NopCloser(strings.NewReader("{bad json")),
				Header:     make(http.Header),
			}, nil
		})
		provider, err := newGoogleServiceAccountTokenProvider(saJSON, gcpDefaultScope)
		require.NoError(t, err)
		provider.httpClient = client

		_, err = provider.Token(context.Background(), "")
		assert.Error(t, err)
	})

	t.Run("missing access token", func(t *testing.T) {
		client := newMockHTTPClient(func(req *http.Request) (*http.Response, error) {
			return jsonResponse(http.StatusOK, map[string]any{"expires_in": 60}), nil
		})
		provider, err := newGoogleServiceAccountTokenProvider(saJSON, gcpDefaultScope)
		require.NoError(t, err)
		provider.httpClient = client

		_, err = provider.Token(context.Background(), "")
		assert.Error(t, err)
	})
}

func TestParsePrivateKey(t *testing.T) {
	rsaKey, err := rsa.GenerateKey(rand.Reader, 2048)
	require.NoError(t, err)

	t.Run("pkcs1 key", func(t *testing.T) {
		der := x509.MarshalPKCS1PrivateKey(rsaKey)
		key, err := parsePrivateKey(der)
		require.NoError(t, err)
		assert.NotNil(t, key)
	})

	t.Run("pkcs8 key", func(t *testing.T) {
		der, err := x509.MarshalPKCS8PrivateKey(rsaKey)
		require.NoError(t, err)
		key, err := parsePrivateKey(der)
		require.NoError(t, err)
		assert.NotNil(t, key)
	})

	t.Run("pkcs8 non-rsa", func(t *testing.T) {
		ecdsaKey, err := ecdsa.GenerateKey(elliptic.P256(), rand.Reader)
		require.NoError(t, err)
		der, err := x509.MarshalPKCS8PrivateKey(ecdsaKey)
		require.NoError(t, err)
		_, err = parsePrivateKey(der)
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "not RSA")
	})

	t.Run("unsupported format", func(t *testing.T) {
		_, err := parsePrivateKey([]byte("not a key"))
		assert.Error(t, err)
	})
}

func TestIsNotFoundError(t *testing.T) {
	assert.False(t, isNotFoundError(nil))
	assert.False(t, isNotFoundError(fmt.Errorf("something else")))
	assert.True(t, isNotFoundError(fmt.Errorf("Not Found")))
}
