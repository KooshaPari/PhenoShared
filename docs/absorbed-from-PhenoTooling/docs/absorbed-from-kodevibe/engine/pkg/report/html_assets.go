package report

// JavaScript code for interactive functionality
const jsScript = `
// Global variables
let currentSort = 'score';
let currentFilter = '';
let charts = {};

// Initialize the report when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initializeReport();
    initializeCharts();
    populateSecurityIssues();
    populateFilesTable();
    updateSecurityStats();
    setupEventListeners();
});

// Initialize report functionality
function initializeReport() {
    // Set score circle CSS variable
    const scoreCircle = document.querySelector('.score-circle');
    if (scoreCircle) {
        scoreCircle.style.setProperty('--score', window.reportData.overallScore);
    }
    
    // Update score circle color based on score
    updateScoreCircleColor();
}

// Update score circle color based on score value
function updateScoreCircleColor() {
    const scoreCircle = document.querySelector('.score-circle');
    const score = window.reportData.overallScore;
    
    let color = '#4CAF50'; // Green for excellent
    if (score < 90) color = '#2196F3'; // Blue for very good
    if (score < 80) color = '#FF9800'; // Orange for good
    if (score < 70) color = '#F44336'; // Red for fair/poor
    
    scoreCircle.style.background = 'conic-gradient(from 0deg, ' + color + ' 0deg, ' + color + ' calc(' + score + ' * 3.6deg), #e0e0e0 calc(' + score + ' * 3.6deg), #e0e0e0 360deg)';
}

// Initialize all charts
function initializeCharts() {
    initializeVibesChart();
    initializeSeverityChart();
    initializeTrendsChart();
}

// Initialize vibes breakdown chart
function initializeVibesChart() {
    const ctx = document.getElementById('vibesChart');
    if (!ctx) return;
    
    const vibeData = window.reportData.vibeResults;
    
    charts.vibesChart = new Chart(ctx, {
        type: 'radar',
        data: {
            labels: vibeData.map(v => v.name.charAt(0).toUpperCase() + v.name.slice(1)),
            datasets: [{
                label: 'Score',
                data: vibeData.map(v => v.score),
                backgroundColor: 'rgba(102, 126, 234, 0.2)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 2,
                pointBackgroundColor: 'rgba(102, 126, 234, 1)',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: 'rgba(102, 126, 234, 1)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                r: {
                    angleLines: {
                        display: true
                    },
                    suggestedMin: 0,
                    suggestedMax: 100,
                    ticks: {
                        stepSize: 20
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

// Initialize severity breakdown chart
function initializeSeverityChart() {
    const ctx = document.getElementById('severityChart');
    if (!ctx) return;
    
    const issues = window.reportData.issues;
    const severityCounts = {
        high: issues.filter(i => i.severity === 'high').length,
        medium: issues.filter(i => i.severity === 'medium').length,
        low: issues.filter(i => i.severity === 'low').length
    };
    
    charts.severityChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['High', 'Medium', 'Low'],
            datasets: [{
                data: [severityCounts.high, severityCounts.medium, severityCounts.low],
                backgroundColor: ['#F44336', '#FF9800', '#4CAF50'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Initialize trends chart
function initializeTrendsChart() {
    const ctx = document.getElementById('trendsChart');
    if (!ctx) return;
    
    const historyData = window.reportData.scoreHistory;
    
    // Group data by vibe
    const vibeGroups = {};
    historyData.forEach(point => {
        if (!vibeGroups[point.vibe]) {
            vibeGroups[point.vibe] = [];
        }
        vibeGroups[point.vibe].push(point);
    });
    
    const datasets = Object.keys(vibeGroups).map((vibe, index) => {
        const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe'];
        return {
            label: vibe.charAt(0).toUpperCase() + vibe.slice(1),
            data: vibeGroups[vibe].map(p => ({
                x: p.timestamp,
                y: p.score
            })),
            borderColor: colors[index % colors.length],
            backgroundColor: colors[index % colors.length] + '20',
            tension: 0.4
        };
    });
    
    charts.trendsChart = new Chart(ctx, {
        type: 'line',
        data: {
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'time',
                    time: {
                        unit: 'day'
                    }
                },
                y: {
                    suggestedMin: 0,
                    suggestedMax: 100
                }
            },
            plugins: {
                legend: {
                    position: 'top'
                }
            }
        }
    });
}

// Populate security issues section
function populateSecurityIssues() {
    const container = document.getElementById('securityIssues');
    if (!container) return;
    
    const securityIssues = window.reportData.securityIssues || [];
    
    if (securityIssues.length === 0) {
        container.innerHTML = '<p class="no-issues">🎉 No security issues found!</p>';
        return;
    }
    
    container.innerHTML = securityIssues.map(issue => '
        <div class="security-issue severity-' + issue.severity + '">
            <div class="issue-header">
                <span class="severity-badge ' + issue.severity + '">' + issue.severity.toUpperCase() + '</span>
                <span class="issue-category">' + issue.category + '</span>
                ' + (issue.cwe ? '<span class="cwe-badge">' + issue.cwe + '</span>' : '') + '
            </div>
            <div class="issue-location">' + issue.file + ':' + issue.line + '</div>
            <div class="issue-description">' + issue.description + '</div>
            <div class="issue-remediation">
                <strong>Remediation:</strong> ' + issue.remediation + '
            </div>
        </div>
    ').join('');
}

// Populate files table
function populateFilesTable() {
    const tbody = document.getElementById('filesTableBody');
    if (!tbody) return;
    
    const files = window.reportData.fileMetrics || [];
    
    tbody.innerHTML = files.map(file => '
        <tr>
            <td class="file-path" title="' + file.path + '">' + truncatePath(file.path) + '</td>
            <td class="score-cell">
                <div class="score-bar">
                    <div class="score-fill" style="width: ' + file.score + '%"></div>
                    <span class="score-text">' + file.score.toFixed(1) + '</span>
                </div>
            </td>
            <td class="issues-cell ' + getIssuesSeverity(file.issues) + '">' + file.issues + '</td>
            <td>' + file.lines.toLocaleString() + '</td>
            <td class="complexity-cell ' + getComplexitySeverity(file.complexity) + '">' + file.complexity + '</td>
            <td>' + file.coverage.toFixed(1) + '%</td>
            <td>' + formatDate(file.lastModified) + '</td>
        </tr>
    ').join('');
}

// Update security statistics
function updateSecurityStats() {
    const securityIssues = window.reportData.securityIssues || [];
    const severityCounts = {
        critical: securityIssues.filter(i => i.severity === 'critical').length,
        high: securityIssues.filter(i => i.severity === 'high').length,
        medium: securityIssues.filter(i => i.severity === 'medium').length,
        low: securityIssues.filter(i => i.severity === 'low').length
    };
    
    Object.keys(severityCounts).forEach(severity => {
        const element = document.getElementById(severity + 'Count');
        if (element) {
            element.textContent = severityCounts[severity];
        }
    });
}

// Setup event listeners
function setupEventListeners() {
    // Tab switching
    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', function() {
            const tabName = this.getAttribute('onclick').match(/showTab\('(.+)'\)/)[1];
            showTab(tabName);
        });
    });
    
    // Trends controls
    const timeframeSelect = document.getElementById('trendsTimeframe');
    const vibeSelect = document.getElementById('trendsVibe');
    
    if (timeframeSelect) {
        timeframeSelect.addEventListener('change', updateTrendsChart);
    }
    
    if (vibeSelect) {
        vibeSelect.addEventListener('change', updateTrendsChart);
    }
}

// Tab switching functionality
function showTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active class from all buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab
    const selectedTab = document.getElementById(tabName);
    if (selectedTab) {
        selectedTab.classList.add('active');
    }
    
    // Activate corresponding button
    const activeButton = document.querySelector('[onclick="showTab(\'' + tabName + '\')"]');
    if (activeButton) {
        activeButton.classList.add('active');
    }
    
    // Refresh charts when switching to chart tabs
    setTimeout(() => {
        if (charts.vibesChart && tabName === 'overview') {
            charts.vibesChart.resize();
        }
        if (charts.severityChart && tabName === 'issues') {
            charts.severityChart.resize();
        }
        if (charts.trendsChart && tabName === 'trends') {
            charts.trendsChart.resize();
        }
    }, 100);
}

// Filter files functionality
function filterFiles() {
    const filter = document.getElementById('fileSearch').value.toLowerCase();
    currentFilter = filter;
    
    const rows = document.querySelectorAll('#filesTableBody tr');
    rows.forEach(row => {
        const filePath = row.querySelector('.file-path').textContent.toLowerCase();
        row.style.display = filePath.includes(filter) ? '' : 'none';
    });
}

// Sort files functionality
function sortFiles() {
    const sortBy = document.getElementById('sortFiles').value;
    currentSort = sortBy;
    
    const tbody = document.getElementById('filesTableBody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    rows.sort((a, b) => {
        let aVal, bVal;
        
        switch (sortBy) {
            case 'score':
                aVal = parseFloat(a.querySelector('.score-text').textContent);
                bVal = parseFloat(b.querySelector('.score-text').textContent);
                return bVal - aVal; // Descending
            case 'issues':
                aVal = parseInt(a.querySelector('.issues-cell').textContent);
                bVal = parseInt(b.querySelector('.issues-cell').textContent);
                return bVal - aVal; // Descending
            case 'lines':
                aVal = parseInt(a.cells[3].textContent.replace(/,/g, ''));
                bVal = parseInt(b.cells[3].textContent.replace(/,/g, ''));
                return bVal - aVal; // Descending
            case 'complexity':
                aVal = parseInt(a.querySelector('.complexity-cell').textContent);
                bVal = parseInt(b.querySelector('.complexity-cell').textContent);
                return bVal - aVal; // Descending
            default:
                return 0;
        }
    });
    
    // Reorder rows
    rows.forEach(row => tbody.appendChild(row));
}

// Update trends chart based on controls
function updateTrendsChart() {
    if (!charts.trendsChart) return;
    
    const timeframe = parseInt(document.getElementById('trendsTimeframe').value);
    const selectedVibe = document.getElementById('trendsVibe').value;
    
    let filteredData = window.reportData.scoreHistory;
    
    // Filter by timeframe
    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - timeframe);
    filteredData = filteredData.filter(point => new Date(point.timestamp) >= cutoffDate);
    
    // Filter by vibe
    if (selectedVibe !== 'all') {
        filteredData = filteredData.filter(point => point.vibe === selectedVibe);
    }
    
    // Group by vibe
    const vibeGroups = {};
    filteredData.forEach(point => {
        if (!vibeGroups[point.vibe]) {
            vibeGroups[point.vibe] = [];
        }
        vibeGroups[point.vibe].push(point);
    });
    
    // Update chart data
    const colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe', '#00f2fe'];
    const datasets = Object.keys(vibeGroups).map((vibe, index) => ({
        label: vibe.charAt(0).toUpperCase() + vibe.slice(1),
        data: vibeGroups[vibe].map(p => ({
            x: p.timestamp,
            y: p.score
        })),
        borderColor: colors[index % colors.length],
        backgroundColor: colors[index % colors.length] + '20',
        tension: 0.4
    }));
    
    charts.trendsChart.data.datasets = datasets;
    charts.trendsChart.update();
}

// Export functionality
function exportPDF() {
    window.print();
}

function exportJSON() {
    const dataStr = JSON.stringify(window.reportData, null, 2);
    const dataBlob = new Blob([dataStr], {type: 'application/json'});
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = window.reportData.projectName + '_analysis.json';
    link.click();
    
    URL.revokeObjectURL(url);
}

function exportCSV() {
    const issues = window.reportData.issues;
    const csvHeader = 'File,Line,Severity,Category,Message\\n';
    const csvData = issues.map(issue => 
        '"' + issue.file + '",' + 
        issue.line + ',' + 
        issue.severity + ',' + 
        (issue.category || 'general') + ',' + 
        '"' + issue.message.replace(/"/g, '""') + '"'
    ).join('\\n');
    
    const dataBlob = new Blob([csvHeader + csvData], {type: 'text/csv'});
    const url = URL.createObjectURL(dataBlob);
    
    const link = document.createElement('a');
    link.href = url;
    link.download = window.reportData.projectName + '_issues.csv';
    link.click();
    
    URL.revokeObjectURL(url);
}

function shareReport() {
    if (navigator.share) {
        navigator.share({
            title: 'KodeVibe Analysis Report - ' + window.reportData.projectName,
            text: 'Code quality analysis report generated by KodeVibe',
            url: window.location.href
        });
    } else {
        // Fallback: copy URL to clipboard
        navigator.clipboard.writeText(window.location.href).then(() => {
            alert('Report URL copied to clipboard!');
        });
    }
}

// Utility functions
function truncatePath(path, maxLength = 40) {
    if (path.length <= maxLength) return path;
    return '...' + path.slice(-(maxLength - 3));
}

function getIssuesSeverity(count) {
    if (count === 0) return 'no-issues';
    if (count <= 2) return 'low-issues';
    if (count <= 5) return 'medium-issues';
    return 'high-issues';
}

function getComplexitySeverity(complexity) {
    if (complexity <= 5) return 'low-complexity';
    if (complexity <= 10) return 'medium-complexity';
    return 'high-complexity';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString();
}
`

