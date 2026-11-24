#!/usr/bin/env bash
# DEPRECATED — use forge-proc-reap.sh (no -er suffix) instead.
#
# This stub is preserved for backwards compatibility with any external
# callers that referenced the old name. The launchd plist
# com.phenoforge.forge-proc-reap now points at forge-proc-reap.sh, not
# this file.
#
# Forwarding wrapper:
exec "$(dirname "$0")/forge-proc-reap.sh" "$@"
