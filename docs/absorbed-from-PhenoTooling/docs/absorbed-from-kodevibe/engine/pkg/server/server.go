package server

import (
	"context"
	"fmt"
	"net/http"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/google/uuid"
	"github.com/gorilla/websocket"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/sirupsen/logrus"

	"kodevibe/internal/models"
	"kodevibe/pkg/report"
	"kodevibe/pkg/scanner"
)

// Server represents the KodeVibe HTTP server
type Server struct {
	config   *models.Configuration
	logger   *logrus.Logger
	scanner  *scanner.Scanner
	reporter *report.Reporter
	upgrader websocket.Upgrader
	clients  map[string]*websocket.Conn
}

// NewServer creates a new HTTP server instance
func NewServer(config *models.Configuration, logger *logrus.Logger) *Server {
	scannerInstance, _ := scanner.NewScanner(config, logger)
	reporter := report.NewReporter(config)

	return &Server{
		config:   config,
		logger:   logger,
		scanner:  scannerInstance,
		reporter: reporter,
		upgrader: websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool {
				return true // Allow all origins in development
			},
		},
		clients: make(map[string]*websocket.Conn),
	}
}

// Start starts the HTTP server
func (s *Server) Start(host string, port int, tlsEnabled bool, certFile, keyFile string) error {
	// Set Gin mode
	if s.logger.Level == logrus.DebugLevel {
		gin.SetMode(gin.DebugMode)
	} else {
		gin.SetMode(gin.ReleaseMode)
	}

	router := gin.New()
	router.Use(gin.Logger())
	router.Use(gin.Recovery())
	router.Use(s.corsMiddleware())
	router.Use(s.loggingMiddleware())

	// Setup routes
	s.setupRoutes(router)

	addr := fmt.Sprintf("%s:%d", host, port)
	s.logger.Infof("Starting KodeVibe server on %s", addr)

	server := &http.Server{
		Addr:    addr,
		Handler: router,
	}

	if tlsEnabled {
		if certFile == "" || keyFile == "" {
			return fmt.Errorf("TLS certificate and key files are required for TLS mode")
		}
		return server.ListenAndServeTLS(certFile, keyFile)
	}

	return server.ListenAndServe()
}

// setupRoutes configures all API routes
func (s *Server) setupRoutes(router *gin.Engine) {
	// Health check
	router.GET("/health", s.healthCheck)

	// Metrics endpoint
	router.GET("/metrics", gin.WrapH(promhttp.Handler()))

	// API v1 routes
	v1 := router.Group("/api/v1")
	{
		// Scan endpoints
		v1.POST("/scan", s.createScan)
		v1.GET("/scan/:id", s.getScan)
		v1.GET("/scans", s.listScans)
		v1.DELETE("/scan/:id", s.deleteScan)

		// Configuration endpoints
		v1.GET("/config", s.getConfig)
		v1.PUT("/config", s.updateConfig)
		v1.POST("/config/validate", s.validateConfig)

		// Report endpoints
		v1.GET("/reports", s.listReports)
		v1.GET("/report/:id", s.getReport)
		v1.POST("/report/:id/download", s.downloadReport)

		// Vibe endpoints
		v1.GET("/vibes", s.listVibes)
		v1.GET("/vibe/:type", s.getVibeInfo)

		// Fix endpoints
		v1.POST("/fix", s.autoFix)
		v1.GET("/fix/:id", s.getFixResult)

		// Watch endpoints
		v1.POST("/watch/start", s.startWatch)
		v1.POST("/watch/stop", s.stopWatch)
		v1.GET("/watch/status", s.getWatchStatus)

		// Profile endpoints
		v1.POST("/profile", s.startProfile)
		v1.GET("/profile/:id", s.getProfileResult)

		// Integration endpoints
		v1.POST("/integrations/slack/webhook", s.slackWebhook)
		v1.POST("/integrations/github/webhook", s.githubWebhook)
	}

	// WebSocket endpoint
	router.GET("/ws", s.handleWebSocket)

	// Static files (dashboard)
	router.Static("/static", "./web/static")
	router.StaticFile("/", "./web/dashboard.html")
}

// Middleware functions

func (s *Server) corsMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Origin, Content-Type, Authorization")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(204)
			return
		}

		c.Next()
	}
}

