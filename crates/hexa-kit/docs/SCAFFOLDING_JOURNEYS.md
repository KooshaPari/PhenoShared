# HexaKit Scaffolding Journeys

__Version:__ 1.0  
__Status:__ Active  
__Updated:__ 2026-04-04  
__Domain:__ Project Scaffolding and Template Usage

---

## Table of Contents

1. [Overview](#overview)
2. [Journey 1: Creating Your First Project from Template](#journey-1-creating-your-first-project-from-template)
3. [Journey 2: Contributing a New Template to HexaKit](#journey-2-contributing-a-new-template-to-hexakit)
4. [Journey 3: Updating Projects When Templates Evolve](#journey-3-updating-projects-when-templates-evolve)
5. [Journey 4: Composing Multi-Language Projects](#journey-4-composing-multi-language-projects)
6. [Journey 5: Customizing Templates with Policy Overrides](#journey-5-customizing-templates-with-policy-overrides)
7. [Design Principles](#design-principles)

---

## Overview

These journeys describe the primary workflows for using and contributing to HexaKit's scaffolding system. Each journey targets a specific persona and use case, providing step-by-step guidance through the template ecosystem.

### Audience

- **Developers**: Creating new projects from templates
- **Template Authors**: Contributing new templates to HexaKit
- **Platform Engineers**: Managing template governance and policies
- **AI Agents**: Generating projects autonomously via MCP

### Template Ecosystem

HexaKit provides templates across multiple languages and project types:

| Template | Language | Use Case | Status |
|----------|----------|----------|--------|
| `template-rust` | Rust | Services, CLIs, libraries | Active |
| `template-typescript` | TypeScript | Web apps, Node libraries | Active |
| `template-python` | Python | Packages, services | Active |
| `template-go` | Go | Microservices, CLIs | Active |
| `template-lang-rust` | Rust | Language-specific extensions | Active |
| `template-lang-typescript` | TypeScript | TS language extensions | Active |
| `template-domain-service-api` | Multi | API services | Active |
| `template-domain-webapp` | Multi | Web applications | Active |
| `template-program-ops` | Multi | Operations tooling | Active |

---

## Journey 1: Creating Your First Project from Template

**Persona**: Developer new to HexaKit  
**Goal**: Create a production-ready Rust service project in under 5 minutes  
**Time**: 5 minutes

### Preconditions

- HexaKit CLI installed (`cargo install hexakit` or `brew install hexakit`)
- Git configured (for template cloning)
- Rust toolchain installed (for Rust templates)
- Network access (initial clone only, full offline thereafter)

### Steps

#### 1. List Available Templates

```bash
$ hexakit template list

Available Templates:
┌─────────────────────────┬────────────────────────────────────┬─────────┐
│ Name                    │ Description                        │ Lang    │
├─────────────────────────┼────────────────────────────────────┼─────────┤
│ template-rust           │ Rust HTTP service (Axum)           │ Rust    │
│ template-typescript      │ TypeScript web application         │ TS/Node │
│ template-python         │ Python package (uv)               │ Python  │
│ template-go             │ Go microservice                    │ Go      │
│ template-domain-api     │ Multi-language API service         │ Mixed   │
└─────────────────────────┴────────────────────────────────────┴─────────┘

Use: hexakit new --template &lt;name&gt;
```

#### 2. Initialize New Project

```bash
$ hexakit new --template template-rust

✨ Creating project from template-rust

Project Configuration:
? Project name: my-awesome-api
  Help: Use kebab-case (my-project)
  
? Crate name: my_awesome_api
  Help: Use snake_case (my_crate)
  Auto-derived from: my-awesome-api
  
? Description: A high-performance Rust API service
  Help: Brief description for Cargo.toml
  
? Features to include (select all that apply):
  ◉ http      → HTTP server (Axum)
  ◉ grpc      → gRPC server
  ◉ sqlite    → SQLite storage
  ◉ redis     → Redis caching
  ◉ metrics   → Prometheus metrics
  ◯ tracing   → Distributed tracing
  ◯ jwt       → JWT authentication

Selected: [http, sqlite, metrics]

? Author name: Koosha Pari
  Help: For Cargo.toml metadata
  Default: Koosha Pari (from Git config)
  
? License: MIT
  Help: See https://choosealicense.com
  Default: MIT
  
📦 Generating project structure...
✓ Created my-awesome-api/
✓ Created Cargo.toml
✓ Created src/main.rs
✓ Created src/domain/mod.rs
✓ Created src/ports/mod.rs
✓ Created src/adapters/mod.rs
✓ Created tests/integration_tests.rs
✓ Created .github/workflows/ci.yml
✓ Created .pre-commit-config.yaml
✓ Created rustfmt.toml
✓ Created clippy.toml
✓ Created README.md

🔧 Running post-generation tasks...
✓ Executed cargo fetch
✓ Executed cargo check
✓ Executed git init
✓ Initial commit created

🎉 Project created successfully!

Next steps:
  cd my-awesome-api
  cargo build
  cargo test
  cargo run
```

#### 3. Explore Generated Structure

```bash
$ cd my-awesome-api
$ tree -L 3

my-awesome-api/
├── Cargo.toml
├── Cargo.lock
├── LICENSE
├── README.md
├── rustfmt.toml
├── clippy.toml
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── .pre-commit-config.yaml
├── src/
│   ├── main.rs
│   ├── lib.rs
│   ├── domain/
│   │   ├── mod.rs
│   │   └── entities.rs
│   ├── ports/
│   │   ├── mod.rs
│   │   ├── http.rs
│   │   └── storage.rs
│   └── adapters/
│       ├── mod.rs
│       ├── http.rs
│       └── sqlite.rs
└── tests/
    └── integration_tests.rs
```

#### 4. Run Quality Checks

```bash
$ cargo fmt --check
$ cargo clippy -- -D warnings
$ cargo test --workspace
$ cargo audit
```

### Post-Conditions

- Project compiles without errors
- All quality gates pass (fmt, clippy, tests, audit)
- Git repository initialized with initial commit
- Documentation complete (README, source comments)

### Success Criteria

| Criterion | Target | Verification |
|-----------|--------|-------------|
| Project compiles | < 60 seconds | `cargo build` |
| Tests pass | 100% | `cargo test` |
| Clippy clean | 0 warnings | `cargo clippy` |
| Format check | Pass | `cargo fmt --check` |
| Audit clean | 0 vulnerabilities | `cargo audit` |

---

## Journey 2: Contributing a New Template to HexaKit

**Persona**: Template Author / Platform Engineer  
**Goal**: Add a new Kotlin template to the HexaKit ecosystem  
**Time**: 2-4 hours

### Preconditions

- Write access to HexaKit repository
- Familiarity with Kotlin and Gradle/Kotlin DSL
- Understanding of hexagonal architecture
- Knowledge of target project type (library vs application)

### Steps

#### 1. Create Template Directory

```bash
$ cd HexaKit
$ mkdir -p template-lang-kotlin
$ cd template-lang-kotlin
```

#### 2. Create Template Manifest

Create `.template.yml`:

```yaml
name: template-lang-kotlin
description: Kotlin library/CLI template with hexagonal architecture

version: 1.0.0

languages:
  - Kotlin 1.9+

package_managers:
  - Gradle Kotlin DSL
  - Maven (optional)

variables:
  - name: project_name
    prompt: "Project name (kebab-case)"
    pattern: "^[a-z][a-z0-9-]*$"
    required: true
    examples:
      - my-library
      - cli-tool

  - name: package_name
    prompt: "Package name (domain.style)"
    pattern: "^[a-z][a-z0-9.]*[a-z0-9]$"
    required: true
    examples:
      - com.example.mylibrary
      - io.platform.tool

  - name: description
    prompt: "Project description"
    default: "A Kotlin library"
    max_length: 280

  - name: project_type
    prompt: "Project type"
    type: select
    options:
      - library: "Library (publishable)"
      - cli: "CLI application"
      - service: "Ktor service"
    default: library

  - name: features
    prompt: "Features"
    type: multiselect
    options:
      - coroutines: "Kotlin Coroutines"
      - serialization: "Kotlin Serialization"
      - arrow: "Arrow FX functional"
      - ktor: "Ktor HTTP server"
      - clikt: "Clikt CLI framework"
    default: [coroutines, serialization]

conditionals:
  - when: project_type == "library"
    include:
      - build.gradle.kts
      - src/commonMain/
      - src/jvmTest/
    exclude:
      - src/main/Application.kt

  - when: project_type == "cli"
    include:
      - build-cli.gradle.kts
      - src/main/Application.kt
      - src/main/Cli.kt
    exclude:
      - src/commonMain/

  - when: project_type == "service"
    include:
      - build-service.gradle.kts
      - src/main/Application.kt
      - src/main/Server.kt
      - src/main/routes/
    exclude:
      - build-cli.gradle.kts

policies:
  - id: kotlin-quality
    rules:
      - id: ktlint-check
        severity: error
      - id: detekt-check
        severity: error
      - id: test-coverage
        min_percent: 80

post_generation:
  - command: ./gradlew build
  - command: ./gradlew ktlintCheck
  - command: ./gradlew detekt

validation:
  - type: gradle_check
  - type: ktlint_check
  - type: detekt_check
```

#### 3. Create Template Files

Create the directory structure and template files:

```bash
$ mkdir -p src/main/kotlin/&#123;&#123;package_path}}/domain/entities
$ mkdir -p src/main/kotlin/&#123;&#123;package_path}}/domain/ports
$ mkdir -p src/main/kotlin/&#123;&#123;package_path}}/adapters
$ mkdir -p src/test/kotlin/&#123;&#123;package_path}}
$ mkdir -p gradle/wrapper
$ mkdir -p .github/workflows
```

#### 4. Create Template Source Files

`build.gradle.kts`:
```kotlin
plugins {
    kotlin("multiplatform") version "2.0.0"
    kotlin("plugin.serialization") version "2.0.0"
    id("org.jetbrains.kotlinx.kotest") version "5.8.0"
}

group = "&#123;&#123;package_name}}"
version = "0.1.0"

kotlin {
    jvm {
        withJava()
        testRuns["test"].executionTask.configure {
            useJUnitPlatform()
        }
    }
    
    sourceSets {
        val commonMain by getting {
            dependencies {
                implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.8.0")
                implementation("org.jetbrains.kotlinx:kotlinx-serialization-json:1.6.0")
            }
        }
        
        val commonTest by getting {
            dependencies {
                implementation(kotlin("test"))
                implementation("io.kotest:kotest-property:5.8.0")
            }
        }
    }
}

tasks.withType&lt;Test&gt; {
    useJUnitPlatform()
}
```

`src/main/kotlin/&#123;&#123;package_path}}/domain/entities/Entity.kt`:
```kotlin
package &#123;&#123;package_name}}.domain.entities

public data class Entity(
    val id: String,
    val name: String,
    val createdAt: Instant = Clock.System.now(),
    val updatedAt: Instant = Clock.System.now()
) {
    public fun rename(newName: String): Entity = copy(
        name = newName,
        updatedAt = Clock.System.now()
    )
}
```

#### 5. Create GitHub Actions Workflow

`.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
      
      - name: Setup Gradle
        uses: gradle/gradle-build-action@v2
      
      - name: Run checks
        run: ./gradlew check
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

#### 6. Test Template Locally

```bash
$ hexakit new --template ./template-lang-kotlin --name test-kotlin-lib --dry-run

# Review generated output without creating files

$ hexakit new --template ./template-lang-kotlin --name test-kotlin-lib

# Create actual project
```

#### 7. Validate Template

```bash
$ hexakit template validate --path ./template-lang-kotlin

Validating template-lang-kotlin...

✓ Manifest parsed successfully
✓ Variables schema valid
✓ Conditionals syntactically correct
✓ Template files found: 12
✓ Template files parse: 12
✓ Git repository clean

Validation complete: 0 errors, 0 warnings
```

#### 8. Submit for Review

```bash
$ git checkout -b feat/template-kotlin
$ git add template-lang-kotlin/
$ git commit -m "feat(templates): add Kotlin language template

Adds template-lang-kotlin with:
- Kotlin Multiplatform support
- Gradle Kotlin DSL
- Hexagonal architecture structure
- Ktlint and Detekt quality gates
- Coroutines and Serialization by default"

$ git push -u origin feat/template-kotlin
$ gh pr create --title "feat(templates): add Kotlin language template" \
    --body "## Summary
- Adds new Kotlin template following hexagonal architecture
- Supports library, CLI, and Ktor service project types
- Includes Ktlint/Detekt quality gates
- Multiplatform ready (JVM, JS, Native)

## Testing
- Validated locally with dry-run
- Generated test project compiles
- All quality gates pass"
```

### Post-Conditions

- Template added to HexaKit repository
- CI validates template on every push
- Template documented in HexaKit README
- Template follows all governance policies

### Success Criteria

| Criterion | Target | Verification |
|-----------|--------|-------------|
| Template validates | 0 errors | `hexakit template validate` |
| Generates project | Success | `hexakit new --dry-run` |
| Quality gates | Pass | CI pipeline |
| Documentation | Complete | README + .template.yml |
| Policy compliant | 100% | Policy check |

---

## Journey 3: Updating Projects When Templates Evolve

**Persona**: Developer with existing project  
**Goal**: Apply template improvements to an existing project without losing customizations  
**Time**: 15-30 minutes

### Preconditions

- Existing project created from HexaKit template
- Template has been updated since project creation
- Local changes (if any) committed or stashed

### Steps

#### 1. Check for Template Updates

```bash
$ cd my-awesome-api
$ hexakit update check

Checking for template updates...

Template: template-rust
  Current version: 1.0.0
  Latest version: 1.2.0
  Status: UPDATE AVAILABLE

Available changes:
  ✦ v1.1.0: Add Prometheus metrics endpoint
  ✦ v1.2.0: Add OpenTelemetry tracing support

Run `hexakit update diff` to see detailed changes.
```

#### 2. View Update Diff

```bash
$ hexakit update diff --to v1.2.0

Comparing template-rust v1.0.0 → v1.2.0

Files changed:
┌─────────────────────────────────────────────────────────────────┐
│ File                  │ Change Type │ Description              │
├─────────────────────────────────────────────────────────────────┤
│ src/main.rs           │ Modified    │ Added tracing setup      │
│ src/adapters/http.rs  │ Modified    │ Added /metrics endpoint  │
│ .github/workflows/   │ Modified    │ Added coverage job       │
│ .pre-commit-config    │ Modified    │ Added trivy security    │
└─────────────────────────────────────────────────────────────────┘

Breaking changes:
⚠ src/main.rs: Tracing initialization changed
  Before: init_tracing()
  After:  TracingBuilder::new().init()
  
  Manual action required: Update custom tracing configuration

Non-breaking changes:
+ src/adapters/metrics.rs: NEW FILE
+ .github/workflows/ci.yml: Added codecov step
+ .pre-commit-config.yaml: Added trivy hook
```

#### 3. Apply Non-Breaking Updates

```bash
$ hexakit update apply --mode safe

Applying safe updates from template-rust v1.1.0...

Applying: src/adapters/metrics.rs (NEW)
  ✓ Created src/adapters/metrics.rs

Applying: .github/workflows/ci.yml (MODIFIED)
  ✓ Added coverage job

Applying: .pre-commit-config.yaml (MODIFIED)
  ✓ Added trivy hook

Skipping (requires manual review):
  ⚠ src/main.rs (BREAKING CHANGE)
  ⚠ src/adapters/http.rs (BREAKING CHANGE)

Update complete.
  3 files updated
  2 files require manual review

Next steps:
  hexakit update review  # Review manual changes
  git status            # Review all changes
```

#### 4. Review and Handle Breaking Changes

```bash
$ hexakit update review

Breaking Change: src/main.rs

Current template version:
------------------
fn main() {
    init_tracing();
    // ...
}

New template version:
------------------
fn main() {
    TracingBuilder::new()
        .with_service_name(env!("CARGO_PKG_NAME"))
        .init();
    // ...
}

Options:
  [1] Accept new version (replace file)
  [2] Keep current version (skip update)
  [3] Merge manually (open editor)

Select option: 3

# Editor opens with merge view
# User manually resolves conflicts
```

#### 5. Verify Updated Project

```bash
$ cargo build
  Building my-awesome-api v0.1.0
  ✓ Compiled successfully

$ cargo test --workspace
  Running 12 tests
  ✓ All tests passed

$ cargo clippy -- -D warnings
  ✓ No warnings

$ hexakit update status
  ✓ Project up to date with template-rust v1.2.0
```

### Post-Conditions

- Project updated to latest template version
- Breaking changes reviewed and resolved
- All quality gates still pass
- Customizations preserved where possible

### Success Criteria

| Criterion | Target | Verification |
|-----------|--------|-------------|
| Template version | Latest | `hexakit update status` |
| Tests pass | 100% | `cargo test` |
| Build succeeds | Yes | `cargo build` |
| Customizations | Preserved | `git diff` |
| Quality gates | Pass | CI pipeline |

---

## Journey 4: Composing Multi-Language Projects

**Persona**: Platform Engineer / Architect  
**Goal**: Create a multi-language microservice with Rust backend and TypeScript frontend  
**Time**: 20 minutes

### Preconditions

- HexaKit with multi-language templates
- Understanding of service composition
- Network access for template fetching

### Steps

#### 1. Create Multi-Language Project

```bash
$ hexakit new --template template-domain-service-api --name my-fullstack-api

✨ Creating fullstack API project

? Project name: my-fullstack-api
  Description: Fullstack API with Rust backend and TS frontend

? Backend language: Rust
  Options: Rust, Go, Python

? Frontend language: TypeScript
  Options: TypeScript

? Include database: Yes (SQLite)
? Include cache: Yes (Redis)
? Include monitoring: Yes (Prometheus)

📦 Generating project structure...
✓ Created my-fullstack-api/
✓ Created backend/
│   └── (template-rust contents)
✓ Created frontend/
│   └── (template-typescript contents)
✓ Created docker-compose.yml
✓ Created Makefile

🎉 Project created successfully!
```

#### 2. Explore Generated Structure

```bash
$ tree my-fullstack-api -L 3

my-fullstack-api/
├── backend/
│   ├── Cargo.toml
│   ├── src/
│   │   ├── main.rs
│   │   ├── domain/
│   │   ├── ports/
│   │   └── adapters/
│   └── .github/workflows/
│       └── ci.yml
├── frontend/
│   ├── package.json
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── api/
│   └── .github/workflows/
│       └── ci.yml
├── docker-compose.yml
├── Makefile
├── README.md
└── SPEC.md
```

#### 3. Build Both Components

```bash
$ cd my-fullstack-api
$ make build

Building backend...
  ✓ cargo build --manifest-path backend/Cargo.toml

Building frontend...
  ✓ bun install
  ✓ bun run build

Build complete!
```

#### 4. Run Integrated Services

```bash
$ make up

Starting services...
✓ Redis started (localhost:6379)
✓ Backend started (localhost:8080)
✓ Frontend started (localhost:3000)

Services ready:
  API: http://localhost:8080
  Frontend: http://localhost:3000
  Metrics: http://localhost:8080/metrics
```

### Post-Conditions

- Backend and frontend both build successfully
- Services communicate correctly
- Local development workflow functional
- CI/CD configured for both components

---

## Journey 5: Customizing Templates with Policy Overrides

**Persona**: Security Officer / Platform Engineer  
**Goal**: Apply organizational security policies to all generated projects  
**Time**: 30 minutes setup, automatic thereafter

### Preconditions

- Access to organizational policy definitions
- Understanding of policy YAML format
- Write access to organization-wide HexaKit config

### Steps

#### 1. Define Organizational Policies

Create `~/.hexakit/policies/security.yaml`:

```yaml
name: org-security-baseline
description: Organizational security baseline for all projects
version: "1.0"

rules:
  - id: no-hardcoded-secrets
    severity: error
    description: "No hardcoded secrets in source code"
    patterns:
      - "password\s*=\s*['\"][^'\"]+['\"]"
      - "api[_-]?key\s*=\s*['\"][^'\"]+['\"]"
      - "secret\s*=\s*['\"][^'\"]+['\"]"
    fix: "Use environment variables or secrets management"

  - id: require-tls
    severity: error
    description: "TLS must be configured for network services"
    applies_to:
      - "**/*server*.rs"
      - "**/*server*.go"
      - "**/*.py" # with flask/etc
    check: presence of TLS configuration

  - id: secure-headers
    severity: warning
    description: "HTTP responses should include security headers"
    applies_to:
      - "**/*handler*.rs"
      - "**/*middleware*.ts"
    headers:
      - "Strict-Transport-Security"
      - "X-Content-Type-Options: nosniff"
      - "X-Frame-Options: DENY"

  - id: input-validation
    severity: error
    description: "All external input must be validated"
    applies_to:
      - "**/*handler*.rs"
      - "**/*endpoint*.py"
      - "**/*route*.ts"
    check: presence of validation logic
```

#### 2. Configure Global Policy

Create `~/.hexakit/config.yaml`:

```yaml
organization:
  name: Acme Corp
  policies:
    - path: ~/.hexakit/policies/security.yaml
      required: true
    - path: ~/.hexakit/policies/quality.yaml
      required: true
    - path: ~/.hexakit/policies/observability.yaml
      required: false

template_overrides:
  allowed:
    - template-rust
    - template-typescript
    - template-python
  blocked:
    - template-unverified

generation:
  audit: true
  policy_strict: true
```

#### 3. Verify Policy on Generation

```bash
$ hexakit new --template template-rust --name secure-service

Applying organizational policies...
✓ security.yaml: applied
✓ quality.yaml: applied
✓ observability.yaml: available (optional)

Policy check results:
  ✓ No hardcoded secrets: passed
  ✓ TLS configuration: passed (no network server)
  ✓ Secure headers: n/a (no HTTP handlers yet)
  ✓ Input validation: n/a (no handlers yet)

Generation complete with policy compliance.
```

#### 4. Policy Violation Handling

```bash
$ hexakit new --template template-rust --name insecure-service

⚠️ Policy violation detected!

Policy: security-baseline
Rule: no-hardcoded-secrets
Severity: ERROR
File: src/main.rs:15
Content: database_url = "postgres://user:password123@localhost/db"

Options:
  [1] Abort generation
  [2] Generate with violations (flagged)
  [3] Override (requires justification)

Select option: 2

Generation complete with WARNINGS.
  - 1 policy violation(s)
  - Violations flagged in .hexakit/violations.yaml

Project created but NOT compliant with security baseline.
```

### Post-Conditions

- All generated projects inherit organizational policies
- Policy violations block or flag generation appropriately
- Audit trail maintained for policy decisions
- Policies enforced at CI time as well

### Success Criteria

| Criterion | Target | Verification |
|-----------|--------|-------------|
| Policy inheritance | 100% | Check new projects |
| Violation detection | Real-time | Test with violations |
| CI enforcement | Yes | CI pipeline checks |
| Audit trail | Complete | `.hexakit/audit/` |

---

## Design Principles

### Journey Design Philosophy

Each journey follows consistent design principles:

1. **Progressive Disclosure**: Simple paths first, advanced options available
2. **Safe Defaults**: Sensible defaults reduce cognitive load
3. **Clear Feedback**: Immediate, actionable feedback at each step
4. **Reversibility**: Easy to undo or restart
5. **Observability**: Clear progress indicators

### Quality Gates

All journeys end with quality gate verification:

```bash
# Standard quality gate check
hexakit quality gate --project my-project

Checking quality gates...
  ✓ Format check (cargo fmt)
  ✓ Lint check (cargo clippy)
  ✓ Test suite (cargo test)
  ✓ Security scan (cargo audit)
  ✓ Policy compliance (hexakit policy check)
  
Quality gate: PASSED (5/5)
```

### Error Handling

Common error scenarios with recovery guidance:

| Error | Cause | Recovery |
|-------|-------|----------|
| Template not found | Invalid template name | `hexakit template list` |
| Variable validation | Invalid input format | Retry with correct format |
| Generation failure | Disk space / permissions | Free space, check permissions |
| Policy violation | Non-compliant code | Review and fix, or override |

---

__Document Owner:__ HexaKit Team  
__Last Updated:__ 2026-04-04  
__Status:__ Active — Journeys added as templates evolve
