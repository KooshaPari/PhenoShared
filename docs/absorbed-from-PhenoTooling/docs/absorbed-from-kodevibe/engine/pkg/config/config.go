package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"kodevibe/internal/models"

	"github.com/spf13/viper"
	"gopkg.in/yaml.v3"
)

const (
	DefaultConfigFile = ".kodevibe.yaml"
	GlobalConfigFile  = "kodevibe.yaml"
)

// Manager handles configuration loading and validation
type Manager struct {
	config *models.Configuration
	viper  *viper.Viper
}

// NewManager creates a new configuration manager
func NewManager() *Manager {
	return &Manager{
		viper: viper.New(),
	}
}

// LoadConfig loads configuration from file and environment variables
func (m *Manager) LoadConfig(configPath string) error {
	m.viper.SetConfigType("yaml")

	// Set default values
	m.setDefaults()

	// Load from file
	if configPath != "" {
		if err := m.loadFromFile(configPath); err != nil {
			return fmt.Errorf("failed to load config from file: %w", err)
		}
	} else {
		// Try to find config file in current directory or home directory
		if err := m.loadFromDefaultLocations(); err != nil {
			// Use default configuration if no config file found
			m.config = m.getDefaultConfig()
		}
	}

	// Load from environment variables
	m.loadFromEnv()

	// Unmarshal into config struct
	if err := m.viper.Unmarshal(&m.config); err != nil {
		return fmt.Errorf("failed to unmarshal config: %w", err)
	}

	// Validate configuration
	if err := m.validateConfig(); err != nil {
		return fmt.Errorf("invalid configuration: %w", err)
	}

	return nil
}

// GetConfig returns the loaded configuration
func (m *Manager) GetConfig() *models.Configuration {
	return m.config
}

// SaveConfig saves the current configuration to file
func (m *Manager) SaveConfig(configPath string) error {
	data, err := yaml.Marshal(m.config)
	if err != nil {
		return fmt.Errorf("failed to marshal config: %w", err)
	}

	if err := os.WriteFile(configPath, data, 0644); err != nil {
		return fmt.Errorf("failed to write config file: %w", err)
	}

	return nil
}

// setDefaults sets default configuration values
func (m *Manager) setDefaults() {
	// Core settings
	m.viper.SetDefault("project.type", "auto-detect")
	m.viper.SetDefault("project.language", "auto-detect")

	// Vibes settings
	m.viper.SetDefault("vibes.security.enabled", true)
	m.viper.SetDefault("vibes.security.level", "strict")
	m.viper.SetDefault("vibes.code.enabled", true)
	m.viper.SetDefault("vibes.code.level", "moderate")
	m.viper.SetDefault("vibes.code.max_function_length", 50)
	m.viper.SetDefault("vibes.code.max_nesting_depth", 4)
	m.viper.SetDefault("vibes.performance.enabled", true)
	m.viper.SetDefault("vibes.performance.level", "moderate")
	m.viper.SetDefault("vibes.performance.max_bundle_size", "2MB")
	m.viper.SetDefault("vibes.file.enabled", true)
	m.viper.SetDefault("vibes.file.level", "strict")
	m.viper.SetDefault("vibes.git.enabled", true)
	m.viper.SetDefault("vibes.git.min_commit_message_length", 10)
	m.viper.SetDefault("vibes.dependency.enabled", true)
	m.viper.SetDefault("vibes.dependency.check_vulnerabilities", true)
	m.viper.SetDefault("vibes.documentation.enabled", false)

	// Exclude patterns
	m.viper.SetDefault("exclude.files", []string{
		"node_modules/**/*",
		".git/**/*",
		"coverage/**/*",
		"*.min.js",
		"*.min.css",
		"vendor/**/*",
		"build/**/*",
		"dist/**/*",
		"*.lock",
		"*.log",
	})

	// Advanced settings
	m.viper.SetDefault("advanced.entropy_analysis", true)
	m.viper.SetDefault("advanced.entropy_threshold", 4.5)
	m.viper.SetDefault("advanced.ai_detection", false)
	m.viper.SetDefault("advanced.cache_enabled", true)
	m.viper.SetDefault("advanced.cache_ttl", "1h")
	m.viper.SetDefault("advanced.max_concurrency", 10)
	m.viper.SetDefault("advanced.timeout", "5m")

	// Server settings
	m.viper.SetDefault("server.host", "localhost")
	m.viper.SetDefault("server.port", 8080)
	m.viper.SetDefault("server.tls", false)
	m.viper.SetDefault("server.auth.enabled", false)
	m.viper.SetDefault("server.rate_limit.enabled", true)
	m.viper.SetDefault("server.rate_limit.rps", 100)
	m.viper.SetDefault("server.rate_limit.burst", 200)
	m.viper.SetDefault("server.cors.enabled", true)
	m.viper.SetDefault("server.cors.allowed_origins", []string{"*"})
	m.viper.SetDefault("server.monitoring.enabled", true)
	m.viper.SetDefault("server.monitoring.prometheus", true)
	m.viper.SetDefault("server.monitoring.health_check", true)
	m.viper.SetDefault("server.monitoring.metrics_path", "/metrics")

	// Reporting settings
	m.viper.SetDefault("reporting.generate_reports", true)
	m.viper.SetDefault("reporting.report_format", "text")
	m.viper.SetDefault("reporting.report_path", "./kodevibe-reports")
	m.viper.SetDefault("reporting.logging.enabled", true)
	m.viper.SetDefault("reporting.logging.level", "info")
	m.viper.SetDefault("reporting.logging.format", "json")
}

