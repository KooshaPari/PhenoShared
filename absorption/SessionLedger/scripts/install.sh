#!/bin/sh
# SessionLedger installer (Linux / macOS)
#
# Downloads a checksum-verified sl-viewer archive from GitHub Releases and
# installs it to SL_INSTALL_DIR (default: ~/.local/bin).
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/KooshaPari/SessionLedger/main/scripts/install.sh | sh
#   SL_VERSION=v0.1.0 curl -fsSL ... | sh
#   sh scripts/install.sh [--help]
#
# Environment:
#   SL_REPO          GitHub owner/repo (default: KooshaPari/SessionLedger)
#   SL_VERSION       Release tag (default: latest). With or without leading v.
#   SL_INSTALL_DIR   Destination directory (default: ~/.local/bin)
#   SL_SKIP_VERIFY   Set to 1 only for emergency/debug (not recommended)

set -eu

REPO="${SL_REPO:-KooshaPari/SessionLedger}"
INSTALL_DIR="${SL_INSTALL_DIR:-$HOME/.local/bin}"
SKIP_VERIFY="${SL_SKIP_VERIFY:-0}"

usage() {
    cat <<'EOF'
SessionLedger install.sh — checksum-verified sl-viewer from GitHub Releases

Usage:
  curl -fsSL https://raw.githubusercontent.com/KooshaPari/SessionLedger/main/scripts/install.sh | sh
  SL_VERSION=v0.1.0 SL_INSTALL_DIR=$HOME/bin sh scripts/install.sh

Environment:
  SL_REPO          GitHub owner/repo (default: KooshaPari/SessionLedger)
  SL_VERSION       Release tag (default: latest)
  SL_INSTALL_DIR   Install directory (default: ~/.local/bin)

This script installs sl-viewer only. Install the daemon with:
  cargo install --git https://github.com/KooshaPari/SessionLedger --locked --path crates/sl-daemon
EOF
}

case "${1:-}" in
    -h|--help|help) usage; exit 0 ;;
esac

need_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "error: required command not found: $1" >&2
        exit 1
    fi
}

need_cmd curl
need_cmd tar
need_cmd awk
need_cmd uname
need_cmd mkdir

case "$(uname -s)" in
    Linux) os_name="Linux" ;;
    Darwin) os_name="Darwin" ;;
    *)
        echo "error: this installer supports Linux and macOS." >&2
        echo "On Windows, use:" >&2
        echo "  irm https://raw.githubusercontent.com/${REPO}/main/scripts/install.ps1 | iex" >&2
        exit 1
        ;;
esac

arch="$(uname -m)"
case "$os_name:$arch" in
    Linux:x86_64|Linux:amd64) os_target="x86_64-unknown-linux-gnu" ;;
    Darwin:arm64|Darwin:aarch64) os_target="aarch64-apple-darwin" ;;
    Darwin:x86_64) os_target="x86_64-apple-darwin" ;;
    *)
        echo "error: unsupported platform: $(uname -s) $(uname -m)" >&2
        exit 1
        ;;
esac

resolve_latest_tag() {
    # Prefer the GitHub API; fall back to the /releases/latest redirect.
    api_tag="$(
        curl -fsSL \
            -H "Accept: application/vnd.github+json" \
            -H "X-GitHub-Api-Version: 2022-11-28" \
            "https://api.github.com/repos/${REPO}/releases/latest" 2>/dev/null \
            | awk -F'"' '/"tag_name"[[:space:]]*:/ { print $4; exit }'
    )" || api_tag=""
    if [ -n "$api_tag" ]; then
        printf '%s\n' "$api_tag"
        return 0
    fi
    latest_url="$(curl -fsSL -o /dev/null -w '%{url_effective}' "https://github.com/${REPO}/releases/latest")"
    printf '%s\n' "${latest_url##*/}"
}

version="${SL_VERSION:-}"
if [ -z "$version" ]; then
    version="$(resolve_latest_tag)"
fi
case "$version" in
    v*) ;;
    *) version="v${version}" ;;
esac
if [ -z "$version" ] || [ "$version" = "v" ] || [ "$version" = "latest" ]; then
    echo "error: could not resolve a release tag for ${REPO}." >&2
    echo "Publish a v* GitHub Release or set SL_VERSION explicitly." >&2
    exit 1
fi

base_url="https://github.com/${REPO}/releases/download/${version}"
tmp_dir="$(mktemp -d "${TMPDIR:-/tmp}/sessionledger-install.XXXXXX")"
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT HUP INT TERM

