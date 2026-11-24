package scanner

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/google/uuid"
	"github.com/sirupsen/logrus"
	"golang.org/x/sync/semaphore"

	"kodevibe/internal/models"
	"kodevibe/internal/utils"
	"kodevibe/pkg/vibes"
)

// Scanner represents the main scanning engine
type Scanner struct {
	config         *models.Configuration
	vibeRegistry   *vibes.Registry
	logger         *logrus.Logger
	cache          *utils.Cache
	metrics        *utils.Metrics
	maxConcurrency int
	timeout        time.Duration
	vibes          []string
}

// NewScanner creates a new scanner instance
func NewScanner(config *models.Configuration, logger *logrus.Logger) (*Scanner, error) {
	if config == nil {
		return nil, fmt.Errorf("configuration is required")
	}

	if logger == nil {
		logger = logrus.New()
	}

	// Initialize vibe registry
	registry := vibes.NewRegistry()
	if err := registry.RegisterAllVibes(config); err != nil {
		return nil, fmt.Errorf("failed to register vibes: %w", err)
	}

	// Initialize cache if enabled
	var cache *utils.Cache
	if config.Advanced.CacheEnabled {
		cache = utils.NewCache(config.Advanced.CacheTTL)
	}

	// Initialize metrics
	metrics := utils.NewMetrics()

	return &Scanner{
		config:         config,
		vibeRegistry:   registry,
		logger:         logger,
		cache:          cache,
		metrics:        metrics,
		maxConcurrency: config.Scanner.MaxConcurrency,
		timeout:        time.Duration(config.Scanner.Timeout) * time.Second,
		vibes:          config.Scanner.EnabledVibes,
	}, nil
}

// Scan performs a comprehensive scan of the specified paths
func (s *Scanner) Scan(ctx context.Context, request *models.ScanRequest) (*models.ScanResult, error) {
	if request == nil {
		return nil, fmt.Errorf("scan request is required")
	}

	startTime := time.Now()
	scanID := request.ID
	if scanID == "" {
		scanID = uuid.New().String()
	}

	s.logger.WithFields(logrus.Fields{
		"scan_id": scanID,
		"paths":   request.Paths,
		"vibes":   request.Vibes,
	}).Info("Starting scan")

	// Initialize scan result
	result := &models.ScanResult{
		ScanID:        scanID,
		ID:            scanID,
		StartTime:     startTime,
		ProjectPath:   strings.Join(request.Paths, ","),
		Configuration: s.config,
		Issues:        []models.Issue{},
		Metadata:      make(map[string]interface{}),
	}

	// Discover files to scan
	files, err := s.discoverFiles(request.Paths, request.StagedOnly, request.DiffTarget)
	if err != nil {
		return nil, fmt.Errorf("failed to discover files: %w", err)
	}

	// Filter files based on exclusion patterns
	filteredFiles := s.filterFiles(files)
	result.FilesScanned = len(filteredFiles)
	result.FilesSkipped = len(files) - len(filteredFiles)

	s.logger.WithFields(logrus.Fields{
		"total_files":    len(files),
		"filtered_files": len(filteredFiles),
		"skipped_files":  result.FilesSkipped,
	}).Info("File discovery completed")

	// Determine which vibes to run
	var vibeTypes []models.VibeType
	for _, v := range request.Vibes {
		vibeTypes = append(vibeTypes, models.VibeType(v))
	}
	vibesToRun := s.getVibesToRun(vibeTypes)

	// Run vibe checks concurrently
	issues, err := s.runVibeChecks(ctx, filteredFiles, vibesToRun)
	if err != nil {
		return nil, fmt.Errorf("failed to run vibe checks: %w", err)
	}

	// Set results
	result.Issues = issues
	result.EndTime = time.Now()
	result.Duration = result.EndTime.Sub(result.StartTime)

	// Generate summary
	result.Summary = s.generateSummary(issues)

	s.logger.WithFields(logrus.Fields{
		"scan_id":      scanID,
		"duration":     result.Duration,
		"total_issues": len(issues),
		"errors":       result.Summary.ErrorIssues,
		"warnings":     result.Summary.WarningIssues,
		"info":         result.Summary.InfoIssues,
	}).Info("Scan completed")

	// Update metrics
	s.metrics.RecordScan(result)

	return result, nil
}

