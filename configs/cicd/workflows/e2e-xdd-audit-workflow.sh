#!/usr/bin/env bash
#===============================================================================
# E2E xDD Architecture Audit Workflow
#
# Purpose: Audit repositories for xDD architecture compliance,
#          identify improvements, and generate refactoring recommendations
#
# Usage: ./e2e-xdd-audit-workflow.sh [--repo REPO] [--format json|md|text]
#
# Dependencies: gh, git, jq, fd, ripgrep
#===============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Configuration
REPO=""
FORMAT="text"
BASE_PATH="/Users/<REDACTED>/CodeProjects/Phenotype/repos"
OUTPUT_FILE=""

# All phenotype repos
ALL_REPOS=(
    "AgilePlus"
    "agileplus-publish"
    "phenotype-design"
    "phenotype-go-kit"
    "phenotype-skills-clone"
    "phench"
    "phenodocs"
)

# Architecture patterns to check
ARCH_PATTERNS=(
    "hexagonal|ports.*adapters|domain.*driven"
    "clean.*architecture|layered.*architecture"
    "cqrs|command.*query.*segregation"
    "event.*sourcing"
    "saga.*pattern|choreography"
)

# Anti-patterns (things to avoid)
ANTI_PATTERNS=(
    "god.*class|big.*ball.*mud"
    "circular.*dependency|circular.*import"
    "shared.*database|coupling"
    "magic.*numbers|magic.*strings"
)

#-------------------------------------------------------------------------------
# Logging
#-------------------------------------------------------------------------------
log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[PASS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $*"; }
log_section() { echo -e "\n${CYAN}==== $* ====${NC}"; }

#-------------------------------------------------------------------------------
# Parse Arguments
#-------------------------------------------------------------------------------
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --repo)
                REPO="$2"
                shift 2
                ;;
            --format)
                FORMAT="$2"
                shift 2
                ;;
            --output)
                OUTPUT_FILE="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

#-------------------------------------------------------------------------------
# Audit Functions
#-------------------------------------------------------------------------------

# Check for hexagonal architecture indicators
audit_hexagonal() {
    local repo="$1"
    local repo_path="$BASE_PATH/$repo"
    local score=0
    local max_score=5

    log_section "Hexagonal Architecture Audit"

    # Check for domain layer
    if [[ -d "$repo_path/domain" ]] || [[ -d "$repo_path/internal/domain" ]]; then
        log_success "Domain layer exists"
        ((score++))
    else
        log_fail "No domain layer found"
    fi

    # Check for ports
    if grep -rq "interface\|trait\|protocol\|Port" "$repo_path" 2>/dev/null; then
        log_success "Ports/interfaces found"
        ((score++))
    else
        log_warn "No explicit ports found"
    fi

    # Check for adapters
    if grep -rq "adapter\|Adapter\|persistence\|repository" "$repo_path" 2>/dev/null; then
        log_success "Adapters found"
        ((score++))
    else
        log_warn "No adapters found"
    fi

    # Check for CQRS
    if grep -rq "command\|Command\|query\|Query" "$repo_path" 2>/dev/null; then
        log_success "CQRS pattern indicators found"
        ((score++))
    else
        log_warn "No CQRS pattern indicators"
    fi

    # Check for value objects
    if grep -rq "value.*object\|ValueObject\|immutable" "$repo_path" 2>/dev/null; then
        log_success "Value objects found"
        ((score++))
    else
        log_warn "No value objects found"
    fi

    local percentage=$((score * 100 / max_score))
    echo ""
    echo "Hexagonal Score: $score/$max_score ($percentage%)"

    if [[ $percentage -ge 80 ]]; then
        echo -e "${GREEN}Excellent hexagonal architecture${NC}"
    elif [[ $percentage -ge 60 ]]; then
        echo -e "${YELLOW}Good, but improvements possible${NC}"
    else
        echo -e "${RED}Needs significant refactoring${NC}"
    fi
}

# Check for SOLID principles compliance
audit_solid() {
    local repo="$1"
    local repo_path="$BASE_PATH/$repo"

    log_section "SOLID Principles Audit"

    # Single Responsibility - check for large files
    local large_files
    large_files=$(find "$repo_path" -name "*.go" -o -name "*.ts" -o -name "*.py" -o -name "*.rs" 2>/dev/null | xargs wc -l 2>/dev/null | sort -rn | head -5 || true)

    if [[ -n "$large_files" ]]; then
        log_info "Largest files:"
        echo "$large_files" | head -3 | while read -r line; do
            local size name
            size=$(echo "$line" | awk '{print $1}')
            name=$(echo "$line" | awk '{print $2}')
            if [[ $size -gt 500 ]]; then
                echo -e "  ${RED}$size lines: $name${NC}"
            else
                echo "  $size lines: $name"
            fi
        done
    fi

    # Dependency Inversion - check for interface usage
    local interfaces
    interfaces=$(find "$repo_path" -name "*.go" -exec grep -l "interface" {} \; 2>/dev/null | wc -l || echo "0")
    log_info "Files with interfaces: $interfaces"

    # Open/Closed - check for extensibility patterns
    local plugins
    plugins=$(find "$repo_path" -type d -name "plugins" -o -type d -name "extensions" 2>/dev/null | wc -l || echo "0")
    if [[ $plugins -gt 0 ]]; then
        log_success "Extensibility directories found"
    else
        log_warn "No extensibility directories"
    fi
}

