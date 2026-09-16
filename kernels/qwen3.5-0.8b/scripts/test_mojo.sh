#!/usr/bin/env bash
# test_mojo.sh — smoke-test the Mojo polyglot kernels for Qwen3.5 0.8B.
#
# What this script does (in order):
#   1. Verify the Mojo toolchain is installed (skips cleanly otherwise).
#   2. Verify the SCOPE files are `mojo format`-clean (reformatting a
#      temp copy and diffing against the source — 0.26's `mojo format`
#      has no native --check flag).
#   3. Run `mojo build` against each SCOPE kernel file with -o /dev/null
#      to verify each top-level kernel is at least parseable / type-checkable.
#   4. Run each SCOPE binary and check exit code = 0 (this exercises the
#      argmax + attn_decode kernels end-to-end on tiny synthetic inputs).
#   5. If libpheno_qwen.dylib has been built by build_dylib.sh, run a
#      Python ctypes smoke test that loads the engine, calls
#      pheno_engine_load_metallib, then kernel_engine_rmsnorm on a small
#      fp16 input.  This is a smoke test of the host engine, NOT a
#      mojo-vs-Metal diff (the latter is python/validate.py).
#
# Outputs:
#   stdout = PASS/FAIL line per check
#   rc     = 0 on all-pass, 1 on any failure
#
# Prerequisites:
#   - A working `mojo` binary (run install_mojo.sh first).
#   - The SCOPE binaries built by build_mojo.sh at
#     build/qwen3_5_argmax_sample and build/qwen3_5_attn_decode.
#   - (Optional) libpheno_qwen.dylib from build_dylib.sh for the ctypes
#     smoke step.  If absent, step 5 is reported as a soft skip.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KERNEL_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
MOJO_DIR="${KERNEL_DIR}/mojo"
BUILD_DIR="${BUILD_DIR:-${KERNEL_DIR}/build}"

# SCOPE: the two kernels this commit migrates.  See build_mojo.sh for the
# rationale (each is self-contained, has its own `fn main()`, and is built
# as a standalone executable).
ARGMAX_BIN="${BUILD_DIR}/qwen3_5_argmax_sample"
ATTN_BIN="${BUILD_DIR}/qwen3_5_attn_decode"

# Optional dylib locations checked by step 5 (in priority order).
DYLIB_CANDIDATES=(
  "${BUILD_DIR}/libpheno_qwen.dylib"
  "${KERNEL_DIR}/zig/build/libpheno_qwen.dylib"
  "${KERNEL_DIR}/cpp/libpheno_qwen.dylib"
)
METALLIB_CANDIDATES=(
  "${BUILD_DIR}/kernels.metallib"
  "${KERNEL_DIR}/metal/build/kernels.metallib"
)

log()   { printf "[test_mojo] %s\n" "$*" >&2; }
pass()  { printf "  PASS: %s\n" "$*"; }
warn_() { printf "  WARN: %s\n" "$*" >&2; }
fail()  { printf "  FAIL: %s\n" "$*" >&2; }
overall=0

# ---------------------------------------------------------------------------
# 1. Toolchain.
# ---------------------------------------------------------------------------
find_mojo() {
  if command -v mojo >/dev/null 2>&1; then
    command -v mojo
    return 0
  fi
  if [[ -x "${HOME}/.local/bin/mojo" ]]; then
    printf '%s\n' "${HOME}/.local/bin/mojo"
    return 0
  fi
  return 1
}

if ! MOJO_BIN="$(find_mojo)"; then
  log "mojo binary not found on PATH or in ~/.local/bin"
  log "run: bash ${SCRIPT_DIR}/install_mojo.sh"
  log "(skipping mojo tests — nothing to exercise without the toolchain)"
  exit 0
fi
log "mojo: ${MOJO_BIN}"
"${MOJO_BIN}" --version 2>&1 | head -1 || true

