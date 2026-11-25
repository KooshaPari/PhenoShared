package utils

import (
	"crypto/rand"
	"encoding/hex"
	"log"
	"os"
)

// GetLogger returns a configured logger instance
func GetLogger() *log.Logger {
	return log.New(os.Stdout, "[KodeVibe] ", log.LstdFlags|log.Lshortfile)
}

// GenerateID generates a random ID string
func GenerateID() string {
	bytes := make([]byte, 16)
	if _, err := rand.Read(bytes); err != nil {
		// Fallback to timestamp-based ID if random fails
		return "id-" + hex.EncodeToString([]byte("fallback"))
	}
	return hex.EncodeToString(bytes)
}
