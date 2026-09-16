# pheno-compute-layer

Global compute layer for accessing your 3090 Ti desktop via Tailscale SSH.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/kooshapari/pheno-compute-layer.git
cd pheno-compute-layer
./scripts/setup.sh

# Use CLI
pheno gpu           # Check GPU status
pheno status        # Check connection
pheno run nvidia-smi -L  # Run any command
```

## Installation for All AI Tools

### 1. SSH Access (already configured)

The `desk` alias is set up in `~/.ssh/config`:
```bash
ssh desk "nvidia-smi"
```

### 2. Global CLI

```bash
# Add to PATH (assuming ~/bin is in PATH)
ln -s /path/to/pheno-compute-layer/bin/pheno ~/bin/pheno

# Or use directly
./bin/pheno gpu
```

### 3. Claude Code

Add to `~/.claude.json`:
```json
{
  "env": {
    "COMPUTE_HOST": "desk",
    "COMPUTE_IP": "100.96.135.160"
  }
}
```

### 4. Cursor Agent

Add to Cursor settings (`~/.cursor/settings.json`):
```json
{
  "cursorai.remoteSshHost": "desk",
  "terminal.integrated.env.LINUX": {
    "COMPUTE_HOST": "desk"
  }
}
```

### 5. FastMCP Server

```bash
# Install dependencies
pip install fastmcp

# Run server
python mcp/pheno_gpu_mcp.py

# Configure Claude Desktop with:
# ~/.config/claude-desktop/mcp_settings.json
{
  "mcpServers": {
    "pheno-gpu": {
      "command": "python",
      "args": ["/path/to/pheno-compute-layer/mcp/pheno_gpu_mcp.py"]
    }
  }
}
```

### 6. Tailscale SSH (WSL)

```bash
# On Windows desktop, run:
.\scripts\setup-tailscale-ssh.sh

# Or manually in WSL:
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --ssh
```

## Available Commands

| Command | Description |
|---------|-------------|
| `pheno status` | Check SSH connection |
| `pheno gpu` | GPU status (quick) |
| `pheno gpu-full` | Full nvidia-smi output |
| `pheno gpu-proc` | GPU compute processes |
| `pheno sysinfo` | System information |
| `pheno run <cmd>` | Run command on desktop |
| `pheno shell` | Interactive SSH shell |

## Structure

```
pheno-compute-layer/
├── bin/
│   └── pheno              # Global CLI
├── mcp/
│   └── pheno_gpu_mcp.py   # FastMCP server
├── config/
│   ├── mcp.json          # MCP configuration
│   └── ssh-config-reference  # SSH config for all tools
├── scripts/
│   ├── setup.sh          # Setup script
│   └── setup-tailscale-ssh.sh  # Tailscale SSH setup
└── docs/
    └── Tailscale-SSH-Setup.md
```

## Hardware

- **Host**: kooshapari-desk (Tailscale: kooshapari-desk.tail2b570.ts.net)
- **GPU**: NVIDIA GeForce RTX 3090 Ti (24GB)
- **IP**: 100.96.135.160
- **CUDA**: 13.1
- **Driver**: 591.86

## argis (argismonitor v4) bridge

The pheno CLI includes an `argis` wrapper for the v4 monorepo's
master CLI. If you have `argis` on PATH (it's symlinked into
`~/bin/argis` from `repos/OmniRoute-frontend-svelte-2026-07-05/bin/argis`),
you can run it through pheno:

```bash
pheno argis dev               # deploy + serve + expose on desktop
pheno argis cutover 1         # flip OMNI_WEB_STACK_ROLLOUT=1
pheno argis status            # health snapshot
pheno argis logs bff          # tail desktop logs
pheno argis ssh               # open shell on desktop
```

The `argis dev` flow: sync the v4 monorepo to the desktop over Tailscale
SSH, build, start BFF + kbridge + legacy Next.js, expose via Tailscale
Funnel, update all matching Vercel prod envs. One command to take a
clean desktop + Vercel frontends to a fully-running v4 deployment.
