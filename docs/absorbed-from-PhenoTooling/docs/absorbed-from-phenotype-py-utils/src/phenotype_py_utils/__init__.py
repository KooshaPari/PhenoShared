"""phenotype-py-utils: shared Python utility library for the Phenotype org.

This package consolidates a small set of utility functions that are commonly
copied across Python projects in the Phenotype org. By depending on this
library, downstream repos get a single canonical implementation that is
tested, typed, and follows the org's quality bar (mypy strict, ruff clean,
pytest with coverage).

Public API:
    load_config: load YAML/TOML/JSON config from a path with env-var override
    setup_logging: configure stdlib logging with sensible defaults
    parse_args: parse CLI args with a typed dataclass return value
    iso_now: get the current UTC time as an ISO 8601 string
    truncate: truncate a string with an ellipsis suffix

Sub-packages:
    extras: optional dependency groups (cli, mcp, web, testing)
    extras.llms_txt: llms.txt renderer (requires extras[cli] + pyyaml)
"""

from __future__ import annotations

from phenotype_py_utils.args import ArgError, parse_args
from phenotype_py_utils.config import ConfigError, load_config
from phenotype_py_utils.datetime import from_unix, iso_now
from phenotype_py_utils.logging import JsonFormatter, setup_logging
from phenotype_py_utils.string import slugify, truncate

__all__ = [
    "ArgError",
    "ConfigError",
    "JsonFormatter",
    "extras",
    "from_unix",
    "iso_now",
    "load_config",
    "parse_args",
    "setup_logging",
    "slugify",
    "truncate",
]

__version__ = "0.2.0"