func (s *Server) loggingMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path
		raw := c.Request.URL.RawQuery

		c.Next()

		latency := time.Since(start)
		clientIP := c.ClientIP()
		method := c.Request.Method
		statusCode := c.Writer.Status()

		if raw != "" {
			path = path + "?" + raw
		}

		s.logger.WithFields(logrus.Fields{
			"status":    statusCode,
			"latency":   latency,
			"client_ip": clientIP,
			"method":    method,
			"path":      path,
		}).Info("HTTP request")
	}
}

// API Handlers

func (s *Server) healthCheck(c *gin.Context) {
	c.JSON(http.StatusOK, gin.H{
		"status":  "healthy",
		"version": "1.0.0",
		"time":    time.Now().UTC(),
	})
}

func (s *Server) createScan(c *gin.Context) {
	var request models.ScanRequest
	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// Set ID if not provided
	if request.ID == "" {
		request.ID = uuid.New().String()
	}
	request.CreatedAt = time.Now()

	// Run scan asynchronously
	go func() {
		ctx := context.Background()
		result, err := s.scanner.Scan(ctx, &request)
		if err != nil {
			s.logger.Errorf("Scan failed: %v", err)
			return
		}

		// Broadcast result to WebSocket clients
		s.broadcastScanResult(result)
	}()

	c.JSON(http.StatusAccepted, gin.H{
		"scan_id": request.ID,
		"status":  "started",
	})
}

func (s *Server) getScan(c *gin.Context) {
	scanID := c.Param("id")

	// TODO: Implement scan storage and retrieval
	c.JSON(http.StatusNotImplemented, gin.H{
		"error":   "Scan storage not implemented yet",
		"scan_id": scanID,
	})
}

func (s *Server) listScans(c *gin.Context) {
	// TODO: Implement scan listing
	c.JSON(http.StatusOK, gin.H{
		"scans": []gin.H{},
		"total": 0,
	})
}

func (s *Server) deleteScan(c *gin.Context) {
	scanID := c.Param("id")

	// TODO: Implement scan deletion
	c.JSON(http.StatusOK, gin.H{
		"message": "Scan deleted",
		"scan_id": scanID,
	})
}

func (s *Server) getConfig(c *gin.Context) {
	c.JSON(http.StatusOK, s.config)
}

func (s *Server) updateConfig(c *gin.Context) {
	var newConfig models.Configuration
	if err := c.ShouldBindJSON(&newConfig); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// TODO: Implement config update and validation
	s.config = &newConfig

	c.JSON(http.StatusOK, gin.H{
		"message": "Configuration updated",
	})
}

func (s *Server) validateConfig(c *gin.Context) {
	var configToValidate models.Configuration
	if err := c.ShouldBindJSON(&configToValidate); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// TODO: Implement proper config validation
	c.JSON(http.StatusOK, gin.H{
		"valid":   true,
		"message": "Configuration is valid",
	})
}

func (s *Server) listReports(c *gin.Context) {
	// TODO: Implement report listing
	c.JSON(http.StatusOK, gin.H{
		"reports": []gin.H{},
		"total":   0,
	})
}

func (s *Server) getReport(c *gin.Context) {
	reportID := c.Param("id")

	// TODO: Implement report retrieval
	c.JSON(http.StatusNotImplemented, gin.H{
		"error":     "Report storage not implemented yet",
		"report_id": reportID,
	})
}

func (s *Server) downloadReport(c *gin.Context) {
	reportID := c.Param("id")
	format := c.DefaultQuery("format", "html")

	// TODO: Implement report download
	c.JSON(http.StatusNotImplemented, gin.H{
		"error":     "Report download not implemented yet",
		"report_id": reportID,
		"format":    format,
	})
}

func (s *Server) listVibes(c *gin.Context) {
	vibes := []gin.H{
		{"type": "security", "name": "SecurityVibe", "description": "Detect secrets and vulnerabilities"},
		{"type": "code", "name": "CodeVibe", "description": "Code quality and anti-patterns"},
		{"type": "performance", "name": "PerformanceVibe", "description": "Performance issues and optimizations"},
		{"type": "file", "name": "FileVibe", "description": "File organization and cleanup"},
		{"type": "git", "name": "GitVibe", "description": "Git hygiene and commit quality"},
		{"type": "dependency", "name": "DependencyVibe", "description": "Dependency management"},
		{"type": "documentation", "name": "DocumentationVibe", "description": "Documentation quality"},
	}

	c.JSON(http.StatusOK, gin.H{
		"vibes": vibes,
		"total": len(vibes),
	})
}

