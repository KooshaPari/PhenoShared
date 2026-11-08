"""Proposed card-to-rubric mapping.

For each card row (id + status), finds the rubric row(s) with the same ID.
Marks exact matches vs ambiguous matches. All mappings are PROPOSED,
not reviewed.

Usage:
    python3 propose_mapping.py
"""
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent  # audit-system/


def load_rubric():
    path = REPO / "rubric" / "rubric-v1.json"
    data = json.loads(path.read_bytes())
    return data["criteria"]


def load_card(card_filename):
    path = REPO / "scorecards" / card_filename
    return json.loads(path.read_bytes())["criteria"]


# Card filename -> rubric source pattern (for lineage)
CARD_SOURCE_PATTERNS = {
    "substrate-audit.json": "substrate-v3",
    "Melosviz-audit.json": "Melosviz",
    "SessionLedger-audit.json": "SessionLedger",
    "Tracera-wtrees-audit.json": "Tracera",
    "phenotype-registry-audit.json": "phenotype-registry",
    "sharecli-audit.json": "sharecli",
}

CARDS = [
    "substrate-audit.json",
    "Melosviz-audit.json",
    "SessionLedger-audit.json",
    "Tracera-wtrees-audit.json",
    "phenotype-registry-audit.json",
    "sharecli-audit.json",
]


def build_mapping():
    criteria = load_rubric()

    # Index rubric by ID
    rubric_by_id = {}
    for i, c in enumerate(criteria):
        rubric_by_id.setdefault(c["id"], []).append({
            "source": c["source"],
            "domain": c["domain"],
            "status": c["status"],
            "title": c.get("title", ""),
            "_rubric_idx": i,
        })

    results = {}
    stats = {"total_rows": 0, "exact": 0, "ambiguous": 0, "missing": 0}

    for card_file in CARDS:
        card_criteria = load_card(card_file)
        product = CARD_SOURCE_PATTERNS.get(card_file, "")
        mappings = []

        for cr in card_criteria:
            cid = cr["id"]
            rubric_rows = rubric_by_id.get(cid, [])

            if len(rubric_rows) == 0:
                # No rubric row with this ID
                mappings.append({
                    "card_id": cid,
                    "card_status": cr["status"],
                    "rubric_id": cid,
                    "match_type": "missing",
                    "rubric_source": None,
                    "rubric_domain": None,
                    "rubric_status": None,
                    "reviewed": False,
                    "note": "No rubric row with this ID",
                })
                stats["missing"] += 1

            elif len(rubric_rows) == 1:
                # Exact match
                rr = rubric_rows[0]
                mappings.append({
                    "card_id": cid,
                    "card_status": cr["status"],
                    "rubric_id": cid,
                    "match_type": "exact",
                    "rubric_source": rr["source"],
                    "rubric_domain": rr["domain"],
                    "rubric_status": rr["status"],
                    "reviewed": False,
                    "note": f"Single rubric row: source={rr['source']}",
                })
                stats["exact"] += 1

            else:
                # Ambiguous: multiple rubric rows share this ID
                # Prefer the product-specific source if available
                product_rows = [r for r in rubric_rows
                               if product.lower() in r["source"].lower()]
                if len(product_rows) == 1:
                    rr = product_rows[0]
                    match_type = "product-preferred"
                    note = (f"Multiple rows share ID; selected product source "
                            f"'{rr['source']}'")
                elif len(product_rows) > 1:
                    rr = product_rows[0]
                    match_type = "product-ambiguous"
                    note = (f"Multiple rows share ID; {len(product_rows)} "
                            f"product sources; first selected")
                else:
                    # No product source; pick first
                    rr = rubric_rows[0]
                    match_type = "ambiguous"
                    note = (f"Multiple rows share ID; no product source found; "
                            f"first selected: source='{rr['source']}'")

                mappings.append({
                    "card_id": cid,
                    "card_status": cr["status"],
                    "rubric_id": cid,
                    "match_type": match_type,
                    "rubric_source": rr["source"],
                    "rubric_domain": rr["domain"],
                    "rubric_status": rr["status"],
                    "reviewed": False,
                    "note": note,
                    "all_sources": [r["source"] for r in rubric_rows],
                })
                stats["ambiguous"] += 1

            stats["total_rows"] += 1

        results[card_file] = mappings

    return results, stats


def main():
    results, stats = build_mapping()

    # Write proposed mapping
    output = {
        "status": "PROPOSED",
        "note": "All mappings are proposed, not reviewed. "
                "Reviewer must approve each ambiguous mapping.",
        "stats": stats,
        "cards": results,
    }

    out_path = HERE / "PROPOSED-MAPPING.json"
    out_path.write_bytes(json.dumps(output, indent=2).encode())

    # Summary
    print(f"Total card rows: {stats['total_rows']}")
    print(f"  Exact match: {stats['exact']}")
    print(f"  Ambiguous (proposed, needs review): {stats['ambiguous']}")
    print(f"  Missing (no rubric row): {stats['missing']}")
    print(f"\nProposed mapping written to: {out_path}")

    # Per-card summary
    for card_file, mappings in results.items():
        name = card_file.replace("-audit.json", "")
        types = Counter(m["match_type"] for m in mappings)
        print(f"\n  {name}: {dict(types)}")


if __name__ == "__main__":
    main()
