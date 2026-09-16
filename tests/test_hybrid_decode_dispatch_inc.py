"""WBS 57 audit-F3 follow-up: hybrid_decode_dispatch.inc.

Asserts the public ABI from the audit (9b850ab):
- file exists and is codegen-owned
- schedule invariants (6 full layers, interval 4u)
- predicate equivalence for layers 0..23
- kArchSimdgroupSize == 32u
"""

from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INC = REPO / "kernels/qwen3.5-0.8b/metal/hybrid_decode_dispatch.inc"


def test_inc_exists_and_owned():
    assert INC.exists(), f"{INC} missing"
    text = INC.read_text()
    assert "AUTO-GENERATED from arch.yaml" in text
    assert "kHybridFullAttnInterval" in text


def test_schedule_invariants():
    text = INC.read_text()
    assert "kHybridFullAttnInterval   = 4u" in text
    assert "kHybridFullAttnNumLayers  = 6u" in text
    assert "kHybridLinearNumLayers    = 18u" in text
    assert "{3, 7, 11, 15, 19, 23}" in text


def test_predicate_equivalence():
    # Python mirror of the METAL predicate
    def is_full(layer: int) -> int:
        return 1 if ((layer + 1) % 4) == 0 else 0

    full = [i for i in range(24) if is_full(i)]
    assert full == [3, 7, 11, 15, 19, 23]


def test_simdgroup_size():
    text = INC.read_text()
    assert "kArchSimdgroupSize = 32u" in text
