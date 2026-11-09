"""Backend package for 4SGM chatbot services."""

import sys

# Python version requirements: CPython 3.14+ or PyPy 3.11+
if sys.implementation.name == "cpython" and sys.version_info < (3, 12):
    raise RuntimeError("4SGM backend requires CPython 3.12+. For PyPy, use PyPy 3.11+")
if sys.implementation.name == "pypy" and sys.version_info < (3, 11):
    raise RuntimeError("4SGM backend requires PyPy 3.11+. For CPython, use 3.12+")
