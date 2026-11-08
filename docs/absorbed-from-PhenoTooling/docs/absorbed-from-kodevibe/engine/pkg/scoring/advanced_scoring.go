package scoring

import (
	"math"
	"sort"
	"time"

	"kodevibe/internal/models"
)

// AdvancedScoringEngine provides sophisticated scoring algorithms
type AdvancedScoringEngine struct {
	weights       map[string]float64
	thresholds    map[string]ScoreThreshold
	penalties     map[string]float64
	bonuses       map[string]float64
	trendAnalysis *TrendAnalysis
}

// ScoreThreshold defines scoring thresholds for different metrics
type ScoreThreshold struct {
	Excellent float64 // 90-100
	Good      float64 // 70-89
	Fair      float64 // 50-69
	Poor      float64 // Below 50
}

// TrendAnalysis tracks scoring trends over time
type TrendAnalysis struct {
	HistoricalScores []HistoricalScore
	TrendDirection   string  // "improving", "declining", "stable"
	TrendStrength    float64 // 0.0 to 1.0
	Momentum         float64 // Rate of change
}

// HistoricalScore represents a score at a specific point in time
type HistoricalScore struct {
	Timestamp time.Time
	Score     float64
	Vibe      string
	Context   map[string]interface{}
}

// ScoringMetrics contains detailed scoring information
type ScoringMetrics struct {
	BaseScore         float64
	WeightedScore     float64
	FinalScore        float64
	Grade             string
	Confidence        float64
	Breakdown         map[string]float64
	Penalties         map[string]float64
	Bonuses           map[string]float64
	TrendAdjustment   float64
	QualityIndicators map[string]float64
}

// NewAdvancedScoringEngine creates a new advanced scoring engine
func NewAdvancedScoringEngine() *AdvancedScoringEngine {
	return &AdvancedScoringEngine{
		weights: map[string]float64{
			"security":        0.25,
			"performance":     0.20,
			"readability":     0.15,
			"maintainability": 0.20,
			"testing":         0.10,
			"documentation":   0.05,
			"complexity":      0.05,
		},
		thresholds: map[string]ScoreThreshold{
			"security":        {Excellent: 95, Good: 80, Fair: 60, Poor: 40},
			"performance":     {Excellent: 90, Good: 75, Fair: 55, Poor: 35},
			"readability":     {Excellent: 85, Good: 70, Fair: 50, Poor: 30},
			"maintainability": {Excellent: 88, Good: 72, Fair: 52, Poor: 32},
			"testing":         {Excellent: 92, Good: 78, Fair: 58, Poor: 38},
			"documentation":   {Excellent: 80, Good: 65, Fair: 45, Poor: 25},
			"complexity":      {Excellent: 85, Good: 70, Fair: 50, Poor: 30},
		},
		penalties: map[string]float64{
			"high_severity_issues":     -15.0,
			"critical_vulnerabilities": -25.0,
			"poor_test_coverage":       -10.0,
			"high_complexity":          -8.0,
			"missing_documentation":    -5.0,
			"performance_bottlenecks":  -12.0,
		},
		bonuses: map[string]float64{
			"excellent_test_coverage": 5.0,
			"comprehensive_docs":      3.0,
			"clean_architecture":      4.0,
			"security_best_practices": 6.0,
			"performance_optimized":   4.0,
			"consistent_style":        2.0,
		},
		trendAnalysis: &TrendAnalysis{
			HistoricalScores: make([]HistoricalScore, 0),
		},
	}
}

