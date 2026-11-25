package routes

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"byteport/lib"
	"byteport/models"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// authTestRouter returns a gin engine with /login, /signup, /authenticate, and
// /current routes. We deliberately keep setup minimal: most auth helpers need
// only a gin context with optional request bodies and branch on validation
// before any database call. Tests that need DB-seeded users, cookie context,
// or per-route custom handlers (UpdateUser, LinkHandler, UpdateLink) build
// their own engine inline rather than going through this helper.
func authTestRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.POST("/signup", Signup)
	r.POST("/login", Login)
	r.GET("/authenticate", Authenticate)
	r.GET("/current", func(c *gin.Context) {
		if _, ok := currentUser(c); !ok {
			return
		}
		c.JSON(http.StatusOK, gin.H{"ok": true})
	})
	return r
}

// ----- currentUser -----

// TestCurrentUserMissing verifies that currentUser returns false and writes a
// 401 JSON body when no "user" key is in the gin context.
func TestCurrentUserMissing(t *testing.T) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/current", nil)

	user, ok := currentUser(c)
	if ok {
		t.Fatalf("ok = true, want false")
	}
	if user.UUID != "" { // zero-value user returned
		t.Errorf("user = %+v, want zero value", user)
	}
	if w.Code != http.StatusUnauthorized {
		t.Errorf("status = %d, want 401", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Unauthorized") {
		t.Errorf("body = %q, want to contain Unauthorized", w.Body.String())
	}
}

// TestCurrentUserWrongType verifies that currentUser returns false and writes
// a 500 JSON body when the "user" value is not a models.User.
func TestCurrentUserWrongType(t *testing.T) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/current", nil)
	c.Set("user", "not-a-user-struct")

	if _, ok := currentUser(c); ok {
		t.Fatal("ok = true, want false on wrong type")
	}
	if w.Code != http.StatusInternalServerError {
		t.Errorf("status = %d, want 500", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Invalid user context") {
		t.Errorf("body = %q, want to contain 'Invalid user context'", w.Body.String())
	}
}

// TestCurrentUserHappyPath verifies the success branch: when the context
// carries a models.User, currentUser returns true and writes nothing.
func TestCurrentUserHappyPath(t *testing.T) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/current", nil)
	want := models.User{UUID: "u-1", Email: "u@example.com"}
	c.Set("user", want)

	got, ok := currentUser(c)
	if !ok {
		t.Fatal("ok = false, want true")
	}
	if got.UUID != want.UUID || got.Email != want.Email {
		t.Errorf("user = %+v, want %+v", got, want)
	}
	if w.Body.Len() != 0 {
		t.Errorf("body = %q, want empty (no error response written)", w.Body.String())
	}
}

// ----- setAuthCookie -----

// TestSetAuthCookieWritesCookie verifies that setAuthCookie sets the authToken
// cookie with the requested value, the documented SameSite=Lax mode, and the
// secure/httpOnly flags.
func TestSetAuthCookieWritesCookie(t *testing.T) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodGet, "/", nil)
	c.Request.Host = "example.test"

	setAuthCookie(c, "token-abc-123")

	cookies := w.Result().Cookies()
	if len(cookies) != 1 {
		t.Fatalf("got %d cookies, want 1", len(cookies))
	}
	got := cookies[0]
	if got.Name != "authToken" {
		t.Errorf("name = %q, want authToken", got.Name)
	}
	if got.Value != "token-abc-123" {
		t.Errorf("value = %q, want token-abc-123", got.Value)
	}
	if got.Path != "/" {
		t.Errorf("path = %q, want /", got.Path)
	}
	if !got.Secure {
		t.Error("secure = false, want true")
	}
	if !got.HttpOnly {
		t.Error("httpOnly = false, want true")
	}
	if got.SameSite != http.SameSiteLaxMode {
		t.Errorf("SameSite = %d, want %d (Lax)", got.SameSite, http.SameSiteLaxMode)
	}
}

// ----- Login -----

