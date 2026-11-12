// loadtest_test.go — BytePort API load testing
//
// Run with: go test -bench=. -benchtime=10s -timeout=60s ./routes/
//
// These benchmarks measure the throughput and latency of the NanoVMS contract
// endpoints under concurrent load. They use mock servers to isolate API
// overhead from NanoVMS processing time.

package routes

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
	"time"
)

// mockNVMSLoadTest returns a mock NanoVMS server that simulates realistic latencies.
func mockNVMSLoadTest(tb testing.TB) *httptest.Server {
	tb.Helper()
	var mu sync.Mutex
	count := 0

	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		mu.Lock()
		count++
		n := count // read under the lock: concurrent handlers raced on count (DATA RACE, release pipeline 2026-10-11)
		mu.Unlock()

		// Simulate realistic NanoVMS latency (1-5ms)
		time.Sleep(time.Duration(1+n%5) * time.Millisecond)

		w.Header().Set("Content-Type", "application/json")
		switch r.Method {
		case "POST":
			w.WriteHeader(http.StatusCreated)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"id":     fmt.Sprintf("sb-%d", n),
				"name":   "load-test",
				"status": "running",
			})
		case "GET":
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode(map[string]interface{}{
				"data": []map[string]interface{}{
					{"id": "sb-1", "name": "test", "status": "running"},
				},
			})
		case "DELETE":
			w.WriteHeader(http.StatusOK)
			json.NewEncoder(w).Encode(map[string]string{"status": "deleted"})
		}
	}))
}

// benchScenario describes one request shape for the BenchmarkEndpoints table.
type benchScenario struct {
	name    string
	method  string
	path    string
	body    []byte
	extra   func(*http.Request)
	wantEnv string // token, used to set NVMS_TOKEN
}

// BenchmarkEndpoints measures throughput across the three NanoVMS contract
// endpoints (deploy, list, stop). Each subbenchmark shares the same env
// setup and request boilerplate via setupBenchEnv + runBenchRequest.
func BenchmarkEndpoints(b *testing.B) {
	jsonBody, _ := json.Marshal(nvmsSandboxConfig{
		Name:        "bench-project",
		Image:       "alpine:latest",
		SandboxType: "native",
	})
	scenarios := []benchScenario{
		{
			name: "deploy", method: "POST", path: "/v1/deploy", body: jsonBody,
			extra:   func(r *http.Request) { r.Header.Set("Content-Type", "application/json") },
			wantEnv: "bench-token",
		},
		{
			name: "list", method: "GET", path: "/v1/sandboxes", body: nil,
			wantEnv: "bench-token",
		},
		{
			name: "stop", method: "POST", path: "/v1/stop?id=bench-sb-1", body: nil,
			wantEnv: "bench-token",
		},
	}

	for _, sc := range scenarios {
		b.Run(sc.name, func(b *testing.B) {
			url := setupBenchEnv(b, sc.wantEnv)
			b.ResetTimer()
			b.RunParallel(func(pb *testing.PB) {
				for pb.Next() {
					runBenchRequest(b, sc.method, url+sc.path, sc.wantEnv, sc.body, sc.extra)
				}
			})
		})
	}
}

// TestConcurrentDeployStress tests 50 concurrent deploys.
func TestConcurrentDeployStress(t *testing.T) {
	mockNVMS := mockNVMSLoadTest(t)
	defer mockNVMS.Close()

	const token = "stress-token"
	setupBenchEnv(t, token)

	const concurrency = 50
	var wg sync.WaitGroup
	errors := make(chan error, concurrency)

	start := time.Now()

	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()

			cfg := nvmsSandboxConfig{
				Name:        fmt.Sprintf("stress-%d", id),
				Image:       "alpine:latest",
				SandboxType: "native",
			}
			jsonBody, _ := json.Marshal(cfg)

			req, _ := http.NewRequest("POST", mockNVMS.URL+"/v1/deploy", bytes.NewReader(jsonBody))
			req.Header.Set("Authorization", "Bearer "+token)
			req.Header.Set("Content-Type", "application/json")

			resp, err := (&http.Client{}).Do(req)
			if err != nil {
				errors <- fmt.Errorf("goroutine %d: %v", id, err)
				return
			}
			defer resp.Body.Close()

			if resp.StatusCode != http.StatusCreated {
				errors <- fmt.Errorf("goroutine %d: status %d", id, resp.StatusCode)
			}
		}(i)
	}

	wg.Wait()
	close(errors)

	elapsed := time.Since(start)
	t.Logf("Concurrent deploy stress: %d requests in %v (%.0f req/s)",
		concurrency, elapsed, float64(concurrency)/elapsed.Seconds())

	for err := range errors {
		t.Errorf("Stress test error: %v", err)
	}
}
