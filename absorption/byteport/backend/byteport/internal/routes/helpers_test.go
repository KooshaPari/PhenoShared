package routes

import (
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
)

// perform executes a single HTTP request against the supplied handler on a
// fresh router and returns the recorded response. Centralizes the 4-line
// preamble that every test in this package repeats.
func perform(t *testing.T, method, path string, handler gin.HandlerFunc, opts ...requestOpt) *httptest.ResponseRecorder {
	t.Helper()
	router := setupRouter()
	router.Handle(method, path, handler)

	req := httptest.NewRequest(method, path, nil)
	for _, opt := range opts {
		opt(req)
	}
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	return w
}

// performWithMiddleware installs middleware before the handler and applies the
// supplied request options. Use this when the test exercises the middleware
// contract (auth, context validation) rather than the handler in isolation.
func performWithMiddleware(t *testing.T, method, path string, handler gin.HandlerFunc, middleware gin.HandlerFunc, opts ...requestOpt) *httptest.ResponseRecorder {
	t.Helper()
	router := setupRouter()
	router.Use(middleware)
	router.Handle(method, path, handler)

	req := httptest.NewRequest(method, path, nil)
	for _, opt := range opts {
		opt(req)
	}
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)
	return w
}

type requestOpt func(*http.Request)

// withJSONBody sets the request body and Content-Type to application/json.
func withJSONBody(body string) requestOpt {
	return func(r *http.Request) {
		r.Body = io.NopCloser(strings.NewReader(body))
		r.Header.Set("Content-Type", "application/json")
		r.ContentLength = int64(len(body))
	}
}

// withCookie adds a single cookie to the request.
func withCookie(name, value string) requestOpt {
	return func(r *http.Request) {
		r.AddCookie(&http.Cookie{Name: name, Value: value})
	}
}

// assertStatus fails the test if the response code doesn't match wantCode.
func assertStatus(t *testing.T, w *httptest.ResponseRecorder, wantCode int) {
	t.Helper()
	if w.Code != wantCode {
		t.Errorf("status = %d, want %d", w.Code, wantCode)
	}
}

// assertBodyContains fails the test if the response body doesn't contain wantStr.
func assertBodyContains(t *testing.T, w *httptest.ResponseRecorder, wantStr string) {
	t.Helper()
	if body := w.Body.String(); !strings.Contains(body, wantStr) {
		t.Errorf("body = %q, want to contain %q", body, wantStr)
	}
}

// assertBodyLacks fails the test if the response body contains forbiddenStr.
func assertBodyLacks(t *testing.T, w *httptest.ResponseRecorder, forbiddenStr string) {
	t.Helper()
	if body := w.Body.String(); strings.Contains(body, forbiddenStr) {
		t.Errorf("body = %q, should not contain %q", body, forbiddenStr)
	}
}

// assertHeaderContains fails the test if the named response header doesn't
// contain wantSubstr. Use for Content-Type and similar.
func assertHeaderContains(t *testing.T, w *httptest.ResponseRecorder, header, wantSubstr string) {
	t.Helper()
	if got := w.Header().Get(header); !strings.Contains(got, wantSubstr) {
		t.Errorf("header[%s] = %q, want to contain %q", header, got, wantSubstr)
	}
}
