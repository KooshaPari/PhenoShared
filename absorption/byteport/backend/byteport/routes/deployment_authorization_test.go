package routes

import (
	"byteport/models"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"sync"
	"testing"

	"github.com/gin-gonic/gin"
	"github.com/glebarez/sqlite"
	"gorm.io/gorm"
)

// These tests cover what the deploy and terminate handlers do with a request
// they cannot trust: a body that is malformed or incomplete, a body that claims
// an identity, and a caller acting on a project it does not own. The NanoVMS
// wire format itself is covered by deployment_contract_test.go.

func init() {
	gin.SetMode(gin.TestMode)
}

// nvmsStub stands in for the NanoVMS sandbox service and records whether it was
// asked to do anything, so a rejected request can be proven not to have reached
// it.
type nvmsStub struct {
	server  *httptest.Server
	mu      sync.Mutex
	deploys int
	stops   int
}

func newNVMSStub(t *testing.T) *nvmsStub {
	t.Helper()

	stub := &nvmsStub{}
	stub.server = httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		stub.mu.Lock()
		switch r.URL.Path {
		case "/v1/deploy":
			stub.deploys++
		case "/v1/stop":
			stub.stops++
		}
		stub.mu.Unlock()

		w.Header().Set("Content-Type", "application/json")
		if r.URL.Path == "/v1/deploy" {
			w.WriteHeader(http.StatusCreated)
			_ = json.NewEncoder(w).Encode(mockNVMSResponse{
				ID:     "sandbox-1",
				Name:   "sandbox",
				Status: "running",
			})
			return
		}
		_ = json.NewEncoder(w).Encode(map[string]string{"status": "stopped"})
	}))
	t.Cleanup(stub.server.Close)
	t.Setenv("NVMS_URL", stub.server.URL)

	return stub
}

func (s *nvmsStub) deployCalls() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.deploys
}

func (s *nvmsStub) stopCalls() int {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.stops
}

// testDB points models.DB at a private SQLite file for the duration of a test.
func testDB(t *testing.T) *gorm.DB {
	t.Helper()

	db, err := gorm.Open(sqlite.Open(filepath.Join(t.TempDir(), "test.db")), &gorm.Config{
		DisableForeignKeyConstraintWhenMigrating: true,
	})
	if err != nil {
		t.Fatalf("open test database: %v", err)
	}
	if err := db.AutoMigrate(&models.User{}, &models.Project{}); err != nil {
		t.Fatalf("migrate test database: %v", err)
	}

	previous := models.DB
	models.DB = db
	t.Cleanup(func() {
		models.DB = previous
		// Close the pool before t.TempDir's RemoveAll runs. Cleanups are LIFO
		// and TempDir was registered first, so without this the open SQLite
		// file handle makes RemoveAll fail on Windows.
		if sqlDB, err := db.DB(); err == nil {
			_ = sqlDB.Close()
		}
	})

	return db
}

// handlerContext builds a gin test context for a handler call. The session user
// is only attached when authenticated is true, which is how an unauthenticated
// request reaching a protected handler is simulated.
func handlerContext(w *httptest.ResponseRecorder, path, body string, user models.User, authenticated bool) *gin.Context {
	c, _ := gin.CreateTestContext(w)
	c.Request = httptest.NewRequest(http.MethodPost, path, strings.NewReader(body))
	c.Request.Header.Set("Content-Type", "application/json")
	if authenticated {
		c.Set("user", user)
	}
	return c
}

// TestDeployProjectRejectsInvalidBody verifies that a body which does not carry
// a usable project name is answered with 400 and never reaches NanoVMS.
//
// Regression: the handler bound an unvalidated models.Project, so every one of
// these bodies passed binding and was proxied to the sandbox service, which then
// answered 500 on the caller's behalf.
func TestDeployProjectRejectsInvalidBody(t *testing.T) {
	stub := newNVMSStub(t)
	alice := models.User{UUID: "alice-uuid", Name: "alice"}

	bodies := []string{
		`{}`,
		`{"name":""}`,
		`{"description":"no name here"}`,
		`not json at all`,
		`[]`,
	}

	for _, body := range bodies {
		t.Run(body, func(t *testing.T) {
			w := httptest.NewRecorder()
			DeployProject(handlerContext(w, "/deploy", body, alice, true))

			if w.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want %d (body %q, response %s)",
					w.Code, http.StatusBadRequest, body, w.Body.String())
			}
		})
	}

	if got := stub.deployCalls(); got != 0 {
		t.Errorf("NanoVMS deploy calls = %d, want 0 for rejected bodies", got)
	}
}

// TestDeployProjectRequiresSession verifies that an unauthenticated caller gets
// 401 and that no sandbox is provisioned.
func TestDeployProjectRequiresSession(t *testing.T) {
	stub := newNVMSStub(t)

	w := httptest.NewRecorder()
	DeployProject(handlerContext(w, "/deploy", `{"name":"p"}`, models.User{}, false))

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusUnauthorized)
	}
	if got := stub.deployCalls(); got != 0 {
		t.Errorf("NanoVMS deploy calls = %d, want 0 without a session", got)
	}
}

