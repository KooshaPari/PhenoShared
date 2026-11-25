package routes

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gin-gonic/gin"
)

func init() {
	// Suppress gin's debug-mode output during tests.
	gin.SetMode(gin.TestMode)
}

// newTestRouter returns a gin engine wired with the metrics middleware and
// health/metrics handlers so tests can assert on the public surface.
func newTestRouter() *gin.Engine {
	r := gin.New()
	r.Use(MetricsMiddleware())
	r.GET("/healthz", HealthHandler)
	r.GET("/metrics", MetricsHandler)
	return r
}

// resetMetricsForTest wipes the package-level metrics counters so each test
// starts from a clean slate.
func resetMetricsForTest() {
	metrics.startTime = time.Now().Add(-time.Second)
	metrics.requestCount.Store(0)
	metrics.errorCount.Store(0)
	metrics.deployCount.Store(0)
	metrics.sandboxActive.Store(0)
}

func TestRecordRequestAndError(t *testing.T) {
	resetMetricsForTest()
	recordRequest()
	recordRequest()
	if got := metrics.requestCount.Load(); got != 2 {
		t.Fatalf("requestCount = %d, want 2", got)
	}
	if got := metrics.errorCount.Load(); got != 0 {
		t.Fatalf("errorCount = %d, want 0", got)
	}
	recordError()
	if got := metrics.errorCount.Load(); got != 1 {
		t.Fatalf("errorCount = %d, want 1", got)
	}
}

func TestRecordDeployIncrementsActive(t *testing.T) {
	resetMetricsForTest()
	recordDeploy()
	recordDeploy()
	recordDeploy()
	if got := metrics.deployCount.Load(); got != 3 {
		t.Fatalf("deployCount = %d, want 3", got)
	}
	if got := metrics.sandboxActive.Load(); got != 3 {
		t.Fatalf("sandboxActive = %d, want 3", got)
	}
	recordSandboxStopped()
	if got := metrics.sandboxActive.Load(); got != 2 {
		t.Fatalf("sandboxActive after stop = %d, want 2", got)
	}
}

func TestMetricsMiddlewareRecordsErrors(t *testing.T) {
	resetMetricsForTest()
	r := gin.New()
	r.Use(MetricsMiddleware())
	r.GET("/ok", func(c *gin.Context) { c.JSON(http.StatusOK, gin.H{}) })
	r.GET("/bad", func(c *gin.Context) { c.JSON(http.StatusBadRequest, gin.H{}) })
	r.GET("/err", func(c *gin.Context) { c.JSON(http.StatusInternalServerError, gin.H{}) })

	for _, path := range []string{"/ok", "/ok"} {
		w := httptest.NewRecorder()
		req := httptest.NewRequest(http.MethodGet, path, nil)
		r.ServeHTTP(w, req)
	}
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/bad", nil)
	r.ServeHTTP(w, req)
	w = httptest.NewRecorder()
	req = httptest.NewRequest(http.MethodGet, "/err", nil)
	r.ServeHTTP(w, req)

	if got := metrics.requestCount.Load(); got != 4 {
		t.Fatalf("requestCount = %d, want 4", got)
	}
	if got := metrics.errorCount.Load(); got != 2 {
		t.Fatalf("errorCount = %d, want 2 (bad + err)", got)
	}
}

func TestMetricsHandler(t *testing.T) {
	resetMetricsForTest()
	recordRequest()
	recordRequest()
	recordError()
	recordDeploy()

	r := newTestRouter()
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/metrics", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	body := w.Body.String()
	for _, want := range []string{
		"# HELP byteport_uptime_seconds",
		"# TYPE byteport_requests_total counter",
		// MetricsMiddleware records the /metrics request itself, so the
		// counter is two manual calls plus the middleware hit.
		"byteport_requests_total 3",
		"byteport_errors_total 1",
		"byteport_deploys_total 1",
		"byteport_sandboxes_active 1",
		"byteport_memory_alloc_bytes",
		"byteport_goroutines",
	} {
		if !strings.Contains(body, want) {
			t.Errorf("metrics body missing %q\nbody:\n%s", want, body)
		}
	}
	ct := w.Header().Get("Content-Type")
	if !strings.HasPrefix(ct, "text/plain") {
		t.Errorf("Content-Type = %q, want text/plain prefix", ct)
	}
}

func TestHealthHandler(t *testing.T) {
	resetMetricsForTest()
	r := newTestRouter()
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	r.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("status = %d, want 200", w.Code)
	}
	body := w.Body.String()
	for _, want := range []string{`"status":"healthy"`, `"service":"byteport"`, `"uptime":`} {
		if !strings.Contains(body, want) {
			t.Errorf("health body missing %q\nbody: %s", want, body)
		}
	}
}

func TestFormatHelpers(t *testing.T) {
	cases := []struct {
		name string
		got  string
		want string
	}{
		{"float zero", formatFloat(0), "0.00"},
		{"float half", formatFloat(0.5), "0.50"},
		{"float round", formatFloat(3.14159), "3.14"},
		{"float neg", formatFloat(-1.5), "-1.50"},
		{"int zero", formatInt(0), "0"},
		{"int pos", formatInt(42), "42"},
		{"int neg", formatInt(-7), "-7"},
		{"int large", formatInt(1234567890), "1234567890"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if tc.got != tc.want {
				t.Errorf("format = %q, want %q", tc.got, tc.want)
			}
		})
	}
}
