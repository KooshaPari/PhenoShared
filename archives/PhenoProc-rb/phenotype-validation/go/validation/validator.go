package validation

import (
	"encoding/json"
	"fmt"
)

// ValidationResult represents the result of validation
type ValidationResult struct {
	IsValid  bool     `json:"isValid"`
	Errors   []string `json:"errors,omitempty"`
	Warnings []string `json:"warnings,omitempty"`
}

// JSONSchemaValidator validates JSON against JSON Schema
type JSONSchemaValidator struct {
	schemas map[string]interface{}
}

// NewJSONSchemaValidator creates a new validator
func NewJSONSchemaValidator() *JSONSchemaValidator {
	return &JSONSchemaValidator{
		schemas: make(map[string]interface{}),
	}
}

// Validate validates a JSON document against a schema
func (v *JSONSchemaValidator) Validate(schemaJSON, documentJSON string) (*ValidationResult, error) {
	result := &ValidationResult{IsValid: true}
	
	// Parse schema
	var schema map[string]interface{}
	if err := json.Unmarshal([]byte(schemaJSON), &schema); err != nil {
		result.IsValid = false
		result.Errors = append(result.Errors, fmt.Sprintf("Invalid schema: %v", err))
		return result, nil
	}
	
	// Parse document
	var document map[string]interface{}
	if err := json.Unmarshal([]byte(documentJSON), &document); err != nil {
		result.IsValid = false
		result.Errors = append(result.Errors, fmt.Sprintf("Invalid document: %v", err))
		return result, nil
	}
	
	// Basic type validation
	if docType, ok := document["type"].(string); ok {
		if schemaType, ok := schema["type"].(string); ok && docType != schemaType {
			result.IsValid = false
			result.Errors = append(result.Errors, 
				fmt.Sprintf("Type mismatch: expected %s, got %s", schemaType, docType))
		}
	}
	
	return result, nil
}

// AddSchema adds a named schema to the cache
func (v *JSONSchemaValidator) AddSchema(name, schemaJSON string) error {
	var schema map[string]interface{}
	if err := json.Unmarshal([]byte(schemaJSON), &schema); err != nil {
		return err
	}
	v.schemas[name] = schema
	return nil
}

// ValidateAgainstSchema validates against a named cached schema
func (v *JSONSchemaValidator) ValidateAgainstSchema(documentJSON, schemaName string) (*ValidationResult, error) {
	schema, ok := v.schemas[schemaName]
	if !ok {
		return &ValidationResult{
			IsValid: false,
			Errors:  []string{fmt.Sprintf("Schema '%s' not found", schemaName)},
		}, nil
	}
	
	schemaJSON, _ := json.Marshal(schema)
	return v.Validate(string(schemaJSON), documentJSON)
}
