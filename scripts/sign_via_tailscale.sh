#!/usr/bin/env bash
# sign_via_tailscale.sh — Run macOS signing scripts remotely from any machine
# (including Windows) by SSHing into your MacBook over Tailscale.
#
# This is the most ergonomic way to do Apple signing + cosign keyless
# signing + GHCR push without leaving your Windows box. Tailscale
# provides the secure mesh VPN; OpenSSH is built into macOS and Windows 10+.
#
# Setup (one-time):
#   1. On MacBook:
#        brew install tailscale
#        tailscale up
#        sudo systemsetup -setremotelogin on
#        # Get the IP:
#        tailscale ip -4
#        # Look for "100.x.y.z"
#   2. On Windows:
#        winget install Tailscale.Tailscale
#        tailscale up
#   3. (Optional but recommended) SSH key auth so no password prompt:
#        ssh-keygen -t ed25519 -f $HOME/.ssh/id_ed25519
#        type $HOME\.ssh\id_ed25519.pub | ssh USER@100.x.y.z "cat >> ~/.ssh/authorized_keys"
#
# Usage:
#   # Default: Tailscale auto-detect, sign v0.37 release
#   bash scripts/sign_via_tailscale.sh
#
#   # Override MacBook host
#   MAC=macos@100.x.y.z bash scripts/sign_via_tailscale.sh
#
#   # Different release tag
#   TAG=v0.38 bash scripts/sign_via_tailscale.sh
#
#   # Only do certain steps
#   STEPS=sign bash scripts/sign_via_tailscale.sh          # only sign tarball
#   STEPS=publish bash scripts/sign_via_tailscale.sh       # only push docker
#   STEPS=kernel bash scripts/sign_via_tailscale.sh        # only sign macOS kernel
#   STEPS="sign publish kernel" bash scripts/sign_via_tailscale.sh
#
#   # Pass extra args through to the remote scripts
#   bash scripts/sign_via_tailscale.sh -- --upload         # sign + upload in one go
#
# Scorecard impact (when run on a MacBook with the required tools):
#   - Signed-Releases: -1 -> 10 (cosign .sig + .cert attached to GH Release)
#   - Packaging:       -1 -> 10 (GHCR image published + cosign-signed)
#   - macOS Gatekeeper: passing locally after ad-hoc codesign

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MAC="${MAC:-}"
TAG="${TAG:-v0.37}"
STEPS="${STEPS:-sign publish kernel}"
EXTRA_ARGS="${*:-}"

# --- Tailscale host discovery ---
discover_mac() {
    # 1) Explicit MAC env var wins
    if [[ -n "$MAC" ]]; then
        echo "$MAC"
        return 0
    fi
    # 2) Tailscale on PATH (macOS, Linux, WSL)
    if command -v tailscale >/dev/null 2>&1; then
        local ip
        ip=$(tailscale status --json 2>/dev/null | \
            python3 -c "import json,sys; d=json.load(sys.stdin); peers=[p for k,p in d.get('Peer',{}).items() if any(os.startswith('100.') for os in p.get('TailscaleIPs',[]))]; print(peers[0]['TailscaleIPs'][0] if peers else '', end='')" 2>/dev/null || echo "")
        if [[ -n "$ip" ]]; then
            # Try to get the user from SSH config
            local user="${USER:-macos}"
            echo "${user}@${ip}"
            return 0
        fi
    fi
    # 3) ~/.ssh/config entries with Host tailscale-*
    if [[ -f "$HOME/.ssh/config" ]]; then
        local host
        host=$(grep -iE "^Host[[:space:]]+.*tailscale" "$HOME/.ssh/config" | head -1 | awk '{print $2}')
        if [[ -n "$host" ]]; then
            echo "$host"
            return 0
        fi
    fi
    return 1
}

MAC="$(discover_mac || true)"
if [[ -z "$MAC" ]]; then
    cat >&2 <<EOF
