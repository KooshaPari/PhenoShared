package deployment

import (
	"errors"
	"strings"
	"testing"
)

// TestApplicationError_Error tests Error() method with wrapped error
func TestApplicationError_Error_WithWrappedError(t *testing.T) {
	innerErr := errors.New("database error")
	appErr := &ApplicationError{
		Code:       "TEST_CODE",
		Message:    "test message",
		StatusCode: 500,
		Err:        innerErr,
	}

	errorString := appErr.Error()
	
	if !strings.Contains(errorString, "TEST_CODE") {
		t.Errorf("Expected error to contain code 'TEST_CODE', got: %s", errorString)
	}
	if !strings.Contains(errorString, "test message") {
		t.Errorf("Expected error to contain message 'test message', got: %s", errorString)
	}
	if !strings.Contains(errorString, "database error") {
		t.Errorf("Expected error to contain wrapped error, got: %s", errorString)
	}
}

// TestApplicationError_Error tests Error() method without wrapped error
func TestApplicationError_Error_WithoutWrappedError(t *testing.T) {
	appErr := &ApplicationError{
		Code:       "TEST_CODE",
		Message:    "test message",
		StatusCode: 400,
		Err:        nil,
	}

	errorString := appErr.Error()
	expected := "TEST_CODE: test message"
	
	if errorString != expected {
		t.Errorf("Expected error '%s', got: %s", expected, errorString)
	}
}

// TestApplicationError_Unwrap tests Unwrap() method
func TestApplicationError_Unwrap(t *testing.T) {
	innerErr := errors.New("inner error")
	appErr := &ApplicationError{
		Code:       "TEST_CODE",
		Message:    "test message",
		StatusCode: 500,
		Err:        innerErr,
	}

	unwrapped := appErr.Unwrap()
	if unwrapped != innerErr {
		t.Errorf("Expected unwrapped error to be inner error, got: %v", unwrapped)
	}
}

// TestApplicationError_Unwrap_Nil tests Unwrap() with no wrapped error
func TestApplicationError_Unwrap_Nil(t *testing.T) {
	appErr := &ApplicationError{
		Code:       "TEST_CODE",
		Message:    "test message",
		StatusCode: 400,
		Err:        nil,
	}

	unwrapped := appErr.Unwrap()
	if unwrapped != nil {
		t.Errorf("Expected unwrapped error to be nil, got: %v", unwrapped)
	}
}

// TestNewValidationError tests validation error constructor
func TestNewValidationError(t *testing.T) {
	err := NewValidationError("invalid input")
	
	if err == nil {
		t.Fatal("Expected error to be created, got nil")
	}

	if err.Code != "VALIDATION_ERROR" {
		t.Errorf("Expected code 'VALIDATION_ERROR', got: %s", err.Code)
	}

	if err.StatusCode != StatusBadRequest {
		t.Errorf("Expected status code %d, got: %d", StatusBadRequest, err.StatusCode)
	}

	if err.Message != "invalid input" {
		t.Errorf("Expected message 'invalid input', got: %s", err.Message)
	}
}

// TestNewNotFoundError tests not found error constructor
func TestNewNotFoundError(t *testing.T) {
	err := NewNotFoundError("deployment")
	
	if err == nil {
		t.Fatal("Expected error to be created, got nil")
	}

	if err.Code != "NOT_FOUND" {
		t.Errorf("Expected code 'NOT_FOUND', got: %s", err.Code)
	}

	if err.StatusCode != StatusNotFound {
		t.Errorf("Expected status code %d, got: %d", StatusNotFound, err.StatusCode)
	}

	if !strings.Contains(err.Message, "deployment") {
		t.Errorf("Expected message to contain 'deployment', got: %s", err.Message)
	}
}

// TestNewUnauthorizedError tests unauthorized error constructor
func TestNewUnauthorizedError(t *testing.T) {
	err := NewUnauthorizedError("authentication required")
	
	if err == nil {
		t.Fatal("Expected error to be created, got nil")
	}

	if err.Code != "UNAUTHORIZED" {
		t.Errorf("Expected code 'UNAUTHORIZED', got: %s", err.Code)
	}

	if err.StatusCode != StatusUnauthorized {
		t.Errorf("Expected status code %d, got: %d", StatusUnauthorized, err.StatusCode)
	}

	if err.Message != "authentication required" {
		t.Errorf("Expected message 'authentication required', got: %s", err.Message)
	}
}

// TestNewForbiddenError tests forbidden error constructor
func TestNewForbiddenError(t *testing.T) {
	err := NewForbiddenError("access denied")
	
	if err == nil {
		t.Fatal("Expected error to be created, got nil")
	}

	if err.Code != "FORBIDDEN" {
		t.Errorf("Expected code 'FORBIDDEN', got: %s", err.Code)
	}

	if err.StatusCode != StatusForbidden {
		t.Errorf("Expected status code %d, got: %d", StatusForbidden, err.StatusCode)
	}

	if err.Message != "access denied" {
		t.Errorf("Expected message 'access denied', got: %s", err.Message)
	}
}

