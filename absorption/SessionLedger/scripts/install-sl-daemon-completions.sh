#!/usr/bin/env bash
# Install committed sl-daemon shell completions from crates/sl-daemon/completions/.
#
# Usage:
#   sh scripts/install-sl-daemon-completions.sh [bash|zsh|fish|powershell|all]
#
# Environment:
#   SL_COMPLETIONS_DIR   Override destination root (default: shell-specific XDG/home paths)
#   SL_REPO_ROOT         Repo root containing crates/sl-daemon/completions (default: git root / cwd)

set -eu

shell_arg="${1:-all}"
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
repo_root="${SL_REPO_ROOT:-}"
if [ -z "$repo_root" ]; then
  if command -v git >/dev/null 2>&1 && git -C "$script_dir/.." rev-parse --show-toplevel >/dev/null 2>&1; then
    repo_root="$(git -C "$script_dir/.." rev-parse --show-toplevel)"
  else
    repo_root="$(CDPATH= cd -- "$script_dir/.." && pwd)"
  fi
fi

src_dir="$repo_root/crates/sl-daemon/completions"
if [ ! -d "$src_dir" ]; then
  echo "error: completions directory not found: $src_dir" >&2
  echo "hint: regenerate with: cargo run -p sl-daemon -- completions <shell>" >&2
  exit 1
fi

install_file() {
  src="$1"
  dest="$2"
  if [ ! -f "$src" ]; then
    echo "error: missing source completion file: $src" >&2
    exit 1
  fi
  mkdir -p "$(dirname -- "$dest")"
  cp "$src" "$dest"
  echo "installed $dest"
}

install_bash() {
  dest="${SL_COMPLETIONS_DIR:-${XDG_DATA_HOME:-$HOME/.local/share}/bash-completion/completions}/sl-daemon"
  install_file "$src_dir/sl-daemon.bash" "$dest"
}

install_zsh() {
  dest="${SL_COMPLETIONS_DIR:-$HOME/.zsh/completions}/_sl-daemon"
  install_file "$src_dir/_sl-daemon" "$dest"
  echo "note: ensure fpath includes $(dirname -- "$dest") and run: autoload -Uz compinit && compinit"
}

install_fish() {
  dest="${SL_COMPLETIONS_DIR:-$HOME/.config/fish/completions}/sl-daemon.fish"
  install_file "$src_dir/sl-daemon.fish" "$dest"
}

install_powershell() {
  # Prefer Windows-friendly copy; also works under pwsh on Unix profiles.
  if command -v pwsh >/dev/null 2>&1; then
    profile_dir="$(pwsh -NoProfile -Command 'Split-Path -Parent $PROFILE' 2>/dev/null || true)"
  else
    profile_dir=""
  fi
  if [ -z "$profile_dir" ]; then
    profile_dir="${SL_COMPLETIONS_DIR:-$HOME/.config/powershell}"
  elif [ -n "${SL_COMPLETIONS_DIR:-}" ]; then
    profile_dir="$SL_COMPLETIONS_DIR"
  fi
  dest="$profile_dir/sl-daemon.ps1"
  install_file "$src_dir/sl-daemon.ps1" "$dest"
  echo "note: add to your PowerShell profile: . '$dest'"
}

usage() {
  cat <<'EOF'
Install SessionLedger sl-daemon shell completions (committed artifacts).

Usage:
  sh scripts/install-sl-daemon-completions.sh [bash|zsh|fish|powershell|all]

Environment:
  SL_COMPLETIONS_DIR   Destination directory override
  SL_REPO_ROOT         Checkout root (default: detected via git)

To regenerate committed files after CLI changes:
  cargo run -p sl-daemon -- completions bash > crates/sl-daemon/completions/sl-daemon.bash
  cargo run -p sl-daemon -- completions zsh > crates/sl-daemon/completions/_sl-daemon
  cargo run -p sl-daemon -- completions fish > crates/sl-daemon/completions/sl-daemon.fish
  cargo run -p sl-daemon -- completions powershell > crates/sl-daemon/completions/sl-daemon.ps1
EOF
}

case "$shell_arg" in
  -h|--help|help) usage; exit 0 ;;
  bash) install_bash ;;
  zsh) install_zsh ;;
  fish) install_fish ;;
  powershell|pwsh) install_powershell ;;
  all)
    install_bash
    install_zsh
    install_fish
    install_powershell
    ;;
  *)
    echo "error: unknown shell '$shell_arg'" >&2
    usage >&2
    exit 2
    ;;
esac
