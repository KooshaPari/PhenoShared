# Cursor plugin — phinbox

Installs the `phinbox` MCP server into Cursor and drops a `.cursorrules`
snippet you can append to your rules file.

## Install

```bash
./install.sh /path/to/your/host-repo
```

Or manually:

1. Add the contents of `cursor-mcp.json` to your `.cursor/mcp.json`.
2. Append `.cursorrules` to your `.cursorrules` (or merge the rules).
3. Restart Cursor.

## Verify

Open Cursor → Settings → MCP. You should see `phinbox_mcp` listed.

## Uninstall

1. Remove the `phinbox_mcp` entry from `.cursor/mcp.json`.
2. Remove the phinbox block from `.cursorrules`.