"""phenotype-py-extras/llms-txt: Generate llms.txt files for Phenotype repos.

Absorbed from ``KooshaPari/pheno-llms-txt`` (2026-06-18, L5-111).

See ``docs/llms-txt-spec.md`` for the full spec, ``docs/llms.txt`` for the
dogfood artifact.
"""

from __future__ import annotations

from phenotype_py_extras.llms_txt.core import LlmConfig, load_config, render, write_llms_txt
from phenotype_py_extras.llms_txt.cli import main as cli_main

__all__ = [
    "LlmConfig",
    "render",
    "load_config",
    "write_llms_txt",
    "cli_main",
]
