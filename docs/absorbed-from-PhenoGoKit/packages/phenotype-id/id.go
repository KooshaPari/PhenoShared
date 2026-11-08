// Package id provides UUID generation utilities for Phenotype services.
package id

import (
	"fmt"

	"github.com/google/uuid"
)

// Generator provides methods for generating unique identifiers.
type Generator struct{}

// NewGenerator creates a new ID generator.
func NewGenerator() *Generator {
	return &Generator{}
}

// GenerateUUID generates a new random UUID v4.
func (g *Generator) GenerateUUID() string {
	return uuid.New().String()
}

// GenerateRequestID generates a new request ID using UUID v4.
func (g *Generator) GenerateRequestID() string {
	return fmt.Sprintf("req-%s", uuid.New().String())
}

// GenerateTraceID generates a new trace ID using UUID v4.
func (g *Generator) GenerateTraceID() string {
	return fmt.Sprintf("trace-%s", uuid.New().String())
}

// GenerateCorrelationID generates a new correlation ID using UUID v4.
func (g *Generator) GenerateCorrelationID() string {
	return fmt.Sprintf("corr-%s", uuid.New().String())
}

// IsValidUUID checks if the given string is a valid UUID.
func (g *Generator) IsValidUUID(id string) bool {
	_, err := uuid.Parse(id)
	return err == nil
}
