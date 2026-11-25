package scoring

import (
	"testing"
	"time"

	"kodevibe/internal/models"

	"github.com/stretchr/testify/assert"
)

func TestNewAdvancedScoringEngine(t *testing.T) {
	engine := NewAdvancedScoringEngine()

	assert.NotNil(t, engine)
	assert.NotNil(t, engine.weights)
	assert.NotNil(t, engine.thresholds)
	assert.NotNil(t, engine.penalties)
	assert.NotNil(t, engine.bonuses)
	assert.NotNil(t, engine.trendAnalysis)

	// Verify default weights sum to approximately 1.0
	totalWeight := 0.0
	for _, weight := range engine.weights {
		totalWeight += weight
	}
	assert.InDelta(t, 1.0, totalWeight, 0.01) // Allow small floating point variance
}

func TestAdvancedScoringEngine_CalculateAdvancedScore(t *testing.T) {
	tests := []struct {
		name          string
		result        *models.AnalysisResult
		expectedGrade string
		expectedRange [2]float64 // min, max expected score
	}{
		{
			name: "excellent code quality",
			result: &models.AnalysisResult{
				OverallScore:  95.0,
				FilesAnalyzed: 50,
				LinesAnalyzed: 5000,
				Duration:      2 * time.Second,
				VibeResults: []models.VibeResult{
					{Name: "security", Score: 98.0},
					{Name: "performance", Score: 94.0},
					{Name: "readability", Score: 96.0},
					{Name: "maintainability", Score: 95.0},
					{Name: "testing", Score: 97.0},
					{Name: "documentation", Score: 90.0},
					{Name: "complexity", Score: 93.0},
				},
				Issues: []models.Issue{
					{Severity: "low", Category: "style", File: "test.go", Line: 1, Message: "Minor style issue"},
				},
			},
			expectedGrade: "A+",
			expectedRange: [2]float64{90.0, 100.0},
		},
		{
			name: "good code quality",
			result: &models.AnalysisResult{
				OverallScore:  80.0,
				FilesAnalyzed: 30,
				LinesAnalyzed: 3000,
				Duration:      3 * time.Second,
				VibeResults: []models.VibeResult{
					{Name: "security", Score: 85.0},
					{Name: "performance", Score: 78.0},
					{Name: "readability", Score: 82.0},
					{Name: "maintainability", Score: 80.0},
					{Name: "testing", Score: 75.0},
					{Name: "documentation", Score: 70.0},
					{Name: "complexity", Score: 85.0},
				},
				Issues: []models.Issue{
					{Severity: "medium", Category: "performance", File: "test.go", Line: 10, Message: "Performance issue"},
					{Severity: "low", Category: "style", File: "main.go", Line: 20, Message: "Style issue"},
				},
			},
			expectedGrade: "B+",
			expectedRange: [2]float64{75.0, 85.0},
		},
		{
			name: "poor code quality with security issues",
			result: &models.AnalysisResult{
				OverallScore:  45.0,
				FilesAnalyzed: 10,
				LinesAnalyzed: 1000,
				Duration:      5 * time.Second,
				VibeResults: []models.VibeResult{
					{Name: "security", Score: 30.0},
					{Name: "performance", Score: 50.0},
					{Name: "readability", Score: 45.0},
					{Name: "maintainability", Score: 40.0},
					{Name: "testing", Score: 35.0},
					{Name: "documentation", Score: 25.0},
					{Name: "complexity", Score: 60.0},
				},
				Issues: []models.Issue{
					{Severity: "high", Category: "security", File: "auth.go", Line: 15, Message: "SQL injection vulnerability"},
					{Severity: "high", Category: "security", File: "auth.go", Line: 25, Message: "XSS vulnerability"},
					{Severity: "medium", Category: "performance", File: "utils.go", Line: 30, Message: "Inefficient algorithm"},
				},
			},
			expectedGrade: "F",
			expectedRange: [2]float64{0.0, 10.0},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			engine := NewAdvancedScoringEngine()
			metrics := engine.CalculateAdvancedScore(tt.result)

			assert.NotNil(t, metrics)
			assert.Equal(t, tt.expectedGrade, metrics.Grade)
			assert.GreaterOrEqual(t, metrics.FinalScore, tt.expectedRange[0])
			assert.LessOrEqual(t, metrics.FinalScore, tt.expectedRange[1])
			assert.GreaterOrEqual(t, metrics.Confidence, 0.0)
			assert.LessOrEqual(t, metrics.Confidence, 1.0)

			// Verify breakdown contains all vibes
			for _, vibe := range tt.result.VibeResults {
				assert.Contains(t, metrics.Breakdown, vibe.Name)
			}
		})
	}
}

