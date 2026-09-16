#!/usr/bin/env bash
# Install phinbox for the Antomous-backed `agent` CLI and the Cursor agent.
#
# Strategy:
#   1. `$agent` is the Antomous command-line agent. It reads MCP config from
#      `~/.clyde/mcp.json` (Antomous convention) and skill manifests from
#      `~/.clyde/skills/phinbox/`.
#   2. Cursor Agent CLI reads MCP config from `~/.cursor/mcp.json` and skill
#      manifests from `~/.cursor/skills/phinbox/`.
#   3. Both shells are kept in sync since the configuration is convergent.
#
# The MCP server entry runs `phinbox-mcp` over stdio. The skill manifest
# describes the behavioural contract so the agent knows when to call it.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SKILL_SRC="$REPO_ROOT/.phinbox/skills/phinbox/SKILL.md"

# ---------------------------------------------------------------------------
# 1. Ensure the phinbox binary is on PATH.
# ---------------------------------------------------------------------------
if ! command -v phinbox >/dev/null 2>&1; then
    echo "✗ phinbox not on PATH. Run \`phinbox install\` first." >&2
    exit 1
fi
if ! command -v phinbox-mcp >/dev/null 2>&1; then
    echo "✗ phinbox-mcp not on PATH. Run \`phinbox install\` first." >&2
    exit 1
fi

# ---------------------------------------------------------------------------
# 2. Write MCP stanzas for both agents.
# ---------------------------------------------------------------------------
write_mcp() {
    local path="$1"
    mkdir -p "$(dirname "$path")"
    if [[ -f "$path" ]]; then
        # Merge into existing mcp.json using a tiny Python helper.
        python3 - "$path" <<'PYEOF'
import json, sys
path = sys.argv[1]
try:
    with open(path) as f:
        data = json.load(f)
except (FileNotFoundError, json.JSONDecodeError):
    data = {}
servers = (
        data.setdefault("mcpServers", {})
        if "mcpServers" in data
        else data.setdefault("servers", {})
)
servers["phinbox"] = {
    "command": "phinbox-mcp",
    "args": [],
    "env": {"PHINBOX_INBOX_DIR": f"{__import__('os').environ.get('HOME', '~')}/.phinbox/inbox"},
    "alwaysAllow": [],
}
with open(path, "w") as f:
    json.dump(data, f, indent=2)
PYEOF
    else
        cat > "$path" <<EOF
{
  "mcpServers": {
    "phinbox": {
      "command": "phinbox-mcp",
      "args": [],
      "env": {"PHINBOX_INBOX_DIR": "\$HOME/.phinbox/inbox"},
      "alwaysAllow": []
    }
  }
}
EOF
    fi
    echo "✓ wrote $path"
}

write_mcp "$HOME/.clyde/mcp.json"
write_mcp "$HOME/.cursor/mcp.json"

# ---------------------------------------------------------------------------
# 3. Install the skill manifest in both locations.
# ---------------------------------------------------------------------------
install_skill() {
    local dest="$1"
    mkdir -p "$dest"
    if [[ -f "$SKILL_SRC" ]]; then
        cp "$SKILL_SRC" "$dest/SKILL.md"
    else
        cat > "$dest/SKILL.md" <<'EOF'
# elicit: non-blocking user prompts

Use the `phinbox_mcp` MCP tool when you need clarification from the user
that would otherwise block your workflow. Prefer it over inline `print` or
`AskUserQuestion` heuristics when:

- The question is one of the supported `FieldSpec` kinds (text, longtext,
  secret, integer, choice, boolean, date).
- The user is at a terminal or has the phinbox tray installed.
- You can defer and continue with useful work while waiting.

Behaviour:
- `phinbox` is **non-blocking** by default for the agent. The form goes
  to `~/.phinbox/inbox/<id>.json` and the agent receives a `deferred`
  response with the request id and an `open_url`.
- The user opens the form in their browser (or via the tray icon / TUI),
  answers, and the agent picks up the response on its next `phinbox wait`
  poll.
- Always set `urgency` and `notes` when the question requires a free-form
  answer.
- Never embed secrets in `notes` — they are logged and not encrypted.
EOF
    fi
    echo "✓ installed skill at $dest"
}

install_skill "$HOME/.clyde/skills/phinbox"
install_skill "$HOME/.cursor/skills/phinbox"

# ---------------------------------------------------------------------------
# 4. Verify by listing available tools.
# ---------------------------------------------------------------------------
if command -v agent >/dev/null 2>&1; then
    echo ""
    echo "→ verifying with \`agent mcp list\` ..."
    agent mcp list 2>&1 || echo "(agent mcp list exited $? — non-fatal)"
fi

echo ""
echo "✓ phinbox installed for the Antomous agent CLI and Cursor Agent CLI."
echo "  Restart your agent session to pick up the new MCP tool and skill."
