# Forge plugin — phinbox

This directory contains the Forgecode plugin manifest for the `phinbox`
native OS popup elicitation tool.

## Install

```bash
./install.sh /path/to/your/host-repo
```

Or, manually:

```bash
mkdir -p /path/to/your/host-repo/.forgecode/plugins/phinbox
cp plugin.toml /path/to/your/host-repo/.forgecode/plugins/phinbox/

mkdir -p /path/to/your/host-repo/.forgecode/skills
ln -s "$(pwd)/../../.phinbox/skills/phinbox" \
       /path/to/your/host-repo/.forgecode/skills/phinbox
```

Then make sure `phinbox-mcp` is on PATH (e.g., `cargo install --path
../../crates/phinbox`) and restart Forgecode.

## What this plugin does

- Registers the `phinbox_mcp` tool with Forgecode.
- Loads the `phinbox` skill so the agent knows when to invoke the tool.
- Wires up the schema so the tool's `inputSchema` / `outputSchema` is
  visible in Forgecode's tool picker.

## Verify

```bash
forgecode plugins list | grep phinbox
forgecode skills list | grep phinbox
```

## Uninstall

```bash
rm -rf /path/to/your/host-repo/.forgecode/plugins/phinbox
rm /path/to/your/host-repo/.forgecode/skills/phinbox
```