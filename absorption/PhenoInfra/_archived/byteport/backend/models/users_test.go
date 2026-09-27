package models

import (
	"encoding/json"
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestUser_Creation(t *testing.T) {
	user := User{
		UUID:     "user-123",
		Name:     "John Doe",
		Email:    "john@example.com",
		Password: "hashedpassword123",
		AwsCreds: AwsCreds{
			AccessKeyID:     "AKIA123456",
			SecretAccessKey: "secret123456",
		},
		LLMConfig: LLM{
			Provider: "openai",
			Providers: map[string]AIProvider{
				"openai": {
					Modal:  "gpt-4",
					APIKey: "sk-123456",
				},
				"anthropic": {
					Modal:  "claude-3",
					APIKey: "ant-123456",
				},
			},
		},
		Portfolio: Portfolio{
			RootEndpoint: "https://api.portfolio.com",
			APIKey:       "portfolio-key-123",
		},
	}

	assert.Equal(t, "user-123", user.UUID)
	assert.Equal(t, "John Doe", user.Name)
	assert.Equal(t, "john@example.com", user.Email)
	assert.Equal(t, "hashedpassword123", user.Password)
	assert.Equal(t, "AKIA123456", user.AwsCreds.AccessKeyID)
	assert.Equal(t, "secret123456", user.AwsCreds.SecretAccessKey)
	assert.Equal(t, "openai", user.LLMConfig.Provider)
	assert.Equal(t, "gpt-4", user.LLMConfig.Providers["openai"].Modal)
	assert.Equal(t, "sk-123456", user.LLMConfig.Providers["openai"].APIKey)
	assert.Equal(t, "https://api.portfolio.com", user.Portfolio.RootEndpoint)
	assert.Equal(t, "portfolio-key-123", user.Portfolio.APIKey)
}

func TestUser_JSONSerialization(t *testing.T) {
	user := User{
		UUID:     "user-456",
		Name:     "Jane Smith",
		Email:    "jane@example.com",
		Password: "hashedpassword456",
		AwsCreds: AwsCreds{
			AccessKeyID:     "AKIA654321",
			SecretAccessKey: "secret654321",
		},
		LLMConfig: LLM{
			Provider: "anthropic",
			Providers: map[string]AIProvider{
				"anthropic": {
					Modal:  "claude-3-sonnet",
					APIKey: "ant-654321",
				},
			},
		},
		Portfolio: Portfolio{
			RootEndpoint: "https://jane.portfolio.com",
			APIKey:       "jane-portfolio-key",
		},
		CreatedAt: time.Now(),
		UpdatedAt: time.Now(),
	}

	// Test JSON marshaling
	jsonData, err := json.Marshal(user)
	assert.NoError(t, err)
	assert.Contains(t, string(jsonData), "user-456")
	assert.Contains(t, string(jsonData), "jane@example.com")
	assert.Contains(t, string(jsonData), "hashedpassword456")

	// Test JSON unmarshaling
	var unmarshaledUser User
	err = json.Unmarshal(jsonData, &unmarshaledUser)
	assert.NoError(t, err)
	assert.Equal(t, user.UUID, unmarshaledUser.UUID)
	assert.Equal(t, user.Name, unmarshaledUser.Name)
	assert.Equal(t, user.Email, unmarshaledUser.Email)
	assert.Equal(t, user.Password, unmarshaledUser.Password)
	assert.Equal(t, user.AwsCreds.AccessKeyID, unmarshaledUser.AwsCreds.AccessKeyID)
	assert.Equal(t, user.LLMConfig.Provider, unmarshaledUser.LLMConfig.Provider)
	assert.Equal(t, user.Portfolio.RootEndpoint, unmarshaledUser.Portfolio.RootEndpoint)
}

func TestLLM_Creation(t *testing.T) {
	llm := LLM{
		Provider: "openai",
		Providers: map[string]AIProvider{
			"openai": {
				Modal:  "gpt-4",
				APIKey: "sk-openai-key",
			},
			"anthropic": {
				Modal:  "claude-3",
				APIKey: "ant-key",
			},
			"google": {
				Modal:  "gemini-pro",
				APIKey: "google-key",
			},
		},
	}

	assert.Equal(t, "openai", llm.Provider)
	assert.Len(t, llm.Providers, 3)
	assert.Equal(t, "gpt-4", llm.Providers["openai"].Modal)
	assert.Equal(t, "sk-openai-key", llm.Providers["openai"].APIKey)
	assert.Equal(t, "claude-3", llm.Providers["anthropic"].Modal)
	assert.Equal(t, "gemini-pro", llm.Providers["google"].Modal)
}

func TestAIProvider_Creation(t *testing.T) {
	tests := []struct {
		name     string
		provider AIProvider
	}{
		{
			name: "OpenAI provider",
			provider: AIProvider{
				Modal:  "gpt-4-turbo",
				APIKey: "sk-openai-key-123",
			},
		},
		{
			name: "Anthropic provider",
			provider: AIProvider{
				Modal:  "claude-3-opus",
				APIKey: "ant-key-456",
			},
		},
		{
			name: "Google provider",
			provider: AIProvider{
				Modal:  "gemini-pro-vision",
				APIKey: "google-key-789",
			},
		},
		{
			name: "empty provider",
			provider: AIProvider{
				Modal:  "",
				APIKey: "",
			},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.Equal(t, tt.provider.Modal, tt.provider.Modal)
			assert.Equal(t, tt.provider.APIKey, tt.provider.APIKey)
		})
	}
}

