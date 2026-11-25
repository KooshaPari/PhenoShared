"""phenotype-py-extras: shared Python extras for the Phenotype ecosystem.

The core package has zero runtime dependencies. Optional dependency groups
(``cli``, ``mcp``, ``web``, ``testing``, ``testing-quality``, ``observability``)
are re-exported lazily through PEP 562 ``__getattr__`` so that importing
``phenotype_py_extras`` never fails and accessing a sub-attribute only fails
when the corresponding extras are not installed.
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["__version__"]
