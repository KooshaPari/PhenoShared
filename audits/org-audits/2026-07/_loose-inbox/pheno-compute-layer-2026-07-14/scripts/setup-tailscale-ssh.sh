#!/bin/bash
#==========================================
# Tailscale SSH Setup for WSL
# Run on Windows desktop to enable Tailscale SSH
#==========================================

set -e

echo "============================================"
echo "Tailscale SSH Setup for WSL"
echo "============================================"
echo ""

# Check if running on Windows
if ! command -v wsl &>/dev/null; then
    echo "[ERROR] WSL not found. Run this on Windows."
    exit 1
fi

echo "[1/5] Checking WSL distribution..."
WSL_DISTRO=$(wsl -l --quiet | grep -E "(Ubuntu|Debian)" | head -1)
if [[ -z "$WSL_DISTRO" ]]; then
    echo "No Ubuntu/Debian WSL found. Please install one first."
    exit 1
fi
echo "Found: $WSL_DISTRO"

echo ""
echo "[2/5] Checking Tailscale in WSL..."
TS_PATH=$(wsl -e which tailscale 2>/dev/null || echo "")
if [[ -z "$TS_PATH" ]]; then
    echo "Tailscale not installed in WSL. Installing..."
    wsl -e bash -c "curl -fsSL https://tailscale.com/install.sh | sh" 2>/dev/null || {
        echo "Manual install needed. Run in WSL:"
        echo "  curl -fsSL https://tailscale.com/install.sh | sh"
    }
else
    echo "Tailscale found at: $TS_PATH"
fi

echo ""
echo "[3/5] Checking WSL user..."
WSL_USER=$(wsl -e whoami 2>/dev/null || echo "root")
echo "WSL user: $WSL_USER"

echo ""
echo "[4/5] Adding SSH public key to WSL..."
SSH_KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILZZVKELp+/rncu0lMKS2N7DSP/nAsgvnhzPQ7AP5ubt kooshapari@gmail.com"

wsl -e bash -c "mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '$SSH_KEY' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
echo "SSH key added to WSL"

echo ""
echo "[5/5] Starting Tailscale SSH..."
wsl -e bash -c "sudo tailscale up --ssh" 2>/dev/null || {
    echo "Tailscale SSH may need authentication. Run manually in WSL:"
    echo "  sudo tailscale up --ssh"
    echo "  tailscale login"
}

echo ""
echo "============================================"
echo "Setup complete!"
echo ""
echo "To connect from Mac:"
echo "  ssh kooshapari-desk"
echo "  tailscale ssh kooshapari-desk"
echo ""
echo "Or add to ~/.ssh/config:"
echo "  Host kooshapari-desk desk"
echo "    HostName kooshapari-desk.tail2b570.ts.net"
echo "    User kooshapari"
echo "    ForwardAgent yes"
echo "============================================"