ERROR: Could not auto-discover your MacBook over Tailscale.

Set MAC explicitly:
  MAC=macos@100.x.y.z bash scripts/sign_via_tailscale.sh

To find the IP, on your MacBook run:
  tailscale ip -4
EOF
    exit 1
fi

log()  { printf '\033[1;34m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*"; }
fail() { printf '\033[1;31m[%s]\033[0m %s\n' "$(date +%H:%M:%S)" "$*" >&2; exit 1; }

log "Tailscale host: $MAC"
log "Tag:            $TAG"
log "Steps:          $STEPS"
[[ -n "$EXTRA_ARGS" ]] && log "Extra args:     $EXTRA_ARGS"
echo

# --- Pre-flight on local machine ---
command -v ssh >/dev/null 2>&1 || fail "ssh not found (install OpenSSH client)"

# SSH options: keep alive, fail fast, no strict host key prompt
SSH_OPTS=(
    -o ServerAliveInterval=30
    -o ServerAliveCountMax=3
    -o ConnectTimeout=15
    -o StrictHostKeyChecking=accept-new
)

# --- Sanity check: can we even reach the MacBook? ---
log "Probing $MAC..."
if ! ssh "${SSH_OPTS[@]}" "$MAC" "uname -s" >/dev/null 2>&1; then
    fail "Cannot reach $MAC over Tailscale. Check:
  - Tailscale is up on both machines: tailscale status
  - MacBook has 'Remote Login' enabled (System Settings -> General -> Sharing)
  - Try: ssh $MAC 'echo ok'"
fi
log "  reachable ($(ssh "${SSH_OPTS[@]}" "$MAC" 'uname -smr' 2>/dev/null))"
echo

# --- Sync the repo to the MacBook ---
# We do a fresh clone in a fixed location to keep this idempotent.
REMOTE_DIR="~/work/pheno-harness-remote"
log "Syncing repo to $MAC:$REMOTE_DIR"
ssh "${SSH_OPTS[@]}" "$MAC" "bash -s" -- <<EOF
set -e
mkdir -p ~/work
if [[ ! -d "$REMOTE_DIR/.git" ]]; then
    git clone https://github.com/<REDACTED>/pheno-harness.git "$REMOTE_DIR"
fi
cd "$REMOTE_DIR"
git fetch --tags origin
git checkout "$TAG" 2>/dev/null || git checkout main
git pull --rebase origin main 2>/dev/null || true
echo "On commit: \$(git rev-parse --short HEAD)"
EOF
echo

# --- Run the requested steps ---
run_remote() {
    local step="$1"
    case "$step" in
        kernel)
            log "=== STEP: kernel (Apple codesign ad-hoc/Developer ID) ==="
            ssh "${SSH_OPTS[@]}" -t "$MAC" "cd $REMOTE_DIR && bash scripts/sign_macos.sh $EXTRA_ARGS"
            ;;
        sign)
            log "=== STEP: sign (cosign keyless + upload tarball) ==="
            ssh "${SSH_OPTS[@]}" -t "$MAC" "cd $REMOTE_DIR && TAG=$TAG bash scripts/sign_release.sh $TAG $EXTRA_ARGS"
            ;;
        publish)
            log "=== STEP: publish (GHCR docker build + cosign sign image) ==="
            ssh "${SSH_OPTS[@]}" -t "$MAC" "cd $REMOTE_DIR && TAG=$TAG bash scripts/publish_docker.sh"
            ;;
        *)
            fail "Unknown step: $step (use: kernel, sign, publish)"
            ;;
    esac
}

for step in $STEPS; do
    run_remote "$step"
    echo
done

log "All steps complete."
log "View release: https://github.com/<REDACTED>/pheno-harness/releases/tag/${TAG}-pheno-harness-summit"
log "View package: https://github.com/<REDACTED>/pheno-harness/pkgs/container/pheno-harness"
