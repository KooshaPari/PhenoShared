"""phenotype-py-extras/llms-txt CLI."""

from __future__ import annotations

from pathlib import Path

import click

from .core import load_config, write_llms_txt


@click.command()
@click.option("--out", default="llms.txt", type=click.Path(), help="Output file")
@click.option("--config", default="pheno-llms-txt.yaml", type=click.Path(), help="Config YAML")
def main(out: str, config: str) -> None:
    """Render an llms.txt from a config and write to disk."""
    cfg = load_config(Path(config))
    write_llms_txt(cfg, Path(out))
    click.echo(f"Wrote {out}")


if __name__ == "__main__":
    main()