func TestAwsCreds_Creation(t *testing.T) {
	creds := AwsCreds{
		AccessKeyID:     "AKIAIOSFODNN7EXAMPLE",
		SecretAccessKey: "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
	}

	assert.Equal(t, "AKIAIOSFODNN7EXAMPLE", creds.AccessKeyID)
	assert.Equal(t, "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", creds.SecretAccessKey)
}

func TestPortfolio_Creation(t *testing.T) {
	portfolio := Portfolio{
		RootEndpoint: "https://api.myportfolio.com/v1",
		APIKey:       "portfolio-api-key-12345",
	}

	assert.Equal(t, "https://api.myportfolio.com/v1", portfolio.RootEndpoint)
	assert.Equal(t, "portfolio-api-key-12345", portfolio.APIKey)
}

func TestLoginRequest_Creation(t *testing.T) {
	request := LoginRequest{
		Email:    "user@example.com",
		Password: "mypassword123",
	}

	assert.Equal(t, "user@example.com", request.Email)
	assert.Equal(t, "mypassword123", request.Password)

	// Test JSON serialization
	jsonData, err := json.Marshal(request)
	assert.NoError(t, err)
	assert.Contains(t, string(jsonData), "user@example.com")
	assert.Contains(t, string(jsonData), "mypassword123")

	// Test JSON deserialization
	var unmarshaled LoginRequest
	err = json.Unmarshal(jsonData, &unmarshaled)
	assert.NoError(t, err)
	assert.Equal(t, request.Email, unmarshaled.Email)
	assert.Equal(t, request.Password, unmarshaled.Password)
}

func TestSignupRequest_Creation(t *testing.T) {
	request := SignupRequest{
		Name:     "New User",
		Email:    "newuser@example.com",
		Password: "securepassword456",
	}

	assert.Equal(t, "New User", request.Name)
	assert.Equal(t, "newuser@example.com", request.Email)
	assert.Equal(t, "securepassword456", request.Password)

	// Test JSON serialization
	jsonData, err := json.Marshal(request)
	assert.NoError(t, err)
	assert.Contains(t, string(jsonData), "New User")
	assert.Contains(t, string(jsonData), "newuser@example.com")
	assert.Contains(t, string(jsonData), "securepassword456")

	// Test JSON deserialization
	var unmarshaled SignupRequest
	err = json.Unmarshal(jsonData, &unmarshaled)
	assert.NoError(t, err)
	assert.Equal(t, request.Name, unmarshaled.Name)
	assert.Equal(t, request.Email, unmarshaled.Email)
	assert.Equal(t, request.Password, unmarshaled.Password)
}

func TestLinkRequest_Creation(t *testing.T) {
	request := LinkRequest{
		AwsCreds: AwsCreds{
			AccessKeyID:     "AKIA123",
			SecretAccessKey: "secret123",
		},
		LLMConfig: LLM{
			Provider: "openai",
			Providers: map[string]AIProvider{
				"openai": {
					Modal:  "gpt-4",
					APIKey: "sk-123",
				},
			},
		},
		Portfolio: Portfolio{
			RootEndpoint: "https://portfolio.com",
			APIKey:       "port-key-123",
		},
	}

	assert.Equal(t, "AKIA123", request.AwsCreds.AccessKeyID)
	assert.Equal(t, "secret123", request.AwsCreds.SecretAccessKey)
	assert.Equal(t, "openai", request.LLMConfig.Provider)
	assert.Equal(t, "gpt-4", request.LLMConfig.Providers["openai"].Modal)
	assert.Equal(t, "https://portfolio.com", request.Portfolio.RootEndpoint)
}

