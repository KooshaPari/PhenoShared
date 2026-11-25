package routes

import (
	"byteport/lib"
	"byteport/models"
	bproutes "byteport/routes"
	"encoding/base64"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

func init() {
	gin.SetMode(gin.TestMode)
}

// setupRouter creates a minimal Gin engine for testing.
func setupRouter() *gin.Engine {
	return gin.New()
}

// --- Route handler registration tests ---

// TestProtectedHandlersRequireUser verifies that GetInstances and GetProjects
// both return 401 with an "Unauthorized" body when no user is present in the
// gin context.
func TestProtectedHandlersRequireUser(t *testing.T) {
	tests := []struct {
		name    string
		path    string
		handler gin.HandlerFunc
	}{
		{"get instances", "/instances", bproutes.GetInstances},
		{"get projects", "/projects", bproutes.GetProjects},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			w := perform(t, http.MethodGet, tt.path, tt.handler)
			assertStatus(t, w, http.StatusUnauthorized)
			assertBodyContains(t, w, "Unauthorized")
		})
	}
}

// TestProtectedHandlersRejectWrongUserType verifies that GetInstances and
// GetProjects return 500 with "Invalid user context" when the gin context
// carries a non-models.User value under the "user" key.
func TestProtectedHandlersRejectWrongUserType(t *testing.T) {
	tests := []struct {
		name       string
		path       string
		handler    gin.HandlerFunc
		wrongValue any
	}{
		{
			name:       "get instances, string in user",
			path:       "/instances",
			handler:    bproutes.GetInstances,
			wrongValue: "not-a-user-struct",
		},
		{
			name:       "get projects, int in user",
			path:       "/projects",
			handler:    bproutes.GetProjects,
			wrongValue: 12345,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			mw := func(c *gin.Context) {
				c.Set("user", tt.wrongValue)
				c.Next()
			}
			w := performWithMiddleware(t, http.MethodGet, tt.path, tt.handler, mw)
			assertStatus(t, w, http.StatusInternalServerError)
			assertBodyContains(t, w, "Invalid user context")
		})
	}
}

// --- Auth middleware tests ---

// TestAuthMiddlewareBlocksUnauthenticated verifies that the auth middleware
// returns 401 for the various ways the request can lack a valid token.
func TestAuthMiddlewareBlocksUnauthenticated(t *testing.T) {
	okHandler := func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	}

	tests := []struct {
		name             string
		opts             []requestOpt
		wantBodyContains string
	}{
		{name: "no cookie at all"},
		{name: "empty cookie", opts: []requestOpt{withCookie("authToken", "")}},
		{
			name:             "garbage token",
			opts:             []requestOpt{withCookie("authToken", "totally-invalid-token")},
			wantBodyContains: "Invalid or expired token",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			w := performWithMiddleware(t, http.MethodGet, "/protected", okHandler, lib.AuthMiddleware(), tt.opts...)
			assertStatus(t, w, http.StatusUnauthorized)
			if tt.wantBodyContains != "" {
				assertBodyContains(t, w, tt.wantBodyContains)
			}
		})
	}
}

// TestAuthMiddlewareWithMockValidToken verifies that when a valid PASETO-shaped
// token is set as the cookie, the middleware reaches the validation step
// rather than short-circuiting on the missing-header path. When the keyring is
// unavailable (test env), it still returns 401 from the token validation path.
func TestAuthMiddlewareWithMockValidToken(t *testing.T) {
	okHandler := func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	}
	token := "v4.local." + base64.StdEncoding.EncodeToString([]byte("fake-paseto-token"))
	w := performWithMiddleware(t, http.MethodGet, "/protected", okHandler, lib.AuthMiddleware(),
		withCookie("authToken", token))

	assertStatus(t, w, http.StatusUnauthorized)
	assertBodyLacks(t, w, "Authorization header missing")
}

// --- Error response status code tests ---

// TestAuthEndpointsReturnBadRequestForInvalidJSON verifies that Login and
// Signup both return 400 for the various ways the request body can fail to
// bind as a JSON object.
func TestAuthEndpointsReturnBadRequestForInvalidJSON(t *testing.T) {
	tests := []struct {
		name    string
		path    string
		handler gin.HandlerFunc
		body    string
	}{
		{name: "login: garbage body", path: "/login", handler: bproutes.Login, body: "not-json{{{"},
		{name: "login: empty body", path: "/login", handler: bproutes.Login, body: ""},
		{name: "signup: garbage body", path: "/signup", handler: bproutes.Signup, body: "{invalid"},
		{name: "signup: array not object", path: "/signup", handler: bproutes.Signup, body: `["name","email"]`},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			w := perform(t, http.MethodPost, tt.path, tt.handler, withJSONBody(tt.body))
			assertStatus(t, w, http.StatusBadRequest)
		})
	}
}

