"""Implementation modules for the PhenoShared codebase atlas generator.

`scripts/atlas/generate.py` is the only entry point; this package holds the
pieces, split so each module stays inside the repository's own 500-line hard /
350-line target rule.
"""

from __future__ import annotations

__all__ = [
    "definitions",
    "gitio",
    "hygiene",
    "packages",
    "readme_text",
    "render",
    "render_hygiene",
    "scan",
]
