package secrets

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// httpClient abstracts the Do method so we can mock HTTP interactions in tests.
type httpClient interface {
	Do(req *http.Request) (*http.Response, error)
}

// accessToken represents a bearer token with expiry metadata.
type accessToken struct {
	Value  string
	Expiry time.Time
}

// tokenProvider fetches access tokens for a given scope.
type tokenProvider interface {
	Token(ctx context.Context, scope string) (accessToken, error)
}

// defaultHTTPClient provides a safe default HTTP client with sane timeouts.
var defaultHTTPClient = func() *http.Client {
	return &http.Client{
		Timeout: 30 * time.Second,
	}
}

var jsonMarshal = json.Marshal

// readResponseBody safely reads response bodies for error reporting.
func readResponseBody(resp *http.Response) ([]byte, error) {
	defer resp.Body.Close()
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response body: %w", err)
	}
	return body, nil
}
