package clients

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

type roundTripFunc func(*http.Request) (*http.Response, error)

func (f roundTripFunc) RoundTrip(req *http.Request) (*http.Response, error) {
	return f(req)
}

func newHTTPResponse(status int, body string) *http.Response {
	return &http.Response{
		StatusCode: status,
		Body:       io.NopCloser(bytes.NewBufferString(body)),
		Header:     make(http.Header),
	}
}

func TestNewCredentialValidator(t *testing.T) {
	t.Run("creates new validator with default HTTP client", func(t *testing.T) {
		validator := NewCredentialValidator()
		assert.NotNil(t, validator)
		assert.NotNil(t, validator.httpClient)
	})
}

// ---------------------------------------------------------------------------
// ValidateLLMCredentials
// ---------------------------------------------------------------------------

func TestCredentialValidator_ValidateLLMCredentials(t *testing.T) {
	ctx := context.Background()

	newValidator := func(handler roundTripFunc) *CredentialValidator {
		return NewCredentialValidator(WithHTTPClient(&http.Client{Transport: handler}))
	}

	t.Run("fails with empty base URL", func(t *testing.T) {
		validator := NewCredentialValidator()
		err := validator.ValidateLLMCredentials(ctx, "", "")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "LLM base URL is required")
	})

	t.Run("succeeds when server returns 200 on /v1/models", func(t *testing.T) {
		validator := newValidator(func(req *http.Request) (*http.Response, error) {
			assert.Equal(t, "/v1/models", req.URL.Path)
			return newHTTPResponse(http.StatusOK, `{"object":"list","data":[]}`), nil
		})
		err := validator.ValidateLLMCredentials(ctx, "http://localhost:8000", "")
		assert.NoError(t, err)
	})

	t.Run("passes Authorization header when apiKey is set", func(t *testing.T) {
		validator := newValidator(func(req *http.Request) (*http.Response, error) {
			assert.Equal(t, "Bearer token123", req.Header.Get("Authorization"))
			return newHTTPResponse(http.StatusOK, `{}`), nil
		})
		err := validator.ValidateLLMCredentials(ctx, "http://localhost:8080", "token123")
		assert.NoError(t, err)
	})

	t.Run("fails when server is unreachable", func(t *testing.T) {
		validator := newValidator(func(_ *http.Request) (*http.Response, error) {
			return nil, fmt.Errorf("connection refused")
		})
		err := validator.ValidateLLMCredentials(ctx, "http://localhost:8000", "")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "LLM server unreachable")
	})

	t.Run("fails when server returns non-2xx", func(t *testing.T) {
		validator := newValidator(func(_ *http.Request) (*http.Response, error) {
			return newHTTPResponse(http.StatusServiceUnavailable, `{"error":"loading"}`), nil
		})
		err := validator.ValidateLLMCredentials(ctx, "http://localhost:8000", "")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "503")
	})
}

// ---------------------------------------------------------------------------
// LLMChat
// ---------------------------------------------------------------------------

