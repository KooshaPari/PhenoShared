package handlers

import (
	"encoding/json"
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/byteport/api/internal/application/deployment"
	"github.com/gin-gonic/gin"
	"github.com/stretchr/testify/assert"
)

func TestGetUserUUID_WithValidContext(t *testing.T) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Set("user_uuid", "test-user-123")

	uuid := getUserUUID(c)
	assert.Equal(t, "test-user-123", uuid)
}

func TestGetUserUUID_WithoutContext(t *testing.T) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	uuid := getUserUUID(c)
	assert.Equal(t, "", uuid)
}

func TestGetUserUUID_WithInvalidType(t *testing.T) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)
	c.Set("user_uuid", 12345)

	uuid := getUserUUID(c)
	assert.Equal(t, "", uuid)
}

func TestHandleApplicationError_WithApplicationError(t *testing.T) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	appErr := &deployment.ApplicationError{
		Code:       "TEST_ERROR",
		Message:    "test error message",
		StatusCode: http.StatusBadRequest,
	}

	handleApplicationError(c, appErr)

	assert.Equal(t, http.StatusBadRequest, w.Code)
	
	var errResp ErrorResponse
	err := json.Unmarshal(w.Body.Bytes(), &errResp)
	assert.NoError(t, err)
	assert.Equal(t, "test error message", errResp.Error)
	assert.Equal(t, "TEST_ERROR", errResp.Code)
}

func TestHandleApplicationError_WithUnknownError(t *testing.T) {
	w := httptest.NewRecorder()
	c, _ := gin.CreateTestContext(w)

	unknownErr := errors.New("unknown error")

	handleApplicationError(c, unknownErr)

	assert.Equal(t, http.StatusInternalServerError, w.Code)
	
	var errResp ErrorResponse
	err := json.Unmarshal(w.Body.Bytes(), &errResp)
	assert.NoError(t, err)
	assert.Equal(t, "internal server error", errResp.Error)
	assert.Equal(t, "INTERNAL_ERROR", errResp.Code)
}