// TestNewConflictError tests conflict error constructor
func TestNewConflictError(t *testing.T) {
	err := NewConflictError("resource already exists")
	
	if err == nil {
		t.Fatal("Expected error to be created, got nil")
	}

	if err.Code != "CONFLICT" {
		t.Errorf("Expected code 'CONFLICT', got: %s", err.Code)
	}

	if err.StatusCode != StatusConflict {
		t.Errorf("Expected status code %d, got: %d", StatusConflict, err.StatusCode)
	}

	if err.Message != "resource already exists" {
		t.Errorf("Expected message 'resource already exists', got: %s", err.Message)
	}
}

// TestNewInternalError tests internal error constructor
func TestNewInternalError(t *testing.T) {
	innerErr := errors.New("database connection failed")
	err := NewInternalError("internal server error", innerErr)
	
	if err == nil {
		t.Fatal("Expected error to be created, got nil")
	}

	if err.Code != "INTERNAL_ERROR" {
		t.Errorf("Expected code 'INTERNAL_ERROR', got: %s", err.Code)
	}

	if err.StatusCode != StatusInternalServerError {
		t.Errorf("Expected status code %d, got: %d", StatusInternalServerError, err.StatusCode)
	}

	if err.Message != "internal server error" {
		t.Errorf("Expected message 'internal server error', got: %s", err.Message)
	}

	if err.Err != innerErr {
		t.Errorf("Expected wrapped error to be preserved, got: %v", err.Err)
	}
}

// TestErrorStatusCodes verifies all status codes are correct
func TestErrorStatusCodes(t *testing.T) {
	testCases := []struct {
		name           string
		err            *ApplicationError
		expectedStatus int
	}{
		{
			name:           "Validation Error",
			err:            NewValidationError("test"),
			expectedStatus: 400,
		},
		{
			name:           "Not Found Error",
			err:            NewNotFoundError("test"),
			expectedStatus: 404,
		},
		{
			name:           "Unauthorized Error",
			err:            NewUnauthorizedError("test"),
			expectedStatus: 401,
		},
		{
			name:           "Forbidden Error",
			err:            NewForbiddenError("test"),
			expectedStatus: 403,
		},
		{
			name:           "Conflict Error",
			err:            NewConflictError("test"),
			expectedStatus: 409,
		},
		{
			name:           "Internal Error",
			err:            NewInternalError("test", nil),
			expectedStatus: 500,
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			if tc.err.StatusCode != tc.expectedStatus {
				t.Errorf("Expected status code %d, got: %d", tc.expectedStatus, tc.err.StatusCode)
			}
		})
	}
}

// TestErrorCodes verifies all error codes are unique and consistent
func TestErrorCodes(t *testing.T) {
	testCases := []struct {
		name         string
		err          *ApplicationError
		expectedCode string
	}{
		{
			name:         "Validation Error",
			err:          NewValidationError("test"),
			expectedCode: "VALIDATION_ERROR",
		},
		{
			name:         "Not Found",
			err:          NewNotFoundError("test"),
			expectedCode: "NOT_FOUND",
		},
		{
			name:         "Unauthorized",
			err:          NewUnauthorizedError("test"),
			expectedCode: "UNAUTHORIZED",
		},
		{
			name:         "Forbidden",
			err:          NewForbiddenError("test"),
			expectedCode: "FORBIDDEN",
		},
		{
			name:         "Conflict",
			err:          NewConflictError("test"),
			expectedCode: "CONFLICT",
		},
		{
			name:         "Internal Error",
			err:          NewInternalError("test", nil),
			expectedCode: "INTERNAL_ERROR",
		},
	}

	codes := make(map[string]bool)
	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			if tc.err.Code != tc.expectedCode {
				t.Errorf("Expected code '%s', got: %s", tc.expectedCode, tc.err.Code)
			}

			if codes[tc.err.Code] {
				t.Errorf("Duplicate error code: %s", tc.err.Code)
			}
			codes[tc.err.Code] = true
		})
	}
}

// TestErrorUnwrapping tests error unwrapping with errors.Is and errors.As
func TestErrorUnwrapping(t *testing.T) {
	innerErr := errors.New("database error")
	appErr := NewInternalError("failed operation", innerErr)

	// Test errors.Is
	if !errors.Is(appErr, innerErr) {
		t.Error("Expected errors.Is to find wrapped error")
	}

	// Test errors.As
	var asAppErr *ApplicationError
	if !errors.As(appErr, &asAppErr) {
		t.Error("Expected errors.As to work with ApplicationError")
	}
	if asAppErr.Code != "INTERNAL_ERROR" {
		t.Errorf("Expected code 'INTERNAL_ERROR', got: %s", asAppErr.Code)
	}
}
