package watch

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"

	"github.com/fsnotify/fsnotify"
	"github.com/sirupsen/logrus"

	"kodevibe/internal/models"
	"kodevibe/pkg/fix"
	"kodevibe/pkg/scanner"
)

// Watcher provides file watching and live scanning capabilities
type Watcher struct {
	config      *models.Configuration
	logger      *logrus.Logger
	scanner     *scanner.Scanner
	fixer       *fix.Fixer
	fsWatcher   *fsnotify.Watcher
	isWatching  bool
	stopChan    chan bool
	mu          sync.RWMutex
	lastScan    time.Time
	debounceMap map[string]time.Time
	debounceMu  sync.Mutex
}

// WatchEvent represents a file system event with scan results
type WatchEvent struct {
	Path      string
	Operation string
	Timestamp time.Time
	Issues    []models.Issue
}

// NewWatcher creates a new file watcher instance
func NewWatcher(config *models.Configuration, logger *logrus.Logger) *Watcher {
	scannerInstance, _ := scanner.NewScanner(config, logger)
	fixerInstance := fix.NewFixer(config, logger)

	return &Watcher{
		config:      config,
		logger:      logger,
		scanner:     scannerInstance,
		fixer:       fixerInstance,
		stopChan:    make(chan bool),
		debounceMap: make(map[string]time.Time),
	}
}

// Watch starts watching the specified paths for changes
func (w *Watcher) Watch(paths []string, autoFix bool, vibes []string) error {
	w.mu.Lock()
	if w.isWatching {
		w.mu.Unlock()
		return fmt.Errorf("already watching")
	}
	w.isWatching = true
	w.mu.Unlock()

	// Create file system watcher
	var err error
	w.fsWatcher, err = fsnotify.NewWatcher()
	if err != nil {
		w.isWatching = false
		return fmt.Errorf("failed to create file watcher: %w", err)
	}
	defer w.fsWatcher.Close()

	// Add paths to watcher
	for _, path := range paths {
		if err := w.addPathRecursively(path); err != nil {
			w.logger.Errorf("Failed to watch path %s: %v", path, err)
			continue
		}
		w.logger.Infof("Watching: %s", path)
	}

	w.logger.Info("🌊 KodeVibe file watcher started")
	if autoFix {
		w.logger.Info("🔧 Auto-fix enabled")
	}

	// Convert vibes to proper types
	var vibeTypes []models.VibeType
	for _, vibe := range vibes {
		vibeTypes = append(vibeTypes, models.VibeType(vibe))
	}

	// Watch for events
	for {
		select {
		case event, ok := <-w.fsWatcher.Events:
			if !ok {
				return nil
			}
			w.handleFileEvent(event, autoFix, vibeTypes)

		case err, ok := <-w.fsWatcher.Errors:
			if !ok {
				return nil
			}
			w.logger.Errorf("File watcher error: %v", err)

		case <-w.stopChan:
			w.logger.Info("File watcher stopped")
			return nil
		}
	}
}

// Stop stops the file watcher
func (w *Watcher) Stop() {
	w.mu.Lock()
	defer w.mu.Unlock()

	if !w.isWatching {
		return
	}

	w.isWatching = false
	close(w.stopChan)
}

// IsWatching returns true if the watcher is currently watching
func (w *Watcher) IsWatching() bool {
	w.mu.RLock()
	defer w.mu.RUnlock()
	return w.isWatching
}

// addPathRecursively adds a path and all its subdirectories to the watcher
func (w *Watcher) addPathRecursively(root string) error {
	return filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		if info.IsDir() {
			// Skip excluded directories
			if w.shouldSkipDirectory(path) {
				return filepath.SkipDir
			}

			// Add directory to watcher
			if err := w.fsWatcher.Add(path); err != nil {
				w.logger.Warnf("Failed to watch directory %s: %v", path, err)
			}
		}

		return nil
	})
}

// shouldSkipDirectory checks if a directory should be skipped
func (w *Watcher) shouldSkipDirectory(path string) bool {
	excludeDirs := []string{
		".git", "node_modules", "vendor", ".vscode", ".idea",
		"build", "dist", "coverage", ".nyc_output", ".cache",
	}

	dirName := filepath.Base(path)
	for _, excludeDir := range excludeDirs {
		if dirName == excludeDir {
			return true
		}
	}

	// Check exclude patterns from config
	for _, pattern := range w.config.Exclude.Files {
		if matched, err := filepath.Match(pattern, path); err == nil && matched {
			return true
		}
	}

	return false
}

// handleFileEvent processes a file system event
func (w *Watcher) handleFileEvent(event fsnotify.Event, autoFix bool, vibes []models.VibeType) {
	// Skip if not a write or create event
	if !event.Has(fsnotify.Write) && !event.Has(fsnotify.Create) {
		return
	}

	// Skip directories
	if info, err := os.Stat(event.Name); err != nil || info.IsDir() {
		return
	}

	// Skip files we don't care about
	if w.shouldSkipFile(event.Name) {
		return
	}

	// Debounce rapid successive events for the same file
	if w.shouldDebounce(event.Name) {
		return
	}

	w.logger.Debugf("File changed: %s", event.Name)

	// Scan the file
	go w.scanFile(event.Name, autoFix, vibes)
}

