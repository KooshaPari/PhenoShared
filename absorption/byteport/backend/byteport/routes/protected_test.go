package routes

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

// protectedRouter wires endpoints that require authentication behind the
// currentUser helper, so tests can assert both the authorized and unauthorized
// branches without touching the database.
func protectedRouter() *gin.Engine {
	gin.SetMode(gin.TestMode)
	r := gin.New()
	r.GET("/projects", GetProjects)
	r.GET("/instances", GetInstances)
	return r
}

func TestGetProjectsUnauthorized(t *testing.T) {
	r := protectedRouter()
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/projects", nil)
	r.ServeHTTP(w, req)
	if w.Code != http.StatusUnauthorized {
		t.Errorf("status = %d, want 401", w.Code)
	}
}

func TestGetInstancesUnauthorized(t *testing.T) {
	r := protectedRouter()
	w := httptest.NewRecorder()
	req := httptest.NewRequest(http.MethodGet, "/instances", nil)
	r.ServeHTTP(w, req)
	if w.Code != http.StatusUnauthorized {
		t.Errorf("status = %d, want 401", w.Code)
	}
}
