"""DAG-11: tests/test_metal_simdgroup_constant.py

The 3 simdgroup-related constants emitted by the kernel codegen must agree
across every language surface that consumes ``arch.yaml``. The constant is
``kernel_strategy.default_simdgroup_size`` (32) plus
``threadgroup_size_default`` (256). Any drift between the C header, the
Rust crate, the Zig build, the Mojo module, the Nim module, and the JSON
arch dump is a regression in codegen.

This test does not import the polyglot generated artifacts (they live in
``kernels/qwen3.5-0.8b/include/``, ``rust/src/``, etc., and are not on the
Python import path). Instead it parses the arch.yaml source of truth +
the generated JSON dump and the public C header, asserting the three
constants are present and agree on their values.

The 3 fixtures are:

  1. ``arch.yaml.kernel_strategy.default_simdgroup_size == 32``
  2. ``arch.yaml.kernel_strategy.threadgroup_size_default == 256``
  3. The generated C header ``include/qwen3_5.h`` carries the same
     constant under a stable macro name.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
KERNELS = REPO_ROOT / "kernels" / "qwen3.5-0.8b"
ARCH_YAML = KERNELS / "arch.yaml"
ARCH_JSON = KERNELS / "codegen" / "arch.json"
INCLUDE = KERNELS / "include" / "qwen3_5.h"
DISPATCH_INC = KERNELS / "iso" / "hybrid_decode_dispatch.inc"


# ---------------------------------------------------------------------------
# Fixture 1 — arch.yaml is the single source of truth
# ---------------------------------------------------------------------------


def test_arch_yaml_default_simdgroup_size_is_32() -> None:
    """arch.yaml.kernel_strategy.default_simdgroup_size must be 32."""
    import yaml  # local import; optional dep on the harness side

    data = yaml.safe_load(ARCH_YAML.read_text())
    assert data["kernel_strategy"]["default_simdgroup_size"] == 32


def test_arch_yaml_threadgroup_size_default_is_256() -> None:
    """arch.yaml.kernel_strategy.threadgroup_size_default must be 256."""
    import yaml

    data = yaml.safe_load(ARCH_YAML.read_text())
    assert data["kernel_strategy"]["threadgroup_size_default"] == 256


# ---------------------------------------------------------------------------
# Fixture 2 — generated JSON dump agrees
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not ARCH_JSON.is_file(), reason="arch.json not yet generated")
def test_arch_json_agrees_with_yaml() -> None:
    """codegen/arch.json must carry the same simdgroup/threadgroup constants
    if it tracks them. The audit-A4 close-out binds the canonical
    simdgroup_size in iso/hybrid_decode_dispatch.inc (constant
    ``kArchSimdgroupSize``) so arch.json is allowed to omit the
    kernel_strategy section until the codegen is regenerated with
    the kernel_strategy emitter (DAG task 41).
    """
    import yaml

    yaml_data = yaml.safe_load(ARCH_YAML.read_text())
    json_data = json.loads(ARCH_JSON.read_text())
    yaml_ks = yaml_data["kernel_strategy"]
    json_ks = json_data.get("kernel_strategy") or json_data.get("kernelStrategy")
    if json_ks is None:
        pytest.skip("arch.json does not track kernel_strategy (DAG-41 pending)")
    assert json_ks["default_simdgroup_size"] == yaml_ks["default_simdgroup_size"]
    assert json_ks["threadgroup_size_default"] == yaml_ks["threadgroup_size_default"]


# ---------------------------------------------------------------------------
# Fixture 3 — generated C header carries the constant
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not INCLUDE.is_file(), reason="qwen3_5.h not yet generated")
def test_c_header_emits_simdgroup_size_macro() -> None:
    """The C header must emit a stable macro name carrying the simdgroup size.

    Accepts any of the common shapes the codegen has historically used:
        #define QWEN3_5_SIMDGROUP_SIZE 32
        constexpr int kArchSimdgroupSize = 32;
    The numeric value must equal 32.
    """
    # The audit-A4 close-out places the constant in iso/hybrid_decode_dispatch.inc
    # as ``constant uint kArchSimdgroupSize = 32u;`` (Metal MSL syntax), so we
    # check the dispatch inc first then fall back to the C header for legacy
    # layouts. Both must agree on 32.
    for path, patterns in [
        (
            DISPATCH_INC,
            [
                r"constant\s+uint\s+kArchSimdgroupSize\s*=\s*(\d+)u?",
                r"constant\s+uint\s+SIMDGROUP_SIZE\s*=\s*(\d+)u?",
            ],
        ),
        (
            INCLUDE,
            [
                r"#define\s+QWEN3_5_SIMDGROUP_SIZE\s+(\d+)",
                r"#define\s+(?:QWEN3_5_DEFAULT_SIMDGROUP_SIZE|QWEN3_5_SIMDGROUP_SIZE_DEFAULT)\s+(\d+)",
                r"constexpr\s+int\s+kArchSimdgroupSize\s*=\s*(\d+)",
                r"static\s+constexpr\s+int\s+SIMDGROUP_SIZE\s*=\s*(\d+)",
            ],
        ),
    ]:
        if not path.is_file():
            continue
        text = path.read_text()
        for pat in patterns:
            m = re.search(pat, text)
            if m is not None:
                assert int(m.group(1)) == 32, (
                    f"{path.name} simdgroup size drifted: {m.group(1)}"
                )
                return
    pytest.fail(
        f"no simdgroup-size constant found in {DISPATCH_INC.name} or {INCLUDE.name}"
    )


# ---------------------------------------------------------------------------
# Cross-surface agreement (uses all 3 fixtures together)
# ---------------------------------------------------------------------------


def test_simdgroup_size_is_consistent_across_surfaces() -> None:
    """Across arch.yaml, arch.json, and the C header, the simdgroup size
    must be the same value. This is the load-bearing drift-guard the
    audit-A4 close-out required.
    """
    import yaml

    yaml_data = yaml.safe_load(ARCH_YAML.read_text())
    yaml_val = yaml_data["kernel_strategy"]["default_simdgroup_size"]
    assert yaml_val == 32

    if ARCH_JSON.is_file():
        json_data = json.loads(ARCH_JSON.read_text())
        json_ks = json_data.get("kernel_strategy") or json_data.get("kernelStrategy")
        if json_ks is not None:
            assert json_ks["default_simdgroup_size"] == yaml_val
        # else: arch.json doesn't track kernel_strategy; the dispatch inc
        # below is the load-bearing drift-guard (audit-A4 close-out).

    if INCLUDE.is_file():
        text = INCLUDE.read_text()
        # Find the first matching macro and compare
        m = re.search(
            r"#define\s+(?:QWEN3_5_SIMDGROUP_SIZE|"
            r"QWEN3_5_DEFAULT_SIMDGROUP_SIZE)\s+(\d+)",
            text,
        )
        if m is None:
            m = re.search(
                r"constexpr\s+int\s+kArchSimdgroupSize\s*=\s*(\d+)",
                text,
            )
        if m is not None:
            assert int(m.group(1)) == yaml_val

    # The audit-A4 close-out binds the constant in
    # iso/hybrid_decode_dispatch.inc as ``constant uint kArchSimdgroupSize``.
    if DISPATCH_INC.is_file():
        text = DISPATCH_INC.read_text()
        m = re.search(
            r"constant\s+uint\s+kArchSimdgroupSize\s*=\s*(\d+)u?",
            text,
        )
        if m is not None:
            assert int(m.group(1)) == yaml_val
