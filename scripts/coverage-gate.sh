#!/usr/bin/env bash
# coverage-gate.sh — Tier-2 coverage gate (ADR-040)
#
# Enforces per-workspace coverage thresholds:
#   Root workspace (lib crates):   ≥ 71%
#   Root workspace (framework):    ≥ 70%
#   IAC workspace (services):      ≥ 60%
#
# The gate runs coverage on each workspace independently so that
# the correct threshold is applied per crate tier.
#
# Exit codes:
#   0  All thresholds met
#   1  Root workspace below threshold
#   2  IAC workspace below threshold
#   3  Required tool (cargo-tarpaulin) not installed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ---- Configuration --------------------------------------------------------
# ADR-040 Tier-2 thresholds
ROOT_LIB_THRESHOLD=71    # lib crates
ROOT_FWK_THRESHOLD=70    # framework crates
IAC_SVC_THRESHOLD=60     # service crates

REPORT_DIR="${REPO_ROOT}/.grade-reports"
mkdir -p "${REPORT_DIR}"

TARPAULIN_ARGS_COMMON="--out Xml --out Json --engine llvm --target-dir ${REPO_ROOT}/target"

# ---- Prerequisites --------------------------------------------------------
if ! command -v cargo >/dev/null 2>&1; then
    echo "[coverage-gate] cargo not found on PATH" >&2
    exit 3
fi

if ! cargo tarpaulin --version >/dev/null 2>&1; then
    echo "[coverage-gate] cargo-tarpaulin not installed; install with: cargo install cargo-tarpaulin" >&2
    exit 3
fi

# ---- Helpers --------------------------------------------------------------
run_coverage() {
    local label="$1"
    local manifest="$2"
    local threshold="$3"
    local report_file="$4"

    echo "[coverage-gate] Running ${label} coverage (threshold: ${threshold}%)..."

    # Build tarpaulin config args — use workspace manifest and fail-under
    # The --fail-under flag is per-run, applied globally for the workspace.
    # We store the raw JSON output for parsing.
    set +e
    cargo tarpaulin \
        --manifest-path "${manifest}" \
        --fail-under "${threshold}" \
        ${TARPAULIN_ARGS_COMMON} \
        --output-dir "${REPORT_DIR}" \
        2>"${REPORT_DIR}/${report_file}.stderr" \
        >"${REPORT_DIR}/${report_file}.stdout"
    local rc=$?
    set -e

    if [ "${rc}" -eq 0 ]; then
        echo "[coverage-gate]   PASS (${label} coverage >= ${threshold}%)"
    else
        echo "[coverage-gate]   FAIL (${label} coverage < ${threshold}%) — see ${REPORT_DIR}/${report_file}.*"
    fi

    return "${rc}"
}

# ---- Root workspace (lib + framework crates) ------------------------------
# Root workspace crates: nanovms-core (lib-71), nvms-ffi (lib-71),
# pheno-config (lib-71), pheno-compose-driver (framework-70).
# Use the strictest threshold (71%) as a conservative gate.
echo ""
echo "================================================================"
echo "  Root workspace (lib/framework crates)"
echo "  Threshold: ${ROOT_LIB_THRESHOLD}% (lib) / ${ROOT_FWK_THRESHOLD}% (framework)"
echo "  Gate uses: ${ROOT_LIB_THRESHOLD}% (conservative: strictest tier)"
echo "================================================================"

ROOT_PASS=true
if ! run_coverage "root-workspace" "${REPO_ROOT}/Cargo.toml" "${ROOT_LIB_THRESHOLD}" "coverage-root"; then
    ROOT_PASS=false
fi

# ---- IAC workspace (service crates) --------------------------------------
echo ""
echo "================================================================"
echo "  IAC workspace (service crates)"
echo "  Threshold: ${IAC_SVC_THRESHOLD}%"
echo "================================================================"

IAC_PASS=true
if [ -f "${REPO_ROOT}/iac/Cargo.toml" ]; then
    if ! run_coverage "iac-workspace" "${REPO_ROOT}/iac/Cargo.toml" "${IAC_SVC_THRESHOLD}" "coverage-iac"; then
        IAC_PASS=false
    fi
else
    echo "[coverage-gate]   SKIP (iac/ directory not found)"
fi

# ---- Summary --------------------------------------------------------------
echo ""
echo "================================================================"
echo "  Coverage Gate Summary"
echo "================================================================"
echo "  Root workspace: $([ "${ROOT_PASS}" = true ] && echo PASS || echo FAIL)"
echo "  IAC workspace:  $([ "${IAC_PASS}" = true ] && echo PASS || echo FAIL)"

if [ "${ROOT_PASS}" = false ]; then
    echo "[coverage-gate] FAIL: root workspace coverage below ${ROOT_LIB_THRESHOLD}% threshold"
    exit 1
fi

if [ "${IAC_PASS}" = false ]; then
    echo "[coverage-gate] FAIL: iac workspace coverage below ${IAC_SVC_THRESHOLD}% threshold"
    exit 2
fi

echo "[coverage-gate] PASS: all coverage thresholds met"
exit 0
