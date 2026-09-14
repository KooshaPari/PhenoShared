#!/usr/bin/env bash
# install.sh — One-liner installer for NanoVMS
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/KooshaPari/nanovms/main/install.sh | sh
#
# Supports: macOS (arm64/x86_64), Linux (amd64/arm64), Windows (via Git Bash/WSL)
# Methods: Homebrew, .deb, .rpm, binary tar.gz

set -euo pipefail

# ── Config ───────────────────────────────────────────────────
GITHUB_REPO="KooshaPari/nanovms"
BINARY_NAME="nvms"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
LATEST_VERSION=""  # auto-detected

# ── Colors ───────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[info]${NC}  $*"; }
ok()    { echo -e "${GREEN}[ok]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[warn]${NC}  $*"; }
err()   { echo -e "${RED}[error]${NC} $*" >&2; }

# ── Platform detection ───────────────────────────────────────
detect_platform() {
    local os arch

    case "$(uname -s)" in
        Linux*)     os="linux" ;;
        Darwin*)    os="darwin" ;;
        MINGW*|MSYS*|CYGWIN*)  os="windows" ;;
        *)          err "Unsupported OS: $(uname -s)"; exit 1 ;;
    esac

    case "$(uname -m)" in
        x86_64|amd64)   arch="amd64" ;;
        aarch64|arm64)   arch="arm64" ;;
        *)               err "Unsupported arch: $(uname -m)"; exit 1 ;;
    esac

    echo "${os}_${arch}"
}

# ── Version detection ────────────────────────────────────────
get_latest_version() {
    if [ -n "$LATEST_VERSION" ]; then
        echo "$LATEST_VERSION"
        return
    fi

    local version
    version=$(curl -fsSL "https://api.github.com/repos/${GITHUB_REPO}/releases/latest" \
        | grep '"tag_name"' | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/')

    if [ -z "$version" ]; then
        err "Failed to detect latest version"
        exit 1
    fi

    echo "$version"
}

# ── Install via Homebrew (macOS) ─────────────────────────────
install_homebrew() {
    if command -v brew >/dev/null 2>&1; then
        info "Installing via Homebrew..."
        brew install KooshaPari/nanovms/nanovms
        ok "Installed via Homebrew"
        return 0
    fi
    return 1
}

# ── Install via .deb (Debian/Ubuntu) ─────────────────────────
install_deb() {
    local version="$1"
    local deb_url="https://github.com/${GITHUB_REPO}/releases/download/${version}/nanovms_${version#v}_linux_amd64.deb"

    if curl -fsSL --head "$deb_url" >/dev/null 2>&1; then
        local deb_file="/tmp/nanovms-${version}.deb"
        info "Downloading .deb package..."
        curl -fSL "$deb_url" -o "$deb_file"
        sudo dpkg -i "$deb_file" || sudo apt-get install -f -y
        rm -f "$deb_file"
        ok "Installed via .deb"
        return 0
    fi
    return 1
}

# ── Install via .rpm (Fedora/RHEL) ───────────────────────────
install_rpm() {
    local version="$1"
    local rpm_url="https://github.com/${GITHUB_REPO}/releases/download/${version}/nanovms_${version#v}_linux_amd64.rpm"

    if curl -fsSL --head "$rpm_url" >/dev/null 2>&1; then
        local rpm_file="/tmp/nanovms-${version}.rpm"
        info "Downloading .rpm package..."
        curl -fSL "$rpm_url" -o "$rpm_file"
        sudo rpm -i "$rpm_file"
        rm -f "$rpm_file"
        ok "Installed via .rpm"
        return 0
    fi
    return 1
}

# ── Install binary tar.gz ────────────────────────────────────
install_binary() {
    local platform="$1" version="$2"
    local os arch

    os=$(echo "$platform" | cut -d_ -f1)
    arch=$(echo "$platform" | cut -d_ -f2)

    local archive_url="https://github.com/${GITHUB_REPO}/releases/download/${version}/${BINARY_NAME}_${version#v}_${os}_${arch}.tar.gz"
    local tmp_dir
    tmp_dir=$(mktemp -d)

    info "Downloading binary tar.gz..."
    curl -fSL "$archive_url" | tar xz -C "$tmp_dir"

    mkdir -p "$INSTALL_DIR"
    mv "${tmp_dir}/${BINARY_NAME}" "${INSTALL_DIR}/${BINARY_NAME}"
    chmod +x "${INSTALL_DIR}/${BINARY_NAME}"
    rm -rf "$tmp_dir"

    ok "Installed ${BINARY_NAME} to ${INSTALL_DIR}/"

    # PATH hint
    case ":$PATH:" in
        *":${INSTALL_DIR}:"*) ;;
        *) warn "Add ${INSTALL_DIR} to your PATH:" ;;
    esac
    echo "  export PATH=\"${INSTALL_DIR}:\$PATH\""
}

# ── Main ─────────────────────────────────────────────────────
main() {
    info "NanoVMS installer"
    echo ""

    local platform version os_type
    platform=$(detect_platform)
    version=$(get_latest_version)
    os_type=$(echo "$platform" | cut -d_ -f1)

    info "Platform: ${platform}"
    info "Version:  ${version}"
    echo ""

    case "$os_type" in
        darwin)
            # Try Homebrew first, then binary
            install_homebrew || install_binary "$platform" "$version"
            ;;
        linux)
            # Try distro packages, then binary
            if command -v dpkg >/dev/null 2>&1; then
                install_deb "$version" || install_binary "$platform" "$version"
            elif command -v rpm >/dev/null 2>&1; then
                install_rpm "$version" || install_binary "$platform" "$version"
            else
                install_binary "$platform" "$version"
            fi
            ;;
        windows)
            install_binary "$platform" "$version"
            ;;
    esac

    echo ""
    ok "Installation complete!"
    echo ""
    info "Quick start:"
    echo "  ${BINARY_NAME} probe          # Check available isolation tiers"
    echo "  ${BINARY_NAME} serve          # Start the API server"
    echo "  ${BINARY_NAME} --help         # Show all commands"
}

main "$@"
