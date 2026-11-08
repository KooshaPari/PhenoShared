#!/usr/bin/env python3
"""
Git-History Domain Evaluator

Evaluates a product's git repository against the git-history domain rubric criteria.
Each criterion corresponds to a commit message (with short SHA prefix).
The evaluator checks whether each commit exists in the product's repo.

Usage:
    python evaluators/git_history.py <product_name>
    python evaluators/git_history.py substrate
"""

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CRITERIA_PATH = PROJECT_ROOT / "scorecards" / "domain-expansion-git-history.json"
REPOS_DIR = PROJECT_ROOT / "repos"
SCORECARDS_DIR = PROJECT_ROOT / "scorecards"


def run_git(repo_path: Path, args: list[str]) -> str:
    """Run a git command and return stdout."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def parse_criterion_title(title: str) -> tuple[str, str]:
    """Extract (sha_prefix, message) from a criterion title.

    Titles look like: 'baf4b055 chore(governance): confirm shared CODEOWNERS template...'
    The SHA prefix is the first token (7-40 hex chars).
    """
    parts = title.split(" ", 1)
    if len(parts) == 2 and len(parts[0]) >= 7:
        sha_part = parts[0]
        # Validate it looks like a hex SHA prefix
        if all(c in "0123456789abcdef" for c in sha_part):
            return sha_part, parts[1]
    return "", title


def collect_git_metrics(repo_path: Path) -> dict:
    """Collect aggregate git metrics from a repo."""
    metrics = {}

    # Total commit count
    count_out = run_git(repo_path, ["rev-list", "--count", "--all"])
    metrics["total_commits"] = int(count_out) if count_out.isdigit() else 0

    # Unique contributors
    authors_out = run_git(repo_path, ["log", "--all", "--format=%aN <%aE>"])
    unique_authors = set(line.strip() for line in authors_out.splitlines() if line.strip())
    metrics["contributor_count"] = len(unique_authors)
    metrics["contributors"] = sorted(unique_authors)

    # Commit frequency: commits per day over repo lifetime
    first_commit = run_git(repo_path, ["log", "--all", "--reverse", "--format=%aI", "--max-count=1"])
    last_commit = run_git(repo_path, ["log", "--all", "--format=%aI", "--max-count=1"])
    if first_commit and last_commit:
        try:
            start = datetime.fromisoformat(first_commit)
            end = datetime.fromisoformat(last_commit)
            span_days = max((end - start).days, 1)
            metrics["repo_span_days"] = span_days
            metrics["commits_per_day"] = round(metrics["total_commits"] / span_days, 2)
        except ValueError:
            metrics["repo_span_days"] = 0
            metrics["commits_per_day"] = 0.0
    else:
        metrics["repo_span_days"] = 0
        metrics["commits_per_day"] = 0.0

    # PR count (merge commits referencing pull requests)
    merge_log = run_git(repo_path, ["log", "--all", "--merges", "--oneline"])
    pr_count = 0
    for line in merge_log.splitlines():
        if "Merge pull request" in line or "pull request" in line.lower():
            pr_count += 1
    metrics["pr_count"] = pr_count

    # Issue references in commit messages
    all_log = run_git(repo_path, ["log", "--all", "--format=%s"])
    issue_refs = set()
    for line in all_log.splitlines():
        lower = line.lower()
        # Match patterns like #123, closes #456, fixes #789
        for m in re.finditer(r"#(\d+)", line):
            issue_refs.add(m.group(1))
    metrics["issue_ref_count"] = len(issue_refs)

    # Conventional commit breakdown
    conventional = {"feat": 0, "fix": 0, "chore": 0, "docs": 0, "test": 0,
                    "ci": 0, "refactor": 0, "style": 0, "perf": 0, "build": 0}
    for line in all_log.splitlines():
        for prefix in conventional:
            if line.startswith(f"{prefix}(") or line.startswith(f"{prefix}:"):
                conventional[prefix] += 1
                break
    metrics["conventional_commits"] = conventional

    # File count
    files_out = run_git(repo_path, ["ls-tree", "-r", "--name-only", "HEAD"])
    metrics["file_count"] = len([f for f in files_out.splitlines() if f.strip()]) if files_out else 0

    return metrics


def load_criteria() -> list[dict]:
    """Load the git-history domain criteria."""
    with open(CRITERIA_PATH) as f:
        data = json.load(f)
    return data.get("criteria", [])


def evaluate_commit(criteria: list[dict], repo_path: Path, product_name: str) -> list[dict]:
    """Evaluate each criterion against the repo's git history."""
    # Build lookup structures from the repo
    all_hashes = set()
    all_short_hashes = set()
    all_messages = set()

    # Get all full hashes
    hashes_out = run_git(repo_path, ["log", "--all", "--format=%H"])
    for h in hashes_out.splitlines():
        h = h.strip()
        if h:
            all_hashes.add(h)
            all_short_hashes.add(h[:7])
            all_short_hashes.add(h[:8])
            all_short_hashes.add(h[:10])

    # Get all commit messages
    msgs_out = run_git(repo_path, ["log", "--all", "--format=%s"])
    for m in msgs_out.splitlines():
        m = m.strip()
        if m:
            all_messages.add(m)

    results = []
    for criterion in criteria:
        title = criterion["title"]
        sha_prefix, message = parse_criterion_title(title)
        is_applicable = product_name in criterion.get("applicable_products", [])

        status = "missing"
        evidence = ""
        notes = ""

        if not is_applicable:
            status = "not_applicable"
            evidence = f"Product '{product_name}' is not in applicable_products list"
        elif sha_prefix and sha_prefix in all_short_hashes:
            status = "satisfied"
            evidence = f"Commit {sha_prefix} found in repo"
        elif message in all_messages:
            status = "satisfied"
            evidence = f"Commit message match found in repo"
        else:
            # Fuzzy check: see if the core of the message (after the colon prefix) exists
            if ": " in message:
                core_msg = message.split(": ", 1)[1]
                for repo_msg in all_messages:
                    if core_msg[:30] in repo_msg:
                        status = "partial"
                        evidence = f"Partial message match: '{repo_msg[:60]}...'"
                        break

        if status == "missing" and is_applicable:
            notes = "Commit not found in product repo"

        results.append({
            "id": criterion["id"],
            "title": title,
            "domain": criterion["domain"],
            "status": status,
            "applicable_products": criterion.get("applicable_products", []),
            "evidence": evidence,
            "notes": notes,
        })

    return results


