#!/usr/bin/env bash
# Install phinbox plugin for Forge.
#
# Usage:
#   ./install.sh [host-repo-path]
#
# If HOST_REPO is omitted, the current working directory is used.

set -euo pipefail

HOST_REPO="${1:-$PWD}"
PHINBOX_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

echo "→ Installing phinbox plugin for Forge into $HOST_REPO"

# 1. Copy the plugin manifest
mkdir -p "$HOST_REPO/.forgecode/plugins/phinbox"
cp "$PHINBOX_DIR/plugins/forgecode/plugin.toml" \
   "$HOST_REPO/.forgecode/plugins/phinbox/"

# 2. Symlink the skill
mkdir -p "$HOST_REPO/.forgecode/skills"
ln -sfn "$PHINBOX_DIR/.phinbox/skills/phinbox" \
        "$HOST_REPO/.forgecode/skills/phinbox"

# 3. Verify phinbox-mcp is on PATH
if ! command -v phinbox-mcp >/dev/null 2>&1; then
    echo "warning: phinbox-mcp not found on PATH"
    echo "         install it with: cargo install --path $PHINBOX_DIR"
    echo "         or:              brew install phinbox   (when available)"
fi

echo "✓ phinbox installed for Forge."
echo "  Restart Forgecode to activate."