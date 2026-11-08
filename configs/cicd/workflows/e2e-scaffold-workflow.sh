#!/usr/bin/env bash
#===============================================================================
# E2E Microservice Scaffolding Workflow
#
# Purpose: Generate new microservices from templates with xDD patterns
#
# Usage: ./e2e-scaffold-workflow.sh --name SERVICE_NAME --lang LANG [--output DIR]
#        LANG: go, rust, typescript, python
#
# Dependencies: git, curl (optional for template fetching)
#===============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SERVICE_NAME=""
LANGUAGE=""
OUTPUT_DIR=""
TEMPLATE_BASE="/Users/<REDACTED>/CodeProjects/Phenotype/repos/template-commons"
BASE_PATH="/Users/<REDACTED>/CodeProjects/Phenotype/repos"

# Supported languages
SUPPORTED_LANGS=("go" "rust" "typescript" "python")

#-------------------------------------------------------------------------------
# Logging
#-------------------------------------------------------------------------------
log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

#-------------------------------------------------------------------------------
# Parse Arguments
#-------------------------------------------------------------------------------
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --name)
                SERVICE_NAME="$2"
                shift 2
                ;;
            --lang)
                LANGUAGE="$2"
                shift 2
                ;;
            --output)
                OUTPUT_DIR="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Validation
    if [[ -z "$SERVICE_NAME" ]]; then
        log_error "--name is required"
        exit 1
    fi

    if [[ -z "$LANGUAGE" ]]; then
        log_error "--lang is required"
        exit 1
    fi

    if [[ ! " ${SUPPORTED_LANGS[*]} " =~ " ${LANGUAGE} " ]]; then
        log_error "Unsupported language: $LANGUAGE"
        log_error "Supported: ${SUPPORTED_LANGS[*]}"
        exit 1
    fi

    # Default output directory
    if [[ -z "$OUTPUT_DIR" ]]; then
        OUTPUT_DIR="$BASE_PATH"
    fi
}

#-------------------------------------------------------------------------------
# Scaffold Functions
#-------------------------------------------------------------------------------

scaffold_go() {
    local output="$OUTPUT_DIR/$SERVICE_NAME"

    log_info "Scaffolding Go microservice: $SERVICE_NAME"

    # Create directory
    mkdir -p "$output"

    # Copy template
    cp -r "$TEMPLATE_BASE/microservice-scaffold/go/"* "$output/"

    # Update module name
    local module_name="github.com/org/$SERVICE_NAME"
    find "$output" -name "*.go" -exec sed -i "s|github.com/org/microservice|$module_name|g" {} \;
    find "$output" -name "go.mod" -exec sed -i "s|github.com/org/microservice|$module_name|g" {} \;

    log_success "Go microservice scaffolded at: $output"
}

scaffold_python() {
    local output="$OUTPUT_DIR/$SERVICE_NAME"

    log_info "Scaffolding Python microservice: $SERVICE_NAME"

    # Create directory
    mkdir -p "$output"

    # Copy template
    cp -r "$TEMPLATE_BASE/microservice-scaffold/python/"* "$output/"

    # Update package name
    find "$output" -name "*.py" -exec sed -i "s|name = \"microservice\"|name = \"$SERVICE_NAME\"|g" {} \;

    log_success "Python microservice scaffolded at: $output"
}

scaffold_rust() {
    local output="$OUTPUT_DIR/$SERVICE_NAME"

    log_info "Scaffolding Rust microservice: $SERVICE_NAME"

    # Create directory
    mkdir -p "$output"

    # Copy template
    cp -r "$TEMPLATE_BASE/clean-rust/"* "$output/"

    # Update Cargo.toml
    sed -i "s|name = \"clean-rust\"|name = \"$SERVICE_NAME\"|g" "$output/Cargo.toml"

    log_success "Rust microservice scaffolded at: $output"
}

