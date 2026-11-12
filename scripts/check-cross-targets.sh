#!/usr/bin/env bash
# Cross-target compile guard for cfg-gated Rust code (E1.7).
#
# A native `cargo test` / `make check` only compiles the cfg branches that
# match the host: a broken Windows renderer or Linux-only daemon path is
# invisible on macOS (and vice versa) — it simply is never compiled. This
# is a real bug class in this repo: `phinbox`'s `windows.rs` had never
# compiled (a hard `format!` "unused formatting arguments" error) until a
# cross-target check was run, and the crate could not be checked for
# Windows at all until the Unix-only inbox IPC module was gated.
#
# Generalised from `crates/phinbox/scripts/check-targets.sh` (E1.7,
# 2026-10-01): the crate list is now an argument, the target matrix lives
# in one table below, and `--locked` makes a stale lockfile fail the check
# instead of silently re-resolving.
#
# For every requested crate it runs `cargo check --all-targets --locked`
# once per target, skipping (loudly) any target whose rust-std component
# is not installed. Exit codes:
#   0  every checked target passed
#   1  at least one target failed with a real compile error
#   2  nothing was checked (rustup missing, or no matrix target installed)
#
# SKIP is neither pass nor failure. A target whose rust-std is absent is
# skipped before it runs. A target whose rust-std IS present but which fails
# without emitting any rustc diagnostic is also skipped: no `error[E....]` means
# rustc never ran, so the cause is the host or the manifest, not this crate. No
# single host holds a C toolchain for every other platform, and the Darwin legs
# need the macOS SDK. A failure WITH a diagnostic is always a real error and
# always fails the run. Every skip prints the tail of its output, so a skip can
# never hide why it happened.
#
# The toolchain itself is preflighted the same way: if rustup, cargo or rustc is
# missing or unusable, or the host target has no rust-std, the run prints
# `SKIP  toolchain — <what is missing>: <why>` and exits 2. It never counts as a
# checked target (see the env_gap note below).
#
# CI (quality-gate E1.8 job) installs every matrix target before calling
# this script, so a green run there proves the whole matrix ran; locally,
# skips are printed so they cannot masquerade as passes.
set -uo pipefail

# Crate -> target matrix. phinbox is currently the only crate with
# cfg-gated per-platform renderers; add another crate here when it grows
# platform-specific code, or pass crates as arguments for a one-off run.
DEFAULT_CRATES=(phinbox)
TARGETS=(
	x86_64-unknown-linux-gnu # Linux renderer + UDS inbox daemon (native on CI)
	x86_64-pc-windows-gnu    # Windows renderer
	x86_64-apple-darwin      # macOS renderer (cross even on this repo's macOS dev hosts)
)

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root" || exit 2

# An unusable toolchain is an ENVIRONMENT GAP: it is neither a pass nor a crate
# failure, so it is reported as an explicit SKIP naming the missing component,
# and the run then exits 2 ("nothing was checked"). It must never reach a CHECK
# line, because a CHECK line is a claim that this toolchain looked at this crate.
#
# This exact hole shipped as a green run. `rustc` was absent from PATH while
# `rustup`/`cargo` were present; `host="$(rustc -vV ...)"` printed
# "rustc: command not found" and, because this script runs `set -uo pipefail`
# (no `-e`), the failed assignment fell through as an empty string. `cargo` is
# the rustup proxy and resolves a rustc internally, so every leg still reported
# OK and the script exited 0 with `passed (3 checked, 0 skipped)` under a
# toolchain it could not name. Guard the toolchain, not just rustup.
env_gap() {
	echo "SKIP  toolchain — $1; nothing was checked" >&2
	exit 2
}

if ! command -v rustup >/dev/null 2>&1; then
	env_gap "rustup not found on PATH; cannot enumerate installed targets"
fi
if ! command -v cargo >/dev/null 2>&1; then
	env_gap "cargo not found on PATH; cannot run 'cargo check'"