func TestAdvancedScoringEngine_ApplyScoreCurve(t *testing.T) {
	engine := NewAdvancedScoringEngine()
	threshold := ScoreThreshold{
		Excellent: 90.0,
		Good:      70.0,
		Fair:      50.0,
		Poor:      30.0,
	}

	tests := []struct {
		name        string
		rawScore    float64
		expectBoost bool // Whether score should be boosted or penalized
	}{
		{
			name:        "excellent score gets boost",
			rawScore:    95.0,
			expectBoost: true,
		},
		{
			name:        "good score unchanged",
			rawScore:    75.0,
			expectBoost: false,
		},
		{
			name:        "fair score gets mild penalty",
			rawScore:    55.0,
			expectBoost: false,
		},
		{
			name:        "poor score gets steep penalty",
			rawScore:    25.0,
			expectBoost: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			adjustedScore := engine.applyScoreCurve(tt.rawScore, threshold)

			if tt.expectBoost {
				assert.GreaterOrEqual(t, adjustedScore, tt.rawScore)
			} else if tt.rawScore >= threshold.Good {
				// Good range should be unchanged
				assert.Equal(t, tt.rawScore, adjustedScore)
			} else {
				// Fair and poor ranges may be penalized
				assert.LessOrEqual(t, adjustedScore, tt.rawScore)
			}

			// Score should always be within valid range
			assert.GreaterOrEqual(t, adjustedScore, 0.0)
			assert.LessOrEqual(t, adjustedScore, 100.0)
		})
	}
}

func TestAdvancedScoringEngine_IssuePenalties(t *testing.T) {
	engine := NewAdvancedScoringEngine()

	tests := []struct {
		name            string
		issues          []models.Issue
		expectedPenalty bool
	}{
		{
			name:            "no issues",
			issues:          []models.Issue{},
			expectedPenalty: false,
		},
		{
			name: "high severity issues",
			issues: []models.Issue{
				{Severity: "high", Category: "security", File: "test.go", Line: 1, Message: "Critical issue"},
				{Severity: "high", Category: "performance", File: "test.go", Line: 2, Message: "Performance issue"},
			},
			expectedPenalty: true,
		},
		{
			name: "critical security vulnerabilities",
			issues: []models.Issue{
				{Severity: "high", Category: "security", File: "auth.go", Line: 10, Message: "SQL injection"},
				{Severity: "high", Category: "security", File: "auth.go", Line: 20, Message: "XSS vulnerability"},
			},
			expectedPenalty: true,
		},
		{
			name:            "many complexity issues",
			issues:          make([]models.Issue, 10),
			expectedPenalty: true,
		},
	}

	// Initialize complexity issues for the many-complexity test
	for i := range tests[3].issues {
		tests[3].issues[i] = models.Issue{
			Severity: "medium",
			Type:     models.VibeType("complexity"),
			Category: "complexity",
			File:     "complex.go",
			Line:     i + 1,
			Message:  "High complexity",
		}
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			metrics := &ScoringMetrics{
				WeightedScore: 80.0,
				Penalties:     make(map[string]float64),
			}

			initialScore := metrics.WeightedScore
			engine.applyIssuePenalties(tt.issues, metrics)

			if tt.expectedPenalty {
				assert.Less(t, metrics.WeightedScore, initialScore)
				assert.NotEmpty(t, metrics.Penalties)
			} else {
				assert.Equal(t, initialScore, metrics.WeightedScore)
				assert.Empty(t, metrics.Penalties)
			}
		})
	}
}

func TestAdvancedScoringEngine_QualityBonuses(t *testing.T) {
	engine := NewAdvancedScoringEngine()

	tests := []struct {
		name          string
		result        *models.AnalysisResult
		expectedBonus bool
	}{
		{
			name: "excellent test coverage",
			result: &models.AnalysisResult{
				VibeResults: []models.VibeResult{
					{Name: "testing", Score: 100.0},
				},
			},
			expectedBonus: true,
		},
		{
			name: "comprehensive documentation",
			result: &models.AnalysisResult{
				VibeResults: []models.VibeResult{
					{Name: "documentation", Score: 90.0},
				},
			},
			expectedBonus: true,
		},
		{
			name: "excellent security practices",
			result: &models.AnalysisResult{
				VibeResults: []models.VibeResult{
					{Name: "security", Score: 98.0},
				},
			},
			expectedBonus: true,
		},
		{
			name: "average quality - no bonus",
			result: &models.AnalysisResult{
				VibeResults: []models.VibeResult{
					{Name: "testing", Score: 70.0},
					{Name: "documentation", Score: 70.0},
					{Name: "security", Score: 70.0},
				},
			},
			expectedBonus: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			metrics := &ScoringMetrics{
				WeightedScore: 80.0,
				Bonuses:       make(map[string]float64),
			}

			initialScore := metrics.WeightedScore
			engine.applyQualityBonuses(tt.result, metrics)

			if tt.expectedBonus {
				assert.GreaterOrEqual(t, metrics.WeightedScore, initialScore)
				assert.NotEmpty(t, metrics.Bonuses)
			} else {
				assert.Equal(t, initialScore, metrics.WeightedScore)
				assert.Empty(t, metrics.Bonuses)
			}
		})
	}
}

