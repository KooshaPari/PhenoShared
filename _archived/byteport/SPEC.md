# BytePort — SPEC.md

> Canonical specification for BytePort. Reflects the actual shipping stack as of 2026-05.
> Supersedes all prior architecture descriptions referencing Rust/Loco.rs/NanoVMS.

---

## 1. Overview

**BytePort** is an Infrastructure-as-Code deployment platform combined with portfolio UX generation. Developers define their application and AWS infrastructure in a single NVMS manifest; BytePort deploys to AWS and automatically generates portfolio site components showcasing the deployed projects. Optionally uses an LLM (OpenAI or local) for enhanced template text generation.

### Canonical Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Backend API | Go 1.25, Gin framework | REST server on port 8081 |
| Persistence | SQLite via GORM | `backend/database.db` |
| Authentication | PASETO tokens | Auth middleware, cookie-based sessions |
| Encryption | AES-256-CFB + Argon2id | Credential encryption at rest |
| GitHub Integration | OAuth 2.0 | Token refresh background job |
| AWS Integration | AWS SDK for Go | EC2/S3 resource provisioning |
| Portfolio API | HTTP + SSRF protection | Credential validation endpoint |
| LLM Backend | OpenAI API (pluggable) | `gpt-4o` default model |
| Frontend | SvelteKit 2 + Svelte 5 + Tailwind 4 | Management UI |
| Desktop Shell | Tauri 2 | Native desktop/mobile packaging |
| Telemetry | OpenTelemetry (ConsoleSpanExporter) | Traces on stdout |

### Key Entry Points

```sh
./start dev   # tmux: SvelteKit dev (5173) + Go backend (8081) with air hot-reload
./start prod # Production: build frontend, run Go server
go build ./backend/...   # Build all Go packages
go test ./backend/...    # Run Go tests
```

### Key Commands

| Command | Description |
|---------|-------------|
| `go build ./backend/...` | Build all Go backend packages |
| `go test ./backend/...` | Run all Go backend tests |
| `golangci-lint run` | Lint Go backend code |
| `go vet ./backend/...` | Static analysis on Go backend |
| `just lint` | Run linting tasks (Go + Rust) |
| `just check` | Full validation: build + test + lint |
| `cargo test -p byteport-tauri` | Run Tauri desktop shell tests |
| `just start` | Start dev orchestration (SvelteKit + Go backend) |

---

## 2. Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        BytePort                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         Frontend — SvelteKit 2 / Tauri 2 Shell           │   │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────────┐  │   │
│  │  │  Dashboard │  │  Deploy    │  │  Portfolio       │  │   │
│  │  │  (Status)  │  │  Wizard    │  │  Settings       │  │   │
│  │  └────────────┘  └────────────┘  └──────────────────┘  │   │
│  └──────────────────────────────────────────────────────────┘   │
│                               │                                  │
│  ┌───────────────────────────┴──────────────────────────────┐  │
│  │              Go Backend API — Gin (port 8081)              │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │  │
│  │  │   Auth API   │  │ Deploy API  │  │ Portfolio API│  │  │
│  │  │  (PASETO)    │  │  (AWS SDK)  │  │  (HTTP)      │  │  │
│  │  │              │  │              │  │              │  │  │
│  │  │ • Signup     │  │ • Deploy     │  │ • Validate   │  │  │
│  │  │ • Login      │  │ • Terminate  │  │ • Link creds │  │  │
│  │  │ • GitHub OAuth│ │ • GitHub repos│ │ • LLM creds  │  │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘  │  │
│  └──────────────────────────────────────────────────────────┘   │
│                               │                                  │
│  ┌───────────────────────────┴──────────────────────────────┐  │
│  │              Persistence Layer (GORM / SQLite)             │  │
│  │  Users · Projects · Instances · Repositories · Secrets    │  │
│  └──────────────────────────────────────────────────────────┘   │
│                               │                                  │
│  ┌───────────────────────────┴──────────────────────────────┐  │
│  │              External Integrations                         │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │  │
│  │  │   GitHub     │  │     AWS      │  │  Portfolio   │   │  │
│  │  │  OAuth API   │  │   SDK Go     │  │  API (Slick) │   │  │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │  │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
1. User signup/login via /signup, /login
   → PASETO token issued, stored in httpOnly cookie

