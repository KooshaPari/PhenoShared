"""Phenotype SDK initialization."""

from pathlib import Path


def init_phenotype(repo_root: str | Path | None = None) -> None:
    """Open or create the .phenotype/config.db for this repo."""
    try:
        import phenotype_config
    except ImportError:
        return  # SDK not installed, skip silently

    if repo_root is None:
        repo_root = Path.cwd()
    else:
        repo_root = Path(repo_root)

    db_path = str(repo_root / ".phenotype" / "config.db")
    # Touch the DB so schema is created on first run
    _config = phenotype_config.PhenoConfig(db_path)
    _flags = phenotype_config.FeatureFlags(db_path)