func TestAdvancedScoringEngine_TrendAnalysis(t *testing.T) {
	engine := NewAdvancedScoringEngine()

	// Add historical scores to simulate trend
	baseTime := time.Now().Add(-10 * 24 * time.Hour)
	for i := 0; i < 5; i++ {
		score := HistoricalScore{
			Timestamp: baseTime.Add(time.Duration(i) * 24 * time.Hour),
			Score:     70.0 + float64(i)*5.0, // Improving trend
			Vibe:      "overall",
		}
		engine.trendAnalysis.HistoricalScores = append(engine.trendAnalysis.HistoricalScores, score)
	}

	engine.calculateTrendMetrics()

	assert.Equal(t, "improving", engine.trendAnalysis.TrendDirection)
	assert.Greater(t, engine.trendAnalysis.TrendStrength, 0.0)
	assert.Greater(t, engine.trendAnalysis.Momentum, 0.0)
}

func TestAdvancedScoringEngine_ConfidenceCalculation(t *testing.T) {
	engine := NewAdvancedScoringEngine()

	tests := []struct {
		name               string
		result             *models.AnalysisResult
		expectedConfidence float64 // approximate
	}{
		{
			name: "high confidence - large dataset",
			result: &models.AnalysisResult{
				FilesAnalyzed: 100,
				LinesAnalyzed: 10000,
				VibeResults: []models.VibeResult{
					{Name: "security", Score: 85.0},
					{Name: "performance", Score: 80.0},
					{Name: "readability", Score: 82.0},
					{Name: "maintainability", Score: 83.0},
					{Name: "testing", Score: 81.0},
					{Name: "documentation", Score: 84.0},
					{Name: "complexity", Score: 79.0},
				},
			},
			expectedConfidence: 0.8,
		},
		{
			name: "medium confidence - small dataset",
			result: &models.AnalysisResult{
				FilesAnalyzed: 5,
				LinesAnalyzed: 500,
				VibeResults: []models.VibeResult{
					{Name: "security", Score: 80.0},
					{Name: "performance", Score: 75.0},
				},
			},
			expectedConfidence: 0.5,
		},
		{
			name: "low confidence - very small dataset",
			result: &models.AnalysisResult{
				FilesAnalyzed: 1,
				LinesAnalyzed: 50,
				VibeResults: []models.VibeResult{
					{Name: "security", Score: 90.0},
				},
			},
			expectedConfidence: 0.3,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			metrics := &ScoringMetrics{
				Breakdown: make(map[string]float64),
			}

			// Populate breakdown for consistency calculation
			for _, vibe := range tt.result.VibeResults {
				metrics.Breakdown[vibe.Name] = vibe.Score
			}

			confidence := engine.calculateConfidence(tt.result, metrics)

			assert.GreaterOrEqual(t, confidence, 0.0)
			assert.LessOrEqual(t, confidence, 1.0)
			assert.InDelta(t, tt.expectedConfidence, confidence, 0.3) // Allow reasonable variance
		})
	}
}

func TestAdvancedScoringEngine_GradeAssignment(t *testing.T) {
	engine := NewAdvancedScoringEngine()

	tests := []struct {
		score float64
		grade string
	}{
		{98.0, "A+"},
		{92.0, "A"},
		{87.0, "A-"},
		{82.0, "B+"},
		{77.0, "B"},
		{72.0, "B-"},
		{67.0, "C+"},
		{62.0, "C"},
		{57.0, "C-"},
		{52.0, "D+"},
		{47.0, "D"},
		{42.0, "D-"},
		{30.0, "F"},
	}

	for _, tt := range tests {
		t.Run(tt.grade, func(t *testing.T) {
			grade := engine.assignGrade(tt.score)
			assert.Equal(t, tt.grade, grade)
		})
	}
}

func TestAdvancedScoringEngine_QualityIndicators(t *testing.T) {
	engine := NewAdvancedScoringEngine()

	result := &models.AnalysisResult{
		VibeResults: []models.VibeResult{
			{Name: "security", Score: 85.0},
			{Name: "performance", Score: 80.0},
			{Name: "maintainability", Score: 75.0},
			{Name: "complexity", Score: 70.0},
			{Name: "documentation", Score: 65.0},
		},
		Issues: []models.Issue{
			{Severity: "high", Category: "security", File: "test.go", Line: 1, Message: "Issue 1"},
			{Severity: "medium", Category: "performance", File: "test.go", Line: 2, Message: "Issue 2"},
		},
		LinesAnalyzed: 1000,
	}

	metrics := &ScoringMetrics{
		QualityIndicators: make(map[string]float64),
	}

	engine.calculateQualityIndicators(result, metrics)

	// Verify all expected indicators are present
	expectedIndicators := []string{
		"maintainability_index",
		"technical_debt_ratio",
		"code_health_score",
		"security_posture",
		"performance_index",
	}

	for _, indicator := range expectedIndicators {
		assert.Contains(t, metrics.QualityIndicators, indicator)
		assert.GreaterOrEqual(t, metrics.QualityIndicators[indicator], 0.0)
	}
}

