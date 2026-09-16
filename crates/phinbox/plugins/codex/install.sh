#!/usr/bin/env bash
# Install phinbox plugin for Codex.
#
# Usage:
#   ./install.sh [host-repo-path]
#
# If HOST_REPO is omitted, ~/.codex is used for global install.

set -euo pipefail

HOST_REPO="${1:-$HOME/.codex}"
PHINBOX_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo "→ Installing phinbox plugin for Codex into $HOST_REPO"

# 1. Copy the skill
mkdir -p "$HOST_REPO/skills/phinbox"
cp -r "$PHINBOX_DIR/.phinbox/skills/phinbox/." \
      "$HOST_REPO/skills/phinbox/"

# 2. Merge the MCP server entry into mcp.toml (create if absent)
MCP_TOML="$HOST_REPO/mcp.toml"
if [ ! -f "$MCP_TOML" ]; then
    cat > "$MCP_TOML" <<'EOF'
# Codex MCP servers — managed.

EOF
fi

if ! grep -q 'phinbox_mcp' "$MCP_TOML"; then
    cat >> "$MCP_TOML" <<'EOF'

# phinbox (added by plugins/phinbox/install.sh)
[mcp_servers.phinbox_mcp]
command = "phinbox-mcp"
args = ["serve"]
disabled = false
trust_level = "trusted"
EOF
fi

# 3. Verify phinbox-mcp is on PATH
if ! command -v phinbox-mcp >/dev/null 2>&1; then
    echo "warning: phinbox-mcp not found on PATH"
    echo "         install it with: cargo install --path $PHINBOX_DIR"
fi

echo "✓ phinbox installed for Codex."
echo "  Restart Codex to activate."