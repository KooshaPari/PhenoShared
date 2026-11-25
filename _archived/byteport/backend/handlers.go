package main

import (
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
)

// DeployRequest represents a deployment request
type DeployRequest struct {
	Name     string                 `json:"name" binding:"required"`
	Type     string                 `json:"type" binding:"required"` // frontend, backend, database
	Provider string                 `json:"provider"`                // optional, auto-selected if empty
	GitURL   string                 `json:"git_url"`
	Branch   string                 `json:"branch"`
	EnvVars  map[string]string      `json:"env_vars"`
	Config   map[string]interface{} `json:"config"`
}

// DeployResponse represents a deployment response
type DeployResponse struct {
	ID        string    `json:"id"`
	Name      string    `json:"name"`
	Status    string    `json:"status"`
	URL       string    `json:"url"`
	Provider  string    `json:"provider"`
	CreatedAt time.Time `json:"created_at"`
	Message   string    `json:"message"`
}

// handleDeploy handles deployment requests
func handleDeploy(store *DeploymentStore) gin.HandlerFunc {
	return func(c *gin.Context) {
		var req DeployRequest
		if err := c.ShouldBindJSON(&req); err != nil {
			c.JSON(http.StatusBadRequest, gin.H{
				"error":   "Invalid request format",
				"details": err.Error(),
			})
			return
		}

		// Auto-select provider if not specified
		if req.Provider == "" {
			req.Provider = selectOptimalProvider(req.Type)
		}

		// Validate provider
		if !isValidProvider(req.Provider) {
			c.JSON(http.StatusBadRequest, gin.H{
				"error":           "Invalid provider",
				"valid_providers": []string{"vercel", "netlify", "render", "railway", "supabase", "cloudflare-pages"},
			})
			return
		}

		// Create deployment
		deployment := &Deployment{
			ID:        uuid.New().String(),
			Name:      req.Name,
			Type:      req.Type,
			Provider:  req.Provider,
			Status:    "deploying",
			GitURL:    req.GitURL,
			Branch:    req.Branch,
			EnvVars:   req.EnvVars,
			CreatedAt: time.Now(),
			UpdatedAt: time.Now(),
		}

		// Generate URL
		deployment.URL = generateDeploymentURL(req.Name, req.Provider)

		// Store deployment
		store.Add(deployment)

		// Simulate async deployment (in production, this would be a background job)
		go simulateDeployment(store, deployment.ID)

		// Return response
		c.JSON(http.StatusCreated, DeployResponse{
			ID:        deployment.ID,
			Name:      deployment.Name,
			Status:    deployment.Status,
			URL:       deployment.URL,
			Provider:  deployment.Provider,
			CreatedAt: deployment.CreatedAt,
			Message:   "Deployment started successfully",
		})
	}
}

// handleListDeployments lists all deployments
func handleListDeployments(store *DeploymentStore) gin.HandlerFunc {
	return func(c *gin.Context) {
		deployments := store.List()

		response := make([]DeployResponse, len(deployments))
		for i, dep := range deployments {
			response[i] = DeployResponse{
				ID:        dep.ID,
				Name:      dep.Name,
				Status:    dep.Status,
				URL:       dep.URL,
				Provider:  dep.Provider,
				CreatedAt: dep.CreatedAt,
			}
		}

		c.JSON(http.StatusOK, gin.H{
			"deployments": response,
			"total":       len(response),
		})
	}
}

// handleGetDeployment gets a specific deployment
func handleGetDeployment(store *DeploymentStore) gin.HandlerFunc {
	return func(c *gin.Context) {
		id := c.Param("id")
		deployment := store.Get(id)

		if deployment == nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Deployment not found",
			})
			return
		}

		c.JSON(http.StatusOK, deployment)
	}
}

// handleTerminateDeployment terminates a deployment
func handleTerminateDeployment(store *DeploymentStore) gin.HandlerFunc {
	return func(c *gin.Context) {
		id := c.Param("id")
		deployment := store.Get(id)

		if deployment == nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Deployment not found",
			})
			return
		}

		// Update status
		deployment.Status = "terminated"
		deployment.UpdatedAt = time.Now()
		store.Update(deployment)

		c.JSON(http.StatusOK, gin.H{
			"message": "Deployment terminated successfully",
			"id":      id,
		})
	}
}

// handleGetStatus gets deployment status
func handleGetStatus(store *DeploymentStore) gin.HandlerFunc {
	return func(c *gin.Context) {
		id := c.Param("id")
		deployment := store.Get(id)

		if deployment == nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Deployment not found",
			})
			return
		}

		status := gin.H{
			"id":         deployment.ID,
			"status":     deployment.Status,
			"progress":   getProgress(deployment.Status),
			"updated_at": deployment.UpdatedAt,
		}

		c.JSON(http.StatusOK, status)
	}
}

// handleGetLogs gets deployment logs
func handleGetLogs(store *DeploymentStore) gin.HandlerFunc {
	return func(c *gin.Context) {
		id := c.Param("id")
		deployment := store.Get(id)

		if deployment == nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Deployment not found",
			})
			return
		}

		// Mock logs
		logs := []gin.H{
			{
				"timestamp": time.Now().Add(-5 * time.Minute),
				"level":     "info",
				"message":   "Starting deployment process",
			},
			{
				"timestamp": time.Now().Add(-4 * time.Minute),
				"level":     "info",
				"message":   "Building application...",
			},
			{
				"timestamp": time.Now().Add(-2 * time.Minute),
				"level":     "info",
				"message":   "Deploying to " + deployment.Provider,
			},
			{
				"timestamp": time.Now(),
				"level":     "info",
				"message":   "Deployment completed successfully",
			},
		}

		c.JSON(http.StatusOK, gin.H{
			"deployment_id": id,
			"logs":          logs,
		})
	}
}

