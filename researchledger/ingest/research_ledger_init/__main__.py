"""Entry point so `python3 -m research_ledger_init --help` works.

This mirrors the original `python3 research_ledger_init.py --help` CLI
that the file-based module exposed. Delegates to the package-level
`main()` defined in `__init__.py`.
"""

import sys

from . import main

if __name__ == "__main__":
    sys.exit(main())
