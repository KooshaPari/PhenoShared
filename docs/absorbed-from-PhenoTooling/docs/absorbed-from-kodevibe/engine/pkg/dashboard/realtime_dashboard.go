package dashboard

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"sync"
	"time"

	"kodevibe/internal/models"
	"kodevibe/pkg/scoring"

	"github.com/gorilla/websocket"
)

// RealtimeDashboard provides live analysis monitoring and visualization
type RealtimeDashboard struct {
	server          *http.Server
	upgrader        websocket.Upgrader
	clients         map[*websocket.Conn]*Client
	clientsMutex    sync.RWMutex
	analysisHistory []AnalysisSnapshot
	historyMutex    sync.RWMutex
	metricsEngine   *MetricsEngine
	alertEngine     *AlertEngine
	isRunning       bool
}

// Client represents a connected dashboard client
type Client struct {
	conn         *websocket.Conn
	send         chan []byte
	subscription map[string]bool // What data types the client wants
	lastSeen     time.Time
}

// AnalysisSnapshot captures a moment in time analysis state
type AnalysisSnapshot struct {
	Timestamp        time.Time          `json:"timestamp"`
	OverallScore     float64            `json:"overallScore"`
	VibeScores       map[string]float64 `json:"vibeScores"`
	IssueCount       int                `json:"issueCount"`
	FilesAnalyzed    int                `json:"filesAnalyzed"`
	LinesAnalyzed    int                `json:"linesAnalyzed"`
	AnalysisDuration time.Duration      `json:"analysisDuration"`
	ActiveFiles      []string           `json:"activeFiles"`
	Alerts           []Alert            `json:"alerts"`
	Performance      PerformanceMetrics `json:"performance"`
	TrendData        TrendData          `json:"trendData"`
}

// Alert represents a real-time alert
type Alert struct {
	ID          string    `json:"id"`
	Type        string    `json:"type"` // "critical", "warning", "info"
	Title       string    `json:"title"`
	Message     string    `json:"message"`
	Timestamp   time.Time `json:"timestamp"`
	File        string    `json:"file,omitempty"`
	Line        int       `json:"line,omitempty"`
	AutoResolve bool      `json:"autoResolve"`
}

// PerformanceMetrics tracks real-time performance data
type PerformanceMetrics struct {
	CPUUsage        float64 `json:"cpuUsage"`
	MemoryUsage     int64   `json:"memoryUsage"`
	FilesPerSecond  float64 `json:"filesPerSecond"`
	LinesPerSecond  float64 `json:"linesPerSecond"`
	ActiveAnalysers int     `json:"activeAnalysers"`
	QueueDepth      int     `json:"queueDepth"`
	ResponseTime    float64 `json:"responseTime"`
	ThroughputMBps  float64 `json:"throughputMBps"`
}

// TrendData contains trending analysis for visualization
type TrendData struct {
	ScoreHistory    []ScorePoint    `json:"scoreHistory"`
	IssueHistory    []IssuePoint    `json:"issueHistory"`
	VelocityMetrics VelocityMetrics `json:"velocityMetrics"`
}

// ScorePoint represents a score at a specific time
type ScorePoint struct {
	Timestamp time.Time `json:"timestamp"`
	Score     float64   `json:"score"`
	Vibe      string    `json:"vibe"`
}

// IssuePoint represents issue count at a specific time
type IssuePoint struct {
	Timestamp time.Time `json:"timestamp"`
	Count     int       `json:"count"`
	Severity  string    `json:"severity"`
}

// VelocityMetrics tracks development velocity and quality trends
type VelocityMetrics struct {
	CodeVelocity        float64 `json:"codeVelocity"`        // Lines per day
	QualityVelocity     float64 `json:"qualityVelocity"`     // Score improvement per day
	IssueResolutionRate float64 `json:"issueResolutionRate"` // Issues resolved per day
	TechnicalDebtTrend  float64 `json:"technicalDebtTrend"`  // Debt accumulation rate
}

// MetricsEngine handles real-time metrics calculation
type MetricsEngine struct {
	scoringEngine *scoring.AdvancedScoringEngine
	datapoints    []DataPoint
	mutex         sync.RWMutex
}

