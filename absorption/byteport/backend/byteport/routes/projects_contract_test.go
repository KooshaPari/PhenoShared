package routes

import (
	"encoding/json"
	"testing"

	"byteport/models"

	"github.com/google/uuid"
)

// TestGetProjectsResponseExposesDeploymentsJSON pins the wire contract that
// frontend/web depends on.
//
// frontend/web/src/components/projectData.ts (parseDeployments) reads the
// `DeploymentsJSON` key off each project and JSON.parses it. Its own comment
// states the string form "is the normal case, not an edge case", because the
// decoded map on models.Project is a private field tagged `json:"-"` and so
// never reaches the client.
//
// History: the sibling module backend/models (module `github.com/byteport/api`)
// once tagged the same field `json:"-"`, which would have caused its
// /projects response to omit the key entirely and the UI to show no
// deployments. That divergent copy was retired in 2026-09-20 along with the
// rest of the `github.com/byteport/api` module (see issue #382), so the
// contract this test pins is now the only one in the repo. Keeping this
// guard makes future re-introductions of `json:"-"` an immediate failure
// rather than a silent regression.
func TestGetProjectsResponseExposesDeploymentsJSON(t *testing.T) {
	db := setupAuthDB(t)
	user := seedUser(t, db)

	project := models.Project{
		UUID:  uuid.NewString(),
		ID:    uuid.NewString(),
		Owner: user.UUID,
		Name:  "contract-project",
	}
	// BeforeSave marshals this into the `deployments` column.
	project.SetDeploy(map[string]models.Instance{
		"deploy-1": {UUID: "deploy-1", Status: "running"},
	})
	if err := db.Create(&project).Error; err != nil {
		t.Fatalf("seed project: %v", err)
	}

	w := authedGet(t, user, "/projects", GetProjects)

	var decoded []map[string]any
	if err := json.Unmarshal(w.Body.Bytes(), &decoded); err != nil {
		t.Fatalf("response is not a JSON array of projects: %v (body %s)", err, w.Body.String())
	}
	if len(decoded) != 1 {
		t.Fatalf("got %d projects, want 1 (body %s)", len(decoded), w.Body.String())
	}

	raw, ok := decoded[0]["DeploymentsJSON"]
	if !ok {
		t.Fatalf("response project has no DeploymentsJSON key, which frontend/web's "+
			"parseDeployments() reads; project = %v", decoded[0])
	}
	encoded, ok := raw.(string)
	if !ok {
		t.Fatalf("DeploymentsJSON is %T, want the JSON string form the frontend parses", raw)
	}

	// Exactly what the frontend does with the value.
	var deployments map[string]map[string]any
	if err := json.Unmarshal([]byte(encoded), &deployments); err != nil {
		t.Fatalf("DeploymentsJSON is not parseable the way the frontend expects: %v (%q)", err, encoded)
	}
	if _, ok := deployments["deploy-1"]; !ok {
		t.Fatalf("parsed deployments missing deploy-1: %v", deployments)
	}
}
