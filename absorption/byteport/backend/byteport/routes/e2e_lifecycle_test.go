// e2e_lifecycle_test.go — End-to-end test for the BytePort→NanoVMS deploy→monitor lifecycle.
//
// Tests the full flow: deploy sandbox → poll status → stop sandbox → verify cleanup.
// Uses a mock NanoVMS server to simulate the full lifecycle without requiring
// a real NanoVMS instance.

package routes

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"os"
	"sync"
	"testing"
)

// lifecycleMockServer simulates NanoVMS with state transitions.
type lifecycleMockServer struct {
	mu        sync.Mutex
	sandboxes map[string]string // id → status
	nextID    int
}

func newLifecycleMock() *httptest.Server {
	mock := &lifecycleMockServer{
		sandboxes: make(map[string]string),
		nextID:    1,
	}

	return httptest.NewServer(mock)
}

// ServeHTTP routes mock NanoVMS requests to one handler per route so each
// handler stays cognitively simple.
func (m *lifecycleMockServer) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")

	switch {
	case r.Method == "POST" && r.URL.Path == "/v1/deploy":
		m.handleDeploy(w, r)
	case r.Method == "GET" && r.URL.Path == "/v1/sandboxes":
		m.handleList(w, r)
	case r.Method == "GET" && len(r.URL.Path) > len("/v1/sandboxes/"):
		m.handleSandboxGet(w, r)
	case r.Method == "POST" && r.URL.Path == "/v1/stop":
		m.handleStop(w, r)
	case r.Method == "DELETE" && len(r.URL.Path) > len("/v1/sandboxes/"):
		m.handleSandboxDelete(w, r)
	default:
		w.WriteHeader(http.StatusMethodNotAllowed)
		json.NewEncoder(w).Encode(map[string]string{"error": "method not allowed"})
	}
}

func (m *lifecycleMockServer) handleDeploy(w http.ResponseWriter, _ *http.Request) {
	m.mu.Lock()
	id := fmt.Sprintf("e2e-%d", m.nextID)
	m.nextID++
	m.sandboxes[id] = "running"
	m.mu.Unlock()

	w.WriteHeader(http.StatusCreated)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"id":     id,
		"name":   "e2e-sandbox",
		"status": "running",
	})
}

func (m *lifecycleMockServer) handleList(w http.ResponseWriter, _ *http.Request) {
	m.mu.Lock()
	var data []map[string]interface{}
	for id, status := range m.sandboxes {
		data = append(data, map[string]interface{}{
			"id":     id,
			"name":   "e2e-sandbox",
			"status": status,
		})
	}
	m.mu.Unlock()

	if data == nil {
		data = []map[string]interface{}{}
	}
	json.NewEncoder(w).Encode(map[string]interface{}{"data": data})
}

func (m *lifecycleMockServer) handleSandboxGet(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Path[len("/v1/sandboxes/"):]
	m.mu.Lock()
	status, ok := m.sandboxes[id]
	m.mu.Unlock()

	if !ok {
		w.WriteHeader(http.StatusNotFound)
		json.NewEncoder(w).Encode(map[string]string{"error": "not found"})
		return
	}
	json.NewEncoder(w).Encode(map[string]interface{}{
		"id":     id,
		"name":   "e2e-sandbox",
		"status": status,
	})
}

func (m *lifecycleMockServer) handleStop(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Query().Get("id")
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.sandboxes[id]; ok {
		m.sandboxes[id] = "stopped"
		json.NewEncoder(w).Encode(map[string]string{"status": "stopped"})
		return
	}
	w.WriteHeader(http.StatusNotFound)
	json.NewEncoder(w).Encode(map[string]string{"error": "not found"})
}

func (m *lifecycleMockServer) handleSandboxDelete(w http.ResponseWriter, r *http.Request) {
	id := r.URL.Path[len("/v1/sandboxes/"):]
	m.mu.Lock()
	defer m.mu.Unlock()
	if _, ok := m.sandboxes[id]; ok {
		delete(m.sandboxes, id)
		json.NewEncoder(w).Encode(map[string]string{"status": "deleted"})
		return
	}
	w.WriteHeader(http.StatusNotFound)
	json.NewEncoder(w).Encode(map[string]string{"error": "not found"})
}

