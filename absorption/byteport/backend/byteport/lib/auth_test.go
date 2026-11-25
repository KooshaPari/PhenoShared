package lib

import (
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
	"time"

	"byteport/models"

	"aidanwoods.dev/go-paseto"
	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/zalando/go-keyring"
)

// seedTokenKey plants a symmetric PASETO key under (tokenKeyService,
// keyringUser) so GenerateToken/ValidateToken can round-trip without going
// through the env-key bootstrap.
func seedTokenKey(t *testing.T, keyHex string) {
	t.Helper()
	if err := keyring.Set(tokenKeyService, keyringUser, keyHex); err != nil {
		t.Fatalf("seed token key: %v", err)
	}
}

// TestKeyringGetReadsValue covers the happy path of keyringGet: with the
// mock backend active, the function must surface what the underlying
// keyring returns rather than timing out.
func TestKeyringGetReadsValue(t *testing.T) {
	resetMockKeyring(t)

	if err := keyring.Set("svc", "u", "the-secret"); err != nil {
		t.Fatalf("seed: %v", err)
	}

	got, err := keyringGet("svc", "u")
	if err != nil {
		t.Fatalf("keyringGet: %v", err)
	}
	if got != "the-secret" {
		t.Fatalf("got %q, want the-secret", got)
	}
}

// TestKeyringGetReportsMissing covers the not-found branch: when the mock
// backend has no entry, keyringGet must surface a not-found error rather
// than swallowing it.
func TestKeyringGetReportsMissing(t *testing.T) {
	resetMockKeyring(t)

	_, err := keyringGet("does-not-exist", "nope")
	if err == nil {
		t.Fatal("expected error from keyringGet, got nil")
	}
}

// TestKeyringSetStoresValue covers the happy path of keyringSet: the value
// must be readable immediately afterward through the same backend.
func TestKeyringSetStoresValue(t *testing.T) {
	resetMockKeyring(t)

	if err := keyringSet("svc", "u", "round-trip"); err != nil {
		t.Fatalf("keyringSet: %v", err)
	}
	got, err := keyring.Get("svc", "u")
	if err != nil {
		t.Fatalf("keyring.Get: %v", err)
	}
	if got != "round-trip" {
		t.Fatalf("got %q, want round-trip", got)
	}
}

// TestGetSymmetricKeyDelegatesToKeyring verifies that getSymmetricKey is a
// thin pass-through to keyringGet(tokenKeyService, keyringUser).
func TestGetSymmetricKeyDelegatesToKeyring(t *testing.T) {
	resetMockKeyring(t)
	want := "deadbeefcafebabe"
	seedTokenKey(t, want)

	got, err := getSymmetricKey()
	if err != nil {
		t.Fatalf("getSymmetricKey: %v", err)
	}
	if got != want {
		t.Fatalf("got %q, want %q", got, want)
	}
}

// TestEnsureKeyExistsCreatesWhenMissing covers the generation branch: when
// keyringGet reports no entry, ensureKeyExists must mint a fresh key via
// generateSymmetricKey and persist it.
func TestEnsureKeyExistsCreatesWhenMissing(t *testing.T) {
	resetMockKeyring(t)

	if err := ensureKeyExists("svc-create", "u"); err != nil {
		t.Fatalf("ensureKeyExists: %v", err)
	}

	got, err := keyring.Get("svc-create", "u")
	if err != nil {
		t.Fatalf("keyring.Get: %v", err)
	}
	if len(got) != 64 {
		t.Fatalf("key length = %d, want 64 hex chars", len(got))
	}
}

// TestEnsureKeyExistsReusesExisting covers the idempotency branch: when the
// key already exists, ensureKeyExists must NOT replace it.
func TestEnsureKeyExistsReusesExisting(t *testing.T) {
	resetMockKeyring(t)
	want := "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
	if len(want) != 64 {
		t.Fatalf("seed value length = %d, want 64 hex chars", len(want))
	}
	if err := keyring.Set("svc-keep", "u", want); err != nil {
		t.Fatalf("seed: %v", err)
	}

	if err := ensureKeyExists("svc-keep", "u"); err != nil {
		t.Fatalf("ensureKeyExists: %v", err)
	}

	got, err := keyring.Get("svc-keep", "u")
	if err != nil {
		t.Fatalf("keyring.Get: %v", err)
	}
	if got != want {
		t.Fatalf("ensureKeyExists replaced the existing key: got %q, want %q", got, want)
	}
}