// Simplified Chart.js bundle for basic chart functionality
const chartJSBundle = `
// Simplified Chart.js implementation for KodeVibe reports
(function() {
    'use strict';
    
    class Chart {
        constructor(ctx, config) {
            this.ctx = typeof ctx === 'string' ? document.getElementById(ctx) : ctx;
            this.config = config;
            this.data = config.data;
            this.options = config.options || {};
            
            this.init();
        }
        
        init() {
            this.ctx.width = this.ctx.clientWidth;
            this.ctx.height = this.ctx.clientHeight;
            this.draw();
        }
        
        draw() {
            const context = this.ctx.getContext('2d');
            context.clearRect(0, 0, this.ctx.width, this.ctx.height);
            
            switch (this.config.type) {
                case 'radar':
                    this.drawRadar(context);
                    break;
                case 'doughnut':
                    this.drawDoughnut(context);
                    break;
                case 'line':
                    this.drawLine(context);
                    break;
            }
        }
        
        drawRadar(ctx) {
            const center = { x: this.ctx.width / 2, y: this.ctx.height / 2 };
            const radius = Math.min(this.ctx.width, this.ctx.height) / 2 - 40;
            const labels = this.data.labels;
            const dataset = this.data.datasets[0];
            
            // Draw grid
            ctx.strokeStyle = '#e0e0e0';
            ctx.lineWidth = 1;
            
            for (let i = 1; i <= 5; i++) {
                ctx.beginPath();
                ctx.arc(center.x, center.y, (radius / 5) * i, 0, 2 * Math.PI);
                ctx.stroke();
            }
            
            // Draw axes
            labels.forEach((label, index) => {
                const angle = (index * 2 * Math.PI) / labels.length - Math.PI / 2;
                const x = center.x + Math.cos(angle) * radius;
                const y = center.y + Math.sin(angle) * radius;
                
                ctx.beginPath();
                ctx.moveTo(center.x, center.y);
                ctx.lineTo(x, y);
                ctx.stroke();
                
                // Draw label
                ctx.fillStyle = '#666';
                ctx.font = '12px Arial';
                ctx.textAlign = 'center';
                ctx.fillText(label, x + Math.cos(angle) * 20, y + Math.sin(angle) * 20);
            });
            
            // Draw data
            ctx.strokeStyle = dataset.borderColor;
            ctx.fillStyle = dataset.backgroundColor;
            ctx.lineWidth = 2;
            
            ctx.beginPath();
            dataset.data.forEach((value, index) => {
                const angle = (index * 2 * Math.PI) / dataset.data.length - Math.PI / 2;
                const distance = (value / 100) * radius;
                const x = center.x + Math.cos(angle) * distance;
                const y = center.y + Math.sin(angle) * distance;
                
                if (index === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });
            ctx.closePath();
            ctx.fill();
            ctx.stroke();
        }
        
        drawDoughnut(ctx) {
            const center = { x: this.ctx.width / 2, y: this.ctx.height / 2 };
            const radius = Math.min(this.ctx.width, this.ctx.height) / 2 - 40;
            const innerRadius = radius * 0.6;
            
            const dataset = this.data.datasets[0];
            const total = dataset.data.reduce((sum, value) => sum + value, 0);
            
            let currentAngle = -Math.PI / 2;
            
            dataset.data.forEach((value, index) => {
                const sliceAngle = (value / total) * 2 * Math.PI;
                
                ctx.fillStyle = dataset.backgroundColor[index];
                ctx.beginPath();
                ctx.arc(center.x, center.y, radius, currentAngle, currentAngle + sliceAngle);
                ctx.arc(center.x, center.y, innerRadius, currentAngle + sliceAngle, currentAngle, true);
                ctx.closePath();
                ctx.fill();
                
                currentAngle += sliceAngle;
            });
            
            // Draw legend
            const legendY = this.ctx.height - 40;
            this.data.labels.forEach((label, index) => {
                const x = 20 + index * 80;
                
                ctx.fillStyle = dataset.backgroundColor[index];
                ctx.fillRect(x, legendY, 12, 12);
                
                ctx.fillStyle = '#666';
                ctx.font = '12px Arial';
                ctx.fillText(label, x + 16, legendY + 10);
            });
        }
        
        drawLine(ctx) {
            const padding = 40;
            const chartArea = {
                left: padding,
                right: this.ctx.width - padding,
                top: padding,
                bottom: this.ctx.height - padding
            };
            
            // Simple line chart implementation
            ctx.strokeStyle = '#e0e0e0';
            ctx.lineWidth = 1;
            
            // Draw grid
            for (let i = 0; i <= 5; i++) {
                const y = chartArea.top + (i * (chartArea.bottom - chartArea.top)) / 5;
                ctx.beginPath();
                ctx.moveTo(chartArea.left, y);
                ctx.lineTo(chartArea.right, y);
                ctx.stroke();
            }
            
            // Draw data
            this.data.datasets.forEach(dataset => {
                ctx.strokeStyle = dataset.borderColor;
                ctx.lineWidth = 2;
                ctx.beginPath();
                
                dataset.data.forEach((point, index) => {
                    const x = chartArea.left + (index * (chartArea.right - chartArea.left)) / (dataset.data.length - 1);
                    const y = chartArea.bottom - ((point.y / 100) * (chartArea.bottom - chartArea.top));
                    
                    if (index === 0) {
                        ctx.moveTo(x, y);
                    } else {
                        ctx.lineTo(x, y);
                    }
                });
                
                ctx.stroke();
            });
        }
        
        resize() {
            this.ctx.width = this.ctx.clientWidth;
            this.ctx.height = this.ctx.clientHeight;
            this.draw();
        }
        
        update() {
            this.draw();
        }
    }
    
    // Export Chart to global scope
    window.Chart = Chart;
})();
`