// discoverFiles discovers all files to be scanned
func (s *Scanner) discoverFiles(paths []string, stagedOnly bool, diffTarget string) ([]string, error) {
	var allFiles []string

	for _, path := range paths {
		files, err := s.discoverFilesInPath(path, stagedOnly, diffTarget)
		if err != nil {
			s.logger.WithFields(logrus.Fields{
				"path":  path,
				"error": err.Error(),
			}).Warn("Failed to discover files in path, skipping")
			continue
		}
		allFiles = append(allFiles, files...)
	}

	// Remove duplicates
	fileSet := make(map[string]bool)
	var uniqueFiles []string
	for _, file := range allFiles {
		if !fileSet[file] {
			fileSet[file] = true
			uniqueFiles = append(uniqueFiles, file)
		}
	}

	return uniqueFiles, nil
}

// discoverFilesInPath discovers files in a specific path
func (s *Scanner) discoverFilesInPath(path string, stagedOnly bool, diffTarget string) ([]string, error) {
	var files []string

	// Handle git-specific file discovery
	if stagedOnly || diffTarget != "" {
		return s.discoverGitFiles(path, stagedOnly, diffTarget)
	}

	// Walk the directory tree
	err := filepath.Walk(path, func(filePath string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// Skip directories
		if info.IsDir() {
			return nil
		}

		// Skip hidden files and directories
		if strings.HasPrefix(info.Name(), ".") {
			return nil
		}

		// Check if file should be ignored based on patterns
		if s.shouldIgnore(filePath) {
			return nil
		}

		// Add file to list
		files = append(files, filePath)
		return nil
	})

	if err != nil {
		return nil, fmt.Errorf("failed to walk directory: %w", err)
	}

	return files, nil
}

// discoverGitFiles discovers git-specific files (staged or diff)
func (s *Scanner) discoverGitFiles(path string, stagedOnly bool, diffTarget string) ([]string, error) {
	gitUtil := utils.NewGitUtil(path)

	if stagedOnly {
		return gitUtil.GetStagedFiles()
	}

	if diffTarget != "" {
		return gitUtil.GetDiffFiles(diffTarget)
	}

	return nil, fmt.Errorf("invalid git file discovery parameters")
}

// filterFiles filters files based on exclusion patterns
func (s *Scanner) filterFiles(files []string) []string {
	var filteredFiles []string

	for _, file := range files {
		if !s.shouldExcludeFile(file) {
			filteredFiles = append(filteredFiles, file)
		}
	}

	return filteredFiles
}

// shouldExcludeFile checks if a file should be excluded based on configuration
func (s *Scanner) shouldExcludeFile(file string) bool {
	// Check file patterns
	for _, pattern := range s.config.Exclude.Files {
		if matched, err := filepath.Match(pattern, file); err == nil && matched {
			return true
		}

		// Check with glob patterns
		if strings.Contains(pattern, "**") {
			// Simplified glob matching
			if s.matchGlob(file, pattern) {
				return true
			}
		}
	}

	// Check filename patterns
	filename := filepath.Base(file)
	for _, pattern := range s.config.Exclude.Patterns {
		if matched, err := filepath.Match(pattern, filename); err == nil && matched {
			return true
		}
	}

	// Check directory paths
	for _, pattern := range s.config.Exclude.Paths {
		if strings.Contains(file, pattern) {
			return true
		}
	}

	return false
}

// matchGlob provides basic glob pattern matching
func (s *Scanner) matchGlob(file, pattern string) bool {
	// Simple implementation - in production, use a proper glob library
	if strings.Contains(pattern, "**") {
		parts := strings.Split(pattern, "**")
		if len(parts) == 2 {
			prefix := parts[0]
			suffix := parts[1]
			return strings.HasPrefix(file, prefix) && strings.HasSuffix(file, suffix)
		}
	}
	return false
}

// getVibesToRun determines which vibes should be executed
func (s *Scanner) getVibesToRun(requestedVibes []models.VibeType) []models.VibeType {
	if len(requestedVibes) > 0 {
		return requestedVibes
	}

	// Return all enabled vibes from configuration
	var enabledVibes []models.VibeType
	for vibeType, vibeConfig := range s.config.Vibes {
		if vibeConfig.Enabled {
			enabledVibes = append(enabledVibes, vibeType)
		}
	}

	return enabledVibes
}

