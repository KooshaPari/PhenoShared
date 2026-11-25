package core

import (
	"fmt"
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

// Config represents the global devenv-abstraction configuration
type Config struct {
	// Global settings
	Debug       bool   `yaml:"debug"`
	Trace       bool   `yaml:"trace"`
	DataDir     string `yaml:"data_dir"`
	CacheDir    string `yaml:"cache_dir"`
	LogLevel    string `yaml:"log_level"`
	LogFormat   string `yaml:"log_format"`

	// Sandbox defaults
	Sandbox SandboxConfig `yaml:"sandbox"`

	// VM defaults
	VM VMConfig `yaml:"vm"`

	// Metrics settings
	Metrics MetricsConfig `yaml:"metrics"`

	// Shell completion
	Completion CompletionConfig `yaml:"completion"`
}

// SandboxConfig holds sandbox-specific settings
type SandboxConfig struct {
	DefaultType   string            `yaml:"default_type"`
	AllowedTypes []string          `yaml:"allowed_types"`
	ResourceLimits ResourceLimits   `yaml:"resource_limits"`
	Timeouts     Timeouts         `yaml:"timeouts"`
}

// ResourceLimits defines CPU, memory, and disk limits
type ResourceLimits struct {
	CPUCount    int    `yaml:"cpu_count"`
	MemoryMB    int    `yaml:"memory_mb"`
	DiskMB      int    `yaml:"disk_mb"`
	Networks    []string `yaml:"networks"`
}

// Timeouts defines various operation timeouts
type Timeouts struct {
	Create       int `yaml:"create_seconds"`
	Start        int `yaml:"start_seconds"`
	Stop         int `yaml:"stop_seconds"`
	Destroy      int `yaml:"destroy_seconds"`
	HealthCheck  int `yaml:"health_check_seconds"`
}

// VMConfig holds VM-specific settings
type VMConfig struct {
	DefaultType   string   `yaml:"default_type"`
	AllowedTypes []string `yaml:"allowed_types"`
	ResourceLimits ResourceLimits `yaml:"resource_limits"`
	Timeouts     Timeouts `yaml:"timeouts"`
}

// MetricsConfig holds metrics/export settings
type MetricsConfig struct {
	Enabled     bool   `yaml:"enabled"`
	Address     string `yaml:"address"`
	Path        string `yaml:"path"`
}

// CompletionConfig holds shell completion settings
type CompletionConfig struct {
	Enabled bool   `yaml:"enabled"`
	Shell   string `yaml:"shell"`
}

// Profile represents a named configuration profile
type Profile struct {
	Name    string `yaml:"name"`
	Desc    string `yaml:"description"`
	Sandbox SandboxConfig `yaml:"sandbox"`
	VM      VMConfig `yaml:"vm"`
}

// LoadConfig loads configuration from a YAML file
func LoadConfig(path string) (*Config, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read config: %w", err)
	}

	var cfg Config
	if err := yaml.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("failed to parse config: %w", err)
	}

	// Apply defaults
	applyDefaults(&cfg)

	return &cfg, nil
}

// SaveConfig saves configuration to a YAML file
func SaveConfig(cfg *Config, path string) error {
	data, err := yaml.Marshal(cfg)
	if err != nil {
		return fmt.Errorf("failed to marshal config: %w", err)
	}

	if err := os.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("failed to write config: %w", err)
	}

	return nil
}

// DefaultConfig returns the default configuration
func DefaultConfig() *Config {
	cfg := &Config{
		Debug:     false,
		Trace:     false,
		DataDir:   "$HOME/.local/share/devenv-abstraction",
		CacheDir:  "$HOME/.cache/devenv-abstraction",
		LogLevel:  "info",
		LogFormat: "json",
		Sandbox: SandboxConfig{
			DefaultType:   "bwrap",
			AllowedTypes: []string{"bwrap", "firejail", "gvisor", "landlock", "seccomp", "wasmtime"},
			ResourceLimits: ResourceLimits{
				CPUCount: 2,
				MemoryMB: 512,
				DiskMB:   10240,
				Networks: []string{"none"},
			},
			Timeouts: Timeouts{
				Create:      30,
				Start:       10,
				Stop:        10,
				Destroy:     30,
				HealthCheck: 5,
			},
		},
		VM: VMConfig{
			DefaultType:   "lima",
			AllowedTypes: []string{"hyperkit", "lima", "firecracker", "wsl2", "kvm"},
			ResourceLimits: ResourceLimits{
				CPUCount: 4,
				MemoryMB: 4096,
				DiskMB:   51200,
				Networks: []string{"bridged"},
			},
			Timeouts: Timeouts{
				Create:      120,
				Start:       30,
				Stop:        30,
				Destroy:     60,
				HealthCheck: 10,
			},
		},
		Metrics: MetricsConfig{
			Enabled: false,
			Address: "localhost:9090",
			Path:    "/metrics",
		},
		Completion: CompletionConfig{
			Enabled: true,
			Shell:   "auto",
		},
	}

	applyDefaults(cfg)
	return cfg
}

