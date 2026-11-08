package utils

import (
	"crypto/sha256"
	"fmt"
	"os"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"

	"kodevibe/internal/models"

	"github.com/patrickmn/go-cache"
)

// Cache wraps go-cache for consistent interface
type Cache struct {
	cache *cache.Cache
}

// NewCache creates a new cache instance
func NewCache(ttl time.Duration) *Cache {
	return &Cache{
		cache: cache.New(ttl, ttl*2),
	}
}

func (c *Cache) Get(key string) (interface{}, bool) { return c.cache.Get(key) }
func (c *Cache) Set(key string, value interface{})  { c.cache.Set(key, value, cache.DefaultExpiration) }
func (c *Cache) Clear()                             { c.cache.Flush() }

// Metrics collects performance metrics
type Metrics struct {
	mu           sync.RWMutex
	scanCount    int64
	scanDuration time.Duration
	vibeMetrics  map[models.VibeType]VibeMetric
}

type VibeMetric struct {
	Count    int64
	Duration time.Duration
	Issues   int64
}

func NewMetrics() *Metrics {
	return &Metrics{
		vibeMetrics: make(map[models.VibeType]VibeMetric),
	}
}

func (m *Metrics) RecordScan(result *models.ScanResult) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.scanCount++
	m.scanDuration += result.Duration
}

func (m *Metrics) RecordVibeCheck(vibeType models.VibeType, duration time.Duration, issues int) {
	m.mu.Lock()
	defer m.mu.Unlock()
	metric := m.vibeMetrics[vibeType]
	metric.Count++
	metric.Duration += duration
	metric.Issues += int64(issues)
	m.vibeMetrics[vibeType] = metric
}

// GitUtil provides git operations
type GitUtil struct {
	repoPath string
}

func NewGitUtil(repoPath string) *GitUtil {
	return &GitUtil{repoPath: repoPath}
}

func (g *GitUtil) GetStagedFiles() ([]string, error) {
	// Would use go-git library in real implementation
	return []string{}, nil
}

func (g *GitUtil) GetDiffFiles(target string) ([]string, error) {
	// Would use go-git library in real implementation
	return []string{}, nil
}

// Utility functions
func TruncateString(s string, maxLen int) string {
	if maxLen <= 0 {
		return ""
	}
	if len(s) <= maxLen {
		return s
	}
	return s[:maxLen]
}

func HashStrings(strs []string) string {
	hasher := sha256.New()
	for _, s := range strs {
		hasher.Write([]byte(s))
	}
	return fmt.Sprintf("%x", hasher.Sum(nil))[:16]
}

func CreateTempFile(content, filename string) (string, error) {
	tempFile, err := os.CreateTemp("", filename)
	if err != nil {
		return "", err
	}
	defer tempFile.Close()

	_, err = tempFile.WriteString(content)
	if err != nil {
		return "", err
	}

	return tempFile.Name(), nil
}

func ParseSize(sizeStr string) (int64, error) {
	sizeStr = strings.ToUpper(strings.TrimSpace(sizeStr))

	// Extract number and unit
	re := regexp.MustCompile(`^(\d+(?:\.\d+)?)\s*([KMGT]?B?)$`)
	matches := re.FindStringSubmatch(sizeStr)
	if len(matches) != 3 {
		return 0, fmt.Errorf("invalid size format: %s", sizeStr)
	}

	size, err := strconv.ParseFloat(matches[1], 64)
	if err != nil {
		return 0, err
	}

	unit := matches[2]
	switch unit {
	case "", "B":
		return int64(size), nil
	case "KB", "K":
		return int64(size * 1024), nil
	case "MB", "M":
		return int64(size * 1024 * 1024), nil
	case "GB", "G":
		return int64(size * 1024 * 1024 * 1024), nil
	case "TB", "T":
		return int64(size * 1024 * 1024 * 1024 * 1024), nil
	default:
		return 0, fmt.Errorf("unknown size unit: %s", unit)
	}
}

func FormatSize(size int64) string {
	if size < 1024 {
		return fmt.Sprintf("%d B", size)
	}
	if size < 1024*1024 {
		return fmt.Sprintf("%.1f KB", float64(size)/1024)
	}
	if size < 1024*1024*1024 {
		return fmt.Sprintf("%.1f MB", float64(size)/(1024*1024))
	}
	return fmt.Sprintf("%.1f GB", float64(size)/(1024*1024*1024))
}

