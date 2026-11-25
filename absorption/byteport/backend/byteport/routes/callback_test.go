package routes

import (
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/gin-gonic/gin"
)

// TestHandleCallbackRejectsMalformedState is a regression test for an
// index-out-of-range panic on the `state` query parameter. GET
// /api/github/callback returned 500 for any request whose `state` lacked the
// "<BYTEPORT>" delimiter, because HandleCallback indexed strings.Split's result
// without checking its length.
//
// Only the pre-persistence validation path is covered: the handler now returns
// 400 before it touches the database or GitHub, so no database or network
// access is required. The success path needs a live database and a real GitHub
// authorization code, and is exercised by the runtime smoke test instead.
func TestHandleCallbackRejectsMalformedState(t *testing.T) {
	gin.SetMode(gin.TestMode)

	cases := []struct {
		name  string
		query string
	}{
		{"missing state", "?code=abc"},
		{"state without delimiter", "?code=abc&state=justatoken"},
		{"empty halves", "?code=abc&state=%3CBYTEPORT%3E"},
		{"empty user id", "?code=abc&state=token%3CBYTEPORT%3E"},
		{"empty auth token", "?code=abc&state=%3CBYTEPORT%3Euserid"},
	}

	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			w := httptest.NewRecorder()
			c, _ := gin.CreateTestContext(w)
			c.Request = httptest.NewRequest(http.MethodGet, "/api/github/callback"+tc.query, nil)

			HandleCallback(c)

			if w.Code != http.StatusBadRequest {
				t.Fatalf("status = %d, want %d (body %s)", w.Code, http.StatusBadRequest, w.Body.String())
			}
		})
	}
}