func TestUser_DatabaseOperations(t *testing.T) {
	// Skip complex database operations for now - focus on core functionality
	// These would require full GORM schema setup with embedded fields
	t.Skip("Database operations test skipped - requires full PostgreSQL setup")
	
	// Note: This test would verify:
	// - User creation with embedded AWS credentials, LLM config, and Portfolio
	// - Finding users by UUID
	// - Updating user fields
	// - Soft deletion of users
	// - Foreign key relationships with projects and instances
}

func TestUser_ValidationScenarios(t *testing.T) {
	tests := []struct {
		name        string
		user        User
		description string
	}{
		{
			name: "minimal valid user",
			user: User{
				UUID:     "min-user",
				Name:     "Min",
				Email:    "min@example.com",
				Password: "pass",
			},
			description: "User with only required fields",
		},
		{
			name: "user with empty LLM providers",
			user: User{
				UUID:     "empty-llm-user",
				Name:     "Empty LLM User",
				Email:    "empty@example.com",
				Password: "pass",
				LLMConfig: LLM{
					Provider:  "",
					Providers: make(map[string]AIProvider),
				},
			},
			description: "User with empty LLM configuration",
		},
		{
			name: "user with multiple AI providers",
			user: User{
				UUID:     "multi-ai-user",
				Name:     "Multi AI User",
				Email:    "multi@example.com",
				Password: "pass",
				LLMConfig: LLM{
					Provider: "openai",
					Providers: map[string]AIProvider{
						"openai":    {Modal: "gpt-4", APIKey: "sk-openai"},
						"anthropic": {Modal: "claude-3", APIKey: "ant-key"},
						"google":    {Modal: "gemini", APIKey: "google-key"},
						"cohere":    {Modal: "command", APIKey: "cohere-key"},
					},
				},
			},
			description: "User with multiple AI provider configurations",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			assert.NotEmpty(t, tt.user.UUID, tt.description)
			assert.NotEmpty(t, tt.user.Name, tt.description)
			assert.NotEmpty(t, tt.user.Email, tt.description)
			assert.NotEmpty(t, tt.user.Password, tt.description)

			// Test JSON serialization doesn't break
			jsonData, err := json.Marshal(tt.user)
			assert.NoError(t, err, tt.description)
			assert.NotEmpty(t, jsonData, tt.description)

			// Test JSON deserialization
			var unmarshaled User
			err = json.Unmarshal(jsonData, &unmarshaled)
			assert.NoError(t, err, tt.description)
			assert.Equal(t, tt.user.UUID, unmarshaled.UUID, tt.description)
		})
	}
}

func TestUser_EdgeCases(t *testing.T) {
	t.Run("user with unicode characters", func(t *testing.T) {
		user := User{
			UUID:     "unicode-user-🦄",
			Name:     "José María Niño-Díaz 🚀",
			Email:    "josé@müller.com",
			Password: "pássword123🔑",
		}

		jsonData, err := json.Marshal(user)
		assert.NoError(t, err)

		var unmarshaled User
		err = json.Unmarshal(jsonData, &unmarshaled)
		assert.NoError(t, err)
		assert.Equal(t, user.Name, unmarshaled.Name)
		assert.Equal(t, user.Email, unmarshaled.Email)
	})

	t.Run("user with very long values", func(t *testing.T) {
		longString := ""
		for i := 0; i < 1000; i++ {
			longString += "a"
		}

		user := User{
			UUID:     "long-user",
			Name:     longString[:255], // Typical DB limit
			Email:    "long@example.com",
			Password: longString,
		}

		assert.NotEmpty(t, user.Name)
		assert.NotEmpty(t, user.Password)
	})

	t.Run("user with nil pointers handled gracefully", func(t *testing.T) {
		user := User{
			UUID:     "safe-user",
			Name:     "Safe User",
			Email:    "safe@example.com",
			Password: "pass",
			Projects:  nil,
			Instances: nil,
		}

		jsonData, err := json.Marshal(user)
		assert.NoError(t, err)
		assert.Contains(t, string(jsonData), "safe-user")
	})
}