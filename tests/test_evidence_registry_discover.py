"""Tests for ``pheno.evidence.store.discover`` and ``discover_all``.

These cover the public parent-module adapter lookup API. Production
code (``scripts/evidence_registry_discover.py``) uses this API so
tests can patch adapters via
``patch.object(scripts.evidence_registry, "HuggingFaceAdapter", ...)``.
"""

from __future__ import annotations

import unittest

from pheno.evidence import store as store_module
from pheno.evidence.adapters import (
    ArxivAdapter,
    GitHubAdapter,
    HuggingFaceAdapter,
    LocalCorpusAdapter,
    ModelScopeAdapter,
    RedditAdapter,
)
from pheno.evidence.store import discover, discover_all


class DiscoverTests(unittest.TestCase):
    def test_discover_returns_all_adapters(self) -> None:
        table = discover()
        self.assertEqual(
            set(table),
            {"arxiv", "github", "hf", "local_corpus", "modelscope", "reddit"},
        )
        self.assertIs(table["arxiv"], ArxivAdapter)
        self.assertIs(table["github"], GitHubAdapter)
        self.assertIs(table["hf"], HuggingFaceAdapter)
        self.assertIs(table["local_corpus"], LocalCorpusAdapter)
        self.assertIs(table["modelscope"], ModelScopeAdapter)
        self.assertIs(table["reddit"], RedditAdapter)

    def test_discover_all_returns_all_adapters(self) -> None:
        table = discover_all()
        self.assertEqual(
            set(table),
            {"arxiv", "github", "hf", "local_corpus", "modelscope", "reddit"},
        )
        self.assertEqual(set(table), set(discover()))

    def test_discover_is_in_all_exports(self) -> None:
        self.assertIn("discover", store_module.__all__)
        self.assertIn("discover_all", store_module.__all__)

    def test_discover_returns_classes_not_instances(self) -> None:
        table = discover()
        for kind, cls in table.items():
            self.assertTrue(
                isinstance(cls, type),
                f"{kind} adapter should be a class, got {type(cls).__name__}",
            )

    def test_discover_is_idempotent(self) -> None:
        # Each call returns a fresh dict (we may want caching later, but
        # for now each call must rebuild so monkey-patching tests work).
        first = discover()
        second = discover()
        self.assertEqual(first, second)
        self.assertIsNot(first, second)


if __name__ == "__main__":
    unittest.main()
