#!/usr/bin/env bash
# W44-B2 Windows Allocator Prod Rollout — Readiness Gate
#
# Validates the machine-resolvable portion of W44-B2 (per WAVE44_SCOPE.md).
# Human-gated: prod rollout window + on-call SRE sign-off.
#
# Exit codes: 0 = ready, 1 = blocker

set -euo pipefail

# 1. mimalloc Windows dep in daemon Cargo.toml
if ! grep -q "mimalloc" crates/sl-daemon/Cargo.toml 2>/dev/null; then
  printf 'BLOCKER: crates/sl-daemon/Cargo.toml missing mimalloc dep\n' >&2
  exit 1
fi

# 2. platform-allocator feature enabled in daemon main
if ! grep -q 'jemalloc\|mimalloc\|platform_allocator' crates/sl-daemon/src/main.rs 2>/dev/null; then
  printf 'BLOCKER: daemon main.rs does not reference platform allocator\n' >&2
  exit 1
fi

# 3. CI workflow mentions Windows
if ! grep -rl 'windows' .github/workflows/*.yml 2>/dev/null | grep -q .; then
  printf 'WARN: no CI workflow mentions windows\n' >&2
fi

printf 'PASS: machine-resolvable W44-B2 portion ready\n'
printf 'NEXT: human-gated — schedule prod rollout (Wed 23:00 UTC), get SRE sign-off\n'
exit 0
