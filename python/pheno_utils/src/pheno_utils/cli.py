#!/usr/bin/env python3
"""Pheno-Utils - Unified CLI for Phenotype ecosystem utilities.

This CLI provides unified access to various utility functions for:
- Dependency analysis
- Health checks
- File size validation
- Lines of code counting
- Import migration
- And more...
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer

from pheno_utils import __version__
from pheno_utils.cleanup import format_report as format_cleanup_report
from pheno_utils.cleanup import validate_cleanup
from pheno_utils.codemap import format_codemap, generate_codemap
from pheno_utils.dependencies import analyze_dependencies, render_mermaid
from pheno_utils.docstrings import simplify_directory
from pheno_utils.file_sizes import check_file_sizes
from pheno_utils.file_sizes import format_report as format_size_report
from pheno_utils.health import format_health_report, run_health_checks
from pheno_utils.inventory import build_inventory, inventory_to_markdown
from pheno_utils.loc_counter import count_loc
from pheno_utils.migration import scan_and_migrate

app = typer.Typer(
    name="pheno-utils",
    help="Unified CLI utilities for Phenotype ecosystem",
    add_completion=True,
)


# Dependency Analysis Commands
@app.command("deps")
def deps_command(
    path: Annotated[Path, typer.Argument(help="Project root path")] = Path("."),
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file")] = None,
    format: Annotated[
        str, typer.Option("--format", "-f", help="Output format (json|mermaid)")
    ] = "json",
    min_count: Annotated[
        int, typer.Option("--min-count", help="Minimum usage count for mermaid")
    ] = 3,
) -> None:
    """Analyze dependencies in a project."""
    results = analyze_dependencies(path)

    if format == "mermaid":
        content = render_mermaid(results, min_count=min_count)
        if output:
            output.write_text(content)
            typer.echo(f"Mermaid diagram written to {output}")
        else:
            typer.echo(content)
    else:
        if output:
            with open(output, "w") as f:
                json.dump(results, f, indent=2, default=str)
            typer.echo(f"Dependency analysis written to {output}")
        else:
            typer.echo(json.dumps(results, indent=2, default=str))


@app.command("mermaid")
def mermaid_command(
    deps_file: Annotated[Path, typer.Argument(help="Path to dependency_analysis.json")],
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file")] = None,
    min_count: Annotated[int, typer.Option("--min-count", "-n", help="Minimum usage count")] = 3,
) -> None:
    """Generate Mermaid diagram from dependency analysis."""
    with open(deps_file) as f:
        analysis = json.load(f)

    content = render_mermaid(analysis, min_count=min_count)

    if output:
        output.write_text(content)
        typer.echo(f"Mermaid diagram written to {output}")
    else:
        typer.echo(content)


# Health Check Commands
@app.command("health")
def health_command(
    path: Annotated[Path, typer.Argument(help="Project root path")] = Path("."),
    check: Annotated[
        str, typer.Option("--check", "-c", help="Check type (all|imports|structure|config)")
    ] = "all",
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Run health checks on a project."""
    checks = None if check == "all" else [check]
    report = run_health_checks(path, checks)

    if json_output:
        typer.echo(json.dumps(report.to_dict(), indent=2))
    else:
        typer.echo(format_health_report(report))

    if not report.all_passed:
        raise typer.Exit(code=1)


# File Size Commands
@app.command("sizes")
def sizes_command(
    path: Annotated[Path, typer.Argument(help="Project root path")] = Path("."),
    limit: Annotated[int, typer.Option("--limit", "-l", help="Hard limit in LOC")] = 500,
    target: Annotated[int, typer.Option("--target", "-t", help="Target LOC")] = 350,
    strict: Annotated[bool, typer.Option("--strict", help="Fail on warnings")] = False,
    report_only: Annotated[
        bool, typer.Option("--report", help="Generate report only (no fail)")
    ] = False,
) -> None:
    """Check file sizes against limits."""
    violations, warnings = check_file_sizes(path, max_loc=limit, target_loc=target)

    output = format_size_report(violations, warnings, limit, target, path)
    typer.echo(output)

    if report_only:
        return

    if violations:
        typer.echo("❌ FAILED: Files exceed hard limit", err=True)
        raise typer.Exit(code=1)

    if strict and warnings:
        typer.echo("❌ FAILED: Files exceed target (strict mode)", err=True)
        raise typer.Exit(code=1)

    typer.echo("✅ PASSED: All files within limits")