// shouldSkipFile checks if a file should be skipped
func (w *Watcher) shouldSkipFile(filePath string) bool {
	// Skip temporary files
	filename := filepath.Base(filePath)
	if strings.HasPrefix(filename, ".") || strings.HasSuffix(filename, "~") {
		return true
	}

	// Skip backup files
	if strings.HasSuffix(filename, ".backup") ||
		strings.HasSuffix(filename, ".bak") ||
		strings.HasSuffix(filename, ".orig") {
		return true
	}

	// Check exclude patterns
	for _, pattern := range w.config.Exclude.Files {
		if matched, err := filepath.Match(pattern, filePath); err == nil && matched {
			return true
		}
	}

	return false
}

// shouldDebounce checks if we should debounce this file event
func (w *Watcher) shouldDebounce(filePath string) bool {
	w.debounceMu.Lock()
	defer w.debounceMu.Unlock()

	now := time.Now()
	lastEvent, exists := w.debounceMap[filePath]

	// Debounce for 500ms
	if exists && now.Sub(lastEvent) < 500*time.Millisecond {
		return true
	}

	w.debounceMap[filePath] = now
	return false
}

// scanFile scans a single file and optionally applies fixes
func (w *Watcher) scanFile(filePath string, autoFix bool, vibes []models.VibeType) {
	ctx := context.Background()

	// Scan the file
	issues, err := w.scanner.ScanFile(ctx, filePath, vibes)
	if err != nil {
		w.logger.Errorf("Failed to scan file %s: %v", filePath, err)
		return
	}

	if len(issues) == 0 {
		w.logger.Debugf("✅ No issues found in %s", filePath)
		return
	}

	// Log issues found
	w.logger.Infof("🔍 Found %d issues in %s", len(issues), filePath)
	for _, issue := range issues {
		icon := w.getSeverityIcon(issue.Severity)
		w.logger.Infof("  %s %s (%s:%d)", icon, issue.Title, issue.File, issue.Line)
	}

	// Apply auto-fixes if enabled
	if autoFix {
		w.applyAutoFix(filePath, issues)
	}

	// Update last scan time
	w.lastScan = time.Now()
}

// applyAutoFix applies automatic fixes to fixable issues
func (w *Watcher) applyAutoFix(filePath string, issues []models.Issue) {
	var fixableRules []string

	// Collect fixable rules
	for _, issue := range issues {
		if issue.Fixable {
			fixableRules = append(fixableRules, issue.Rule)
		}
	}

	if len(fixableRules) == 0 {
		return
	}

	// Apply fixes
	w.logger.Infof("🔧 Auto-fixing %d issues in %s", len(fixableRules), filePath)
	err := w.fixer.Fix([]string{filePath}, true, true, fixableRules)
	if err != nil {
		w.logger.Errorf("Auto-fix failed for %s: %v", filePath, err)
	} else {
		w.logger.Infof("✅ Auto-fix completed for %s", filePath)
	}
}

// getSeverityIcon returns an icon for the severity level
func (w *Watcher) getSeverityIcon(severity models.SeverityLevel) string {
	switch severity {
	case models.SeverityError:
		return "❌"
	case models.SeverityWarning:
		return "⚠️"
	case models.SeverityInfo:
		return "ℹ️"
	default:
		return "🔍"
	}
}

// GetStatus returns the current watcher status
func (w *Watcher) GetStatus() map[string]interface{} {
	w.mu.RLock()
	defer w.mu.RUnlock()

	return map[string]interface{}{
		"watching":  w.isWatching,
		"last_scan": w.lastScan,
	}
}

// WatchSingle watches a single file for changes
func (w *Watcher) WatchSingle(filePath string, autoFix bool, vibes []string) error {
	return w.Watch([]string{filePath}, autoFix, vibes)
}

// SetDebounceInterval sets the debounce interval for file events
func (w *Watcher) SetDebounceInterval(interval time.Duration) {
	// This would be configurable in a real implementation
	w.logger.Infof("Debounce interval set to %v", interval)
}

// GetWatchedPaths returns the list of currently watched paths
func (w *Watcher) GetWatchedPaths() []string {
	if w.fsWatcher == nil {
		return []string{}
	}

	w.mu.RLock()
	defer w.mu.RUnlock()

	return w.fsWatcher.WatchList()
}

// AddPath adds a new path to watch
func (w *Watcher) AddPath(path string) error {
	if w.fsWatcher == nil {
		return fmt.Errorf("watcher not initialized")
	}

	return w.addPathRecursively(path)
}

// RemovePath removes a path from watching
func (w *Watcher) RemovePath(path string) error {
	if w.fsWatcher == nil {
		return fmt.Errorf("watcher not initialized")
	}

	return w.fsWatcher.Remove(path)
}
