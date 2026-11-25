// Package core provides utilities and helpers for devenv-abstraction
package core

import (
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

var (
	// Sandbox metrics
	sandboxCreated = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "devenv_sandbox_created_total",
			Help: "Total number of sandboxes created",
		},
		[]string{"type", "os"},
	)

	sandboxDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "devenv_sandbox_duration_seconds",
			Help:    "Sandbox creation/destruction duration",
			Buckets: prometheus.ExponentialBuckets(0.001, 2, 15),
		},
		[]string{"type", "operation"},
	)

	sandboxErrors = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "devenv_sandbox_errors_total",
			Help: "Total number of sandbox errors",
		},
		[]string{"type", "error_type"},
	)

	// VM metrics
	vmCreated = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "devenv_vm_created_total",
			Help: "Total number of VMs created",
		},
		[]string{"type", "os"},
	)

	vmDuration = promauto.NewHistogramVec(
		prometheus.HistogramOpts{
			Name:    "devenv_vm_duration_seconds",
			Help:    "VM creation/destruction duration",
			Buckets: prometheus.ExponentialBuckets(0.01, 2, 15),
		},
		[]string{"type", "operation"},
	)

	vmErrors = promauto.NewCounterVec(
		prometheus.CounterOpts{
			Name: "devenv_vm_errors_total",
			Help: "Total number of VM errors",
		},
		[]string{"type", "error_type"},
	)

	// Resource metrics
	activeSandboxes = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "devenv_active_sandboxes",
			Help: "Number of currently active sandboxes",
		},
	)

	activeVMs = promauto.NewGauge(
		prometheus.GaugeOpts{
			Name: "devenv_active_vms",
			Help: "Number of currently active VMs",
		},
	)

	// Resource usage
	cpuUsage = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "devenv_cpu_usage_percent",
			Help: "CPU usage by sandbox/VM",
		},
		[]string{"name", "type"},
	)

	memoryUsage = promauto.NewGaugeVec(
		prometheus.GaugeOpts{
			Name: "devenv_memory_usage_bytes",
			Help: "Memory usage by sandbox/VM",
		},
		[]string{"name", "type"},
	)
)

// MetricsCollector provides a simple metrics API without Prometheus
type MetricsCollector struct {
	mu         sync.RWMutex
	sandboxes  map[string]*SandboxMetrics
	vms        map[string]*VMMetrics
	httpServer *http.Server
}

// SandboxMetrics tracks metrics for a single sandbox
type SandboxMetrics struct {
	Name      string
	Type      string
	OS        string
	CreatedAt time.Time
	Duration  time.Duration
	CPUUsage  float64
	MemUsage  uint64
}

// VMMetrics tracks metrics for a single VM
type VMMetrics struct {
	Name      string
	Type      string
	OS        string
	CreatedAt time.Time
	Duration  time.Duration
	CPUUsage  float64
	MemUsage  uint64
}

// MetricsSnapshot is a point-in-time snapshot of all metrics
type MetricsSnapshot struct {
	Timestamp      time.Time `json:"timestamp"`
	ActiveSandbox  int       `json:"active_sandboxes"`
	ActiveVMs      int       `json:"active_vms"`
	TotalSandbox   int64     `json:"total_sandbox_created"`
	TotalVMs       int64     `json:"total_vms_created"`
	SandboxErrors  int64     `json:"total_sandbox_errors"`
	VMErrors       int64     `json:"total_vm_errors"`
	TopSandboxes   []string  `json:"top_sandboxes_by_memory"`
	TopVMs         []string  `json:"top_vms_by_memory"`
}

// NewMetricsCollector creates a new metrics collector
func NewMetricsCollector(addr string) *MetricsCollector {
	m := &MetricsCollector{
		sandboxes: make(map[string]*SandboxMetrics),
		vms:       make(map[string]*VMMetrics),
	}

	if addr != "" {
		mux := http.NewServeMux()
		mux.Handle("/metrics", promhttp.Handler())
		mux.HandleFunc("/health", m.healthHandler)
		mux.HandleFunc("/snapshot", m.snapshotHandler)

		m.httpServer = &http.Server{
			Addr:    addr,
			Handler: mux,
		}

		go m.httpServer.ListenAndServe()
	}

	return m
}

// Close shuts down the metrics collector
func (m *MetricsCollector) Close() error {
	if m.httpServer != nil {
		return m.httpServer.Close()
	}
	return nil
}

func (m *MetricsCollector) healthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte(`{"status":"ok"}`))
}

func (m *MetricsCollector) snapshotHandler(w http.ResponseWriter, r *http.Request) {
	snapshot := m.Snapshot()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(snapshot)
}

// RecordSandboxCreated records a new sandbox creation
func (m *MetricsCollector) RecordSandboxCreated(name, sandboxType, os string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	metrics := &SandboxMetrics{
		Name:      name,
		Type:      sandboxType,
		OS:        os,
		CreatedAt: time.Now(),
	}
	m.sandboxes[name] = metrics
	activeSandboxes.Inc()
	sandboxCreated.WithLabelValues(sandboxType, os).Inc()
}

