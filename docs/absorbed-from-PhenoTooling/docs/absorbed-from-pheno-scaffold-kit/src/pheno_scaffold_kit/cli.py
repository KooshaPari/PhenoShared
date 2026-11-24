"""Command-line interface for pheno-scaffold-kit."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from pheno_scaffold_kit import (
    detect_repo_type,
    init_llms,
    init_prompt_test,
    init_scaffold,
    init_worklog,
    install_hooks,
)
from pheno_scaffold_kit import _framework_lint as _fl
from pheno_scaffold_kit import _drift_detector as _dd
from pheno_scaffold_kit import _predict as _pr


def _repo_path(repo_dir: str) -> Path:
    path = Path(repo_dir).expanduser().resolve()
    if not path.exists():
        raise click.ClickException(f"Repository directory does not exist: {path}")
    if not path.is_dir():
        raise click.ClickException(f"Repository path is not a directory: {path}")
    return path


def _emit(result: Any, json_output: bool) -> None:
    if json_output:
        click.echo(json.dumps(result, indent=2, sort_keys=True, default=str))
    else:
        click.echo("done")


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def cli() -> None:
    """Phenotype scaffold umbrella CLI."""


@cli.command("init")
@click.argument("repo_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=str))
@click.option("--json", "json_output", is_flag=True, help="Print structured JSON output.")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Print the sub-step plan without executing (V6 PR-7).",
)
def init_command(repo_dir: str, json_output: bool, dry_run: bool) -> None:
    """Detect repo type and run all scaffold setup steps."""
    root = _repo_path(repo_dir)
    repo_type = detect_repo_type(root)
    plan = {
        "repo_dir": str(root),
        "repo_type": repo_type,
        "steps": [
            {"name": "llms", "fn": "init_llms"},
            {"name": "prompt_test", "fn": "init_prompt_test"},
            {"name": "hooks", "fn": "install_hooks"},
            {"name": "worklog", "fn": "init_worklog"},
        ],
    }
    if dry_run:
        if json_output:
            click.echo(json.dumps(plan, indent=2, sort_keys=True, default=str))
        else:
            click.echo(f"Plan for {root}:")
            for step in plan["steps"]:
                click.echo(f"  - {step['name']} ({step['fn']})")
        return
    click.echo(f"Initializing scaffold for {root}", err=True)
    click.echo(f"Detected: {', '.join(k for k, v in repo_type.items() if v) or 'generic'}", err=True)
    _emit(init_scaffold(root, repo_type=repo_type), json_output)


@cli.command("init-llms")
@click.argument("repo_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=str))
@click.option("--json", "json_output", is_flag=True, help="Print structured JSON output.")
def init_llms_command(repo_dir: str, json_output: bool) -> None:
    """Initialize llms.txt context files."""
    _emit(init_llms(_repo_path(repo_dir)), json_output)


@cli.command("init-prompt-test")
@click.argument("repo_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=str))
@click.option("--json", "json_output", is_flag=True, help="Print structured JSON output.")
def init_prompt_test_command(repo_dir: str, json_output: bool) -> None:
    """Initialize prompt-test configuration."""
    _emit(init_prompt_test(_repo_path(repo_dir)), json_output)


@cli.command("install-hooks")
@click.argument("repo_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=str))
@click.option("--json", "json_output", is_flag=True, help="Print structured JSON output.")
def install_hooks_command(repo_dir: str, json_output: bool) -> None:
    """Install vibecoding guard hooks."""
    _emit(install_hooks(_repo_path(repo_dir)), json_output)


@cli.command("init-worklog")
@click.argument("repo_dir", type=click.Path(file_okay=False, dir_okay=True, path_type=str))
@click.option("--json", "json_output", is_flag=True, help="Print structured JSON output.")
def init_worklog_command(repo_dir: str, json_output: bool) -> None:
    """Initialize worklog schema files."""
    _emit(init_worklog(_repo_path(repo_dir)), json_output)


# ---------------------------------------------------------------------------
# Absorbed 2026-06-19: pheno-framework-lint (L73, ADR-048)
# ---------------------------------------------------------------------------


@cli.group("framework-lint")
def framework_lint_group() -> None:
    """Substrate graduation & tier-convention linter (L73, ADR-048)."""


@framework_lint_group.command("check")
@click.option("--path", required=True, help="Path to a single repository to check.")
def framework_lint_check(path: str) -> None:
    """Check a single repo against ADR-048 tier conventions."""
    rc = _fl.cmd_check(_fl.argparse.Namespace(path=path))
    raise SystemExit(rc)


@framework_lint_group.command("check-all")
@click.option("--root", required=True, help="Root directory of repos to scan.")
@click.option("--out", default=None, help="Write output to file (default stdout).")
def framework_lint_check_all(root: str, out: str | None) -> None:
    """Check all repos under a root for tier-convention violations."""
    rc = _fl.cmd_check_all(_fl.argparse.Namespace(root=root, out=out))
    raise SystemExit(rc)


# ---------------------------------------------------------------------------
# Absorbed 2026-06-19: pheno-drift-detector (L74, ADR-049)
# ---------------------------------------------------------------------------


@cli.group("drift-detector")
def drift_detector_group() -> None:
    """App-substrate drift detector (L74, ADR-049)."""


@drift_detector_group.command("scan")
@click.option("--root", required=True, help="Root directory containing app repos.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "md", "gh-issues"], case_sensitive=False),
    default="json",
    show_default=True,
)
@click.option("--out", default=None, help="Write output to file (default stdout).")
def drift_detector_scan(root: str, fmt: str, out: str | None) -> None:
    """Scan fleet for drift hits."""
    rc = _dd.cmd_scan(_dd.argparse.Namespace(root=root, format=fmt.lower(), out=out))
    raise SystemExit(rc)


@drift_detector_group.command("validate")
@click.option("--hit", required=True, help="Path to a hit JSON file.")
@click.option("--yes", is_flag=True, help="Auto-confirm validation.")
def drift_detector_validate(hit: str, yes: bool) -> None:
    """Validate a single drift hit (HITL gate)."""
    rc = _dd.cmd_validate(_dd.argparse.Namespace(hit=hit, yes=yes))
    raise SystemExit(rc)


# ---------------------------------------------------------------------------
# Absorbed 2026-06-19: pheno-predict (L72, ADR-047)
# ---------------------------------------------------------------------------


@cli.group("predict")
def predict_group() -> None:
    """Fleet-wide similar-code scanner (L72, ADR-047)."""


@predict_group.command("scan")
@click.option("--target", required=True, help="Target repo path.")
@click.option("--baseline", required=True, multiple=True, help="Baseline repo path(s).")
@click.option(
    "--threshold",
    type=float,
    default=_pr.DEFAULT_THRESHOLD,
    show_default=True,
    help=f"Jaccard threshold (default {_pr.DEFAULT_THRESHOLD})",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "csv", "md"], case_sensitive=False),
    default="md",
    show_default=True,
)
@click.option("--out", default=None, help="Write output to file (default stdout).")
def predict_scan(
    target: str,
    baseline: tuple[str, ...],
    threshold: float,
    fmt: str,
    out: str | None,
) -> None:
    """Scan target vs baseline for similar code."""
    rc = _pr.cmd_scan(
        _pr.argparse.Namespace(
            target=target,
            baseline=list(baseline),
            threshold=threshold,
            format=fmt.lower(),
            out=out,
        )
    )
    raise SystemExit(rc)


@predict_group.command("check-criteria")
@click.option("--candidate", required=True, help="JSON candidate object.")
def predict_check_criteria(candidate: str) -> None:
    """Run 4 ADR-047 criteria check on a candidate."""
    rc = _pr.cmd_check_criteria(_pr.argparse.Namespace(candidate=candidate))
    raise SystemExit(rc)


if __name__ == "__main__":
    cli()
