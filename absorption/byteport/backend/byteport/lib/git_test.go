package lib

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"sync/atomic"
	"testing"
	"time"

	"byteport/models"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// stubGitHubDoer replaces httpGitHubDoer for the duration of a test. The
// returned restore function should be deferred. Tests use this to inject
// canned responses without making outbound HTTP calls.
func stubGitHubDoer(t *testing.T, doer func(*http.Request) (*http.Response, error)) func() {
	t.Helper()
	prev := httpGitHubDoer
	httpGitHubDoer = doer
	return func() { httpGitHubDoer = prev }
}

// jsonResponse builds a minimal *http.Response with the supplied status and
// body, JSON Content-Type, and a non-nil Header so callers can defer
// resp.Body.Close() safely.
func jsonResponse(status int, body string) *http.Response {
	h := make(http.Header)
	h.Set("Content-Type", "application/json")
	return &http.Response{
		StatusCode: status,
		Body:       io.NopCloser(strings.NewReader(body)),
		Header:     h,
	}
}

// TestListRepositoriesHappyPath covers the success branch: a 200 with a JSON
// body must surface the body verbatim so the route layer can hand it to the
// client. Authorization header must be set to "Bearer <token>".
func TestListRepositoriesHappyPath(t *testing.T) {
	restore := stubGitHubDoer(t, func(req *http.Request) (*http.Response, error) {
		if !strings.HasSuffix(req.URL.Path, "/user/repos") {
			t.Errorf("unexpected path %q, want /user/repos", req.URL.Path)
		}
		if req.Method != http.MethodGet {
			t.Errorf("method = %q, want GET", req.Method)
		}
		if got := req.Header.Get("Authorization"); got != "Bearer test-token" {
			t.Errorf("Authorization = %q, want Bearer test-token", got)
		}
		return jsonResponse(http.StatusOK, `[{"name":"hello"}]`), nil
	})
	defer restore()

	body, err := ListRepositories("test-token")
	if err != nil {
		t.Fatalf("ListRepositories: %v", err)
	}
	if body != `[{"name":"hello"}]` {
		t.Fatalf("body = %q, want %q", body, `[{"name":"hello"}]`)
	}
}

// TestListRepositoriesReportsAuthError covers the 4xx branch: a 401 must
// surface as a non-nil error carrying the status code.
func TestListRepositoriesReportsAuthError(t *testing.T) {
	restore := stubGitHubDoer(t, func(req *http.Request) (*http.Response, error) {
		return jsonResponse(http.StatusUnauthorized, `{"message":"bad creds"}`), nil
	})
	defer restore()

	_, err := ListRepositories("bad-token")
	if err == nil {
		t.Fatal("ListRepositories accepted 401; auth failure is being swallowed")
	}
	if !strings.Contains(err.Error(), "401") {
		t.Fatalf("error %q does not mention status 401", err.Error())
	}
}

// TestListRepositoriesReportsTransportError covers the connection-error
// branch: when the doer returns an error, ListRepositories must wrap it.
func TestListRepositoriesReportsTransportError(t *testing.T) {
	restore := stubGitHubDoer(t, func(req *http.Request) (*http.Response, error) {
		return nil, errors.New("connection refused")
	})
	defer restore()

	_, err := ListRepositories("any")
	if err == nil {
		t.Fatal("ListRepositories accepted a transport error")
	}
	if !strings.Contains(err.Error(), "connection refused") {
		t.Fatalf("error %q does not mention the underlying cause", err.Error())
	}
}

