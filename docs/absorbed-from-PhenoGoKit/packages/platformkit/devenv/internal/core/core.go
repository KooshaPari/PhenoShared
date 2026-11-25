// Package core provides core utilities for devenv-abstraction
package core

import (
	"context"
	"fmt"
	"log/slog"
	"os"
	"sync"
	"time"
)

// Logger provides structured logging for the application
type Logger struct {
	*slog.Logger
	mu     sync.Mutex
	output *slog.JSONHandler
}

// LogLevel represents the logging level
type LogLevel string

const (
	LogLevelDebug LogLevel = "debug"
	LogLevelInfo  LogLevel = "info"
	LogLevelWarn  LogLevel = "warn"
	LogLevelError LogLevel = "error"
)

// NewLogger creates a new structured logger
func NewLogger(level LogLevel, pretty bool) *Logger {
	var handler slog.Handler

	opts := &slog.HandlerOptions{
		Level: getSlogLevel(level),
	}

	if pretty {
		handler = slog.NewTextHandler(os.Stdout, opts)
	} else {
		handler = slog.NewJSONHandler(os.Stdout, opts)
	}

	return &Logger{
		Logger: slog.New(handler),
	}
}

func getSlogLevel(level LogLevel) slog.Level {
	switch level {
	case LogLevelDebug:
		return slog.LevelDebug
	case LogLevelInfo:
		return slog.LevelInfo
	case LogLevelWarn:
		return slog.LevelWarn
	case LogLevelError:
		return slog.LevelError
	default:
		return slog.LevelInfo
	}
}

// With returns a logger with additional context
func (l *Logger) With(args ...any) *Logger {
	return &Logger{
		Logger: l.Logger.With(args...),
	}
}

// WithComponent returns a logger with component context
func (l *Logger) WithComponent(component string) *Logger {
	return l.With("component", component)
}

// WithSandbox returns a logger with sandbox context
func (l *Logger) WithSandbox(sandboxID string) *Logger {
	return l.With("sandbox_id", sandboxID)
}

// WithVM returns a logger with VM context
func (l *Logger) WithVM(vmID string) *Logger {
	return l.With("vm_id", vmID)
}

// RetryConfig holds retry configuration
type RetryConfig struct {
	MaxAttempts int
	InitialDelay time.Duration
	MaxDelay     time.Duration
	Multiplier   float64
}

// DefaultRetryConfig returns sensible defaults
func DefaultRetryConfig() *RetryConfig {
	return &RetryConfig{
		MaxAttempts:  3,
		InitialDelay: 100 * time.Millisecond,
		MaxDelay:     5 * time.Second,
		Multiplier:   2.0,
	}
}

// Retry executes a function with retry logic
func Retry(ctx context.Context, config *RetryConfig, fn func() error) error {
	var lastErr error
	delay := config.InitialDelay

	for attempt := 0; attempt < config.MaxAttempts; attempt++ {
		select {
		case <-ctx.Done():
			return ctx.Err()
		default:
		}

		lastErr = fn()
		if lastErr == nil {
			return nil
		}

		if attempt < config.MaxAttempts-1 {
			select {
			case <-ctx.Done():
				return ctx.Err()
			case <-time.After(delay):
			}

			delay = time.Duration(float64(delay) * config.Multiplier)
			if delay > config.MaxDelay {
				delay = config.MaxDelay
			}
		}
	}

	return fmt.Errorf("retry exhausted after %d attempts: %w", config.MaxAttempts, lastErr)
}

// HealthCheck represents a health check function
type HealthCheck func() error

// HealthStatus represents the health status of a component
type HealthStatus struct {
	Name      string    `json:"name"`
	Status    string    `json:"status"`
	Message   string    `json:"message,omitempty"`
	Timestamp time.Time `json:"timestamp"`
	Duration  time.Duration `json:"duration,omitempty"`
}