# Resolve the archive name. Release archives historically used the tag verbatim
# (sl-viewer-v0.1.1-...) and later dropped the leading `v` (sl-viewer-0.1.1-...).
# Probe both spellings and use the first that exists so the installer works
# against every published release.
asset_version="${version#v}"
archive=""
for candidate in "sl-viewer-${version}-${os_target}.tar.gz" \
                "sl-viewer-${asset_version}-${os_target}.tar.gz"; do
    if curl -fsSL -I -o /dev/null "${base_url}/${candidate}" 2>/dev/null; then
        archive="$candidate"
        break
    fi
done
if [ -z "$archive" ]; then
    echo "error: no sl-viewer archive found for ${version} (${os_target})." >&2
    echo "Tried: sl-viewer-${version}-${os_target}.tar.gz, sl-viewer-${asset_version}-${os_target}.tar.gz" >&2
    exit 1
fi

echo "Installing SessionLedger sl-viewer ${version} (${os_target})"
echo "  archive: ${archive}"
echo "  dest:    ${INSTALL_DIR}/sl-viewer"

curl -fsSL "${base_url}/${archive}" -o "${tmp_dir}/${archive}"
curl -fsSL "${base_url}/SHA256SUMS" -o "${tmp_dir}/SHA256SUMS"

if [ "$SKIP_VERIFY" != "1" ]; then
    expected="$(awk -v file="$archive" '
        $2 == file || $2 == ("*" file) || $2 == ("./" file) { print $1; exit }
    ' "${tmp_dir}/SHA256SUMS")"
    if [ -z "$expected" ]; then
        echo "error: no checksum found for ${archive} in SHA256SUMS." >&2
        echo "Available entries:" >&2
        awk '{ print "  " $2 }' "${tmp_dir}/SHA256SUMS" >&2 || true
        exit 1
    fi

    if command -v sha256sum >/dev/null 2>&1; then
        actual="$(sha256sum "${tmp_dir}/${archive}" | awk '{ print $1 }')"
    elif command -v shasum >/dev/null 2>&1; then
        actual="$(shasum -a 256 "${tmp_dir}/${archive}" | awk '{ print $1 }')"
    else
        echo "error: need sha256sum or shasum to verify the download." >&2
        exit 1
    fi

    if [ "$actual" != "$expected" ]; then
        echo "error: checksum mismatch for ${archive}." >&2
        echo "  expected: ${expected}" >&2
        echo "  actual:   ${actual}" >&2
        exit 1
    fi
    echo "Checksum OK (${actual})"
else
    echo "warning: SL_SKIP_VERIFY=1 — skipping SHA-256 verification." >&2
fi

tar -xzf "${tmp_dir}/${archive}" -C "$tmp_dir"

bin_path=""
for candidate in \
    "${tmp_dir}/${archive%.tar.gz}/sl-viewer" \
    "${tmp_dir}/sl-viewer" \
    ; do
    if [ -f "$candidate" ]; then
        bin_path="$candidate"
        break
    fi
done
if [ -z "$bin_path" ]; then
    # Portable fallback without relying on find -print0 / xargs.
    for candidate in "${tmp_dir}"/*/sl-viewer "${tmp_dir}"/*/*/sl-viewer; do
        if [ -f "$candidate" ]; then
            bin_path="$candidate"
            break
        fi
    done
fi
if [ -z "$bin_path" ] || [ ! -f "$bin_path" ]; then
    echo "error: sl-viewer binary not found inside ${archive}." >&2
    exit 1
fi

mkdir -p "$INSTALL_DIR"
if command -v install >/dev/null 2>&1; then
    install -m 0755 "$bin_path" "${INSTALL_DIR}/sl-viewer"
else
    cp "$bin_path" "${INSTALL_DIR}/sl-viewer"
    chmod 0755 "${INSTALL_DIR}/sl-viewer"
fi

echo "Installed sl-viewer ${version} to ${INSTALL_DIR}/sl-viewer"
if "${INSTALL_DIR}/sl-viewer" --version >/dev/null 2>&1; then
    "${INSTALL_DIR}/sl-viewer" --version || true
fi

case ":${PATH}:" in
    *":${INSTALL_DIR}:"*) ;;
    *)
        echo
        echo "Add ${INSTALL_DIR} to PATH to run sl-viewer, for example:"
        echo "  export PATH=\"${INSTALL_DIR}:\$PATH\""
        ;;
esac

echo
echo "Daemon (optional, from source):"
echo "  cargo install --git https://github.com/${REPO} --locked --path crates/sl-daemon"
echo "Releases: https://github.com/${REPO}/releases"