// loadFromFile loads configuration from a specific file
func (m *Manager) loadFromFile(configPath string) error {
	if _, err := os.Stat(configPath); os.IsNotExist(err) {
		return fmt.Errorf("config file not found: %s", configPath)
	}

	m.viper.SetConfigFile(configPath)
	return m.viper.ReadInConfig()
}

// loadFromDefaultLocations tries to load config from default locations
func (m *Manager) loadFromDefaultLocations() error {
	// Try current directory
	if _, err := os.Stat(DefaultConfigFile); err == nil {
		m.viper.SetConfigFile(DefaultConfigFile)
		return m.viper.ReadInConfig()
	}

	// Try home directory
	home, err := os.UserHomeDir()
	if err == nil {
		homeConfig := filepath.Join(home, ".config", "kodevibe", GlobalConfigFile)
		if _, err := os.Stat(homeConfig); err == nil {
			m.viper.SetConfigFile(homeConfig)
			return m.viper.ReadInConfig()
		}
	}

	return fmt.Errorf("no config file found in default locations")
}

// loadFromEnv loads configuration from environment variables
func (m *Manager) loadFromEnv() {
	m.viper.SetEnvPrefix("KODEVIBE")
	m.viper.SetEnvKeyReplacer(strings.NewReplacer(".", "_"))
	m.viper.AutomaticEnv()
}

// validateConfig validates the loaded configuration
func (m *Manager) validateConfig() error {
	if m.config == nil {
		return fmt.Errorf("configuration is nil")
	}

	// Validate project settings
	if m.config.Project.Type == "" {
		m.config.Project.Type = "auto-detect"
	}

	// Validate vibe settings
	if m.config.Vibes == nil {
		m.config.Vibes = make(map[models.VibeType]models.VibeConfig)
	}

	// Ensure required vibes are configured
	requiredVibes := []models.VibeType{
		models.VibeTypeSecurity,
		models.VibeTypeCode,
		models.VibeTypePerformance,
		models.VibeTypeFile,
		models.VibeTypeGit,
		models.VibeTypeDependency,
		models.VibeTypeDocumentation,
	}

	for _, vibe := range requiredVibes {
		if _, exists := m.config.Vibes[vibe]; !exists {
			m.config.Vibes[vibe] = models.VibeConfig{
				Enabled: true,
				Level:   "moderate",
			}
		}
	}

	// Validate advanced settings
	if m.config.Advanced.MaxConcurrency <= 0 {
		m.config.Advanced.MaxConcurrency = 10
	}

	if m.config.Advanced.Timeout <= 0 {
		m.config.Advanced.Timeout = 5 * time.Minute
	}

	if m.config.Advanced.EntropyThreshold <= 0 {
		m.config.Advanced.EntropyThreshold = 4.5
	}

	return nil
}

