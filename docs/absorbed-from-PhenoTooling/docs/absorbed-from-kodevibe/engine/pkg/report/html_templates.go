package report

// HTML template for the interactive report
const htmlTemplate = `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>KodeVibe Analysis Report - {{.ProjectName}}</title>
    <link rel="stylesheet" href="styles.css">
    <script src="assets/chart.min.js"></script>
</head>
<body>
    <div class="header">
        <div class="container">
            <h1>🌊 KodeVibe Analysis Report</h1>
            <div class="project-info">
                <h2>{{.ProjectName}}</h2>
                <p>Generated on {{.GeneratedAt.Format "January 2, 2006 at 3:04 PM"}}</p>
            </div>
        </div>
    </div>

    <div class="container">
        <!-- Summary Dashboard -->
        <div class="dashboard">
            <div class="card score-card">
                <h3>Overall Score</h3>
                <div class="score-display">
                    <div class="score-circle" data-score="{{.OverallScore}}">
                        <span class="score-value">{{printf "%.1f" .OverallScore}}</span>
                        <span class="score-max">/100</span>
                    </div>
                </div>
                <div class="score-grade">{{if ge .OverallScore 90}}⭐⭐⭐⭐⭐ Excellent{{else if ge .OverallScore 80}}⭐⭐⭐⭐ Very Good{{else if ge .OverallScore 70}}⭐⭐⭐ Good{{else if ge .OverallScore 60}}⭐⭐ Fair{{else}}⭐ Needs Improvement{{end}}</div>
            </div>

            <div class="card stats-card">
                <h3>Analysis Statistics</h3>
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-value">{{.TotalFiles}}</span>
                        <span class="stat-label">Files Analyzed</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">{{.TotalLines}}</span>
                        <span class="stat-label">Lines of Code</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">{{len .Issues}}</span>
                        <span class="stat-label">Issues Found</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-value">{{printf "%.1fs" .AnalysisDuration.Seconds}}</span>
                        <span class="stat-label">Analysis Time</span>
                    </div>
                </div>
            </div>

            <div class="card performance-card">
                <h3>Performance Metrics</h3>
                <div class="performance-grid">
                    <div class="perf-item">
                        <span class="perf-value">{{printf "%.1f" .PerformanceData.FilesPerSecond}}</span>
                        <span class="perf-label">Files/sec</span>
                    </div>
                    <div class="perf-item">
                        <span class="perf-value">{{printf "%.0fMB" (div .PerformanceData.MemoryUsage 1048576)}}</span>
                        <span class="perf-label">Memory Used</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs">
            <button class="tab-button active" onclick="showTab('overview')">📊 Overview</button>
            <button class="tab-button" onclick="showTab('vibes')">🎯 Vibes Analysis</button>
            <button class="tab-button" onclick="showTab('issues')">🚨 Issues</button>
            <button class="tab-button" onclick="showTab('security')">🔒 Security</button>
            <button class="tab-button" onclick="showTab('files')">📁 File Metrics</button>
            <button class="tab-button" onclick="showTab('trends')">📈 Trends</button>
        </div>

        <!-- Tab Content -->
        <div id="overview" class="tab-content active">
            <div class="section">
                <h3>📊 Score Breakdown</h3>
                <div class="chart-container">
                    <canvas id="vibesChart"></canvas>
                </div>
            </div>

            <div class="section">
                <h3>💡 Key Recommendations</h3>
                <div class="recommendations">
                    {{range .Recommendations}}
                    <div class="recommendation-item">
                        <span class="rec-icon">💡</span>
                        <span class="rec-text">{{.}}</span>
                    </div>
                    {{end}}
                </div>
            </div>
        </div>

        <div id="vibes" class="tab-content">
            <div class="section">
                <h3>🎯 Vibes Analysis Results</h3>
                <div class="vibes-grid">
                    {{range .VibeResults}}
                    <div class="vibe-card">
                        <div class="vibe-header">
                            <h4>{{title .Name}}</h4>
                            <div class="vibe-score {{if ge .Score 90}}excellent{{else if ge .Score 70}}good{{else}}poor{{end}}">
                                {{printf "%.1f" .Score}}/100
                            </div>
                        </div>
                        <div class="vibe-progress">
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {{.Score}}%"></div>
                            </div>
                        </div>
                        {{if .Details}}
                        <div class="vibe-details">{{.Details}}</div>
                        {{end}}
                    </div>
                    {{end}}
                </div>
            </div>
        </div>

        <div id="issues" class="tab-content">
            <div class="section">
                <h3>🚨 Issues Summary</h3>
                <div class="issues-summary">
                    <div class="severity-chart">
                        <canvas id="severityChart"></canvas>
                    </div>
                    <div class="issues-list">
                        {{range .Issues}}
                        <div class="issue-item severity-{{.Severity}}">
                            <div class="issue-header">
                                <span class="severity-badge {{.Severity}}">{{upper .Severity}}</span>
                                <span class="issue-file">{{.File}}:{{.Line}}</span>
                            </div>
                            <div class="issue-message">{{.Message}}</div>
                            {{if .Fix}}
                            <div class="issue-fix">
                                <strong>Suggested Fix:</strong> {{.Fix}}
                            </div>
                            {{end}}
                        </div>
                        {{end}}
                    </div>
                </div>
            </div>
        </div>

        <div id="security" class="tab-content">
            <div class="section">
                <h3>🔒 Security Analysis</h3>
                <div class="security-overview">
                    <div class="security-stats">
                        <div class="security-stat critical">
                            <span class="stat-number" id="criticalCount">0</span>
                            <span class="stat-text">Critical</span>
                        </div>
                        <div class="security-stat high">
                            <span class="stat-number" id="highCount">0</span>
                            <span class="stat-text">High</span>
                        </div>
                        <div class="security-stat medium">
                            <span class="stat-number" id="mediumCount">0</span>
                            <span class="stat-text">Medium</span>
                        </div>
                        <div class="security-stat low">
                            <span class="stat-number" id="lowCount">0</span>
                            <span class="stat-text">Low</span>
                        </div>
                    </div>
                </div>
                <div class="security-issues" id="securityIssues">
                    <!-- Security issues will be populated by JavaScript -->
                </div>
            </div>
        </div>

        <div id="files" class="tab-content">
            <div class="section">
                <h3>📁 File Analysis</h3>
                <div class="file-controls">
                    <input type="text" id="fileSearch" placeholder="Search files..." onkeyup="filterFiles()">
                    <select id="sortFiles" onchange="sortFiles()">
                        <option value="score">Sort by Score</option>
                        <option value="issues">Sort by Issues</option>
                        <option value="lines">Sort by Lines</option>
                        <option value="complexity">Sort by Complexity</option>
                    </select>
                </div>
                <div class="files-table-container">
                    <table class="files-table" id="filesTable">
                        <thead>
                            <tr>
                                <th>File</th>
                                <th>Score</th>
                                <th>Issues</th>
                                <th>Lines</th>
                                <th>Complexity</th>
                                <th>Coverage</th>
                                <th>Last Modified</th>
                            </tr>
                        </thead>
                        <tbody id="filesTableBody">
                            <!-- File data will be populated by JavaScript -->
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div id="trends" class="tab-content">
            <div class="section">
                <h3>📈 Score Trends</h3>
                <div class="trends-controls">
                    <select id="trendsTimeframe">
                        <option value="7">Last 7 days</option>
                        <option value="30" selected>Last 30 days</option>
                        <option value="90">Last 90 days</option>
                    </select>
                    <select id="trendsVibe">
                        <option value="all">All Vibes</option>
                        {{range .VibeResults}}
                        <option value="{{.Name}}">{{title .Name}}</option>
                        {{end}}
                    </select>
                </div>
                <div class="chart-container">
                    <canvas id="trendsChart"></canvas>
                </div>
            </div>
        </div>
    </div>

    <!-- Export Controls -->
    <div class="export-controls">
        <button onclick="exportPDF()" class="export-btn">📄 Export PDF</button>
        <button onclick="exportJSON()" class="export-btn">📊 Export JSON</button>
        <button onclick="exportCSV()" class="export-btn">📋 Export CSV</button>
        <button onclick="shareReport()" class="export-btn">🔗 Share Report</button>
    </div>

    <!-- Footer -->
    <footer class="footer">
        <div class="container">
            <p>Generated by <strong>KodeVibe</strong> - Advanced Code Quality Analysis Tool</p>
            <p>Report generated in {{printf "%.2f" .AnalysisDuration.Seconds}}s | 
               {{.TotalFiles}} files | {{.TotalLines}} lines analyzed</p>
        </div>
    </footer>

    <!-- Data for JavaScript -->
    <script>
        window.reportData = {{.JSONData}};
    </script>
    <script src="script.js"></script>
</body>
</html>
`