// TestGenerateGitPasetoDelegatesToGenerateToken documents that
// GenerateGitPaseto is a thin wrapper around GenerateToken. We assert on the
// AUDIENCE field rather than raw equality: both calls include IssuedAt /
// NotBefore timestamps at nanosecond resolution, so the ciphertexts will
// differ even though the wrapping key, audience, and structure are identical.
func TestGenerateGitPasetoDelegatesToGenerateToken(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}

	user := models.User{UUID: uuid.NewString(), Email: "alias@example.com"}
	a, err := GenerateGitPaseto(user)
	if err != nil {
		t.Fatalf("GenerateGitPaseto: %v", err)
	}
	b, err := GenerateToken(user)
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}
	if a == "" || b == "" {
		t.Fatal("one of the tokens is empty")
	}
	// Both tokens must validate against the same user-id claim.
	for _, tok := range []string{a, b} {
		valid, parsed, err := ValidateToken(tok)
		if err != nil || !valid {
			t.Fatalf("token failed validation: %v / valid=%v", err, valid)
		}
		uid, _ := parsed.GetString("user-id")
		if uid != user.UUID {
			t.Fatalf("user-id claim = %q, want %q", uid, user.UUID)
		}
	}
}

// TestLinkWithGithubRedirectsToAuthorize covers the success branch:
// LinkWithGithub must redirect to GitHub's authorize endpoint with the
// decrypted client_id and a state token of the form "<paseto><BYTEPORT><uuid>".
func TestLinkWithGithubRedirectsToAuthorize(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}
	seedEncryptionKey(t)

	db := newLibTestDB(t)
	clientIDPlain := "my-client-id"
	encrypted, err := EncryptSecret(clientIDPlain)
	if err != nil {
		t.Fatalf("EncryptSecret: %v", err)
	}
	if err := db.Create(&models.GitSecret{ClientID: encrypted}).Error; err != nil {
		t.Fatalf("seed GitSecret: %v", err)
	}

	user := models.User{UUID: uuid.NewString(), Email: "u@example.com"}

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/link", nil)
	LinkWithGithub(c, user)

	if w.Code != http.StatusFound {
		t.Fatalf("status = %d, want 302 (body %s)", w.Code, w.Body.String())
	}
	loc := w.Header().Get("Location")
	if !strings.HasPrefix(loc, "https://github.com/login/oauth/authorize?client_id="+clientIDPlain+"&state=") {
		t.Fatalf("Location = %q, want it to begin with the GitHub authorize URL carrying the decrypted client_id", loc)
	}
	if !strings.Contains(loc, "<BYTEPORT>"+user.UUID) {
		t.Fatalf("Location = %q, want it to embed the user UUID after <BYTEPORT>", loc)
	}
}

// TestLinkWithGithubReportsDecryptError covers the failure branch: when
// DecryptSecret fails, the handler must return 500.
func TestLinkWithGithubReportsDecryptError(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}
	seedEncryptionKey(t)

	db := newLibTestDB(t)
	if err := db.Create(&models.GitSecret{ClientID: "not-base64-or-valid-ciphertext"}).Error; err != nil {
		t.Fatalf("seed GitSecret: %v", err)
	}

	user := models.User{UUID: "u", Email: "u@example.com"}

	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/link", nil)
	LinkWithGithub(c, user)

	if w.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500 (body %s)", w.Code, w.Body.String())
	}
}

