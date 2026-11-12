package routes

import (
	"net/http"

	"github.com/gin-gonic/gin"
)

// respondError writes a JSON {"error": msg} body with the given status code.
// It centralizes the inline c.JSON(http.StatusXxx, gin.H{"error": ...}) shape
// that was repeated across 64+ call sites in routes/{auth,deployment,git,
// metrics,projects,instances,pm}.go so every error response stays consistent
// and future response-shape changes have one home.
func respondError(c *gin.Context, status int, msg string) {
	c.JSON(status, gin.H{"error": msg})
}

// respondErrorWithDetails writes a JSON body with an `error` field plus a
// caller-supplied set of additional fields. Use this when the caller needs to
// surface extra context (upstream status, response body, a debug string) that
// does not fit into the single-message shape.
func respondErrorWithDetails(c *gin.Context, status int, msg string, details gin.H) {
	body := gin.H{"error": msg}
	for k, v := range details {
		body[k] = v
	}
	c.JSON(status, body)
}

// respondBadRequest is a shortcut for respondError(c, http.StatusBadRequest, msg).
func respondBadRequest(c *gin.Context, msg string) {
	respondError(c, http.StatusBadRequest, msg)
}

// respondUnauthorized is a shortcut for respondError(c, http.StatusUnauthorized, msg).
func respondUnauthorized(c *gin.Context, msg string) {
	respondError(c, http.StatusUnauthorized, msg)
}

// respondNotFound is a shortcut for respondError(c, http.StatusNotFound, msg).
func respondNotFound(c *gin.Context, msg string) {
	respondError(c, http.StatusNotFound, msg)
}

// respondInternalError is a shortcut for respondError(c, http.StatusInternalServerError, msg).
func respondInternalError(c *gin.Context, msg string) {
	respondError(c, http.StatusInternalServerError, msg)
}
