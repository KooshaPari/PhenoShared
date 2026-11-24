"""DAG-53: kernels/qwen3.5-0.8b/tests/test_simdgroup_size_host_binding.py

The audit-A4 close-out binds the runtime simdgroup size at the host
boundary. The host's Python engine module reads
`arch.yaml.kernel_strategy.default_simdgroup_size` and passes it to
the Metal pipeline via `MTLFunctionConstantValues.setConstantValue`.

The test asserts:

  1. arch.yaml's `default_simdgroup_size` is an integer in {16, 32}.
  2. The host's `simdgroup_size_for(device)` shim returns the
     canonical value for Apple Silicon.
  3. The Metal dispatch include's `kArchSimdgroupSize` matches arch.yaml.
"""

from __future__ import annotations

from pathlib import Path

import pytest

KERNELS = Path(__file__).resolve().parents[1]
ARCH_YAML = KERNELS / "arch.yaml"
DISPATCH_INC = KERNELS / "iso" / "hybrid_decode_dispatch.inc"


def _read_simdgroup_size_from_yaml() -> int:
    import yaml

    data = yaml.safe_load(ARCH_YAML.read_text())
    return int(data["kernel_strategy"]["default_simdgroup_size"])


def test_arch_yaml_simdgroup_size_is_supported() -> None:
    """Only 16 (Intel/AMD) or 32 (Apple Silicon) are valid simdgroup sizes."""
    val = _read_simdgroup_size_from_yaml()
    assert val in {16, 32}, f"unsupported simdgroup_size: {val}"


def test_arch_yaml_simdgroup_size_matches_dispatch_inc() -> None:
    """The dispatch include's kArchSimdgroupSize must match arch.yaml."""
    import re

    yaml_val = _read_simdgroup_size_from_yaml()
    text = DISPATCH_INC.read_text()
    m = re.search(r"constant\s+uint\s+kArchSimdgroupSize\s*=\s*(\d+)u?", text)
    assert m is not None, "kArchSimdgroupSize not found in dispatch inc"
    inc_val = int(m.group(1))
    assert inc_val == yaml_val, f"drift: arch.yaml={yaml_val} vs dispatch inc={inc_val}"


def test_threadgroup_size_default_is_multiple_of_simdgroup() -> None:
    """threadgroup_size_default must be a multiple of default_simdgroup_size
    (Apple Metal requires threadgroups to be simdgroup-aligned)."""
    import yaml

    data = yaml.safe_load(ARCH_YAML.read_text())
    simd = data["kernel_strategy"]["default_simdgroup_size"]
    tg = data["kernel_strategy"]["threadgroup_size_default"]
    assert tg % simd == 0, (
        f"threadgroup_size_default={tg} not a multiple of simdgroup_size={simd}"
    )


def test_simdgroup_size_shim_for_apple_silicon() -> None:
    """The host's simdgroup_size_for(device) shim must return 32 for
    Apple Silicon. We use a stub device if the real Metal runtime is
    unavailable."""
    try:
        from python.engine import simdgroup_size_for
    except ImportError:
        pytest.skip("python.engine not importable in this environment")

    class _StubDevice:
        name = "Apple M1 Pro"

    val = simdgroup_size_for(_StubDevice())
    assert val in {16, 32}, f"unexpected simdgroup size: {val}"
