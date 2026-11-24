// lib/tunnel.go - Cloudflare Tunnel management for BytePort Windows
package lib

import (
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"strings"
	"sync"

	"gopkg.in/yaml.v2"
	"nvms/models"
)

type TunnelManager struct {
	configPath      string
	tunnelName      string
	domain          string
	credentialsFile string
	runningTunnels  map[string]*TunnelProcess
	mutex           sync.RWMutex
}

type TunnelProcess struct {
	ProjectName string
	ConfigFile  string
	URL         string
}

type TunnelConfig struct {
	Tunnel          string                   `yaml:"tunnel"`
	CredentialsFile string                   `yaml:"credentials-file"`
	Ingress         []map[string]interface{} `yaml:"ingress"`
	LogFile         string                   `yaml:"logfile,omitempty"`
}

var tunnelManagerInstance *TunnelManager
var tunnelManagerOnce sync.Once

func GetTunnelManager() (*TunnelManager, error) {
	var err error
	tunnelManagerOnce.Do(func() {
		// Default configuration - should be overridden by environment variables
		configPath := os.Getenv("TUNNEL_CONFIG_PATH")
		if configPath == "" {
			configPath = "C:\\BytePort\\tunnels"
		}

		tunnelName := os.Getenv("TUNNEL_NAME")
		if tunnelName == "" {
			tunnelName = "byteport-main"
		}

		domain := os.Getenv("BYTEPORT_DOMAIN")
		if domain == "" {
			domain = "yourdomain.com"
		}

		credentialsFile := filepath.Join(configPath, "credentials.json")

		tunnelManagerInstance, err = NewTunnelManager(configPath, tunnelName, domain, credentialsFile)
	})
	return tunnelManagerInstance, err
}

func NewTunnelManager(configPath, tunnelName, domain, credentialsFile string) (*TunnelManager, error) {
	tm := &TunnelManager{
		configPath:      configPath,
		tunnelName:      tunnelName,
		domain:          domain,
		credentialsFile: credentialsFile,
		runningTunnels:  make(map[string]*TunnelProcess),
	}

	// Ensure config directory exists
	err := os.MkdirAll(configPath, 0755)
	if err != nil {
		return nil, fmt.Errorf("failed to create config directory: %w", err)
	}

	return tm, nil
}

func (tm *TunnelManager) CreateProjectTunnel(projectName string, services []models.Service) (string, error) {
	tm.mutex.Lock()
	defer tm.mutex.Unlock()

	// Generate tunnel configuration
	config := TunnelConfig{
		Tunnel:          tm.tunnelName,
		CredentialsFile: tm.credentialsFile,
		Ingress:         tm.generateIngressRules(projectName, services),
		LogFile:         filepath.Join(tm.configPath, fmt.Sprintf("%s.log", projectName)),
	}

	// Write configuration to file
	configBytes, err := yaml.Marshal(config)
	if err != nil {
		return "", fmt.Errorf("failed to marshal tunnel config: %w", err)
	}

	configFile := filepath.Join(tm.configPath, fmt.Sprintf("%s.yml", projectName))
	err = ioutil.WriteFile(configFile, configBytes, 0644)
	if err != nil {
		return "", fmt.Errorf("failed to write tunnel config: %w", err)
	}

	// Generate project URL
	projectURL := fmt.Sprintf("https://%s.%s", projectName, tm.domain)

	return projectURL, nil
}

func (tm *TunnelManager) StartProjectTunnel(projectName string) (string, error) {
	tm.mutex.Lock()
	defer tm.mutex.Unlock()

	// Check if tunnel is already running
	if tunnel, exists := tm.runningTunnels[projectName]; exists {
		return tunnel.URL, nil
	}

	configFile := filepath.Join(tm.configPath, fmt.Sprintf("%s.yml", projectName))
	if _, err := os.Stat(configFile); os.IsNotExist(err) {
		return "", fmt.Errorf("tunnel configuration not found for project %s", projectName)
	}

	projectURL := fmt.Sprintf("https://%s.%s", projectName, tm.domain)

	// Store configured tunnel info. Runtime startup is handled by the Windows setup scripts.
	tm.runningTunnels[projectName] = &TunnelProcess{
		ProjectName: projectName,
		ConfigFile:  configFile,
		URL:         projectURL,
	}

	return projectURL, nil
}

func (tm *TunnelManager) StopProjectTunnel(projectName string) error {
	tm.mutex.Lock()
	defer tm.mutex.Unlock()

	tunnel, exists := tm.runningTunnels[projectName]
	if !exists {
		return fmt.Errorf("tunnel not found for project %s", projectName)
	}

	_ = tunnel
	delete(tm.runningTunnels, projectName)

	return nil
}

