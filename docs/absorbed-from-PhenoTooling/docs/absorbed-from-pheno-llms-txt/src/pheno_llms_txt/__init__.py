"""pheno-llms-txt: generate llms.txt files for Phenotype repos."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .core import LlmConfig, render, load_config, write_llms_txt

__all__ = [
    "LlmConfig",
    "render",
    "load_config",
    "write_llms_txt",
    "init_llms",
]
__version__ = "0.1.0"


def init_llms(repo_dir: Path | str) -> dict[str, Any]:
    """V6 PR-3 scaffold-kit entrypoint.

    Bootstrap an llms.txt for ``repo_dir`` by writing a starter
    ``pheno-llms-txt.yaml`` (only if one is not already present) and
    rendering the resulting llms.txt to ``<repo_dir>/llms.txt``.

    Idempotent: re-runs are no-ops. Missing ``repo_dir`` returns
    ``{ok: False, error: "..."}`` rather than raising so the calling
    scaffold-kit orchestrator can surface the failure as a structured
    dict instead of crashing the whole run.

    Returns a dict of the form::

        {"ok": True, "llms_txt": "/abs/path/llms.txt", "repo_dir": "..."}
        {"ok": False, "error": "..."}
    """
    p = Path(repo_dir)
    if not p.exists():
        return {"ok": False, "error": f"repo_dir {p!s} does not exist", "repo_dir": str(p)}
    if not p.is_dir():
        return {"ok": False, "error": f"repo_dir {p!s} is not a directory", "repo_dir": str(p)}

    config_path = p / "pheno-llms-txt.yaml"
    if not config_path.exists():
        # Minimal starter config that callers can hand-edit.
        config_path.write_text(
            "repo_name: " + p.name + "\n"
            "tagline: One-line description.\n"
            "install:\n  - pip install " + p.name + "\n"
            "usage:\n  - " + p.name + " --help\n"
            "public_api: []\n"
            "common_errors: []\n"
            "references:\n  - https://llmstxt.org\n"
        )

    cfg = load_config(config_path)
    dest = p / "llms.txt"
    write_llms_txt(cfg, dest)
    return {"ok": True, "llms_txt": str(dest), "repo_dir": str(p)}