// TestEnsureKeyExistsServiceKeyAlsoSetsEnv covers the service-key branch:
// when the service argument matches serviceKeyService, ensureKeyExists must
// also publish the freshly generated key to the SERVICE_KEY env var so the
// NVMS sandbox can pick it up.
func TestEnsureKeyExistsServiceKeyAlsoSetsEnv(t *testing.T) {
	resetMockKeyring(t)
	t.Setenv("SERVICE_KEY", "")

	if err := ensureKeyExists(serviceKeyService, keyringUser); err != nil {
		t.Fatalf("ensureKeyExists: %v", err)
	}

	envVal := os.Getenv("SERVICE_KEY")
	if envVal == "" {
		t.Fatal("SERVICE_KEY env var was not set by ensureKeyExists")
	}

	ringVal, err := keyring.Get(serviceKeyService, keyringUser)
	if err != nil {
		t.Fatalf("keyring.Get: %v", err)
	}
	if envVal != ringVal {
		t.Fatalf("SERVICE_KEY=%q does not match keyring value %q", envVal, ringVal)
	}
}

// TestInitAuthSystemCreatesAllThreeKeys covers the success path of
// InitAuthSystem: with a fresh keyring, it must populate all three services
// (token, secrets, NVMS) without error.
func TestInitAuthSystemCreatesAllThreeKeys(t *testing.T) {
	resetMockKeyring(t)
	t.Setenv("SERVICE_KEY", "")

	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}

	for _, svc := range []string{tokenKeyService, secretsKeyService, serviceKeyService} {
		v, err := keyring.Get(svc, keyringUser)
		if err != nil {
			t.Fatalf("keyring.Get(%s): %v", svc, err)
		}
		if len(v) != 64 {
			t.Fatalf("key for %s has length %d, want 64 hex chars", svc, len(v))
		}
	}

	if os.Getenv("SERVICE_KEY") == "" {
		t.Fatal("InitAuthSystem did not set SERVICE_KEY env var")
	}
}

// TestInitAuthSystemIsIdempotent covers the second-call branch: once
// initialized, a second InitAuthSystem must preserve the existing keys.
func TestInitAuthSystemIsIdempotent(t *testing.T) {
	resetMockKeyring(t)
	t.Setenv("SERVICE_KEY", "")

	if err := InitAuthSystem(); err != nil {
		t.Fatalf("first InitAuthSystem: %v", err)
	}

	tok1, _ := keyring.Get(tokenKeyService, keyringUser)
	sec1, _ := keyring.Get(secretsKeyService, keyringUser)
	svc1, _ := keyring.Get(serviceKeyService, keyringUser)

	if err := InitAuthSystem(); err != nil {
		t.Fatalf("second InitAuthSystem: %v", err)
	}

	tok2, _ := keyring.Get(tokenKeyService, keyringUser)
	sec2, _ := keyring.Get(secretsKeyService, keyringUser)
	svc2, _ := keyring.Get(serviceKeyService, keyringUser)

	if tok1 != tok2 || sec1 != sec2 || svc1 != svc2 {
		t.Fatalf("InitAuthSystem replaced existing keys on second call")
	}
}

// TestGenerateSymmetricKeyProducesHexOfCorrectLength covers the only behavior
// of generateSymmetricKey that callers care about: a 64-character hex string
// consumable by paseto.V4SymmetricKeyFromHex. Output is also non-deterministic.
func TestGenerateSymmetricKeyProducesHexOfCorrectLength(t *testing.T) {
	k1 := generateSymmetricKey()
	if len(k1) != 64 {
		t.Fatalf("key length = %d, want 64", len(k1))
	}
	// Round-trip through PASETO to confirm the format is valid.
	if _, err := paseto.V4SymmetricKeyFromHex(k1); err != nil {
		t.Fatalf("V4SymmetricKeyFromHex(%q): %v", k1, err)
	}

	k2 := generateSymmetricKey()
	if k1 == k2 {
		t.Fatal("generateSymmetricKey returned the same value twice; entropy is broken")
	}
}

