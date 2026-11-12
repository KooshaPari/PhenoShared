package routes

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"

	"github.com/gin-gonic/gin"
)

// TestSignupRejectsMissingCredentials is a regression test for POST /signup
// accepting an empty JSON body and creating a user with empty name, email and
// password. Observed before the fix: HTTP 201 for a `{}` payload, with an empty
// password hashed into the password column.
//
// Only the pre-persistence validation path is covered: the handler returns 400
// during binding, so no database connection is required. The success path needs
// a live database and is exercised by the runtime smoke test instead.
func TestSignupRejectsMissingCredentials(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cases := []struct {
		name string
		body string
	}{
		{"empty object", `{}`},
		{"empty strings", `{"name":"","email":"","password":""}`},
		{"missing password", `{"name":"a","email":"a@b.c"}`},
		{"missing email", `{"name":"a","password":"x"}`},
		{"missing name", `{"email":"a@b.c","password":"x"}`},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(w)
			c.Request = httptest.NewRequest(http.MethodPost, "/signup", strings.NewReader(tc.body))
			c.Request.Header.Set("Content-Type", "application/json")

			Signup(c)

			if w.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want %d (body %s)", w.Code, http.StatusBadRequest, w.Body.String())
			}
		})
	}
}