// TestGetUserAccessTokenHappyPath covers the success branch: a 200 with a
// valid access_token + refresh_token response must be parsed into a
// models.Git with the expected expiry windows.
func TestGetUserAccessTokenHappyPath(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}
	seedEncryptionKey(t)

	db := newLibTestDB(t)
	clientIDPlain := "cid"
	clientSecretPlain := "csec"
	cidEnc, _ := EncryptSecret(clientIDPlain)
	csecEnc, _ := EncryptSecret(clientSecretPlain)
	if err := db.Create(&models.GitSecret{ClientID: cidEnc, ClientSecret: csecEnc}).Error; err != nil {
		t.Fatalf("seed GitSecret: %v", err)
	}

	user := models.User{UUID: uuid.NewString(), Email: "u@example.com"}
	pasetoToken, err := GenerateToken(user)
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	restore := stubGitHubDoer(t, func(req *http.Request) (*http.Response, error) {
		if req.Method != http.MethodPost {
			t.Errorf("method = %q, want POST", req.Method)
		}
		body, _ := io.ReadAll(req.Body)
		var payload map[string]string
		if err := json.Unmarshal(body, &payload); err != nil {
			t.Fatalf("payload not JSON: %v", err)
		}
		if payload["client_id"] != clientIDPlain {
			t.Errorf("client_id = %q, want %q", payload["client_id"], clientIDPlain)
		}
		if payload["client_secret"] != clientSecretPlain {
			t.Errorf("client_secret = %q, want %q", payload["client_secret"], clientSecretPlain)
		}
		return jsonResponse(http.StatusOK, `{"access_token":"new-tok","refresh_token":"new-ref"}`), nil
	})
	defer restore()

	before := time.Now()
	got, err := GetUserAccessToken(pasetoToken, "the-code")
	if err != nil {
		t.Fatalf("GetUserAccessToken: %v", err)
	}
	if got.Token != "new-tok" {
		t.Errorf("Token = %q, want new-tok", got.Token)
	}
	if got.RefreshToken != "new-ref" {
		t.Errorf("RefreshToken = %q, want new-ref", got.RefreshToken)
	}
	if got.TokenExpiry.Before(before.Add(7*time.Hour + 44*time.Minute)) {
		t.Errorf("TokenExpiry = %s, expected >= 7h45m from now", got.TokenExpiry)
	}
	if got.RefreshTokenExpiry.Before(before.Add(4 * 30 * 24 * time.Hour)) {
		t.Errorf("RefreshTokenExpiry = %s, expected >= 4mo from now", got.RefreshTokenExpiry)
	}
}

// TestGetUserAccessTokenRejectsInvalidPaseto covers the early-exit branch:
// a malformed pasetoToken must surface an error without hitting GitHub.
func TestGetUserAccessTokenRejectsInvalidPaseto(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}
	seedEncryptionKey(t)
	newLibTestDB(t)

	hits := 0
	restore := stubGitHubDoer(t, func(req *http.Request) (*http.Response, error) {
		hits++
		return nil, errors.New("should not be called")
	})
	defer restore()

	_, err := GetUserAccessToken("not-a-token", "code")
	if err == nil {
		t.Fatal("GetUserAccessToken accepted a garbage paseto token")
	}
	if hits != 0 {
		t.Fatalf("GetUserAccessToken reached GitHub despite bad paseto (hits=%d)", hits)
	}
}

// TestRefreshTokenHappyPath covers the refresh-token success branch: the
// refreshed Git credentials must surface with the expected fields and the
// GitHub payload must contain the decrypted refresh token under the
// refresh_token grant_type.
func TestRefreshTokenHappyPath(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}
	seedEncryptionKey(t)

	db := newLibTestDB(t)
	cidEnc, _ := EncryptSecret("cid")
	csecEnc, _ := EncryptSecret("csec")
	if err := db.Create(&models.GitSecret{ClientID: cidEnc, ClientSecret: csecEnc}).Error; err != nil {
		t.Fatalf("seed GitSecret: %v", err)
	}

	user := models.User{
		UUID:  uuid.NewString(),
		Email: "u@example.com",
		Git:   models.Git{RefreshToken: mustEncrypt(t, "the-refresh")},
	}

	restore := stubGitHubDoer(t, func(req *http.Request) (*http.Response, error) {
		body, _ := io.ReadAll(req.Body)
		var payload map[string]string
		if err := json.Unmarshal(body, &payload); err != nil {
			t.Fatalf("payload not JSON: %v", err)
		}
		if payload["grant_type"] != "refresh_token" {
			t.Errorf("grant_type = %q, want refresh_token", payload["grant_type"])
		}
		if payload["refresh_token"] != "the-refresh" {
			t.Errorf("refresh_token = %q, want the-refresh", payload["refresh_token"])
		}
		return jsonResponse(http.StatusOK, `{"access_token":"new-access","refresh_token":"new-ref"}`), nil
	})
	defer restore()

	got, err := refreshToken(user, "paseto-token-unused")
	if err != nil {
		t.Fatalf("refreshToken: %v", err)
	}
	if got.Token != "new-access" {
		t.Errorf("Token = %q, want new-access", got.Token)
	}
	if got.RefreshToken != "new-ref" {
		t.Errorf("RefreshToken = %q, want new-ref", got.RefreshToken)
	}
}

