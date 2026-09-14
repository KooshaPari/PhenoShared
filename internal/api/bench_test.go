// SPDX-License-Identifier: MIT OR Apache-2.0
// Package api benchmarks: HTTP-level load testing for the NanoVMS API server.
//
// Run with: go test -bench=. -benchtime=5s -timeout=60s ./internal/api/

package api

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
)

// newBenchRouter creates a test router with mock handlers for benchmarking.
func newBenchRouter(b *testing.B) http.Handler {
	b.Helper()
	h := Handlers{
		Port: &fakePort{},
	}
	return NewRouter(h)
}

// BenchmarkHealthz measures health check throughput.
func BenchmarkHealthz(b *testing.B) {
	router := newBenchRouter(b)
	req := httptest.NewRequest("GET", "/healthz", nil)
	w := httptest.NewRecorder()

	b.ResetTimer()
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		router.ServeHTTP(w, req)
	}
}

// BenchmarkListSandboxes measures list sandbox throughput.
func BenchmarkListSandboxes(b *testing.B) {
	router := newBenchRouter(b)
	req := httptest.NewRequest("GET", "/v1/sandboxes", nil)
	w := httptest.NewRecorder()

	b.ResetTimer()
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		router.ServeHTTP(w, req)
	}
}

// BenchmarkDeploy measures deploy request throughput.
func BenchmarkDeploy(b *testing.B) {
	router := newBenchRouter(b)
	cfg := map[string]interface{}{
		"name":         "bench-sandbox",
		"image":        "alpine:latest",
		"sandbox_type": "native",
	}
	body, _ := json.Marshal(cfg)

	b.ResetTimer()
	b.ReportAllocs()
	for i := 0; i < b.N; i++ {
		req := httptest.NewRequest("POST", "/v1/deploy", bytes.NewReader(body))
		req.Header.Set("Content-Type", "application/json")
		w := httptest.NewRecorder()
		router.ServeHTTP(w, req)
	}
}

// BenchmarkConcurrentDeploy tests deploy under parallel load.
func BenchmarkConcurrentDeploy(b *testing.B) {
	router := newBenchRouter(b)
	cfg := map[string]interface{}{
		"name":         "bench-concurrent",
		"image":        "alpine:latest",
		"sandbox_type": "native",
	}
	body, _ := json.Marshal(cfg)

	b.ResetTimer()
	b.ReportAllocs()
	b.RunParallel(func(pb *testing.PB) {
		for pb.Next() {
			req := httptest.NewRequest("POST", "/v1/deploy", bytes.NewReader(body))
			req.Header.Set("Content-Type", "application/json")
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)
		}
	})
}

// BenchmarkConcurrentMixed tests mixed endpoint load (80% list, 20% deploy).
func BenchmarkConcurrentMixed(b *testing.B) {
	router := newBenchRouter(b)
	cfg := map[string]interface{}{
		"name":         "bench-mixed",
		"image":        "alpine:latest",
		"sandbox_type": "native",
	}
	body, _ := json.Marshal(cfg)

	b.ResetTimer()
	b.ReportAllocs()
	b.RunParallel(func(pb *testing.PB) {
		i := 0
		for pb.Next() {
			i++
			var req *http.Request
			if i%5 == 0 {
				req = httptest.NewRequest("POST", "/v1/deploy", bytes.NewReader(body))
				req.Header.Set("Content-Type", "application/json")
			} else {
				req = httptest.NewRequest("GET", "/v1/sandboxes", nil)
			}
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)
		}
	})
}

// TestAPIConcurrencyStress runs 100 concurrent requests.
func TestAPIConcurrencyStress(t *testing.T) {
	h := Handlers{
		Port: &fakePort{},
	}
	router := NewRouter(h)
	const concurrency = 100
	var wg sync.WaitGroup
	errors := make(chan error, concurrency)

	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func(id int) {
			defer wg.Done()
			req := httptest.NewRequest("GET", "/v1/sandboxes", nil)
			w := httptest.NewRecorder()
			router.ServeHTTP(w, req)

			if w.Code != http.StatusOK {
				errors <- &stressError{id: id, code: w.Code}
			}
		}(i)
	}

	wg.Wait()
	close(errors)

	for err := range errors {
		t.Errorf("Concurrency stress error: %v", err)
	}
}

type stressError struct {
	id   int
	code int
}

func (e *stressError) Error() string {
	return "request failed"
}
