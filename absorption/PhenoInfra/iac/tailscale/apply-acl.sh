#!/usr/bin/env bash
# Justification (per scripting policy, ≤5 lines): single curl PUT against the
# Tailscale ACL endpoint. A Rust binary would add a Cargo.toml + reqwest just
# to wrap one HTTP call already covered by `tailscale-keygen` infra; net loss.
set -euo pipefail
: "${TS_API_KEY:?TS_API_KEY required}"; : "${TS_TAILNET:?TS_TAILNET required}"
curl -fsS -u "${TS_API_KEY}:" -H 'Content-Type: application/hujson' \
  -X PUT "https://api.tailscale.com/api/v2/tailnet/${TS_TAILNET}/acl" \
  --data-binary @"$(dirname "$0")/acl.json"
