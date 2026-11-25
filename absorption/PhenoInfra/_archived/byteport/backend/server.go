package main

import (
	"os"
	"strings"

	"github.com/byteport/api/internal/container"
	"github.com/byteport/api/lib"
	"github.com/gin-contrib/cors"
	"github.com/gin-gonic/gin"
)

// APIServer represents the HTTP API server
type APIServer struct {
	router    *gin.Engine
	container *container.Container
	store     *DeploymentStore // Legacy - will be removed
}

// NewAPIServer creates a new API server instance
func NewAPIServer(c *container.Container) *APIServer {
	r := gin.Default()

	// Legacy store for backward compatibility during migration
	store := NewDeploymentStore()

	allowedOrigins := parseAllowedOrigins()

	// CORS middleware
	r.Use(cors.New(cors.Config{
		AllowOrigins:     allowedOrigins,
		AllowMethods:     []string{"GET", "POST", "PUT", "DELETE", "OPTIONS"},
		AllowHeaders:     []string{"Origin", "Content-Type", "Accept", "Authorization", "X-Requested-With", "Cookie"},
		ExposeHeaders:    []string{"Content-Length"},
		AllowCredentials: true,
	}))

	// API routes
	v1 := r.Group("/api/v1")
	{
		// Health check
		v1.GET("/health", handleHealth)
		v1.GET("/", handleAPIInfo)

		// Public auth endpoints
		// Auth endpoints - WorkOS AuthKit only
		v1.POST("/auth/workos/callback", handleWorkOSCallback)

		protected := v1.Group("/")
		protected.Use(lib.AuthMiddleware())
		{
			// Protected endpoints - require AuthKit authentication
			protected.GET("/user/:id", handleGetUser)

			// NEW: Hexagonal architecture endpoints
			c.DeploymentHandler.RegisterRoutes(protected)

			// LEGACY: Old deployment endpoints (will be removed)
			legacyDeployments := protected.Group("/legacy/deployments")
			{
				legacyDeployments.POST("", handleDeploy(store))
				legacyDeployments.GET("", handleListDeployments(store))
				legacyDeployments.GET("/:id", handleGetDeployment(store))
				legacyDeployments.DELETE("/:id", handleTerminateDeployment(store))

				// Deployment operations
				legacyDeployments.GET("/:id/status", handleGetStatus(store))
				legacyDeployments.GET("/:id/logs", handleGetLogs(store))
				legacyDeployments.GET("/:id/metrics", handleGetMetrics(store))
			}
		}

		// Utilities
		v1.POST("/detect", handleDetectApp)
		v1.POST("/estimate-cost", handleEstimateCost)
		v1.POST("/validate-config", handleValidateConfig)

		// Documentation
		v1.GET("/docs", handleDocs)
	}

	return &APIServer{
		router:    r,
		container: c,
		store:     store,
	}
}

func parseAllowedOrigins() []string {
	raw := strings.Split(os.Getenv("ALLOWED_ORIGINS"), ",")
	origins := make([]string, 0, len(raw))
	for _, origin := range raw {
		origin = strings.TrimSpace(origin)
		if origin != "" {
			origins = append(origins, origin)
		}
	}
	if len(origins) == 0 {
		origins = []string{
			"http://localhost:3000",
			"http://localhost:5173",
			"http://localhost:8002",
			"https://byte.kooshapari.com",
		}
	}
	return origins
}

// API info handler
func handleAPIInfo(c *gin.Context) {
	c.JSON(200, gin.H{
		"name":        "BytePort API",
		"version":     "2.0.0",
		"description": "Zero-cost deployment platform API",
		"endpoints": gin.H{
			"health":      "/api/v1/health",
			"deployments": "/api/v1/deployments",
			"projects":    "/api/v1/projects",
			"docs":        "/api/v1/docs",
		},
	})
}

// Health check handler
func handleHealth(c *gin.Context) {
	c.JSON(200, gin.H{
		"status":  "healthy",
		"service": "byteport-api",
		"version": "2.0.0",
	})
}

// Documentation handler
func handleDocs(c *gin.Context) {
	c.JSON(200, gin.H{
		"title":       "BytePort API Documentation",
		"version":     "2.0.0",
		"description": "REST API for zero-cost deployments",
		"endpoints": []gin.H{
			{
				"method":      "POST",
				"path":        "/api/v1/deployments",
				"description": "Deploy an application",
				"body": gin.H{
					"name":     "string",
					"type":     "string (frontend/backend/database)",
					"provider": "string (optional)",
					"git_url":  "string (optional)",
					"env_vars": "object (optional)",
				},
			},
			{
				"method":      "GET",
				"path":        "/api/v1/deployments",
				"description": "List all deployments",
			},
			{
				"method":      "GET",
				"path":        "/api/v1/deployments/:id",
				"description": "Get deployment details",
			},
			{
				"method":      "DELETE",
				"path":        "/api/v1/deployments/:id",
				"description": "Terminate a deployment",
			},
			{
				"method":      "GET",
				"path":        "/api/v1/deployments/:id/status",
				"description": "Get deployment status",
			},
			{
				"method":      "GET",
				"path":        "/api/v1/deployments/:id/logs",
				"description": "Get deployment logs",
			},
			{
				"method":      "POST",
				"path":        "/api/v1/detect",
				"description": "Auto-detect application type",
			},
			{
				"method":      "POST",
				"path":        "/api/v1/estimate-cost",
				"description": "Estimate deployment cost",
			},
		},
	})
}