2. User links GitHub via /link → OAuth redirect → /api/github/callback
   → GitHub OAuth token encrypted and stored in DB

3. User links AWS, LLM, Portfolio credentials via /link (POST)
   → Credentials validated then AES-256-encrypted, stored in DB

4. User deploys project via /deploy
   → Project + NVMS config forwarded to nvms service
   → Resources tracked in Instance/Project records

5. User terminates via /terminate
   → nvms service called, DB records cleaned up
```

### Directory Structure

```
BytePort/
├── backend/
│   └── byteport/
│       ├── main.go                # Entry point: Gin server, OTel, auth init
│       ├── smoke_test.go          # Minimum floor test (FR-CI-FLOOR)
│       ├── go.mod / go.sum        # Go module dependencies
│       ├── lib/                   # Core business logic
│       │   ├── auth.go           # PASETO token generation/validation
│       │   ├── crypto.go         # AES-256 encryption, Argon2id hashing
│       │   ├── git.go            # GitHub OAuth, token refresh job
│       │   ├── apilink.go        # AWS/AI/Portfolio credential validation + SSRF protection
│       │   └── index.go          # Package exports documentation
│       ├── models/                # GORM data models
│       │   ├── users.go          # User, AwsCreds, LLM, Portfolio, Git
│       │   ├── projects.go       # Project with deployments map
│       │   ├── instances.go      # Instance with AWS resources
│       │   ├── repositories.go  # GitHub Repository/Owner/Permissions
│       │   ├── secrets.go        # GitSecret (app credentials)
│       │   ├── data.go          # Database connection, GORM automigrate
│       │   └── types.go         # NVMS, Service, BuildPack, AWSConfig
│       └── routes/               # Gin HTTP handlers
│           ├── auth.go           # /signup, /login, /authenticate, /link, /user/:id/creds
│           ├── deployment.go     # /deploy, /terminate
│           ├── git.go            # /api/github/callback, /api/github/repositories
│           ├── projects.go       # /projects
│           ├── instances.go      # /instances
│           └── pm.go             # Project model helpers
├── frontend/
│   └── web/                      # SvelteKit 2 application
│       ├── src/                  # Svelte components + routes
│       └── src-tauri/           # Tauri 2 desktop shell (Rust)
├── nvms/                         # NVMS deployment service (Go, port 3000)
│   └── ...                      # MicroVM/Firecracker deployment logic
├── start                         # Dev orchestration script (tmux)
├── golangci.yml                 # golangci-lint configuration
└── justfile                     # Just task runner
```

---

## 3. Data Models

### User

```go
type User struct {
    UUID     string    `gorm:"type:text;primaryKey"`
    Name     string    `gorm:"not null"`
    Email    string    `gorm:"unique;not null"`
    Password string    `gorm:"not null"`        // Argon2id hash
    AwsCreds AwsCreds  `gorm:"embedded;embeddedPrefix:aws_"`
    LLMConfig LLM      `gorm:"embedded;embeddedPrefix:llm_"`
    Portfolio Portfolio `gorm:"embedded;embeddedPrefix:portfolio_"`
    Git      Git       `gorm:"embedded;embeddedPrefix:git_"`
    Projects []Project `gorm:"foreignKey:Owner;references:UUID"`
    Instances []Instance `gorm:"foreignKey:Owner;references:UUID"`
}

type AwsCreds struct {
    AccessKeyID     string `gorm:"column:access_key_id"`      // AES-256 encrypted
    SecretAccessKey string `gorm:"column:secret_access_key"`  // AES-256 encrypted
}

type LLM struct {
    Provider  string                  `json:"provider"`            // "openai", "local"
    Providers map[string]AIProvider  `gorm:"serializer:json"`
}

type AIProvider struct {
    Modal  string `json:"modal"`  // e.g. "gpt-4o"
    APIKey string `json:"api_key"` // AES-256 encrypted
}

type Portfolio struct {
    RootEndpoint string `gorm:"column:root_endpoint"`  // AES-256 encrypted
    APIKey       string `gorm:"column:api_key"`        // AES-256 encrypted
}

