#!/usr/bin/env python3
"""Architecture evaluator: scans full repos for standard files and patterns.

Maps findings to rubric criteria to update audit scorecards.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUBRIC_PATH = PROJECT_ROOT / "rubric" / "rubric-v1.json"
SCORECARDS_DIR = PROJECT_ROOT / "scorecards"
REPOS_DIR = PROJECT_ROOT / "repos"

# Product name -> full repo directory
PRODUCT_TO_REPO = {
    "HeliosLab": "_full_HeliosLab",
    "OmniRoute": "_full_OmniRoute",
    "PhenoVCS": "_full_PhenoVCS",
    "AgilePlus-recovered-20260822": "_full_AgilePlus",
    "cliproxyapi-plusplus": "_full_agentapi",
    "hwLedger": "_full_hwLedger",
    "pheno-crates-hexa-kit": "_full_HexaKit",
    "pheno-crates-hexa-kit-templates-appgen": "_full_HexaKit",
    "phenotype-tooling-mergify": "_full_tooling",
    "phenoAI": "_full_pheno",
    "PhenoPlugins": "_full_pheno",
    "Agentora-wtrees-wt-206": "_full_Agentora",
    "argis-extensions": "_full_argis",
}

# File patterns that indicate architecture maturity
ARCHITECTURE_SIGNALS = {
    "has_readme": ["README.md", "README.rst", "README.txt"],
    "has_license": ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"],
    "has_contributing": ["CONTRIBUTING.md", "CONTRIBUTING.rst"],
    "has_code_of_conduct": ["CODE_OF_CONDUCT.md"],
    "has_security": ["SECURITY.md"],
    "has_changelog": ["CHANGELOG.md", "CHANGES.md", "HISTORY.md"],
    "has_ci": [".github/workflows/", ".circleci/", ".travis.yml", "Jenkinsfile"],
    "has_docker": ["Dockerfile", "docker-compose.yml", "docker-compose.yaml"],
    "has_tests_dir": ["tests/", "test/", "__tests__/", "spec/"],
    "has_docs_dir": ["docs/", "doc/", "documentation/"],
    "has_src_dir": ["src/", "lib/", "app/"],
    "has_config_files": [".editorconfig", ".eslintrc", ".prettierrc", "pyproject.toml", "Cargo.toml", "package.json", "go.mod"],
    "has_gitignore": [".gitignore"],
    "has_env_example": [".env.example", ".env.sample", ".env.template"],
    "has_dependabot": [".github/dependabot.yml", ".github/dependabot.yaml"],
    "has_codeowners": [".github/CODEOWNERS"],
    "has_issue_templates": [".github/ISSUE_TEMPLATE/"],
    "has_pr_template": [".github/pull_request_template.md", ".github/PULL_REQUEST_TEMPLATE.md"],
}

# Mapping from architecture signals to rubric domains
SIGNAL_TO_DOMAINS = {
    "has_readme": ["documentation", "dx"],
    "has_license": ["supply_chain"],
    "has_contributing": ["documentation"],
    "has_code_of_conduct": ["documentation"],
    "has_security": ["security"],
    "has_changelog": ["release_engineering", "documentation"],
    "has_ci": ["ci_cd"],
    "has_docker": ["ci_cd", "release_engineering"],
    "has_tests_dir": ["testing"],
    "has_docs_dir": ["documentation", "dx"],
    "has_src_dir": ["architecture"],
    "has_config_files": ["code_quality", "dx"],
    "has_gitignore": ["documentation"],
    "has_env_example": ["documentation", "dx"],
    "has_dependabot": ["supply_chain"],
    "has_codeowners": ["documentation"],
    "has_issue_templates": ["documentation"],
    "has_pr_template": ["documentation"],
}


def load_rubric():
    data = json.loads(RUBRIC_PATH.read_bytes())
    return data["criteria"]


def scan_repo(repo_path: Path) -> dict:
    """Scan a repo for architecture signals."""
    signals = {}
    for signal_name, patterns in ARCHITECTURE_SIGNALS.items():
        found = False
        for pattern in patterns:
            if pattern.endswith("/"):
                # Directory check
                if (repo_path / pattern).is_dir():
                    found = True
                    break
            else:
                # File check
                if (repo_path / pattern).exists():
                    found = True
                    break
        signals[signal_name] = found
    return signals


def compute_domain_scores(signals: dict) -> dict[str, float]:
    """Compute domain scores from architecture signals."""
    domain_signals = defaultdict(list)
    for signal, found in signals.items():
        domains = SIGNAL_TO_DOMAINS.get(signal, [])
        for d in domains:
            domain_signals[d].append(1 if found else 0)

    scores = {}
    for domain, vals in domain_signals.items():
        scores[domain] = round(sum(vals) / len(vals) * 100) if vals else 0
    return scores


def score_to_status(score: float) -> str:
    if score >= 80:
        return "satisfied"
    elif score >= 40:
        return "partial"
    else:
        return "missing"


def evaluate_product(product_name: str, repo_dir: Path, rubric_criteria: list) -> list | None:
    """Evaluate a product using file-content analysis."""
    signals = scan_repo(repo_dir)
    domain_scores = compute_domain_scores(signals)

    # Load existing audit criteria
    audit_path = SCORECARDS_DIR / f"{product_name}-audit.json"
    if not audit_path.exists():
        return None
    audit_data = json.loads(audit_path.read_bytes())
    existing = audit_data.get("criteria", [])

    # Deduplicate rubric by ID
    rubric_by_id = {}
    for c in rubric_criteria:
        if c["id"] not in rubric_by_id:
            rubric_by_id[c["id"]] = c

    # Enrich existing criteria
    enriched = []
    improved = 0
    seen = set()
    for ec in existing:
        cid = ec["id"]
        if cid in seen:
            continue
        seen.add(cid)

        rc = rubric_by_id.get(cid)
        if not rc:
            enriched.append(ec)
            continue

        domain = rc["domain"]
        domain_score = domain_scores.get(domain, ec.get("pillar_score", 50))
        new_status = score_to_status(domain_score)
        existing_status = ec.get("status", "missing")

        priority = {"satisfied": 3, "partial": 2, "missing": 1}
        if priority.get(new_status, 0) > priority.get(existing_status, 0):
            final_status = new_status
            improved += 1
        else:
            final_status = existing_status

        enriched.append({
            "id": cid,
            "status": final_status,
            "domain": domain,
            "source": rc.get("source", "unknown"),
            "pillar_score": domain_score,
        })

    return enriched, improved, signals, domain_scores


def main():
    rubric_criteria = load_rubric()

    for product_name, repo_name in sorted(PRODUCT_TO_REPO.items()):
        repo_dir = REPOS_DIR / repo_name
        if not repo_dir.exists():
            print(f"SKIP {product_name}: repo not found at {repo_dir}")
            continue

        result = evaluate_product(product_name, repo_dir, rubric_criteria)
        if result is None:
            print(f"SKIP {product_name}: no audit scorecard")
            continue

        enriched, improved, signals, domain_scores = result
        sat = sum(1 for c in enriched if c["status"] == "satisfied")
        part = sum(1 for c in enriched if c["status"] == "partial")
        total = len(enriched)

        # Find signal summary
        true_signals = [k for k, v in signals.items() if v]
        false_signals = [k for k, v in signals.items() if not v]

        print(f"{product_name}: {sat}/{total} sat, {part} partial (+{improved} improved)")
        print(f"  Signals: {len(true_signals)}/{len(signals)} ({', '.join(true_signals[:5])}...)")
        print(f"  Domain scores: {dict(sorted(domain_scores.items(), key=lambda x: -x[1])[:5])}")

        # Write enriched scorecard
        enriched_data = {
            "product": product_name,
            "source_format": "file_content_analysis",
            "original_overall": None,
            "original_grade": None,
            "criteria": enriched,
        }
        audit_path = SCORECARDS_DIR / f"{product_name}-audit.json"
        audit_path.write_text(json.dumps(enriched_data, indent=2))
        print()


if __name__ == "__main__":
    main()