func TestAdvancedScoringEngine_GetGradeDescription(t *testing.T) {
	engine := NewAdvancedScoringEngine()

	tests := []string{"A+", "A", "B", "C", "D", "F"}

	for _, grade := range tests {
		t.Run(grade, func(t *testing.T) {
			description := engine.GetGradeDescription(grade)
			assert.NotEmpty(t, description)
			assert.Contains(t, description, "code quality")
		})
	}
}

// Benchmark tests
func BenchmarkAdvancedScoringEngine_CalculateAdvancedScore(b *testing.B) {
	engine := NewAdvancedScoringEngine()

	result := &models.AnalysisResult{
		OverallScore:  80.0,
		FilesAnalyzed: 100,
		LinesAnalyzed: 10000,
		VibeResults: []models.VibeResult{
			{Name: "security", Score: 85.0},
			{Name: "performance", Score: 78.0},
			{Name: "readability", Score: 82.0},
			{Name: "maintainability", Score: 80.0},
			{Name: "testing", Score: 75.0},
			{Name: "documentation", Score: 70.0},
			{Name: "complexity", Score: 85.0},
		},
		Issues: make([]models.Issue, 50),
	}

	// Initialize issues
	for i := range result.Issues {
		result.Issues[i] = models.Issue{
			Severity: "medium",
			Category: "general",
			File:     "test.go",
			Line:     i + 1,
			Message:  "Test issue",
		}
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		engine.CalculateAdvancedScore(result)
	}
}

func BenchmarkAdvancedScoringEngine_TrendAnalysis(b *testing.B) {
	engine := NewAdvancedScoringEngine()

	// Add historical data
	baseTime := time.Now().Add(-30 * 24 * time.Hour)
	for i := 0; i < 30; i++ {
		score := HistoricalScore{
			Timestamp: baseTime.Add(time.Duration(i) * 24 * time.Hour),
			Score:     70.0 + float64(i%10),
			Vibe:      "overall",
		}
		engine.trendAnalysis.HistoricalScores = append(engine.trendAnalysis.HistoricalScores, score)
	}

	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		engine.calculateTrendMetrics()
	}
}

// Test edge cases and error conditions
func TestAdvancedScoringEngine_EdgeCases(t *testing.T) {
	engine := NewAdvancedScoringEngine()

	t.Run("empty analysis result", func(t *testing.T) {
		result := &models.AnalysisResult{
			VibeResults: []models.VibeResult{},
			Issues:      []models.Issue{},
		}

		metrics := engine.CalculateAdvancedScore(result)
		assert.NotNil(t, metrics)
		assert.GreaterOrEqual(t, metrics.FinalScore, 0.0)
		assert.LessOrEqual(t, metrics.FinalScore, 100.0)
	})

	t.Run("extremely high issue count", func(t *testing.T) {
		issues := make([]models.Issue, 1000)
		for i := range issues {
			issues[i] = models.Issue{
				Severity: "high",
				Category: "security",
				File:     "test.go",
				Line:     i + 1,
				Message:  "Critical issue",
			}
		}

		result := &models.AnalysisResult{
			VibeResults: []models.VibeResult{
				{Name: "security", Score: 10.0},
			},
			Issues: issues,
		}

		metrics := engine.CalculateAdvancedScore(result)
		assert.NotNil(t, metrics)
		assert.GreaterOrEqual(t, metrics.FinalScore, 0.0) // Should not go negative
	})

	t.Run("perfect scores", func(t *testing.T) {
		result := &models.AnalysisResult{
			OverallScore: 100.0,
			VibeResults: []models.VibeResult{
				{Name: "security", Score: 100.0},
				{Name: "performance", Score: 100.0},
				{Name: "readability", Score: 100.0},
				{Name: "maintainability", Score: 100.0},
				{Name: "testing", Score: 100.0},
				{Name: "documentation", Score: 100.0},
				{Name: "complexity", Score: 100.0},
			},
			Issues: []models.Issue{}, // No issues
		}

		metrics := engine.CalculateAdvancedScore(result)
		assert.NotNil(t, metrics)
		assert.Equal(t, "A+", metrics.Grade)
		assert.GreaterOrEqual(t, metrics.FinalScore, 95.0)
	})
}
