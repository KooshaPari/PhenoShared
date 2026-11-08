#!/usr/bin/env python3
"""WP-22 dependency license checker.

Reads a CycloneDX SBOM, extracts the licenses of every component,
and reports any non-allowlisted license as a violation. Exits non-zero
if any violations are found. License list source-of-truth is
`LICENSE_ALLOWLIST.toml` in the repo root.

Used by `.github/workflows/license-check.yml` on every PR to block
introductions of copyleft or unknown-licensed dependencies.
"""
from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path
from typing import Any


def load_allowlist(path: Path) -> dict[str, Any]:
    """Load allowlist config from a TOML file."""
    with path.open("rb") as fh:
        return tomllib.load(fh)


def extract_component_licenses(sbom: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, str]]:
    """Extract [{name, version, license}] from CycloneDX or cargo-license JSON."""
    out: list[dict[str, str]] = []
    components = sbom if isinstance(sbom, list) else sbom.get("components", [])
    for comp in components:
        name = comp.get("name", "?")
        version = comp.get("version", "?")
        cargo_license = comp.get("license")
        if cargo_license:
            out.append({"name": name, "version": version, "license": cargo_license})
            continue
        licenses = comp.get("licenses", []) or []
        if not licenses:
            out.append({"name": name, "version": version, "license": "UNKNOWN"})
            continue
        for lic in licenses:
            lic_obj = lic.get("license", {}) or {}
            lic_id = lic_obj.get("id") or lic_obj.get("name") or "UNKNOWN"
            out.append({"name": name, "version": version, "license": lic_id})
    return out


def _strip_outer_parens(expression: str) -> str:
    """Remove balanced outer parentheses from an SPDX expression."""
    expression = expression.strip()
    while expression.startswith("(") and expression.endswith(")"):
        depth = 0
        balanced = True
        for index, char in enumerate(expression):
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0 and index != len(expression) - 1:
                    balanced = False
                    break
        if not balanced or depth != 0:
            break
        expression = expression[1:-1].strip()
    return expression


def _split_expression(expression: str, operator: str) -> list[str]:
    """Split an SPDX expression on a top-level boolean operator."""
    parts: list[str] = []
    start = 0
    depth = 0
    marker = f" {operator} "
    index = 0
    while index < len(expression):
        char = expression[index]
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif depth == 0 and expression.startswith(marker, index):
            parts.append(expression[start:index].strip())
            start = index + len(marker)
            index = start
            continue
        index += 1
    if parts:
        parts.append(expression[start:].strip())
    return parts


def classify_license(
    expression: str,
    allowed: set[str],
    denied: set[str],
    review_required: set[str],
) -> str:
    """Classify an SPDX expression as allowed, denied, review, or unknown.

    For ``OR`` expressions, one approved option is sufficient. For ``AND``
    expressions every term must be approved. This handles the composite SPDX
    strings emitted by cargo-license without weakening deny/review semantics.
    """
    expression = _strip_outer_parens(expression.upper().strip())
    if expression in denied:
        return "denied"
    if expression in review_required:
        return "review"
    if expression in allowed:
        return "allowed"

    # SPDX WITH expressions retain the base license's policy classification.
    if " WITH " in expression:
        return classify_license(expression.split(" WITH ", 1)[0], allowed, denied, review_required)

    disjunction = _split_expression(expression, "OR")
    if disjunction:
        classifications = [
            classify_license(part, allowed, denied, review_required)
            for part in disjunction
        ]
        if "allowed" in classifications:
            return "allowed"
        if "review" in classifications:
            return "review"
        if all(item == "denied" for item in classifications):
            return "denied"
        return "unknown"

    conjunction = _split_expression(expression, "AND")
    if conjunction:
        classifications = [
            classify_license(part, allowed, denied, review_required)
            for part in conjunction
        ]
        if "denied" in classifications:
            return "denied"
        if "review" in classifications:
            return "review"
        if all(item == "allowed" for item in classifications):
            return "allowed"
        return "unknown"

    return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sbom", required=True, help="Path to CycloneDX JSON SBOM")
    parser.add_argument(
        "--allowlist",
        default="LICENSE_ALLOWLIST.toml",
        help="Path to allowlist config (default: repo root)",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text)",
    )
    args = parser.parse_args()

    sbom_path = Path(args.sbom)
    allowlist_path = Path(args.allowlist)

    if not sbom_path.exists():
        print(f"ERROR: SBOM not found at {sbom_path}", file=sys.stderr)
        return 2
    if not allowlist_path.exists():
        print(f"ERROR: allowlist not found at {allowlist_path}", file=sys.stderr)
        return 2

    with sbom_path.open("r", encoding="utf-8") as fh:
        sbom = json.load(fh)

    allowlist = load_allowlist(allowlist_path)
    allowed: set[str] = set(allowlist.get("licenses", {}).get("allow", []))
    denied: set[str] = set(allowlist.get("licenses", {}).get("deny", []))
    review_required: set[str] = set(
        allowlist.get("licenses", {}).get("review_required", [])
    )

    components = extract_component_licenses(sbom)

    violations: list[dict[str, str]] = []
    review: list[dict[str, str]] = []
    for comp in components:
        lic = comp["license"].upper().strip()
        classification = classify_license(lic, allowed, denied, review_required)
        if classification == "denied":
            violations.append({**comp, "reason": "denied license"})
        elif classification == "review":
            review.append({**comp, "reason": "review-required license"})
        elif classification != "allowed":
            violations.append({**comp, "reason": "not in allowlist"})

    if args.format == "json":
        print(
            json.dumps(
                {
                    "sbom": str(sbom_path),
                    "components_scanned": len(components),
                    "violations": violations,
                    "review": review,
                },
                indent=2,
            )
        )
    else:
        print(f"Scanned {len(components)} components")
        if violations:
            print(f"\n{len(violations)} violations:")
            for v in violations:
                print(f"  {v['name']}@{v['version']}: {v['license']} ({v['reason']})")
        if review:
            print(f"\n{len(review)} need review:")
            for r in review:
                print(f"  {r['name']}@{r['version']}: {r['license']}")

    if violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
