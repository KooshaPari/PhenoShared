#!/usr/bin/env bash
# phinbox plugin install — Factory Droid (factory)
# Registers phinbox-mcp via direct write to ~/.factory/mcp.json
# and installs the phinbox skill into ~/.factory/skills/.

set -euo pipefail

SRC="/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-tooling"

# 1. Resolve the phinbox-mcp binary
if ! command -v phinbox-mcp >/dev/null 2>&1; then
  echo "→ phinbox-mcp not on PATH"
  exit 1
fi

# 2. Write MCP server entry into ~/.factory/mcp.json
DROID_CONFIG="$HOME/.factory/mcp.json"
# Remove broken symlinks before writing — droid reads the resolved file
if [[ -L "$DROID_CONFIG" ]] && [[ ! -e "$DROID_CONFIG" ]]; then
  echo "→ removing broken symlink at $DROID_CONFIG"
  rm -f "$DROID_CONFIG"
fi
mkdir -p "$(dirname "$DROID_CONFIG")"
[[ -f "$DROID_CONFIG" ]] || echo '{}' > "$DROID_CONFIG"

# 3. Use Python heredoc for safe JSON merge (preserves any other MCP servers)
DROID_CONFIG="$DROID_CONFIG" python3 <<'PYEOF'
import json, os, pathlib

cfg_path = pathlib.Path(os.environ["DROID_CONFIG"])
text = cfg_path.read_text().strip()
cfg = json.loads(text) if text else {}

servers = cfg.setdefault("mcpServers", {})
servers["phinbox"] = {
    "command": "phinbox-mcp",
    "args": [],
    "transport": "stdio",
    "env": {
        "PHINBOX_INBOX_DIR": os.path.expanduser("~/.phinbox/inbox"),
    },
}

cfg_path.write_text(json.dumps(cfg, indent=2, sort_keys=False) + "\n")
print(f"✓ wrote {cfg_path}")
PYEOF

# 4. Install the phinbox skill into ~/.factory/skills-dir/phinbox
SKILL_SRC="$SRC/crates/phinbox/.phinbox/skills/phinbox/SKILL.md"
SKILL_DIR="$HOME/.factory/skills-dir/phinbox"
SKILL_DEST="$SKILL_DIR/SKILL.md"
mkdir -p "$SKILL_DIR"
cp "$SKILL_SRC" "$SKILL_DEST"
echo "→ installed skill at $SKILL_DEST"

# 5. Verify
echo "→ verification:"
grep -q '"phinbox"' "$DROID_CONFIG" || { echo "FAIL: phinbox not registered in mcp.json"; exit 1; }
test -f "$SKILL_DEST" || { echo "FAIL: skill not installed"; exit 1; }
echo "✓ phinbox plugin installed for droid (factory)"