// CSS styles for the HTML report
const cssStyles = `
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: #333;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
}

.header {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    padding: 2rem 0;
    margin-bottom: 2rem;
}

.header h1 {
    color: white;
    font-size: 2.5rem;
    font-weight: 300;
    margin-bottom: 0.5rem;
}

.project-info h2 {
    color: #f0f0f0;
    font-size: 1.5rem;
    margin-bottom: 0.25rem;
}

.project-info p {
    color: #d0d0d0;
    font-size: 0.9rem;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 2rem;
}

.dashboard {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 2rem;
    margin-bottom: 2rem;
}

.card {
    background: white;
    border-radius: 12px;
    padding: 2rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
}

.score-card {
    text-align: center;
}

.score-circle {
    width: 120px;
    height: 120px;
    border-radius: 50%;
    background: conic-gradient(from 0deg, #4CAF50 0deg, #4CAF50 calc(var(--score) * 3.6deg), #e0e0e0 calc(var(--score) * 3.6deg), #e0e0e0 360deg);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    margin: 1rem auto;
    position: relative;
}

.score-circle::before {
    content: '';
    position: absolute;
    width: 80px;
    height: 80px;
    background: white;
    border-radius: 50%;
}

.score-value {
    font-size: 2rem;
    font-weight: bold;
    color: #333;
    z-index: 1;
}

.score-max {
    font-size: 0.9rem;
    color: #666;
    z-index: 1;
}

.score-grade {
    font-size: 1.1rem;
    font-weight: 500;
    color: #4CAF50;
    margin-top: 0.5rem;
}

.stats-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
}

.stat-item {
    text-align: center;
}

.stat-value {
    display: block;
    font-size: 1.5rem;
    font-weight: bold;
    color: #667eea;
}

.stat-label {
    font-size: 0.8rem;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.performance-grid {
    display: flex;
    justify-content: space-around;
}

.perf-item {
    text-align: center;
}

.perf-value {
    display: block;
    font-size: 1.3rem;
    font-weight: bold;
    color: #764ba2;
}

.perf-label {
    font-size: 0.8rem;
    color: #666;
}

.tabs {
    display: flex;
    background: white;
    border-radius: 12px 12px 0 0;
    overflow: hidden;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.tab-button {
    flex: 1;
    padding: 1rem;
    border: none;
    background: #f8f9fa;
    cursor: pointer;
    transition: all 0.3s ease;
    font-weight: 500;
}

.tab-button.active {
    background: white;
    color: #667eea;
    border-bottom: 3px solid #667eea;
}

.tab-button:hover {
    background: #e9ecef;
}

.tab-content {
    display: none;
    background: white;
    border-radius: 0 0 12px 12px;
    padding: 2rem;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    margin-bottom: 2rem;
}

.tab-content.active {
    display: block;
}

.section {
    margin-bottom: 2rem;
}

.section h3 {
    margin-bottom: 1rem;
    color: #333;
    font-size: 1.3rem;
}

.chart-container {
    position: relative;
    height: 400px;
    margin: 1rem 0;
}

.recommendations {
    display: grid;
    gap: 1rem;
}

.recommendation-item {
    display: flex;
    align-items: center;
    padding: 1rem;
    background: #f8f9fa;
    border-radius: 8px;
    border-left: 4px solid #667eea;
}

.rec-icon {
    margin-right: 1rem;
    font-size: 1.2rem;
}

.rec-text {
    flex: 1;
}

.vibes-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
}

.vibe-card {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 1.5rem;
    border: 1px solid #e9ecef;
}

.vibe-header {
    display: flex;
    justify-content: between;
    align-items: center;
    margin-bottom: 1rem;
}

.vibe-header h4 {
    margin: 0;
    color: #333;
}

.vibe-score {
    font-weight: bold;
    padding: 0.25rem 0.75rem;
    border-radius: 20px;
    font-size: 0.9rem;
}

.vibe-score.excellent {
    background: #d4edda;
    color: #155724;
}

.vibe-score.good {
    background: #fff3cd;
    color: #856404;
}

.vibe-score.poor {
    background: #f8d7da;
    color: #721c24;
}

.vibe-progress {
    margin-bottom: 1rem;
}

.progress-bar {
    width: 100%;
    height: 8px;
    background: #e9ecef;
    border-radius: 4px;
    overflow: hidden;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea, #764ba2);
    transition: width 0.3s ease;
}

.vibe-details {
    font-size: 0.9rem;
    color: #666;
    line-height: 1.5;
}

.issues-summary {
    display: grid;
    grid-template-columns: 300px 1fr;
    gap: 2rem;
}

.issues-list {
    max-height: 600px;
    overflow-y: auto;
}

.issue-item {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 1rem;
    margin-bottom: 1rem;
    border-left: 4px solid #6c757d;
}

.issue-item.severity-high {
    border-left-color: #dc3545;
}

.issue-item.severity-medium {
    border-left-color: #ffc107;
}

.issue-item.severity-low {
    border-left-color: #28a745;
}

.issue-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.5rem;
}

.severity-badge {
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    font-size: 0.8rem;
    font-weight: bold;
    text-transform: uppercase;
}

.severity-badge.high {
    background: #f8d7da;
    color: #721c24;
}

.severity-badge.medium {
    background: #fff3cd;
    color: #856404;
}

.severity-badge.low {
    background: #d4edda;
    color: #155724;
}

.issue-file {
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 0.9rem;
    color: #666;
}

.issue-message {
    margin-bottom: 0.5rem;
    line-height: 1.5;
}

.issue-fix {
    padding: 0.75rem;
    background: #e3f2fd;
    border-radius: 4px;
    border-left: 3px solid #2196f3;
    font-size: 0.9rem;
}

.security-overview {
    margin-bottom: 2rem;
}

.security-stats {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
}

.security-stat {
    flex: 1;
    text-align: center;
    padding: 1rem;
    border-radius: 8px;
    background: #f8f9fa;
}

.security-stat.critical {
    background: #f8d7da;
    color: #721c24;
}

.security-stat.high {
    background: #f8d7da;
    color: #721c24;
}

.security-stat.medium {
    background: #fff3cd;
    color: #856404;
}

.security-stat.low {
    background: #d4edda;
    color: #155724;
}

.stat-number {
    display: block;
    font-size: 2rem;
    font-weight: bold;
}

.stat-text {
    font-size: 0.9rem;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.file-controls {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
}

.file-controls input,
.file-controls select {
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.9rem;
}

.file-controls input {
    flex: 1;
}

.files-table-container {
    overflow-x: auto;
}

.files-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
}

.files-table th,
.files-table td {
    padding: 0.75rem;
    text-align: left;
    border-bottom: 1px solid #e9ecef;
}

.files-table th {
    background: #f8f9fa;
    font-weight: 600;
    color: #495057;
    position: sticky;
    top: 0;
}

.files-table tr:hover {
    background: #f8f9fa;
}

.trends-controls {
    display: flex;
    gap: 1rem;
    margin-bottom: 1rem;
}

.trends-controls select {
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 0.9rem;
}

.export-controls {
    position: fixed;
    bottom: 2rem;
    right: 2rem;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
}

.export-btn {
    padding: 0.75rem 1rem;
    background: #667eea;
    color: white;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: background 0.3s ease;
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
}

.export-btn:hover {
    background: #5a67d8;
    transform: translateY(-2px);
    box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
}

.footer {
    background: rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);
    border-top: 1px solid rgba(255, 255, 255, 0.2);
    padding: 2rem 0;
    margin-top: 4rem;
    text-align: center;
    color: white;
}

.footer p {
    margin-bottom: 0.5rem;
}

@media (max-width: 768px) {
    .dashboard {
        grid-template-columns: 1fr;
    }
    
    .tabs {
        flex-direction: column;
    }
    
    .issues-summary {
        grid-template-columns: 1fr;
    }
    
    .export-controls {
        position: static;
        flex-direction: row;
        justify-content: center;
        margin: 2rem 0;
    }
}

/* Loading animations */
@keyframes fadeIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.card,
.tab-content {
    animation: fadeIn 0.5s ease-out;
}

/* Responsive design */
@media (max-width: 1024px) {
    .vibes-grid {
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    }
}

@media (max-width: 640px) {
    .container {
        padding: 0 1rem;
    }
    
    .header {
        padding: 1rem 0;
    }
    
    .header h1 {
        font-size: 2rem;
    }
    
    .security-stats {
        flex-direction: column;
    }
    
    .file-controls {
        flex-direction: column;
    }
    
    .trends-controls {
        flex-direction: column;
    }
}
`