// applyDefaults applies default values to fill in any missing configuration
func applyDefaults(cfg *Config) {
	home, _ := os.UserHomeDir()

	// Expand paths
	if cfg.DataDir != "" && cfg.DataDir[0] == '~' {
		cfg.DataDir = filepath.Join(home, cfg.DataDir[2:])
	} else if cfg.DataDir == "" {
		cfg.DataDir = filepath.Join(home, ".local/share/devenv-abstraction")
	}

	if cfg.CacheDir != "" && cfg.CacheDir[0] == '~' {
		cfg.CacheDir = filepath.Join(home, cfg.CacheDir[2:])
	} else if cfg.CacheDir == "" {
		cfg.CacheDir = filepath.Join(home, ".cache/devenv-abstraction")
	}

	// Ensure directories exist
	os.MkdirAll(cfg.DataDir, 0755)
	os.MkdirAll(cfg.CacheDir, 0755)
}

// Validate validates the configuration and returns any errors
func (c *Config) Validate() error {
	if c.Sandbox.DefaultType != "" {
		found := false
		for _, t := range c.Sandbox.AllowedTypes {
			if t == c.Sandbox.DefaultType {
				found = true
				break
			}
		}
		if !found {
			return fmt.Errorf("default sandbox type %q not in allowed types", c.Sandbox.DefaultType)
		}
	}

	if c.VM.DefaultType != "" {
		found := false
		for _, t := range c.VM.AllowedTypes {
			if t == c.VM.DefaultType {
				found = true
				break
			}
		}
		if !found {
			return fmt.Errorf("default VM type %q not in allowed types", c.VM.DefaultType)
		}
	}

	return nil
}

// LoadProfile loads a named profile from a profiles directory
func LoadProfile(profilesDir, name string) (*Profile, error) {
	path := filepath.Join(profilesDir, fmt.Sprintf("%s.yaml", name))
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read profile %q: %w", name, err)
	}

	var profile Profile
	if err := yaml.Unmarshal(data, &profile); err != nil {
		return nil, fmt.Errorf("failed to parse profile %q: %w", name, err)
	}

	return &profile, nil
}

// ListProfiles lists all available profiles in a directory
func ListProfiles(profilesDir string) ([]string, error) {
	entries, err := os.ReadDir(profilesDir)
	if err != nil {
		return nil, fmt.Errorf("failed to read profiles directory: %w", err)
	}

	var profiles []string
	for _, entry := range entries {
		if !entry.IsDir() && filepath.Ext(entry.Name()) == ".yaml" {
			profiles = append(profiles, entry.Name()[:len(entry.Name())-len(".yaml")])
		}
	}

	return profiles, nil
}

// ProfileForSandboxType creates a profile optimized for a specific sandbox type
func ProfileForSandboxType(sandboxType string) *Profile {
	switch sandboxType {
	case "gvisor":
		return &Profile{
			Name:    "gvisor-optimized",
			Desc:    "Optimized for gVisor with better syscall performance",
			Sandbox: SandboxConfig{
				DefaultType: "gvisor",
				ResourceLimits: ResourceLimits{
					CPUCount: 4,
					MemoryMB: 2048,
					DiskMB:   20480,
				},
			},
		}
	case "wasmtime":
		return &Profile{
			Name:    "wasm-optimized",
			Desc:    "Optimized for WASM workloads",
			Sandbox: SandboxConfig{
				DefaultType: "wasmtime",
				ResourceLimits: ResourceLimits{
					CPUCount: 2,
					MemoryMB: 512,
					DiskMB:   8192,
				},
			},
		}
	case "bwrap":
		return &Profile{
			Name:    "bwrap-lightweight",
			Desc:    "Lightweight profile using bubblewrap",
			Sandbox: SandboxConfig{
				DefaultType: "bwrap",
				ResourceLimits: ResourceLimits{
					CPUCount: 1,
					MemoryMB: 256,
					DiskMB:   4096,
				},
			},
		}
	default:
		return DefaultConfig().Sandbox.Profile("default")
	}
}

// Profile returns a copy of the sandbox profile with a name
func (s *SandboxConfig) Profile(name string) *Profile {
	return &Profile{
		Name:    name,
		Desc:    fmt.Sprintf("Profile %s", name),
		Sandbox: *s,
	}
}