// handleGetMetrics gets deployment metrics
func handleGetMetrics(store *DeploymentStore) gin.HandlerFunc {
	return func(c *gin.Context) {
		id := c.Param("id")
		deployment := store.Get(id)

		if deployment == nil {
			c.JSON(http.StatusNotFound, gin.H{
				"error": "Deployment not found",
			})
			return
		}

		// Mock metrics
		metrics := gin.H{
			"deployment_id": id,
			"uptime":        "99.9%",
			"requests":      1234,
			"bandwidth":     "1.2 GB",
			"response_time": "45ms",
			"cost": gin.H{
				"monthly":  0.0,
				"currency": "USD",
			},
		}

		c.JSON(http.StatusOK, metrics)
	}
}

// handleCreateProject creates a new project
func handleCreateProject(c *gin.Context) {
	var req struct {
		Name        string `json:"name" binding:"required"`
		Description string `json:"description"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	project := gin.H{
		"id":          uuid.New().String(),
		"name":        req.Name,
		"description": req.Description,
		"created_at":  time.Now(),
	}

	c.JSON(http.StatusCreated, project)
}

// handleListProjects lists all projects
func handleListProjects(c *gin.Context) {
	projects := []gin.H{
		{
			"id":          "proj_001",
			"name":        "my-app",
			"deployments": 3,
			"created_at":  time.Now().Add(-24 * time.Hour),
		},
	}

	c.JSON(http.StatusOK, gin.H{"projects": projects})
}

// handleGetProject gets a specific project
func handleGetProject(c *gin.Context) {
	id := c.Param("id")

	project := gin.H{
		"id":          id,
		"name":        "my-app",
		"description": "My awesome app",
		"deployments": 3,
		"created_at":  time.Now().Add(-24 * time.Hour),
	}

	c.JSON(http.StatusOK, project)
}

// handleDeleteProject deletes a project
func handleDeleteProject(c *gin.Context) {
	id := c.Param("id")

	c.JSON(http.StatusOK, gin.H{
		"message": "Project deleted successfully",
		"id":      id,
	})
}

// handleDetectApp detects application type
func handleDetectApp(c *gin.Context) {
	var req struct {
		Files []string `json:"files"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Simple detection logic
	detection := gin.H{
		"type":               "frontend",
		"framework":          "react",
		"confidence":         0.9,
		"suggested_provider": "vercel",
	}

	c.JSON(http.StatusOK, detection)
}

// handleEstimateCost estimates deployment cost
func handleEstimateCost(c *gin.Context) {
	var req struct {
		Type     string `json:"type"`
		Provider string `json:"provider"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	cost := gin.H{
		"monthly":  0.0,
		"currency": "USD",
		"breakdown": []gin.H{
			{
				"service":  req.Type,
				"provider": req.Provider,
				"cost":     0.0,
				"plan":     "Free Tier",
			},
		},
		"message": "This deployment uses 100% free tiers",
	}

	c.JSON(http.StatusOK, cost)
}

// handleValidateConfig validates a deployment configuration
func handleValidateConfig(c *gin.Context) {
	var config map[string]interface{}

	if err := c.ShouldBindJSON(&config); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	validation := gin.H{
		"valid":    true,
		"errors":   []string{},
		"warnings": []string{},
	}

	c.JSON(http.StatusOK, validation)
}

func handleWorkOSCallback(c *gin.Context) {
	var req struct {
		Code  string `json:"code"`
		State string `json:"state"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	if req.Code == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "authorization code is required"})
		return
	}

	c.JSON(http.StatusOK, gin.H{
		"access_token": req.Code,
		"token_type":   "Bearer",
		"state":        req.State,
	})
}

func handleGetUser(c *gin.Context) {
	id := c.Param("id")
	if id == "" {
		id = "current"
	}

	user := gin.H{"id": id}
	if userID, ok := c.Get("user_id"); ok {
		user["id"] = userID
	}
	if email, ok := c.Get("user_email"); ok {
		user["email"] = email
	}

	c.JSON(http.StatusOK, gin.H{"user": user})
}

// Helper functions

func selectOptimalProvider(appType string) string {
	switch appType {
	case "frontend":
		return "vercel"
	case "backend":
		return "render"
	case "database":
		return "supabase"
	default:
		return "vercel"
	}
}

func isValidProvider(provider string) bool {
	valid := []string{"vercel", "netlify", "render", "railway", "supabase", "cloudflare-pages"}
	for _, p := range valid {
		if p == provider {
			return true
		}
	}
	return false
}

func generateDeploymentURL(name, provider string) string {
	switch provider {
	case "vercel":
		return fmt.Sprintf("https://%s.vercel.app", name)
	case "netlify":
		return fmt.Sprintf("https://%s.netlify.app", name)
	case "render":
		return fmt.Sprintf("https://%s.onrender.com", name)
	case "railway":
		return fmt.Sprintf("https://%s.up.railway.app", name)
	case "supabase":
		return fmt.Sprintf("https://%s.supabase.co", name)
	case "cloudflare-pages":
		return fmt.Sprintf("https://%s.pages.dev", name)
	default:
		return fmt.Sprintf("https://%s.deployed.io", name)
	}
}

func getProgress(status string) int {
	switch status {
	case "deploying", "building":
		return 50
	case "deployed":
		return 100
	case "failed":
		return 0
	default:
		return 25
	}
}

func simulateDeployment(store *DeploymentStore, id string) {
	// Simulate deployment process
	time.Sleep(3 * time.Second)

	deployment := store.Get(id)
	if deployment != nil {
		deployment.Status = "deployed"
		deployment.UpdatedAt = time.Now()
		store.Update(deployment)
	}
}
