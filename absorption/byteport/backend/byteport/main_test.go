package main

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

// TestResolvePortPrecedence pins the documented port contract: PORT beats
// BYTEPORT_API_PORT, which beats canonicalPort. INSTALL.md, DEPLOYMENT.md,
// setup-windows.ps1, .air.toml, the Tauri CSP, and frontend/web's getBaseUrl
// all depend on this precedence, so a silent change here breaks every client.
func TestResolvePortPrecedence(t *testing.T) {
	cases := []struct {
		name   string
		port   string
		legacy string
		want   string
	}{
		{name: "PORT wins over BYTEPORT_API_PORT", port: "1111", legacy: "2222", want: "1111"},
		{name: "BYTEPORT_API_PORT used when PORT unset", legacy: "2222", want: "2222"},
		{name: "canonical default when neither is set", want: canonicalPort},
		{name: "blank PORT falls through to BYTEPORT_API_PORT", port: "   ", legacy: "2222", want: "2222"},
		{name: "blank PORT with no fallback yields canonical", port: "   ", want: canonicalPort},
		{name: "surrounding whitespace is trimmed", port: " 3333 ", want: "3333"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			t.Setenv("PORT", tc.port)
			t.Setenv("BYTEPORT_API_PORT", tc.legacy)

			if got := resolvePort(); got != tc.want {
				t.Fatalf("resolvePort() = %q, want %q", got, tc.want)
			}
		})
	}
}

// TestSetupRouterRegistersExpectedRoutes pins the route table. The desktop shell
// and the SvelteKit client call these paths directly, so a rename or a dropped
// registration is a breaking change rather than an internal detail.
func TestSetupRouterRegistersExpectedRoutes(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := setupRouter()

	registered := make(map[string]bool, len(r.Routes()))
	for _, route := range r.Routes() {
		registered[route.Method+" "+route.Path] = true
	}

	// Routes behind lib.AuthMiddleware().
	protected := []string{
		"GET /link",
		"POST /link",
		"GET /authenticate",
		"GET /instances",
		"GET /projects",
		"GET /api/github/repositories",
		"POST /deploy",
		"POST /terminate",
		"GET /user/:id/creds",
		"PUT /user/:id/creds",
	}
	// Unauthenticated routes.
	public := []string{
		"POST /login",
		"POST /signup",
		"GET /api/github/callback",
		"GET /health",
		"GET /metrics",
	}

	for _, want := range append(protected, public...) {
		if !registered[want] {
			t.Errorf("route %q is not registered", want)
		}
	}
}

// TestSetupRouterAdmitsTauriOrigin covers the packaged-desktop regression the
// CORS block documents: gin-contrib/cors panics on scheme-less origins such as
// tauri://localhost, so it cannot be listed in AllowOrigins and must be admitted
// through AllowOriginFunc. Without that, every preflight from the desktop app
// 403s and the app cannot reach the backend at all.
func TestSetupRouterAdmitsTauriOrigin(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := setupRouter()

	allowed := []string{
		"tauri://localhost",
		"http://tauri.localhost",
		"http://localhost:5173",
		"http://localhost:8081",
	}

	for _, origin := range allowed {
		t.Run(origin, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodOptions, "/health", nil)
			req.Header.Set("Origin", origin)
			req.Header.Set("Access-Control-Request-Method", http.MethodGet)
			w := httptest.NewRecorder()

			r.ServeHTTP(w, req)

			if w.Code != http.StatusNoContent {
				t.Errorf("preflight status = %d, want %d", w.Code, http.StatusNoContent)
			}
			if got := w.Header().Get("Access-Control-Allow-Origin"); got != origin {
				t.Errorf("Access-Control-Allow-Origin = %q, want %q", got, origin)
			}
		})
	}
}

// TestSetupRouterRejectsDisallowedOrigin is the other half of the CORS contract:
// an origin that is neither a listed http origin nor tauri://localhost must not
// receive an Access-Control-Allow-Origin grant.
func TestSetupRouterRejectsDisallowedOrigin(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := setupRouter()

	req := httptest.NewRequest(http.MethodOptions, "/health", nil)
	req.Header.Set("Origin", "https://evil.example.com")
	req.Header.Set("Access-Control-Request-Method", http.MethodGet)
	w := httptest.NewRecorder()

	r.ServeHTTP(w, req)

	if got := w.Header().Get("Access-Control-Allow-Origin"); got != "" {
		t.Errorf("Access-Control-Allow-Origin = %q for a disallowed origin, want empty", got)
	}
	if w.Code == http.StatusNoContent {
		t.Errorf("preflight from a disallowed origin succeeded with %d, want a rejection", w.Code)
	}
}

// TestSetupRouterProtectedGroupRequiresAuth proves the protected group really is
// wired to lib.AuthMiddleware: an unauthenticated request must be rejected with
// 401 rather than reaching the handler. This exercises the middleware chain
// through the real router instead of calling the middleware in isolation.
func TestSetupRouterProtectedGroupRequiresAuth(t *testing.T) {
	gin.SetMode(gin.TestMode)
	r := setupRouter()

	for _, path := range []string{"/projects", "/instances", "/link"} {
		t.Run(path, func(t *testing.T) {
			req := httptest.NewRequest(http.MethodGet, path, nil)
			w := httptest.NewRecorder()

			r.ServeHTTP(w, req)

			if w.Code != http.StatusUnauthorized {
				t.Fatalf("GET %s without a cookie: status = %d, want %d", path, w.Code, http.StatusUnauthorized)
			}
		})
	}
}

// TestInitTracerReturnsProvider covers the tracer bootstrap and its shutdown
// path, which main() calls before any route is served.
func TestInitTracerReturnsProvider(t *testing.T) {
	tp, err := initTracer()
	if err != nil {
		t.Fatalf("initTracer() error = %v", err)
	}
	if tp == nil {
		t.Fatal("initTracer() returned a nil provider")
	}
	if err := tp.Shutdown(context.Background()); err != nil {
		t.Fatalf("Shutdown() error = %v", err)
	}
}
