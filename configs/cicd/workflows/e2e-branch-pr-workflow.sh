#!/usr/bin/env bash
#===============================================================================
# E2E Branch & PR Management Workflow
#
# Purpose: Scan all phenotype repos, find branches needing attention,
#          create/merge PRs, and clean up stale worktrees
#
# Usage: ./e2e-branch-pr-workflow.sh [--dry-run] [--repo PATTERN]
#
# Dependencies: gh, git, jq
#===============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DRY_RUN=false
REPO_PATTERN=""
BASE_PATH="/Users/<REDACTED>/CodeProjects/Phenotype/repos"
PHENOTYPE_REPOS=(
    "AgilePlus"
    "agileplus-publish"
    "phenotype-design"
    "phenotype-go-kit"
    "phenotype-skills-clone"
    "phench"
    "phenodocs"
)

#-------------------------------------------------------------------------------
# Functions
#-------------------------------------------------------------------------------

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# Parse arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --repo)
                REPO_PATTERN="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
}

# Check dependencies
check_deps() {
    local deps=("gh" "git" "jq")
    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "Required dependency not found: $dep"
            exit 1
        fi
    done
}

# Get repos to process
get_repos() {
    if [[ -n "$REPO_PATTERN" ]]; then
        for repo in "${PHENOTYPE_REPOS[@]}"; do
            if [[ "$repo" == *"$REPO_PATTERN"* ]]; then
                echo "$repo"
            fi
        done
    else
        for repo in "${PHENOTYPE_REPOS[@]}"; do
            echo "$repo"
        done
    fi
}

# Check if worktree has unpushed commits
check_worktree_status() {
    local worktree_path="$1"
    local branch
    branch=$(cd "$worktree_path" && git branch --show-current 2>/dev/null || echo "detached")

    if [[ "$branch" == "detached" ]]; then
        return 1
    fi

    # Check if ahead of origin/main
    local ahead
    ahead=$(cd "$worktree_path" && git log origin/main..HEAD --oneline 2>/dev/null | wc -l)

    if [[ "$ahead" -gt 0 ]]; then
        echo "AHEAD:$ahead:$branch"
    fi
}

# Scan a single repo
scan_repo() {
    local repo="$1"
    local repo_path="$BASE_PATH/$repo"

    if [[ ! -d "$repo_path/.git" ]]; then
        log_warn "Skipping $repo - not found or not a git repo"
        return
    fi

    log_info "Scanning $repo..."

    # Check main branch
    local main_ahead
    main_ahead=$(cd "$repo_path" && git log origin/main..HEAD --oneline 2>/dev/null | wc -l)

    if [[ "$main_ahead" -gt 0 ]]; then
        log_warn "$repo main is $main_ahead commits ahead of origin/main"
    fi

    # Check open PRs
    local open_prs
    open_prs=$(gh pr list --repo "<REDACTED>/$repo" --state open --json number,title --json number,title 2>/dev/null | jq 'length' 2>/dev/null || echo "0")

    if [[ "$open_prs" -gt 0 ]]; then
        log_info "  Open PRs: $open_prs"
        gh pr list --repo "<REDACTED>/$repo" --state open --json number,title,headRefName 2>/dev/null | jq -r '.[] | "    #\(.number): \(.title) [\( .headRefName)]"'
    fi

    # Check worktrees
    local worktree_count
    worktree_count=$(cd "$repo_path" && git worktree list 2>/dev/null | wc -l)

    if [[ "$worktree_count" -gt 1 ]]; then
        log_info "  Worktrees: $worktree_count"

        # Find worktrees with unpushed commits
        while IFS= read -r wt; do
            local wt_path
            wt_path=$(echo "$wt" | awk '{print $2}')

            if [[ -n "$wt_path" && -d "$wt_path/.git" ]]; then
                local status
                status=$(check_worktree_status "$wt_path")

                if [[ -n "$status" ]]; then
                    local ahead branch
                    IFS=':' read -r _ ahead branch <<< "$status"
                    log_warn "  Worktree $wt_path: $branch ($ahead ahead)"
                fi
            fi
        done < <(cd "$repo_path" && git worktree list --porcelain 2>/dev/null | grep -A1 "^worktree" | grep -v "^worktree")
    fi
}

# Create PR for branch
create_pr() {
    local repo="$1"
    local branch="$2"
    local title="$3"
    local description="${4:-}"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would create PR for $repo:$branch"
        return
    fi

    # Check if PR already exists
    local existing_pr
    existing_pr=$(gh pr list --repo "<REDACTED>/$repo" --head "$branch" --json number --json number 2>/dev/null | jq '.[0].number' 2>/dev/null || echo "null")

    if [[ "$existing_pr" != "null" ]]; then
        log_warn "PR already exists for $branch: #$existing_pr"
        return
    fi

    # Push branch if needed
    cd "$BASE_PATH/$repo"
    git push origin "$branch" 2>&1 | head -3

    # Create PR
    gh pr create \
        --repo "<REDACTED>/$repo" \
        --title "$title" \
        --body "$description" \
        --base main \
        --head "$branch" 2>&1
}

# Merge PR
merge_pr() {
    local repo="$1"
    local pr_number="$2"
    local method="${3:-squash}"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would merge PR #$pr_number in $repo"
        return
    fi

    gh pr merge "$pr_number" --"$method" --delete-branch --auto 2>&1 || \
    log_warn "Failed to merge PR #$pr_number (may need manual review)"
}

# Close PR
close_pr() {
    local repo="$1"
    local pr_number="$2"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would close PR #$pr_number in $repo"
        return
    fi

    gh pr close "$pr_number" 2>&1
}

# Remove stale worktree
remove_worktree() {
    local repo="$1"
    local worktree_path="$2"
    local branch="$3"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would remove worktree $worktree_path"
        return
    fi

    log_info "Removing stale worktree: $worktree_path"
    cd "$BASE_PATH/$repo"
    git worktree remove "$worktree_path" --force 2>&1 || \
    log_warn "Failed to remove worktree $worktree_path"
}

# Generate PR description
generate_pr_desc() {
    local branch="$1"
    local commits="$2"

    cat << EOF
## Summary

Automated PR from E2E workflow.

## Changes

$(echo "$commits" | head -10 | sed 's/^/- /')

## Checklist

- [ ] Tests pass
- [ ] Code follows project standards
- [ ] Documentation updated (if needed)
- [ ] No merge conflicts
EOF
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

main() {
    parse_args "$@"
    check_deps

    log_info "E2E Branch & PR Management Workflow"
    log_info "Dry run: $DRY_RUN"
    echo ""

    for repo in $(get_repos); do
        scan_repo "$repo"
        echo ""
    done

    log_success "Scan complete!"
    log_info "Review the output above for branches needing attention."
    log_info "Run with --dry-run to preview actions without making changes."
}

main "$@"
