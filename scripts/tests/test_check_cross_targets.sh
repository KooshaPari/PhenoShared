#!/usr/bin/env bash
# test_check_cross_targets.sh — exercise scripts/check-cross-targets.sh against
# a fake toolchain, so every preflight branch is reachable without touching the
# real one.
#
# The case that matters: `rustc` absent from PATH while `rustup`/`cargo` are
# present. `cargo` is the rustup proxy and resolves a rustc internally, so the
# guard used to run every leg, print `rustc: command not found`, and exit 0 with
# `passed (3 checked, 0 skipped)` under a toolchain it could not name. That is
# an environment gap reported as a pass; these tests fail on it.
#
# Fake binaries only (rustup, rustc, cargo) in a throwaway PATH. Nothing is
# compiled and no network is used.
#
# Bash 3.2 portable (macOS default); no external deps.

set -euo pipefail

TESTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$(cd "${TESTS_DIR}/.." && pwd)"
# CHECK_SCRIPT lets the same cases run against a reverted copy of the script,
# which is how the regression test is proven to fail on the old behaviour.
CHECK="${CHECK_SCRIPT:-${SCRIPTS_DIR}/check-cross-targets.sh}"
FAKE_BIN="$(mktemp -d -t check_cross_targets.XXXXXX)"
trap 'rm -rf "${FAKE_BIN}"' EXIT

_log() { printf '[test_check_cross_targets] %s\n' "$*" >&2; }

# System paths minus every toolchain directory, so only FAKE_BIN supplies the
# rust tools.
BASE_PATH="/usr/bin:/bin:/usr/sbin:/sbin"

_host="aarch64-apple-darwin"
_matrix="x86_64-unknown-linux-gnu
x86_64-pc-windows-gnu
x86_64-apple-darwin"

_make_rustup() {
	cat >"${FAKE_BIN}/rustup" <<EOF
#!/usr/bin/env bash
if [ "\${1:-}" = "target" ] && [ "\${2:-}" = "list" ] && [ "\${3:-}" = "--installed" ]; then
    printf '%s\n' "${_matrix}" "${_host}"
    exit 0
fi
echo "fake rustup: unsupported argv \$*" >&2
exit 1
EOF
	chmod +x "${FAKE_BIN}/rustup"
}

_make_rustc() {
	# $1 = exit code of `rustc -vV`; $2 = whether to emit a host line
	cat >"${FAKE_BIN}/rustc" <<EOF
#!/usr/bin/env bash
if [ "\${1:-}" = "-vV" ]; then
    echo "rustc 1.99.0 (fake)"
    echo "binary: rustc"
    [ "${2}" = "with-host" ] && echo "host: ${_host}"
    exit ${1}
fi
if [ "\${1:-}" = "--version" ]; then
    echo "rustc 1.99.0 (fake)"
    exit 0
fi
exit 0
EOF
	chmod +x "${FAKE_BIN}/rustc"
}

_make_cargo() {
	# $1 = "ok" (exit 0), "diag" (exit 1 with error[E0308]), "envgap"
	case "$1" in
	ok)
		cat >"${FAKE_BIN}/cargo" <<'EOF'
#!/usr/bin/env bash
echo "    Finished `dev` profile [unoptimized + debuginfo] target(s)"
exit 0
EOF
		;;
	diag)
		cat >"${FAKE_BIN}/cargo" <<'EOF'
#!/usr/bin/env bash
echo "   Compiling demo v0.1.0"
echo "error[E0308]: mismatched types"
echo " --> src/lib.rs:2:5"
echo "  |"
echo "2 |     1u8"
echo "  |     ^^^ expected `u32`, found `u8`"
exit 101
EOF
		;;
	envgap)
		# cc-rs style, no rustc diagnostic anywhere in the output.
		cat >"${FAKE_BIN}/cargo" <<'EOF'
#!/usr/bin/env bash
echo "   Compiling demo v0.1.0"
echo "error: failed to run custom build command for `demo v0.1.0`"
echo "  error occurred in cc-rs: failed to find tool \"x86_64-linux-gnu-gcc\": No such file or directory (os error 2)"
echo "warning: build failed, waiting for other jobs to finish..."
exit 101
EOF
		;;
	*)
		_log "unknown fake cargo mode: $1"
		exit 1
		;;
	esac
	chmod +x "${FAKE_BIN}/cargo"
}