// CalculateAdvancedScore computes a sophisticated score with multiple factors
func (e *AdvancedScoringEngine) CalculateAdvancedScore(result *models.AnalysisResult) *ScoringMetrics {
	metrics := &ScoringMetrics{
		Breakdown:         make(map[string]float64),
		Penalties:         make(map[string]float64),
		Bonuses:           make(map[string]float64),
		QualityIndicators: make(map[string]float64),
	}

	// Calculate base scores for each vibe
	vibeScores := e.calculateVibeScores(result.VibeResults)

	// Calculate weighted average
	weightedSum := 0.0
	totalWeight := 0.0

	for vibe, score := range vibeScores {
		weight := e.weights[vibe]
		weightedSum += score * weight
		totalWeight += weight
		metrics.Breakdown[vibe] = score
	}

	if totalWeight == 0 {
		metrics.BaseScore = 100.0
	} else {
		metrics.BaseScore = weightedSum / totalWeight
	}
	metrics.WeightedScore = metrics.BaseScore

	// Apply issue-based penalties
	e.applyIssuePenalties(result.Issues, metrics)

	// Apply quality bonuses
	e.applyQualityBonuses(result, metrics)

	// Apply trend adjustments
	e.applyTrendAdjustments(result, metrics)

	// Calculate confidence score
	metrics.Confidence = e.calculateConfidence(result, metrics)

	// Calculate final score
	metrics.FinalScore = math.Max(0, math.Min(100, metrics.WeightedScore))

	// Assign grade
	metrics.Grade = e.assignGrade(metrics.FinalScore)

	// Calculate quality indicators
	e.calculateQualityIndicators(result, metrics)

	// Update trend analysis
	e.updateTrendAnalysis(result, metrics.FinalScore)

	return metrics
}

// calculateVibeScores computes individual vibe scores with advanced algorithms
func (e *AdvancedScoringEngine) calculateVibeScores(vibeResults []models.VibeResult) map[string]float64 {
	scores := make(map[string]float64)

	for _, vibe := range vibeResults {
		threshold := e.thresholds[vibe.Name]

		// Apply non-linear scoring curve
		normalizedScore := e.applyScoreCurve(vibe.Score, threshold)
		scores[vibe.Name] = normalizedScore
	}

	return scores
}

// applyScoreCurve applies a non-linear scoring curve for more nuanced scoring
func (e *AdvancedScoringEngine) applyScoreCurve(rawScore float64, threshold ScoreThreshold) float64 {
	switch {
	case rawScore >= threshold.Excellent:
		// Excellent range: apply gentle boost
		excess := rawScore - threshold.Excellent
		boost := math.Log1p(excess) * 2
		return math.Min(100, rawScore+boost)

	case rawScore >= threshold.Good:
		// Good range: linear scaling
		return rawScore

	case rawScore >= threshold.Fair:
		// Fair range: apply mild penalty
		deficit := threshold.Good - rawScore
		penalty := math.Sqrt(deficit) * 0.5
		return math.Max(threshold.Fair, rawScore-penalty)

	default:
		// Poor range: apply steeper penalty
		deficit := threshold.Fair - rawScore
		penalty := math.Pow(deficit, 1.2) * 0.3
		return math.Max(0, rawScore-penalty)
	}
}

// applyIssuePenalties applies penalties based on issues found
func (e *AdvancedScoringEngine) applyIssuePenalties(issues []models.Issue, metrics *ScoringMetrics) {
	severityCounts := e.countIssuesBySeverity(issues)

	// High severity issues penalty
	if severityCounts["high"] > 0 {
		penalty := float64(severityCounts["high"]) * e.penalties["high_severity_issues"]
		metrics.Penalties["high_severity_issues"] = penalty
		metrics.WeightedScore += penalty
	}

	// Critical vulnerabilities penalty
	criticalSecurity := e.countCriticalSecurityIssues(issues)
	if criticalSecurity > 0 {
		penalty := float64(criticalSecurity) * e.penalties["critical_vulnerabilities"]
		metrics.Penalties["critical_vulnerabilities"] = penalty
		metrics.WeightedScore += penalty
	}

	// Complexity penalty
	complexityIssues := e.countComplexityIssues(issues)
	if complexityIssues > 5 {
		penalty := math.Log1p(float64(complexityIssues-5)) * e.penalties["high_complexity"]
		metrics.Penalties["high_complexity"] = penalty
		metrics.WeightedScore += penalty
	}
}

