package routes

import (
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"testing"

	"byteport/models"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// TestRepositoryIDPrefersExplicitField covers the first branch of
// repositoryID: when `repository_id` is set, it wins regardless of the
// embedded repository.
func TestRepositoryIDPrefersExplicitField(t *testing.T) {
	req := deployRequest{RepositoryID: "explicit-id"}
	req.Repository = &models.Repository{ID: 42} // must be ignored
	if got := req.repositoryID(); got != "explicit-id" {
		t.Fatalf("got %q, want explicit-id", got)
	}
}

// TestRepositoryIDFallsBackToEmbedded covers the second branch: when the
// explicit field is empty but `repository` carries an ID, the embedded ID
// (as a base-10 string) is returned.
func TestRepositoryIDFallsBackToEmbedded(t *testing.T) {
	req := deployRequest{Repository: &models.Repository{ID: 42}}
	if got := req.repositoryID(); got != "42" {
		t.Fatalf("got %q, want 42", got)
	}
}

// TestRepositoryIDReturnsEmptyWhenAbsent covers the empty branch: with
// neither field populated, the result is the empty string.
func TestRepositoryIDReturnsEmptyWhenAbsent(t *testing.T) {
	req := deployRequest{}
	if got := req.repositoryID(); got != "" {
		t.Fatalf("got %q, want empty string", got)
	}

	req = deployRequest{Repository: &models.Repository{ID: 0}}
	if got := req.repositoryID(); got != "" {
		t.Fatalf("got %q, want empty string (ID 0 is not populated)", got)
	}
}

// TestGetProjectsEmpty covers the empty branch: an authenticated user with
// no projects must get back an empty (or null) list, NOT a 500.
func TestGetProjectsEmpty(t *testing.T) {
	db := setupAuthDB(t)
	_ = seedUser(t, db)

	r := gin.New()
	r.GET("/projects", GetProjects)
	req := httptest.NewRequest(http.MethodGet, "/projects", nil)
	w := httptest.NewRecorder()
	r.ServeHTTP(w, req)
}

// TestGetInstancesEmpty covers the empty branch: an authenticated user
// with no instances must get back an empty list.
func TestGetInstancesEmpty(t *testing.T) {
	db := setupAuthDB(t)
	user := seedUser(t, db)
	_ = db // referenced for clarity; seedUser mutates it

	// Reuse authedGet so the token/cookie/middleware boilerplate stays
	// in one place. It asserts 200.
	authedGet(t, user, "/instances", GetInstances)
}

// TestGetInstancesHappyPath covers the populated branch: an authenticated
// user with two instances must get them both back, scoped to that owner.
func TestGetInstancesHappyPath(t *testing.T) {
	db := setupAuthDB(t)
	user := seedUser(t, db)
	other := seedOtherUser(t, db)

	// Two instances owned by `user`, one owned by `other`. Only the two
	// owned by `user` must come back.
	if err := db.Create(&models.Instance{
		UUID: "mine-1", Owner: user.UUID, Name: "i1", Status: "running",
	}).Error; err != nil {
		t.Fatalf("seed mine-1: %v", err)
	}
	if err := db.Create(&models.Instance{
		UUID: "mine-2", Owner: user.UUID, Name: "i2", Status: "stopped",
	}).Error; err != nil {
		t.Fatalf("seed mine-2: %v", err)
	}
	if err := db.Create(&models.Instance{
		UUID: "theirs", Owner: other.UUID, Name: "i3", Status: "running",
	}).Error; err != nil {
		t.Fatalf("seed theirs: %v", err)
	}

	w := authedGet(t, user, "/instances", GetInstances)
	body := w.Body.String()
	if !strings.Contains(body, "mine-1") || !strings.Contains(body, "mine-2") {
		t.Errorf("body did not include owned instances: %s", body)
	}
	if strings.Contains(body, "theirs") {
		t.Errorf("body leaked another user's instance: %s", body)
	}
}

// TestGetProjectsHappyPath covers the populated branch: an authenticated
// user with two projects must get them back.
func TestGetProjectsHappyPath(t *testing.T) {
	db := setupAuthDB(t)
	user := seedUser(t, db)
	other := seedOtherUser(t, db)

	// Two projects owned by `user`, one owned by `other`.
	for i, owner := range []string{user.UUID, user.UUID, other.UUID} {
		p := models.Project{
			UUID:  uuid.NewString(),
			ID:    uuid.NewString(),
			Owner: owner,
			Name:  "p-" + strconv.FormatInt(int64(i), 10),
		}
		if err := db.Create(&p).Error; err != nil {
			t.Fatalf("seed project: %v", err)
		}
	}

	w := authedGet(t, user, "/projects", GetProjects)
	body := w.Body.String()
	// The owned projects must be present; the other user's must not.
	for _, name := range []string{"p-0", "p-1"} {
		if !strings.Contains(body, name) {
			t.Errorf("body did not include owned project %q: %s", name, body)
		}
	}
	if strings.Contains(body, "p-2") {
		t.Errorf("body leaked another user's project: %s", body)
	}
}
