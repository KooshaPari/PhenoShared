#!/bin/bash
#==========================================
# Setup script for pheno-compute-layer
# Run once to configure all tools
#==========================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/CodeProjects/Phenotype/pheno-compute-layer"
BIN_DIR="$HOME/bin"
SSH_CONFIG="$HOME/.ssh/config"

echo "============================================"
echo "pheno-compute-layer Setup"
echo "============================================"
echo ""

#----------------------------------
# 1. Verify SSH connection
#----------------------------------
echo "[1/4] Checking SSH connection..."
if timeout 5 ssh -o BatchMode=yes -o ConnectTimeout=5 desk "echo ok" 2>/dev/null; then
    echo "  SSH: Connected to desk"
else
    echo "  WARNING: Could not connect to desk via SSH"
    echo "  Please ensure SSH is working first"
fi

#----------------------------------
# 2. Install CLI to ~/bin
#----------------------------------
echo ""
echo "[2/4] Installing CLI..."

# Create ~/bin if needed
if [[ ! -d "$BIN_DIR" ]]; then
    mkdir -p "$BIN_DIR"
    echo "  Created $BIN_DIR"
fi

# Add to PATH if not already there
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo 'export PATH="$HOME/bin:$PATH"' >> "$HOME/.zshrc"
    echo "  Added $BIN_DIR to PATH in ~/.zshrc"
fi

# Symlink pheno CLI
if [[ ! -e "$BIN_DIR/pheno" ]]; then
    ln -s "$INSTALL_DIR/bin/pheno" "$BIN_DIR/pheno"
    echo "  Symlinked pheno to $BIN_DIR/pheno"
else
    echo "  pheno already installed"
fi

chmod +x "$INSTALL_DIR/bin/pheno"

#----------------------------------
# 3. Configure SSH
#----------------------------------
echo ""
echo "[3/4] Configuring SSH..."

# Check if desk host already configured
if grep -q "^Host desk" "$SSH_CONFIG" 2>/dev/null; then
    echo "  SSH config already contains 'desk' host"
else
    cat >> "$SSH_CONFIG" << 'EOF'

# pheno-compute-layer: kooshapari-desk (3090 Ti)
Host desk kooshapari-desk
    HostName kooshapari-desk.tail2b570.ts.net
    User kooshapari
    ForwardAgent yes
    IdentityFile ~/.ssh/id-git
    AddKeysToAgent yes
    UseKeychain yes
    BatchMode yes
    ConnectTimeout 10
    ServerAliveInterval 60

Host koosh-desk
    HostName 100.96.135.160
    User koosh
    IdentityFile ~/.ssh/id-git
    BatchMode yes
    StrictHostKeyChecking accept-new
EOF
    echo "  Added 'desk' host to SSH config"
fi

#----------------------------------
# 4. Verify installation
#----------------------------------
echo ""
echo "[4/4] Verifying installation..."
if command -v pheno &>/dev/null; then
    echo "  pheno CLI installed: $(which pheno)"
    echo ""
    echo "  Testing connection..."
    pheno status || true
else
    echo "  WARNING: pheno not in PATH. Restart shell or run:"
    echo "    source ~/.zshrc"
fi

#----------------------------------
# 5. Install FastMCP (optional)
#----------------------------------
echo ""
echo "[Optional] Install FastMCP server? (y/n)"
read -r -n 1 response
if [[ "$response" =~ ^[Yy]$ ]]; then
    pip install fastmcp 2>/dev/null || uv pip install fastmcp 2>/dev/null || echo "  Could not install fastmcp"
fi

echo ""
echo "============================================"
echo "Setup complete!"
echo ""
echo "Usage:"
echo "  pheno gpu           # Check GPU"
echo "  pheno status        # Check connection"
echo "  pheno run <cmd>     # Run command"
echo ""
echo "Or use directly:"
echo "  $INSTALL_DIR/bin/pheno gpu"
echo "============================================"
