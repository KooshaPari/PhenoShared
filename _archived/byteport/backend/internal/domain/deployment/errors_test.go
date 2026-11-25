package deployment

import (
	"errors"
	"strings"
	"testing"
)

// TestDomainError_Error tests Error() method with wrapped error
func TestDomainError_Error_WithWrappedError(t *testing.T) {
	innerErr := errors.New("inner error")
	domainErr := &DomainError{
		Code:    "TEST_CODE",
		Message: "test message",
		Err:     innerErr,
	}

	errorString := domainErr.Error()
	
	if !strings.Contains(errorString, "TEST_CODE") {
		t.Errorf("Expected error to contain code 'TEST_CODE', got: %s", errorString)
	}
	if !strings.Contains(errorString, "test message") {
		t.Errorf("Expected error to contain message 'test message', got: %s", errorString)
	}
	if !strings.Contains(errorString, "inner error") {
		t.Errorf("Expected error to contain wrapped error 'inner error', got: %s", errorString)
	}
}

// TestDomainError_Error tests Error() method without wrapped error
func TestDomainError_Error_WithoutWrappedError(t *testing.T) {
	domainErr := &DomainError{
		Code:    "TEST_CODE",
		Message: "test message",
		Err:     nil,
	}

	errorString := domainErr.Error()
	expected := "TEST_CODE: test message"
	
	if errorString != expected {
		t.Errorf("Expected error '%s', got: %s", expected, errorString)
	}
}

// TestDomainError_Unwrap tests Unwrap() method
func TestDomainError_Unwrap(t *testing.T) {
	innerErr := errors.New("inner error")
	domainErr := &DomainError{
		Code:    "TEST_CODE",
		Message: "test message",
		Err:     innerErr,
	}

	unwrapped := domainErr.Unwrap()
	if unwrapped != innerErr {
		t.Errorf("Expected unwrapped error to be inner error, got: %v", unwrapped)
	}
}

// TestDomainError_Unwrap_Nil tests Unwrap() with no wrapped error
func TestDomainError_Unwrap_Nil(t *testing.T) {
	domainErr := &DomainError{
		Code:    "TEST_CODE",
		Message: "test message",
		Err:     nil,
	}

	unwrapped := domainErr.Unwrap()
	if unwrapped != nil {
		t.Errorf("Expected unwrapped error to be nil, got: %v", unwrapped)
	}
}

// TestNewInvalidStatusTransitionError tests status transition error constructor
func TestNewInvalidStatusTransitionError(t *testing.T) {
	err := NewInvalidStatusTransitionError(StatusPending, StatusDeployed)
	
	if err == nil {
		t.Fatal("Expected error to be created, got nil")
	}

	var domainErr *DomainError
	if !errors.As(err, &domainErr) {
		t.Fatalf("Expected error to be DomainError, got: %T", err)
	}

	if domainErr.Code != "INVALID_STATUS_TRANSITION" {
		t.Errorf("Expected code 'INVALID_STATUS_TRANSITION', got: %s", domainErr.Code)
	}

	errorString := err.Error()
	if !strings.Contains(errorString, "pending") {
		t.Errorf("Expected error to contain 'pending', got: %s", errorString)
	}
	if !strings.Contains(errorString, "deployed") {
		t.Errorf("Expected error to contain 'deployed', got: %s", errorString)
	}
}

// TestNewDeploymentNotFoundError tests not found error constructor
func TestNewDeploymentNotFoundError(t *testing.T) {
	testUUID := "deploy-123"
	err := NewDeploymentNotFoundError(testUUID)
	
	if err == nil {
		t.Fatal("Expected error to be created, got nil")
	}

	var domainErr *DomainError
	if !errors.As(err, &domainErr) {
		t.Fatalf("Expected error to be DomainError, got: %T", err)
	}

	if domainErr.Code != "DEPLOYMENT_NOT_FOUND" {
		t.Errorf("Expected code 'DEPLOYMENT_NOT_FOUND', got: %s", domainErr.Code)
	}

	errorString := err.Error()
	if !strings.Contains(errorString, testUUID) {
		t.Errorf("Expected error to contain UUID '%s', got: %s", testUUID, errorString)
	}
}

// TestNewInvalidDeploymentError tests invalid deployment error constructor
func TestNewInvalidDeploymentError(t *testing.T) {
	testMessage := "deployment name is required"
	err := NewInvalidDeploymentError(testMessage)
	
	if err == nil {
		t.Fatal("Expected error to be created, got nil")
	}

	var domainErr *DomainError
	if !errors.As(err, &domainErr) {
		t.Fatalf("Expected error to be DomainError, got: %T", err)
	}

	if domainErr.Code != "INVALID_DEPLOYMENT" {
		t.Errorf("Expected code 'INVALID_DEPLOYMENT', got: %s", domainErr.Code)
	}

	if domainErr.Message != testMessage {
		t.Errorf("Expected message '%s', got: %s", testMessage, domainErr.Message)
	}

	errorString := err.Error()
	if !strings.Contains(errorString, testMessage) {
		t.Errorf("Expected error to contain message '%s', got: %s", testMessage, errorString)
	}
}

