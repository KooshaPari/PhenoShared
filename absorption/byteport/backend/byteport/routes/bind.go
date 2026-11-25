package routes

import (
	"strings"

	"github.com/gin-gonic/gin"
)

// bindJSON binds the request body into dst. On parse failure it writes a
// 400 response of the form "context: <bind error>" (or just "<bind error>"
// when context is empty) and returns false; callers should `return`
// immediately on false.
//
// context is an optional human-readable label that identifies which handler
// was being called (e.g. "Invalid deploy request"). Pass an empty string to
// use the bare bind error.
//
// Centralizes the `var req X; if err := c.ShouldBindJSON(&req); err != nil
// { respondBadRequest(c, ...); return }` pattern that was repeated at 5
// sites across auth.go and deployment.go.
func bindJSON(c *gin.Context, dst any, context string) bool {
	if err := c.ShouldBindJSON(dst); err != nil {
		msg := err.Error()
		if context != "" {
			msg = strings.TrimSpace(context) + ": " + msg
		}
		respondBadRequest(c, msg)
		return false
	}
	return true
}