// TestLoginHappyPath covers the success branch: a known user with the right
// password gets back a 200, the authToken cookie is set, and the response
// body lists the user with the password field cleared.
func TestLoginHappyPath(t *testing.T) {
	db := setupAuthDB(t)
	hashed, err := lib.EncryptPass("hunter2")
	if err != nil {
		t.Fatalf("EncryptPass: %v", err)
	}
	user := models.User{
		UUID:     uuid.NewString(),
		Email:    "login@example.com",
		Name:     "Login",
		Password: string(hashed),
	}
	if err := db.Create(&user).Error; err != nil {
		t.Fatalf("seed user: %v", err)
	}

	r := gin.New()
	r.POST("/login", Login)
	body := `{"email":"login@example.com","password":"hunter2"}`
	req := httptest.NewRequest(http.MethodPost, "/login", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body %s)", w.Code, w.Body.String())
	}
	cookies := w.Result().Cookies()
	if len(cookies) == 0 || cookies[0].Name != "authToken" {
		t.Fatalf("expected authToken cookie, got %v", cookies)
	}
	if cookies[0].Value == "" {
		t.Fatal("authToken cookie value is empty")
	}

	var resp map[string]any
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("response not JSON: %v", err)
	}
	if resp["message"] != "Success" {
		t.Errorf("message = %v, want Success", resp["message"])
	}
	u, ok := resp["user"].(map[string]any)
	if !ok {
		t.Fatalf("user field missing or wrong type: %v", resp["user"])
	}
	if u["password"] != "" && u["password"] != nil {
		t.Errorf("password = %v, want empty (cleared before response)", u["password"])
	}
}

// TestLoginUnknownEmail covers the not-found branch: an email that is not in
// the database must produce a 401, NOT a 500. We previously crashed here
// when the query returned ErrRecordNotFound without a type assertion.
func TestLoginUnknownEmail(t *testing.T) {
	gin.SetMode(gin.TestMode)
	resetMockKeyring(t)
	seedAuthSystem(t)
	newRouteTestDB(t)

	r := gin.New()
	r.POST("/login", Login)
	body := `{"email":"nobody@example.com","password":"x"}`
	req := httptest.NewRequest(http.MethodPost, "/login", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401 (body %s)", w.Code, w.Body.String())
	}
}

// TestLoginWrongPassword covers the bad-credentials branch: the user
// exists but the password does not match. Login must respond 401.
func TestLoginWrongPassword(t *testing.T) {
	db := setupAuthDB(t)
	hashed, err := lib.EncryptPass("right")
	if err != nil {
		t.Fatalf("EncryptPass: %v", err)
	}
	user := models.User{
		UUID:     uuid.NewString(),
		Email:    "wrong@example.com",
		Name:     "Wrong",
		Password: string(hashed),
	}
	if err := db.Create(&user).Error; err != nil {
		t.Fatalf("seed: %v", err)
	}

	r := gin.New()
	r.POST("/login", Login)
	body := `{"email":"wrong@example.com","password":"wrong"}`
	req := httptest.NewRequest(http.MethodPost, "/login", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401 (body %s)", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "invalid credentials") {
		t.Errorf("body = %q, want it to mention invalid credentials", w.Body.String())
	}
}

// TestLoginRejectsNonJSONBody verifies the body-binding error branch.
func TestLoginRejectsNonJSONBody(t *testing.T) {
	r := authTestRouter()
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/login", bytes.NewBufferString("not-json"))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want 400", w.Code)
	}
}

// ----- Signup -----

