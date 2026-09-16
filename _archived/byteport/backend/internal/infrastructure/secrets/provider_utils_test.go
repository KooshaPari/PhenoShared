package secrets

import (
	"errors"
	"net/http"
	"testing"

	"github.com/stretchr/testify/assert"
)

type errorReadCloser struct {
	err error
}

func (e *errorReadCloser) Read([]byte) (int, error) {
	return 0, e.err
}

func (e *errorReadCloser) Close() error { return nil }

func TestReadResponseBody_Error(t *testing.T) {
	resp := &http.Response{Body: &errorReadCloser{err: errors.New("boom")}}

	_, err := readResponseBody(resp)
	assert.Error(t, err)
	assert.Contains(t, err.Error(), "failed to read response body")
}
