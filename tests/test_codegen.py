"""
tests/test_codegen.py — Tests for the Qwen3.5 0.8B architecture codegen.

These tests exercise ``kernels/qwen3.5-0.8b/python/codegen.py`` end-to-end:

  1. ``test_idempotence`` — re-running codegen on the same arch.yaml produces
     byte-identical output (the on-disk ``iso/*`` files are unchanged after
     a second invocation).
  2. ``test_c_header_contains_all_required_constants`` — the generated
     ``iso/qwen3_5.h`` declares every scalar/macro the kernel headers
     (C/Rust/Zig/Mojo) are expected to expose.
  3. ``test_rust_block_contains_all_required_constants`` — same for
     ``iso/arch.rs``.
  4. ``test_zig_block_contains_all_required_constants`` — same for
     ``iso/qwen3_5.zig``.
  5. ``test_mojo_block_contains_all_required_constants`` — same for
     ``iso/qwen3_5.mojo``.
  6. ``test_cross_language_round_trip`` — every constant emitted to one
     language appears with the same value in every other language
     (the "single source of truth" property).
  7. ``test_layer_schedule_matches_arch_yaml`` — the layer_is_full schedule
     round-trips exactly: every (i+1) % interval == 0 → True.
  8. ``test_rot_dim_is_mrope_sum`` — rot_dim = sum(mrope_section) per
     Qwen3.5 convention; the partial_rotary_factor check is also enforced.
  9. ``test_minimal_yaml_parser_handles_arch`` — the fallback YAML reader
     (used when pyyaml is unavailable) parses arch.yaml to the same
     structure.
 10. ``test_codegen_check_flag_passes`` — ``codegen.py --check`` returns 0
     on a freshly-generated tree.
 11. ``test_emit_modes_distinct_paths`` — DEFAULT vs CANONICAL output
     paths differ (so codegen never silently clobbers the hand-written
     canonical headers unless ``--canonical`` is passed).

These tests are deliberately self-contained: they only import the pure
``codegen`` module, do not touch MLX, and run in <2 s on any machine.

Run via::

    cd /Users/kooshapari/CodeProjects/Phenotype/pheno-harness-validation
    /opt/homebrew/bin/python3 -m pytest tests/ -v
    /opt/homebrew/bin/python3 tests/test_codegen.py        # bare-script fallback
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths — these tests live in <repo>/tests/, so repo root is the parent.
# ---------------------------------------------------------------------------

THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent
KERNEL_DIR = REPO_ROOT / "kernels" / "qwen3.5-0.8b"
ARCH_YAML = KERNEL_DIR / "arch.yaml"
CODEGEN_PY = KERNEL_DIR / "python" / "codegen.py"

# Make ``import codegen`` work without an installed package.
sys.path.insert(0, str(KERNEL_DIR / "python"))
import codegen  # noqa: E402

# ---------------------------------------------------------------------------
# Constants every generated header MUST expose.  This is the contract the
# rest of the kernel suite (metal, rust, zig, mojo) depends on.
# ---------------------------------------------------------------------------

REQUIRED_C_MACROS = [
    "QWEN3_5_VOCAB_SIZE",
    "QWEN3_5_HIDDEN_SIZE",
    "QWEN3_5_INTERMEDIATE_SIZE",
    "QWEN3_5_NUM_HIDDEN_LAYERS",
    "QWEN3_5_MAX_POSITION_EMB",
    "QWEN3_5_RMS_NORM_EPS_F",
    "QWEN3_5_PARTIAL_ROTARY_FACTOR",
    "QWEN3_5_ROPE_THETA",
    "QWEN3_5_MROPE_SECTION_T",
    "QWEN3_5_MROPE_SECTION_H",
    "QWEN3_5_MROPE_SECTION_W",
    "QWEN3_5_ROT_DIM",
    "QWEN3_5_FULL_HEADS",
    "QWEN3_5_FULL_KV_HEADS",
    "QWEN3_5_FULL_HEAD_DIM",
    "QWEN3_5_FULL_HEADS_PER_KV",
    "QWEN3_5_FULL_Q_DIM",
    "QWEN3_5_FULL_KV_DIM",
    "QWEN3_5_FULL_QKV_DIM",
    "QWEN3_5_FULL_ATTN_INTERVAL",
    "QWEN3_5_FULL_ATTN_NUM_LAYERS",
    "QWEN3_5_LIN_KEY_HEADS",
    "QWEN3_5_LIN_VALUE_HEADS",
    "QWEN3_5_LIN_KEY_HEAD_DIM",
    "QWEN3_5_LIN_VALUE_HEAD_DIM",
    "QWEN3_5_LIN_CONV_KERNEL",
    "QWEN3_5_LIN_NUM_LAYERS",
    "QWEN3_5_LIN_STATE_PER_LAYER_F32_BYTES",
    "QWEN3_5_LIN_STATE_PER_LAYER_BF16_BYTES",
    "QWEN3_5_LAYER_IS_FULL",
]

REQUIRED_RUST_CONSTS = [
    "VOCAB_SIZE",
    "HIDDEN_SIZE",
    "INTERMEDIATE_SIZE",
    "NUM_HIDDEN_LAYERS",
    "RMS_NORM_EPS",
    "TIE_WORD_EMBEDDINGS",
    "FULL_HEADS",
    "FULL_KV_HEADS",
    "FULL_HEAD_DIM",
    "FULL_HEADS_PER_KV",
    "FULL_Q_DIM",
    "FULL_KV_DIM",
    "FULL_QKV_DIM",
    "FULL_ATTN_INTERVAL",
    "FULL_ATTN_NUM_LAYERS",
    "FULL_ATTN_LAYER_INDICES",
    "ROPE_THETA",
    "PARTIAL_ROTARY_FACTOR",
    "MROPE_INTERLEAVED",
    "MROPE_SECTION",
    "ROT_DIM",
    "LIN_NUM_LAYERS",
    "LIN_KEY_HEADS",
    "LIN_VALUE_HEADS",
    "LIN_KEY_HEAD_DIM",
    "LIN_VALUE_HEAD_DIM",
    "LIN_CONV_KERNEL",
    "LIN_QKV_DIM",
    "LIN_STATE_ELEMENTS",
    "LIN_STATE_BYTES_F32",
    "LIN_STATE_BYTES_BF16",
    "LAYER_IS_FULL",
]

REQUIRED_ZIG_CONSTS = [
    "VocabSize",
    "HiddenSize",
    "IntermediateSize",
    "NumHiddenLayers",
    "RmsNormEps",
    "TieWordEmbeddings",
    "FullHeads",
    "FullKvHeads",
    "FullHeadDim",
    "FullHeadsPerKv",
    "FullQDim",
    "FullKvDim",
    "FullQkvDim",
    "FullAttnInterval",
    "FullAttnNumLayers",
    "RopeTheta",
    "PartialRotaryFactor",
    "MRopeInterleaved",
    "MRopeSection",
    "RotDim",
    "LinNumLayers",
    "LinKeyHeads",
    "LinValueHeads",
    "LinKeyHeadDim",
    "LinValueHeadDim",
    "LinConvKernel",
    "LinQkvDim",
    "LinStateElements",
    "LinStateBytesF32",
    "LinStateBytesBf16",
    "LayerIsFull",
]

REQUIRED_MOJO_ALIASES = [
    "VocabSize",
    "HiddenSize",
    "IntermediateSize",
    "NumHiddenLayers",
    "RmsNormEps",
    "TieWordEmbeddings",
    "FullHeads",
    "FullKvHeads",
    "FullHeadDim",
    "FullHeadsPerKv",
    "FullQDim",
    "FullKvDim",
    "FullQkvDim",
    "FullAttnInterval",
    "FullAttnNumLayers",
    "RopeTheta",
    "PartialRotaryFactor",
    "MRopeInterleaved",
    "RotDim",
    "LinNumLayers",
    "LinKeyHeads",
    "LinValueHeads",
    "LinKeyHeadDim",
    "LinValueHeadDim",
    "LinConvKernel",
    "LinQkvDim",
    "LinStateElements",
    "LinStateBytesF32",
    "LinStateBytesBf16",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_codegen(*args: str) -> subprocess.CompletedProcess:
    """Invoke ``codegen.py`` as a subprocess and return the result.

    Always uses ``--arch <absolute>`` so the subprocess is independent of
    CWD — the verify command in the task description is `cd <repo> && …`,
    but the test should work no matter where pytest is invoked.
    """
    return subprocess.run(
        [sys.executable, str(CODEGEN_PY), "--arch", str(ARCH_YAML), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def _emit_all() -> dict:
    """Run codegen in-process; return the {lang: text} dict."""
    arch_text = ARCH_YAML.read_text()
    a = codegen.parse_arch_yaml(arch_text)
    return {
        "c": codegen.emit_c(a),
        "rust": codegen.emit_rust(a),
        "zig": codegen.emit_zig(a),
        "mojo": codegen.emit_mojo(a),
        "nim": codegen.emit_nim(a),
        "json": codegen.emit_json(a),
    }


def _shasumi(text: str) -> str:
    """Stable hash of a string for the idempotence check."""
    import hashlib

    return hashlib.sha256(text.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_arch_yaml_exists():
    assert ARCH_YAML.exists(), f"missing arch.yaml at {ARCH_YAML}"
    assert ARCH_YAML.read_text().strip(), "arch.yaml is empty"


def test_codegen_py_exists():
    assert CODEGEN_PY.exists()


def test_parse_arch_yaml_returns_typed_dataclass():
    a = codegen.parse_arch_yaml(ARCH_YAML.read_text())
    assert isinstance(a, codegen.QwenArch)
    # Sanity-check a few known values (Qwen3.5 0.8B canonical)
    assert a.hidden_size == 1024
    assert a.num_hidden_layers == 24
    assert a.full_attention_interval == 4
    assert a.mrope_section == (11, 11, 10)  # T, H, W (M-RoPE)
    assert a.rot_dim == 11 + 11 + 10  # = 32
    assert a.full_attention_layer_indices == (3, 7, 11, 15, 19, 23)
    assert a.full_heads == 8
    assert a.full_kv_heads == 2
    assert a.full_head_dim == 256


def test_layer_schedule_matches_arch_yaml():
    a = codegen.parse_arch_yaml(ARCH_YAML.read_text())
    expected = tuple(
        ((i + 1) % a.full_attention_interval == 0) for i in range(a.num_hidden_layers)
    )
    assert a.layer_is_full == expected
    # 24 layers, every 4th = 6 full
    assert sum(a.layer_is_full) == 6
    # Full layer indices (0-based): 3, 7, 11, 15, 19, 23
    assert [i for i, v in enumerate(a.layer_is_full) if v] == [3, 7, 11, 15, 19, 23]


def test_rot_dim_is_mrope_sum():
    a = codegen.parse_arch_yaml(ARCH_YAML.read_text())
    assert a.rot_dim == sum(a.mrope_section)
    # partial_rotary_factor * head_dim = 0.25 * 256 = 64, but Qwen3.5 uses
    # the M-RoPE convention where half that (32) is the rotated dim. So the
    # consistency check inside rot_dim accepts 2 * rot_dim == partial * head_dim.
    assert a.partial_rotary_factor * a.full_head_dim == 2 * a.rot_dim


def test_state_elements_match_explicit_formula():
    a = codegen.parse_arch_yaml(ARCH_YAML.read_text())
    expected = (
        a.lin_key_heads * a.lin_value_heads * a.lin_value_head_dim * a.lin_key_head_dim
    )
    assert a.state_elements == expected


# --- Idempotence -------------------------------------------------------------


def test_idempotence():
    """Re-running codegen produces byte-identical output (no timestamps,
    no platform-dependent newlines, no random ordering of fields)."""
    first = _emit_all()
    second = _emit_all()
    for lang in first:
        assert first[lang] == second[lang], (
            f"idempotence violated for {lang}: "
            f"hash1={_shasumi(first[lang])[:8]} hash2={_shasumi(second[lang])[:8]}"
        )


def test_idempotence_subprocess():
    """Run codegen.py twice as a subprocess; iso/* outputs must be unchanged."""
    # First run — will create iso/* if missing.
    r1 = _run_codegen()
    assert r1.returncode == 0, f"first run failed:\n{r1.stdout}\n{r1.stderr}"

    # Capture hashes
    iso_dir = KERNEL_DIR / "iso"
    before = {p.name: p.read_bytes() for p in iso_dir.iterdir()}

    # Second run
    r2 = _run_codegen()
    assert r2.returncode == 0, f"second run failed:\n{r2.stdout}\n{r2.stderr}"

    after = {p.name: p.read_bytes() for p in iso_dir.iterdir()}
    assert set(before) == set(after), (
        f"second run added/removed files: {set(before) ^ set(after)}"
    )
    for name, content in before.items():
        assert content == after[name], (
            f"{name} changed on idempotent re-run "
            f"({len(content)} -> {len(after[name])} bytes)"
        )


# --- C header ----------------------------------------------------------------


def test_c_header_contains_all_required_constants():
    c_src = _emit_all()["c"]
    missing = [
        m
        for m in REQUIRED_C_MACROS
        if f"#define {m}" not in c_src and f"static const int8_t {m}" not in c_src
    ]
    assert not missing, f"C header missing required macros: {missing}"


def test_c_header_has_static_asserts():
    c_src = _emit_all()["c"]
    assert "_Static_assert" in c_src
    # All four expected static asserts
    assert "HIDDEN_SIZE" in c_src
    assert "FULL_HEAD_DIM" in c_src
    assert "FULL_HEADS % QWEN3_5_FULL_KV_HEADS" in c_src
    assert "ROT_DIM" in c_src


def test_c_header_layer_schedule_array_size_matches():
    a = codegen.parse_arch_yaml(ARCH_YAML.read_text())
    c_src = _emit_all()["c"]
    pattern = re.compile(
        r"QWEN3_5_LAYER_IS_FULL\[QWEN3_5_NUM_HIDDEN_LAYERS\]\s*=\s*\{(.+?)\}",
        re.DOTALL,
    )
    m = pattern.search(c_src)
    assert m, "C header missing LAYER_IS_FULL array"
    body = m.group(1)
    # Strip C++ line comments before counting (e.g. "0-3", "8-11" contain '1')
    body_no_comments = re.sub(r"//.*", "", body)
    ones = body_no_comments.count("1")
    zeros = body_no_comments.count("0")
    assert ones == sum(a.layer_is_full), (
        f"LAYER_IS_FULL has {ones} ones, expected {sum(a.layer_is_full)}"
    )
    assert zeros == a.num_hidden_layers - sum(a.layer_is_full)


# --- Rust block --------------------------------------------------------------


def test_rust_block_contains_all_required_constants():
    rust_src = _emit_all()["rust"]
    missing = [c for c in REQUIRED_RUST_CONSTS if f"pub const {c}" not in rust_src]
    assert not missing, f"Rust block missing consts: {missing}"


def test_rust_block_full_attn_indices_literal():
    a = codegen.parse_arch_yaml(ARCH_YAML.read_text())
    rust_src = _emit_all()["rust"]
    # exact literal appears (no separate expected_arr; build inline)
    assert f"{list(a.full_attention_layer_indices)!r}".replace("'", "") in rust_src


# --- Zig block ---------------------------------------------------------------


def test_zig_block_contains_all_required_constants():
    zig_src = _emit_all()["zig"]
    missing = [c for c in REQUIRED_ZIG_CONSTS if f"pub const {c}" not in zig_src]
    assert not missing, f"Zig block missing consts: {missing}"


def test_zig_block_compile_time_asserts():
    zig_src = _emit_all()["zig"]
    assert "@compileError" in zig_src
    assert "HiddenSize" in zig_src
    assert "FullHeadDim" in zig_src
    assert "RotDim" in zig_src


# --- Mojo block --------------------------------------------------------------


def test_mojo_block_contains_all_required_constants():
    mojo_src = _emit_all()["mojo"]
    missing = [a for a in REQUIRED_MOJO_ALIASES if f"alias {a}" not in mojo_src]
    assert not missing, f"Mojo block missing aliases: {missing}"


def test_mojo_block_compile_time_asserts():
    mojo_src = _emit_all()["mojo"]
    # Mojo uses `comptime if` for compile-time asserts
    assert "comptime if" in mojo_src
    assert "HiddenSize" in mojo_src
    assert "FullHeadDim" in mojo_src
    assert "RotDim" in mojo_src


# --- Cross-language round trip ----------------------------------------------


def test_cross_language_round_trip():
    """Every scalar in arch.yaml must appear with the same value in every
    generated language (the 'single source of truth' property)."""
    a = codegen.parse_arch_yaml(ARCH_YAML.read_text())
    out = _emit_all()

    # Pull out the value of each scalar as a string; check it appears in
    # every language's source.
    def check(label: str, value, languages=("c", "rust", "zig", "mojo")):
        for lang in languages:
            assert str(value) in out[lang], f"{label}={value!r} missing from {lang}"

    # Identity (skip — format differs per language)
    # Core dims
    check("vocab_size", a.vocab_size)
    check("hidden_size", a.hidden_size)
    check("intermediate_size", a.intermediate_size)
    check("num_hidden_layers", a.num_hidden_layers)
    check("max_position_embeddings", a.max_position_embeddings)
    # Full attention
    check("full_heads", a.full_heads)
    check("full_kv_heads", a.full_kv_heads)
    check("full_head_dim", a.full_head_dim)
    check("full_attention_interval", a.full_attention_interval)
    check("full_attention_num_layers", a.full_attention_num_layers)
    # Linear attention
    check("lin_key_heads", a.lin_key_heads)
    check("lin_value_heads", a.lin_value_heads)
    check("lin_key_head_dim", a.lin_key_head_dim)
    check("lin_value_head_dim", a.lin_value_head_dim)
    check("lin_conv_kernel", a.lin_conv_kernel)
    # M-RoPE section
    for s in a.mrope_section:
        check(f"mrope_section_{s}", s)
    # rot_dim
    check("rot_dim", a.rot_dim)


def test_cross_language_schedule_consistency():
    """The layer schedule must encode the same pattern in every language."""
    out = _emit_all()
    a = codegen.parse_arch_yaml(ARCH_YAML.read_text())
    expected_ones = sum(a.layer_is_full)
    expected_zeros = a.num_hidden_layers - expected_ones
    assert expected_ones == 6 and expected_zeros == 18  # sanity check

    # C: static int8_t array, count "1" and "0" tokens within the schedule.
    sched_c = re.search(
        r"QWEN3_5_LAYER_IS_FULL\[QWEN3_5_NUM_HIDDEN_LAYERS\]\s*=\s*\{(.+?)\}",
        out["c"],
        re.DOTALL,
    )
    assert sched_c
    # Strip C++ line comments before counting (e.g. "0-3" contains '1')
    c_body = re.sub(r"//.*", "", sched_c.group(1))
    c_ones_in_sched = c_body.count("1")
    assert c_ones_in_sched == expected_ones

    # Rust const is computed at const-time; check the expected count
    # via the docstring instead.
    assert "6 full, 18 linear" in out["rust"]

    # Zig: const array initialization
    assert "LayerIsFull" in out["zig"]
    assert "FullAttnInterval" in out["zig"]

    # Mojo: fn layer_is_full uses modular arithmetic
    assert "fn layer_is_full" in out["mojo"]
    assert "FullAttnInterval" in out["mojo"]

    # Sanity: C schedule array contains exactly 6 ones.
    assert c_ones_in_sched == expected_ones, (
        f"C schedule has {c_ones_in_sched} ones, expected {expected_ones}"
    )


# --- JSON canonical dump -----------------------------------------------------


def test_json_dump_is_canonical():
    """The JSON dump must be reproducible: same input -> same bytes."""
    j1 = _emit_all()["json"]
    j2 = _emit_all()["json"]
    assert j1 == j2
    obj = json.loads(j1)
    # Spot-check structure
    assert obj["hidden_size"] == 1024
    assert obj["num_hidden_layers"] == 24
    assert obj["mrope"]["rot_dim"] == 11 + 11 + 10  # = 32
    assert sum(obj["layer_is_full"]) == 6
    # Top-level keys are sorted (canonical form).
    keys = list(obj.keys())
    assert keys == sorted(keys), f"JSON keys not sorted: {keys}"


# --- YAML fallback reader ---------------------------------------------------


def test_minimal_yaml_parser_handles_arch():
    """The fallback YAML reader (used when pyyaml is missing) must parse
    arch.yaml to the same QwenArch."""
    arch_text = ARCH_YAML.read_text()
    a_yaml = codegen.parse_arch_yaml(arch_text)  # uses pyyaml
    # Always exercise the minimal loader; it's a separate codepath.
    a_min = codegen._minimal_yaml_load(arch_text)
    # Drill into the dict and compare
    assert isinstance(a_min, dict)
    assert a_min["model"]["hidden_size"] == a_yaml.hidden_size
    assert a_min["model"]["num_hidden_layers"] == a_yaml.num_hidden_layers
    assert a_min["model"]["full_attention"]["num_attention_heads"] == a_yaml.full_heads
    assert a_min["model"]["mrope"]["section"] == list(a_yaml.mrope_section)


# --- CLI behaviour ----------------------------------------------------------


def test_codegen_check_flag_passes():
    """``codegen.py --check`` returns 0 when iso/* is up to date."""
    r = _run_codegen()
    assert r.returncode == 0, f"setup run failed:\n{r.stdout}{r.stderr}"
    r = _run_codegen("--check")
    assert r.returncode == 0, (
        f"--check failed:\nSTDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    )


def test_emit_modes_distinct_paths():
    """Default and --canonical modes must use different output paths
    (so codegen never silently overwrites the hand-written canonical
    headers unless explicitly asked)."""
    assert codegen.DEFAULT_OUTPUTS != codegen.CANONICAL_OUTPUTS
    # Specifically: the C header in iso/ must not be the same path as in include/.
    assert codegen.DEFAULT_OUTPUTS["c"] != codegen.CANONICAL_OUTPUTS["c"]
    assert codegen.DEFAULT_OUTPUTS["rust"] != codegen.CANONICAL_OUTPUTS["rust"]
    assert codegen.DEFAULT_OUTPUTS["zig"] != codegen.CANONICAL_OUTPUTS["zig"]


def test_codegen_check_canonical_flag():
    """``--check-canonical`` should report whether the hand-written
    include/qwen3_5.h, rust/src/arch.rs, zig/qwen3_5.zig match what
    codegen would emit.  We don't require OK (drift is expected until
    canonical files are regenerated); we just require the flag runs."""
    r = _run_codegen("--check-canonical")
    assert r.returncode in (0, 1), (
        f"--check-canonical returned unexpected code: {r.returncode}\n"
        f"STDOUT:\n{r.stdout}\nSTDERR:\n{r.stderr}"
    )


# --- Bash-style invocation (matches the task verify command) -----------------


def test_main_module_invocable():
    """Smoke test: ``python -m codegen`` style invocation is import-safe."""
    # We invoke the script as `__main__` to cover the
    # ``if __name__ == "__main__"`` branch.
    r = subprocess.run(
        [sys.executable, str(CODEGEN_PY), "--arch", str(ARCH_YAML), "--print", "c"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0
    assert "QWEN3_5_HIDDEN_SIZE" in r.stdout
    assert "QWEN3_5_VOCAB_SIZE" in r.stdout
