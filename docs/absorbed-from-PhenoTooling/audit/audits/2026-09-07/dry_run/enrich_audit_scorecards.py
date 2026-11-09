#!/usr/bin/env python3
"""Enrich audit scorecards using repo-level pillar scores.

Reads repos/*/audit_scorecard.json (30 pillars, 0-100 scores) and maps
them to rubric domains. Updates scorecards/*-audit.json with better
product-specific assessments.
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RUBRIC_PATH = PROJECT_ROOT / "rubric" / "rubric-v1.json"
REPOS_DIR = PROJECT_ROOT / "repos"
SCORECARDS_DIR = PROJECT_ROOT / "scorecards"

# Map pillar names to rubric domains
PILLAR_TO_DOMAIN = {
    "L1 Architecture": ["architecture"],
    "L2 Dev Loop": ["ci_cd", "release_engineering"],
    "L3 Agent Loop": ["agentic-github", "workflow"],
    "L4 Observability": ["observability"],
    "L5 Security": ["security", "owasp-top10", "owasp-asvs"],
    "L6 Performance": ["code_quality"],
    "L7 Extensibility": ["architecture", "dx"],
    "L8 Compliance": ["SOX", "CIS_Controls", "owasp-asvs"],
    "L9 Complexity": ["code_quality"],
    "L10 Type Safety": ["code_quality"],
    "L11 Dependencies": ["supply_chain", "third-party"],
    "L12 Error Handling": ["code_quality"],
    "L13 Logging": ["observability"],
    "L14 Data Layer": ["architecture"],
    "L15 API Surface": ["architecture", "documentation"],
    "L16 Frontend": ["dx"],
    "L17 I18n/A11y": ["dx"],
    "L18 Concurrency": ["code_quality"],
    "L19 Memory": ["code_quality"],
    "L20 Config": ["documentation"],
    "L21 Testing Depth": ["testing"],
    "L22 Fuzzing": ["testing"],
    "L23 Release": ["release_engineering"],
    "L24 Migration": ["documentation"],
    "L25 Vendor Lockin": ["supply_chain"],
    "L26 Event Driven": ["architecture"],
    "L27 Infrastructure": ["ci_cd"],
    "L28 Cost Efficiency": ["dx"],
    "L29 Monitoring": ["observability"],
    "L30 Onboarding": ["documentation", "dx"],
}


def pillar_score_to_status(score: int) -> str:
    """Convert a 0-100 pillar score to a criterion status."""
    if score >= 80:
        return "satisfied"
    elif score >= 40:
        return "partial"
    else:
        return "missing"


def load_rubric():
    data = json.loads(RUBRIC_PATH.read_bytes())
    return data["criteria"]


def find_repo_scorecard(product_name: str):
    """Find the repo-level audit_scorecard.json for a product."""
    for f in REPOS_DIR.rglob("audit_scorecard.json"):
        data = json.loads(f.read_bytes())
        repo = data.get("repo", "").lower()
        if product_name.lower() in repo or repo in product_name.lower():
            if "scores" in data and data.get("overall", 0) > 0:
                return data
    return None


def build_domain_scores(pillar_scores: dict) -> dict[str, int]:
    """Map pillar scores to domain average scores."""
    domain_scores = defaultdict(list)
    for pillar, score in pillar_scores.items():
        domains = PILLAR_TO_DOMAIN.get(pillar, [])
        for d in domains:
            domain_scores[d].append(score)

    # Average per domain
    return {d: sum(s) // len(s) for d, s in domain_scores.items()}


def enrich_audit_scorecard(product_name: str, rubric_criteria: list) -> tuple | None:
    """Enrich an audit scorecard using repo pillar data.

    Only enriches criteria that were already in the original audit scorecard.
    Returns (enriched_criteria, improved_count) or None.
    """
    repo_data = find_repo_scorecard(product_name)
    if not repo_data:
        return None

    pillar_scores = repo_data.get("scores", {})
    domain_scores = build_domain_scores(pillar_scores)

    # Load existing audit criteria (scope to these IDs only)
    audit_path = SCORECARDS_DIR / f"{product_name}-audit.json"
    if not audit_path.exists():
        return None
    audit_data = json.loads(audit_path.read_bytes())
    existing_criteria = audit_data.get("criteria", [])
    existing_ids = {c["id"] for c in existing_criteria}

    # Build rubric lookup - deduplicate by ID (pick first occurrence)
    rubric_by_id = {}
    for c in rubric_criteria:
        if c["id"] not in rubric_by_id:
            rubric_by_id[c["id"]] = c

    # Enrich only the criteria that were in the original audit
    enriched = []
    improved = 0
    seen_ids = set()
    for ec in existing_criteria:
        cid = ec["id"]
        if cid in seen_ids:
            continue  # Skip duplicates
        seen_ids.add(cid)

        rc = rubric_by_id.get(cid)
        if not rc:
            enriched.append(ec)
            continue

        domain = rc["domain"]
        domain_score = domain_scores.get(domain, 50)
        new_status = pillar_score_to_status(domain_score)

        existing_status = ec.get("status", "missing")

        status_priority = {"satisfied": 3, "partial": 2, "missing": 1}
        if status_priority.get(new_status, 0) > status_priority.get(existing_status, 0):
            final_status = new_status
            improved += 1
        else:
            final_status = existing_status

        enriched.append({
            "id": cid,
            "status": final_status,
            "domain": domain,
            "source": rc.get("source", "unknown"),
        })

    return enriched, improved


def main():
    rubric_criteria = load_rubric()

    # Find products with repo scorecards but weak audit scorecards
    products_improved = 0
    total_improved = 0

    for f in sorted(SCORECARDS_DIR.glob("*-audit.json")):
        product = f.stem.replace("-audit", "")
        repo_data = find_repo_scorecard(product)
        if not repo_data:
            continue

        overall = repo_data.get("overall", 0)
        audit_data = json.loads(f.read_bytes())
        criteria = audit_data.get("criteria", [])
        current_sat = sum(1 for c in criteria if c.get("status") == "satisfied")

        result = enrich_audit_scorecard(product, rubric_criteria)
        if result is None:
            continue

        enriched, improved = result
        if improved > 0:
            new_sat = sum(1 for c in enriched if c.get("status") == "satisfied")
            new_part = sum(1 for c in enriched if c.get("status") == "partial")
            print(f"{product}: repo={overall}% | audit {current_sat}->{new_sat} satisfied, {new_part} partial (+{improved})")

            # Write enriched scorecard
            enriched_data = {
                "product": product,
                "source_format": "enriched_pillar",
                "original_overall": overall,
                "original_grade": repo_data.get("grade", "?"),
                "criteria": enriched,
            }
            f.write_text(json.dumps(enriched_data, indent=2))
            products_improved += 1
            total_improved += improved
        else:
            print(f"{product}: no improvement (repo={overall}%, already optimal)")

    print(f"\nEnriched {products_improved} products, {total_improved} criteria improved")


if __name__ == "__main__":
    main()