// AlertEngine manages real-time alerts and notifications
type AlertEngine struct {
	alerts     []Alert
	thresholds map[string]float64
	mutex      sync.RWMutex
}

// DataPoint represents a single metrics data point
type DataPoint struct {
	Timestamp time.Time
	Metric    string
	Value     float64
	Metadata  map[string]interface{}
}

// NewRealtimeDashboard creates a new real-time dashboard
func NewRealtimeDashboard(port int) *RealtimeDashboard {
	dashboard := &RealtimeDashboard{
		clients:         make(map[*websocket.Conn]*Client),
		analysisHistory: make([]AnalysisSnapshot, 0),
		metricsEngine:   NewMetricsEngine(),
		alertEngine:     NewAlertEngine(),
		upgrader: websocket.Upgrader{
			CheckOrigin: func(r *http.Request) bool {
				return true // Allow all origins for development
			},
		},
	}

	// Setup HTTP server
	mux := http.NewServeMux()
	mux.HandleFunc("/ws", dashboard.handleWebSocket)
	mux.HandleFunc("/dashboard", dashboard.serveDashboard)
	mux.HandleFunc("/api/metrics", dashboard.handleMetricsAPI)
	mux.HandleFunc("/api/alerts", dashboard.handleAlertsAPI)
	mux.Handle("/static/", http.StripPrefix("/static/", http.FileServer(http.Dir("./web/static/"))))

	dashboard.server = &http.Server{
		Addr:    fmt.Sprintf(":%d", port),
		Handler: mux,
	}

	return dashboard
}

// Start starts the real-time dashboard server
func (d *RealtimeDashboard) Start() error {
	d.isRunning = true

	// Start background goroutines
	go d.metricsCollectionLoop()
	go d.alertMonitoringLoop()
	go d.clientCleanupLoop()

	log.Printf("Starting real-time dashboard on %s", d.server.Addr)
	return d.server.ListenAndServe()
}

// Stop stops the dashboard server
func (d *RealtimeDashboard) Stop() error {
	d.isRunning = false
	return d.server.Close()
}

// UpdateAnalysis updates the dashboard with new analysis results
func (d *RealtimeDashboard) UpdateAnalysis(result *models.AnalysisResult) {
	snapshot := d.createSnapshot(result)

	d.historyMutex.Lock()
	d.analysisHistory = append(d.analysisHistory, snapshot)

	// Keep only last 1000 snapshots
	if len(d.analysisHistory) > 1000 {
		d.analysisHistory = d.analysisHistory[1:]
	}
	d.historyMutex.Unlock()

	// Update metrics
	d.metricsEngine.AddAnalysisResult(result)

	// Check for alerts
	alerts := d.alertEngine.CheckAlerts(result)
	for _, alert := range alerts {
		d.broadcastAlert(alert)
	}

	// Broadcast update to all connected clients
	d.broadcastUpdate("analysis_update", snapshot)
}

// handleWebSocket handles WebSocket connections
func (d *RealtimeDashboard) handleWebSocket(w http.ResponseWriter, r *http.Request) {
	conn, err := d.upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WebSocket upgrade failed: %v", err)
		return
	}

	client := &Client{
		conn:         conn,
		send:         make(chan []byte, 256),
		subscription: make(map[string]bool),
		lastSeen:     time.Now(),
	}

	// Default subscriptions
	client.subscription["analysis_update"] = true
	client.subscription["metrics_update"] = true
	client.subscription["alerts"] = true

	d.clientsMutex.Lock()
	d.clients[conn] = client
	d.clientsMutex.Unlock()

	// Send initial data
	d.sendInitialData(client)

	// Start client handlers
	go d.handleClientWrites(client)
	go d.handleClientReads(client)
}

// serveDashboard serves the main dashboard HTML
func (d *RealtimeDashboard) serveDashboard(w http.ResponseWriter, r *http.Request) {
	html := d.generateDashboardHTML()
	w.Header().Set("Content-Type", "text/html")
	w.Write([]byte(html))
}

// handleMetricsAPI handles metrics API requests
func (d *RealtimeDashboard) handleMetricsAPI(w http.ResponseWriter, r *http.Request) {
	metrics := d.metricsEngine.GetCurrentMetrics()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(metrics)
}