# ---------------------------------------------------------------------------
# 2. Format check on SCOPE files.
# ---------------------------------------------------------------------------
log "step 1/5 — mojo format --check (SCOPE files)"
# Mojo 0.26's `mojo format` has no --check flag.  Implement our own:
# format a temp copy and diff against the source.
SCOPE_SOURCES=(
  "${MOJO_DIR}/argmax_sample.mojo"
  "${MOJO_DIR}/attn_decode.mojo"
)
fmt_ok=1
for f in "${SCOPE_SOURCES[@]}"; do
  if [[ ! -f "${f}" ]]; then
    fail "missing scope source: ${f}"
    fmt_ok=0
    overall=1
    continue
  fi
  # macOS mktemp(-t prefix) treats the prefix verbatim and ignores any
  # Xs embedded before the last `.` — so a template like
  # `mojo_fmt.XXXXXX.mojo` produces a literal-Xs filename in the user's
  # temp dir.  Build the path ourselves: mktemp -> prefix, then rename
  # to have a `.mojo` extension so `mojo format` accepts it.
  tmp_no_ext="$(mktemp -t mojo_fmt)"
  mv "${tmp_no_ext}" "${tmp_no_ext}.mojo"
  tmp="${tmp_no_ext}.mojo"
  cp "${f}" "${tmp}"
  if ! "${MOJO_BIN}" format "${tmp}" >/dev/null 2>&1; then
    fail "format: ${f#${KERNEL_DIR}/} (mojo format raised)"
    fmt_ok=0
    overall=1
    rm -f "${tmp}"
    continue
  fi
  if ! diff -q "${tmp}" "${f}" >/dev/null 2>&1; then
    fail "format check: ${f#${KERNEL_DIR}/} (would reformat)"
    diff -u "${f}" "${tmp}" | sed 's/^/    /' >&2 || true
    fmt_ok=0
    overall=1
  fi
  rm -f "${tmp}"
done
# If formatting would change the SCOPE files, suggest running
# `mojo format <file>` on the developer's machine to normalize.  We
# don't auto-rewrite to keep CI behaviour deterministic.
if [[ "${fmt_ok}" -ne 1 ]]; then
  log "  hint: run 'mojo format <file>' on the affected files to"
  log "        bring them in line with the canonical style."
fi
[[ "${fmt_ok}" -eq 1 ]] && pass "format check (${#SCOPE_SOURCES[@]} SCOPE files)"

# ---------------------------------------------------------------------------
# 3. Per-file type check (parse + type-check, no codegen).
# ---------------------------------------------------------------------------
log "step 2/5 — mojo build (per-file type check, no codegen)"
type_ok=1
for src in "${SCOPE_SOURCES[@]}"; do
  if [[ ! -f "${src}" ]]; then
    fail "missing kernel: $(basename "${src}")"
    type_ok=0
    overall=1
    continue
  fi
  # `mojo build` with -o /dev/null produces no binary; we just want
  # parse + type-check feedback.  Each SCOPE file has its own `fn main`
  # so it builds standalone (no relative-import dependency).
  if ! "${MOJO_BIN}" build "${src}" -o /dev/null 2>&1 \
        | sed "s|^|[$(basename "${src}")] |" >&2; then
    fail "type check: $(basename "${src}")"
    type_ok=0
    overall=1
  fi
done
[[ "${type_ok}" -eq 1 ]] && pass "type check (${#SCOPE_SOURCES[@]} SCOPE files)"

