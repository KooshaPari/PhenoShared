"""Root conftest for HexaKit Python tests.

Handles module availability and provides skip markers for tests
that require external dependencies.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add src to path for local source imports
# Handle both direct run (from python/) and parent run (from HexaKit with python/ path)
test_dir = Path(__file__).parent.resolve()
python_dir = test_dir.parent
src_path = python_dir / "src"
if src_path.exists() and str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))
