"""Tests for host-guard public ABI + hybrid_decode_dispatch (P27/P28).

Covers:
- P27: host-guard public ABI — TaskStatus.WRONG vs PASS contract
- P28: hybrid_decode_dispatch.inc presence + kArchSimdgroupSize binding
"""

from __future__ import annotations

from pathlib import Path

from bench.types import TaskStatus


class TestHostGuardPublicABI:
    """P27: TaskStatus.WRONG vs PASS public ABI contract."""

    def test_wrong_is_distinct_from_pass(self) -> None:
        """WRONG and PASS are distinct members."""
        assert TaskStatus.WRONG is not TaskStatus.PASS
        assert TaskStatus.WRONG != TaskStatus.PASS

    def test_wrong_wire_value(self) -> None:
        """WRONG serializes to 'wrong' (not 'fail')."""
        assert TaskStatus.WRONG == "wrong"

    def test_pass_wire_value(self) -> None:
        """PASS serializes to 'ok' (not 'pass')."""
        assert TaskStatus.PASS == "ok"

    def test_pass_in_ok_set(self) -> None:
        """PASS is in the set {OK} — host-guard accepts both."""
        assert TaskStatus.PASS in {TaskStatus.OK}

    def test_fail_in_wrong_set(self) -> None:
        """FAIL is in the set {WRONG} — host-guard accepts both."""
        assert TaskStatus.FAIL in {TaskStatus.WRONG}


class TestHybridDecodeDispatch:
    """P28: hybrid_decode_dispatch.inc presence and contract."""

    def test_inc_file_exists(self) -> None:
        """hybrid_decode_dispatch.inc exists in the kernel tree."""
        inc = Path("kernels/qwen3.5-0.8b/iso/hybrid_decode_dispatch.inc")
        assert inc.exists(), f"Missing {inc}"

    def test_inc_file_has_header_guard(self) -> None:
        """File has proper header guard."""
        inc = Path("kernels/qwen3.5-0.8b/iso/hybrid_decode_dispatch.inc")
        content = inc.read_text(encoding="utf-8")
        assert "#ifndef QWEN_HYBRID_DECODE_DISPATCH_INC" in content
        assert "#define QWEN_HYBRID_DECODE_DISPATCH_INC" in content

    def test_inc_file_binds_simdgroup_size(self) -> None:
        """File binds kArchSimdgroupSize = 32u (matches arch.yaml)."""
        inc = Path("kernels/qwen3.5-0.8b/iso/hybrid_decode_dispatch.inc")
        content = inc.read_text(encoding="utf-8")
        assert "kArchSimdgroupSize" in content
        assert "32u" in content

    def test_inc_file_references_arch_yaml(self) -> None:
        """File comments reference arch.yaml as source of truth."""
        inc = Path("kernels/qwen3.5-0.8b/iso/hybrid_decode_dispatch.inc")
        content = inc.read_text(encoding="utf-8")
        assert "arch.yaml" in content
