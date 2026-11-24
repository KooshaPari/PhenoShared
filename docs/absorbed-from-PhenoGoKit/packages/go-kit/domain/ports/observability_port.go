// Package ports - ObservabilityPort composite interface.
//
// ObservabilityPort composes the individual observability ports
// (LoggerPort, MetricsPort, TracerPort) into a single interface for
// application services that want a single dependency rather than three.
//
// This is a thin facade — concrete adapters can implement it by
// delegating to existing logger / metrics / tracer adapters, or a
// single composite adapter can implement all three methods directly.
package ports

import "context"

// ObservabilityPort provides structured logging, metrics collection,
// and distributed tracing under a single interface.
//
// Implementations may satisfy all three methods or compose delegates.
// The RecordError helper is provided as a one-line convenience that
// combines log + span error annotation for the common failure path.
type ObservabilityPort interface {
	// LogError records an error message with the given fields.
	// Equivalent to LoggerPort.Error(msg, fields...).
	LogError(msg string, fields ...Field)

	// IncrementCounter increments a counter metric by 1.
	// Equivalent to MetricsPort.Counter(name, labels).Inc().
	IncrementCounter(name string, labels map[string]string)

	// RecordError annotates the current span with err and logs it.
	// Equivalent to SpanPort.RecordError(err) + LogError(msg, Error(err)).
	RecordError(ctx context.Context, operation string, err error, fields ...Field)
}