type Git struct {
    Token              string    `gorm:"column:access_token"`          // AES-256 encrypted
    RefreshToken       string    `gorm:"column:refresh_token"`          // AES-256 encrypted
    TokenExpiry        time.Time `gorm:"column:token_expiry"`
    RefreshTokenExpiry time.Time `gorm:"column:refresh_token_expiry"`
}
```

### Project

```go
type Project struct {
    gorm.Model
    UUID            string     `gorm:"type:text;primaryKey"`
    ID              string     `gorm:"type:text;primaryKey;not null"`
    Owner           string     `gorm:"type:text;not null;index"`
    Name            string     `gorm:"type:text;not null"`
    RepositoryID    string     `gorm:"type:text;index"`
    Repository      Repository `gorm:"foreignKey:RepositoryID;references:ID"`
    Readme          string     `gorm:"type:text"`
    Description     string     `gorm:"type:text"`
    LastUpdated     time.Time  `gorm:"autoUpdateTime"`
    Platform        string     `gorm:"type:text"`
    AccessURL       string     `gorm:"type:text"`
    Type            string     `gorm:"type:text"`
    DeploymentsJSON string     `gorm:"type:jsonb;column:deployments"`
    deployments     map[string]Instance `gorm:"-"`  // deserialized from JSON
}
```

### Instance

```go
type Instance struct {
    UUID          string         `gorm:"type:text;primaryKey"`
    Owner         string        `gorm:"type:text;not null;index"`
    Name          string        `gorm:"not null"`
    Status        string        `gorm:"not null"`
    ResUUID       string        `gorm:"not null"`
    ResourcesJSON string         `gorm:"type:jsonb;column:resources"`
    Resources     []AWSResource  `gorm:"foreignKey:InstanceID;references:UUID"`
}
```

### NVMS Types

```go
type NVMS struct {
    ID          string    `gorm:"primaryKey;type:uuid"`
    Name        string    `gorm:"type:text;not null"`
    Description string    `gorm:"type:text"`
    Services    []Service `gorm:"serializer:json"`
}

type Service struct {
    ID          string            `gorm:"primaryKey;type:uuid"`
    Name        string            `gorm:"type:text;not null"`
    Path        string            `gorm:"type:text;not null"`
    Port        int              `gorm:"type:integer;not null"`
    Build       []string         `gorm:"serializer:json"`
    Env         map[string]string `gorm:"serializer:json"`
    BuildPackID string           `gorm:"type:uuid;index"`
    BuildPack   *BuildPack       `gorm:"foreignKey:BuildPackID"`
    Runtime     string           `gorm:"type:text"`
}

type BuildPack struct {
    ID              string            `gorm:"primaryKey;type:uuid"`
    DetectFiles     []string         `gorm:"serializer:json"`
    Packages        []string         `gorm:"serializer:json"`
    PreBuild        []string         `gorm:"serializer:json"`
    Build           []string         `gorm:"serializer:json"`
    Start           string           `gorm:"type:text"`
    RuntimeVersions map[string]string `gorm:"serializer:json"`
    EnvVars         map[string]string `gorm:"serializer:json"`
}

type AWSConfig struct {
    ID       string              `gorm:"primaryKey;type:uuid"`
    Region   string              `gorm:"type:text;not null"`
    Services []AWSServiceConfig  `gorm:"serializer:json"`
}

type AWSResource struct {
    InstanceID          string    `gorm:"primaryKey;type:uuid"`
    Type        string    `gorm:"type:text;not null;index"`
    Name        string    `gorm:"type:text;not null"`
    ARN         string    `gorm:"type:text"`
    Status      string    `gorm:"type:text"`
    Region      string    `gorm:"type:text"`
    Service     string    `gorm:"type:text;index"`
    CreatedAt   time.Time `gorm:"autoCreateTime"`
    UpdatedAt   time.Time `gorm:"autoUpdateTime"`
}
```

---

## 4. API Endpoints

### Public (no auth required)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/login` | Authenticate user, set PASETO cookie |
| POST | `/signup` | Create new user, set PASETO cookie |
| GET | `/api/github/callback` | GitHub OAuth callback (OAuth flow redirect) |

### Protected (PASETO auth required)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/authenticate` | Validate token, return user object |
| GET | `/link` | Initiate GitHub OAuth redirect |
| POST | `/link` | Validate + save AWS/AI/Portfolio credentials |
| GET | `/instances` | List all instances for authenticated user |
| GET | `/projects` | List all projects for authenticated user |
| GET | `/api/github/repositories` | List user's GitHub repositories |
| POST | `/deploy` | Trigger deployment of a project |
| POST | `/terminate` | Terminate an instance |
| GET | `/user/:id/creds` | Get decrypted credentials for current user |
| PUT | `/user/:id/creds` | Update user profile (name, email, password) |

