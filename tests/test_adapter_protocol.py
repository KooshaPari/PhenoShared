"""TypedAdapter Protocol conformance tests.

Asserts that every concrete ``bench`` adapter (MockModel, MLXStubAdapter,
HttpOpenAI, HttpAnthropic, HttpGemini, LocalPhenoAdapter) satisfies the
``TypedAdapter`` Protocol from bench.adapters_typing, and that every
concrete ``bench.runner`` adapter satisfies bench.runner.adapters_typing.
"""

from __future__ import annotations

import unittest

from bench.adapters_typing import TypedAdapter as TopTypedAdapter
from bench.mlx_stub import MLXStubAdapter as TopMLXStub
from bench.runner.adapters_typing import TypedAdapter as RunnerTypedAdapter
from bench.runner.model_adapter_mock import MLXStubAdapter as RunnerMLXStub


class TypedAdapterConformanceTests(unittest.TestCase):
    """Every concrete bench adapter must satisfy TypedAdapter."""

    def test_mock_model_satisfies_typed_adapter(self) -> None:
        from bench.adapters_mock import MockModel

        m = MockModel()
        self.assertIsInstance(m, TopTypedAdapter)

    def test_mlx_stub_satisfies_typed_adapter(self) -> None:
        m = TopMLXStub(seed=0)
        self.assertIsInstance(m, TopTypedAdapter)

    def test_http_openai_satisfies_typed_adapter(self) -> None:
        from bench.adapters import HttpOpenAI

        a = HttpOpenAI(base_url="https://api.openai.com/v1", api_key="sk-test")
        self.assertIsInstance(a, TopTypedAdapter)

    def test_http_anthropic_satisfies_typed_adapter(self) -> None:
        from bench.adapters import HttpAnthropic

        a = HttpAnthropic(api_key="sk-ant-test")
        self.assertIsInstance(a, TopTypedAdapter)

    def test_http_gemini_satisfies_typed_adapter(self) -> None:
        from bench.adapters import HttpGemini

        a = HttpGemini(api_key="gem-test")
        self.assertIsInstance(a, TopTypedAdapter)

    def test_local_pheno_satisfies_typed_adapter(self) -> None:
        from bench.adapters import LocalPhenoAdapter

        a = LocalPhenoAdapter()
        self.assertIsInstance(a, TopTypedAdapter)

    def test_typed_adapter_requires_generate(self) -> None:
        """A class without generate() must NOT satisfy TypedAdapter."""

        class NotAnAdapter:
            name = "nope"

            async def aclose(self) -> None:
                pass

        self.assertNotIsInstance(NotAnAdapter(), TopTypedAdapter)

    # Runner layer checks

    def test_runner_mlx_stub_satisfies_typed_adapter(self) -> None:
        m = RunnerMLXStub(model_id="mlx-stub")
        self.assertIsInstance(m, RunnerTypedAdapter)

    def test_runner_typed_adapter_requires_complete(self) -> None:
        """A class without complete() must NOT satisfy Runner TypedAdapter."""

        class NotRunnerAdapter:
            name = "nope"

            async def aclose(self) -> None:
                pass

        self.assertNotIsInstance(NotRunnerAdapter(), RunnerTypedAdapter)


if __name__ == "__main__":
    unittest.main()