// TestRefreshTokenReportsGitHubError covers the GitHub-side error branch:
// when GitHub returns a 4xx, refreshToken must surface it as an error
// carrying the status code.
func TestRefreshTokenReportsGitHubError(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}
	seedEncryptionKey(t)

	db := newLibTestDB(t)
	cidEnc, _ := EncryptSecret("cid")
	csecEnc, _ := EncryptSecret("csec")
	if err := db.Create(&models.GitSecret{ClientID: cidEnc, ClientSecret: csecEnc}).Error; err != nil {
		t.Fatalf("seed GitSecret: %v", err)
	}

	user := models.User{
		UUID:  uuid.NewString(),
		Email: "u@example.com",
		Git:   models.Git{RefreshToken: mustEncrypt(t, "the-refresh")},
	}

	restore := stubGitHubDoer(t, func(req *http.Request) (*http.Response, error) {
		return jsonResponse(http.StatusBadRequest, `{"error":"bad refresh"}`), nil
	})
	defer restore()

	_, err := refreshToken(user, "paseto-token-unused")
	if err == nil {
		t.Fatal("refreshToken accepted a 400; GitHub error is being swallowed")
	}
	if !strings.Contains(err.Error(), "400") {
		t.Fatalf("error %q does not mention status 400", err.Error())
	}
}

// TestRefreshTokensIteratesExpiredUsers covers the loop branch:
// refreshTokens must call refreshToken for every user whose access token
// is expired and update the user row with the new credentials.
func TestRefreshTokensIteratesExpiredUsers(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}
	seedEncryptionKey(t)

	db := newLibTestDB(t)

	// refreshToken → models.DB.First(&secrets) → DecryptSecret(secrets.ClientID);
	// if no GitSecret row exists, First returns a zero-value struct and the
	// decrypt fails with "ciphertext too short". Seed the row alongside the
	// users.
	cidEnc, _ := EncryptSecret("cid")
	csecEnc, _ := EncryptSecret("csec")
	if err := db.Create(&models.GitSecret{ClientID: cidEnc, ClientSecret: csecEnc}).Error; err != nil {
		t.Fatalf("seed GitSecret: %v", err)
	}

	expired := models.User{
		UUID: "expired-uid", Email: "exp@example.com",
		Git: models.Git{
			RefreshToken: mustEncrypt(t, "old-refresh"),
			TokenExpiry:  time.Now().Add(-time.Hour),
		},
	}
	fresh := models.User{
		UUID: "fresh-uid", Email: "fresh@example.com",
		Git: models.Git{
			RefreshToken: mustEncrypt(t, "untouched-refresh"),
			TokenExpiry:  time.Now().Add(time.Hour),
		},
	}
	if err := db.Create(&expired).Error; err != nil {
		t.Fatalf("seed expired: %v", err)
	}
	if err := db.Create(&fresh).Error; err != nil {
		t.Fatalf("seed fresh: %v", err)
	}

	refreshedFor := make([]string, 0)
	restore := stubGitHubDoer(t, func(req *http.Request) (*http.Response, error) {
		body, _ := io.ReadAll(req.Body)
		var payload map[string]string
		_ = json.Unmarshal(body, &payload)
		refreshedFor = append(refreshedFor, payload["refresh_token"])
		return jsonResponse(http.StatusOK, `{"access_token":"new-acc","refresh_token":"new-ref"}`), nil
	})
	defer restore()

	refreshTokens()

	if len(refreshedFor) != 1 {
		t.Fatalf("refreshTokens called GitHub %d times, want exactly 1 (only the expired user)", len(refreshedFor))
	}
	if refreshedFor[0] != "old-refresh" {
		t.Errorf("refreshTokens refreshed %q, want old-refresh", refreshedFor[0])
	}

	var reloadedExpired models.User
	if err := db.Where("uuid = ?", "expired-uid").First(&reloadedExpired).Error; err != nil {
		t.Fatalf("reload expired: %v", err)
	}
	newRefreshPlain, err := DecryptSecret(reloadedExpired.Git.RefreshToken)
	if err != nil {
		t.Fatalf("decrypt refreshed refresh token: %v", err)
	}
	if newRefreshPlain != "new-ref" {
		t.Errorf("refreshed refresh token = %q, want new-ref", newRefreshPlain)
	}

	var reloadedFresh models.User
	if err := db.Where("uuid = ?", "fresh-uid").First(&reloadedFresh).Error; err != nil {
		t.Fatalf("reload fresh: %v", err)
	}
	freshRefreshPlain, err := DecryptSecret(reloadedFresh.Git.RefreshToken)
	if err != nil {
		t.Fatalf("decrypt fresh refresh token: %v", err)
	}
	if freshRefreshPlain != "untouched-refresh" {
		t.Errorf("fresh user refresh token = %q, want untouched-refresh (was incorrectly refreshed)", freshRefreshPlain)
	}
}