// TestDeployProjectDerivesOwnerFromSession verifies that identity fields in the
// body are ignored: the stored project is owned by the session user and carries
// server-generated identifiers.
//
// Regression: the handler read newProject.User.UUID as the owner and
// newProject.UUID as the project key, both straight from the JSON body, so a
// caller could attribute a deployment to any account and pick its identifiers.
func TestDeployProjectDerivesOwnerFromSession(t *testing.T) {
	db := testDB(t)
	stub := newNVMSStub(t)
	alice := models.User{UUID: "alice-uuid", Name: "alice"}

	body := `{"name":"my-app","owner":"victim","uuid":"victim-uuid","id":"victim-id","user":{"uuid":"victim-uuid"}}`

	w := httptest.NewRecorder()
	DeployProject(handlerContext(w, "/deploy", body, alice, true))

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d (response %s)", w.Code, http.StatusOK, w.Body.String())
	}
	if got := stub.deployCalls(); got != 1 {
		t.Fatalf("NanoVMS deploy calls = %d, want 1", got)
	}

	var stored models.Project
	if err := db.Where("name = ?", "my-app").First(&stored).Error; err != nil {
		t.Fatalf("stored project not found: %v", err)
	}

	if stored.Owner != alice.UUID {
		t.Errorf("owner = %q, want %q (body-supplied identity was trusted)", stored.Owner, alice.UUID)
	}
	if stored.UUID == "victim-uuid" || stored.ID == "victim-id" {
		t.Errorf("client-supplied identifiers were stored: uuid=%q id=%q", stored.UUID, stored.ID)
	}
	if stored.UUID == "" || stored.ID == "" {
		t.Errorf("server-generated identifiers missing: uuid=%q id=%q", stored.UUID, stored.ID)
	}
}

// TestTerminateInstanceRejectsInvalidBody verifies that a terminate request
// without a project identifier is answered with 400 and never reaches NanoVMS.
func TestTerminateInstanceRejectsInvalidBody(t *testing.T) {
	stub := newNVMSStub(t)
	alice := models.User{UUID: "alice-uuid"}

	for _, body := range []string{`{}`, `{"uuid":""}`, `not json at all`} {
		t.Run(body, func(t *testing.T) {
			w := httptest.NewRecorder()
			TerminateInstance(handlerContext(w, "/terminate", body, alice, true))

			if w.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want %d (body %q)", w.Code, http.StatusBadRequest, body)
			}
		})
	}

	if got := stub.stopCalls(); got != 0 {
		t.Errorf("NanoVMS stop calls = %d, want 0 for rejected bodies", got)
	}
}

// TestTerminateInstanceRequiresSession verifies an unauthenticated caller gets
// 401 rather than reaching the database or the sandbox service.
func TestTerminateInstanceRequiresSession(t *testing.T) {
	stub := newNVMSStub(t)

	w := httptest.NewRecorder()
	TerminateInstance(handlerContext(w, "/terminate", `{"uuid":"some-project"}`, models.User{}, false))

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("status = %d, want %d", w.Code, http.StatusUnauthorized)
	}
	if got := stub.stopCalls(); got != 0 {
		t.Errorf("NanoVMS stop calls = %d, want 0 without a session", got)
	}
}

// TestTerminateInstanceScopedToOwner verifies that a caller cannot stop or
// delete a project owned by somebody else.
//
// Regression: the handler forwarded the client-supplied uuid to NanoVMS and to
// a database delete without checking ownership, so any authenticated caller
// could stop and delete any project by guessing its identifier.
func TestTerminateInstanceScopedToOwner(t *testing.T) {
	db := testDB(t)
	stub := newNVMSStub(t)

	if err := db.Create(&models.Project{
		UUID:  "bob-project",
		ID:    "bob-project",
		Owner: "bob-uuid",
		Name:  "bob-app",
	}).Error; err != nil {
		t.Fatalf("seed bob's project: %v", err)
	}

	alice := models.User{UUID: "alice-uuid"}
	w := httptest.NewRecorder()
	TerminateInstance(handlerContext(w, "/terminate", `{"uuid":"bob-project"}`, alice, true))

	if w.Code != http.StatusNotFound {
		t.Fatalf("status = %d, want %d for a project owned by another user", w.Code, http.StatusNotFound)
	}
	if got := stub.stopCalls(); got != 0 {
		t.Errorf("NanoVMS stop calls = %d, want 0 for a project owned by another user", got)
	}

	var remaining int64
	if err := db.Model(&models.Project{}).Where("uuid = ?", "bob-project").Count(&remaining).Error; err != nil {
		t.Fatalf("count bob's project: %v", err)
	}
	if remaining != 1 {
		t.Errorf("bob's project rows remaining = %d, want 1 (delete was not owner-scoped)", remaining)
	}
}

// TestTerminateInstanceStopsOwnProject verifies the owner path is unchanged: the
// sandbox is stopped and the project row is removed.
func TestTerminateInstanceStopsOwnProject(t *testing.T) {
	db := testDB(t)
	stub := newNVMSStub(t)
	alice := models.User{UUID: "alice-uuid"}

	if err := db.Create(&models.Project{
		UUID:  "alice-project",
		ID:    "alice-project",
		Owner: alice.UUID,
		Name:  "alice-app",
	}).Error; err != nil {
		t.Fatalf("seed alice's project: %v", err)
	}

	w := httptest.NewRecorder()
	TerminateInstance(handlerContext(w, "/terminate", `{"uuid":"alice-project"}`, alice, true))

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want %d (response %s)", w.Code, http.StatusOK, w.Body.String())
	}
	if got := stub.stopCalls(); got != 1 {
		t.Errorf("NanoVMS stop calls = %d, want 1", got)
	}

	var remaining int64
	if err := db.Model(&models.Project{}).Where("uuid = ?", "alice-project").Count(&remaining).Error; err != nil {
		t.Fatalf("count alice's project: %v", err)
	}
	if remaining != 0 {
		t.Errorf("alice's project rows remaining = %d, want 0", remaining)
	}
}