func TestCredentialValidator_LLMChat(t *testing.T) {
	ctx := context.Background()

	newValidator := func(handler roundTripFunc) *CredentialValidator {
		return NewCredentialValidator(WithHTTPClient(&http.Client{Transport: handler}))
	}

	t.Run("sends correct chat completions request", func(t *testing.T) {
		validator := newValidator(func(req *http.Request) (*http.Response, error) {
			assert.Equal(t, "/v1/chat/completions", req.URL.Path)
			assert.Equal(t, "application/json", req.Header.Get("Content-Type"))

			var chatReq LLMChatRequest
			err := json.NewDecoder(req.Body).Decode(&chatReq)
			require.NoError(t, err)
			assert.Equal(t, "mistralai/Mistral-7B-v0.1", chatReq.Model)
			assert.Len(t, chatReq.Messages, 1)
			assert.Equal(t, "user", chatReq.Messages[0].Role)
			assert.Equal(t, "hello", chatReq.Messages[0].Content)

			body := `{"choices":[{"message":{"role":"assistant","content":"world"}}]}`
			return newHTTPResponse(http.StatusOK, body), nil
		})
		result, err := validator.LLMChat(ctx, "http://localhost:8000", "", "", "hello")
		require.NoError(t, err)
		assert.Equal(t, "world", result)
	})

	t.Run("uses default base URL when empty", func(t *testing.T) {
		validator := newValidator(func(req *http.Request) (*http.Response, error) {
			assert.Equal(t, "localhost:8000", req.URL.Host)
			body := `{"choices":[{"message":{"role":"assistant","content":"ok"}}]}`
			return newHTTPResponse(http.StatusOK, body), nil
		})
		_, err := validator.LLMChat(ctx, "", "", "", "ping")
		assert.NoError(t, err)
	})

	t.Run("sets Authorization header when apiKey is provided", func(t *testing.T) {
		validator := newValidator(func(req *http.Request) (*http.Response, error) {
			assert.Equal(t, "Bearer mytoken", req.Header.Get("Authorization"))
			body := `{"choices":[{"message":{"role":"assistant","content":"ok"}}]}`
			return newHTTPResponse(http.StatusOK, body), nil
		})
		_, err := validator.LLMChat(ctx, "http://localhost:8000", "model", "mytoken", "ping")
		assert.NoError(t, err)
	})

	t.Run("fails on non-200 response", func(t *testing.T) {
		validator := newValidator(func(_ *http.Request) (*http.Response, error) {
			return newHTTPResponse(http.StatusInternalServerError, `{"error":"oops"}`), nil
		})
		_, err := validator.LLMChat(ctx, "http://localhost:8000", "", "", "ping")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "500")
	})

	t.Run("fails when choices is empty", func(t *testing.T) {
		validator := newValidator(func(_ *http.Request) (*http.Response, error) {
			return newHTTPResponse(http.StatusOK, `{"choices":[]}`), nil
		})
		_, err := validator.LLMChat(ctx, "http://localhost:8000", "", "", "ping")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "empty response")
	})

	t.Run("fails on network error", func(t *testing.T) {
		validator := newValidator(func(_ *http.Request) (*http.Response, error) {
			return nil, fmt.Errorf("dial tcp: connection refused")
		})
		_, err := validator.LLMChat(ctx, "http://localhost:8000", "", "", "ping")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "LLM chat request failed")
	})
}

// ---------------------------------------------------------------------------
// ValidateAWSCredentials
// ---------------------------------------------------------------------------

func TestCredentialValidator_ValidateAWSCredentials(t *testing.T) {
	validator := NewCredentialValidator()
	ctx := context.Background()

	t.Run("fails with empty access key ID", func(t *testing.T) {
		err := validator.ValidateAWSCredentials(ctx, "", "secret", "us-east-1")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "AWS access key ID is required")
	})

	t.Run("fails with empty secret access key", func(t *testing.T) {
		err := validator.ValidateAWSCredentials(ctx, "access-key", "", "us-east-1")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "AWS secret access key is required")
	})

	t.Run("fails with invalid credentials when no real AWS env present", func(t *testing.T) {
		if os.Getenv("AWS_ACCESS_KEY_ID") != "" || os.Getenv("AWS_PROFILE") != "" {
			t.Skip("Skipping AWS validation test — real credentials present")
		}
		err := validator.ValidateAWSCredentials(ctx, "fake-access-key", "fake-secret-key", "us-east-1")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "invalid AWS credentials")
	})

	t.Run("uses default region when empty", func(t *testing.T) {
		if os.Getenv("AWS_ACCESS_KEY_ID") != "" || os.Getenv("AWS_PROFILE") != "" {
			t.Skip("Skipping AWS validation test — real credentials present")
		}
		err := validator.ValidateAWSCredentials(ctx, "fake-access-key", "fake-secret-key", "")
		assert.Error(t, err)
		// Should reach STS (default region applied) and fail on bad creds — not on missing region
		assert.Contains(t, err.Error(), "invalid AWS credentials")
	})
}

// ---------------------------------------------------------------------------
// GetAWSConfig
// ---------------------------------------------------------------------------