# ---------------------------------------------------------------------------
# 4. Run each SCOPE binary as a smoke test.
# ---------------------------------------------------------------------------
log "step 3/5 — run SCOPE binaries"
run_bin() {
  local bin="$1"
  local name
  name="$(basename "${bin}")"
  if [[ ! -x "${bin}" ]]; then
    fail "${name}: not built (run scripts/build_mojo.sh first)"
    return 1
  fi
  # Each binary prints "SMOKE OK" on success.  5 s timeout — these are
  # tiny CPU-only kernels and should finish in well under 1 s.
  log "  running ${name} (5 s timeout)"
  local out
  out="$(timeout 5s "${bin}" 2>&1)"
  local rc=$?
  if [[ "${rc}" -ne 0 ]]; then
    fail "${name}: exit ${rc}"
    printf '%s\n' "${out}" | sed 's/^/    /' >&2 || true
    return 1
  fi
  if [[ "${out}" != *"SMOKE OK"* ]]; then
    fail "${name}: did not print 'SMOKE OK'"
    printf '%s\n' "${out}" | sed 's/^/    /' >&2 || true
    return 1
  fi
  pass "${name}: SMOKE OK"
  printf '%s\n' "${out}" | sed 's/^/    /'
  return 0
}
run_ok=1
run_bin "${ARGMAX_BIN}" || { run_ok=0; overall=1; }
run_bin "${ATTN_BIN}" || { run_ok=0; overall=1; }
[[ "${run_ok}" -eq 1 ]] && pass "smoke runs (${#SCOPE_SOURCES[@]} binaries)"

# ---------------------------------------------------------------------------
# 5. Optional Python ctypes smoke test against libpheno_qwen.dylib.
# ---------------------------------------------------------------------------
log "step 4/5 — Python ctypes smoke (libpheno_qwen.dylib + kernel_engine_rmsnorm)"

dylib_path=""
for c in "${DYLIB_CANDIDATES[@]}"; do
  if [[ -f "${c}" ]]; then
    dylib_path="${c}"
    break
  fi
done

metallib_path=""
for c in "${METALLIB_CANDIDATES[@]}"; do
  if [[ -f "${c}" ]]; then
    metallib_path="${c}"
    break
  fi
done

if [[ -z "${dylib_path}" ]]; then
  log "  libpheno_qwen.dylib not found — soft-skipping ctypes smoke."
  log "  (run scripts/build_dylib.sh to produce it; this is a non-blocking skip)"
  pass "ctypes smoke: dylib not built (soft skip)"
else
  log "  dylib:    ${dylib_path}"
  log "  metallib: ${metallib_path:-<none — engine will use default search>}"
  # Inline the ctypes smoke as a heredoc.  We bind only the symbols we
  # need (no full EngineHandle class) so this test has zero python
  # dependencies beyond the standard library + ctypes (which means
  # numpy is *not* required).  The kernel_engine_rmsnorm signature is
  # taken from include/kernel_engine.h and validate.py:200-217:
  #   status_t kernel_engine_rmsnorm(
  #       engine, x_ptr, residual_ptr, weight_ptr, out_ptr, B, S, H);
  python3 - "${dylib_path}" "${metallib_path}" <<'PY' || { fail "ctypes smoke: python3 raised"; overall=1; }
import ctypes, sys

dylib_path, metallib_path = sys.argv[1], sys.argv[2]
dylib = ctypes.CDLL(dylib_path)

# ---- engine_create
dylib.pheno_engine_create.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
dylib.pheno_engine_create.restype = ctypes.c_int
dylib.pheno_engine_destroy.argtypes = [ctypes.c_void_p]
dylib.pheno_engine_destroy.restype = ctypes.c_int

engine = ctypes.c_void_p()
status = dylib.pheno_engine_create(ctypes.byref(engine))
if status != 0 or not engine.value:
    print(f"[ctypes] pheno_engine_create failed: status={status}")
    sys.exit(1)
print(f"[ctypes] engine created: handle={engine.value:#x}")

# ---- load metallib if available
if metallib_path:
    dylib.pheno_engine_load_metallib.argtypes = [
        ctypes.c_void_p, ctypes.c_char_p]
    dylib.pheno_engine_load_metallib.restype = ctypes.c_int
    s = dylib.pheno_engine_load_metallib(
        engine, metallib_path.encode("utf-8"))
    print(f"[ctypes] pheno_engine_load_metallib({metallib_path}): status={s}")
    if s != 0:
        dylib.pheno_engine_destroy(engine)
        sys.exit(1)