// getDefaultConfig returns a default configuration
func (m *Manager) getDefaultConfig() *models.Configuration {
	return &models.Configuration{
		Vibes: map[models.VibeType]models.VibeConfig{
			models.VibeTypeSecurity: {
				Enabled: true,
				Level:   "strict",
			},
			models.VibeTypeCode: {
				Enabled: true,
				Level:   "moderate",
				Settings: map[string]interface{}{
					"max_function_length": 50,
					"max_nesting_depth":   4,
				},
			},
			models.VibeTypePerformance: {
				Enabled: true,
				Level:   "moderate",
				Settings: map[string]interface{}{
					"max_bundle_size": "2MB",
				},
			},
			models.VibeTypeFile: {
				Enabled: true,
				Level:   "strict",
			},
			models.VibeTypeGit: {
				Enabled: true,
				Level:   "moderate",
				Settings: map[string]interface{}{
					"min_commit_message_length": 10,
				},
			},
			models.VibeTypeDependency: {
				Enabled: true,
				Level:   "moderate",
				Settings: map[string]interface{}{
					"check_vulnerabilities": true,
				},
			},
			models.VibeTypeDocumentation: {
				Enabled: false,
				Level:   "moderate",
			},
		},
		Project: models.ProjectConfig{
			Type:     "auto-detect",
			Language: "auto-detect",
		},
		Exclude: models.ExcludeConfig{
			Files: []string{
				"node_modules/**/*",
				".git/**/*",
				"coverage/**/*",
				"*.min.js",
				"*.min.css",
				"vendor/**/*",
				"build/**/*",
				"dist/**/*",
			},
			Patterns: []string{
				"test-*",
				"*.test.*",
				"*.spec.*",
			},
		},
		Advanced: models.AdvancedConfig{
			EntropyAnalysis:  true,
			EntropyThreshold: 4.5,
			AIDetection:      false,
			CacheEnabled:     true,
			CacheTTL:         time.Hour,
			MaxConcurrency:   10,
			Timeout:          5 * time.Minute,
		},
		Reporting: models.ReportingConfig{
			GenerateReports: true,
			ReportFormat:    "text",
			ReportPath:      "./kodevibe-reports",
			Logging: models.LoggingConfig{
				Enabled: true,
				Level:   "info",
				Format:  "json",
			},
		},
	}
}

// CreateDefaultConfig creates a default configuration file
func CreateDefaultConfig(path string) error {
	manager := NewManager()
	manager.config = manager.getDefaultConfig()
	return manager.SaveConfig(path)
}

// MergeConfigs merges multiple configurations with the later ones taking precedence
func MergeConfigs(configs ...*models.Configuration) *models.Configuration {
	if len(configs) == 0 {
		return nil
	}

	base := configs[0]
	for i := 1; i < len(configs); i++ {
		if configs[i] == nil {
			continue
		}

		// Merge vibes configuration
		if configs[i].Vibes != nil {
			if base.Vibes == nil {
				base.Vibes = make(map[models.VibeType]models.VibeConfig)
			}
			for k, v := range configs[i].Vibes {
				base.Vibes[k] = v
			}
		}

		// Merge project configuration
		if configs[i].Project.Type != "" {
			base.Project.Type = configs[i].Project.Type
		}
		if configs[i].Project.Language != "" {
			base.Project.Language = configs[i].Project.Language
		}
		if configs[i].Project.Framework != "" {
			base.Project.Framework = configs[i].Project.Framework
		}

		// Merge exclude configuration
		if len(configs[i].Exclude.Files) > 0 {
			base.Exclude.Files = append(base.Exclude.Files, configs[i].Exclude.Files...)
		}
		if len(configs[i].Exclude.Patterns) > 0 {
			base.Exclude.Patterns = append(base.Exclude.Patterns, configs[i].Exclude.Patterns...)
		}

		// Merge custom rules
		if len(configs[i].CustomRules) > 0 {
			base.CustomRules = append(base.CustomRules, configs[i].CustomRules...)
		}
	}

	return base
}

// ValidateConfigFile validates a configuration file
func ValidateConfigFile(path string) error {
	manager := NewManager()
	return manager.LoadConfig(path)
}
