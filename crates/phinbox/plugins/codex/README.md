# Codex isolated-profile integration

The current installer uses the installed native `codex mcp add/get/remove` interface and **config.toml**. It does not write the obsolete auxiliary mcp.toml, inject a trust override, pass an unsupported `serve` subcommand, or modify PermissionRequest/Moshi/Xirp hooks.

Dry run (no filesystem changes):

```sh
bash crates/phinbox/plugins/codex/install.sh --profile-dir /tmp/phinbox-codex-profile --inbox-dir /tmp/phinbox-inbox --binary /absolute/path/phinbox-mcp
```

Add `--apply` to install into that explicit isolated profile. Use the same arguments with `--apply --uninstall` to remove only the unchanged registration owned by its receipt. Canonical ~/.codex and related harness profiles are deliberately rejected. For actual Codex discovery use `CODEX_HOME=/tmp/phinbox-codex-profile codex mcp get phinbox_mcp --json`; the installer never starts an MCP tool or an LLM session.

Native permission routing is a separate opt-in contract. See ../../docs/harness-contracts.md. Installing MCP does not intercept permission requests or authorize tool execution. The typed bridge handles only an actual pending PermissionRequest event and returns a native decision after explicit correlated input; its hooks must not replace existing guardrails.