// RecordSandboxDestroyed records sandbox destruction
func (m *MetricsCollector) RecordSandboxDestroyed(name string, duration time.Duration) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if metrics, ok := m.sandboxes[name]; ok {
		metrics.Duration = duration
		sandboxDuration.WithLabelValues(metrics.Type, "destroy").Observe(duration.Seconds())
		activeSandboxes.Dec()
		delete(m.sandboxes, name)
	}
}

// RecordSandboxError records a sandbox error
func (m *MetricsCollector) RecordSandboxError(sandboxType, errorType string) {
	sandboxErrors.WithLabelValues(sandboxType, errorType).Inc()
}

// UpdateSandboxUsage updates CPU and memory usage for a sandbox
func (m *MetricsCollector) UpdateSandboxUsage(name string, cpu float64, mem uint64) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if metrics, ok := m.sandboxes[name]; ok {
		metrics.CPUUsage = cpu
		metrics.MemUsage = mem
		cpuUsage.WithLabelValues(name, "sandbox").Set(cpu)
		memoryUsage.WithLabelValues(name, "sandbox").Set(float64(mem))
	}
}

// RecordVMCreated records a new VM creation
func (m *MetricsCollector) RecordVMCreated(name, vmType, os string) {
	m.mu.Lock()
	defer m.mu.Unlock()

	metrics := &VMMetrics{
		Name:      name,
		Type:      vmType,
		OS:        os,
		CreatedAt: time.Now(),
	}
	m.vms[name] = metrics
	activeVMs.Inc()
	vmCreated.WithLabelValues(vmType, os).Inc()
}

// RecordVMDestroyed records VM destruction
func (m *MetricsCollector) RecordVMDestroyed(name string, duration time.Duration) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if metrics, ok := m.vms[name]; ok {
		metrics.Duration = duration
		vmDuration.WithLabelValues(metrics.Type, "destroy").Observe(duration.Seconds())
		activeVMs.Dec()
		delete(m.vms, name)
	}
}

// RecordVMError records a VM error
func (m *MetricsCollector) RecordVMError(vmType, errorType string) {
	vmErrors.WithLabelValues(vmType, errorType).Inc()
}

// UpdateVMUsage updates CPU and memory usage for a VM
func (m *MetricsCollector) UpdateVMUsage(name string, cpu float64, mem uint64) {
	m.mu.Lock()
	defer m.mu.Unlock()

	if metrics, ok := m.vms[name]; ok {
		metrics.CPUUsage = cpu
		metrics.MemUsage = mem
		cpuUsage.WithLabelValues(name, "vm").Set(cpu)
		memoryUsage.WithLabelValues(name, "vm").Set(float64(mem))
	}
}

// Snapshot returns a point-in-time snapshot of all metrics
func (m *MetricsCollector) Snapshot() MetricsSnapshot {
	m.mu.RLock()
	defer m.mu.RUnlock()

	snapshot := MetricsSnapshot{
		Timestamp:     time.Now(),
		ActiveSandbox: len(m.sandboxes),
		ActiveVMs:      len(m.vms),
	}

	// Find top sandboxes by memory
	for _, s := range m.sandboxes {
		snapshot.TopSandboxes = append(snapshot.TopSandboxes, s.Name)
	}

	// Find top VMs by memory
	for _, v := range m.vms {
		snapshot.TopVMs = append(snapshot.TopVMs, v.Name)
	}

	return snapshot
}

// GetSandboxMetrics returns metrics for a specific sandbox
func (m *MetricsCollector) GetSandboxMetrics(name string) (*SandboxMetrics, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	metrics, ok := m.sandboxes[name]
	return metrics, ok
}

// GetVMMetrics returns metrics for a specific VM
func (m *MetricsCollector) GetVMMetrics(name string) (*VMMetrics, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	metrics, ok := m.vms[name]
	return metrics, ok
}

// RecordSandboxDuration records the duration of a sandbox operation
func RecordSandboxDuration(sandboxType, operation string, duration time.Duration) {
	sandboxDuration.WithLabelValues(sandboxType, operation).Observe(duration.Seconds())
}

// RecordVMDuration records the duration of a VM operation
func RecordVMDuration(vmType, operation string, duration time.Duration) {
	vmDuration.WithLabelValues(vmType, operation).Observe(duration.Seconds())
}

// StartMetricsServer starts a background HTTP server for metrics
func StartMetricsServer(ctx context.Context, addr string) (*http.Server, error) {
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprintf(w, `{"status":"ok","service":"devenv-abstraction"}`)
	})

	server := &http.Server{Addr: addr, Handler: mux}

	go func() {
		<-ctx.Done()
		server.Shutdown(context.Background())
	}()

	return server, server.ListenAndServe()
}
