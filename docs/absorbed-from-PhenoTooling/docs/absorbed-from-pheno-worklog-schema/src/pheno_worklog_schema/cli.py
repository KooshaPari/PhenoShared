"""pheno-worklog-schema CLI."""

from __future__ import annotations

from pathlib import Path

import click

from .schema import parse_worklog, validate_entry


@click.command()
@click.argument("worklog", type=click.Path(exists=True), default="WORKLOG.md")
def validate_cmd(worklog: str) -> None:
    """Validate WORKLOG.md (default: ./WORKLOG.md)."""
    entries = parse_worklog(Path(worklog))
    if not entries:
        click.echo(f"No WORKLOG v2 table found in {worklog}")
        raise click.exceptions.Exit(1)
    n_err = 0
    for i, e in enumerate(entries, 1):
        errs = validate_entry(e)
        if errs:
            n_err += 1
            click.echo(f"Row {i} ({e.date} {e.task_id}):")
            for msg in errs:
                click.echo(f"  - {msg}")
    click.echo(f"\n{len(entries)} entries, {n_err} with errors")
    raise click.exceptions.Exit(1 if n_err else 0)


if __name__ == "__main__":
    validate_cmd()
