// Package rum provides OpenTelemetry Real User Monitoring instrumentation
// for BytePort's HTTP server.
//
// T31: emits BrowserSessionSpan on every LinkClick, scroll-50%, page load.
package rum

import (
	"context"
	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/attribute"
	"go.opentelemetry.io/otel/trace"
)

var tracer = otel.Tracer("byteport-rum")

// LinkClick exports a span when a user clicks a tracked link.
func LinkClick(ctx context.Context, url string) {
	_, span := tracer.Start(ctx, "link.click",
		trace.WithAttributes(attribute.String("link.url", url)))
	span.End()
}

// ScrollDepth exports a span at 50% scroll.
func ScrollDepth(ctx context.Context, percent int) {
	_, span := tracer.Start(ctx, "scroll.depth",
		trace.WithAttributes(attribute.Int("scroll.percent", percent)))
	span.End()
}