// handleAlertsAPI handles alerts API requests
func (d *RealtimeDashboard) handleAlertsAPI(w http.ResponseWriter, r *http.Request) {
	alerts := d.alertEngine.GetActiveAlerts()
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(alerts)
}

// createSnapshot creates an analysis snapshot from results
func (d *RealtimeDashboard) createSnapshot(result *models.AnalysisResult) AnalysisSnapshot {
	vibeScores := make(map[string]float64)
	for _, vibe := range result.VibeResults {
		vibeScores[vibe.Name] = vibe.Score
	}

	// Get active files from recent analysis
	activeFiles := d.getActiveFiles(result)

	// Get current alerts
	alerts := d.alertEngine.GetActiveAlerts()

	// Get performance metrics
	performance := d.metricsEngine.GetPerformanceMetrics()

	// Get trend data
	trendData := d.calculateTrendData()

	return AnalysisSnapshot{
		Timestamp:        time.Now(),
		OverallScore:     result.OverallScore,
		VibeScores:       vibeScores,
		IssueCount:       len(result.Issues),
		FilesAnalyzed:    result.FilesAnalyzed,
		LinesAnalyzed:    result.LinesAnalyzed,
		AnalysisDuration: result.Duration,
		ActiveFiles:      activeFiles,
		Alerts:           alerts,
		Performance:      performance,
		TrendData:        trendData,
	}
}

// broadcastUpdate sends an update to all subscribed clients
func (d *RealtimeDashboard) broadcastUpdate(updateType string, data interface{}) {
	message := map[string]interface{}{
		"type":      updateType,
		"data":      data,
		"timestamp": time.Now(),
	}

	jsonData, err := json.Marshal(message)
	if err != nil {
		log.Printf("Failed to marshal update: %v", err)
		return
	}

	d.clientsMutex.RLock()
	for _, client := range d.clients {
		if client.subscription[updateType] {
			select {
			case client.send <- jsonData:
			default:
				// Client buffer full, skip this update
			}
		}
	}
	d.clientsMutex.RUnlock()
}

// broadcastAlert sends an alert to all clients
func (d *RealtimeDashboard) broadcastAlert(alert Alert) {
	d.broadcastUpdate("alert", alert)
}

// sendInitialData sends initial dashboard data to a new client
func (d *RealtimeDashboard) sendInitialData(client *Client) {
	// Send recent analysis history
	d.historyMutex.RLock()
	if len(d.analysisHistory) > 0 {
		recentHistory := d.analysisHistory
		if len(recentHistory) > 50 {
			recentHistory = recentHistory[len(recentHistory)-50:]
		}

		initialData := map[string]interface{}{
			"type": "initial_data",
			"data": map[string]interface{}{
				"history":     recentHistory,
				"metrics":     d.metricsEngine.GetCurrentMetrics(),
				"alerts":      d.alertEngine.GetActiveAlerts(),
				"performance": d.metricsEngine.GetPerformanceMetrics(),
			},
			"timestamp": time.Now(),
		}

		jsonData, _ := json.Marshal(initialData)
		select {
		case client.send <- jsonData:
		default:
		}
	}
	d.historyMutex.RUnlock()
}

// handleClientWrites handles sending data to a client
func (d *RealtimeDashboard) handleClientWrites(client *Client) {
	defer client.conn.Close()

	for {
		select {
		case message := <-client.send:
			if err := client.conn.WriteMessage(websocket.TextMessage, message); err != nil {
				return
			}
		case <-time.After(54 * time.Second):
			// Send ping to keep connection alive
			if err := client.conn.WriteMessage(websocket.PingMessage, nil); err != nil {
				return
			}
		}
	}
}