// TestGenerateTokenAndValidateRoundTrip covers the full happy path: a token
// minted with GenerateToken must be accepted by ValidateToken, and the
// "user-id" claim must round-trip exactly.
func TestGenerateTokenAndValidateRoundTrip(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}

	user := models.User{UUID: uuid.NewString(), Email: "round-trip@example.com"}
	tok, err := GenerateToken(user)
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}
	if tok == "" {
		t.Fatal("GenerateToken returned empty string")
	}

	valid, parsed, err := ValidateToken(tok)
	if err != nil {
		t.Fatalf("ValidateToken: %v", err)
	}
	if !valid {
		t.Fatal("ValidateToken returned valid=false")
	}
	if parsed == nil {
		t.Fatal("ValidateToken returned nil token")
	}

	gotID, err := parsed.GetString("user-id")
	if err != nil {
		t.Fatalf("GetString user-id: %v", err)
	}
	if gotID != user.UUID {
		t.Fatalf("user-id claim = %q, want %q", gotID, user.UUID)
	}
}

// TestValidateTokenRejectsGarbage covers the rejection branch: a string that
// is not a valid PASETO token must surface an error.
func TestValidateTokenRejectsGarbage(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}

	valid, tok, err := ValidateToken("not-a-token")
	if err == nil {
		t.Fatal("ValidateToken(garbage) returned nil error")
	}
	if valid {
		t.Fatal("ValidateToken(garbage) returned valid=true")
	}
	if tok != nil {
		t.Fatal("ValidateToken(garbage) returned non-nil token")
	}
}

// TestGenerateNVMSTokenAndValidateServiceRoundTrip covers the NVMS branch:
// service tokens carry both user-id and project-id claims and use the
// serviceKeyService audience.
func TestGenerateNVMSTokenAndValidateServiceRoundTrip(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}

	project := models.Project{
		UUID:  uuid.NewString(),
		Name:  "test-project",
		Owner: "user-1",
		User:  models.User{UUID: "user-1", Email: "owner@example.com"},
	}
	tok, err := GenerateNVMSToken(project)
	if err != nil {
		t.Fatalf("GenerateNVMSToken: %v", err)
	}

	valid, parsed, err := ValidateServiceToken(tok)
	if err != nil {
		t.Fatalf("ValidateServiceToken: %v", err)
	}
	if !valid {
		t.Fatal("ValidateServiceToken returned valid=false")
	}

	uid, err := parsed.GetString("user-id")
	if err != nil {
		t.Fatalf("GetString user-id: %v", err)
	}
	if uid != project.User.UUID {
		t.Fatalf("user-id claim = %q, want %q", uid, project.User.UUID)
	}
	pid, err := parsed.GetString("project-id")
	if err != nil {
		t.Fatalf("GetString project-id: %v", err)
	}
	if pid != project.UUID {
		t.Fatalf("project-id claim = %q, want %q", pid, project.UUID)
	}
}

// TestValidateServiceTokenRejectsSessionToken covers cross-audience rejection:
// a session token (audience = user email) must fail ValidateServiceToken
// (audience = serviceKeyService).
func TestValidateServiceTokenRejectsSessionToken(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}

	user := models.User{UUID: "u", Email: "u@example.com"}
	sessionTok, err := GenerateToken(user)
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	valid, _, err := ValidateServiceToken(sessionTok)
	if err == nil {
		t.Fatal("ValidateServiceToken accepted a session token: cross-audience check is missing")
	}
	if valid {
		t.Fatal("ValidateServiceToken returned valid=true for a session token")
	}
}

