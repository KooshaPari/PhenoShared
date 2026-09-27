package projectManager

import (
	"fmt"
	"nvms/models"
	"strings"

	"gopkg.in/yaml.v2"
)

func parseNVMSConfig(yamlContent string) (*models.NVMS, error) {
	fmt.Printf("Parsing YAML content: %s\n", yamlContent) // Debug log

	config := &models.NVMS{
		Services: []models.Service{},
	}

	// Validate YAML content
	if strings.TrimSpace(yamlContent) == "" {
		return nil, fmt.Errorf("empty YAML content")
	}

	// Parse YAML with error handling
	err := yaml.Unmarshal([]byte(yamlContent), config)
	if err != nil {
		return nil, fmt.Errorf("YAML parsing error: %w", err)
	}

	// Validate required fields
	if config.Name == "" {
		return nil, fmt.Errorf("missing required field: NAME")
	}
	if len(config.Services) == 0 {
		return nil, fmt.Errorf("no services defined in YAML")
	}

	// Validate each service
	found := false
	for name, svc := range config.Services {
		if svc.Path == "" {
			return nil, fmt.Errorf("service %s missing PATH", name)
		}
		if svc.Port == 0 {
			return nil, fmt.Errorf("service %s missing PORT", name)
		}
		if svc.Name == "main" {
			if found {
				return nil, fmt.Errorf("service main already defined", name)
			} else {
				found = true
			}
		}
	}
	if !found {
		return nil, fmt.Errorf("service main not defined")
	}

	return config, nil
}
