"""phenotype-py-utils/extras: optional dependency groups absorbed from phenotype-py-extras.

This subpackage re-exports popular third-party libraries lazily (PEP 562) so
that importing ``phenotype_py_utils.extras`` never pulls in transitive
dependencies. Accessing a sub-attribute only fails when the corresponding
optional dep group is not installed.

Groups:

.. list-table::
   :header-rows: 1

   * - Group
     - Libraries
   * - ``cli``
     - click, rich, typer, pydantic
   * - ``mcp``
     - fastmcp, pydantic, pydantic-settings, httpx
   * - ``web``
     - fastapi, uvicorn, pydantic, pydantic-settings
   * - ``testing``
     - pytest, pytest-asyncio, pytest-cov
   * - ``observability``
     - structlog, loguru
   * - ``all``
     - everything above
"""

from __future__ import annotations

__all__ = ["__version__"]
__version__ = "0.2.0"