// TestGenerateTokenReturnsErrorWhenKeyUnavailable covers the error path that
// replaced log.Fatal: a missing keyring entry must be returned to the caller.
func TestGenerateTokenReturnsErrorWhenKeyUnavailable(t *testing.T) {
	resetMockKeyring(t) // empty keyring

	tok, err := GenerateToken(models.User{UUID: uuid.NewString(), Email: "x@example.com"})
	if err == nil {
		t.Fatalf("GenerateToken returned token %q with no key available", tok)
	}
	if tok != "" {
		t.Fatalf("GenerateToken returned token %q alongside error %v", tok, err)
	}
}

// TestGenerateNVMSTokenReturnsErrorWhenKeyUnavailable is the service-token
// twin of TestGenerateTokenReturnsErrorWhenKeyUnavailable.
func TestGenerateNVMSTokenReturnsErrorWhenKeyUnavailable(t *testing.T) {
	resetMockKeyring(t) // empty keyring

	project := models.Project{
		UUID: uuid.NewString(),
		User: models.User{UUID: uuid.NewString()},
	}
	tok, err := GenerateNVMSToken(project)
	if err == nil {
		t.Fatalf("GenerateNVMSToken returned token %q with no key available", tok)
	}
	if tok != "" {
		t.Fatalf("GenerateNVMSToken returned token %q alongside error %v", tok, err)
	}
}

// TestAuthenticateRequestMissingUserIDClaimReturnsError covers the claim
// extraction path: a structurally valid but claim-deficient token must be
// rejected with an error rather than terminating the process.
func TestAuthenticateRequestMissingUserIDClaimReturnsError(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}
	newLibTestDB(t) // empty DB

	keyHex, err := keyring.Get(tokenKeyService, keyringUser)
	if err != nil {
		t.Fatalf("keyring.Get: %v", err)
	}
	key, err := paseto.V4SymmetricKeyFromHex(keyHex)
	if err != nil {
		t.Fatalf("V4SymmetricKeyFromHex: %v", err)
	}
	tok := paseto.NewToken()
	tok.SetIssuer("BytePort")
	tok.SetExpiration(time.Now().Add(time.Minute))
	tok.SetIssuedAt(time.Now())
	tok.SetNotBefore(time.Now())
	signed := tok.V4Encrypt(key, nil)

	user, err := AuthenticateRequest(signed)
	if err == nil {
		t.Fatalf("AuthenticateRequest accepted a token with no user-id claim: %+v", user)
	}
	if user != nil {
		t.Fatalf("AuthenticateRequest returned a user alongside error: %+v", user)
	}
}

// TestAuthenticateRequestReturnsUserFromDB covers the happy path:
// ValidateToken succeeds AND the user-id claim resolves to a row in the
// database. The returned user must have its password cleared.
func TestAuthenticateRequestReturnsUserFromDB(t *testing.T) {
	_, user, tok := seedUserWithToken(t, "auth@example.com", "Auth", "secret-hash")

	got, err := AuthenticateRequest(tok)
	if err != nil {
		t.Fatalf("AuthenticateRequest: %v", err)
	}
	if got == nil {
		t.Fatal("AuthenticateRequest returned nil user")
	}
	if got.UUID != user.UUID {
		t.Fatalf("UUID = %q, want %q", got.UUID, user.UUID)
	}
	if got.Password != "" {
		t.Fatalf("Password = %q, want empty (sensitive field leaked)", got.Password)
	}
}

// TestAuthenticateRequestRejectsInvalidToken covers the rejection branch.
func TestAuthenticateRequestRejectsInvalidToken(t *testing.T) {
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}
	newLibTestDB(t) // empty DB

	_, err := AuthenticateRequest("not-a-token")
	if err == nil {
		t.Fatal("AuthenticateRequest accepted garbage; token validation is bypassed")
	}
}

// TestAuthMiddlewareRejectsMissingCookie covers the first branch of
// AuthMiddleware: when the authToken cookie is absent, the handler must
// respond 401 with "Authorization header missing" and abort the chain.
func TestAuthMiddlewareRejectsMissingCookie(t *testing.T) {
	gin.SetMode(gin.TestMode)
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}

	r := gin.New()
	r.Use(AuthMiddleware())
	r.GET("/protected", func(c *gin.Context) {
		t.Fatal("handler ran despite missing cookie")
	})

	w := httptest.NewRecorder()
	r.ServeHTTP(w, httptest.NewRequest(http.MethodGet, "/protected", nil))

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401 (body %s)", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "Authorization header missing") {
		t.Fatalf("body = %q, want it to mention Authorization header missing", w.Body.String())
	}
}