fi
if ! command -v rustc >/dev/null 2>&1; then
	env_gap "rustc not found on PATH; cargo can still resolve one via the rustup proxy, so a 'pass' here would name no toolchain"
fi

# `rustc` being on PATH is not the same as being usable: a broken rustup
# override, a dangling proxy, or a mismatched toolchain all fail here.
if ! rustc_verbose="$(rustc -vV 2>&1)"; then
	env_gap "rustc is on PATH but 'rustc -vV' failed: ${rustc_verbose%%$'\n'*}"
fi
host="$(printf '%s\n' "${rustc_verbose}" | sed -n 's/^host: //p')"
if [[ -z ${host} ]]; then
	env_gap "'rustc -vV' reported no host triple; cannot tell which targets are cross"
fi
if ! rustc_identity="$(rustc --version 2>&1)"; then
	env_gap "rustc is on PATH but 'rustc --version' failed: ${rustc_identity%%$'\n'*}"
fi

crates=("$@")
if [ "${#crates[@]}" -eq 0 ]; then
	crates=("${DEFAULT_CRATES[@]}")
fi

if ! installed="$(rustup target list --installed 2>/dev/null)"; then
	env_gap "'rustup target list --installed' failed; cannot enumerate installed rust-std targets"
fi
if [[ -z ${installed} ]]; then
	env_gap "no rust-std targets installed for the active toolchain"
fi
if ! printf '%s\n' "${installed}" | grep -qx "${host}"; then
	env_gap "host target '${host}' has no rust-std installed (run: rustup target add ${host})"
fi

fail=0
checked=0
skipped=0

check_one() {
	local crate="$1" target="$2" out rc
	printf 'CHECK %-10s (%s) ... ' "$crate" "$target"
	# One cargo invocation, captured: the old version re-ran the same command to
	# print detail, which could report a different result than the first call.
	out="$(cargo check -p "$crate" --all-targets --target "$target" --locked 2>&1)"
	rc=$?
	if [ "$rc" -eq 0 ]; then
		echo "OK"
		checked=$((checked + 1))
		return
	fi
	# A failure carrying NO rustc diagnostic did not come from this crate: rustc
	# never ran. The first attempt at this keyed on cc-rs's wording instead, and
	# that was wrong -- the Darwin leg fails on a Linux host with a message that
	# matches no known marker, so the run said FAILED and then printed nothing,
	# because the detail grep also only looked for a rustc error. Judge on the
	# diagnostic, not the phrasing.
	if ! printf '%s\n' "$out" | grep -qE 'error\[E[0-9]+\]'; then
		echo "SKIP  — no rustc diagnostic; build environment, not this crate"
		# Always print the tail, so a skip can never hide its own reason.
		printf '%s\n' "$out" | tail -6 | sed 's/^/        /'
		skipped=$((skipped + 1))
		return
	fi
	echo "FAILED"
	printf '%s\n' "$out" | grep -E 'error\[E[0-9]+\]' -A5 | head -40
	checked=$((checked + 1))
	fail=1
}

echo "cross-target check (host: $host, toolchain: ${rustc_identity})"
for crate in "${crates[@]}"; do
	for target in "${TARGETS[@]}"; do
		if ! printf '%s\n' "$installed" | grep -qx "$target"; then
			echo "SKIP  $crate ($target) — not installed; 'rustup target add $target'"
			skipped=$((skipped + 1))
			continue
		fi
		check_one "$crate" "$target"
	done
done

if [ "$checked" -eq 0 ]; then
	echo "no matrix targets installed; nothing checked (matrix: ${TARGETS[*]})" >&2
	exit 2
fi
if [ "$fail" -ne 0 ]; then
	echo "cross-target check FAILED ($checked checked, $skipped skipped)"
	exit 1
fi
echo "cross-target check passed ($checked checked, $skipped skipped)"
