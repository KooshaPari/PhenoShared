package cloud

import (
	"context"
	"errors"
	"fmt"
	"time"
)

// ErrorCategory classifies cloud provider errors for consistent handling
type ErrorCategory string

const (
	ErrorCategoryAuthentication ErrorCategory = "AUTHENTICATION"
	ErrorCategoryQuota          ErrorCategory = "QUOTA"
	ErrorCategoryValidation     ErrorCategory = "VALIDATION"
	ErrorCategoryNotFound       ErrorCategory = "NOT_FOUND"
	ErrorCategoryConflict       ErrorCategory = "CONFLICT"
	ErrorCategoryProvisioning   ErrorCategory = "PROVISIONING"
	ErrorCategoryNetwork        ErrorCategory = "NETWORK"
	ErrorCategoryInternal       ErrorCategory = "INTERNAL"
	ErrorCategoryNotSupported   ErrorCategory = "NOT_SUPPORTED"
)

// CloudError is the base error type for all cloud provider errors
type CloudError struct {
	Category   ErrorCategory     `json:"category"`
	Code       string            `json:"code"`
	Message    string            `json:"message"`
	Provider   string            `json:"provider,omitempty"`
	ResourceID string            `json:"resource_id,omitempty"`
	Retryable  bool              `json:"retryable"`
	StatusCode int               `json:"status_code,omitempty"`
	Metadata   map[string]string `json:"metadata,omitempty"`
	Cause      error             `json:"-"`
}

// Error implements the error interface
func (e *CloudError) Error() string {
	if e.Provider != "" {
		return fmt.Sprintf("[%s/%s] %s: %s", e.Provider, e.Category, e.Code, e.Message)
	}
	return fmt.Sprintf("[%s] %s: %s", e.Category, e.Code, e.Message)
}

// Unwrap returns the underlying error
func (e *CloudError) Unwrap() error {
	return e.Cause
}

// Is checks if the error matches the target
func (e *CloudError) Is(target error) bool {
	t, ok := target.(*CloudError)
	if !ok {
		return false
	}
	return e.Category == t.Category && e.Code == t.Code
}

// AuthenticationError indicates credential or permission issues
type AuthenticationError struct {
	*CloudError
}

// NewAuthenticationError creates a new authentication error
func NewAuthenticationError(provider, message string, cause error) *AuthenticationError {
	return &AuthenticationError{
		CloudError: &CloudError{
			Category:  ErrorCategoryAuthentication,
			Code:      "AUTH_FAILED",
			Message:   message,
			Provider:  provider,
			Retryable: false,
			Cause:     cause,
		},
	}
}

// QuotaError indicates resource or rate limits exceeded
type QuotaError struct {
	*CloudError
	Limit     int64     `json:"limit"`
	Current   int64     `json:"current"`
	ResetTime time.Time `json:"reset_time,omitempty"`
}

// NewQuotaError creates a new quota error
func NewQuotaError(provider, message string, limit, current int64, resetTime time.Time) *QuotaError {
	return &QuotaError{
		CloudError: &CloudError{
			Category:  ErrorCategoryQuota,
			Code:      "QUOTA_EXCEEDED",
			Message:   message,
			Provider:  provider,
			Retryable: true,
		},
		Limit:     limit,
		Current:   current,
		ResetTime: resetTime,
	}
}

// ValidationError indicates invalid configuration or input
type ValidationError struct {
	*CloudError
	Field string `json:"field,omitempty"`
}

// NewValidationError creates a new validation error
func NewValidationError(provider, field, message string) *ValidationError {
	return &ValidationError{
		CloudError: &CloudError{
			Category:  ErrorCategoryValidation,
			Code:      "INVALID_CONFIG",
			Message:   message,
			Provider:  provider,
			Retryable: false,
		},
		Field: field,
	}
}

// ResourceNotFoundError indicates a resource doesn't exist
type ResourceNotFoundError struct {
	*CloudError
}

// NewResourceNotFoundError creates a new resource not found error
func NewResourceNotFoundError(provider, resourceID string) *ResourceNotFoundError {
	return &ResourceNotFoundError{
		CloudError: &CloudError{
			Category:   ErrorCategoryNotFound,
			Code:       "RESOURCE_NOT_FOUND",
			Message:    fmt.Sprintf("Resource '%s' not found", resourceID),
			Provider:   provider,
			ResourceID: resourceID,
			Retryable:  false,
		},
	}
}

// ConflictError indicates a resource conflict (e.g., already exists)
type ConflictError struct {
	*CloudError
	ConflictingResource string `json:"conflicting_resource,omitempty"`
}

// NewConflictError creates a new conflict error
func NewConflictError(provider, message, conflictingResource string) *ConflictError {
	return &ConflictError{
		CloudError: &CloudError{
			Category:  ErrorCategoryConflict,
			Code:      "RESOURCE_CONFLICT",
			Message:   message,
			Provider:  provider,
			Retryable: false,
		},
		ConflictingResource: conflictingResource,
	}
}

// ProvisioningError indicates resource creation/modification failed
type ProvisioningError struct {
	*CloudError
	Phase string `json:"phase,omitempty"` // building, deploying, health_check, etc.
}

// NewProvisioningError creates a new provisioning error
func NewProvisioningError(provider, phase, message string, cause error) *ProvisioningError {
	return &ProvisioningError{
		CloudError: &CloudError{
			Category:  ErrorCategoryProvisioning,
			Code:      "PROVISIONING_FAILED",
			Message:   message,
			Provider:  provider,
			Retryable: true,
			Cause:     cause,
		},
		Phase: phase,
	}
}

// NetworkError indicates connection or network issues
type NetworkError struct {
	*CloudError
	Endpoint string `json:"endpoint,omitempty"`
}

