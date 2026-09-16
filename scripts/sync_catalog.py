#!/usr/bin/env python3
"""sync_catalog.py — Sync catalog/registry.yaml with registry/disposition-index.json.

Reads the disposition-index as the source of truth for FSM states and maps them
to the valid catalog statuses. Generates a fixed catalog/registry.yaml.
"""
import json
import sys
from pathlib import Path

import yaml

# --- Config ---
REPO_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = REPO_ROOT / "catalog" / "registry.yaml"
INDEX_PATH = REPO_ROOT / "registry" / "disposition-index.json"

# FSM state -> catalog status mapping (valid: active, archived, deprecated, absorbed)
FSM_TO_CATALOG_STATUS = {
    "live": "active",
    "done": "archived",
    "archived": "archived",
    "absorbed": "absorbed",
    "deleted": "archived",
    "never_existed": "deprecated",
}

def load_index(path: Path) -> dict:
    """Load the JSON index and return a dict keyed by normalized path.
    
    When multiple rows exist for the same repo, we prefer the "best" FSM state:
    live > done > archived > deleted > absorbed > never_existed
    
    If there are multiple entries with the same best FSM state, we prefer the one
    with the highest ID (numeric > string, later in file).
    """
    FSM_PRIORITY = {
        "live": 6,
        "done": 5,
        "archived": 4,
        "deleted": 3,
        "absorbed": 2,
        "never_existed": 1,
    }
    
    with path.open() as f:
        data = json.load(f)
    
    # Build a lookup by normalized repo path
    index_by_path = {}
    for idx, row in enumerate(data["rows"]):
        raw_path = str(row.get("path", "")).strip()
        # Normalize: remove "KooshaPari/" prefix if present
        normalized = raw_path.split("/")[-1].lower()
        fsm = row.get("fsm", "").lower()
        
        if not normalized or not fsm:
            continue
            
        row_id = row.get("id", idx)
        new_priority = FSM_PRIORITY.get(fsm, 0)
        
        if normalized not in index_by_path:
            index_by_path[normalized] = (fsm, row_id, new_priority)
        else:
            existing_fsm, existing_id, existing_priority = index_by_path[normalized]
            # Prefer higher priority FSM state
            if new_priority > existing_priority:
                index_by_path[normalized] = (fsm, row_id, new_priority)
            elif new_priority == existing_priority:
                # Same priority - prefer higher ID (later in file)
                if isinstance(row_id, int) and (not isinstance(existing_id, int) or row_id > existing_id):
                    index_by_path[normalized] = (fsm, row_id, new_priority)
                elif isinstance(row_id, str) and isinstance(existing_id, str) and row_id > existing_id:
                    index_by_path[normalized] = (fsm, row_id, new_priority)
    
    return {k: v[0] for k, v in index_by_path.items()}

def load_catalog(path: Path) -> dict:
    """Load the YAML catalog."""
    with path.open() as f:
        return yaml.safe_load(f)

def main():
    if not CATALOG_PATH.exists() or not INDEX_PATH.exists():
        print(f"Error: Required files not found.")
        return 1

    print("Loading index...")
    index = load_index(INDEX_PATH)
    
    print("Loading catalog...")
    catalog = load_catalog(CATALOG_PATH)
    substrates = catalog.get("substrates", [])
    
    mismatches = []
    fixed_entries = []
    
    print("\nAnalyzing mismatches...")
    for entry in substrates:
        slug = entry.get("id", "<missing>")
        repo = entry.get("repo", "")
        current_status = entry.get("status", "")
        
        # Normalize repo name for lookup
        repo_name = repo.split("/")[-1].lower() if "/" in repo else repo.lower()
        
        fsm_state = index.get(repo_name)
        
        expected_status = None
        if fsm_state:
            expected_status = FSM_TO_CATALOG_STATUS.get(fsm_state, current_status)
            
        if expected_status and expected_status != current_status:
            mismatches.append({
                "slug": slug,
                "repo": repo,
                "current": current_status,
                "expected": expected_status,
                "fsm": fsm_state
            })
            # Update the entry
            new_entry = entry.copy()
            new_entry["status"] = expected_status
            fixed_entries.append(new_entry)
        else:
            fixed_entries.append(entry)

    if not mismatches:
        print("No mismatches found. Catalog is in sync.")
        return 0

    print(f"\nFound {len(mismatches)} mismatches:")
    for m in mismatches:
        print(f"  - {m['slug']}: {m['current']} -> {m['expected']} (FSM: {m['fsm']})")

    # Write fixed catalog
    catalog["substrates"] = fixed_entries
    # Preserve order of top-level keys if possible, but simple dump is safer
    print(f"\nWriting fixed catalog to {CATALOG_PATH}...")
    with CATALOG_PATH.open("w") as f:
        yaml.dump(catalog, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
    print("Done.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
