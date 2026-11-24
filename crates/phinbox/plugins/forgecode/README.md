# Forge isolated project integration

The current Forge/HeliosLite source resolves project MCP configuration at the project root **.mcp.json**, with a camelCase mcpServers map. The obsolete .forgecode/plugins manifest installer did not establish current MCP registration.

```sh
bash crates/phinbox/plugins/forgecode/install.sh --profile-dir /tmp/phinbox-forge-project --inbox-dir /tmp/phinbox-inbox --binary /absolute/path/phinbox-mcp
```

Dry-run is the default. Add --apply for the explicit isolated project, or --apply --uninstall to remove only the unchanged receipt-owned entry. Existing servers and hook files are preserved. No canonical user profile is modified, no server is started, and no hook protocol is invented. The current installed `forge` identifies as a deprecated HeliosLite lineage binary; runtime loader acceptance additionally requires its actual provider/model initialization. Isolated JSON lifecycle tests do not establish a running Forge integration.