# LOC Counter Commands
@app.command("loc")
def loc_command(
    path: Annotated[Path, typer.Argument(help="Project root path")] = Path("."),
    threshold: Annotated[int, typer.Option("--threshold", "-t", help="Maximum allowed LOC")] = 8500,
    exclude: Annotated[list[str], typer.Option("--exclude", "-e", help="Patterns to exclude")] = [],
    include: Annotated[list[str], typer.Option("--include", "-i", help="Paths to include")] = [],
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
) -> None:
    """Count logical lines of code."""
    summary = count_loc(
        path, includes=include or None, excludes=exclude or None, threshold=threshold
    )

    if json_output:
        typer.echo(summary.to_json())
    else:
        typer.echo(
            f"Runtime LOC: {summary.total_loc} "
            f"(threshold: {summary.threshold}, files counted: {summary.files_counted})"
        )

    if summary.exceeded:
        typer.echo(
            f"ERROR: LOC threshold exceeded by {summary.total_loc - summary.threshold} lines.",
            err=True,
        )
        raise typer.Exit(code=1)


# Inventory Commands
@app.command("inventory")
def inventory_command(
    path: Annotated[Path, typer.Argument(help="Project root path")] = Path("."),
    format: Annotated[str, typer.Option("--format", "-f", help="Output format (json|md)")] = "json",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file")] = None,
) -> None:
    """Generate public API inventory."""
    inventory = build_inventory(path)

    if format == "md":
        content = inventory_to_markdown(inventory)
    else:
        content = json.dumps(inventory, indent=2)

    if output:
        output.write_text(content)
        typer.echo(f"Inventory written to {output}")
    else:
        typer.echo(content)


# Migration Commands
@app.command("migrate")
def migrate_command(
    path: Annotated[Path, typer.Argument(help="Project root path")],
    from_version: Annotated[str, typer.Option("--from", help="Source version")] = "",
    to_version: Annotated[str, typer.Option("--to", help="Target version")] = "",
    apply: Annotated[
        bool, typer.Option("--apply", help="Apply changes (default: dry-run)")
    ] = False,
) -> None:
    """Migrate imports from old to new structure."""
    changes = list(scan_and_migrate(path, apply=apply))

    if apply:
        typer.echo(f"✅ Applied migration to {len(changes)} files")
    else:
        typer.echo(f"🔎 Dry-run: {len(changes)} files would be modified (use --apply to write)")

    if changes:
        typer.echo("Files that would be/were changed:")
        for file_path, n_changes in changes[:10]:
            typer.echo(f"  {file_path} ({n_changes} changes)")
        if len(changes) > 10:
            typer.echo(f"  ... and {len(changes) - 10} more")


# Docstring Commands
@app.command("simplify-docs")
def simplify_docs_command(
    path: Annotated[Path, typer.Argument(help="Directory to process")] = Path("."),
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview changes without applying")
    ] = True,
) -> None:
    """Simplify verbose docstrings."""
    files, changes = simplify_directory(path, dry_run=dry_run)

    action = "Would simplify" if dry_run else "Simplified"
    typer.echo(f"{action} {changes} docstrings in {files} files")


# Cleanup Validation Commands
@app.command("validate")
def validate_command(
    path: Annotated[Path, typer.Argument(help="Project root path")] = Path("."),
    strict: Annotated[bool, typer.Option("--strict", help="Fail on any issues")] = False,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    threshold: Annotated[
        int, typer.Option("--threshold", help="Large file threshold (bytes)")
    ] = 1_000_000,
) -> None:
    """Validate repository hygiene."""
    report = validate_cleanup(path, threshold=threshold)

    if json_output:
        typer.echo(json.dumps(report, indent=2))
    else:
        typer.echo(format_cleanup_report(report))

    if strict and report["status"] != "clean":
        raise typer.Exit(code=1)

    if report["status"] != "clean":
        typer.echo("⚠️  Repository needs cleanup", err=True)


# Code Map Commands
@app.command("codemap")
def codemap_command(
    path: Annotated[Path, typer.Argument(help="Project root path")] = Path("."),
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file")] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = True,
) -> None:
    """Generate code map of pheno namespace references."""
    codemap = generate_codemap(path)

    if json_output:
        content = json.dumps(codemap, indent=2)
    else:
        content = format_codemap(codemap)

    if output:
        output.write_text(content)
        typer.echo(f"Code map written to {output}")
    else:
        typer.echo(content)


# Version Command
@app.command("version")
def version_command() -> None:
    """Show version information."""
    typer.echo(f"pheno-utils version {__version__}")


def main() -> Any:
    """Entry point for the CLI."""
    return app()


if __name__ == "__main__":
    main()