// TestStartTokenRefreshJobInvokesRefreshTokens covers the kickoff branch:
// StartTokenRefreshJob's first action is a synchronous refreshTokens call
// before the ticker starts. StartTokenRefreshJob blocks forever, so we
// run it in a goroutine and exit once we see the first refresh hit.
func TestStartTokenRefreshJobInvokesRefreshTokens(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}
	seedEncryptionKey(t)

	db := newLibTestDB(t)
	if err := db.Create(&models.User{
		UUID: "u-1", Email: "u@example.com",
		Git: models.Git{
			RefreshToken: mustEncrypt(t, "the-refresh"),
			TokenExpiry:  time.Now().Add(-time.Hour),
		},
	}).Error; err != nil {
		t.Fatalf("seed user: %v", err)
	}

	cidEnc, _ := EncryptSecret("cid")
	csecEnc, _ := EncryptSecret("csec")
	if err := db.Create(&models.GitSecret{ClientID: cidEnc, ClientSecret: csecEnc}).Error; err != nil {
		t.Fatalf("seed GitSecret: %v", err)
	}

	hits := int64(0)
	restore := stubGitHubDoer(t, func(req *http.Request) (*http.Response, error) {
		atomic.AddInt64(&hits, 1)
		return jsonResponse(http.StatusOK, `{"access_token":"a","refresh_token":"r"}`), nil
	})
	defer restore()

	// StartTokenRefreshJob blocks forever; run it with a stop channel and shut
	// it down before newLibTestDB's cleanup swaps models.DB back — otherwise
	// the background refresh goroutine races the fixture teardown (DATA RACE
	// under -race, caught by the release pipeline 2026-10-11). This cleanup is
	// registered after newLibTestDB's, so LIFO ordering runs it first and <-done
	// guarantees the goroutine finished its in-flight refreshTokens.
	stop := make(chan struct{})
	done := make(chan struct{})
	go func() {
		defer close(done)
		StartTokenRefreshJob(stop)
	}()
	t.Cleanup(func() {
		close(stop)
		<-done
	})

	deadline := time.Now().Add(2 * time.Second)
	for time.Now().Before(deadline) {
		if atomic.LoadInt64(&hits) >= 1 {
			break
		}
		time.Sleep(20 * time.Millisecond)
	}

	if atomic.LoadInt64(&hits) < 1 {
		t.Fatal("StartTokenRefreshJob did not invoke refreshTokens synchronously; first-run refresh is missing")
	}
	// The registered cleanup above stops the job and waits for it to exit
	// before the DB fixture is restored.
}

// keep "strconv" imported so a future refactor can use strconv.Itoa
// instead of the manual itoa below without touching the import block.
var _ = strconv.Itoa
