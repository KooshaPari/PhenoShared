package routes

import (
	"fmt"
	"net/http"
	"runtime"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gin-gonic/gin"
)

// metrics holds application-level counters.
var metrics = struct {
	mu            sync.RWMutex
	requestCount  atomic.Int64
	errorCount    atomic.Int64
	deployCount   atomic.Int64
	startTime     time.Time
	sandboxActive atomic.Int64
}{
	startTime: time.Now(),
}

// recordRequest increments the request counter.
func recordRequest() {
	metrics.requestCount.Add(1)
}

// recordError increments the error counter.
func recordError() {
	metrics.errorCount.Add(1)
}

// recordDeploy increments the deploy counter.
func recordDeploy() {
	metrics.deployCount.Add(1)
	metrics.sandboxActive.Add(1)
}

// recordSandboxStopped decrements the active sandbox counter.
func recordSandboxStopped() {
	metrics.sandboxActive.Add(-1)
}

// MetricsMiddleware records the total request count and the error count for
// every request handled by the engine.
func MetricsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		recordRequest()
		c.Next()
		if c.Writer.Status() >= http.StatusBadRequest {
			recordError()
		}
	}
}

// MetricsHandler exposes application metrics in Prometheus text format.
func MetricsHandler(c *gin.Context) {
	var m runtime.MemStats
	runtime.ReadMemStats(&m)

	uptime := time.Since(metrics.startTime).Seconds()
	reqCount := metrics.requestCount.Load()
	errCount := metrics.errorCount.Load()
	depCount := metrics.deployCount.Load()
	active := metrics.sandboxActive.Load()

	output := `# HELP byteport_uptime_seconds Server uptime in seconds.
# TYPE byteport_uptime_seconds gauge
byteport_uptime_seconds ` + formatFloat(uptime) + `
# HELP byteport_requests_total Total HTTP requests processed.
# TYPE byteport_requests_total counter
byteport_requests_total ` + formatInt(reqCount) + `
# HELP byteport_errors_total Total HTTP errors.
# TYPE byteport_errors_total counter
byteport_errors_total ` + formatInt(errCount) + `
# HELP byteport_deploys_total Total deploy operations.
# TYPE byteport_deploys_total counter
byteport_deploys_total ` + formatInt(depCount) + `
# HELP byteport_sandboxes_active Currently active sandboxes.
# TYPE byteport_sandboxes_active gauge
byteport_sandboxes_active ` + formatInt(active) + `
# HELP byteport_memory_alloc_bytes Current memory allocation.
# TYPE byteport_memory_alloc_bytes gauge
byteport_memory_alloc_bytes ` + formatInt(int64(m.Alloc)) + `
# HELP byteport_memory_sys_bytes Total memory obtained from OS.
# TYPE byteport_memory_sys_bytes gauge
byteport_memory_sys_bytes ` + formatInt(int64(m.Sys)) + `
# HELP byteport_goroutines Number of goroutines.
# TYPE byteport_goroutines gauge
byteport_goroutines ` + formatInt(int64(runtime.NumGoroutine())) + `
`

	c.Data(http.StatusOK, "text/plain; version=0.0.4; charset=utf-8", []byte(output))
}

// HealthHandler returns a simple health check response.
func HealthHandler(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "healthy",
		"service": "byteport",
		"uptime":  time.Since(metrics.startTime).String(),
	})
}

func formatFloat(f float64) string {
	return fmt.Sprintf("%.2f", f)
}

func formatInt(n int64) string {
	return fmt.Sprintf("%d", n)
}
