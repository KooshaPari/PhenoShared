package main

import (
	"sync"
	"time"
)

// Deployment represents a deployment in the system
type Deployment struct {
	ID        string            `json:"id"`
	Name      string            `json:"name"`
	Type      string            `json:"type"`
	Provider  string            `json:"provider"`
	Status    string            `json:"status"`
	URL       string            `json:"url"`
	GitURL    string            `json:"git_url,omitempty"`
	Branch    string            `json:"branch,omitempty"`
	EnvVars   map[string]string `json:"env_vars,omitempty"`
	CreatedAt time.Time         `json:"created_at"`
	UpdatedAt time.Time         `json:"updated_at"`
}

// DeploymentStore manages deployments in memory
type DeploymentStore struct {
	deployments map[string]*Deployment
	mu          sync.RWMutex
}

// NewDeploymentStore creates a new deployment store
func NewDeploymentStore() *DeploymentStore {
	return &DeploymentStore{
		deployments: make(map[string]*Deployment),
	}
}

// Add adds a deployment to the store
func (s *DeploymentStore) Add(deployment *Deployment) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.deployments[deployment.ID] = deployment
}

// Get retrieves a deployment by ID
func (s *DeploymentStore) Get(id string) *Deployment {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.deployments[id]
}

// Update updates an existing deployment
func (s *DeploymentStore) Update(deployment *Deployment) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.deployments[deployment.ID] = deployment
}

// Delete removes a deployment from the store
func (s *DeploymentStore) Delete(id string) {
	s.mu.Lock()
	defer s.mu.Unlock()
	delete(s.deployments, id)
}

// List returns all deployments
func (s *DeploymentStore) List() []*Deployment {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]*Deployment, 0, len(s.deployments))
	for _, dep := range s.deployments {
		result = append(result, dep)
	}
	return result
}
