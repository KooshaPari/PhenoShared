package models

import "time"

type User struct {
	UUID      string     `json:"uuid" gorm:"type:uuid;primaryKey;default:gen_random_uuid()"`
	Name      string     `json:"name" gorm:"type:varchar(255);not null"`
	Email     string     `json:"email" gorm:"type:varchar(255);uniqueIndex;not null"`
	Password  string     `json:"password" gorm:"type:varchar(255);not null"`
	AwsCreds    AwsCreds      `json:"awsCreds" gorm:"embedded;embeddedPrefix:aws_"`
	AzureCreds  AzureCreds    `json:"azureCreds" gorm:"embedded;embeddedPrefix:azure_"`
	GCPCreds    GCPCreds      `json:"gcpCreds" gorm:"embedded;embeddedPrefix:gcp_"`
	VercelCreds VercelCreds   `json:"vercelCreds" gorm:"embedded;embeddedPrefix:vercel_"`
	NetlifyCreds NetlifyCreds `json:"netlifyCreds" gorm:"embedded;embeddedPrefix:netlify_"`
	RailwayCreds RailwayCreds `json:"railwayCreds" gorm:"embedded;embeddedPrefix:railway_"`
	FlyIOCreds  FlyIOCreds    `json:"flyioCreds" gorm:"embedded;embeddedPrefix:flyio_"`
	SupabaseCreds SupabaseCreds `json:"supabaseCreds" gorm:"embedded;embeddedPrefix:supabase_"`
	LLMConfig   LLM           `json:"llmConfig" gorm:"embedded;embeddedPrefix:llm_"`
	Portfolio   Portfolio     `json:"portfolio" gorm:"embedded;embeddedPrefix:portfolio_"`
	Projects  []Project  `json:"projects" gorm:"foreignKey:Owner;references:UUID"`
	Instances []Instance `json:"instances" gorm:"foreignKey:Owner;references:UUID"`
	CreatedAt time.Time  `json:"created_at" gorm:"autoCreateTime"`
	UpdatedAt time.Time  `json:"updated_at" gorm:"autoUpdateTime"`
}

// LLM holds the user's LLM provider configuration.
// Provider defaults to "vllm" for self-hosted Linux/prod installs.
// Use "mlx" for macOS/Apple Silicon. Both expose an OpenAI-compatible API.
// Set Provider to "openai", "anthropic", etc. for cloud providers.
type LLM struct {
	// Provider is one of: "vllm" (Linux/prod default), "mlx" (macOS/Apple Silicon),
	// "openai", "anthropic", "gemini", "deepseek"
	Provider  string                `json:"provider" gorm:"column:provider"`
	Providers map[string]AIProvider `json:"providers" gorm:"type:jsonb;serializer:json"`
}

type AIProvider struct {
	Modal string `json:"modal" gorm:"column:modal"`
	// APIKey is optional for local vLLM/MLX servers; required for cloud providers.
	APIKey string `json:"api_key" gorm:"column:api_key"`
	// BaseUrl specifies the LLM server address.
	// vLLM default: http://localhost:8000
	// MLX default:  http://localhost:8080
	BaseUrl string `json:"baseUrl,omitempty" gorm:"column:base_url"`
}

type AwsCreds struct {
	AccessKeyID     string `gorm:"column:access_key_id"`
	SecretAccessKey string `gorm:"column:secret_access_key"`
}

// AzureCreds holds Azure service principal credentials.
type AzureCreds struct {
	TenantID       string `json:"azure_tenant_id,omitempty" gorm:"column:tenant_id"`
	ClientID       string `json:"azure_client_id,omitempty" gorm:"column:client_id"`
	ClientSecret   string `json:"azure_client_secret,omitempty" gorm:"column:client_secret"`
	SubscriptionID string `json:"azure_subscription_id,omitempty" gorm:"column:subscription_id"`
}

// GCPCreds holds GCP service account credentials.
type GCPCreds struct {
	ServiceAccountJSON string `json:"gcp_service_account_json,omitempty" gorm:"column:service_account_json;type:text"`
}

// VercelCreds holds a Vercel personal access token.
type VercelCreds struct {
	Token string `json:"vercel_token,omitempty" gorm:"column:token"`
}

// NetlifyCreds holds a Netlify personal access token.
type NetlifyCreds struct {
	Token string `json:"netlify_token,omitempty" gorm:"column:token"`
}

// RailwayCreds holds a Railway API token.
type RailwayCreds struct {
	Token string `json:"railway_token,omitempty" gorm:"column:token"`
}

// FlyIOCreds holds a Fly.io API token.
type FlyIOCreds struct {
	ApiToken string `json:"flyio_token,omitempty" gorm:"column:api_token"`
}

// SupabaseCreds holds a Supabase management access token.
type SupabaseCreds struct {
	AccessToken string `json:"supabase_access_token,omitempty" gorm:"column:access_token"`
}

type Portfolio struct {
	RootEndpoint string `gorm:"column:root_endpoint"`
	APIKey       string `gorm:"column:api_key"`
}

type LoginRequest struct {
	Email    string `json:"email"`
	Password string `json:"password"`
}
type SignupRequest struct {
	Name     string `json:"name"`
	Email    string `json:"email"`
	Password string `json:"password"`
}

// LinkRequest contains all credential and configuration fields settable after signup.
type LinkRequest struct {
	AwsCreds     AwsCreds      `gorm:"embedded;embeddedPrefix:aws_"`
	AzureCreds   AzureCreds    `gorm:"embedded;embeddedPrefix:azure_"`
	GCPCreds     GCPCreds      `gorm:"embedded;embeddedPrefix:gcp_"`
	VercelCreds  VercelCreds   `gorm:"embedded;embeddedPrefix:vercel_"`
	NetlifyCreds NetlifyCreds  `gorm:"embedded;embeddedPrefix:netlify_"`
	RailwayCreds RailwayCreds  `gorm:"embedded;embeddedPrefix:railway_"`
	FlyIOCreds   FlyIOCreds    `gorm:"embedded;embeddedPrefix:flyio_"`
	SupabaseCreds SupabaseCreds `gorm:"embedded;embeddedPrefix:supabase_"`
	LLMConfig    LLM           `gorm:"embedded;embeddedPrefix:openai_"`
	Portfolio    Portfolio     `gorm:"embedded;embeddedPrefix:portfolio_"`
}