scaffold_typescript() {
    local output="$OUTPUT_DIR/$SERVICE_NAME"

    log_info "Scaffolding TypeScript microservice: $SERVICE_NAME"

    # Create directory
    mkdir -p "$output"

    # Copy template
    cp -r "$TEMPLATE_BASE/plugin-typescript/"* "$output/"

    # Update package.json
    sed -i "s|\"name\": \"@agileplus/plugin-typescript\"|\"name\": \"@agileplus/$SERVICE_NAME\"|g" "$output/package.json"

    log_success "TypeScript microservice scaffolded at: $output"
}

#-------------------------------------------------------------------------------
# Git Initialization
#-------------------------------------------------------------------------------
init_git() {
    local output="$OUTPUT_DIR/$SERVICE_NAME"

    log_info "Initializing git repository..."

    cd "$output"
    git init
    git add .
    git commit -m "feat: initial scaffold from template-commons

- Added hexagonal/clean architecture structure
- Added CQRS pattern (commands + queries)
- Added ports and adapters
- Added observability (logging, metrics, tracing)
- Added xDD methodology documentation"

    log_success "Git repository initialized"
}

#-------------------------------------------------------------------------------
# Generate README
#-------------------------------------------------------------------------------
generate_readme() {
    local output="$OUTPUT_DIR/$SERVICE_NAME"

    cat > "$output/README.md" << EOF
# $SERVICE_NAME

A microservice built with hexagonal/clean architecture.

## Architecture

```
$SERVICE_NAME/
├── domain/           # Core business logic (no dependencies)
│   ├── entities/     # Domain models
│   ├── ports/        # Interface definitions
│   └── services/     # Domain services
├── application/      # Application layer
│   ├── commands/     # Write operations (CQRS)
│   └── queries/      # Read operations (CQRS)
├── infrastructure/    # Infrastructure layer
│   └── adapters/     # Database, cache, messaging
└── interfaces/       # API handlers
```

## xDD Methodologies Applied

- **TDD**: Test-driven development
- **BDD**: Behavior-driven development
- **CQRS**: Command Query Responsibility Segregation
- **Hexagonal**: Ports & Adapters architecture
- **SOLID**: Single responsibility, open/closed, etc.

## Getting Started

\`\`\`bash
# Install dependencies
cd $SERVICE_NAME

# Run tests
make test

# Run locally
make run

# Build Docker
make docker-build
\`\`\`

## Observability

- Structured logging
- Prometheus metrics
- OpenTelemetry tracing

## See Also

- [xDD Methodologies Reference](https://github.com/KooshaPari/template-commons)
- [Hexagonal Architecture](https://alistair.cockburn.us/hexagonal-architecture/)
EOF

    log_success "README generated"
}

#-------------------------------------------------------------------------------
# Summary
#-------------------------------------------------------------------------------
print_summary() {
    local output="$OUTPUT_DIR/$SERVICE_NAME"

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Microservice Scaffolding Complete!${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "  Service: $SERVICE_NAME"
    echo "  Language: $LANGUAGE"
    echo "  Location: $output"
    echo ""
    echo "  Next steps:"
    echo "    cd $output"
    echo "    # Edit configuration"
    echo "    # Add domain logic"
    echo "    # Run tests"
    echo "    make test"
    echo ""
    echo "  xDD Patterns Applied:"
    echo "    - Hexagonal/Ports & Adapters"
    echo "    - CQRS (Commands + Queries)"
    echo "    - SOLID Principles"
    echo "    - Domain-Driven Design"
    echo "    - Test-Driven Development"
    echo ""
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

main() {
    parse_args "$@"

    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║           E2E Microservice Scaffolding Workflow                  ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""

    log_info "Service name: $SERVICE_NAME"
    log_info "Language: $LANGUAGE"
    log_info "Output: $OUTPUT_DIR/$SERVICE_NAME"
    echo ""

    # Scaffold based on language
    case "$LANGUAGE" in
        go)
            scaffold_go
            ;;
        rust)
            scaffold_rust
            ;;
        typescript)
            scaffold_typescript
            ;;
        python)
            scaffold_python
            ;;
    esac

    # Generate documentation
    generate_readme

    # Initialize git
    init_git

    # Print summary
    print_summary
}

main "$@"
