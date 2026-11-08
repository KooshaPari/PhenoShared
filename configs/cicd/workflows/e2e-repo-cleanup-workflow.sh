#!/usr/bin/env bash
#===============================================================================
# E2E Repository Cleanup Workflow
#
# Purpose: Clean up merged branches, stale worktrees, and optimize repos
#
# Usage: ./e2e-repo-cleanup-workflow.sh [--dry-run] [--repo REPO]
#
# Dependencies: gh, git, jq
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
DRY_RUN=false
REPO=""
BASE_PATH="/Users/<REDACTED>/CodeProjects/Phenotype/repos"

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

#-------------------------------------------------------------------------------
# Logging
#-------------------------------------------------------------------------------
log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }
log_section() { echo -e "\n${CYAN}==== $* ====${NC}"; }

#-------------------------------------------------------------------------------
# Parse Arguments
#-------------------------------------------------------------------------------
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --repo)
                REPO="$2"
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
# Dependency Check
#-------------------------------------------------------------------------------
check_deps() {
    for dep in gh git jq; do
        if ! command -v "$dep" &> /dev/null; then
            log_error "Missing dependency: $dep"
            exit 1
        fi
    done
}

#-------------------------------------------------------------------------------
# Get Repos
#-------------------------------------------------------------------------------
get_repos() {
    if [[ -n "$REPO" ]]; then
        echo "$REPO"
    else
        printf '%s\n' "${ALL_REPOS[@]}"
    fi
}

#-------------------------------------------------------------------------------
# Cleanup Functions
#-------------------------------------------------------------------------------

# Delete merged local branches
cleanup_merged_branches() {
    local repo="$1"
    local repo_path="$BASE_PATH/$repo"

    log_section "Cleaning merged branches in $repo"

    cd "$repo_path" || return

    # Fetch and prune
    git fetch origin --prune 2>/dev/null || true

    # Find merged branches (exclude main and protected)
    local merged
    merged=$(git branch --merged origin/main 2>/dev/null | grep -v "^\*" | grep -v "main" | grep -v "master" | grep -v "develop" || true)

    if [[ -z "$merged" ]]; then
        log_info "No merged branches to delete"
        return
    fi

    echo "$merged" | while read -r branch; do
        branch=$(echo "$branch" | xargs)
        if [[ -z "$branch" ]]; then
            continue
        fi

        if [[ "$DRY_RUN" == true ]]; then
            log_info "[DRY-RUN] Would delete branch: $branch"
        else
            log_info "Deleting branch: $branch"
            git branch -d "$branch" 2>/dev/null || true
        fi
    done
}

# Delete merged remote branches
cleanup_merged_remote_branches() {
    local repo="$1"

    log_section "Cleaning merged remote branches for $repo"

    # Get merged branches
    local merged
    merged=$(gh api repos/<REDACTED>/"$repo"/branches --jq '.[] | select(.merged) | .name' 2>/dev/null | grep -v "main" || true)

    if [[ -z "$merged" ]]; then
        log_info "No merged remote branches"
        return
    fi

    echo "$merged" | while read -r branch; do
        if [[ -z "$branch" ]]; then
            continue
        fi

        if [[ "$DRY_RUN" == true ]]; then
            log_info "[DRY-RUN] Would delete remote branch: $branch"
        else
            log_info "Deleting remote branch: $branch"
            gh api -X DELETE repos/<REDACTED>/"$repo"/branches/"$branch" 2>/dev/null || true
        fi
    done
}

# Remove stale worktrees
cleanup_worktrees() {
    local repo="$1"
    local repo_path="$BASE_PATH/$repo"

    log_section "Checking worktrees in $repo"

    cd "$repo_path" || return

    local worktree_count
    worktree_count=$(git worktree list 2>/dev/null | wc -l)

    if [[ "$worktree_count" -le 1 ]]; then
        log_info "No additional worktrees"
        return
    fi

    # List worktrees
    log_info "Worktrees:"
    git worktree list --porcelain 2>/dev/null | grep "^worktree" | awk '{print "  - " $2}' | while read -r wt; do
        echo "$wt"
    done
}