// applyQualityBonuses applies bonuses for exceptional quality indicators
func (e *AdvancedScoringEngine) applyQualityBonuses(result *models.AnalysisResult, metrics *ScoringMetrics) {
	// Test coverage bonus
	testCoverage := e.estimateTestCoverage(result)
	if testCoverage >= 80 {
		bonus := (testCoverage - 80) / 20 * e.bonuses["excellent_test_coverage"]
		metrics.Bonuses["excellent_test_coverage"] = bonus
		metrics.WeightedScore += bonus
	}

	// Documentation bonus
	docQuality := e.evaluateDocumentationQuality(result)
	if docQuality > 85 {
		bonus := (docQuality - 85) / 15 * e.bonuses["comprehensive_docs"]
		metrics.Bonuses["comprehensive_docs"] = bonus
		metrics.WeightedScore += bonus
	}

	// Clean architecture bonus
	architectureScore := e.evaluateArchitectureQuality(result)
	if architectureScore > 90 {
		bonus := e.bonuses["clean_architecture"]
		metrics.Bonuses["clean_architecture"] = bonus
		metrics.WeightedScore += bonus
	}

	// Security best practices bonus
	securityScore := e.getVibeScore(result.VibeResults, "security")
	if securityScore > 95 {
		bonus := e.bonuses["security_best_practices"]
		metrics.Bonuses["security_best_practices"] = bonus
		metrics.WeightedScore += bonus
	}
}

// applyTrendAdjustments applies adjustments based on historical trends
func (e *AdvancedScoringEngine) applyTrendAdjustments(result *models.AnalysisResult, metrics *ScoringMetrics) {
	if len(e.trendAnalysis.HistoricalScores) < 3 {
		metrics.TrendAdjustment = 0
		return
	}

	// Calculate trend direction and strength
	e.calculateTrendMetrics()

	// Apply trend-based adjustments
	switch e.trendAnalysis.TrendDirection {
	case "improving":
		// Reward consistent improvement
		adjustment := e.trendAnalysis.TrendStrength * e.trendAnalysis.Momentum * 2.0
		metrics.TrendAdjustment = math.Min(5, adjustment)

	case "declining":
		// Penalize decline, but less harshly if recent
		adjustment := e.trendAnalysis.TrendStrength * e.trendAnalysis.Momentum * -1.5
		metrics.TrendAdjustment = math.Max(-8, adjustment)

	default:
		// Stable trend - small positive adjustment for consistency
		metrics.TrendAdjustment = 0.5
	}

	metrics.WeightedScore += metrics.TrendAdjustment
}

// calculateConfidence estimates the confidence in the score
func (e *AdvancedScoringEngine) calculateConfidence(result *models.AnalysisResult, metrics *ScoringMetrics) float64 {
	factors := []float64{
		e.calculateDataQualityFactor(result),
		e.calculateCoverageFactor(result),
		e.calculateConsistencyFactor(metrics),
		e.calculateHistoryFactor(),
	}

	// Calculate weighted average of confidence factors
	totalConfidence := 0.0
	for _, factor := range factors {
		totalConfidence += factor
	}

	return totalConfidence / float64(len(factors))
}

// assignGrade assigns a letter grade based on the final score
func (e *AdvancedScoringEngine) assignGrade(score float64) string {
	switch {
	case score >= 95:
		return "A+"
	case score >= 90:
		return "A"
	case score >= 85:
		return "A-"
	case score >= 80:
		return "B+"
	case score >= 75:
		return "B"
	case score >= 70:
		return "B-"
	case score >= 65:
		return "C+"
	case score >= 60:
		return "C"
	case score >= 55:
		return "C-"
	case score >= 50:
		return "D+"
	case score >= 45:
		return "D"
	case score >= 40:
		return "D-"
	default:
		return "F"
	}
}

// calculateQualityIndicators computes various quality metrics
func (e *AdvancedScoringEngine) calculateQualityIndicators(result *models.AnalysisResult, metrics *ScoringMetrics) {
	metrics.QualityIndicators["maintainability_index"] = e.calculateMaintainabilityIndex(result)
	metrics.QualityIndicators["technical_debt_ratio"] = e.calculateTechnicalDebtRatio(result)
	metrics.QualityIndicators["code_health_score"] = e.calculateCodeHealthScore(result)
	metrics.QualityIndicators["security_posture"] = e.calculateSecurityPosture(result)
	metrics.QualityIndicators["performance_index"] = e.calculatePerformanceIndex(result)
}

// Helper methods for calculations

func (e *AdvancedScoringEngine) countIssuesBySeverity(issues []models.Issue) map[string]int {
	counts := make(map[string]int)
	for _, issue := range issues {
		counts[string(issue.Severity)]++
	}
	return counts
}

func (e *AdvancedScoringEngine) countCriticalSecurityIssues(issues []models.Issue) int {
	count := 0
	for _, issue := range issues {
		if issue.Type == models.VibeTypeSecurity && issue.Severity == models.SeverityCritical {
			count++
		}
	}
	return count
}

