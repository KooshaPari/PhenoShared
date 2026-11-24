#!/usr/bin/env python3
"""
Traceability Checker for Phenotype Ecosystem.
Validates that all Functional Requirements (FRs) defined in traceability.json
have corresponding implementations in code and coverage in tests.
"""

import os
import re
import json
import sys
import argparse
from typing import Dict, List, Set, Tuple

# Regex patterns for finding traceability markers in code/tests
SPEC_MARKERS = {
    "FR": re.compile(r"FR-(?:[A-Z0-9]+-)?\d+|SKILL-\d+|TASK-\d+|AUTH-\d+|CONF-\d+|VES-\d+|FORGE-\d+|EVAL-\d+|TYPE-\d+|INFRA-\d+|GOV-\d+|HUB-\d+|CLI-\d+|META-\d+|VM-\d+"),
    "TRACE": re.compile(r"@trace\s+([A-Z0-9-]+\d+)"),
}

def find_markers_in_dir(directory: str, extensions: Tuple[str, ...] = (".rs", ".ts", ".py", ".yaml", ".yml", ".md")) -> Set[str]:
    """Scan directory for FR and @trace markers."""
    found_frs = set()

    for root, _, files in os.walk(directory):
        if any(d in root for d in ["target", "node_modules", ".git", "vendor", "__pycache__"]):
            continue
            
        for file in files:
            if file.endswith(extensions):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        found_frs.update(SPEC_MARKERS["FR"].findall(content))
                        # Also check for @trace annotations
                        traces = SPEC_MARKERS["TRACE"].findall(content)
                        found_frs.update(traces)
                except Exception as e:
                    print(f"Error reading {path}: {e}", file=sys.stderr)
                    
    return found_frs

def main():
    parser = argparse.ArgumentParser(description="Phenotype Traceability Checker")
    parser.add_argument("--json", help="Path to traceability.json")
    parser.add_argument("--root", default=".", help="Root directory to scan")
    parser.add_argument(
        "--strict-annotations",
        action="store_true",
        help="Fail (exit nonzero) if any implemented spec is missing code/tests. "
             "Default is soft mode: prints WARN lines and exits 0. "
             "See specs/FR-TRACE-BACKFILL-001.md for the pending backfill.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        dest="strict_annotations",
        help="Deprecated alias for --strict-annotations.",
    )
    args = parser.parse_args()

    if not args.json:
        common_paths = [
            "docs/traceability/traceability.json",
            "phenodocs/docs/traceability/traceability.json",
            "phenodocs/docs/public/api/traceability.json"
        ]
        for p in common_paths:
            if os.path.exists(p):
                args.json = p
                break
    
    if not args.json or not os.path.exists(args.json):
        print(f"Error: Traceability JSON not found.")
        sys.exit(1)

    with open(args.json, "r") as f:
        data = json.load(f)

    ecosystem = data.get("ecosystem", "Phenotype")
    repos = data.get("repositories", data.get("repos", []))
    
    print(f"--- Traceability Validation for {ecosystem} ---")
    print(f"Scanning {args.root} for annotations...")
    
    found_frs = find_markers_in_dir(args.root)
    print(f"Found {len(found_frs)} unique traceability markers.\n")

    overall_missing = []

    # Map current scan results to repositories defined in JSON
    for repo in repos:
        repo_name = repo.get("name", "Unknown")
        if "specsList" in repo:
            implemented = [s for s in repo["specsList"] if s.get("status") == "implemented"]
            missing = [s["id"] for s in implemented if s["id"] not in found_frs]
            
            if missing:
                print(f"❌ {repo_name}: Missing {len(missing)} implementation(s): {', '.join(missing)}")
                for sid in missing:
                    print(f"WARN: Missing {sid} ({repo_name})")
                overall_missing.extend([(repo_name, sid) for sid in missing])
            else:
                print(f"✅ {repo_name}: All {len(implemented)} implemented specs verified.")
        else:
            print(f"ℹ️ {repo_name}: No detailed spec list available for validation.")

    print("\n--- Summary ---")
    if overall_missing:
        print(f"Total missing annotations: {len(overall_missing)}")
        if args.strict_annotations:
            print("Strict mode enabled (--strict-annotations): failing.")
            sys.exit(1)
        else:
            print(
                "Soft mode (default): exiting 0. "
                "Pass --strict-annotations to fail on gaps. "
                "Backfill tracked in specs/FR-TRACE-BACKFILL-001.md."
            )
    else:
        print("All traceability checks passed!")

if __name__ == "__main__":
    main()