// TestSignupHappyPath covers the success branch: a new user with valid
// credentials must be persisted with a hashed password (NOT the plaintext),
// receive an authToken cookie, and return 201.
func TestSignupHappyPath(t *testing.T) {
	db := setupAuthDB(t)

	r := gin.New()
	r.POST("/signup", Signup)
	body := `{"name":"New","email":"new@example.com","password":"hunter2"}`
	req := httptest.NewRequest(http.MethodPost, "/signup", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusCreated {
		t.Fatalf("status = %d, want 201 (body %s)", w.Code, w.Body.String())
	}
	cookies := w.Result().Cookies()
	if len(cookies) == 0 || cookies[0].Name != "authToken" {
		t.Fatalf("expected authToken cookie, got %v", cookies)
	}

	var stored models.User
	if err := db.Where("email = ?", "new@example.com").First(&stored).Error; err != nil {
		t.Fatalf("user not persisted: %v", err)
	}
	if stored.UUID == "" {
		t.Error("UUID was not generated")
	}
	if stored.Password == "hunter2" {
		t.Error("password stored in plaintext (must be hashed)")
	}
	if stored.Password == "" {
		t.Error("password was not set")
	}
	matched, err := lib.ValidatePass("hunter2", stored.Password)
	if err != nil {
		t.Fatalf("ValidatePass: %v", err)
	}
	if !matched {
		t.Error("stored password does not verify against the supplied plaintext")
	}
}

// TestSignupDuplicateEmail covers the duplicate branch: a Signup request
// with an email that already exists must produce 409 Conflict.
func TestSignupDuplicateEmail(t *testing.T) {
	db := setupAuthDB(t)
	hashed, err := lib.EncryptPass("anything")
	if err != nil {
		t.Fatalf("EncryptPass: %v", err)
	}
	existing := models.User{
		UUID:     uuid.NewString(),
		Email:    "dupe@example.com",
		Name:     "Existing",
		Password: string(hashed),
	}
	if err := db.Create(&existing).Error; err != nil {
		t.Fatalf("seed: %v", err)
	}

	r := gin.New()
	r.POST("/signup", Signup)
	body := `{"name":"Other","email":"dupe@example.com","password":"hunter2"}`
	req := httptest.NewRequest(http.MethodPost, "/signup", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusConflict {
		t.Fatalf("status = %d, want 409 (body %s)", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "Already Exists") {
		t.Errorf("body = %q, want it to mention User Already Exists", w.Body.String())
	}

	// And the duplicate must NOT have created a second row.
	var n int64
	if err := db.Model(&models.User{}).Where("email = ?", "dupe@example.com").Count(&n).Error; err != nil {
		t.Fatalf("count: %v", err)
	}
	if n != 1 {
		t.Errorf("rows for dupe@example.com = %d, want exactly 1 (a second row was created)", n)
	}
}

// TestSignupRejectsNonJSONBody verifies the body-binding error branch.
func TestSignupRejectsNonJSONBody(t *testing.T) {
	r := authTestRouter()
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodPost, "/signup", bytes.NewBufferString("not-json"))
	req.Header.Set("Content-Type", "application/json")
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Errorf("status = %d, want 400", w.Code)
	}
}

// ----- Authenticate -----

// TestAuthenticateHappyPath covers the success branch: when the cookie
// carries a valid token that resolves to a real user, Authenticate must
// respond 200 and put the user in the context.
func TestAuthenticateHappyPath(t *testing.T) {
	db := setupAuthDB(t)
	user := models.User{
		UUID:     uuid.NewString(),
		Email:    "auth@example.com",
		Name:     "Auth",
		Password: "x",
	}
	if err := db.Create(&user).Error; err != nil {
		t.Fatalf("seed: %v", err)
	}

	tok, err := lib.GenerateToken(user)
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	r := gin.New()
	r.GET("/authenticate", Authenticate)
	req := httptest.NewRequest(http.MethodGet, "/authenticate", nil)
	req.AddCookie(&http.Cookie{Name: "authToken", Value: tok})
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body %s)", w.Code, w.Body.String())
	}
	var resp map[string]any
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("response not JSON: %v", err)
	}
	if resp["message"] != "Success" {
		t.Errorf("message = %v, want Success", resp["message"])
	}
	u, ok := resp["User"].(map[string]any)
	if !ok {
		t.Fatalf("User field missing or wrong type: %v", resp["User"])
	}
	if u["uuid"] != user.UUID {
		t.Errorf("uuid = %v, want %s", u["uuid"], user.UUID)
	}
}

// TestAuthenticateInvalidToken covers the rejection branch: a cookie
// carrying a garbage token must surface 401.
func TestAuthenticateInvalidToken(t *testing.T) {
	gin.SetMode(gin.TestMode)
	resetMockKeyring(t)
	seedAuthSystem(t)
	newRouteTestDB(t)

	r := gin.New()
	r.GET("/authenticate", Authenticate)
	req := httptest.NewRequest(http.MethodGet, "/authenticate", nil)
	req.AddCookie(&http.Cookie{Name: "authToken", Value: "garbage"})
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401 (body %s)", w.Code, w.Body.String())
	}
}