// TestAuthMiddlewareRejectsInvalidBearer covers the parse-failure branch:
// when the cookie carries an unparseable token, AuthMiddleware must respond
// 401 with "Invalid or expired token".
func TestAuthMiddlewareRejectsInvalidBearer(t *testing.T) {
	gin.SetMode(gin.TestMode)
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}

	r := gin.New()
	r.Use(AuthMiddleware())
	r.GET("/protected", func(c *gin.Context) {
		t.Fatal("handler ran despite invalid bearer")
	})

	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.AddCookie(&http.Cookie{Name: "authToken", Value: "garbage"})
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401 (body %s)", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "Invalid or expired token") {
		t.Fatalf("body = %q, want it to mention invalid/expired token", w.Body.String())
	}
}

// TestAuthMiddlewareStripsBearerPrefix covers the prefix-tolerance branch:
// AuthMiddleware calls strings.TrimPrefix(authToken, "Bearer ") so a token
// submitted as "Bearer <token>" is treated the same as "<token>".
func TestAuthMiddlewareStripsBearerPrefix(t *testing.T) {
	gin.SetMode(gin.TestMode)
	_, _, tok := seedUserWithToken(t, "bearer@example.com", "Bearer", "x")

	var hit bool
	r := gin.New()
	r.Use(AuthMiddleware())
	r.GET("/protected", func(c *gin.Context) {
		hit = true
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.AddCookie(&http.Cookie{Name: "authToken", Value: "Bearer " + tok})
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body %s)", w.Code, w.Body.String())
	}
	if !hit {
		t.Fatal("protected handler did not run; Bearer-prefix stripping is broken")
	}
}

// TestAuthMiddlewareRejectsTokenForMissingUser covers the user-not-found
// branch: the token validates, but the user-id claim does not resolve to a
// row.
func TestAuthMiddlewareRejectsTokenForMissingUser(t *testing.T) {
	gin.SetMode(gin.TestMode)
	resetMockKeyring(t)
	if err := InitAuthSystem(); err != nil {
		t.Fatalf("InitAuthSystem: %v", err)
	}
	newLibTestDB(t) // empty DB

	user := models.User{UUID: "ghost", Email: "ghost@example.com"}
	tok, err := GenerateToken(user)
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	r := gin.New()
	r.Use(AuthMiddleware())
	r.GET("/protected", func(c *gin.Context) {
		t.Fatal("handler ran despite missing user row")
	})

	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.AddCookie(&http.Cookie{Name: "authToken", Value: tok})
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401 (body %s)", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "User not found") {
		t.Fatalf("body = %q, want it to mention User not found", w.Body.String())
	}
}

// TestAuthMiddlewareSetsUserOnHappyPath covers the success branch
// end-to-end: a valid cookie + a valid token + a real user row must yield
// a 200 and the user must be retrievable from the gin context under the
// "user" key.
func TestAuthMiddlewareSetsUserOnHappyPath(t *testing.T) {
	gin.SetMode(gin.TestMode)
	_, user, tok := seedUserWithToken(t, "happy@example.com", "Happy", "x")

	var got models.User
	r := gin.New()
	r.Use(AuthMiddleware())
	r.GET("/protected", func(c *gin.Context) {
		v, ok := c.Get("user")
		if !ok {
			t.Fatal("user not set in context")
		}
		got = v.(models.User)
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})

	req := httptest.NewRequest(http.MethodGet, "/protected", nil)
	req.AddCookie(&http.Cookie{Name: "authToken", Value: tok})
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body %s)", w.Code, w.Body.String())
	}
	if got.UUID != user.UUID {
		t.Fatalf("context user UUID = %q, want %q", got.UUID, user.UUID)
	}
}
