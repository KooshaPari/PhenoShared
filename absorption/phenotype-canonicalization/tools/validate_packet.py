#!/usr/bin/env python3
"""Validate packet cross-references; optionally validate its four JSON Schemas.

Default checks use only the standard library. --jsonschema requires an installed
jsonschema library; missing validation machinery fails rather than silently skips.
This validates packet structure, NOT evidence authenticity or product behavior.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _check_dag(graph: dict[str, list[str]], label: str) -> None:
    active: set[str] = set()
    done: set[str] = set()

    def visit(node: str) -> None:
        if node in active:
            raise ValueError(f"{label}: dependency cycle")
        if node in done:
            return
        active.add(node)
        for dependency in graph.get(node, []):
            visit(dependency)
        active.remove(node)
        done.add(node)

    for node in graph:
        visit(node)


def validate(root: Path, schema_checks: bool = False) -> list[str]:
    errors: list[str] = []

    def load(path: str) -> Any:
        return json.loads((root / path).read_text(encoding="utf-8"))

    try:
        decisions = load("decisions.json")
        sources = load("audit/sources.json")
        findings = load("audit/findings.json")
        profiles = load("profiles.json")
        patterns = load("pattern-matrix.json")
        work = load("migration/work-packages.json")
        trees = load("decision-trees.json")["trees"]
        datasets = {
            "decisions": decisions, "sources": sources, "findings": findings,
            "profiles": profiles, "patterns": patterns, "work": work, "trees": trees,
        }
        for name, rows in datasets.items():
            if not isinstance(rows, list) or not rows:
                raise ValueError(f"{name}: expected a nonempty list")
            identifiers = [row["id"] for row in rows]
            if len(identifiers) != len(set(identifiers)):
                errors.append(f"duplicate IDs: {name}")
        did = {row["id"] for row in decisions}
        sid = {row["id"] for row in sources}
        fid = {row["id"] for row in findings}
        wid = {row["id"] for row in work}
        for row in decisions + findings:
            for reference in row["evidence"]:
                if reference not in sid:
                    errors.append(f'{row["id"]}: unknown evidence {reference}')
        for row in profiles:
            if not set(row["decision_ids"]) <= did:
                errors.append(f'{row["id"]}: unknown decision')
        for row in patterns:
            if row["decision_id"] not in did:
                errors.append(f'{row["id"]}: unknown decision')
        graph = {row["id"]: row["hard_dependencies"] for row in work}
        for row in work:
            if not set(row["finding_ids"]) <= fid:
                errors.append(f'{row["id"]}: unknown finding')
            if not set(row["hard_dependencies"]) <= wid:
                errors.append(f'{row["id"]}: unknown work dependency')
        _check_dag(graph, "work packages")
        for tree in trees:
            rows = tree["nodes"]
            nodes = {node["id"]: node for node in rows}
            if len(nodes) != len(rows):
                errors.append(f'{tree["id"]}: duplicate node IDs')
            if tree["start"] not in nodes:
                errors.append(f'{tree["id"]}: invalid start')
            graph = {node: [] for node in nodes}
            for node in rows:
                for branch in ("when_true", "when_false"):
                    target = node[branch]
                    if target in nodes:
                        graph[node["id"]].append(target)
                    elif not target.startswith("ACTION:"):
                        errors.append(f'{tree["id"]}: unknown branch {target}')
            _check_dag(graph, tree["id"])
        if schema_checks:
            try:
                from jsonschema import Draft202012Validator, FormatChecker
                from jsonschema.exceptions import SchemaError
            except ImportError:
                return errors + ["jsonschema dependency not installed; requested schema validation was NOT run"]
            pairs = [
                ("decisions.json", "schemas/decisions.schema.json"),
                ("examples/component.json", "schemas/component.schema.json"),
                ("examples/exception.json", "schemas/exception.schema.json"),
                ("examples/synthetic-receipt.json", "schemas/receipt.schema.json"),
            ]
            for data_path, schema_path in pairs:
                schema = load(schema_path)
                try:
                    Draft202012Validator.check_schema(schema)
                except SchemaError as exc:
                    errors.append(f"{schema_path}: invalid schema: {exc.message}")
                    continue
                validator = Draft202012Validator(schema, format_checker=FormatChecker())
                for error in validator.iter_errors(load(data_path)):
                    errors.append(f"{data_path}: {error.message}")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        errors.append(str(exc))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", type=Path, default=Path("."))
    parser.add_argument("--jsonschema", action="store_true")
    args = parser.parse_args()
    errors = validate(args.root, args.jsonschema)
    print(json.dumps({
        "packet_structure": "INVALID" if errors else "VALID",
        "schema_validation_requested": args.jsonschema,
        "product_qualification": "NOT_EVALUATED", "errors": errors,
    }, indent=2))
    return 2 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
