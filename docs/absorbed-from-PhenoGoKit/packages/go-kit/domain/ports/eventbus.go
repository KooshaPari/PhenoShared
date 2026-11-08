// Package ports - EventBusPort for in-process event publishing.
//
// This interface is consumed by application services (e.g. FeatureService)
// to publish domain events without coupling to a specific messaging
// implementation. Adapters implementing this port are responsible for
// routing the event to a broker (Kafka, NATS, in-process bus, etc.).
package ports

import "context"

// EventBusPort publishes domain events to subscribers.
//
// Implementations should be non-blocking on the happy path (the caller
// does not need to wait for delivery) and must never block the caller
// on transient broker errors — log and drop is the standard policy.
type EventBusPort interface {
	// Publish publishes a single event under the given topic.
	//
	// topic is a stable, lowercase identifier that subscribers subscribe to
	// (e.g. "feature.created", "feature.updated", "feature.deleted").
	//
	// payload is an opaque, JSON-serializable value describing the event.
	// Callers should prefer struct types so the payload shape is documented
	// in code; callers using `any`/`map[string]any` are responsible for
	// shape stability across versions.
	Publish(ctx context.Context, topic string, payload any) error
}
