package routes

import (
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"byteport/lib"
	"byteport/models"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// TestRetrieveRepositoriesHappyPath covers the success branch: when the
// user has a valid encrypted GitHub access token in the database, the route
// must call lib.ListRepositories (stubbed to return canned JSON) and surface
// it as application/json.
func TestRetrieveRepositoriesHappyPath(t *testing.T) {
	db := setupAuthDB(t)
	user := models.User{
		UUID: uuid.NewString(),
		Git: models.Git{
			Token: mustEncrypt(t, "real-access-token"),
		},
	}
	if err := db.Create(&user).Error; err != nil {
		t.Fatalf("seed user: %v", err)
	}

	// Stub lib.ListRepositories via a function value would require
	// changing the production code, which we already did in lib/git.go
	// via httpGitHubDoer. Swap that here so the call returns a canned
	// 200 with a JSON body.
	prev := lib.ListRepositories
	lib.ListRepositories = func(accessToken string) (string, error) {
		if accessToken != "real-access-token" {
			t.Errorf("accessToken passed to ListRepositories = %q, want real-access-token", accessToken)
		}
		return `[{"name":"repo-a"},{"name":"repo-b"}]`, nil
	}
	t.Cleanup(func() { lib.ListRepositories = prev })

	r := gin.New()
	r.GET("/repos", func(c *gin.Context) {
		c.Set("user", user)
		RetrieveRepositories(c)
	})
	req := httptest.NewRequest(http.MethodGet, "/repos", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body %s)", w.Code, w.Body.String())
	}
	if got := w.Header().Get("Content-Type"); !strings.HasPrefix(got, "application/json") {
		t.Errorf("Content-Type = %q, want application/json", got)
	}
	if w.Body.String() != `[{"name":"repo-a"},{"name":"repo-b"}]` {
		t.Errorf("body = %q, want the canned JSON", w.Body.String())
	}
}

// TestRetrieveRepositoriesDecryptError covers the decrypt-failure branch:
// when the stored Git token is not a valid AES payload, the route must
// respond 500 with "Failed to decrypt Git token".
func TestRetrieveRepositoriesDecryptError(t *testing.T) {
	db := setupAuthDB(t)
	user := models.User{
		UUID: uuid.NewString(),
		Git:  models.Git{Token: "garbage-not-encrypted"},
	}
	if err := db.Create(&user).Error; err != nil {
		t.Fatalf("seed user: %v", err)
	}

	r := gin.New()
	r.GET("/repos", func(c *gin.Context) {
		c.Set("user", user)
		RetrieveRepositories(c)
	})
	req := httptest.NewRequest(http.MethodGet, "/repos", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500 (body %s)", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "Failed to decrypt Git token") {
		t.Errorf("body = %q, want it to mention decrypt failure", w.Body.String())
	}
}

// TestRetrieveRepositoriesGitHubError covers the GitHub-side error branch:
// when lib.ListRepositories returns an error, the route must respond 500
// with "Failed to list repositories".
func TestRetrieveRepositoriesGitHubError(t *testing.T) {
	db := setupAuthDB(t)
	user := models.User{
		UUID: uuid.NewString(),
		Git:  models.Git{Token: mustEncrypt(t, "real-access-token")},
	}
	if err := db.Create(&user).Error; err != nil {
		t.Fatalf("seed user: %v", err)
	}

	prev := lib.ListRepositories
	lib.ListRepositories = func(accessToken string) (string, error) {
		return "", fmt.Errorf("github down")
	}
	t.Cleanup(func() { lib.ListRepositories = prev })

	r := gin.New()
	r.GET("/repos", func(c *gin.Context) {
		c.Set("user", user)
		RetrieveRepositories(c)
	})
	req := httptest.NewRequest(http.MethodGet, "/repos", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500 (body %s)", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "Failed to list repositories") {
		t.Errorf("body = %q, want it to mention Failed to list repositories", w.Body.String())
	}
}

