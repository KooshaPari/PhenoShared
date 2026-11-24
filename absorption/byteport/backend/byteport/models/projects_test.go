package models

import (
	"testing"
)

// TestProjectDeployRoundTrip exercises the GetDeploy/SetDeploy accessors and
// verifies that BeforeSave serializes the deployments map to JSON while
// AfterFind deserializes it back. The hooks are pure functions of the in-memory
// Project struct so no DB is required.
func TestProjectDeployRoundTrip(t *testing.T) {
	p := &Project{Name: "demo"}

	// GetDeploy on a fresh project returns nil (deployments never set).
	if got := p.GetDeploy(); got != nil {
		t.Fatalf("fresh GetDeploy = %v, want nil", got)
	}

	// SetDeploy + GetDeploy round-trip.
	want := map[string]Instance{
		"deploy-1": {UUID: "deploy-1", Status: "running"},
		"deploy-2": {UUID: "deploy-2", Status: "stopped"},
	}
	p.SetDeploy(want)
	got := p.GetDeploy()
	if len(got) != len(want) {
		t.Fatalf("len(GetDeploy) = %d, want %d", len(got), len(want))
	}
	for k, v := range want {
		if got[k].UUID != v.UUID || got[k].Status != v.Status {
			t.Errorf("entry %q = %+v, want %+v", k, got[k], v)
		}
	}
}

// TestProjectBeforeSaveSerializesDeployments checks that BeforeSave converts
// the deployments map into a non-empty JSON blob.
func TestProjectBeforeSaveSerializesDeployments(t *testing.T) {
	p := &Project{Name: "demo"}
	p.SetDeploy(map[string]Instance{
		"only": {UUID: "only", Status: "running"},
	})

	if err := p.BeforeSave(nil); err != nil {
		t.Fatalf("BeforeSave: %v", err)
	}
	if p.DeploymentsJSON == "" {
		t.Fatal("DeploymentsJSON empty after BeforeSave")
	}
	if p.UUID == "" {
		t.Fatal("UUID empty after BeforeSave")
	}
}

// TestProjectBeforeSaveUUIDOnlyAssignsWhenEmpty verifies the UUID-on-save
// contract: a pre-existing UUID is preserved, a missing one is generated.
func TestProjectBeforeSaveUUIDOnlyAssignsWhenEmpty(t *testing.T) {
	t.Run("generates when empty", func(t *testing.T) {
		p := &Project{Name: "demo"}
		if err := p.BeforeSave(nil); err != nil {
			t.Fatalf("BeforeSave: %v", err)
		}
		if p.UUID == "" {
			t.Fatal("UUID empty after BeforeSave")
		}
	})
	t.Run("preserves when set", func(t *testing.T) {
		p := &Project{Name: "demo", UUID: "pinned-uuid-123"}
		if err := p.BeforeSave(nil); err != nil {
			t.Fatalf("BeforeSave: %v", err)
		}
		if p.UUID != "pinned-uuid-123" {
			t.Fatalf("UUID = %q, want pinned-uuid-123", p.UUID)
		}
	})
	t.Run("empty deployments skips JSON write", func(t *testing.T) {
		p := &Project{Name: "demo"}
		if err := p.BeforeSave(nil); err != nil {
			t.Fatalf("BeforeSave: %v", err)
		}
		if p.DeploymentsJSON != "" {
			t.Fatalf("DeploymentsJSON = %q, want empty", p.DeploymentsJSON)
		}
	})
}

// TestProjectAfterFindDeserializesDeployments verifies that AfterFind hydrates
// the in-memory deployments map from a stored JSON blob.
func TestProjectAfterFindDeserializesDeployments(t *testing.T) {
	t.Run("with JSON", func(t *testing.T) {
		p := &Project{
			DeploymentsJSON: `{"deploy-1":{"UUID":"deploy-1","Status":"running"}}`,
		}
		if err := p.AfterFind(nil); err != nil {
			t.Fatalf("AfterFind: %v", err)
		}
		got := p.GetDeploy()
		if got == nil {
			t.Fatal("GetDeploy = nil after AfterFind")
		}
		if len(got) != 1 {
			t.Fatalf("len = %d, want 1", len(got))
		}
		if got["deploy-1"].Status != "running" {
			t.Errorf("status = %q, want running", got["deploy-1"].Status)
		}
	})
	t.Run("empty JSON yields empty map", func(t *testing.T) {
		p := &Project{}
		if err := p.AfterFind(nil); err != nil {
			t.Fatalf("AfterFind: %v", err)
		}
		got := p.GetDeploy()
		if got == nil {
			t.Fatal("GetDeploy = nil after AfterFind with empty JSON")
		}
		if len(got) != 0 {
			t.Fatalf("len = %d, want 0", len(got))
		}
	})
	t.Run("invalid JSON returns error", func(t *testing.T) {
		p := &Project{DeploymentsJSON: "not-json"}
		if err := p.AfterFind(nil); err == nil {
			t.Fatal("AfterFind on invalid JSON returned no error")
		}
	})
}
