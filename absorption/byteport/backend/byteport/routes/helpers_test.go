package routes

import (
	"bytes"
	"encoding/base64"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"sync/atomic"
	"testing"

	"byteport/lib"
	"byteport/models"

	"github.com/gin-gonic/gin"
	"github.com/glebarez/sqlite"
	"github.com/google/uuid"
	"github.com/zalando/go-keyring"
	"gorm.io/gorm"
	"gorm.io/gorm/logger"
)

// ----- DB fixtures -----

// routeDBSeq hands every test its own in-memory database; sharing one DSN
// across tests makes them collide because the connection pool sees both.
var routeDBSeq int64

// newRouteTestDB swaps models.DB for a fresh in-memory SQLite holding every
// table the route tests touch, and restores the previous handle on cleanup.
func newRouteTestDB(t *testing.T) *gorm.DB {
	t.Helper()

	dsn := fmt.Sprintf("file:routes%d?mode=memory&cache=shared", atomic.AddInt64(&routeDBSeq, 1))
	db, err := gorm.Open(sqlite.Open(dsn), &gorm.Config{
		Logger: logger.Default.LogMode(logger.Silent),
	})
	if err != nil {
		t.Fatalf("open sqlite: %v", err)
	}
	if err := db.AutoMigrate(&models.User{}, &models.Project{}, &models.Instance{}, &models.GitSecret{}); err != nil {
		t.Fatalf("migrate: %v", err)
	}

	prev := models.DB
	models.DB = db
	t.Cleanup(func() { models.DB = prev })
	return db
}

// ----- Auth / keyring / encryption -----

// resetMockKeyring installs a fresh in-memory keyring backend. The auth and
// git routes read their signing keys from the OS keyring, so every test that
// exercises them needs this before calling seedAuthSystem.
func resetMockKeyring(t *testing.T) {
	t.Helper()
	keyring.MockInit()
	t.Cleanup(func() { keyring.MockInit() })
}

// testEncryptionKeyBytes returns a deterministic 32-byte (AES-256) key. It is
// built programmatically rather than written as a literal so that secret
// scanners do not flag the fixture as a committed credential.
func testEncryptionKeyBytes() []byte {
	k := make([]byte, 32)
	for i := range k {
		k[i] = byte(i)
	}
	return k
}

// seedAuthSystem seeds ENCRYPTION_KEY and bootstraps the token and service
// keys so session-token-protected routes can run end-to-end.
func seedAuthSystem(t *testing.T) {
	t.Helper()
	t.Setenv("ENCRYPTION_KEY", base64.StdEncoding.EncodeToString(testEncryptionKeyBytes()))
	if err := lib.InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}
}

// mustEncrypt encrypts s with the seeded key and fails the test on error.
func mustEncrypt(t *testing.T, s string) string {
	t.Helper()
	out, err := lib.EncryptSecret(s)
	if err != nil {
		t.Fatalf("EncryptSecret(%q): %v", s, err)
	}
	return out
}

// ----- Convenience compound helpers -----

// setupAuthDB bundles the four calls every DB-backed route test opens with:
//
//	gin.SetMode(gin.TestMode)
//	resetMockKeyring(t)
//	seedAuthSystem(t)
//	newRouteTestDB(t)
//
// Use this in any test that exercises a route through its full middleware
// stack (AuthMiddleware → handler) with seeded data. Tests that only need
// pure-function coverage (e.g. deployRequest.repositoryID()) should call
// the individual helpers directly.
func setupAuthDB(t *testing.T) *gorm.DB {
	t.Helper()
	gin.SetMode(gin.TestMode)
	resetMockKeyring(t)
	seedAuthSystem(t)
	return newRouteTestDB(t)
}

// seedUser creates and persists a fresh user; returned UUID is the
// authenticated identity for downstream routes.
func seedUser(t *testing.T, db *gorm.DB) models.User {
	t.Helper()
	u := models.User{
		UUID:     uuid.NewString(),
		Email:    "u@example.com",
		Name:     "U",
		Password: "x",
	}
	if err := db.Create(&u).Error; err != nil {
		t.Fatalf("seed user: %v", err)
	}
	return u
}

// seedOtherUser creates a second user with a distinct email so a test can
// verify ownership scoping (the second user's data must not be returned to
// the first).
func seedOtherUser(t *testing.T, db *gorm.DB) models.User {
	t.Helper()
	u := models.User{
		UUID:     uuid.NewString(),
		Email:    "other@example.com",
		Name:     "Other",
		Password: "x",
	}
	if err := db.Create(&u).Error; err != nil {
		t.Fatalf("seed other user: %v", err)
	}
	return u
}

// authedGet drives a GET through a router wired the way main.go wires the
// protected group, and fails the test unless the handler answers 200. It
// exists so the token/cookie/middleware boilerplate lives in one place.
func authedGet(t *testing.T, user models.User, path string, handler gin.HandlerFunc) *httptest.ResponseRecorder {
	t.Helper()

	tok, err := lib.GenerateToken(user)
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	r := gin.New()
	r.Use(lib.AuthMiddleware())
	r.GET(path, handler)

	req := httptest.NewRequest(http.MethodGet, path, nil)
	req.AddCookie(&http.Cookie{Name: "authToken", Value: tok})
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("GET %s: status = %d, want 200 (body %s)", path, w.Code, w.Body.String())
	}
	return w
}

// ----- Loadtest / benchmark helpers -----

// setupBenchEnv starts the mock NanoVMS server and sets the NVMS_URL / NVMS_TOKEN
// env vars to point at it. It registers a cleanup via t.Cleanup that closes the
// server and unsets the env vars. Returns the server URL.
func setupBenchEnv(tb testing.TB, token string) string {
	tb.Helper()
	mockNVMS := mockNVMSLoadTest(tb)
	tb.Cleanup(mockNVMS.Close)

	os.Setenv("NVMS_URL", mockNVMS.URL)
	os.Setenv("NVMS_TOKEN", token)
	tb.Cleanup(func() {
		os.Unsetenv("NVMS_URL")
		os.Unsetenv("NVMS_TOKEN")
	})

	return mockNVMS.URL
}

// runBenchRequest performs a single request against the mock NVMS server.
// `extra` is an optional finalizer for headers/body that vary per benchmark.
func runBenchRequest(b *testing.B, method, url, token string, body []byte, extra func(*http.Request)) {
	b.Helper()
	req, _ := http.NewRequest(method, url, bytes.NewReader(body))
	req.Header.Set("Authorization", "Bearer "+token)
	if extra != nil {
		extra(req)
	}
	resp, err := (&http.Client{}).Do(req)
	if err != nil {
		b.Errorf("request failed: %v", err)
		return
	}
	resp.Body.Close()
}