### Request/Response Examples

#### POST /signup

```json
// Request
{ "name": "Alice", "email": "alice@example.com", "password": "s3cr3t" }

// Response 201 Created
{
  "UUID": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Alice",
  "email": "alice@example.com"
}
```

#### POST /login

```json
// Request
{ "email": "alice@example.com", "password": "s3cr3t" }

// Response 200 OK — sets "authToken" cookie (httpOnly, 1hr)
{
  "message": "Success",
  "user": { "UUID": "...", "name": "Alice", "email": "alice@example.com" }
}
```

#### POST /deploy

```json
// Request
{
  "name": "my-app",
  "repository_id": "12345",
  "readme": "# My App\nA task management application...",
  "description": "Task management web app"
}

// Response 200 OK
{ "message": "Success" }
```

#### POST /link (credential validation)

```json
// Request — AWS + AI + Portfolio credentials
{
  "aws_access_key_id": "AKIA...",
  "aws_secret_access_key": "...",
  "openai_api_key": "sk-...",
  "portfolio_root_endpoint": "https://portfolio.example.com",
  "portfolio_api_key": "..."
}

// Response 200 OK
{ "message": "Credentials validated and saved successfully" }
```

#### GET /projects

```json
// Response 200 OK
[
  {
    "uuid": "...",
    "name": "my-app",
    "repository_id": "12345",
    "access_url": "http://...",
    "description": "Task management web app",
    "deployments": {
      "production": { "uuid": "...", "status": "running", "name": "vm-01" }
    }
  }
]
```

---

## 5. Security Model

### Credential Handling

1. **At rest**: All secrets (AWS keys, API keys, GitHub tokens) are AES-256-CFB encrypted before storage.
2. **Encryption key**: Auto-generated on first boot via `InitializeEncryptionKey()`, stored in `ENCRYPTION_KEY` env var. Persisted to `$HOME/.zshrc` via `PersistEncryptionKey()`.
3. **Passwords**: Hashed with Argon2id (memory=64MiB, iterations=3, parallelism=2, salt=16B, key=32B).
4. **Session**: PASETO v2 tokens issued on login, stored in httpOnly cookies.
5. **GitHub tokens**: Auto-refreshed every 7h45m via `StartTokenRefreshJob()` background goroutine.

### SSRF Protection

Portfolio API validation uses `ssrfSafePortfolioClient()` which:
- Validates host is public IP (unless allowlisted via `BYTEPORT_PORTFOLIO_API_ALLOWED_HOSTS`)
- Rejects loopback, private, link-local, multicast addresses
- Resolves DNS and validates resolved IPs are public
- Enforces redirect host validation to prevent response header injection

### AWS Credentials Validation

Validated by creating an STS session and calling `s3.ListBuckets`. Fails fast on bad credentials.

### OpenAI Credentials Validation

Validated by calling `GET /v1/models` with the bearer token. Fails fast on invalid API keys.

---

## 6. Functional Requirements

| ID | Requirement | Category |
|----|-------------|----------|
| FR-MANIFEST-001 | Parse BytePort/NVMS manifest file defining app structure and infra | IaC |
| FR-MANIFEST-002 | Validate manifest against schema, fail loudly on errors | IaC |
| FR-MANIFEST-003 | Support multiple services within a single manifest | IaC |
| FR-MANIFEST-004 | Each service includes name, runtime, port, source repo reference | IaC |
| FR-DEPLOY-001 | Provision AWS infrastructure described in manifest | Deploy |
| FR-DEPLOY-002 | Resources visible in AWS console after successful deploy | Deploy |
| FR-DEPLOY-003 | Pull application source from specified GitHub repository | Deploy |
| FR-DEPLOY-004 | Use the branch or ref specified in manifest | Deploy |
| FR-DEPLOY-005 | Output live endpoint URLs on successful deployment | Deploy |
| FR-DEPLOY-006 | Report per-service deployment status | Deploy |
| FR-PORTFOLIO-001 | Generate portfolio site component templates | Portfolio |
| FR-PORTFOLIO-002 | Templates include live endpoint URLs | Portfolio |
| FR-PORTFOLIO-003 | Templates provide UI widgets for project interaction | Portfolio |
| FR-PORTFOLIO-004 | LLM-assisted text generation for descriptions | Portfolio |
| FR-PORTFOLIO-005 | Support OpenAI and local LLM backends | Portfolio |
| FR-CLI-001 | `byteport deploy` triggers full pipeline | CLI |
| FR-CLI-002 | `byteport status` displays per-service health and endpoints | CLI |
| FR-CLI-003 | All CLI errors print to stderr and exit non-zero | CLI |
| FR-CLI-004 | AWS credentials read from env vars or `~/.aws/credentials` | CLI |