// TestAuthenticateTokenForMissingUser covers the user-not-found branch:
// the token is valid but the user-id claim does not resolve to a row.
func TestAuthenticateTokenForMissingUser(t *testing.T) {
	gin.SetMode(gin.TestMode)
	resetMockKeyring(t)
	seedAuthSystem(t)
	newRouteTestDB(t) // empty DB

	user := models.User{UUID: "ghost", Email: "ghost@example.com"}
	tok, err := lib.GenerateToken(user)
	if err != nil {
		t.Fatalf("GenerateToken: %v", err)
	}

	r := gin.New()
	r.GET("/authenticate", Authenticate)
	req := httptest.NewRequest(http.MethodGet, "/authenticate", nil)
	req.AddCookie(&http.Cookie{Name: "authToken", Value: tok})
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want 401 (body %s)", w.Code, w.Body.String())
	}
}

// TestAuthenticateMissingCookie verifies the cookie-missing branch of the
// Authenticate handler (it returns 401 before any DB call).
func TestAuthenticateMissingCookie(t *testing.T) {
	r := authTestRouter()
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/authenticate", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Errorf("status = %d, want 401", w.Code)
	}
	if !strings.Contains(w.Body.String(), "Unauthorized") {
		t.Errorf("body = %q, want to contain Unauthorized", w.Body.String())
	}
}

// ----- UpdateUser -----

// TestUpdateUserHappyPath covers the success branch: a partial update (just
// name) must persist the change and return 200 with the updated user.
func TestUpdateUserHappyPath(t *testing.T) {
	db := setupAuthDB(t)
	user := models.User{
		UUID:     uuid.NewString(),
		Email:    "upd@example.com",
		Name:     "Original",
		Password: "x",
	}
	if err := db.Create(&user).Error; err != nil {
		t.Fatalf("seed: %v", err)
	}

	r := gin.New()
	r.PUT("/user", func(c *gin.Context) {
		c.Set("user", user)
		UpdateUser(c)
	})
	body := `{"name":"Updated","email":"new@example.com"}`
	req := httptest.NewRequest(http.MethodPut, "/user", strings.NewReader(body))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body %s)", w.Code, w.Body.String())
	}

	var reloaded models.User
	if err := db.Where("uuid = ?", user.UUID).First(&reloaded).Error; err != nil {
		t.Fatalf("reload: %v", err)
	}
	if reloaded.Name != "Updated" {
		t.Errorf("Name = %q, want Updated", reloaded.Name)
	}
	if reloaded.Email != "new@example.com" {
		t.Errorf("Email = %q, want new@example.com", reloaded.Email)
	}
}

// TestUpdateUserRejectsBadJSON covers the binding-error branch: malformed
// JSON must produce 400.
func TestUpdateUserRejectsBadJSON(t *testing.T) {
	gin.SetMode(gin.TestMode)
	resetMockKeyring(t)
	seedAuthSystem(t)
	newRouteTestDB(t)

	user := models.User{UUID: uuid.NewString(), Email: "u@example.com"}

	r := gin.New()
	r.PUT("/user", func(c *gin.Context) {
		c.Set("user", user)
		UpdateUser(c)
	})
	req := httptest.NewRequest(http.MethodPut, "/user", strings.NewReader("not-json"))
	req.Header.Set("Content-Type", "application/json")
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("status = %d, want 400 (body %s)", w.Code, w.Body.String())
	}
}

// ----- LinkHandler / UpdateLink -----

