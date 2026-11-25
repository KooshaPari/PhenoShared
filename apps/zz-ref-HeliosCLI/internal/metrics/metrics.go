package metrics

import (
	"fmt"
	"sync"
	"time"
)

// MetricType identifies the kind of metric.
type MetricType string

const (
	Counter   MetricType = "counter"
	Gauge     MetricType = "gauge"
	Histogram MetricType = "histogram"
)

// Metric is a single measurement point.
type Metric struct {
	Name      string
	Type      MetricType
	Value     float64
	Timestamp time.Time
	Labels    map[string]string
}

// Collector is a thread-safe in-memory metrics collector.
type Collector struct {
	mu      sync.RWMutex
	metrics map[string][]Metric
}

// NewCollector creates a new metrics collector.
func NewCollector() *Collector {
	return &Collector{
		metrics: make(map[string][]Metric),
	}
}

// Record adds a metric measurement.
func (c *Collector) Record(name string, mtype MetricType, value float64, labels map[string]string) {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.metrics[name] = append(c.metrics[name], Metric{
		Name:      name,
		Type:      mtype,
		Value:     value,
		Timestamp: time.Now(),
		Labels:    labels,
	})
}

// Get returns all measurements for a metric name.
func (c *Collector) Get(name string) []Metric {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.metrics[name]
}

// Summary returns aggregated statistics for a metric.
func (c *Collector) Summary(name string) (count int, sum float64, min float64, max float64) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	metrics := c.metrics[name]
	if len(metrics) == 0 {
		return 0, 0, 0, 0
	}
	min = metrics[0].Value
	max = metrics[0].Value
	for _, m := range metrics {
		count++
		sum += m.Value
		if m.Value < min {
			min = m.Value
		}
		if m.Value > max {
			max = m.Value
		}
	}
	return
}

// Reset clears all collected metrics.
func (c *Collector) Reset() {
	c.mu.Lock()
	defer c.mu.Unlock()
	c.metrics = make(map[string][]Metric)
}

// PrintSummary outputs a human-readable summary.
func (c *Collector) PrintSummary(name string) string {
	count, sum, min, max := c.Summary(name)
	if count == 0 {
		return fmt.Sprintf("%s: no data", name)
	}
	avg := sum / float64(count)
	return fmt.Sprintf("%s: count=%d avg=%.2f min=%.2f max=%.2f", name, count, avg, min, max)
}