func (e *AdvancedScoringEngine) countComplexityIssues(issues []models.Issue) int {
	count := 0
	for _, issue := range issues {
		if issue.Type == models.VibeType("complexity") || issue.Category == "complexity" {
			count++
		}
	}
	return count
}

func (e *AdvancedScoringEngine) estimateTestCoverage(result *models.AnalysisResult) float64 {
	testingScore := e.getVibeScore(result.VibeResults, "testing")
	return testingScore * 0.8
}

func (e *AdvancedScoringEngine) evaluateDocumentationQuality(result *models.AnalysisResult) float64 {
	return e.getVibeScore(result.VibeResults, "documentation")
}

func (e *AdvancedScoringEngine) evaluateArchitectureQuality(result *models.AnalysisResult) float64 {
	maintainabilityScore := e.getVibeScore(result.VibeResults, "maintainability")
	complexityScore := e.getVibeScore(result.VibeResults, "complexity")
	return (maintainabilityScore + complexityScore) / 2
}

func (e *AdvancedScoringEngine) getVibeScore(vibeResults []models.VibeResult, vibeName string) float64 {
	for _, vibe := range vibeResults {
		if vibe.Name == vibeName {
			return vibe.Score
		}
	}
	return 0
}

func (e *AdvancedScoringEngine) calculateTrendMetrics() {
	if len(e.trendAnalysis.HistoricalScores) < 3 {
		return
	}

	// Sort by timestamp
	scores := make([]HistoricalScore, len(e.trendAnalysis.HistoricalScores))
	copy(scores, e.trendAnalysis.HistoricalScores)
	sort.Slice(scores, func(i, j int) bool {
		return scores[i].Timestamp.Before(scores[j].Timestamp)
	})

	// Calculate trend using linear regression
	n := float64(len(scores))
	var sumX, sumY, sumXY, sumX2 float64

	for i, score := range scores {
		x := float64(i)
		y := score.Score
		sumX += x
		sumY += y
		sumXY += x * y
		sumX2 += x * x
	}

	// Calculate slope (trend direction and strength)
	slope := (n*sumXY - sumX*sumY) / (n*sumX2 - sumX*sumX)

	e.trendAnalysis.TrendStrength = math.Abs(slope) / 10 // Normalize
	e.trendAnalysis.Momentum = slope

	if slope > 0.5 {
		e.trendAnalysis.TrendDirection = "improving"
	} else if slope < -0.5 {
		e.trendAnalysis.TrendDirection = "declining"
	} else {
		e.trendAnalysis.TrendDirection = "stable"
	}
}

func (e *AdvancedScoringEngine) calculateDataQualityFactor(result *models.AnalysisResult) float64 {
	// Higher confidence for more comprehensive analysis
	if result.FilesAnalyzed > 50 && result.LinesAnalyzed > 5000 {
		return 1.0
	} else if result.FilesAnalyzed > 10 && result.LinesAnalyzed > 1000 {
		return 0.8
	} else {
		return 0.6
	}
}

func (e *AdvancedScoringEngine) calculateCoverageFactor(result *models.AnalysisResult) float64 {
	// Confidence based on analysis coverage
	vibeCount := len(result.VibeResults)
	maxVibes := 7.0 // Total available vibes
	return float64(vibeCount) / maxVibes
}

func (e *AdvancedScoringEngine) calculateConsistencyFactor(metrics *ScoringMetrics) float64 {
	// Check consistency across vibe scores
	scores := make([]float64, 0, len(metrics.Breakdown))
	for _, score := range metrics.Breakdown {
		scores = append(scores, score)
	}

	if len(scores) < 2 {
		return 0.7
	}

	// Calculate standard deviation
	mean := 0.0
	for _, score := range scores {
		mean += score
	}
	mean /= float64(len(scores))

	variance := 0.0
	for _, score := range scores {
		variance += math.Pow(score-mean, 2)
	}
	variance /= float64(len(scores))
	stdDev := math.Sqrt(variance)

	// Lower standard deviation = higher consistency = higher confidence
	consistency := math.Max(0, 1.0-stdDev/50.0)
	return consistency
}