---

## 7. Quality Gates

| Gate | Command | Requirement |
|------|---------|-------------|
| Build | `go build ./backend/...` | 0 errors |
| Vet | `go vet ./backend/...` | 0 warnings |
| Test | `go test ./backend/...` | all pass |
| Lint | `golangci-lint run` | 0 errors |
| Tauri | `cargo test` (src-tauri) | all pass |

CI workflows: `ci.yml` (pytest), `go-ci.yml` (go vet+build), `cargo-audit.yml`, `cargo-deny.yml`, `cargo-semver-checks.yml`, `codeql.yml`, `fr-coverage.yml`, `quality-gate.yml`.

---

## 8. NVMS Manifest Format

```yaml
# odin.nvms — BytePort IaC manifest
NAME: my-app
DESCRIPTION: A task management web application

SERVICES:
  - NAME: "main"          # Required — public-facing service
    PATH: "./frontend"
    PORT: 8080
    RUNTIME: "nodejs"
    BUILD: ["npm install", "npm run build"]
    ENV:
      API_URL: "http://localhost:8081"

  - NAME: "backend"
    PATH: "./backend"
    PORT: 8081
    RUNTIME: "go"
    BUILD: ["go build -o server ./cmd/server"]
    ENV:
      DATABASE_URL: "postgres://localhost/myapp"

INFRASTRUCTURE:
  compute: ec2           # or ecs, lambda
  region: us-east-1
  instance_type: t3.micro

PORTFOLIO:
  generate_page: true
  description_source: llm  # or readme, manual
```

---

## 9. Dependencies

### Go (`backend/byteport/go.mod`)

| Package | Purpose |
|---------|---------|
| `github.com/gin-gonic/gin` | HTTP framework |
| `github.com/gin-contrib/cors` | CORS middleware |
| `gorm.io/gorm` | ORM |
| `gorm.io/driver/sqlite` | SQLite driver |
| `github.com/o1egl/paseto` | PASETO token generation/validation |
| `github.com/google/uuid` | UUID generation |
| `golang.org/x/crypto/argon2` | Argon2id password hashing |
| `github.com/aws/aws-sdk-go` | AWS SDK |
| `go.opentelemetry.io/otel` | OpenTelemetry |
| `go.opentelemetry.io/contrib/instrumentation/github.com/gin-gonic/gin/otelgin` | Gin OTel middleware |

### Rust (`frontend/web/src-tauri/Cargo.toml`)

| Crate | Purpose |
|-------|---------|
| `tauri` | Desktop/mobile shell |
| `tauri-plugin-*` | Tauri plugins (shell, fs, etc.) |

---

## 9.1. Integration Points

- `pheno-otel` — OpenTelemetry tracing for Go backend and Tauri shell
- `pheno-schema` — Zod schemas for API validation and data model contracts
- `pheno-utils` — Shared Go utility functions for crypto, auth, and HTTP helpers

## 9.2. Design Decisions

- **Go backend + SvelteKit frontend**: Go provides efficient, concurrent backend handling; SvelteKit offers lightweight reactive frontend with minimal bundle overhead.
- **AES-256-CFB + Argon2id for credential encryption**: Defense-in-depth for secrets at rest; symmetric encryption with derived keys for zero-trust credential storage.
- **PASETO over JWT for session tokens**: PASETO v2 eliminates JWT's known attack vectors (algorithm confusion, weak signatures) and is easier to reason about.

## 10. Status

- **Last Updated**: 2026-05-06
- **Spec Status**: Current — reflects actual shipping implementation
- **Canonical Stack**: Go/Gin/GORM/SQLite/PASETO/SvelteKit/Tauri 2
- **Outdated**: All prior references to Rust/Loco.rs/NanoVMS have been retired
