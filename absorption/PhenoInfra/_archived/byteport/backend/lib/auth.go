package lib

import (
	"crypto/rand"
	"encoding/base64"
	"fmt"
	"os"

	httpmiddleware "github.com/byteport/api/internal/infrastructure/http/middleware"
	"github.com/gin-gonic/gin"
)

const encryptionKeyEnv = "ENCRYPTION_KEY"

// InitializeEncryptionKey ensures the API process has an AES-compatible key.
func InitializeEncryptionKey() error {
	if os.Getenv(encryptionKeyEnv) != "" {
		return nil
	}

	key := make([]byte, 32)
	if _, err := rand.Read(key); err != nil {
		return fmt.Errorf("generate encryption key: %w", err)
	}

	if err := os.Setenv(encryptionKeyEnv, base64.StdEncoding.EncodeToString(key)); err != nil {
		return fmt.Errorf("set encryption key: %w", err)
	}

	return nil
}

// InitAuthSystem is retained for the legacy server startup path.
func InitAuthSystem() error {
	return nil
}

// AuthMiddleware returns the API's legacy-compatible Gin auth middleware.
func AuthMiddleware() gin.HandlerFunc {
	return httpmiddleware.AuthMiddlewareWithFallback(nil)
}
