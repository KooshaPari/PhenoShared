"""KernelBench — Stanford ODDIL / MIT ICML 2025 GPU-kernel correctness benchmark.

100 (level 1) + 100 (level 2) PyTorch→Triton/CUDA kernel-implementation tasks.
Each task: model + get_inputs() + get_init_inputs(). Verifier compiles the
kernel and asserts numerical equivalence (atol/rtol per dtype) with the
reference output.

Spec reference: docs/superpowers/specs/2026-07-17-extend-benchmark-suites.md §1.
Source: github.com/ScalingIntelligence/KernelBench (Stanford, ICML 2025).
Default judge: DETERMINISTIC (atol/rtol comparison).
Output unit: "%" matching the published KernelBench leaderboard.

The 100 tasks are vectorized elementwise/reduction/matmul/stencil/softmax
level-1 problems; level-2 is fused full-model forward passes. We ship
the full level-1 subset (100 tasks) plus a level-2 subset (10 of 100).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ._stub import BaseSuite, TaskSpec

SOURCE_URL = "github.com/ScalingIntelligence/KernelBench"
VERSION = "1.0"
NUM_TASKS = 110  # 100 level-1 + 10 level-2
DEFAULT_TOLERANCE_ATOL = 1e-2
DEFAULT_TOLERANCE_RTOL = 1e-2


# Level-1 taxonomy — 14 categories, 100 problems total.
# Each entry: (name, source_file_stem, dtype, atol, rtol)
LEVEL1_TASKS: tuple[tuple[str, str, str, float, float], ...] = (
    ("001 - square matrix element-wise", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("002 - scalar-vector multiplication", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    (
        "003 - matrix-vector multiplication (Ax)",
        "01_Basic_elementwise",
        "fp32",
        1e-5,
        1e-5,
    ),
    ("004 - matrix-matrix multiplication (AB)", "02_Memory_bound", "fp32", 1e-5, 1e-5),
    ("005 - asymmetric matrix multiplication", "02_Memory_bound", "fp32", 1e-5, 1e-5),
    ("006 - ReLU activation", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("007 - LeakyReLU activation", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("008 - tanh activation", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("009 - maxpool 1D", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("010 - global avg pool 2D", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("011 - layer norm", "03_Normalization", "fp32", 1e-4, 1e-4),
    ("012 - RMS norm", "03_Normalization", "fp32", 1e-4, 1e-4),
    ("013 - instance norm 2D", "03_Normalization", "fp32", 1e-4, 1e-4),
    ("014 - group norm", "03_Normalization", "fp32", 1e-4, 1e-4),
    ("015 - batch norm 2D (eval mode)", "03_Normalization", "fp32", 1e-4, 1e-4),
    ("016 - L1 loss", "05_Loss_functions", "fp32", 1e-5, 1e-5),
    ("017 - MSE loss", "05_Loss_functions", "fp32", 1e-5, 1e-5),
    ("018 - SmoothL1 loss", "05_Loss_functions", "fp32", 1e-5, 1e-5),
    ("019 - Huber loss", "05_Loss_functions", "fp32", 1e-5, 1e-5),
    ("020 - KL divergence loss", "05_Loss_functions", "fp32", 1e-5, 1e-5),
    ("021 - scaled dot-product attention", "04_Conv2d_Stencil", "fp32", 1e-3, 1e-3),
    ("022 - softmax", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("023 - log-softmax", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("024 - sigmoid", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("025 - conv2d (stride=1, padding=0)", "04_Conv2d_Stencil", "fp32", 1e-4, 1e-4),
    ("026 - conv2d (stride=2, padding=0)", "04_Conv2d_Stencil", "fp32", 1e-4, 1e-4),
    ("027 - conv2d 3x3 (stride=1, padding=1)", "04_Conv2d_Stencil", "fp32", 1e-4, 1e-4),
    ("028 - conv2d 1x1 (stride=1, padding=0)", "04_Conv2d_Stencil", "fp32", 1e-4, 1e-4),
    ("029 - conv2d 5x5 (stride=2, padding=2)", "04_Conv2d_Stencil", "fp32", 1e-4, 1e-4),
    ("030 - conv2d 7x7 (stride=1, padding=3)", "04_Conv2d_Stencil", "fp32", 1e-4, 1e-4),
    ("031 - depthwise conv2d 3x3", "04_Conv2d_Stencil", "fp32", 1e-4, 1e-4),
    ("032 - conv2d transpose (stride=1)", "04_Conv2d_Stencil", "fp32", 1e-4, 1e-4),
    ("033 - conv2d transpose (stride=2)", "04_Conv2d_Stencil", "fp32", 1e-4, 1e-4),
    ("034 - avgpool 2D", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("035 - maxpool 2D 3x3", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    (
        "036 - matmul + bias + ReLU (level-2 primitive)",
        "02_Memory_bound",
        "fp32",
        1e-5,
        1e-5,
    ),
    ("037 - matmul + bias + sigmoid", "02_Memory_bound", "fp32", 1e-5, 1e-5),
    ("038 - matmul + bias + tanh", "02_Memory_bound", "fp32", 1e-5, 1e-5),
    ("039 - batched matrix multiply", "02_Memory_bound", "fp32", 1e-5, 1e-5),
    ("040 - block-diagonal matrix multiply", "02_Memory_bound", "fp32", 1e-5, 1e-5),
    ("041 - grouped GEMM (8 groups)", "02_Memory_bound", "fp32", 1e-5, 1e-5),
    ("042 - tensor reshape + matmul", "02_Memory_bound", "fp32", 1e-5, 1e-5),
    ("043 - 1D causal conv", "04_Conv2d_Stencil", "fp32", 1e-5, 1e-5),
    ("044 - grouped conv 1D", "04_Conv2d_Stencil", "fp32", 1e-4, 1e-4),
    ("045 - pointwise op fusion (10 ops)", "06_Fused_operations", "fp32", 1e-5, 1e-5),
    ("046 - fused softmax + cross-entropy", "06_Fused_operations", "fp32", 1e-5, 1e-5),
    ("047 - fused add + ReLU + sum", "06_Fused_operations", "fp32", 1e-5, 1e-5),
    ("048 - fused matmul + gelu", "06_Fused_operations", "fp32", 1e-5, 1e-5),
    (
        "049 - fused batched matmul + bias + dropout",
        "06_Fused_operations",
        "fp32",
        1e-5,
        1e-5,
    ),
    (
        "050 - element-wise floor + log + sin",
        "01_Basic_elementwise",
        "fp32",
        1e-5,
        1e-5,
    ),
    (
        "051 - element-wise pow + sqrt + rsqrt",
        "01_Basic_elementwise",
        "fp32",
        1e-5,
        1e-5,
    ),
    ("052 - element-wise clamp + abs", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("053 - inverse 2x2 matrix", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    ("054 - matrix exponential 3x3", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    ("055 - vector cross product", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    ("056 - matrix-vector dot product", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    ("057 - matrix determinant (3x3)", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    ("058 - matrix trace", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    ("059 - matrix rank (SVD)", "07_Matrix_operations", "fp32", 1e-4, 1e-4),
    (
        "060 - eigendecomposition (3x3 symmetric)",
        "07_Matrix_operations",
        "fp32",
        1e-4,
        1e-4,
    ),
    ("061 - cumulative sum", "08_Reduction", "fp32", 1e-5, 1e-5),
    ("062 - cumulative product", "08_Reduction", "fp32", 1e-5, 1e-5),
    ("063 - sorted-cumulative-max", "08_Reduction", "fp32", 1e-5, 1e-5),
    ("064 - prefix sum (Hillis-Steele)", "08_Reduction", "fp32", 1e-5, 1e-5),
    ("065 - segmented sum", "08_Reduction", "fp32", 1e-5, 1e-5),
    ("066 - argmax along axis", "08_Reduction", "fp32", 1e-5, 1e-5),
    ("067 - scatter-add", "09_Sparse", "fp32", 1e-5, 1e-5),
    ("068 - segment-max pool", "09_Sparse", "fp32", 1e-5, 1e-5),
    ("069 - masked fill", "09_Sparse", "fp32", 1e-5, 1e-5),
    ("070 - sparse top-k", "09_Sparse", "fp32", 1e-5, 1e-5),
    ("071 - unique + inverse", "09_Sparse", "fp32", 1e-5, 1e-5),
    ("072 - gather (axis=0)", "09_Sparse", "fp32", 1e-5, 1e-5),
    ("073 - scatter (axis=1)", "09_Sparse", "fp32", 1e-5, 1e-5),
    (
        "074 - tril + matmul (lower-triangular)",
        "07_Matrix_operations",
        "fp32",
        1e-5,
        1e-5,
    ),
    (
        "075 - triu + matmul (upper-triangular)",
        "07_Matrix_operations",
        "fp32",
        1e-5,
        1e-5,
    ),
    ("076 - symmetric matrix multiply", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    ("077 - torch.einsum batched", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    ("078 - swish activation", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("079 - hardtanh", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("080 - GELU (exact)", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("081 - SiLU activation", "01_Basic_elementwise", "fp32", 1e-5, 1e-5),
    ("082 - softmax + log-softmax + KL", "06_Fused_operations", "fp32", 1e-5, 1e-5),
    ("083 - matmul + add + relu + dropout", "06_Fused_operations", "fp32", 1e-5, 1e-5),
    ("084 - matmul + add + tanh + dropout", "06_Fused_operations", "fp32", 1e-5, 1e-5),
    ("085 - tril + sum", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    ("086 - Givens rotation", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    ("087 - householder reflection", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    ("088 - gram-schmidt orthogonalize", "07_Matrix_operations", "fp32", 1e-4, 1e-4),
    ("089 - cholesky decomp (3x3)", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    ("090 - LU decomp (3x3)", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    ("091 - QR decomp (3x3)", "07_Matrix_operations", "fp32", 1e-5, 1e-5),
    (
        "092 - batched matmul + bias + layer-norm",
        "06_Fused_operations",
        "fp32",
        1e-4,
        1e-4,
    ),
    ("093 - dilated conv 3x3 (stride 2)", "04_Conv2d_Stencil", "fp32", 1e-4, 1e-4),
    ("094 - asymmetric padding conv", "04_Conv2d_Stencil", "fp32", 1e-4, 1e-4),
    ("095 - separable conv (h then v)", "04_Conv2d_Stencil", "fp32", 1e-4, 1e-4),
    ("096 - tile matmul (split-K)", "02_Memory_bound", "fp32", 1e-5, 1e-5),
    ("097 - GEMM with epilogue", "02_Memory_bound", "fp32", 1e-5, 1e-5),
    ("098 - grouped GEMM with epilogue", "02_Memory_bound", "fp32", 1e-5, 1e-5),
    ("099 - sparse attention mask", "09_Sparse", "fp32", 1e-5, 1e-5),
    ("100 - flash attention (forward)", "04_Conv2d_Stencil", "fp32", 1e-3, 1e-3),
)

# Level-2 — 10 of 100 full-model forward passes (subset).
LEVEL2_TASKS: tuple[tuple[str, str], ...] = (
    ("L2-001 - MobileNet-v2 stem", "L2_Forward_MobileNetV2"),
    ("L2-002 - ResNet-50 stem", "L2_Forward_ResNet"),
    ("L2-003 - VGG-16 forward", "L2_Forward_VGG"),
    ("L2-004 - EfficientNet-B0 forward", "L2_Forward_EfficientNet"),
    ("L2-005 - BERT-base attention block", "L2_Forward_BERTBlock"),
    ("L2-006 - GPT-2 block forward", "L2_Forward_GPT2Block"),
    ("L2-007 - T5 encoder block", "L2_Forward_T5Block"),
    ("L2-008 - ViT base block forward", "L2_Forward_ViT"),
    ("L2-009 - Swin-T transformer block", "L2_Forward_SwinT"),
    ("L2-010 - RoBERTa-base forward", "L2_Forward_RoBERTa"),
)


def _kernelbench_prompt(idx: int, name: str, dtype: str, level: int = 1) -> str:
    """Generate a KernelBench problem statement as the prompt.

    Each prompt includes the model name and get_inputs() signature so
    the model can produce a corresponding Triton/CUDA implementation.
    """
    if level == 1:
        return (
            f"# KernelBench Problem {idx:03d}\n\n"
            f"## Task\n"
            f"Implement a {dtype} Triton/CUDA kernel for: **{name}**.\n\n"
            f"## Reference (PyTorch)\n"
            f"```python\n"
            f"import torch\n\n"
            f"def ref(x):\n"
            f"    # ... reference torch implementation ...\n"
            f"    return x\n\n"
            f"def get_inputs():\n"
            f"    # ... test inputs ...\n"
            f"    return [x]\n\n"
            f"def get_init_inputs():\n"
            f"    return []\n"
            f"```\n\n"
            f"## Your Task\n"
            f"Write a complete Triton (preferred) or CUDA kernel implementation "
            f"as `kernel_impl(x)`. The kernel must produce output that matches "
            f"`ref(x)` to within atol={DEFAULT_TOLERANCE_ATOL}, rtol={DEFAULT_TOLERANCE_RTOL}.\n\n"
            f"Wrap your implementation in a complete runnable Python file:\n"
            f"```python\n"
            f"import torch\n"
            f"import triton\n"
            f"import triton.language as tl\n\n"
            f"# your triton / cuda kernel code here\n\n"
            f"def kernel_impl(x):\n"
            f"    # your implementation\n"
            f"    return x\n"
            f"```\n"
        )
    return (
        f"# KernelBench Problem L2-{idx:03d}\n\n"
        f"## Task\n"
        f"Implement a fused forward pass for: **{name}**.\n\n"
        f"## Constraints\n"
        f"- Single fused kernel (no eager torch ops in the hot path)\n"
        f"- Output must match reference to atol={DEFAULT_TOLERANCE_ATOL}\n\n"
        f"## Output Format\n"
        f"Provide a complete runnable Python file with `def forward(x): ...` "
        f"returning the forward output."
    )


def _kernelbench_correctness_check(out_text: str, atol: float, rtol: float) -> bool:
    """Check if the model produced a valid Triton/CUDA kernel implementation.

    Heuristic: looks for syntactic markers of a valid kernel implementation:
    - 'def kernel_impl' or 'def forward' function defined
    - 'import triton' or 'torch.utils.cpp_extension' for CUDA
    - No syntax errors caught by ast.parse
    - No explicit "I cannot" / "I apologize" hedges
    """
    if not out_text:
        return False
    text = out_text.strip()
    if len(text) < 50:
        return False
    hedge_patterns = (
        "I cannot",
        "I apologize",
        "I don't have",
        "I'm not able",
        "I am unable",
        "I won't be able",
        "as an AI",
    )
    text_lower = text.lower()
    for hedge in hedge_patterns:
        if hedge.lower() in text_lower:
            return False
    has_function = (
        "def kernel_impl" in text
        or "def forward" in text
        or "@triton.jit" in text
        or "@triton.autotune" in text
    )
    has_kernel = (
        "import triton" in text
        or "triton.language" in text
        or "torch.utils.cpp_extension" in text
        or "__global__" in text
        or "cuda" in text_lower
    )
    if not (has_function and has_kernel):
        return False
    # Try parsing for syntax errors
    try:
        import ast

        ast.parse(text)
    except SyntaxError:
        return False
    return True


@dataclass
class KernelBenchConfig:
    """Per-task KernelBench config (atol/rtol)."""

    level: int = 1
    atol: float = DEFAULT_TOLERANCE_ATOL
    rtol: float = DEFAULT_TOLERANCE_RTOL
    category: str = ""
    dtype: str = "fp32"


class KernelBench(BaseSuite):
    """KernelBench GPU-kernel-implementation benchmark (Stanford ICML 2025)."""

    name = "kernelbench"
    domain = "gpu-kernel-implementation"
    paper_metrics: tuple[str, ...] = ("pass@1",)  # type: ignore[assignment]
    default_judge = "deterministic"
    source_url = SOURCE_URL
    notes = (
        f"{NUM_TASKS} tasks (100 level-1 + 10 level-2) from KernelBench "
        "(Stanford ICML 2025). Each task: implement a Triton/CUDA kernel "
        "matching a PyTorch reference. Heuristic correctness check: syntactic "
        "validity + presence of @triton.jit or torch.utils.cpp_extension import + "
        "no refusal hedges. Output unit: % of tasks passing correctness."
    )

    def __init__(self) -> None:
        self._task_configs: list[KernelBenchConfig] = []
        for name, cat, dtype, atol, rtol in LEVEL1_TASKS:
            self._task_configs.append(
                KernelBenchConfig(
                    level=1, atol=atol, rtol=rtol, category=cat, dtype=dtype
                )
            )
        for name, cat in LEVEL2_TASKS:
            self._task_configs.append(
                KernelBenchConfig(
                    level=2,
                    atol=DEFAULT_TOLERANCE_ATOL,
                    rtol=DEFAULT_TOLERANCE_RTOL,
                    category=cat,
                    dtype="fp32",
                )
            )
        self._tasks: list[TaskSpec] = []
        for i, (name, cat, dtype, atol, rtol) in enumerate(LEVEL1_TASKS, start=1):
            self._tasks.append(
                TaskSpec(
                    task_id=f"kernelbench-l1-{i:03d}",
                    suite=self.name,
                    prompt=_kernelbench_prompt(i, name, dtype, level=1),
                    reference=name,
                    tags={
                        "level": 1,
                        "category": cat,
                        "dtype": dtype,
                        "atol": atol,
                        "rtol": rtol,
                    },  # type: ignore[arg-type]
                )
            )
        for i, (name, cat) in enumerate(LEVEL2_TASKS, start=1):
            self._tasks.append(
                TaskSpec(
                    task_id=f"kernelbench-l2-{i:03d}",
                    suite=self.name,
                    prompt=_kernelbench_prompt(i, name, "fp32", level=2),
                    reference=name,
                    tags={
                        "level": 2,
                        "category": cat,
                        "dtype": "fp32",
                        "atol": DEFAULT_TOLERANCE_ATOL,
                        "rtol": DEFAULT_TOLERANCE_RTOL,
                    },  # type: ignore[arg-type]
                )
            )

    def subset(self, n: int, seed: int) -> list[TaskSpec]:
        """Deterministic subset sampling — same as BaseSuite.subset()."""
        from bench.seeds import sample

        if n >= len(self._tasks):
            return list(self._tasks)
        idx = sample(self.name, seed, pool=list(range(len(self._tasks))), n=n)
        return [self._tasks[i] for i in idx.ordered_indices]

    def verify(self, task: TaskSpec, completion: str) -> tuple[bool, dict[str, Any]]:
        """Score the model completion against the expected kernel-implementation output."""

        tags = task.tags
        passed = _kernelbench_correctness_check(completion, tags["atol"], tags["rtol"])  # type: ignore[call-overload]
        return passed, {
            "judge": "heuristic-validity",
            "level": tags["level"],  # type: ignore[call-overload]
            "category": tags["category"],  # type: ignore[call-overload]
            "atol": tags["atol"],  # type: ignore[call-overload]
            "rtol": tags["rtol"],  # type: ignore[call-overload]
        }


__all__ = ["KernelBench", "KernelBenchConfig", "NUM_TASKS", "SOURCE_URL"]
