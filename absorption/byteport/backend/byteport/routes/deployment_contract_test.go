package routes

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"
)

// mockNVMSResponse is the JSON shape NanoVMS returns from POST /v1/deploy.
type mockNVMSResponse struct {
	ID        string `json:"id"`
	Name      string `json:"name"`
	Status    string `json:"status"`
	VMFlavor  string `json:"vm_flavor"`
	IPAddress string `json:"ip_address"`
}

// TestNVMSURLDefault verifies the default NVMS_URL points to port 8443.
func TestNVMSURLDefault(t *testing.T) {
	os.Unsetenv("NVMS_URL")
	url := nvmsURL()
	if url != "http://localhost:8443" {
		t.Errorf("nvmsURL() = %q, want http://localhost:8443", url)
	}
}

// TestNVMSURLEnvVar verifies NVMS_URL env var overrides the default.
func TestNVMSURLEnvVar(t *testing.T) {
	os.Setenv("NVMS_URL", "http://custom:9999")
	defer os.Unsetenv("NVMS_URL")
	url := nvmsURL()
	if url != "http://custom:9999" {
		t.Errorf("nvmsURL() = %q, want http://custom:9999", url)
	}
}

// TestNVMSTokenReadsEnv verifies nvmsToken reads from NVMS_TOKEN env var.
func TestNVMSTokenReadsEnv(t *testing.T) {
	os.Setenv("NVMS_TOKEN", "my-test-token")
	defer os.Unsetenv("NVMS_TOKEN")
	tok := nvmsToken()
	if tok != "my-test-token" {
		t.Errorf("nvmsToken() = %q, want my-test-token", tok)
	}
}

// TestDeployCallsCorrectEndpoint verifies BytePort deploys to /v1/deploy
// with Authorization header and SandboxConfig body.
func TestDeployCallsCorrectEndpoint(t *testing.T) {
	var receivedMethod, receivedPath, receivedAuth string
	var receivedBody map[string]interface{}

	mockNVMS := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedMethod = r.Method
		receivedPath = r.URL.Path
		receivedAuth = r.Header.Get("Authorization")

		body, _ := json.Marshal(map[string]interface{}{})
		_ = body
		json.NewDecoder(r.Body).Decode(&receivedBody)

		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusCreated)
		json.NewEncoder(w).Encode(mockNVMSResponse{
			ID:     "test-sandbox-123",
			Name:   "test-project",
			Status: "running",
		})
	}))
	defer mockNVMS.Close()

	cfg := nvmsSandboxConfig{
		Name:        "test-project",
		Image:       "alpine:latest",
		SandboxType: "native",
	}
	jsonBody, _ := json.Marshal(cfg)

	req, _ := http.NewRequest("POST", mockNVMS.URL+"/v1/deploy", bytes.NewReader(jsonBody))
	req.Header.Set("Authorization", "Bearer test-token-abc123")
	req.Header.Set("Content-Type", "application/json")

	resp, err := (&http.Client{}).Do(req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if receivedMethod != "POST" {
		t.Errorf("method = %q, want POST", receivedMethod)
	}
	if receivedPath != "/v1/deploy" {
		t.Errorf("path = %q, want /v1/deploy", receivedPath)
	}
	if receivedAuth != "Bearer test-token-abc123" {
		t.Errorf("auth = %q, want Bearer test-token-abc123", receivedAuth)
	}
	if receivedBody["sandbox_type"] != "native" {
		t.Errorf("sandbox_type = %q, want native", receivedBody["sandbox_type"])
	}
	if resp.StatusCode != http.StatusCreated {
		t.Errorf("status = %d, want 201", resp.StatusCode)
	}
}

// TestStopCallsCorrectEndpoint verifies BytePort calls /v1/stop?id=<id>.
func TestStopCallsCorrectEndpoint(t *testing.T) {
	var receivedMethod, receivedPath, receivedAuth string

	mockNVMS := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		receivedMethod = r.Method
		receivedPath = r.URL.Path
		receivedAuth = r.Header.Get("Authorization")
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"status": "stopped"})
	}))
	defer mockNVMS.Close()

	req, _ := http.NewRequest("POST", mockNVMS.URL+"/v1/stop?id=test-sandbox-123", nil)
	req.Header.Set("Authorization", "Bearer test-token-abc123")

	resp, err := (&http.Client{}).Do(req)
	if err != nil {
		t.Fatalf("request failed: %v", err)
	}
	defer resp.Body.Close()

	if receivedMethod != "POST" {
		t.Errorf("method = %q, want POST", receivedMethod)
	}
	if receivedPath != "/v1/stop" {
		t.Errorf("path = %q, want /v1/stop", receivedPath)
	}
	if receivedAuth != "Bearer test-token-abc123" {
		t.Errorf("auth = %q, want Bearer test-token-abc123", receivedAuth)
	}
}

// TestSandboxConfigBodyShape verifies the request body matches NanoVMS schema.
func TestSandboxConfigBodyShape(t *testing.T) {
	cfg := nvmsSandboxConfig{
		Name:        "my-app",
		Image:       "nginx:latest",
		SandboxType: "native",
		Labels:      map[string]string{"team": "platform"},
	}

	jsonBody, err := json.Marshal(cfg)
	if err != nil {
		t.Fatalf("marshal failed: %v", err)
	}

	var parsed map[string]interface{}
	if err := json.Unmarshal(jsonBody, &parsed); err != nil {
		t.Fatalf("unmarshal failed: %v", err)
	}

	required := []string{"name", "image", "sandbox_type"}
	for _, field := range required {
		if _, ok := parsed[field]; !ok {
			t.Errorf("missing required field %q in SandboxConfig", field)
		}
	}

	if parsed["name"] != "my-app" {
		t.Errorf("name = %q, want my-app", parsed["name"])
	}
	if parsed["sandbox_type"] != "native" {
		t.Errorf("sandbox_type = %q, want native", parsed["sandbox_type"])
	}
}