// TestNewPermissionDeniedError tests permission denied error constructor
func TestNewPermissionDeniedError(t *testing.T) {
	action := "delete"
	resource := "deployment-123"
	err := NewPermissionDeniedError(action, resource)
	
	if err == nil {
		t.Fatal("Expected error to be created, got nil")
	}

	var domainErr *DomainError
	if !errors.As(err, &domainErr) {
		t.Fatalf("Expected error to be DomainError, got: %T", err)
	}

	if domainErr.Code != "PERMISSION_DENIED" {
		t.Errorf("Expected code 'PERMISSION_DENIED', got: %s", domainErr.Code)
	}

	errorString := err.Error()
	if !strings.Contains(errorString, action) {
		t.Errorf("Expected error to contain action '%s', got: %s", action, errorString)
	}
	if !strings.Contains(errorString, resource) {
		t.Errorf("Expected error to contain resource '%s', got: %s", resource, errorString)
	}
}

// TestErrorUnwrapping tests error unwrapping with errors.Is and errors.As
func TestErrorUnwrapping(t *testing.T) {
	innerErr := errors.New("database error")
	domainErr := &DomainError{
		Code:    "REPOSITORY_ERROR",
		Message: "failed to access repository",
		Err:     innerErr,
	}

	// Test errors.Is
	if !errors.Is(domainErr, innerErr) {
		t.Error("Expected errors.Is to find wrapped error")
	}

	// Test errors.As
	var asDomainErr *DomainError
	if !errors.As(domainErr, &asDomainErr) {
		t.Error("Expected errors.As to work with DomainError")
	}
	if asDomainErr.Code != "REPOSITORY_ERROR" {
		t.Errorf("Expected code 'REPOSITORY_ERROR', got: %s", asDomainErr.Code)
	}
}

// TestDomainErrorAs tests error casting with errors.As
func TestDomainErrorAs(t *testing.T) {
	err := NewInvalidDeploymentError("test error")
	
	var domainErr *DomainError
	if !errors.As(err, &domainErr) {
		t.Error("Expected error to be DomainError")
	}
	if domainErr.Code != "INVALID_DEPLOYMENT" {
		t.Errorf("Expected code 'INVALID_DEPLOYMENT', got: %s", domainErr.Code)
	}
}

// TestDeploymentNotFoundErrorAs tests error casting for not found errors
func TestDeploymentNotFoundErrorAs(t *testing.T) {
	err := NewDeploymentNotFoundError("test-uuid")
	
	var domainErr *DomainError
	if !errors.As(err, &domainErr) {
		t.Error("Expected error to be DomainError")
	}
	if domainErr.Code != "DEPLOYMENT_NOT_FOUND" {
		t.Errorf("Expected code 'DEPLOYMENT_NOT_FOUND', got: %s", domainErr.Code)
	}
}

// TestDomainErrorCodes verifies all error codes are unique and consistent
func TestDomainErrorCodes(t *testing.T) {
	testCases := []struct {
		name         string
		err          error
		expectedCode string
	}{
		{
			name:         "Invalid Status Transition",
			err:          NewInvalidStatusTransitionError(StatusPending, StatusDeployed),
			expectedCode: "INVALID_STATUS_TRANSITION",
		},
		{
			name:         "Deployment Not Found",
			err:          NewDeploymentNotFoundError("test-uuid"),
			expectedCode: "DEPLOYMENT_NOT_FOUND",
		},
		{
			name:         "Invalid Deployment",
			err:          NewInvalidDeploymentError("test message"),
			expectedCode: "INVALID_DEPLOYMENT",
		},
		{
			name:         "Permission Denied",
			err:          NewPermissionDeniedError("delete", "resource"),
			expectedCode: "PERMISSION_DENIED",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			var domainErr *DomainError
			if !errors.As(tc.err, &domainErr) {
				t.Fatalf("Expected error to be DomainError, got: %T", tc.err)
			}

			if domainErr.Code != tc.expectedCode {
				t.Errorf("Expected code '%s', got: %s", tc.expectedCode, domainErr.Code)
			}
		})
	}
}

// TestDomainErrorMessages verifies error messages are descriptive
func TestDomainErrorMessages(t *testing.T) {
	testCases := []struct {
		name              string
		err               error
		expectedSubstring string
	}{
		{
			name:              "Status Transition",
			err:               NewInvalidStatusTransitionError(StatusPending, StatusDeployed),
			expectedSubstring: "cannot transition",
		},
		{
			name:              "Not Found",
			err:               NewDeploymentNotFoundError("abc-123"),
			expectedSubstring: "not found",
		},
		{
			name:              "Invalid",
			err:               NewInvalidDeploymentError("missing name"),
			expectedSubstring: "missing name",
		},
		{
			name:              "Permission",
			err:               NewPermissionDeniedError("update", "deployment"),
			expectedSubstring: "permission denied",
		},
	}

	for _, tc := range testCases {
		t.Run(tc.name, func(t *testing.T) {
			errorString := tc.err.Error()
			if !strings.Contains(strings.ToLower(errorString), strings.ToLower(tc.expectedSubstring)) {
				t.Errorf("Expected error to contain '%s', got: %s", tc.expectedSubstring, errorString)
			}
		})
	}
}
