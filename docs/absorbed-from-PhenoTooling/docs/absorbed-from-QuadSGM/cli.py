#!/usr/bin/env python3
"""4SGM CLI wrapper - delegates to package CLI."""

import sys  # noqa: E402 -- sys.path manipulation must occur before imports
from pathlib import Path

# Add the package directory to the path
package_dir = Path(__file__).parent / "4sgm"
sys.path.insert(0, str(package_dir))

# Import and run the CLI
from cli import main  # noqa: E402 -- import after sys.path manipulation

if __name__ == "__main__":
    main()