func TestCredentialValidator_GetAWSConfig(t *testing.T) {
	validator := NewCredentialValidator()
	ctx := context.Background()

	t.Run("creates AWS config successfully", func(t *testing.T) {
		cfg, err := validator.GetAWSConfig(ctx, "access-key", "secret-key", "us-west-2")
		require.NoError(t, err)
		assert.NotNil(t, cfg.Credentials)
	})

	t.Run("applies default region when empty", func(t *testing.T) {
		cfg, err := validator.GetAWSConfig(ctx, "access-key", "secret-key", "")
		require.NoError(t, err)
		assert.Equal(t, "us-east-1", cfg.Region)
	})
}

// ---------------------------------------------------------------------------
// ValidatePortfolioAPI
// ---------------------------------------------------------------------------

func TestCredentialValidator_ValidatePortfolioAPI(t *testing.T) {
	ctx := context.Background()

	newValidator := func(handler roundTripFunc) *CredentialValidator {
		return NewCredentialValidator(WithHTTPClient(&http.Client{Transport: handler}))
	}

	t.Run("fails with empty endpoint", func(t *testing.T) {
		validator := NewCredentialValidator()
		err := validator.ValidatePortfolioAPI(ctx, "", "api-key")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "Portfolio API endpoint is required")
	})

	t.Run("fails with empty API key", func(t *testing.T) {
		validator := NewCredentialValidator()
		err := validator.ValidatePortfolioAPI(ctx, "https://api.example.com", "")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "Portfolio API key is required")
	})

	t.Run("validates with successful response", func(t *testing.T) {
		validator := newValidator(func(req *http.Request) (*http.Response, error) {
			assert.Equal(t, "Bearer test-api-key", req.Header.Get("Authorization"))
			assert.Equal(t, "BytePort/1.0", req.Header.Get("User-Agent"))
			assert.Equal(t, "/byteport", req.URL.Path)
			return newHTTPResponse(http.StatusOK, `{"status":"success"}`), nil
		})
		err := validator.ValidatePortfolioAPI(ctx, "https://portfolio.example.com", "test-api-key")
		assert.NoError(t, err)
	})

	t.Run("fails with 401 response", func(t *testing.T) {
		validator := newValidator(func(_ *http.Request) (*http.Response, error) {
			return newHTTPResponse(http.StatusUnauthorized, `{"error":"invalid credentials"}`), nil
		})
		err := validator.ValidatePortfolioAPI(ctx, "https://portfolio.example.com", "invalid-key")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "invalid Portfolio API credentials, status: 401")
	})

	t.Run("fails with 500 response", func(t *testing.T) {
		validator := newValidator(func(_ *http.Request) (*http.Response, error) {
			return newHTTPResponse(http.StatusInternalServerError, `{"error":"server"}`), nil
		})
		err := validator.ValidatePortfolioAPI(ctx, "https://portfolio.example.com", "test-key")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "invalid Portfolio API credentials, status: 500")
	})

	t.Run("fails with network error", func(t *testing.T) {
		validator := newValidator(func(_ *http.Request) (*http.Response, error) {
			return nil, fmt.Errorf("dial tcp: connection refused")
		})
		err := validator.ValidatePortfolioAPI(ctx, "https://portfolio.example.com", "test-key")
		assert.Error(t, err)
		assert.Contains(t, err.Error(), "failed to connect to Portfolio API")
	})

	t.Run("fails with invalid URL", func(t *testing.T) {
		validator := NewCredentialValidator()
		err := validator.ValidatePortfolioAPI(ctx, "invalid-url", "test-key")
		assert.Error(t, err)
		assert.True(t,
			strings.Contains(err.Error(), "failed to create request") ||
				strings.Contains(err.Error(), "failed to connect to Portfolio API"),
		)
	})
}

// ---------------------------------------------------------------------------
// ValidateAllCredentials
// ---------------------------------------------------------------------------