// TestLinkHandlerRedirectsToGitHub covers the success branch: when the
// auth context has a real user, LinkHandler must call LinkWithGithub and
// emit a 302 to github.com/login/oauth/authorize.
func TestLinkHandlerRedirectsToGitHub(t *testing.T) {
	db := setupAuthDB(t)
	clientIDPlain := "client-id-123"
	encrypted, err := lib.EncryptSecret(clientIDPlain)
	if err != nil {
		t.Fatalf("EncryptSecret: %v", err)
	}
	if err := db.Create(&models.GitSecret{ClientID: encrypted}).Error; err != nil {
		t.Fatalf("seed GitSecret: %v", err)
	}

	user := models.User{UUID: uuid.NewString(), Email: "link@example.com"}

	r := gin.New()
	r.GET("/link", func(c *gin.Context) {
		c.Set("user", user)
		LinkHandler(c)
	})
	req := httptest.NewRequest(http.MethodGet, "/link", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusFound {
		t.Fatalf("status = %d, want 302 (body %s)", w.Code, w.Body.String())
	}
	loc := w.Header().Get("Location")
	if !strings.HasPrefix(loc, "https://github.com/login/oauth/authorize") {
		t.Errorf("Location = %q, want it to redirect to GitHub", loc)
	}
}

// TestUpdateLinkLocalProviderNoDecrypt covers the "local" provider branch:
// when LLMConfig.Provider == "local", UpdateLink must skip the OpenAI
// decrypt and return the user with the credentials cleared.
//
// This is the path the UI hits when the user picks a local LLM and so has
// no provider entry in LLMConfig.Providers.
func TestUpdateLinkLocalProviderNoDecrypt(t *testing.T) {
	db := setupAuthDB(t)
	user := models.User{
		UUID:     uuid.NewString(),
		Email:    "local@example.com",
		Name:     "Local",
		Password: "x",
		LLMConfig: models.LLM{
			Provider: "local",
		},
		// Pre-encrypt the AWS + Portfolio fields so the decrypt succeeds.
		AwsCreds: models.AwsCreds{
			AccessKeyID:     mustEncrypt(t, "AKIA-test"),
			SecretAccessKey: mustEncrypt(t, "secret-test"),
		},
		Portfolio: models.Portfolio{
			RootEndpoint: mustEncrypt(t, "https://portfolio.example.com"),
			APIKey:       mustEncrypt(t, "portfolio-key"),
		},
	}
	if err := db.Create(&user).Error; err != nil {
		t.Fatalf("seed: %v", err)
	}

	r := gin.New()
	r.GET("/update-link", func(c *gin.Context) {
		c.Set("user", user)
		UpdateLink(c)
	})
	req := httptest.NewRequest(http.MethodGet, "/update-link", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200 (body %s)", w.Code, w.Body.String())
	}
	var resp models.User
	if err := json.Unmarshal(w.Body.Bytes(), &resp); err != nil {
		t.Fatalf("body not JSON: %v", err)
	}
	if resp.AwsCreds.AccessKeyID != "AKIA-test" {
		t.Errorf("AwsCreds.AccessKeyID = %q, want AKIA-test (was not decrypted)", resp.AwsCreds.AccessKeyID)
	}
}

// TestUpdateLinkDecryptError covers the AWS decrypt failure branch: when
// the stored AWS secret is not a valid AES payload, UpdateLink must
// respond 500 with "Failed to decrypt AWS Access".
func TestUpdateLinkDecryptError(t *testing.T) {
	db := setupAuthDB(t)
	user := models.User{
		UUID:     uuid.NewString(),
		Email:    "broken@example.com",
		Name:     "Broken",
		Password: "x",
		LLMConfig: models.LLM{
			Provider: "openai",
			Providers: map[string]models.AIProvider{
				"openai": {Modal: "gpt-4o", APIKey: mustEncrypt(t, "sk-test")},
			},
		},
		AwsCreds: models.AwsCreds{
			AccessKeyID: "garbage-not-encrypted", // will fail to decode
		},
	}
	if err := db.Create(&user).Error; err != nil {
		t.Fatalf("seed: %v", err)
	}

	r := gin.New()
	r.GET("/update-link", func(c *gin.Context) {
		c.Set("user", user)
		UpdateLink(c)
	})
	req := httptest.NewRequest(http.MethodGet, "/update-link", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)

	if w.Code != http.StatusInternalServerError {
		t.Fatalf("status = %d, want 500 (body %s)", w.Code, w.Body.String())
	}
	if !strings.Contains(w.Body.String(), "Failed to decrypt AWS") {
		t.Errorf("body = %q, want it to mention Failed to decrypt AWS", w.Body.String())
	}
}