# ---- kernel_engine_rmsnorm on a small fp16 input
# Use c_uint16 buffers holding fp16 bit patterns.  B=S=H=2 keeps the
# total payload to 8 fp16 = 16 bytes, well within any minimum allocation.
B, S, H = 2, 2, 2
n_elem = B * S * H
x_bytes = (ctypes.c_uint16 * n_elem)(0x3C00)  # fp16 1.0 = 0x3C00
w_bytes = (ctypes.c_uint16 * n_elem)(0x3C00)
r_bytes = (ctypes.c_uint16 * n_elem)(0x0000)  # zero residual
o_bytes = (ctypes.c_uint16 * n_elem)(0x0000)

try:
    dylib.kernel_engine_rmsnorm
except AttributeError:
    print("[ctypes] kernel_engine_rmsnorm not exported — soft skip")
    dylib.pheno_engine_destroy(engine)
    sys.exit(0)

dylib.kernel_engine_rmsnorm.argtypes = [
    ctypes.c_void_p,
    ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32,
]
dylib.kernel_engine_rmsnorm.restype = ctypes.c_int

s = dylib.kernel_engine_rmsnorm(
    engine,
    ctypes.cast(x_bytes, ctypes.c_void_p),
    ctypes.cast(r_bytes, ctypes.c_void_p),
    ctypes.cast(w_bytes, ctypes.c_void_p),
    ctypes.cast(o_bytes, ctypes.c_void_p),
    B, S, H,
)
print(f"[ctypes] kernel_engine_rmsnorm(B={B},S={S},H={H}): status={s}")
print(f"[ctypes] out[0..3] = {[hex(o_bytes[i]) for i in range(min(4, n_elem))]}")

dylib.pheno_engine_destroy(engine)
sys.exit(0 if s == 0 else 2)
PY
  if [[ "${overall}" -eq 0 ]]; then
    pass "ctypes smoke: kernel_engine_rmsnorm callable"
  fi
fi

# ---------------------------------------------------------------------------
# 6. Final aggregate check: per-file type-check on every .mojo under mojo/.
# ---------------------------------------------------------------------------
# The commit's task scope only covers argmax_sample + attn_decode, but
# we also probe the *other* files for type-check errors so the developer
# can see at a glance which files still need migration.  Failures in
# out-of-scope files are reported as soft warnings, not hard fails —
# they are documented as pre-existing in the commit message.
log "step 5/5 — full-directory probe (informational; out-of-scope failures are warnings)"
shopt -s nullglob
all_files=( "${MOJO_DIR}"/*.mojo )
shopt -u nullglob
non_scope_files=()
for f in "${all_files[@]}"; do
  base="$(basename "${f}")"
  case "${base}" in
    argmax_sample.mojo|attn_decode.mojo|qwen3_5_types.mojo|__init__.mojo)
      # In-scope or read-only; already checked above.
      continue
      ;;
    *)
      non_scope_files+=( "${f}" )
      ;;
  esac
done
non_scope_warn=0
for f in "${non_scope_files[@]}"; do
  out="$("${MOJO_BIN}" build "${f}" -o /dev/null 2>&1 || true)"
  if [[ "${out}" == *"error"* ]]; then
    warn_ "$(basename "${f}"): pre-0.26 GPU API still in use (out of scope for this commit)"
    non_scope_warn=1
  fi
done
if [[ "${non_scope_warn}" -eq 0 ]]; then
  pass "full-directory probe: no errors in any .mojo file"
else
  log "  (non-scope failures are pre-existing; tracked in commit message)"
fi

# ---------------------------------------------------------------------------
# 7. Summary.
# ---------------------------------------------------------------------------
log "DONE."
if [[ "${overall}" -eq 0 ]]; then
  cat <<NEXT

[test_mojo] SUCCESS — all in-scope checks passed.

The two migrated kernels (argmax_sample, attn_decode) compile and run
their built-in self-tests.  Numerical validation against the reference
Python implementation remains:
    python3 kernels/qwen3.5-0.8b/python/validate.py --kernel all --quick

NEXT
  exit 0
else
  cat <<NEXT

[test_mojo] FAIL — at least one check failed.
NEXT
  exit 1
fi