package models

import (
	"gorm.io/datatypes"
	"time"
)

// ProviderConfig stores system-level cloud provider configurations
type ProviderConfig struct {
	ID          int    `gorm:"primaryKey;autoIncrement" json:"id"`
	Provider    string `gorm:"type:varchar(100);not null;uniqueIndex" json:"provider"`
	DisplayName string `gorm:"type:varchar(255);not null" json:"display_name"`

	// Provider capabilities
	SupportedTypes datatypes.JSON `gorm:"type:jsonb;not null" json:"supported_types"`
	// Example: ["frontend", "backend", "database"]

	// Pricing information
	PricingTiers datatypes.JSON `gorm:"type:jsonb;not null" json:"pricing_tiers"`
	// Tier information for cost estimation

	// Provider status
	IsEnabled bool `gorm:"default:true" json:"is_enabled"`
	IsBeta    bool `gorm:"default:false" json:"is_beta"`

	// Provider metadata
	Metadata datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"metadata"`
	// API endpoints, documentation links, etc.

	// Rate limits
	RateLimits datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"rate_limits"`

	CreatedAt time.Time `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt time.Time `gorm:"autoUpdateTime" json:"updated_at"`
}

// FrameworkPattern stores patterns for detecting application frameworks
type FrameworkPattern struct {
	ID        int    `gorm:"primaryKey;autoIncrement" json:"id"`
	Framework string `gorm:"type:varchar(100);not null;index" json:"framework"`
	Type      string `gorm:"type:varchar(50);not null;index" json:"type"`
	// Type: frontend, backend, fullstack

	// Detection patterns
	FilePatterns datatypes.JSON `gorm:"type:jsonb;not null" json:"file_patterns"`
	// Example: {"package.json": {"dependencies": {"next": "*"}}}

	DependencyPatterns datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"dependency_patterns"`
	// Dependency name patterns to check

	ConfidenceWeight float64 `gorm:"type:decimal(3,2);default:1.0" json:"confidence_weight"`
	// Weight for confidence calculation

	// Build configuration
	DefaultBuildCommand   *string `gorm:"type:varchar(500)" json:"default_build_command,omitempty"`
	DefaultStartCommand   *string `gorm:"type:varchar(500)" json:"default_start_command,omitempty"`
	DefaultInstallCommand *string `gorm:"type:varchar(500)" json:"default_install_command,omitempty"`

	// Recommended providers
	RecommendedProviders datatypes.JSON `gorm:"type:jsonb;default:'[]'" json:"recommended_providers"`

	// Framework metadata
	Metadata datatypes.JSON `gorm:"type:jsonb;default:'{}'" json:"metadata"`

	CreatedAt time.Time `gorm:"autoCreateTime" json:"created_at"`
	UpdatedAt time.Time `gorm:"autoUpdateTime" json:"updated_at"`
}

// APIRateLimit tracks API rate limits per user and endpoint
type APIRateLimit struct {
	ID           int64     `gorm:"primaryKey;autoIncrement" json:"id"`
	UserID       string    `gorm:"type:uuid;not null;index" json:"user_id"`
	Endpoint     string    `gorm:"type:varchar(255);not null" json:"endpoint"`
	WindowStart  time.Time `gorm:"not null;index" json:"window_start"`
	RequestCount int       `gorm:"default:1" json:"request_count"`
	CreatedAt    time.Time `gorm:"autoCreateTime" json:"created_at"`
}

// TableName overrides
func (ProviderConfig) TableName() string {
	return "provider_configs"
}

func (FrameworkPattern) TableName() string {
	return "framework_patterns"
}

func (APIRateLimit) TableName() string {
	return "api_rate_limits"
}

// Helper methods for ProviderConfig

// SupportsType checks if provider supports a given service type
func (pc *ProviderConfig) SupportsType(serviceType string) bool {
	// This would need to unmarshal the JSONB and check
	// Implementation depends on how you want to handle JSONB in Go
	return true // Placeholder
}

// GetTier returns pricing tier information
func (pc *ProviderConfig) GetTier(tierName string) (map[string]interface{}, error) {
	// Unmarshal and return tier info
	// Implementation depends on JSONB handling
	return nil, nil // Placeholder
}

// Helper methods for FrameworkPattern

// Matches checks if files match this framework pattern
func (fp *FrameworkPattern) Matches(files []string) (bool, float64) {
	// Implementation for pattern matching
	// Returns (matches, confidence)
	return false, 0.0 // Placeholder
}

// GetBuildConfig returns the build configuration
func (fp *FrameworkPattern) GetBuildConfig() map[string]string {
	config := make(map[string]string)

	if fp.DefaultBuildCommand != nil {
		config["build"] = *fp.DefaultBuildCommand
	}
	if fp.DefaultStartCommand != nil {
		config["start"] = *fp.DefaultStartCommand
	}
	if fp.DefaultInstallCommand != nil {
		config["install"] = *fp.DefaultInstallCommand
	}

	return config
}

// Helper methods for APIRateLimit

// IsExpired checks if the rate limit window has expired
func (arl *APIRateLimit) IsExpired() bool {
	return time.Since(arl.WindowStart) > time.Hour
}

// IncrementCount increments the request count
func (arl *APIRateLimit) IncrementCount() {
	arl.RequestCount++
}