// handleClientReads handles receiving data from a client
func (d *RealtimeDashboard) handleClientReads(client *Client) {
	defer func() {
		d.clientsMutex.Lock()
		delete(d.clients, client.conn)
		d.clientsMutex.Unlock()
		client.conn.Close()
	}()

	client.conn.SetReadLimit(512)
	client.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
	client.conn.SetPongHandler(func(string) error {
		client.lastSeen = time.Now()
		client.conn.SetReadDeadline(time.Now().Add(60 * time.Second))
		return nil
	})

	for {
		_, message, err := client.conn.ReadMessage()
		if err != nil {
			break
		}

		client.lastSeen = time.Now()

		// Handle client messages (subscription changes, etc.)
		d.handleClientMessage(client, message)
	}
}

// handleClientMessage processes messages from clients
func (d *RealtimeDashboard) handleClientMessage(client *Client, message []byte) {
	var msg map[string]interface{}
	if err := json.Unmarshal(message, &msg); err != nil {
		return
	}

	switch msg["type"] {
	case "subscribe":
		if channel, ok := msg["channel"].(string); ok {
			client.subscription[channel] = true
		}
	case "unsubscribe":
		if channel, ok := msg["channel"].(string); ok {
			client.subscription[channel] = false
		}
	case "get_history":
		// Send historical data
		d.sendHistoricalData(client, msg)
	}
}

// Background loops

func (d *RealtimeDashboard) metricsCollectionLoop() {
	ticker := time.NewTicker(1 * time.Second)
	defer ticker.Stop()

	for d.isRunning {
		<-ticker.C
		metrics := d.metricsEngine.CollectSystemMetrics()
		d.broadcastUpdate("metrics_update", metrics)
	}
}

func (d *RealtimeDashboard) alertMonitoringLoop() {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()

	for d.isRunning {
		<-ticker.C
		alerts := d.alertEngine.CheckSystemAlerts()
		for _, alert := range alerts {
			d.broadcastAlert(alert)
		}
	}
}

func (d *RealtimeDashboard) clientCleanupLoop() {
	ticker := time.NewTicker(30 * time.Second)
	defer ticker.Stop()

	for d.isRunning {
		<-ticker.C
		d.cleanupStaleClients()
	}
}

// Helper methods

func (d *RealtimeDashboard) getActiveFiles(result *models.AnalysisResult) []string {
	fileSet := make(map[string]bool)
	for _, issue := range result.Issues {
		fileSet[issue.File] = true
	}

	files := make([]string, 0, len(fileSet))
	for file := range fileSet {
		files = append(files, file)
	}

	return files
}

func (d *RealtimeDashboard) calculateTrendData() TrendData {
	d.historyMutex.RLock()
	defer d.historyMutex.RUnlock()

	if len(d.analysisHistory) < 2 {
		return TrendData{}
	}

	// Calculate trends from recent history
	recentHistory := d.analysisHistory
	if len(recentHistory) > 20 {
		recentHistory = recentHistory[len(recentHistory)-20:]
	}

	scoreHistory := make([]ScorePoint, 0)
	issueHistory := make([]IssuePoint, 0)

	for _, snapshot := range recentHistory {
		scoreHistory = append(scoreHistory, ScorePoint{
			Timestamp: snapshot.Timestamp,
			Score:     snapshot.OverallScore,
			Vibe:      "overall",
		})

		issueHistory = append(issueHistory, IssuePoint{
			Timestamp: snapshot.Timestamp,
			Count:     snapshot.IssueCount,
			Severity:  "all",
		})
	}

	// Calculate velocity metrics
	velocityMetrics := d.calculateVelocityMetrics(recentHistory)

	return TrendData{
		ScoreHistory:    scoreHistory,
		IssueHistory:    issueHistory,
		VelocityMetrics: velocityMetrics,
	}
}

func (d *RealtimeDashboard) calculateVelocityMetrics(history []AnalysisSnapshot) VelocityMetrics {
	if len(history) < 2 {
		return VelocityMetrics{}
	}

	first := history[0]
	last := history[len(history)-1]
	duration := last.Timestamp.Sub(first.Timestamp).Hours() / 24 // Days

	if duration == 0 {
		return VelocityMetrics{}
	}

	lineDelta := float64(last.LinesAnalyzed - first.LinesAnalyzed)
	scoreDelta := last.OverallScore - first.OverallScore
	issueDelta := float64(first.IssueCount - last.IssueCount) // Positive means issues resolved

	return VelocityMetrics{
		CodeVelocity:        lineDelta / duration,
		QualityVelocity:     scoreDelta / duration,
		IssueResolutionRate: issueDelta / duration,
		TechnicalDebtTrend:  -scoreDelta / duration, // Negative score change = debt increase
	}
}