// TestHandleCallbackHappyPath covers the success branch: when the state
// splits into "<paseto><BYTEPORT><uuid>" AND the paseto is valid AND the
// uuid resolves to a user AND lib.GetUserAccessToken returns credentials
// AND lib.ValidateGit succeeds, the route must persist the new git
// credentials and return the success HTML.
func TestHandleCallbackHappyPath(t *testing.T) {
	db := setupAuthDB(t)
	cidEnc, _ := lib.EncryptSecret("cid")
	csecEnc, _ := lib.EncryptSecret("csec")
	if err := db.Create(&models.GitSecret{ClientID: cidEnc, ClientSecret: csecEnc}).Error; err != nil {
		t.Fatalf("seed GitSecret: %v", err)
	}

	user := models.User{
		UUID:     uuid.NewString(),
		Email:    "cb@example.com",
		Password: "x",
	}
	if err := db.Create(&user).Error; err != nil {
		t.Fatalf("seed user: %v", err)
	}

	pasetoTok, err := lib.GenerateToken(user)
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	// Stub lib.GetUserAccessToken and lib.ValidateGit.
	prevGetUserAccessToken := lib.GetUserAccessToken
	lib.GetUserAccessToken = func(pasetoToken, code string) (models.Git, error) {
		return models.Git{
			Token:              "new-access",
			RefreshToken:       "new-refresh",
			TokenExpiry:        timeNow(),
			RefreshTokenExpiry: timeNow(),
		}, nil
	}
	t.Cleanup(func() { lib.GetUserAccessToken = prevGetUserAccessToken })

	prevValidateGit := lib.ValidateGit
	lib.ValidateGit = func(u models.User) error { return nil }
	t.Cleanup(func() { lib.ValidateGit = prevValidateGit })

	state := pasetoTok + "<BYTEPORT>" + user.UUID
	r := gin.New()
	r.GET("/callback", HandleCallback)
	req := httptest.NewRequest(http.MethodGet, "/callback?code=auth-code&state="+urlEscape(state), nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body %s)", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "github-linked") {
		t.Errorf("body = %q, want it to embed the postMessage 'github-linked'", w.Body.String())
	}

	// Confirm the user's git credentials were persisted.
	var reloaded models.User
	if err := db.Where("uuid = ?", user.UUID).First(&reloaded).Error; err != nil {
		t.Fatalf("reload: %v", err)
	}
	if reloaded.Git.Token == "" {
		t.Error("user.Git.Token was not persisted")
	}
	if reloaded.Git.RefreshToken == "" {
		t.Error("user.Git.RefreshToken was not persisted")
	}
	// And the encrypted blobs should decrypt back to the canned values.
	gotToken, err := lib.DecryptSecret(reloaded.Git.Token)
	if err != nil {
		t.Fatalf("decrypt token: %v", err)
	}
	if gotToken != "new-access" {
		t.Errorf("decrypted token = %q, want new-access", gotToken)
	}
}

// TestHandleCallbackInvalidState covers the malformed-state branch: when
// the state does not split into two non-empty halves, the route must
// respond 400 immediately, before any DB call.
func TestHandleCallbackInvalidState(t *testing.T) {
	gin.SetMode(gin.TestMode)
	resetMockKeyring(t)
	seedAuthSystem(t)
	newRouteTestDB(t)

	cases := []struct {
		name  string
		state string
	}{
		{"no delimiter", "abc"},
		{"empty halves", "<BYTEPORT>"},
		{"empty auth token", "<BYTEPORT>user-1"},
		{"empty user id", "tok<BYTEPORT>"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			r := gin.New()
			r.GET("/callback", HandleCallback)
			req := httptest.NewRequest(http.MethodGet, "/callback?code=x&state="+urlEscape(tc.state), nil)
			w := httptest.NewRecorder()
			r.ServeHTTP(w, req)

			if w.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want 400 (body %s)", w.Code, w.Body.String())
			}
			if !strings.Contains(w.Body.String(), "Invalid state parameter") {
				t.Errorf("body = %q, want it to mention Invalid state parameter", w.Body.String())
			}
		})
	}
}

// TestHandleCallbackUnknownUser covers the user-not-found branch: the
// state parses cleanly but the user-id half does not resolve to a row.
// The route must respond 401.
func TestHandleCallbackUnknownUser(t *testing.T) {
	gin.SetMode(gin.TestMode)
	resetMockKeyring(t)
	seedAuthSystem(t)
	newRouteTestDB(t)

	user := models.User{UUID: "real-user", Email: "u@example.com"}
	pasetoTok, err := lib.GenerateToken(user)
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}
	state := pasetoTok + "<BYTEPORT>ghost-user"

	r := gin.New()
	r.GET("/callback", HandleCallback)
	req := httptest.NewRequest(http.MethodGet, "/callback?code=x&state="+urlEscape(state), nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401 (body %s)", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "Invalid uuid") {
		t.Errorf("body = %q, want it to mention Invalid uuid", w.Body.String())
	}
}

// TestValidateLinkMissingProvider covers the "no provider for the
// configured name" branch: when the request body has an LLM provider name
// that does not appear in LLMConfig.Providers AND the canonical fallback
// is also absent, ValidateLink must respond 400 with "Missing OpenAI API key".
func TestValidateLinkMissingProvider(t *testing.T) {
	gin.SetMode(gin.TestMode)
	resetMockKeyring(t)
	seedAuthSystem(t)

	// Stub the outbound validators so we don't hit AWS/OpenAI/Portfolio.
	stubValidatorsForGit(t)

	db := newRouteTestDB(t)
	user := models.User{
		UUID:     uuid.NewString(),
		Email:    "vp@example.com",
		Name:     "VP",
		Password: "x",
	}
	if err := db.Create(&user).Error; err != nil {
		t.Fatalf("seed: %v", err)
	}

	r := gin.New()
	r.POST("/validate-link", func(c *gin.Context) {
		c.Set("user", user)
		ValidateLink(c)
	})
	body := `{
	  "awsCreds": {"accessKeyId":"a","secretAccessKey":"b"},
	  "llmConfig": {"provider":"nonexistent","providers":{}},
	  "portfolio": {"rootEndpoint":"https://x","apiKey":"y"}
	}`
	req := httptest.NewRequest(http.MethodPost, "/validate-link", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400 (body %s)", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "Missing OpenAI API key") {
		t.Errorf("body = %q, want it to mention Missing OpenAI API key", w.Body.String())
	}
}