func (tm *TunnelManager) RemoveProjectTunnel(projectName string) error {
	// Stop tunnel if running
	if _, exists := tm.runningTunnels[projectName]; exists {
		err := tm.StopProjectTunnel(projectName)
		if err != nil {
			return err
		}
	}

	// Remove configuration file
	configFile := filepath.Join(tm.configPath, fmt.Sprintf("%s.yml", projectName))
	err := os.Remove(configFile)
	if err != nil && !os.IsNotExist(err) {
		return fmt.Errorf("failed to remove tunnel config: %w", err)
	}

	// Remove log file
	logFile := filepath.Join(tm.configPath, fmt.Sprintf("%s.log", projectName))
	os.Remove(logFile) // Ignore errors for log file removal

	return nil
}

func (tm *TunnelManager) GetProjectURL(projectName string) string {
	tm.mutex.RLock()
	defer tm.mutex.RUnlock()

	if tunnel, exists := tm.runningTunnels[projectName]; exists {
		return tunnel.URL
	}

	return fmt.Sprintf("https://%s.%s", projectName, tm.domain)
}

func (tm *TunnelManager) ListRunningTunnels() map[string]string {
	tm.mutex.RLock()
	defer tm.mutex.RUnlock()

	result := make(map[string]string)
	for projectName, tunnel := range tm.runningTunnels {
		result[projectName] = tunnel.URL
	}

	return result
}

func (tm *TunnelManager) generateIngressRules(projectName string, services []models.Service) []map[string]interface{} {
	var rules []map[string]interface{}
	hostname := fmt.Sprintf("%s.%s", projectName, tm.domain)

	// Sort services to ensure 'main' comes first
	var mainService *models.Service
	var otherServices []models.Service

	for i, service := range services {
		if service.Name == "main" {
			mainService = &services[i]
		} else {
			otherServices = append(otherServices, service)
		}
	}

	// Add main service rule (root path)
	if mainService != nil {
		rules = append(rules, map[string]interface{}{
			"hostname": hostname,
			"service":  fmt.Sprintf("http://localhost:%d", mainService.Port),
		})
	}

	// Add other services with path-based routing
	for _, service := range otherServices {
		rules = append(rules, map[string]interface{}{
			"hostname": hostname,
			"path":     fmt.Sprintf("/%s/*", service.Name),
			"service":  fmt.Sprintf("http://localhost:%d", service.Port),
		})
	}

	// Add catch-all rule
	rules = append(rules, map[string]interface{}{
		"service": "http_status:404",
	})

	return rules
}

func (tm *TunnelManager) UpdateProjectTunnel(projectName string, services []models.Service) error {
	// Stop existing tunnel
	if _, exists := tm.runningTunnels[projectName]; exists {
		err := tm.StopProjectTunnel(projectName)
		if err != nil {
			return fmt.Errorf("failed to stop existing tunnel: %w", err)
		}
	}

	// Create new configuration
	_, err := tm.CreateProjectTunnel(projectName, services)
	if err != nil {
		return fmt.Errorf("failed to create updated tunnel config: %w", err)
	}

	// Start tunnel with new configuration
	_, err = tm.StartProjectTunnel(projectName)
	if err != nil {
		return fmt.Errorf("failed to start updated tunnel: %w", err)
	}

	return nil
}

func (tm *TunnelManager) ValidateTunnelSetup() error {
	// Check if credentials file exists
	if _, err := os.Stat(tm.credentialsFile); os.IsNotExist(err) {
		return fmt.Errorf("tunnel credentials file not found: %s", tm.credentialsFile)
	}

	return nil
}

func (tm *TunnelManager) GetTunnelStatus(projectName string) string {
	tm.mutex.RLock()
	defer tm.mutex.RUnlock()

	if tunnel, exists := tm.runningTunnels[projectName]; exists {
		_ = tunnel
		return "configured"
	}

	return "not_started"
}

// Compatibility function to match existing AWS deployment interface
func (tm *TunnelManager) ProvisionNetwork(projectName string, services []models.Service) (NetworkInfo, error) {
	projectURL, err := tm.CreateProjectTunnel(projectName, services)
	if err != nil {
		return NetworkInfo{}, err
	}

	actualURL, err := tm.StartProjectTunnel(projectName)
	if err != nil {
		return NetworkInfo{}, err
	}

	return NetworkInfo{
		ProxyURL: actualURL,
		LocalURL: fmt.Sprintf("http://localhost:%d", services[0].Port),
		ALBARN:   projectURL, // For compatibility
		VpcID:    "local",    // For compatibility
	}, nil
}

type NetworkInfo struct {
	ProxyURL string
	LocalURL string
	ALBARN   string
	VpcID    string
}