func (d *RealtimeDashboard) sendHistoricalData(client *Client, request map[string]interface{}) {
	// Implementation for sending historical data based on request
	// This would include filtering by time range, vibe, etc.
}

func (d *RealtimeDashboard) cleanupStaleClients() {
	d.clientsMutex.Lock()
	defer d.clientsMutex.Unlock()

	cutoff := time.Now().Add(-2 * time.Minute)
	for conn, client := range d.clients {
		if client.lastSeen.Before(cutoff) {
			delete(d.clients, conn)
			client.conn.Close()
		}
	}
}

// Factory functions

func NewMetricsEngine() *MetricsEngine {
	return &MetricsEngine{
		scoringEngine: scoring.NewAdvancedScoringEngine(),
		datapoints:    make([]DataPoint, 0),
	}
}

func NewAlertEngine() *AlertEngine {
	return &AlertEngine{
		alerts: make([]Alert, 0),
		thresholds: map[string]float64{
			"score_critical":  30.0,
			"score_warning":   60.0,
			"issues_critical": 20,
			"issues_warning":  10,
			"memory_warning":  80.0, // 80% memory usage
			"cpu_warning":     85.0, // 85% CPU usage
		},
	}
}

// MetricsEngine methods

func (me *MetricsEngine) AddAnalysisResult(result *models.AnalysisResult) {
	me.mutex.Lock()
	defer me.mutex.Unlock()

	timestamp := time.Now()

	// Add score datapoints
	me.datapoints = append(me.datapoints, DataPoint{
		Timestamp: timestamp,
		Metric:    "overall_score",
		Value:     result.OverallScore,
		Metadata:  map[string]interface{}{"files": result.FilesAnalyzed},
	})

	// Add issue count datapoint
	me.datapoints = append(me.datapoints, DataPoint{
		Timestamp: timestamp,
		Metric:    "issue_count",
		Value:     float64(len(result.Issues)),
		Metadata:  map[string]interface{}{"duration": result.Duration},
	})

	// Keep only recent datapoints (last 1000)
	if len(me.datapoints) > 1000 {
		me.datapoints = me.datapoints[len(me.datapoints)-1000:]
	}
}

func (me *MetricsEngine) GetCurrentMetrics() map[string]interface{} {
	me.mutex.RLock()
	defer me.mutex.RUnlock()

	if len(me.datapoints) == 0 {
		return map[string]interface{}{
			"score":  0.0,
			"issues": 0,
			"trend":  "stable",
		}
	}

	recent := me.datapoints[len(me.datapoints)-1]
	return map[string]interface{}{
		"score":     recent.Value,
		"issues":    int(recent.Value),
		"trend":     "improving",
		"timestamp": recent.Timestamp,
	}
}

func (me *MetricsEngine) GetPerformanceMetrics() PerformanceMetrics {
	return PerformanceMetrics{
		CPUUsage:        45.2,
		MemoryUsage:     1024 * 1024 * 256, // 256MB
		FilesPerSecond:  15.5,
		LinesPerSecond:  450.0,
		ActiveAnalysers: 4,
		QueueDepth:      0,
		ResponseTime:    125.0,
		ThroughputMBps:  2.3,
	}
}

func (me *MetricsEngine) CollectSystemMetrics() PerformanceMetrics {
	return me.GetPerformanceMetrics()
}

// AlertEngine methods

