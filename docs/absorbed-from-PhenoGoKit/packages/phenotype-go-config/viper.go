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
		return fmt.Errorf("configuration path is empty")
	}

	// Check if path is a directory
	info, err := os.Stat(path)
	if err != nil {
		return fmt.Errorf("failed to stat config path: %w", err)
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
		return fmt.Errorf("failed to read config file: %w", err)
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
// Returns an empty string if the key doesn't exist or the value cannot be converted to a string.
//
// Parameters:
//   - key: The configuration key
//
// Returns:
//   - string: The string value
func (cl *ConfigLoader) GetString(key string) string {
	return cl.viper.GetString(key)
}

// GetInt retrieves an integer configuration value by key.
// Returns 0 if the key doesn't exist or the value cannot be converted to an integer.
//
// Parameters:
//   - key: The configuration key
//
// Returns:
//   - int: The integer value
func (cl *ConfigLoader) GetInt(key string) int {
	return cl.viper.GetInt(key)
}

// GetBool retrieves a boolean configuration value by key.
// Returns false if the key doesn't exist or the value cannot be converted to a boolean.
//
// Parameters:
//   - key: The configuration key
//
// Returns:
//   - bool: The boolean value
func (cl *ConfigLoader) GetBool(key string) bool {
	return cl.viper.GetBool(key)
}

// GetStringMap retrieves a nested map configuration value by key.
// Returns an empty map if the key doesn't exist.
//
// Parameters:
//   - key: The configuration key
//
// Returns:
//   - map[string]any: The map value
func (cl *ConfigLoader) GetStringMap(key string) map[string]any {
	return cl.viper.GetStringMap(key)
}

// GetStringSlice retrieves a string slice configuration value by key.
// Returns an empty slice if the key doesn't exist.
//
// Parameters:
//   - key: The configuration key
//
// Returns:
//   - []string: The string slice value
func (cl *ConfigLoader) GetStringSlice(key string) []string {
	return cl.viper.GetStringSlice(key)
}

// AllKeys returns all configuration keys that are set.
//
// Returns:
//   - []string: A slice of all configuration keys
func (cl *ConfigLoader) AllKeys() []string {
	return cl.viper.AllKeys()
}

// Unmarshal unmarshals the entire configuration into a struct.
// The struct should have viper tags for field mapping.
//
// Parameters:
//   - config: A pointer to a struct to unmarshal into
//
// Returns:
//   - error: An error if unmarshaling fails
func (cl *ConfigLoader) Unmarshal(config any) error {
	return cl.viper.Unmarshal(config)
}

// BindEnv binds a configuration key to an environment variable.
// When the key is accessed, viper will first check the environment variable.
//
// Parameters:
//   - key: The configuration key
//   - envVar: The environment variable name
//
// Returns:
//   - error: An error if binding fails
func (cl *ConfigLoader) BindEnv(key string, envVar string) error {
	return cl.viper.BindEnv(key, envVar)
}

// Set sets a configuration value in memory (not persisted to file).
//
// Parameters:
//   - key: The configuration key
//   - value: The value to set
func (cl *ConfigLoader) Set(key string, value any) {
	cl.viper.Set(key, value)
}

// CreateConfigFileIfMissing creates a new configuration file with a default template
// if the file does not exist.
//
// Parameters:
//   - filePath: The path where the config file should be created
//   - template: The default configuration content as a string
//
// Returns:
//   - error: An error if the file cannot be created
func CreateConfigFileIfMissing(filePath string, template string) error {
	filePath = strings.TrimSpace(filePath)
	if filePath == "" {
		return fmt.Errorf("file path is empty")
	}

	// Check if file already exists
	if _, err := os.Stat(filePath); err == nil {
		return nil // File exists, nothing to do
	}

	// Create directory if necessary
	dir := filepath.Dir(filePath)
	if err := os.MkdirAll(dir, 0700); err != nil {
		return fmt.Errorf("failed to create config directory: %w", err)
	}

	// Write the template to the file
	if err := os.WriteFile(filePath, []byte(template), 0644); err != nil {
		return fmt.Errorf("failed to create config file: %w", err)
	}

	return nil
}

// ConfigTemplate returns a basic YAML configuration template.
// This can be used to bootstrap new configuration files.
func ConfigTemplate() string {
	return `# Phenotype Configuration Template
# This file contains configuration options for Phenotype services

server:
  # Server listening host
  host: localhost
  # Server listening port
  port: 8080

log:
  # Log level: debug, info, warn, error
  level: info

auth:
  # OAuth provider settings can be configured here
  providers: {}

# Service-specific configuration can be added below
`
}
