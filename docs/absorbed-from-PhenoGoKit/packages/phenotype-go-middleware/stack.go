// Package middleware provides shared HTTP middleware utilities for Phenotype services.
package middleware

import (
	"fmt"
	"net/http"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
	"github.com/go-chi/cors"
	"github.com/google/uuid"
	log "github.com/sirupsen/logrus"
)

// DefaultMiddlewareStack applies a standard set of middleware to a chi router.
// It includes recovery, logging, CORS, and request ID tracking.
//
// The stack includes:
// - chi/middleware.Recoverer: Panic recovery middleware
// - chi/middleware.Logger: Request logging middleware
// - CORS middleware: Cross-origin resource sharing support
// - Request ID middleware: Unique request ID tracking
//
// Parameters:
//   - router: The chi router to apply middleware to
//
// Returns:
//   - error: An error if middleware setup fails, nil otherwise
func DefaultMiddlewareStack(router *chi.Mux) error {
	// Add panic recovery middleware
	router.Use(middleware.Recoverer)

	// Add request logging middleware
	router.Use(RequestLogger)

	// Add CORS middleware with default permissive settings
	router.Use(cors.Handler(cors.Options{
		AllowedOrigins:   []string{"*"},
		AllowedMethods:   []string{"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"},
		AllowedHeaders:   []string{"Accept", "Authorization", "Content-Type", "X-CSRF-Token", "X-Request-ID"},
		ExposedHeaders:   []string{"X-Request-ID"},
		AllowCredentials: false,
		MaxAge:           300,
	}))

	// Add request ID middleware
	router.Use(RequestIDMiddleware)

	return nil
}

// RequestLogger logs HTTP requests using logrus.
// Logs include method, path, status code, duration, and size.
func RequestLogger(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		startTime := time.Now()

		// Create a wrapper to capture the response status and size
		wrapped := &responseWriter{
			ResponseWriter: w,
			statusCode:     http.StatusOK,
		}

		// Call the next handler
		next.ServeHTTP(wrapped, r)

		// Log the request details
		duration := time.Since(startTime)
		log.WithFields(log.Fields{
			"method":     r.Method,
			"path":       r.RequestURI,
			"status":     wrapped.statusCode,
			"duration_ms": duration.Milliseconds(),
			"size_bytes": wrapped.size,
		}).Debug("HTTP request")
	})
}

// RequestIDMiddleware adds a unique request ID to each request context.
// If a request does not have an X-Request-ID header, a new UUID is generated.
func RequestIDMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		requestID := r.Header.Get("X-Request-ID")
		if requestID == "" {
			requestID = uuid.New().String()
		}

		// Set the request ID in the response header
		w.Header().Set("X-Request-ID", requestID)

		// Log the request ID
		log.WithFields(log.Fields{
			"request_id": requestID,
			"method":     r.Method,
			"path":       r.RequestURI,
		}).Trace("Request assigned ID")

		next.ServeHTTP(w, r)
	})
}

// responseWriter wraps http.ResponseWriter to capture status code and body size.
type responseWriter struct {
	http.ResponseWriter
	statusCode int
	size       int
}

// WriteHeader captures the HTTP status code.
func (rw *responseWriter) WriteHeader(statusCode int) {
	rw.statusCode = statusCode
	rw.ResponseWriter.WriteHeader(statusCode)
}

// Write captures the number of bytes written.
func (rw *responseWriter) Write(b []byte) (int, error) {
	size, err := rw.ResponseWriter.Write(b)
	rw.size += size
	return size, err
}

// HealthCheckHandler returns a simple health check handler.
// This is commonly used for liveness probes in Kubernetes or other orchestration systems.
func HealthCheckHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = fmt.Fprintf(w, `{"status":"ok","timestamp":"%s"}`, time.Now().UTC().Format(time.RFC3339))
}

// ReadinessCheckHandler returns a readiness check handler.
// This can be extended to check dependencies like databases.
func ReadinessCheckHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	_, _ = fmt.Fprintf(w, `{"ready":true,"timestamp":"%s"}`, time.Now().UTC().Format(time.RFC3339))
}
