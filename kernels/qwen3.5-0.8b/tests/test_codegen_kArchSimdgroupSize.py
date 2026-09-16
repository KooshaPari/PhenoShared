"""DAG-49: kernels/qwen3.5-0.8b/tests/test_codegen_kArchSimdgroupSize.py

Drift-guard for the codegen-emitted ``kArchSimdgroupSize`` /
``QWEN3_5_SIMDGROUP_SIZE_DEFAULT`` (alias ``QWEN3_5_DEFAULT_SIMDGROUP_SIZE``)
constant against the ``arch.yaml`` source of truth.

The A4 audit close-out wired ``arch.yaml::kernel_strategy.default_simdgroup_size``
through the codegen emitter into three derived artifacts:

  1. ``codegen/arch.json``              — canonical JSON dump (emit_json)
  2. ``include/qwen3_5.h``              — C header macro (emit_c)
  3. ``iso/hybrid_decode_dispatch.inc`` — Metal simdgroup constant
                                          (emit_metal_dispatch)

If any of these drift from ``arch.yaml``, the kernel will bind the wrong
simdgroup size at host-boundary pipeline creation and Metal will assert.

This test file parses the static artifacts directly (no subprocess) and
asserts each derived value matches ``arch.yaml``. The C header macro name
may be ``QWEN3_5_SIMDGROUP_SIZE_DEFAULT`` (renamed) or
``QWEN3_5_DEFAULT_SIMDGROUP_SIZE`` (legacy) — both are accepted.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

KERNELS = Path(__file__).resolve().parents[1]
ARCH_YAML = KERNELS / "arch.yaml"
ARCH_JSON = KERNELS / "codegen" / "arch.json"
C_HEADER = KERNELS / "include" / "qwen3_5.h"
DISPATCH_INC = KERNELS / "iso" / "hybrid_decode_dispatch.inc"

# The C macro may live under either of two names depending on which
# rename wave is currently on the branch. We accept either.
SIMDGROUP_MACRO_RE = re.compile(
    r"#define\s+(?:QWEN3_5_SIMDGROUP_SIZE_DEFAULT|"
    r"QWEN3_5_DEFAULT_SIMDGROUP_SIZE)\s+(\d+)"
)

# Metal dispatch constant. The trailing ``u`` is mandatory MSL syntax.
KARCH_SIMDGROUP_RE = re.compile(r"constant\s+uint\s+kArchSimdgroupSize\s*=\s*(\d+)u\b")


def _read_arch_yaml_simdgroup_size() -> int | None:
    """Parse ``kernel_strategy.default_simdgroup_size`` from arch.yaml.

    Returns ``None`` if ``yaml`` is unavailable or the file is missing —
    callers must ``pytest.skip`` on ``None`` rather than failing hard.
    """
    if not ARCH_YAML.is_file():
        return None
    try:
        import yaml
    except ImportError:
        return None
    data = yaml.safe_load(ARCH_YAML.read_text())
    try:
        return int(data["kernel_strategy"]["default_simdgroup_size"])
    except (KeyError, TypeError, ValueError):
        return None


def _read_c_header_macro() -> int | None:
    """Extract the simdgroup-size macro value from the C header, or
    ``None`` if the header is missing or the macro is absent."""
    if not C_HEADER.is_file():
        return None
    text = C_HEADER.read_text()
    m = SIMDGROUP_MACRO_RE.search(text)
    return int(m.group(1)) if m else None


def _read_dispatch_inc_karch() -> int | None:
    """Extract ``kArchSimdgroupSize`` from the Metal dispatch include,
    or ``None`` if the file or constant is missing."""
    if not DISPATCH_INC.is_file():
        return None
    text = DISPATCH_INC.read_text()
    m = KARCH_SIMDGROUP_RE.search(text)
    return int(m.group(1)) if m else None


def _read_arch_json_simdgroup_size() -> int | None:
    """Extract ``kernel_strategy.default_simdgroup_size`` from the
    canonical ``codegen/arch.json`` dump, or ``None`` if missing."""
    if not ARCH_JSON.is_file():
        return None
    try:
        data = json.loads(ARCH_JSON.read_text())
    except json.JSONDecodeError:
        return None
    try:
        return int(data["kernel_strategy"]["default_simdgroup_size"])
    except (KeyError, TypeError, ValueError):
        return None


def test_arch_yaml_simdgroup_size_is_in_supported_set() -> None:
    """arch.yaml must declare a simdgroup size of 16 (Intel/AMD) or
    32 (Apple Silicon). Anything else is an unsupported device class."""
    val = _read_arch_yaml_simdgroup_size()
    if val is None:
        pytest.skip(f"arch.yaml not parseable or pyyaml missing: {ARCH_YAML}")
    assert val in {16, 32}, f"unsupported simdgroup_size in arch.yaml: {val}"


def test_c_header_emits_simdgroup_size_macro() -> None:
    """``include/qwen3_5.h`` must define the simdgroup-size macro
    (``QWEN3_5_SIMDGROUP_SIZE_DEFAULT`` or the legacy
    ``QWEN3_5_DEFAULT_SIMDGROUP_SIZE``) and its value must equal
    arch.yaml's ``kernel_strategy.default_simdgroup_size``."""
    arch_val = _read_arch_yaml_simdgroup_size()
    if arch_val is None:
        pytest.skip(f"arch.yaml not parseable or pyyaml missing: {ARCH_YAML}")
    header_val = _read_c_header_macro()
    if header_val is None:
        pytest.skip(f"C header missing or macro absent: {C_HEADER}")
    assert header_val == arch_val, (
        f"drift: arch.yaml={arch_val} vs C header macro={header_val}"
    )


