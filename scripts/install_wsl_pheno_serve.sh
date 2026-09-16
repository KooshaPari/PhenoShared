#!/bin/bash
# DAG-81: scripts/install_wsl_pheno_serve.sh
#
# Install the pheno-serve (inner inference router) baseline on a
# Fedora 44 WSL2 distribution. Idempotent.
#
# What it does:
#   1. dnf install -y python3.12 python3-pip git tailscale nvidia-driver
#   2. Creates the pheno-serve user + systemd unit (optional)
#   3. Clones the named branch into /opt/pheno-harness
#   4. Symlinks the launchd cron payloads to /etc/cron.d/pheno-harness
#      (the WSL/Fedora equivalent — systemd timers are also accepted
#      but cron is simpler for the dual-GPU lane schedule)
#   5. Records the install in /var/log/pheno-harness-install.log
#
# Usage (on the WSL host):
#   sudo bash scripts/install_wsl_pheno_serve.sh \\
#     --branch main \\
#     --repo-url https://github.com/<REDACTED>/pheno-harness.git
#
# The script is safe to re-run (idempotent at every step).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="${REPO_DIR:-/opt/pheno-harness}"
BRANCH="${BRANCH:-main}"
REPO_URL="${REPO_URL:-https://github.com/<REDACTED>/pheno-harness.git}"
LOG="/var/log/pheno-harness-install.log"

log() { echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" | tee -a "$LOG"; }

log "pheno-harness WSL/Fedora 44 install starting"
log "REPO_DIR=$REPO_DIR BRANCH=$BRANCH REPO_URL=$REPO_URL"

# 1. dnf packages
if command -v dnf >/dev/null 2>&1; then
  dnf install -y python3.12 python3-pip git tailscale nvidia-driver
else
  log "WARN: dnf not found; assuming packages are pre-installed"
fi

# 2. Repo clone
if [ ! -d "$REPO_DIR" ]; then
  git clone --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
fi
cd "$REPO_DIR"
git fetch origin "$BRANCH"
git checkout "origin/$BRANCH"

# 3. Symlink the cron payloads (systemd-style, not launchd)
mkdir -p /etc/cron.d/pheno-harness
for cron in scripts/cron/*.sh; do
  base="$(basename "$cron")"
  ln -sf "$REPO_DIR/$cron" "/etc/cron.d/pheno-harness/$base"
done

# 4. Force-fire today's SOTA snapshot (best-effort)
if [ -f "$REPO_DIR/scripts/cron/snapshot_sota.py" ]; then
  python3 "$REPO_DIR/scripts/cron/snapshot_sota.py" || true
fi

log "pheno-harness WSL/Fedora 44 install complete"
