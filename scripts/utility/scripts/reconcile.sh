#!/bin/bash
# reconcile.sh - Verify cross-repo consistency against governance contracts
#
# Usage: ./scripts/reconcile.sh [OPTIONS]
#   -r, --repos REPO_LIST    Comma-separated list of repos to check
#   -c, --check-only         Report-only mode (no fixes applied)
#   -v, --verbose            Enable verbose output
#   -h, --help               Show this help message

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
RULES_FILE="${REPO_ROOT}/contracts/reconcile.rules.yaml"
TEMPLATES_DIR="${REPO_ROOT}/templates"

CHECK_ONLY=false
VERBOSE=false
TARGET_REPOS=""
PHENOTYPE_ROOT="/Users/<REDACTED>/CodeProjects/Phenotype/repos"

# Counters for reporting
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $*"
}

log_success() {
    echo -e "${GREEN}✓${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $*"
}

log_error() {
    echo -e "${RED}✗${NC} $*"
}

log_verbose() {
    if [[ "$VERBOSE" == true ]]; then
        echo -e "${BLUE}→${NC} $*"
    fi
}

# Show help message
show_help() {
    grep '^# ' "$0" | sed 's/^# //' | head -20
    exit 0
}

# Parse command-line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -r|--repos)
                TARGET_REPOS="$2"
                shift 2
                ;;
            -c|--check-only)
                CHECK_ONLY=true
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            -h|--help)
                show_help
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# Check if a file exists
check_file_exists() {
    local repo_path=$1
    local file_path=$2

    if [[ -f "${repo_path}/${file_path}" ]]; then
        log_verbose "Found: ${file_path}"
        return 0
    else
        log_verbose "Missing: ${file_path}"
        return 1
    fi
}

# Compare file against template using diff
check_file_diff() {
    local repo_path=$1
    local file_path=$2
    local template_path=$3

    if [[ ! -f "${repo_path}/${file_path}" ]]; then
        log_verbose "File missing: ${file_path}"
        return 1
    fi

    if [[ ! -f "${template_path}" ]]; then
        log_warning "Template not found: ${template_path}"
        return 1
    fi

    # Create temp diff output
    local diff_output
    diff_output=$(diff -u "${template_path}" "${repo_path}/${file_path}" 2>&1 || true)

    if [[ -z "$diff_output" ]]; then
        log_verbose "Content matches template: ${file_path}"
        return 0
    else
        log_verbose "Content diverges from template: ${file_path}"
        if [[ "$VERBOSE" == true ]]; then
            echo "$diff_output" | head -10
        fi
        return 1
    fi
}

# Check governance file requirements
check_governance_files() {
    local repo_name=$1
    local repo_path=$2

    log_info "Checking governance files for ${repo_name}..."

    # Parse YAML to extract required files (simple extraction)
    local required_files=("AGENTS.md" "CLAUDE.md" "SECURITY.md" ".gitignore")

    for file in "${required_files[@]}"; do
        ((TOTAL_CHECKS++))

        if check_file_exists "$repo_path" "$file"; then
            ((PASSED_CHECKS++))
            log_success "${repo_name}: ${file} exists"
        else
            ((FAILED_CHECKS++))
            log_error "${repo_name}: ${file} missing"
        fi
    done

    # Check for template divergence
    for file in "AGENTS.md" "CLAUDE.md"; do
        ((TOTAL_CHECKS++))

        local template="${TEMPLATES_DIR}/${file}"
        if check_file_diff "$repo_path" "$file" "$template"; then
            ((PASSED_CHECKS++))
            log_success "${repo_name}: ${file} matches template"
        else
            ((FAILED_CHECKS++))
            log_warning "${repo_name}: ${file} diverges from template (acceptable if customized)"
        fi
    done
}

# Check CI/CD workflow requirements
check_ci_workflows() {
    local repo_name=$1
    local repo_path=$2

    log_info "Checking CI/CD workflows for ${repo_name}..."

    local workflows_dir="${repo_path}/.github/workflows"

    if [[ ! -d "$workflows_dir" ]]; then
        ((TOTAL_CHECKS++))
        ((FAILED_CHECKS++))
        log_error "${repo_name}: .github/workflows directory missing"
        return 1
    fi

    # Check for required workflow files
    local required_workflows=("policy-gate" "lint-test")

    for workflow in "${required_workflows[@]}"; do
        ((TOTAL_CHECKS++))

        # Look for workflow file matching pattern
        local workflow_file
        workflow_file=$(find "$workflows_dir" -name "*${workflow}*.yml" -o -name "*${workflow}*.yaml" 2>/dev/null | head -1)

        if [[ -n "$workflow_file" ]]; then
            # Check if it uses composite action from phenotypeActions
            # Match patterns like: uses: phenotypeActions/actions/policy-gate
            # or phenotypeActions/actions/policy-gate@v1, etc
            if grep -qE "(phenotypeActions/actions/${workflow}|uses:.*phenotypeActions.*${workflow})" "$workflow_file" 2>/dev/null; then
                ((PASSED_CHECKS++))
                log_success "${repo_name}: ${workflow} workflow references composite action"
            else
                ((FAILED_CHECKS++))
                log_warning "${repo_name}: ${workflow} workflow exists but may not reference composite action from phenotypeActions"
            fi
        else
            ((FAILED_CHECKS++))
            log_error "${repo_name}: ${workflow} workflow not found"
        fi
    done
}

