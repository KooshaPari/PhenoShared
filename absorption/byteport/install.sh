#!/usr/bin/env bash
# install.sh — One-liner installer for BytePort
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/KooshaPari/BytePort/main/install.sh | sh
#
# Supports: macOS (arm64/x86_64), Linux (amd64/arm64), Windows (via Git Bash/WSL)

set -euo pipefail

# ── Config ───────────────────────────────────────────────────
GITHUB_REPO="KooshaPari/BytePort"
BINARY_NAME="byteport-cli"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"
LATEST_VERSION="v1.0.3"

# curl hardening: HTTPS-only for request and redirect protocols (shared constant).
CURL_HTTPS_ONLY=(--proto '=https' --proto-redir '=https')

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
    if [[ -n "$LATEST_VERSION" ]]; then
        echo "$LATEST_VERSION"
        return
    fi

    local version
    version=$(curl -fsSL "${CURL_HTTPS_ONLY[@]}" "https://api.github.com/repos/${GITHUB_REPO}/releases/latest" \
        | grep '"tag_name"' | sed -E 's/.*"tag_name": *"([^"]+)".*/\1/')

    if [[ -z "$version" ]]; then
        err "Failed to detect latest version"
        exit 1
    fi

    echo "$version"
}

# ── Main install ─────────────────────────────────────────────
main() {
    info "BytePort installer"
    echo ""

    local platform version
    platform=$(detect_platform)
    version=$(get_latest_version)

    info "Platform: ${platform}"
    info "Version:  ${version}"
    echo ""

    # Check if this is a Tauri desktop app release
    local os_type
    os_type=$(echo "$platform" | cut -d_ -f1)

    case "$os_type" in
        darwin)
            info "macOS detected — downloading .dmg installer..."
            local dmg_url="https://github.com/${GITHUB_REPO}/releases/download/${version}/BytePort_${version}_aarch64.dmg"
            local dmg_file="/tmp/byteport-${version}.dmg"

            curl -fSL "${CURL_HTTPS_ONLY[@]}" "$dmg_url" -o "$dmg_file" || {
                # Fallback to tar.gz binary
                warn ".dmg not found, installing CLI binary instead..."
                install_binary "$platform" "$version"
                return
            }

            info "Mounting .dmg..."
            local mount_point
            mount_point=$(hdiutil attach "$dmg_file" -nobrowse | grep "/Volumes" | awk '{print $NF}')

            info "Installing to /Applications..."
            cp -R "${mount_point}/BytePort.app" /Applications/
            hdiutil detach "$mount_point" -quiet
            rm -f "$dmg_file"

            ok "BytePort.app installed to /Applications/"
            info "Run: open /Applications/BytePort.app"
            ;;

        linux)
            info "Linux detected — checking for .deb package..."
            local deb_url="https://github.com/${GITHUB_REPO}/releases/download/${version}/BytePort_${version}_amd64.deb"

            if curl -fsSL "${CURL_HTTPS_ONLY[@]}" --head "$deb_url" >/dev/null 2>&1; then
                local deb_file="/tmp/byteport-${version}.deb"
                curl -fSL "${CURL_HTTPS_ONLY[@]}" "$deb_url" -o "$deb_file"
                sudo dpkg -i "$deb_file" || sudo apt-get install -f -y
                rm -f "$deb_file"
                ok "BytePort installed via .deb"
            else
                install_binary "$platform" "$version"
            fi
            ;;

        windows)
            info "Windows detected — downloading .msi installer..."
            local msi_url="https://github.com/${GITHUB_REPO}/releases/download/${version}/BytePort_${version}_x64-setup.msi"
            local msi_file="/tmp/byteport-${version}.msi"

            curl -fSL "${CURL_HTTPS_ONLY[@]}" "$msi_url" -o "$msi_file" || {
                warn ".msi not found, installing CLI binary instead..."
                install_binary "$platform" "$version"
                return
            }

            info "Running installer..."
            msiexec //i "$msi_file" //quiet //norestart
            rm -f "$msi_file"
            ok "BytePort installed via .msi"
            ;;
        *)
            warn "Unexpected platform '$os_type'; falling back to CLI binary..."
            install_binary "$platform" "$version"
            return
            ;;
    esac
}

# ── Binary fallback ──────────────────────────────────────────
install_binary() {
    local platform="$1" version="$2"
    local os arch ext

    os=$(echo "$platform" | cut -d_ -f1)
    arch=$(echo "$platform" | cut -d_ -f2)

    case "$os" in
        windows) ext=".exe" ;;
        *)       ext="" ;;
    esac

    local archive_url="https://github.com/${GITHUB_REPO}/releases/download/${version}/${BINARY_NAME}_${version#v}_${os}_${arch}.tar.gz"
    local tmp_dir
    tmp_dir=$(mktemp -d)

    info "Downloading binary..."
    curl -fSL "${CURL_HTTPS_ONLY[@]}" "$archive_url" | tar xz -C "$tmp_dir"

    mkdir -p "$INSTALL_DIR"
    mv "${tmp_dir}/${BINARY_NAME}${ext}" "${INSTALL_DIR}/${BINARY_NAME}${ext}"
    chmod +x "${INSTALL_DIR}/${BINARY_NAME}${ext}"
    rm -rf "$tmp_dir"

    ok "Installed ${BINARY_NAME} to ${INSTALL_DIR}/"

    # PATH hint
    case ":$PATH:" in
        *":${INSTALL_DIR}:"*) ;;
        *) warn "Add ${INSTALL_DIR} to your PATH:" ;;
    esac
    echo "  export PATH=\"${INSTALL_DIR}:\$PATH\""
}

main "$@"