// runVibeChecks executes all vibe checks concurrently
func (s *Scanner) runVibeChecks(ctx context.Context, files []string, vibesToRun []models.VibeType) ([]models.Issue, error) {
	var allIssues []models.Issue
	var mu sync.Mutex

	// Create semaphore for concurrency control
	sem := semaphore.NewWeighted(int64(s.maxConcurrency))

	// Create error group for concurrent execution
	var wg sync.WaitGroup
	errChan := make(chan error, len(vibesToRun))

	// Run each vibe check
	for _, vibeType := range vibesToRun {
		wg.Add(1)
		go func(vType models.VibeType) {
			defer wg.Done()

			// Acquire semaphore
			if err := sem.Acquire(ctx, 1); err != nil {
				errChan <- fmt.Errorf("failed to acquire semaphore: %w", err)
				return
			}
			defer sem.Release(1)

			// Get vibe checker
			checker, err := s.vibeRegistry.GetChecker(vType)
			if err != nil {
				errChan <- fmt.Errorf("failed to get checker for vibe %s: %w", vType, err)
				return
			}

			// Run vibe check
			issues, err := s.runSingleVibeCheck(ctx, checker, files, vType)
			if err != nil {
				errChan <- fmt.Errorf("failed to run vibe check %s: %w", vType, err)
				return
			}

			// Add issues to result
			mu.Lock()
			allIssues = append(allIssues, issues...)
			mu.Unlock()

			s.logger.WithFields(logrus.Fields{
				"vibe":   vType,
				"issues": len(issues),
				"files":  len(files),
			}).Debug("Vibe check completed")
		}(vibeType)
	}
	// Wait for all checks to complete
	wg.Wait()
	close(errChan)

	// Check for errors
	for err := range errChan {
		if err != nil {
			return nil, err
		}
	}

	return allIssues, nil
}

// runSingleVibeCheck executes a single vibe check
func (s *Scanner) runSingleVibeCheck(ctx context.Context, checker vibes.Checker, files []string, vibeType models.VibeType) ([]models.Issue, error) {
	var issues []models.Issue

	// Check if we can use cache
	if s.cache != nil {
		cacheKey := s.generateCacheKey(files, vibeType)
		if cachedIssues, found := s.cache.Get(cacheKey); found {
			if cachedIssuesList, ok := cachedIssues.([]models.Issue); ok {
				s.logger.WithField("vibe", vibeType).Debug("Using cached results")
				return cachedIssuesList, nil
			}
		}
	}

	// Execute the check
	startTime := time.Now()
	vibeIssues, err := checker.Check(ctx, files)
	if err != nil {
		return nil, fmt.Errorf("vibe check failed: %w", err)
	}

	// Add vibe type to all issues
	for i := range vibeIssues {
		vibeIssues[i].Type = vibeType
		vibeIssues[i].ID = uuid.New().String()
		vibeIssues[i].CreatedAt = time.Now()
	}

	issues = append(issues, vibeIssues...)

	// Cache results if cache is enabled
	if s.cache != nil {
		cacheKey := s.generateCacheKey(files, vibeType)
		s.cache.Set(cacheKey, issues)
	}

	// Record metrics
	s.metrics.RecordVibeCheck(vibeType, time.Since(startTime), len(issues))

	return issues, nil
}

// generateCacheKey generates a cache key for vibe check results
func (s *Scanner) generateCacheKey(files []string, vibeType models.VibeType) string {
	// Create a hash of file paths and modification times
	var keyParts []string
	keyParts = append(keyParts, string(vibeType))

	for _, file := range files {
		info, err := os.Stat(file)
		if err == nil {
			keyParts = append(keyParts, fmt.Sprintf("%s:%d", file, info.ModTime().Unix()))
		}
	}

	return utils.HashStrings(keyParts)
}