// ContainsString checks if a string slice contains a given string
func ContainsString(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}

// UniqueStrings returns a new slice with unique strings only
func UniqueStrings(slice []string) []string {
	keys := make(map[string]bool)
	var result []string

	for _, item := range slice {
		if !keys[item] {
			keys[item] = true
			result = append(result, item)
		}
	}
	return result
}

// EnsureDir creates a directory if it doesn't exist
func EnsureDir(path string) error {
	return os.MkdirAll(path, 0755)
}

// FileExists checks if a file exists and is not a directory
func FileExists(path string) bool {
	info, err := os.Stat(path)
	if os.IsNotExist(err) {
		return false
	}
	return !info.IsDir()
}

// IsGitRepo checks if a directory is a Git repository
func IsGitRepo(path string) bool {
	gitDir := filepath.Join(path, ".git")
	_, err := os.Stat(gitDir)
	return err == nil
}

// GetRelativePath returns the relative path from base to target
func GetRelativePath(base, target string) string {
	// Clean the paths
	base = filepath.Clean(base)
	target = filepath.Clean(target)

	// If target doesn't start with base, return absolute path
	if !strings.HasPrefix(target, base) {
		return target
	}

	// Remove base from target
	relative, err := filepath.Rel(base, target)
	if err != nil {
		return target
	}

	return relative
}

// SanitizeFileName sanitizes a filename by replacing invalid characters
func SanitizeFileName(filename string) string {
	// Replace invalid characters with underscores
	invalidChars := regexp.MustCompile(`[<>:"/\\|?*\s]+`)
	sanitized := invalidChars.ReplaceAllString(filename, "_")

	// Replace quotes and other special characters
	sanitized = strings.ReplaceAll(sanitized, `"`, "_")
	sanitized = strings.ReplaceAll(sanitized, `'`, "_")

	return sanitized
}

// Hash generates a SHA256 hash of a string
func Hash(input string) string {
	hasher := sha256.New()
	hasher.Write([]byte(input))
	return fmt.Sprintf("%x", hasher.Sum(nil))
}

// FormatBytes formats bytes into human readable format
func FormatBytes(bytes int64) string {
	const unit = 1024
	if bytes < unit {
		return fmt.Sprintf("%d B", bytes)
	}
	div, exp := int64(unit), 0
	for n := bytes / unit; n >= unit; n /= unit {
		div *= unit
		exp++
	}
	return fmt.Sprintf("%.1f %cB", float64(bytes)/float64(div), "KMGTPE"[exp])
}

// FormatDuration formats milliseconds into human readable duration
func FormatDuration(ms int64) string {
	if ms < 1000 {
		return fmt.Sprintf("%dms", ms)
	}

	seconds := float64(ms) / 1000
	if seconds < 60 {
		return fmt.Sprintf("%.1fs", seconds)
	}

	minutes := int(seconds / 60)
	remainingSeconds := int(seconds) % 60

	if minutes < 60 {
		return fmt.Sprintf("%dm%ds", minutes, remainingSeconds)
	}

	hours := minutes / 60
	remainingMinutes := minutes % 60
	return fmt.Sprintf("%dh%dm%ds", hours, remainingMinutes, remainingSeconds)
}

// NormalizePattern normalizes a file pattern by removing leading ./
func NormalizePattern(pattern string) string {
	if strings.HasPrefix(pattern, "./") {
		return pattern[2:]
	}
	return pattern
}

// CalculateScore calculates a quality score based on issue counts
func CalculateScore(total, critical, errors, warnings int) float64 {
	if total == 0 {
		return 100.0
	}

	// Penalty system: critical=30, error=5, warning=1 per issue
	penalty := float64(critical*30 + errors*5 + warnings*1)
	score := 100.0 - penalty

	if score < 0 {
		score = 0
	}

	return score
}

// GetGrade converts a score to a letter grade
func GetGrade(score float64) string {
	switch {
	case score >= 97:
		return "A+"
	case score >= 90:
		return "A"
	case score >= 80:
		return "B"
	case score >= 70:
		return "C"
	case score >= 60:
		return "D"
	default:
		return "F"
	}
}