// TestAuthenticateReturnsUnauthorizedWithoutCookie verifies that the
// Authenticate handler returns 401 when no auth cookie is provided.
func TestAuthenticateReturnsUnauthorizedWithoutCookie(t *testing.T) {
	w := perform(t, http.MethodGet, "/authenticate", bproutes.Authenticate)
	assertStatus(t, w, http.StatusUnauthorized)
}

// TestRouteRegistration verifies that all expected routes are registered
// on a router configured with the same structure as setupRouter in main.go.
func TestRouteRegistration(t *testing.T) {
	router := setupRouter()

	protected := router.Group("/")
	protected.Use(lib.AuthMiddleware())
	{
		protected.GET("/link", bproutes.LinkHandler)
		protected.GET("/authenticate", bproutes.Authenticate)
		protected.GET("/instances", bproutes.GetInstances)
		protected.GET("/projects", bproutes.GetProjects)
		protected.POST("/deploy", bproutes.DeployProject)
		protected.POST("/terminate", bproutes.TerminateInstance)
	}
	router.POST("/login", bproutes.Login)
	router.POST("/signup", bproutes.Signup)

	routes := router.Routes()
	routeMap := make(map[string]bool, len(routes))
	for _, r := range routes {
		routeMap[r.Method+" "+r.Path] = true
	}

	expected := []string{
		"GET /link",
		"GET /authenticate",
		"GET /instances",
		"GET /projects",
		"POST /deploy",
		"POST /terminate",
		"POST /login",
		"POST /signup",
	}

	for _, route := range expected {
		if !routeMap[route] {
			t.Errorf("expected route %q not found in registered routes", route)
		}
	}
	if len(routes) < len(expected) {
		t.Errorf("registered %d routes, want at least %d", len(routes), len(expected))
	}
}

// TestRouteRegistrationMethodMismatch verifies that a POST request to a
// GET-only route returns 405 Method Not Allowed when HandleMethodNotAllowed
// is enabled on the router.
func TestRouteRegistrationMethodMismatch(t *testing.T) {
	router := setupRouter()
	router.HandleMethodNotAllowed = true
	router.GET("/instances", bproutes.GetInstances)

	req := httptest.NewRequest(http.MethodPost, "/instances", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	assertStatus(t, w, http.StatusMethodNotAllowed)
}

// TestAuthMiddlewareResponseFormat verifies that the auth middleware returns
// a JSON response with the correct structure.
func TestAuthMiddlewareResponseFormat(t *testing.T) {
	okHandler := func(c *gin.Context) {
		c.JSON(http.StatusOK, gin.H{"ok": true})
	}
	w := performWithMiddleware(t, http.MethodGet, "/protected", okHandler, lib.AuthMiddleware())

	assertStatus(t, w, http.StatusUnauthorized)
	assertBodyContains(t, w, "error")
	assertHeaderContains(t, w, "Content-Type", "application/json")
}

// TestGetInstancesReturnsJSON verifies that the handler returns valid JSON
// with the correct Content-Type header even on error paths.
func TestGetInstancesReturnsJSON(t *testing.T) {
	w := perform(t, http.MethodGet, "/instances", bproutes.GetInstances)

	assertHeaderContains(t, w, "Content-Type", "application/json")
	assertBodyContains(t, w, "error")
}

// TestUserContextPropagatedToHandler verifies that when a middleware sets a
// models.User in the gin context, the handler can retrieve it via c.Get.
func TestUserContextPropagatedToHandler(t *testing.T) {
	router := setupRouter()

	router.Use(func(c *gin.Context) {
		c.Set("user", models.User{
			UUID:  "test-uuid-123",
			Name:  "Test User",
			Email: "test@example.com",
		})
		c.Next()
	})

	var capturedUser models.User
	router.GET("/instances", func(c *gin.Context) {
		userVal, exists := c.Get("user")
		if !exists {
			t.Error("user not in context")
			c.Status(http.StatusInternalServerError)
			return
		}
		user, ok := userVal.(models.User)
		if !ok {
			t.Error("user is not models.User type")
			c.Status(http.StatusInternalServerError)
			return
		}
		capturedUser = user
		c.JSON(http.StatusOK, gin.H{"uuid": user.UUID})
	})

	req := httptest.NewRequest(http.MethodGet, "/instances", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Errorf("status = %d, want %d", w.Code, http.StatusOK)
	}
	if capturedUser.UUID != "test-uuid-123" {
		t.Errorf("captured user UUID = %q, want %q", capturedUser.UUID, "test-uuid-123")
	}
	if capturedUser.Email != "test@example.com" {
		t.Errorf("captured user email = %q, want %q", capturedUser.Email, "test@example.com")
	}
}