# Check for testing practices
audit_testing() {
    local repo="$1"
    local repo_path="$BASE_PATH/$repo"

    log_section "Testing Practices Audit"

    # Check for test directories
    local test_dirs
    test_dirs=$(find "$repo_path" -type d \( -name "test*" -o -name "*test*" -o -name "__tests__" \) 2>/dev/null | wc -l || echo "0")
    log_info "Test directories: $test_dirs"

    # Check test coverage if available
    if [[ -f "$repo_path/coverage.xml" ]] || [[ -f "$repo_path/coverage/lcov.info" ]]; then
        log_success "Coverage reports found"
    else
        log_warn "No coverage reports found"
    fi

    # Check for BDD/TDD patterns
    local bdd_patterns
    bdd_patterns=$(grep -r "describe\|it\.\|Given\|When\|Then\|test\|Test" "$repo_path" 2>/dev/null | head -5 | wc -l || echo "0")
    log_info "Test patterns found: $bdd_patterns occurrences"
}

# Check for documentation
audit_documentation() {
    local repo="$1"
    local repo_path="$BASE_PATH/$repo"

    log_section "Documentation Audit"

    # Required docs
    local docs=("README.md" "CONTRIBUTING.md" "CHANGELOG.md")

    for doc in "${docs[@]}"; do
        if [[ -f "$repo_path/$doc" ]]; then
            log_success "$doc exists"
        else
            log_warn "$doc missing"
        fi
    done

    # Check for ADR
    if [[ -d "$repo_path/docs/adr" ]] || [[ -d "$repo_path/adr" ]]; then
        log_success "Architecture Decision Records found"
    else
        log_warn "No ADR directory found"
    fi

    # Check for API docs
    if grep -rq "swagger\|openapi\|api.*doc" "$repo_path" 2>/dev/null; then
        log_success "API documentation found"
    else
        log_warn "No API documentation found"
    fi
}

# Check for CI/CD
audit_cicd() {
    local repo="$1"
    local repo_path="$BASE_PATH/$repo"

    log_section "CI/CD Audit"

    # Check for workflows
    local workflows
    workflows=$(find "$repo_path" -type f \( -path "*github/workflows*" -o -path "*gitlab-ci*" -o -path "*.circleci*" \) 2>/dev/null | wc -l || echo "0")
    log_info "CI/CD workflow files: $workflows"

    if [[ $workflows -gt 0 ]]; then
        log_success "CI/CD configured"
    else
        log_warn "No CI/CD workflows found"
    fi

    # Check for docker
    if [[ -f "$repo_path/Dockerfile" ]] || [[ -f "$repo_path/docker-compose.yml" ]]; then
        log_success "Docker files found"
    else
        log_warn "No Docker files found"
    fi
}

# Check for observability
audit_observability() {
    local repo="$1"
    local repo_path="$BASE_PATH/$repo"

    log_section "Observability Audit"

    # Logging
    if grep -rq "log\|logger\|structlog\|zerolog\|pino\|winston" "$repo_path" 2>/dev/null; then
        log_success "Logging configured"
    else
        log_warn "No logging found"
    fi

    # Metrics
    if grep -rq "prometheus\|metrics\|datadog\|statsd" "$repo_path" 2>/dev/null; then
        log_success "Metrics configured"
    else
        log_warn "No metrics found"
    fi

    # Tracing
    if grep -rq "tracing\|opentelemetry\|jaeger\|zipkin" "$repo_path" 2>/dev/null; then
        log_success "Tracing configured"
    else
        log_warn "No tracing found"
    fi
}

# Generate recommendations
generate_recommendations() {
    local repo="$1"

    log_section "Recommendations for $repo"

    echo "Based on the audit, consider:"
    echo ""
    echo "1. Architecture:"
    echo "   - Extract domain logic to separate layer"
    echo "   - Define ports (interfaces) for external dependencies"
    echo "   - Implement adapters for database, cache, messaging"
    echo ""
    echo "2. Testing:"
    echo "   - Add unit tests for domain layer (>80%)"
    echo "   - Add integration tests for adapters"
    echo "   - Consider BDD with Given/When/Then"
    echo ""
    echo "3. Documentation:"
    echo "   - Add Architecture Decision Records (ADR)"
    echo "   - Document API with OpenAPI/Swagger"
    echo "   - Add runbooks for operations"
    echo ""
    echo "4. Observability:"
    echo "   - Add structured logging"
    echo "   - Add Prometheus metrics"
    echo "   - Add OpenTelemetry tracing"
}

#-------------------------------------------------------------------------------
# Report Generation
#-------------------------------------------------------------------------------

generate_summary_report() {
    local repo="$1"

    cat << EOF

╔══════════════════════════════════════════════════════════════════════╗
║                    xDD Architecture Audit Report                      ║
║                         Repository: $repo                           ║
╚══════════════════════════════════════════════════════════════════════╝

$(date)

EOF
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

main() {
    parse_args "$@"

    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║        E2E xDD Architecture Audit Workflow                 ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""

    local repos
    if [[ -n "$REPO" ]]; then
        repos=("$REPO")
    else
        repos=("${ALL_REPOS[@]}")
    fi

    for repo in "${repos[@]}"; do
        local repo_path="$BASE_PATH/$repo"

        if [[ ! -d "$repo_path/.git" ]]; then
            log_warn "Skipping $repo - not found"
            continue
        fi

        generate_summary_report "$repo"

        audit_hexagonal "$repo"
        audit_solid "$repo"
        audit_testing "$repo"
        audit_documentation "$repo"
        audit_cicd "$repo"
        audit_observability "$repo"
        generate_recommendations "$repo"

        echo ""
        echo "──────────────────────────────────────────────────────────────"
        echo ""
    done

    log_success "Audit complete!"
}

main "$@"