// generateSummary generates a summary of scan results
func (s *Scanner) generateSummary(issues []models.Issue) models.ScanSummary {
	summary := models.ScanSummary{
		TotalIssues:      len(issues),
		IssuesByType:     make(map[models.VibeType]int),
		IssuesBySeverity: make(map[models.SeverityLevel]int),
		TopIssues:        make([]string, 0),
	}

	// Count issues by type and severity
	for _, issue := range issues {
		summary.IssuesByType[issue.Type]++
		summary.IssuesBySeverity[issue.Severity]++

		switch issue.Severity {
		case models.SeverityCritical:
			summary.CriticalIssues++
		case models.SeverityError:
			summary.ErrorIssues++
		case models.SeverityWarning:
			summary.WarningIssues++
		case models.SeverityInfo:
			summary.InfoIssues++
		}
	}

	// Calculate score (higher is better)
	totalPossibleScore := 100.0
	criticalPenalty := float64(summary.CriticalIssues) * 25.0
	errorPenalty := float64(summary.ErrorIssues) * 10.0
	warningPenalty := float64(summary.WarningIssues) * 5.0
	infoPenalty := float64(summary.InfoIssues) * 1.0

	summary.Score = totalPossibleScore - criticalPenalty - errorPenalty - warningPenalty - infoPenalty
	if summary.Score < 0 {
		summary.Score = 0
	}

	// Determine grade
	switch {
	case summary.Score >= 90:
		summary.Grade = "A"
	case summary.Score >= 80:
		summary.Grade = "B"
	case summary.Score >= 70:
		summary.Grade = "C"
	case summary.Score >= 60:
		summary.Grade = "D"
	default:
		summary.Grade = "F"
	}

	// Generate top issues
	ruleCount := make(map[string]int)
	for _, issue := range issues {
		ruleCount[issue.Rule]++
	}

	// Sort rules by frequency (simplified)
	for rule, count := range ruleCount {
		if count > 1 {
			summary.TopIssues = append(summary.TopIssues, fmt.Sprintf("%s (%d occurrences)", rule, count))
		}
	}

	return summary
}

// GetMetrics returns scanner metrics
func (s *Scanner) GetMetrics() *utils.Metrics {
	return s.metrics
}

// ClearCache clears the scanner cache
func (s *Scanner) ClearCache() {
	if s.cache != nil {
		s.cache.Clear()
	}
}

// ScanFile scans a single file
func (s *Scanner) ScanFile(ctx context.Context, filePath string, vibes []models.VibeType) ([]models.Issue, error) {
	// Convert VibeType slice to string slice
	vibeStrings := make([]string, len(vibes))
	for i, vibe := range vibes {
		vibeStrings[i] = string(vibe)
	}

	request := &models.ScanRequest{
		ID:    uuid.New().String(),
		Paths: []string{filePath},
		Vibes: vibeStrings,
	}

	result, err := s.Scan(ctx, request)
	if err != nil {
		return nil, err
	}

	return result.Issues, nil
}

// ScanString scans a string content
func (s *Scanner) ScanString(ctx context.Context, content string, filename string, vibes []models.VibeType) ([]models.Issue, error) {
	// Create temporary file
	tempFile, err := utils.CreateTempFile(content, filename)
	if err != nil {
		return nil, fmt.Errorf("failed to create temp file: %w", err)
	}
	defer os.Remove(tempFile)

	return s.ScanFile(ctx, tempFile, vibes)
}

// ValidateConfiguration validates the scanner configuration
func (s *Scanner) ValidateConfiguration() error {
	if s.config == nil {
		return fmt.Errorf("configuration is nil")
	}

	// Validate that at least one vibe is enabled
	hasEnabledVibe := false
	for _, vibeConfig := range s.config.Vibes {
		if vibeConfig.Enabled {
			hasEnabledVibe = true
			break
		}
	}

	if !hasEnabledVibe {
		return fmt.Errorf("no vibes are enabled")
	}

	// Validate concurrency settings
	if s.config.Advanced.MaxConcurrency <= 0 {
		return fmt.Errorf("max concurrency must be positive")
	}

	if s.config.Advanced.Timeout <= 0 {
		return fmt.Errorf("timeout must be positive")
	}

	return nil
}

// shouldIgnore checks if a file should be ignored based on patterns
func (s *Scanner) shouldIgnore(path string) bool {
	for _, pattern := range s.config.Scanner.ExcludePatterns {
		// Check filename pattern (e.g., "*.txt")
		if matched, _ := filepath.Match(pattern, filepath.Base(path)); matched {
			return true
		}

		// Handle directory patterns like "node_modules/*", ".git/*"
		if strings.HasSuffix(pattern, "/*") {
			dirPattern := strings.TrimSuffix(pattern, "/*")
			if strings.Contains(path, dirPattern+"/") || strings.HasPrefix(path, dirPattern+"/") {
				return true
			}
		}

		// Check full path pattern
		if matched, _ := filepath.Match(pattern, path); matched {
			return true
		}
	}
	return false
}