// HealthMonitor monitors the health of components
type HealthMonitor struct {
	mu        sync.RWMutex
	checks    map[string]HealthCheck
	statuses  map[string]*HealthStatus
	interval  time.Duration
	stopCh    chan struct{}
	wg        sync.WaitGroup
}

// NewHealthMonitor creates a new health monitor
func NewHealthMonitor(interval time.Duration) *HealthMonitor {
	return &HealthMonitor{
		checks:   make(map[string]HealthCheck),
		statuses: make(map[string]*HealthStatus),
		interval: interval,
		stopCh:   make(chan struct{}),
	}
}

// RegisterCheck registers a health check
func (m *HealthMonitor) RegisterCheck(name string, check HealthCheck) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.checks[name] = check
}

// Start starts the health monitor
func (m *HealthMonitor) Start(ctx context.Context) {
	m.wg.Add(1)
	go m.run(ctx)
}

// Stop stops the health monitor
func (m *HealthMonitor) Stop() {
	close(m.stopCh)
	m.wg.Wait()
}

func (m *HealthMonitor) run(ctx context.Context) {
	defer m.wg.Done()

	ticker := time.NewTicker(m.interval)
	defer ticker.Stop()

	// Run initial checks
	m.runChecks()

	for {
		select {
		case <-ctx.Done():
			return
		case <-m.stopCh:
			return
		case <-ticker.C:
			m.runChecks()
		}
	}
}

func (m *HealthMonitor) runChecks() {
	m.mu.Lock()
	defer m.mu.Unlock()

	for name, check := range m.checks {
		start := time.Now()
		err := check()

		status := &HealthStatus{
			Name:      name,
			Timestamp: time.Now(),
			Duration:  time.Since(start),
		}

		if err != nil {
			status.Status = "unhealthy"
			status.Message = err.Error()
		} else {
			status.Status = "healthy"
		}

		m.statuses[name] = status
	}
}

// GetStatus returns the health status of all components
func (m *HealthMonitor) GetStatus() []*HealthStatus {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]*HealthStatus, 0, len(m.statuses))
	for _, status := range m.statuses {
		result = append(result, status)
	}
	return result
}

// GetComponentStatus returns the health status of a specific component
func (m *HealthMonitor) GetComponentStatus(name string) *HealthStatus {
	m.mu.RLock()
	defer m.mu.RUnlock()
	return m.statuses[name]
}

// ResourceLimits holds resource constraints
type ResourceLimits struct {
	CPUQuota    float64 `json:"cpu_quota,omitempty"`    // CPU limit as percentage
	MemoryLimit  int64   `json:"memory_limit,omitempty"` // Memory limit in bytes
	DiskQuota   int64   `json:"disk_quota,omitempty"`  // Disk limit in bytes
	PIDsLimit   int     `json:"pids_limit,omitempty"`   // Max number of processes
	NoNewPrivs  bool    `json:"no_new_privs"`           // Set no_new_privs flag
}

// DefaultResourceLimits returns sensible defaults
func DefaultResourceLimits() *ResourceLimits {
	return &ResourceLimits{
		CPUQuota:   100, // 100% = 1 core
		MemoryLimit: 512 * 1024 * 1024, // 512MB
		DiskQuota:  10 * 1024 * 1024 * 1024, // 10GB
		PIDsLimit:  256,
		NoNewPrivs: true,
	}
}

// Validate validates the resource limits
func (r *ResourceLimits) Validate() error {
	if r.CPUQuota <= 0 || r.CPUQuota > 1000 {
		return fmt.Errorf("CPU quota must be between 0 and 1000")
	}
	if r.MemoryLimit <= 0 {
		return fmt.Errorf("memory limit must be positive")
	}
	if r.DiskQuota <= 0 {
		return fmt.Errorf("disk quota must be positive")
	}
	if r.PIDsLimit <= 0 {
		return fmt.Errorf("PIDs limit must be positive")
	}
	return nil
}