# Prune git reflog
prune_reflog() {
    local repo="$1"
    local repo_path="$BASE_PATH/$repo"

    log_section "Pruning reflog in $repo"

    cd "$repo_path" || return

    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would prune reflog"
    else
        git reflog expire --expire=now --all 2>/dev/null || true
        git gc --prune=now --aggressive 2>/dev/null || true
        log_success "Pruned reflog and ran gc"
    fi
}

# Clean untracked files
clean_untracked() {
    local repo="$1"
    local repo_path="$BASE_PATH/$repo"

    log_section "Cleaning untracked files in $repo"

    cd "$repo_path" || return

    # List untracked
    local untracked
    untracked=$(git status --porcelain | grep "^??" | awk '{print $2}' | head -20 || true)

    if [[ -z "$untracked" ]]; then
        log_info "No untracked files"
        return
    fi

    local count
    count=$(echo "$untracked" | wc -l)
    log_info "Found $count untracked files/directories"

    if [[ "$DRY_RUN" == true ]]; then
        echo "$untracked" | head -10 | while read -r f; do
            log_info "[DRY-RUN] Would remove: $f"
        done
    else
        echo "$untracked" | xargs rm -rf 2>/dev/null || true
        log_success "Removed untracked files"
    fi
}

# Sync with remote
sync_with_remote() {
    local repo="$1"
    local repo_path="$BASE_PATH/$repo"

    log_section "Syncing $repo with remote"

    cd "$repo_path" || return

    # Check current branch
    local branch
    branch=$(git branch --show-current)

    if [[ "$branch" != "main" ]]; then
        log_warn "Not on main branch (on $branch), skipping sync"
        return
    fi

    # Fetch and reset
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would fetch and reset to origin/main"
    else
        git fetch origin 2>/dev/null || true
        git reset --hard origin/main 2>/dev/null || true
        log_success "Synced with origin/main"
    fi
}

#-------------------------------------------------------------------------------
# Status Report
#-------------------------------------------------------------------------------

report_repo_status() {
    local repo="$1"
    local repo_path="$BASE_PATH/$repo"

    if [[ ! -d "$repo_path/.git" ]]; then
        log_warn "$repo not found"
        return
    fi

    cd "$repo_path" || return

    # Fetch latest
    git fetch origin --prune 2>/dev/null || true

    # Branch status
    local ahead behind
    ahead=$(git rev-list --left-right --count HEAD...origin/main 2>/dev/null | awk '{print $2}')
    behind=$(git rev-list --left-right --count HEAD...origin/main 2>/dev/null | awk '{print $1}')

    if [[ "$ahead" == "0" && "$behind" == "0" ]]; then
        log_success "$repo: Up to date with origin/main"
    elif [[ "$ahead" -gt 0 ]]; then
        log_warn "$repo: $ahead commits ahead, $behind behind"
    else
        log_info "$repo: $behind commits behind origin/main"
    fi

    # Worktree count
    local wt_count
    wt_count=$(git worktree list 2>/dev/null | wc -l)
    if [[ "$wt_count" -gt 1 ]]; then
        log_info "  Worktrees: $wt_count"
    fi

    # Open PRs
    local open_prs
    open_prs=$(gh pr list --repo "<REDACTED>/$repo" --state open 2>/dev/null | wc -l || echo "0")
    if [[ "$open_prs" -gt 0 ]]; then
        log_info "  Open PRs: $open_prs"
    fi
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

main() {
    parse_args "$@"
    check_deps

    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║        E2E Repository Cleanup Workflow                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    log_info "Dry run: $DRY_RUN"
    echo ""

    for repo in $(get_repos); do
        log_section "Processing: $repo"

        # Status report
        report_repo_status "$repo"

        # Cleanup tasks
        cleanup_merged_branches "$repo"
        cleanup_merged_remote_branches "$repo"
        cleanup_worktrees "$repo"
        clean_untracked "$repo"
        prune_reflog "$repo"

        echo ""
    done

    log_success "Cleanup complete!"

    if [[ "$DRY_RUN" == true ]]; then
        log_info "This was a dry run. Run without --dry-run to apply changes."
    fi
}

main "$@"