// NewNetworkError creates a new network error
func NewNetworkError(provider, endpoint, message string, cause error) *NetworkError {
	return &NetworkError{
		CloudError: &CloudError{
			Category:  ErrorCategoryNetwork,
			Code:      "NETWORK_ERROR",
			Message:   message,
			Provider:  provider,
			Retryable: true,
			Cause:     cause,
		},
		Endpoint: endpoint,
	}
}

// InternalProviderError indicates a provider-side error
type InternalProviderError struct {
	*CloudError
}

// NewInternalProviderError creates a new internal provider error
func NewInternalProviderError(provider, message string, statusCode int, cause error) *InternalProviderError {
	return &InternalProviderError{
		CloudError: &CloudError{
			Category:   ErrorCategoryInternal,
			Code:       "PROVIDER_ERROR",
			Message:    message,
			Provider:   provider,
			Retryable:  true,
			StatusCode: statusCode,
			Cause:      cause,
		},
	}
}

// NotSupportedError indicates an operation is not supported by the provider
type NotSupportedError struct {
	*CloudError
	Operation string `json:"operation"`
}

// NewNotSupportedError creates a new not supported error
func NewNotSupportedError(provider, operation string) *NotSupportedError {
	return &NotSupportedError{
		CloudError: &CloudError{
			Category:  ErrorCategoryNotSupported,
			Code:      "NOT_SUPPORTED",
			Message:   fmt.Sprintf("Operation '%s' not supported by provider", operation),
			Provider:  provider,
			Retryable: false,
		},
		Operation: operation,
	}
}

// Common sentinel errors for quick checks
var (
	ErrNotSupported       = errors.New("operation not supported")
	ErrInvalidCredentials = errors.New("invalid credentials")
	ErrResourceNotFound   = errors.New("resource not found")
	ErrQuotaExceeded      = errors.New("quota exceeded")
	ErrInvalidConfig      = errors.New("invalid configuration")
	ErrConflict           = errors.New("resource conflict")
	ErrTimeout            = errors.New("operation timeout")
	ErrCancelled          = errors.New("operation cancelled")
)

// RetryConfig defines retry behavior
type RetryConfig struct {
	MaxRetries      int             `json:"max_retries"`
	InitialDelay    time.Duration   `json:"initial_delay"`
	MaxDelay        time.Duration   `json:"max_delay"`
	Multiplier      float64         `json:"multiplier"`
	Jitter          bool            `json:"jitter"`
	RetryableErrors []ErrorCategory `json:"retryable_errors"`
}

// DefaultRetryConfig provides sensible defaults for retries
var DefaultRetryConfig = RetryConfig{
	MaxRetries:   5,
	InitialDelay: 1 * time.Second,
	MaxDelay:     16 * time.Second,
	Multiplier:   2.0,
	Jitter:       true,
	RetryableErrors: []ErrorCategory{
		ErrorCategoryQuota,
		ErrorCategoryProvisioning,
		ErrorCategoryNetwork,
		ErrorCategoryInternal,
	},
}

// ShouldRetry determines if an error should be retried
func ShouldRetry(err error, config RetryConfig) bool {
	if err == nil {
		return false
	}

	// Check for specific error types that embed CloudError
	var networkErr *NetworkError
	if errors.As(err, &networkErr) {
		if !networkErr.Retryable {
			return false
		}
		for _, category := range config.RetryableErrors {
			if networkErr.Category == category {
				return true
			}
		}
	}

	var provisioningErr *ProvisioningError
	if errors.As(err, &provisioningErr) {
		if !provisioningErr.Retryable {
			return false
		}
		for _, category := range config.RetryableErrors {
			if provisioningErr.Category == category {
				return true
			}
		}
	}

	var quotaErr *QuotaError
	if errors.As(err, &quotaErr) {
		if !quotaErr.Retryable {
			return false
		}
		for _, category := range config.RetryableErrors {
			if quotaErr.Category == category {
				return true
			}
		}
	}

	var internalErr *InternalProviderError
	if errors.As(err, &internalErr) {
		if !internalErr.Retryable {
			return false
		}
		for _, category := range config.RetryableErrors {
			if internalErr.Category == category {
				return true
			}
		}
	}

	// Fall back to generic CloudError check
	var cloudErr *CloudError
	if errors.As(err, &cloudErr) {
		if !cloudErr.Retryable {
			return false
		}
		for _, category := range config.RetryableErrors {
			if cloudErr.Category == category {
				return true
			}
		}
	}

	// Network errors and timeouts are generally retryable
	if errors.Is(err, ErrTimeout) || errors.Is(err, context.DeadlineExceeded) {
		return true
	}

	return false
}

// CalculateBackoff calculates the next retry delay with exponential backoff
func CalculateBackoff(attempt int, config RetryConfig) time.Duration {
	if attempt >= config.MaxRetries {
		return 0
	}

	delay := config.InitialDelay
	for i := 0; i < attempt; i++ {
		delay = time.Duration(float64(delay) * config.Multiplier)
		if delay > config.MaxDelay {
			delay = config.MaxDelay
			break
		}
	}

	if config.Jitter {
		// Add up to 25% jitter
		jitter := time.Duration(float64(delay) * 0.25 * (0.5 - (float64(time.Now().UnixNano()%1000) / 2000.0)))
		delay += jitter
	}

	return delay
}

// WrapError wraps a generic error as a CloudError
func WrapError(provider string, category ErrorCategory, message string, err error) *CloudError {
	return &CloudError{
		Category: category,
		Code:     string(category),
		Message:  message,
		Provider: provider,
		Retryable: category == ErrorCategoryNetwork ||
			category == ErrorCategoryProvisioning ||
			category == ErrorCategoryInternal ||
			category == ErrorCategoryQuota,
		Cause: err,
	}
}