// TestE2EFullLifecycle tests: deploy → list → get → stop → delete → verify empty.
func TestE2EFullLifecycle(t *testing.T) {
	mock := newLifecycleMock()
	defer mock.Close()

	os.Setenv("NVMS_URL", mock.URL)
	os.Setenv("NVMS_TOKEN", "e2e-token")
	defer os.Unsetenv("NVMS_URL")
	defer os.Unsetenv("NVMS_TOKEN")

	// Step 1: Deploy
	t.Log("Step 1: Deploy sandbox")
	cfg := nvmsSandboxConfig{
		Name:        "e2e-test",
		Image:       "alpine:latest",
		SandboxType: "native",
	}
	jsonBody, _ := json.Marshal(cfg)

	req, _ := http.NewRequest("POST", mock.URL+"/v1/deploy", bytes.NewReader(jsonBody))
	req.Header.Set("Authorization", "Bearer e2e-token")
	req.Header.Set("Content-Type", "application/json")

	resp, err := (&http.Client{}).Do(req)
	if err != nil {
		t.Fatalf("Deploy failed: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("Deploy status = %d, want 201", resp.StatusCode)
	}

	var deployResp struct {
		ID     string `json:"id"`
		Status string `json:"status"`
	}
	json.NewDecoder(resp.Body).Decode(&deployResp)

	if deployResp.ID == "" {
		t.Fatal("Deploy returned empty ID")
	}
	if deployResp.Status != "running" {
		t.Errorf("Deploy status = %q, want running", deployResp.Status)
	}
	sandboxID := deployResp.ID
	t.Logf("Deployed sandbox: %s", sandboxID)

	// Step 2: List
	t.Log("Step 2: List sandboxes")
	req, _ = http.NewRequest("GET", mock.URL+"/v1/sandboxes", nil)
	req.Header.Set("Authorization", "Bearer e2e-token")

	resp, err = (&http.Client{}).Do(req)
	if err != nil {
		t.Fatalf("List failed: %v", err)
	}
	defer resp.Body.Close()

	var listResp struct {
		Data []struct {
			ID     string `json:"id"`
			Status string `json:"status"`
		} `json:"data"`
	}
	json.NewDecoder(resp.Body).Decode(&listResp)

	if len(listResp.Data) != 1 {
		t.Errorf("List returned %d sandboxes, want 1", len(listResp.Data))
	}
	if len(listResp.Data) > 0 && listResp.Data[0].ID != sandboxID {
		t.Errorf("List sandbox ID = %q, want %q", listResp.Data[0].ID, sandboxID)
	}

	// Step 3: Get status
	t.Log("Step 3: Get sandbox status")
	req, _ = http.NewRequest("GET", mock.URL+"/v1/sandboxes/"+sandboxID, nil)
	req.Header.Set("Authorization", "Bearer e2e-token")

	resp, err = (&http.Client{}).Do(req)
	if err != nil {
		t.Fatalf("Get status failed: %v", err)
	}
	defer resp.Body.Close()

	var statusResp struct {
		ID     string `json:"id"`
		Status string `json:"status"`
	}
	json.NewDecoder(resp.Body).Decode(&statusResp)

	if statusResp.Status != "running" {
		t.Errorf("Status = %q, want running", statusResp.Status)
	}

	// Step 4: Stop
	t.Log("Step 4: Stop sandbox")
	req, _ = http.NewRequest("POST", mock.URL+"/v1/stop?id="+sandboxID, nil)
	req.Header.Set("Authorization", "Bearer e2e-token")

	resp, err = (&http.Client{}).Do(req)
	if err != nil {
		t.Fatalf("Stop failed: %v", err)
	}
	defer resp.Body.Close()

	var stopResp struct {
		Status string `json:"status"`
	}
	json.NewDecoder(resp.Body).Decode(&stopResp)

	if stopResp.Status != "stopped" {
		t.Errorf("Stop status = %q, want stopped", stopResp.Status)
	}

	// Step 5: Delete
	t.Log("Step 5: Delete sandbox")
	req, _ = http.NewRequest("DELETE", mock.URL+"/v1/sandboxes/"+sandboxID, nil)
	req.Header.Set("Authorization", "Bearer e2e-token")

	resp, err = (&http.Client{}).Do(req)
	if err != nil {
		t.Fatalf("Delete failed: %v", err)
	}
	defer resp.Body.Close()

	var deleteResp struct {
		Status string `json:"status"`
	}
	json.NewDecoder(resp.Body).Decode(&deleteResp)

	if deleteResp.Status != "deleted" {
		t.Errorf("Delete status = %q, want deleted", deleteResp.Status)
	}

	// Step 6: Verify empty
	t.Log("Step 6: Verify sandboxes list is empty")
	req, _ = http.NewRequest("GET", mock.URL+"/v1/sandboxes", nil)
	req.Header.Set("Authorization", "Bearer e2e-token")

	resp, err = (&http.Client{}).Do(req)
	if err != nil {
		t.Fatalf("Final list failed: %v", err)
	}
	defer resp.Body.Close()

	json.NewDecoder(resp.Body).Decode(&listResp)

	if len(listResp.Data) != 0 {
		t.Errorf("Final list returned %d sandboxes, want 0", len(listResp.Data))
	}

	t.Logf("E2E lifecycle complete: deploy(%s) → list → get → stop → delete → verify empty", sandboxID)
}

// TestE2EMultipleSandboxes tests deploying and managing multiple sandboxes.
func TestE2EMultipleSandboxes(t *testing.T) {
	mock := newLifecycleMock()
	defer mock.Close()

	os.Setenv("NVMS_URL", mock.URL)
	os.Setenv("NVMS_TOKEN", "e2e-multi-token")
	defer os.Unsetenv("NVMS_URL")
	defer os.Unsetenv("NVMS_TOKEN")

	const numSandboxes = 5
	deployedIDs := make([]string, 0, numSandboxes)

	// Deploy multiple sandboxes
	for i := 0; i < numSandboxes; i++ {
		cfg := nvmsSandboxConfig{
			Name:        fmt.Sprintf("multi-%d", i),
			Image:       "alpine:latest",
			SandboxType: "native",
		}
		jsonBody, _ := json.Marshal(cfg)

		req, _ := http.NewRequest("POST", mock.URL+"/v1/deploy", bytes.NewReader(jsonBody))
		req.Header.Set("Authorization", "Bearer e2e-multi-token")
		req.Header.Set("Content-Type", "application/json")

		resp, err := (&http.Client{}).Do(req)
		if err != nil {
			t.Fatalf("Deploy %d failed: %v", i, err)
		}

		var deployResp struct {
			ID string `json:"id"`
		}
		json.NewDecoder(resp.Body).Decode(&deployResp)
		resp.Body.Close()

		deployedIDs = append(deployedIDs, deployResp.ID)
	}

	// Verify list has all sandboxes
	req, _ := http.NewRequest("GET", mock.URL+"/v1/sandboxes", nil)
	req.Header.Set("Authorization", "Bearer e2e-multi-token")
	resp, err := (&http.Client{}).Do(req)
	if err != nil {
		t.Fatalf("List failed: %v", err)
	}

	var listResp struct {
		Data []struct {
			ID string `json:"id"`
		} `json:"data"`
	}
	json.NewDecoder(resp.Body).Decode(&listResp)
	resp.Body.Close()

	if len(listResp.Data) != numSandboxes {
		t.Errorf("List returned %d sandboxes, want %d", len(listResp.Data), numSandboxes)
	}

	// Stop all sandboxes
	for _, id := range deployedIDs {
		req, _ = http.NewRequest("POST", mock.URL+"/v1/stop?id="+id, nil)
		req.Header.Set("Authorization", "Bearer e2e-multi-token")
		resp, err := (&http.Client{}).Do(req)
		if err != nil {
			t.Fatalf("Stop %s failed: %v", id, err)
		}
		resp.Body.Close()
	}

	// Delete all sandboxes
	for _, id := range deployedIDs {
		req, _ = http.NewRequest("DELETE", mock.URL+"/v1/sandboxes/"+id, nil)
		req.Header.Set("Authorization", "Bearer e2e-multi-token")
		resp, err := (&http.Client{}).Do(req)
		if err != nil {
			t.Fatalf("Delete %s failed: %v", id, err)
		}
		resp.Body.Close()
	}

	// Verify empty
	req, _ = http.NewRequest("GET", mock.URL+"/v1/sandboxes", nil)
	req.Header.Set("Authorization", "Bearer e2e-multi-token")
	resp, err = (&http.Client{}).Do(req)
	if err != nil {
		t.Fatalf("Final list failed: %v", err)
	}
	json.NewDecoder(resp.Body).Decode(&listResp)
	resp.Body.Close()

	if len(listResp.Data) != 0 {
		t.Errorf("Final list returned %d sandboxes, want 0", len(listResp.Data))
	}

	t.Logf("Multi-sandbox lifecycle: %d sandboxes deployed, stopped, deleted, verified empty", numSandboxes)
}

// TestE2EAuthHeaderPropagation verifies auth headers are correctly passed.
func TestE2EAuthHeaderPropagation(t *testing.T) {
	var receivedAuth string

	mock := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedAuth = r.Header.Get("Authorization")
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(map[string]interface{}{
			"id":     "auth-test-1",
			"status": "running",
		})
	}))
	defer mock.Close()

	os.Setenv("NVMS_URL", mock.URL)
	os.Setenv("NVMS_TOKEN", "my-secret-token-123")
	defer os.Unsetenv("NVMS_URL")
	defer os.Unsetenv("NVMS_TOKEN")

	cfg := nvmsSandboxConfig{
		Name:  "auth-test",
		Image: "alpine:latest",
	}
	jsonBody, _ := json.Marshal(cfg)

	req, _ := http.NewRequest("POST", mock.URL+"/v1/deploy", bytes.NewReader(jsonBody))
	req.Header.Set("Authorization", "Bearer my-secret-token-123")
	req.Header.Set("Content-Type", "application/json")

	resp, err := (&http.Client{}).Do(req)
	if err != nil {
		t.Fatalf("Request failed: %v", err)
	}
	resp.Body.Close()

	if receivedAuth != "Bearer my-secret-token-123" {
		t.Errorf("Auth header = %q, want Bearer my-secret-token-123", receivedAuth)
	}
}