// TestValidateLinkHappyPath covers the success branch: a complete body
// with a canonical provider entry must persist encrypted credentials and
// return 200.
func TestValidateLinkHappyPath(t *testing.T) {
	gin.SetMode(gin.TestMode)
	resetMockKeyring(t)
	seedAuthSystem(t)

	gotOpenAIKey := stubValidatorsForGit(t)

	db := newRouteTestDB(t)
	user := models.User{
		UUID:     uuid.NewString(),
		Email:    "vlh@example.com",
		Name:     "VLH",
		Password: "x",
	}
	if err := db.Create(&user).Error; err != nil {
		t.Fatalf("seed: %v", err)
	}

	r := gin.New()
	r.POST("/validate-link", func(c *gin.Context) {
		c.Set("user", user)
		ValidateLink(c)
	})
	body := `{
	  "awsCreds": {"accessKeyId":"AKIA-test","secretAccessKey":"secret-test"},
	  "llmConfig": {"provider":"openai","providers":{"openai":{"modal":"gpt-4o","api_key":"sk-test-key"}}},
	  "portfolio": {"rootEndpoint":"https://portfolio.example.com","apiKey":"portfolio-key"}
	}`
	req := httptest.NewRequest(http.MethodPost, "/validate-link", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body %s)", w.Code, w.Body.String())
	}
	if *gotOpenAIKey != "sk-test-key" {
		t.Errorf("OpenAI validator received %q, want sk-test-key", *gotOpenAIKey)
	}

	// Confirm the credentials were persisted under the canonical
	// "openai" key.
	var reloaded models.User
	if err := db.Where("uuid = ?", user.UUID).First(&reloaded).Error; err != nil {
		t.Fatalf("reload: %v", err)
	}
	provider, ok := reloaded.LLMConfig.Providers["openai"]
	if !ok {
		t.Fatalf("providers = %v, want an openai entry", reloaded.LLMConfig.Providers)
	}
	plain, err := lib.DecryptSecret(provider.APIKey)
	if err != nil {
		t.Fatalf("decrypt: %v", err)
	}
	if plain != "sk-test-key" {
		t.Errorf("stored api_key decrypts to %q, want sk-test-key", plain)
	}
	if reloaded.LLMConfig.Provider != "openai" {
		t.Errorf("Provider = %q, want openai", reloaded.LLMConfig.Provider)
	}
}

// stubValidatorsForGit replaces lib.ValidateAWSCredentials, lib.ValidateOpenAICredentials,
// and lib.ValidatePortfolioAPI with no-op stubs and reports the api key
// passed to the OpenAI validator. Returns a pointer to the captured string.
func stubValidatorsForGit(t *testing.T) *string {
	t.Helper()
	gotOpenAIKey := new(string)
	prevAWS, prevOAI, prevPortfolio := lib.ValidateAWSCredentials, lib.ValidateOpenAICredentials, lib.ValidatePortfolioAPI
	t.Cleanup(func() {
		lib.ValidateAWSCredentials = prevAWS
		lib.ValidateOpenAICredentials = prevOAI
		lib.ValidatePortfolioAPI = prevPortfolio
	})
	lib.ValidateAWSCredentials = func(accessKey, secretKey string) error { return nil }
	lib.ValidateOpenAICredentials = func(apiToken string) error {
		*gotOpenAIKey = apiToken
		return nil
	}
	lib.ValidatePortfolioAPI = func(rootEndpoint, apiKey string) error { return nil }
	return gotOpenAIKey
}

// urlEscape is a tiny helper that percent-encodes the special chars that
// appear in state values without dragging in net/url across the test file.
func urlEscape(s string) string {
	// Hand-roll the few chars that appear in our states: < and >
	var b strings.Builder
	for _, r := range s {
		switch r {
		case '<':
			b.WriteString("%3C")
		case '>':
			b.WriteString("%3E")
		default:
			b.WriteRune(r)
		}
	}
	return b.String()
}

// timeNow returns time.Now(); kept here so this file's imports stay tight
// when time isn't otherwise needed by a refactor.
var timeNow = func() time.Time { return time.Now() }