func (e *AdvancedScoringEngine) calculateHistoryFactor() float64 {
	// More historical data = higher confidence
	historyCount := len(e.trendAnalysis.HistoricalScores)
	if historyCount >= 10 {
		return 1.0
	} else if historyCount >= 5 {
		return 0.8
	} else if historyCount >= 2 {
		return 0.6
	} else {
		return 0.4
	}
}

// Advanced quality metrics

func (e *AdvancedScoringEngine) calculateMaintainabilityIndex(result *models.AnalysisResult) float64 {
	maintainability := e.getVibeScore(result.VibeResults, "maintainability")
	complexity := e.getVibeScore(result.VibeResults, "complexity")
	documentation := e.getVibeScore(result.VibeResults, "documentation")

	// Weighted combination
	return maintainability*0.5 + (100-complexity)*0.3 + documentation*0.2
}

func (e *AdvancedScoringEngine) calculateTechnicalDebtRatio(result *models.AnalysisResult) float64 {
	totalIssues := len(result.Issues)
	highSeverityIssues := e.countIssuesBySeverity(result.Issues)["high"]

	if totalIssues == 0 {
		return 0
	}

	// Higher ratio = more technical debt
	return float64(highSeverityIssues) / float64(totalIssues) * 100
}

func (e *AdvancedScoringEngine) calculateCodeHealthScore(result *models.AnalysisResult) float64 {
	totalScore := 0.0
	count := 0

	for _, vibe := range result.VibeResults {
		totalScore += vibe.Score
		count++
	}

	if count == 0 {
		return 0
	}

	baseHealth := totalScore / float64(count)

	// Adjust for issue density
	issueRatio := float64(len(result.Issues)) / float64(result.LinesAnalyzed) * 1000
	healthAdjustment := math.Max(0, 10-issueRatio) // Penalty for high issue density

	return math.Min(100, baseHealth+healthAdjustment)
}

func (e *AdvancedScoringEngine) calculateSecurityPosture(result *models.AnalysisResult) float64 {
	securityScore := e.getVibeScore(result.VibeResults, "security")
	securityIssues := e.countCriticalSecurityIssues(result.Issues)

	// Penalty for security issues
	penalty := float64(securityIssues) * 5
	return math.Max(0, securityScore-penalty)
}

func (e *AdvancedScoringEngine) calculatePerformanceIndex(result *models.AnalysisResult) float64 {
	performanceScore := e.getVibeScore(result.VibeResults, "performance")
	complexity := e.getVibeScore(result.VibeResults, "complexity")

	// Better performance with lower complexity
	return (performanceScore + (100 - complexity)) / 2
}

// updateTrendAnalysis adds the current score to historical data
func (e *AdvancedScoringEngine) updateTrendAnalysis(result *models.AnalysisResult, finalScore float64) {
	newScore := HistoricalScore{
		Timestamp: time.Now(),
		Score:     finalScore,
		Vibe:      "overall",
		Context: map[string]interface{}{
			"files_analyzed": result.FilesAnalyzed,
			"lines_analyzed": result.LinesAnalyzed,
			"issues_count":   len(result.Issues),
		},
	}

	e.trendAnalysis.HistoricalScores = append(e.trendAnalysis.HistoricalScores, newScore)

	// Keep only last 30 scores to manage memory
	if len(e.trendAnalysis.HistoricalScores) > 30 {
		e.trendAnalysis.HistoricalScores = e.trendAnalysis.HistoricalScores[1:]
	}
}

// GetGradeDescription returns a detailed description of the grade
func (e *AdvancedScoringEngine) GetGradeDescription(grade string) string {
	descriptions := map[string]string{
		"A+": "Exceptional code quality - industry-leading practices",
		"A":  "Excellent code quality - very well maintained",
		"A-": "Very good code quality - minor improvements possible",
		"B+": "Good code quality - some areas for improvement",
		"B":  "Satisfactory code quality - several improvements recommended",
		"B-": "Acceptable code quality - notable issues to address",
		"C+": "Below average code quality - significant improvements needed",
		"C":  "Poor code quality - major refactoring recommended",
		"C-": "Very poor code quality - extensive work required",
		"D+": "Critically poor code quality - immediate attention needed",
		"D":  "Severely compromised code quality - major overhaul required",
		"D-": "Extremely poor code quality - complete rewrite recommended",
		"F":  "Failed code quality standards - not production ready",
	}

	return descriptions[grade]
}