_reset_fakes() {
	rm -f "${FAKE_BIN}/rustup" "${FAKE_BIN}/rustc" "${FAKE_BIN}/cargo"
}

_failures=0

# run_case <name> <expected-exit> <expected-stdout-substring>...
run_case() {
	local name="$1" want_rc="$2"
	shift 2
	local out rc=0
	out="$(PATH="${FAKE_BIN}:${BASE_PATH}" bash "${CHECK}" demo 2>&1)" || rc=$?
	if [[ ${rc} -ne ${want_rc} ]]; then
		_log "FAIL ${name}: exit ${rc}, expected ${want_rc}"
		printf '%s\n' "${out}" | sed 's/^/        /' >&2
		_failures=$((_failures + 1))
		return
	fi
	local needle
	for needle in "$@"; do
		if ! printf '%s\n' "${out}" | grep -qF "${needle}"; then
			_log "FAIL ${name}: output missing '${needle}'"
			printf '%s\n' "${out}" | sed 's/^/        /' >&2
			_failures=$((_failures + 1))
			return
		fi
	done
	_log "ok   ${name} (exit ${rc})"
}

# --- 1. rustc missing (rustup + cargo present): the reported defect ----------
_reset_fakes
_make_rustup
_make_cargo ok
run_case "rustc missing -> SKIP, never a pass" 2 \
	"SKIP  toolchain" "rustc not found on PATH"
assert_no_check() {
	local name="$1" out rc=0
	out="$(PATH="${FAKE_BIN}:${BASE_PATH}" bash "${CHECK}" demo 2>&1)" || rc=$?
	if printf '%s\n' "${out}" | grep -q '^CHECK '; then
		_log "FAIL ${name}: a CHECK line was emitted with no usable toolchain"
		printf '%s\n' "${out}" | sed 's/^/        /' >&2
		_failures=$((_failures + 1))
	else
		_log "ok   ${name} (no CHECK line) (exit ${rc})"
	fi
}

# --- 2. rustup missing -------------------------------------------------------
_reset_fakes
_make_rustc 0 with-host
_make_cargo ok
run_case "rustup missing -> SKIP" 2 "SKIP  toolchain" "rustup not found on PATH"

# --- 3. cargo missing --------------------------------------------------------
_reset_fakes
_make_rustup
_make_rustc 0 with-host
run_case "cargo missing -> SKIP" 2 "SKIP  toolchain" "cargo not found on PATH"

# --- 4. rustc on PATH but unusable (`rustc -vV` fails) ----------------------
_reset_fakes
_make_rustup
_make_rustc 1 with-host
_make_cargo ok
run_case "unusable rustc -> SKIP" 2 "SKIP  toolchain" "'rustc -vV' failed"

# --- 5. rustc -vV emits no host triple --------------------------------------
_reset_fakes
_make_rustup
_make_rustc 0 no-host
_make_cargo ok
run_case "no host triple -> SKIP" 2 "SKIP  toolchain" "no host triple"

# --- 6. clean crate: every matrix target OK -> real pass --------------------
_reset_fakes
_make_rustup
_make_rustc 0 with-host
_make_cargo ok
run_case "clean crate -> PASS" 0 "passed (3 checked, 0 skipped)" "CHECK demo"

# --- 7. real compile diagnostic still FAILS ---------------------------------
_reset_fakes
_make_rustup
_make_rustc 0 with-host
_make_cargo diag
run_case "compile error -> FAIL" 1 "FAILED" "error[E0308]" "cross-target check FAILED"

# --- 8. build.rs environment gap: SKIP and print the tail -------------------
_reset_fakes
_make_rustup
_make_rustc 0 with-host
_make_cargo envgap
run_case "build.rs env gap -> SKIP + tail" 2 \
	"SKIP  — no rustc diagnostic" \
	"failed to find tool" \
	"nothing checked"

if [[ ${_failures} -ne 0 ]]; then
	echo "check-cross-targets tests: ${_failures} failure(s)" >&2
	exit 1
fi
echo "check-cross-targets tests: PASS (8 cases)"