def build_scorecard(product_name: str, criteria_results: list[dict], metrics: dict) -> dict:
    """Build the output scorecard."""
    satisfied = sum(1 for c in criteria_results if c["status"] == "satisfied")
    partial = sum(1 for c in criteria_results if c["status"] == "partial")
    missing = sum(1 for c in criteria_results if c["status"] == "missing")
    not_applicable = sum(1 for c in criteria_results if c["status"] == "not_applicable")
    total_applicable = satisfied + partial + missing

    score_pct = round((satisfied / total_applicable * 100) if total_applicable > 0 else 0, 1)

    return {
        "schema": "git-history-eval-v1",
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "product": product_name,
        "domain": "git-history",
        "repo_metrics": metrics,
        "summary": {
            "total_criteria": len(criteria_results),
            "satisfied": satisfied,
            "partial": partial,
            "missing": missing,
            "not_applicable": not_applicable,
            "score_percentage": score_pct,
        },
        "criteria": criteria_results,
    }


def find_repo(product_name: str) -> Optional[Path]:
    """Find a product's repo directory."""
    direct = REPOS_DIR / product_name
    if direct.is_dir():
        return direct
    # Try case-insensitive search
    for d in REPOS_DIR.iterdir():
        if d.is_dir() and d.name.lower() == product_name.lower():
            return d
    return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python evaluators/git_history.py <product_name>")
        print("Example: python evaluators/git_history.py substrate")
        sys.exit(1)

    product_name = sys.argv[1]
    repo_path = find_repo(product_name)

    if not repo_path:
        print(f"ERROR: No repo found for '{product_name}' in {REPOS_DIR}")
        available = [d.name for d in REPOS_DIR.iterdir() if d.is_dir()]
        print(f"Available repos: {', '.join(sorted(available))}")
        sys.exit(1)

    print(f"Evaluating '{product_name}' at {repo_path}")

    # Load criteria
    criteria = load_criteria()
    print(f"Loaded {len(criteria)} git-history criteria")

    # Collect git metrics
    print("Collecting git metrics...")
    metrics = collect_git_metrics(repo_path)
    print(f"  Commits: {metrics['total_commits']}")
    print(f"  Contributors: {metrics['contributor_count']}")
    print(f"  PRs (merge commits): {metrics['pr_count']}")
    print(f"  Issue references: {metrics['issue_ref_count']}")
    print(f"  Files: {metrics['file_count']}")

    # Evaluate criteria
    print("Evaluating criteria against repo...")
    results = evaluate_commit(criteria, repo_path, product_name)

    # Build scorecard
    scorecard = build_scorecard(product_name, results, metrics)

    # Write output
    SCORECARDS_DIR.mkdir(exist_ok=True)
    output_path = SCORECARDS_DIR / f"{product_name}-git-history.json"
    with open(output_path, "w") as f:
        json.dump(scorecard, f, indent=2)

    # Print summary
    s = scorecard["summary"]
    print(f"\n--- Results ---")
    print(f"Criteria evaluated: {s['total_criteria']}")
    print(f"Satisfied:          {s['satisfied']}")
    print(f"Partial:            {s['partial']}")
    print(f"Missing:            {s['missing']}")
    print(f"Not applicable:     {s['not_applicable']}")
    print(f"Score:              {s['score_percentage']}%")
    print(f"\nOutput written to: {output_path}")


if __name__ == "__main__":
    main()
