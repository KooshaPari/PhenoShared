#!/usr/bin/env bash
# Install phinbox plugin for Claude Code v2.x
#
# Discovery paths used by Claude Code 2.1.197:
#   - MCP server catalog : ~/.claude.json    (mcpServers object)
#   - Skills             : ~/.claude/skills/<name>/SKILL.md
#   - Commands           : ~/.claude/commands/<name>.md
#   - Plugins            : ~/.claude/plugins/<name>/plugin.json
#
# We write directly to these JSON files because the `claude` CLI on this
# v2.1.x build does not expose a `claude mcp add` or `claude plugin install`
# subcommand (only the desktop app does). The CLI is a thin wrapper; the
# config is the source of truth and is read by the desktop app + the
# daemonised assistant.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRATE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL_SRC="$CRATE_ROOT/.phinbox/skills/phinbox/SKILL.md"
BIN_DIR="$CRATE_ROOT/target/release"
PHINBOX_BIN_DIR="${PHINBOX_BIN_DIR:-$BIN_DIR}"

# 1) Resolve the phinbox-mcp binary path
if command -v phinbox-mcp >/dev/null 2>&1; then
    PHINBOX_MCP_BIN="$(command -v phinbox-mcp)"
elif [ -x "$PHINBOX_BIN_DIR/phinbox-mcp" ]; then
    PHINBOX_MCP_BIN="$PHINBOX_BIN_DIR/phinbox-mcp"
elif [ -x "$PHINBOX_BIN_DIR/phinbox" ]; then
    PHINBOX_MCP_BIN="$PHINBOX_BIN_DIR/phinbox"
else
    echo "[claude_code] phinbox-mcp not on PATH; install phinbox first (cargo install --path $CRATE_ROOT --bin phinbox-mcp)." >&2
    exit 1
fi

CLAUDE_JSON="$HOME/.claude.json"

# 2) Register MCP server in ~/.claude.json
echo "[claude_code] Writing phinbox-mcp to $CLAUDE_JSON..."
if [ -f "$CLAUDE_JSON" ]; then
    # Use python3 for safe JSON manipulation (jq may not be available on all systems)
    python3 - "$CLAUDE_JSON" "$PHINBOX_MCP_BIN" <<'PYEOF'
import json
import sys
path, cmd = sys.argv[1], sys.argv[2]
with open(path, "r") as f:
    cfg = json.load(f)
cfg.setdefault("mcpServers", {})
cfg["mcpServers"]["phinbox-mcp"] = {
    "type": "stdio",
    "command": cmd,
    "args": [],
    "env": {},
}
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
print(f"  registered mcpServers.phinbox-mcp -> {cmd}")
PYEOF
else
    cat > "$CLAUDE_JSON" <<EOF
{
  "mcpServers": {
    "phinbox-mcp": {
      "type": "stdio",
      "command": "$PHINBOX_MCP_BIN",
      "args": [],
      "env": {}
    }
  }
}
EOF
    echo "  created $CLAUDE_JSON with phinbox-mcp entry"
fi

# 3) Install skill
if [ ! -f "$SKILL_SRC" ]; then
    echo "[claude_code] SKILL.md not found at $SKILL_SRC" >&2
    exit 1
fi
mkdir -p "$HOME/.claude/skills/phinbox"
ln -sf "$SKILL_SRC" "$HOME/.claude/skills/phinbox/SKILL.md"
echo "  symlinked $HOME/.claude/skills/phinbox/SKILL.md"

# 4) Install plugin manifest (Claude Code 2.x reads these directly)
mkdir -p "$HOME/.claude/plugins/phinbox"
cat > "$HOME/.claude/plugins/phinbox/plugin.json" <<EOF
{
  "name": "phinbox",
  "version": "$(phinbox --version 2>/dev/null | awk '{print $2}' || echo '0.9.0')",
  "description": "phinbox MCP server + skill for Claude Code",
  "mcpServers": {
    "phinbox-mcp": {
      "type": "stdio",
      "command": "$PHINBOX_MCP_BIN",
      "args": [],
      "env": {}
    }
  },
  "skills": [
    {
      "name": "phinbox",
      "path": "$HOME/.claude/skills/phinbox/SKILL.md"
    }
  ]
}
EOF
echo "  wrote $HOME/.claude/plugins/phinbox/plugin.json"

# 5) Smoke
echo "[claude_code] Smoke: phinbox --version"
phinbox --version

echo "[claude_code] OK."
