# Codex plugin — phinbox

Installs the `phinbox` MCP server + skill into Codex.

## Install

```bash
./install.sh                    # global: ~/.codex
./install.sh /path/to/host-repo # per-repo: <repo>/.codex
```

Or manually, copy `codex.toml` into your Codex MCP config and copy the
SKILL.md into your Codex skills directory.

## Verify

```bash
codex mcp list | grep phinbox_mcp
codex skills list | grep phinbox
```

## Uninstall

```bash
rm -rf ~/.codex/skills/phinbox
# Remove the [mcp_servers.phinbox_mcp] block from ~/.codex/mcp.toml
```