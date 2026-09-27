#!/usr/bin/env bash
# Justification (scripting policy): read-only health probe; ≤5 lines of orchestration
# calling `tailscale ping` and `curl`. Rust-replaceable but this is strictly glue.
set -euo pipefail
for n in oci-primary oci-secondary gcp-e2 home-mac; do
  printf "%-16s " "$n"; tailscale ping --c 1 --timeout 5s "$n" >/dev/null 2>&1 && echo OK || echo FAIL
done