func (s *Server) getVibeInfo(c *gin.Context) {
	vibeType := c.Param("type")

	// TODO: Get actual vibe info from registry
	c.JSON(http.StatusOK, gin.H{
		"type":     vibeType,
		"name":     fmt.Sprintf("%sVibe", vibeType),
		"rules":    []gin.H{},
		"settings": gin.H{},
	})
}

func (s *Server) autoFix(c *gin.Context) {
	var request struct {
		Paths   []string `json:"paths"`
		Rules   []string `json:"rules"`
		AutoFix bool     `json:"auto_fix"`
		Backup  bool     `json:"backup"`
	}

	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	fixID := uuid.New().String()

	// TODO: Implement auto-fix functionality
	c.JSON(http.StatusAccepted, gin.H{
		"fix_id": fixID,
		"status": "started",
	})
}

func (s *Server) getFixResult(c *gin.Context) {
	fixID := c.Param("id")

	// TODO: Implement fix result retrieval
	c.JSON(http.StatusNotImplemented, gin.H{
		"error":  "Fix result storage not implemented yet",
		"fix_id": fixID,
	})
}

func (s *Server) startWatch(c *gin.Context) {
	var request struct {
		Paths   []string `json:"paths"`
		Vibes   []string `json:"vibes"`
		AutoFix bool     `json:"auto_fix"`
	}

	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	// TODO: Implement file watching
	c.JSON(http.StatusOK, gin.H{
		"status": "watching",
		"paths":  request.Paths,
	})
}

func (s *Server) stopWatch(c *gin.Context) {
	// TODO: Implement watch stopping
	c.JSON(http.StatusOK, gin.H{
		"status": "stopped",
	})
}

func (s *Server) getWatchStatus(c *gin.Context) {
	// TODO: Implement watch status
	c.JSON(http.StatusOK, gin.H{
		"watching": false,
		"paths":    []string{},
	})
}

func (s *Server) startProfile(c *gin.Context) {
	var request struct {
		Tool string `json:"tool"`
		URL  string `json:"url"`
	}

	if err := c.ShouldBindJSON(&request); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": err.Error()})
		return
	}

	profileID := uuid.New().String()

	// TODO: Implement profiling
	c.JSON(http.StatusAccepted, gin.H{
		"profile_id": profileID,
		"status":     "started",
		"tool":       request.Tool,
	})
}

func (s *Server) getProfileResult(c *gin.Context) {
	profileID := c.Param("id")

	// TODO: Implement profile result retrieval
	c.JSON(http.StatusNotImplemented, gin.H{
		"error":      "Profile result storage not implemented yet",
		"profile_id": profileID,
	})
}

func (s *Server) slackWebhook(c *gin.Context) {
	// TODO: Implement Slack webhook
	c.JSON(http.StatusOK, gin.H{
		"message": "Slack webhook received",
	})
}

func (s *Server) githubWebhook(c *gin.Context) {
	// TODO: Implement GitHub webhook
	c.JSON(http.StatusOK, gin.H{
		"message": "GitHub webhook received",
	})
}

// WebSocket handling

func (s *Server) handleWebSocket(c *gin.Context) {
	conn, err := s.upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		s.logger.Errorf("WebSocket upgrade failed: %v", err)
		return
	}
	defer conn.Close()

	clientID := uuid.New().String()
	s.clients[clientID] = conn

	s.logger.Infof("WebSocket client connected: %s", clientID)

	// Send welcome message
	welcome := gin.H{
		"type":      "welcome",
		"client_id": clientID,
		"message":   "Connected to KodeVibe",
	}
	if err := conn.WriteJSON(welcome); err != nil {
		s.logger.Errorf("Failed to send welcome message: %v", err)
		return
	}

	// Handle messages
	for {
		var msg gin.H
		err := conn.ReadJSON(&msg)
		if err != nil {
			s.logger.Infof("WebSocket client disconnected: %s", clientID)
			delete(s.clients, clientID)
			break
		}

		// Echo message back (for now)
		if err := conn.WriteJSON(gin.H{
			"type": "echo",
			"data": msg,
		}); err != nil {
			s.logger.Errorf("Failed to send echo message: %v", err)
			break
		}
	}
}

func (s *Server) broadcastScanResult(result *models.ScanResult) {
	message := gin.H{
		"type": "scan_complete",
		"data": result,
	}

	for clientID, conn := range s.clients {
		err := conn.WriteJSON(message)
		if err != nil {
			s.logger.Errorf("Failed to send message to client %s: %v", clientID, err)
			delete(s.clients, clientID)
		}
	}
}