# Check code quality standards
check_code_quality() {
    local repo_name=$1
    local repo_path=$2

    log_info "Checking code quality standards for ${repo_name}..."

    # Detect language and check appropriate linters
    local has_go=false
    local has_py=false
    local has_ts=false
    local has_rust=false

    [[ -f "${repo_path}/go.mod" ]] && has_go=true
    [[ -f "${repo_path}/pyproject.toml" ]] || [[ -f "${repo_path}/setup.py" ]] && has_py=true
    [[ -f "${repo_path}/package.json" ]] && has_ts=true
    [[ -f "${repo_path}/Cargo.toml" ]] && has_rust=true

    ((TOTAL_CHECKS++))

    if [[ "$has_go" == true ]]; then
        if [[ -f "${repo_path}/.golangci.yml" ]]; then
            ((PASSED_CHECKS++))
            log_success "${repo_name}: Go linter config found"
        else
            ((FAILED_CHECKS++))
            log_warning "${repo_name}: Go project but no .golangci.yml"
        fi
    fi

    ((TOTAL_CHECKS++))
    if [[ "$has_py" == true ]]; then
        if [[ -f "${repo_path}/pyproject.toml" ]]; then
            ((PASSED_CHECKS++))
            log_success "${repo_name}: Python project configured"
        else
            ((FAILED_CHECKS++))
            log_warning "${repo_name}: Python project but no pyproject.toml"
        fi
    fi

    ((TOTAL_CHECKS++))
    if [[ "$has_ts" == true ]]; then
        if [[ -f "${repo_path}/tsconfig.json" ]]; then
            ((PASSED_CHECKS++))
            log_success "${repo_name}: TypeScript configured"
        else
            ((FAILED_CHECKS++))
            log_warning "${repo_name}: TypeScript project but no tsconfig.json"
        fi
    fi
}

# Check directory structure
check_directory_structure() {
    local repo_name=$1
    local repo_path=$2

    log_info "Checking directory structure for ${repo_name}..."

    local required_dirs=("docs" ".github/workflows")

    for dir in "${required_dirs[@]}"; do
        ((TOTAL_CHECKS++))

        if [[ -d "${repo_path}/${dir}" ]]; then
            ((PASSED_CHECKS++))
            log_success "${repo_name}: ${dir}/ exists"
        else
            ((FAILED_CHECKS++))
            log_warning "${repo_name}: ${dir}/ not found (may be optional)"
        fi
    done
}

# Process a single repository
process_repo() {
    local repo_name=$1
    local repo_path=$2

    echo ""
    log_info "═══════════════════════════════════════════════"
    log_info "Reconciling: ${repo_name}"
    log_info "Path: ${repo_path}"
    log_info "═══════════════════════════════════════════════"

    if [[ ! -d "$repo_path" ]]; then
        log_error "Repository not found: ${repo_path}"
        return 1
    fi

    # Run all checks
    check_governance_files "$repo_name" "$repo_path"
    check_ci_workflows "$repo_name" "$repo_path"
    check_code_quality "$repo_name" "$repo_path"
    check_directory_structure "$repo_name" "$repo_path"
}

# Main execution
main() {
    parse_args "$@"

    echo ""
    log_info "Template Commons Contract Reconciliation Tool"
    log_info "Rules file: ${RULES_FILE}"
    echo ""

    # Discover repositories to check
    local repos_to_check=()

    if [[ -n "$TARGET_REPOS" ]]; then
        # Parse comma-separated repo list
        IFS=',' read -ra repos_array <<< "$TARGET_REPOS"
        for repo_name in "${repos_array[@]}"; do
            repo_name=$(echo "$repo_name" | xargs)  # Trim whitespace
            repos_to_check+=("$repo_name")
        done
    else
        # Discover all repos in Phenotype/repos (excluding template-commons itself and wtree directories)
        if [[ -d "$PHENOTYPE_ROOT" ]]; then
            while IFS= read -r repo_path; do
                local repo_name
                repo_name=$(basename "$repo_path")
                # Exclude: template-commons, wtree dirs, and non-git dirs
                if [[ "$repo_name" != "template-commons" && "$repo_name" != *"-wtrees" && -d "${repo_path}/.git" ]]; then
                    repos_to_check+=("$repo_name")
                fi
            done < <(find "$PHENOTYPE_ROOT" -maxdepth 1 -type d ! -name '.*' 2>/dev/null)
        fi
    fi

    if [[ ${#repos_to_check[@]} -eq 0 ]]; then
        log_warning "No repositories found to check"
        exit 0
    fi

    # Process each repository
    for repo_name in "${repos_to_check[@]}"; do
        repo_path="${PHENOTYPE_ROOT}/${repo_name}"

        if [[ -d "$repo_path" ]]; then
            process_repo "$repo_name" "$repo_path"
        else
            log_warning "Repository directory not found: ${repo_path}"
        fi
    done

    # Print summary
    echo ""
    echo "═══════════════════════════════════════════════"
    log_info "Reconciliation Summary"
    echo "═══════════════════════════════════════════════"
    echo "Total Checks:  $TOTAL_CHECKS"
    echo -e "Passed:        ${GREEN}${PASSED_CHECKS}${NC}"
    echo -e "Failed:        ${RED}${FAILED_CHECKS}${NC}"

    local pass_rate=0
    if [[ $TOTAL_CHECKS -gt 0 ]]; then
        pass_rate=$((PASSED_CHECKS * 100 / TOTAL_CHECKS))
    fi
    echo "Pass Rate:     ${pass_rate}%"
    echo ""

    if [[ $FAILED_CHECKS -eq 0 ]]; then
        log_success "All checks passed!"
        exit 0
    else
        log_warning "${FAILED_CHECKS} check(s) failed"
        if [[ "$CHECK_ONLY" == true ]]; then
            log_info "Use without --check-only to apply fixes"
        fi
        exit 1
    fi
}

main "$@"