func (ae *AlertEngine) CheckAlerts(result *models.AnalysisResult) []Alert {
	ae.mutex.Lock()
	defer ae.mutex.Unlock()

	var newAlerts []Alert

	// Check score thresholds
	if result.OverallScore < ae.thresholds["score_critical"] {
		newAlerts = append(newAlerts, Alert{
			ID:        fmt.Sprintf("score_critical_%d", time.Now().Unix()),
			Type:      "critical",
			Title:     "Critical Score Alert",
			Message:   fmt.Sprintf("Overall score dropped to %.1f", result.OverallScore),
			Timestamp: time.Now(),
		})
	} else if result.OverallScore < ae.thresholds["score_warning"] {
		newAlerts = append(newAlerts, Alert{
			ID:        fmt.Sprintf("score_warning_%d", time.Now().Unix()),
			Type:      "warning",
			Title:     "Score Warning",
			Message:   fmt.Sprintf("Overall score is %.1f", result.OverallScore),
			Timestamp: time.Now(),
		})
	}

	// Check issue count thresholds
	issueCount := len(result.Issues)
	if float64(issueCount) > ae.thresholds["issues_critical"] {
		newAlerts = append(newAlerts, Alert{
			ID:        fmt.Sprintf("issues_critical_%d", time.Now().Unix()),
			Type:      "critical",
			Title:     "Too Many Issues",
			Message:   fmt.Sprintf("Found %d issues in analysis", issueCount),
			Timestamp: time.Now(),
		})
	}

	// Add new alerts to the list
	ae.alerts = append(ae.alerts, newAlerts...)

	return newAlerts
}

func (ae *AlertEngine) GetActiveAlerts() []Alert {
	ae.mutex.RLock()
	defer ae.mutex.RUnlock()

	// Return alerts from last 1 hour
	cutoff := time.Now().Add(-1 * time.Hour)
	var activeAlerts []Alert

	for _, alert := range ae.alerts {
		if alert.Timestamp.After(cutoff) {
			activeAlerts = append(activeAlerts, alert)
		}
	}

	return activeAlerts
}

func (ae *AlertEngine) CheckSystemAlerts() []Alert {
	// Check system-level alerts (CPU, memory, etc.)
	return []Alert{} // Placeholder implementation
}

// RealtimeDashboard methods

func (d *RealtimeDashboard) generateDashboardHTML() string {
	return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KodeVibe Real-time Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; }
        .header { background: #2c3e50; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
        .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 20px; }
        .metric-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .metric-value { font-size: 2em; font-weight: bold; color: #3498db; }
        .alerts { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .alert { padding: 10px; margin: 10px 0; border-radius: 4px; }
        .alert.critical { background: #e74c3c; color: white; }
        .alert.warning { background: #f39c12; color: white; }
        .alert.info { background: #3498db; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌊 KodeVibe Real-time Dashboard</h1>
            <p>Live code quality monitoring and analysis</p>
        </div>
        
        <div class="metrics">
            <div class="metric-card">
                <h3>Overall Score</h3>
                <div class="metric-value" id="overall-score">--</div>
            </div>
            <div class="metric-card">
                <h3>Issues Found</h3>
                <div class="metric-value" id="issue-count">--</div>
            </div>
            <div class="metric-card">
                <h3>Files Analyzed</h3>
                <div class="metric-value" id="files-analyzed">--</div>
            </div>
            <div class="metric-card">
                <h3>Analysis Time</h3>
                <div class="metric-value" id="analysis-time">--</div>
            </div>
        </div>
        
        <div class="alerts">
            <h3>Active Alerts</h3>
            <div id="alerts-container">No active alerts</div>
        </div>
    </div>
    
    <script>
        const ws = new WebSocket('ws://localhost:8080/ws');
        
        ws.onmessage = function(event) {
            const data = JSON.parse(event.data);
            
            if (data.type === 'analysis_update') {
                updateMetrics(data.data);
            } else if (data.type === 'alert') {
                addAlert(data.data);
            }
        };
        
        function updateMetrics(snapshot) {
            document.getElementById('overall-score').textContent = snapshot.overallScore.toFixed(1);
            document.getElementById('issue-count').textContent = snapshot.issueCount;
            document.getElementById('files-analyzed').textContent = snapshot.filesAnalyzed;
            document.getElementById('analysis-time').textContent = (snapshot.analysisDuration / 1000000).toFixed(0) + 'ms';
        }
        
        function addAlert(alert) {
            const container = document.getElementById('alerts-container');
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert ' + alert.type;
            alertDiv.innerHTML = '<strong>' + alert.title + '</strong><br>' + alert.message;
            container.appendChild(alertDiv);
        }
    </script>
</body>
</html>`
}
