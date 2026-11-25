// Package config provides shared configuration loading utilities for Phenotype services.
package config

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/spf13/viper"
)

// ConfigLoader wraps viper to provide easy configuration loading from YAML files.
type ConfigLoader struct {
	viper *viper.Viper
	path  string
}

// NewConfigLoader creates a new ConfigLoader instance.
// It initializes viper with sensible defaults for loading YAML configurations.
//
// Parameters:
//   - path: The path to the configuration file (or directory containing config.yaml)
//
// Returns:
//   - *ConfigLoader: A new ConfigLoader instance
func NewConfigLoader(path string) *ConfigLoader {
	v := viper.New()
	v.SetConfigType("yaml")

	// Set default values for common configuration options
	v.SetDefault("server.port", 8080)
	v.SetDefault("server.host", "localhost")
	v.SetDefault("log.level", "info")

	// Environment variable support
	v.SetEnvPrefix("PHENOTYPE")
	v.AutomaticEnv()

	return &ConfigLoader{
		viper: v,
		path:  path,
	}
}

// Load reads the configuration file and loads it into viper.
// Supports both direct file paths and directory paths (looks for config.yaml).
//
// Returns:
//   - error: An error if the configuration file cannot be read or parsed
func (cl *ConfigLoader) Load() error {
	path := strings.TrimSpace(cl.path)
	if path == "" {
		// If path is empty, we just rely on defaults and environment variables
		return nil
	}

	// Check if path is a directory
	info, err := os.Stat(path)
	if err != nil {
		// If file doesn't exist, we'll just skip loading from file
		return nil
	}

	if info.IsDir() {
		// Look for config.yaml in the directory
		cl.viper.AddConfigPath(path)
		cl.viper.SetConfigName("config")
	} else {
		// Use the file directly
		cl.viper.SetConfigFile(path)
	}

	// Read the configuration
	if err := cl.viper.ReadInConfig(); err != nil {
		// It's okay if the config file is missing if we have defaults
		if _, ok := err.(viper.ConfigFileNotFoundError); !ok {
			return fmt.Errorf("failed to read config file: %w", err)
		}
	}

	return nil
}

// LoadWithDefaults reads the configuration file and merges with a default configuration.
// The default configuration provides base values that can be overridden by the file.
//
// Parameters:
//   - defaults: A map of default configuration values
//
// Returns:
//   - error: An error if the configuration file cannot be read or parsed
func (cl *ConfigLoader) LoadWithDefaults(defaults map[string]any) error {
	// Set all defaults
	for key, value := range defaults {
		cl.viper.SetDefault(key, value)
	}

	// Load the configuration file
	return cl.Load()
}

// Get retrieves a configuration value by key.
//
// Parameters:
//   - key: The configuration key (dot-separated for nested values, e.g., "server.port")
//
// Returns:
//   - any: The configuration value, or nil if not found
func (cl *ConfigLoader) Get(key string) any {
	return cl.viper.Get(key)
}

// GetString retrieves a string configuration value by key.
func (cl *ConfigLoader) GetString(key string) string {
	return cl.viper.GetString(key)
}

// GetInt retrieves an integer configuration value by key.
func (cl *ConfigLoader) GetInt(key string) int {
	return cl.viper.GetInt(key)
}

// GetBool retrieves a boolean configuration value by key.
func (cl *ConfigLoader) GetBool(key string) bool {
	return cl.viper.GetBool(key)
}

// GetStringMap retrieves a nested map configuration value by key.
func (cl *ConfigLoader) GetStringMap(key string) map[string]any {
	return cl.viper.GetStringMap(key)
}

// GetStringSlice retrieves a string slice configuration value by key.
func (cl *ConfigLoader) GetStringSlice(key string) []string {
	return cl.viper.GetStringSlice(key)
}

// AllKeys returns all configuration keys that are set.
func (cl *ConfigLoader) AllKeys() []string {
	return cl.viper.AllKeys()
}

// Unmarshal unmarshals the entire configuration into a struct.
func (cl *ConfigLoader) Unmarshal(config any) error {
	return cl.viper.Unmarshal(config)
}

// BindEnv binds a configuration key to an environment variable.
func (cl *ConfigLoader) BindEnv(key string, envVar string) error {
	return cl.viper.BindEnv(key, envVar)
}

// Set sets a configuration value in memory (not persisted to file).
func (cl *ConfigLoader) Set(key string, value any) {
	cl.viper.Set(key, value)
}
