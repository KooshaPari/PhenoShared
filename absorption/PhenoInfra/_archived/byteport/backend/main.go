package main

import (
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/byteport/api/internal/container"
	"github.com/byteport/api/lib"
	"github.com/byteport/api/models"
	"github.com/gin-gonic/gin"
	"github.com/joho/godotenv"
)

func main() {
	// Load orchestrator port before .env overrides
	orchestratorPort := os.Getenv("PORT")

	// Load environment configuration from backend/.env if present
	envPath := filepath.Join("..", ".env")
	if err := godotenv.Load(envPath); err != nil {
		log.Printf("Warning: .env file not found at %s, using environment variables", envPath)
	} else {
		log.Printf("Loaded environment from %s", envPath)
	}

	if orchestratorPort != "" {
		os.Setenv("PORT", orchestratorPort)
	}

	if err := lib.InitializeEncryptionKey(); err != nil {
		log.Fatalf("failed to initialise encryption key: %v", err)
	}

	models.ConnectDatabase()

	if err := lib.InitAuthSystem(); err != nil {
		log.Fatalf("failed to initialise auth system: %v", err)
	}

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	env := os.Getenv("ENV")
	if env == "production" {
		gin.SetMode(gin.ReleaseMode)
	}

	// Initialize dependency injection container
	containerInst := container.NewContainer(models.DB)
	log.Printf("✅ Dependency injection container initialized")

	server := NewAPIServer(containerInst)

	addr := fmt.Sprintf(":%s", port)
	log.Printf("🚀 BytePort API Server starting on %s", addr)
	log.Printf("📊 Environment: %s", env)
	log.Printf("🌐 API Documentation: http://localhost:%s/api/v1/docs", port)

	if err := server.router.Run(addr); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
}
