#!/usr/bin/env bash
# Justification (per scripting policy): ≤5-line glue wrapper. The orchestrator
# itself is the Rust binary `oci-post-acquire`; this wrapper just locates it on
# $PATH and execs. Installed to `~/.local/bin/oci-post-acquire.sh` for the
# lottery daemon to invoke.
set -euo pipefail
exec oci-post-acquire "$@"