func TestCredentialValidator_ValidateAllCredentials(t *testing.T) {
	ctx := context.Background()

	portfolioSuccessClient := &http.Client{Transport: roundTripFunc(func(req *http.Request) (*http.Response, error) {
		return newHTTPResponse(http.StatusOK, `{"status":"success"}`), nil
	})}

	validator := NewCredentialValidator(WithHTTPClient(portfolioSuccessClient))

	t.Run("skips empty credentials", func(t *testing.T) {
		creds := &AllCredentials{}
		results := validator.ValidateAllCredentials(ctx, creds)
		assert.Empty(t, results, "should not validate empty credentials")
	})

	t.Run("skips incomplete AWS credentials", func(t *testing.T) {
		creds := &AllCredentials{}
		creds.AWS.AccessKeyID = "access-key"
		// Missing SecretAccessKey
		creds.AWS.Region = "us-east-1"

		results := validator.ValidateAllCredentials(ctx, creds)
		assert.Empty(t, results, "should not validate incomplete AWS credentials")
	})

	t.Run("skips incomplete Portfolio credentials", func(t *testing.T) {
		creds := &AllCredentials{}
		creds.Portfolio.Endpoint = "https://api.example.com"
		// Missing APIKey

		results := validator.ValidateAllCredentials(ctx, creds)
		assert.Empty(t, results, "should not validate incomplete Portfolio credentials")
	})

	t.Run("validates portfolio credentials when provided", func(t *testing.T) {
		creds := &AllCredentials{}
		creds.Portfolio.Endpoint = "https://portfolio.example.com"
		creds.Portfolio.APIKey = "test-portfolio-key"

		results := validator.ValidateAllCredentials(ctx, creds)
		assert.Len(t, results, 1)
		assert.Equal(t, "portfolio", results[0].Service)
		assert.True(t, results[0].Valid)
	})
}

// ---------------------------------------------------------------------------
// formatError
// ---------------------------------------------------------------------------

func TestFormatError(t *testing.T) {
	t.Run("returns empty string for nil error", func(t *testing.T) {
		result := formatError(nil)
		assert.Empty(t, result)
	})

	t.Run("returns error message for non-nil error", func(t *testing.T) {
		err := fmt.Errorf("test error message")
		result := formatError(err)
		assert.Equal(t, "test error message", result)
	})
}

// ---------------------------------------------------------------------------
// AllCredentials struct
// ---------------------------------------------------------------------------

func TestAllCredentials(t *testing.T) {
	t.Run("creates AllCredentials struct correctly", func(t *testing.T) {
		var creds AllCredentials
		creds.LLM.BaseURL = "http://localhost:8000"
		creds.LLM.Model = "mistralai/Mistral-7B-v0.1"
		creds.AWS.AccessKeyID = "test-access-key"
		creds.AWS.SecretAccessKey = "test-secret-key"
		creds.AWS.Region = "us-east-1"
		creds.Portfolio.Endpoint = "https://api.portfolio.com"
		creds.Portfolio.APIKey = "test-portfolio-key"

		assert.Equal(t, "http://localhost:8000", creds.LLM.BaseURL)
		assert.Equal(t, "mistralai/Mistral-7B-v0.1", creds.LLM.Model)
		assert.Equal(t, "test-access-key", creds.AWS.AccessKeyID)
		assert.Equal(t, "test-secret-key", creds.AWS.SecretAccessKey)
		assert.Equal(t, "us-east-1", creds.AWS.Region)
		assert.Equal(t, "https://api.portfolio.com", creds.Portfolio.Endpoint)
		assert.Equal(t, "test-portfolio-key", creds.Portfolio.APIKey)
	})
}

// ---------------------------------------------------------------------------
// CredentialValidationResult struct
// ---------------------------------------------------------------------------

func TestCredentialValidationResult(t *testing.T) {
	t.Run("creates CredentialValidationResult correctly", func(t *testing.T) {
		result := CredentialValidationResult{
			Service: "test-service",
			Valid:   true,
			Error:   "",
		}
		assert.Equal(t, "test-service", result.Service)
		assert.True(t, result.Valid)
		assert.Empty(t, result.Error)
	})

	t.Run("handles error case", func(t *testing.T) {
		result := CredentialValidationResult{
			Service: "test-service",
			Valid:   false,
			Error:   "test error",
		}
		assert.Equal(t, "test-service", result.Service)
		assert.False(t, result.Valid)
		assert.Equal(t, "test error", result.Error)
	})
}