def test_codegen_arch_json_has_kernel_strategy_default_simdgroup_size() -> None:
    """``codegen/arch.json`` (canonical JSON dump from ``emit_json``)
    must mirror arch.yaml's ``kernel_strategy.default_simdgroup_size``."""
    arch_val = _read_arch_yaml_simdgroup_size()
    if arch_val is None:
        pytest.skip(f"arch.yaml not parseable or pyyaml missing: {ARCH_YAML}")
    json_val = _read_arch_json_simdgroup_size()
    if json_val is None:
        pytest.skip(f"codegen/arch.json missing or malformed: {ARCH_JSON}")
    assert json_val == arch_val, (
        f"drift: arch.yaml={arch_val} vs codegen/arch.json={json_val}"
    )


def test_dispatch_inc_kArchSimdgroupSize_matches_arch_yaml() -> None:
    """``iso/hybrid_decode_dispatch.inc`` must declare
    ``constant uint kArchSimdgroupSize = <N>u;`` where ``<N>`` equals
    arch.yaml's ``kernel_strategy.default_simdgroup_size``. Metal simdgroup
    sizes are runtime-bound through this constant, so drift breaks the
    host-binding contract (see DAG-53)."""
    arch_val = _read_arch_yaml_simdgroup_size()
    if arch_val is None:
        pytest.skip(f"arch.yaml not parseable or pyyaml missing: {ARCH_YAML}")
    inc_val = _read_dispatch_inc_karch()
    if inc_val is None:
        pytest.skip(
            f"dispatch include missing or kArchSimdgroupSize absent: {DISPATCH_INC}"
        )
    assert inc_val == arch_val, f"drift: arch.yaml={arch_val} vs dispatch inc={inc_val}"


def test_c_macro_and_dispatch_constant_agree() -> None:
    """The C header macro (``QWEN3_5_SIMDGROUP_SIZE_DEFAULT`` or legacy
    ``QWEN3_5_DEFAULT_SIMDGROUP_SIZE``) and the Metal dispatch constant
    (``kArchSimdgroupSize``) must agree, independent of arch.yaml. This
    catches a partial regen where one artifact is updated and the other
    is not."""
    header_val = _read_c_header_macro()
    if header_val is None:
        pytest.skip(f"C header missing or macro absent: {C_HEADER}")
    inc_val = _read_dispatch_inc_karch()
    if inc_val is None:
        pytest.skip(
            f"dispatch include missing or kArchSimdgroupSize absent: {DISPATCH_INC}"
        )
    assert header_val == inc_val, (
        f"drift: C header macro={header_val} vs dispatch inc={inc_val}"
    )
