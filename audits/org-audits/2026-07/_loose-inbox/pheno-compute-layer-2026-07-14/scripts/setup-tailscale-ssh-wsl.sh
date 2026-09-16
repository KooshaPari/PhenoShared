#!/bin/bash
#==========================================
# Tailscale SSH Setup for WSL
# Run ONCE on Windows desktop in PowerShell
#==========================================

set -e

echo "============================================"
echo "Tailscale SSH Setup for WSL"
echo "============================================"
echo ""

# 1. Copy this script to Windows
# 2. Run: cmd /c C:\\Users\\koosh\\setup-wsl-ssh.bat
# 3. Use the pheno CLI: pheno wsl-ssh "command"

# Contents of setup-wsl-ssh.bat:
cat << 'BATCH'
@echo off
REM Setup SSH in WSL for Tailscale SSH

REM Generate SSH host keys
wsl -e bash -c "mkdir -p ~/.ssh"
wsl -e bash -c "ssh-keygen -t ed25519 -f ~/.ssh/ssh_host_ed25519_key -N ''"

REM Start sshd on port 2222
wsl -e bash -c "pkill sshd 2>nul"
wsl -e bash -c "/usr/sbin/sshd -p 2222 -h ~/.ssh/ssh_host_ed25519_key"

echo SSH daemon started on port 2222
BATCH

echo ""
echo "============================================"
echo "After setup, use these commands:"
echo ""
echo "SSH to WSL directly:"
echo "  ssh -p 2222 kooshapari@100.84.189.31 hostname"
echo ""
echo "Or use pheno CLI:"
echo "  pheno wsl hostname"
echo "============================================"
