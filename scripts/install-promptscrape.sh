#!/usr/bin/env sh
# promptscrape installer.
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/KooshaPari/PhenoShared/main/scripts/install-promptscrape.sh | sh
#   curl -fsSL .../install-promptscrape.sh | sh -s -- --version promptscrape-v0.2.0
#   curl -fsSL .../install-promptscrape.sh | sh -s -- --dir /usr/local/bin
set -eu

REPO="KooshaPari/PhenoShared"
BINARY="promptscrape"
INSTALL_DIR="${INSTALL_DIR:-${HOME}/.local/bin}"
VERSION="latest"

die() {
  echo "error: $*" >&2
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --version)
      VERSION="${2:?--version needs a value}"
      shift 2
      ;;
    --version=*)
      VERSION="${1#*=}"
      shift
      ;;
    --dir)
      INSTALL_DIR="${2:?--dir needs a value}"
      shift 2
      ;;
    --dir=*)
      INSTALL_DIR="${1#*=}"
      shift
      ;;
    -h|--help)
      echo "Usage: install-promptscrape.sh [--version <tag>] [--dir <path>]"
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

command -v curl >/dev/null 2>&1 || die "curl is required"
command -v uname >/dev/null 2>&1 || die "uname is required"

OS="$(uname -s | tr '[:upper:]' '[:lower:]')"
case "$OS" in
  darwin) OS="darwin" ;;
  linux) OS="linux" ;;
  *) die "unsupported OS: $OS (only macOS and Linux are supported)" ;;
esac

ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64) ARCH="amd64" ;;
  arm64|aarch64) ARCH="arm64" ;;
  *) die "unsupported architecture: $ARCH" ;;
esac

ASSET="${BINARY}-${OS}-${ARCH}"
if [ "$VERSION" = "latest" ]; then
  URL="https://github.com/${REPO}/releases/latest/download/${ASSET}"
else
  URL="https://github.com/${REPO}/releases/download/${VERSION}/${ASSET}"
fi

mkdir -p "$INSTALL_DIR"

TMP="$(mktemp "${TMPDIR:-/tmp}/${BINARY}.XXXXXX")"
cleanup() {
  rm -f "$TMP"
}
trap cleanup EXIT INT TERM

echo "Downloading ${BINARY} for ${OS}/${ARCH}..."
if ! curl -fsSL "$URL" -o "$TMP"; then
  die "download failed: $URL
If no release exists yet, build from source:
  git clone https://github.com/${REPO}.git
  cd PhenoShared/cmd/promptscrape && go build -o ${BINARY} . && ./${BINARY} install"
fi

chmod +x "$TMP"
mv "$TMP" "${INSTALL_DIR}/${BINARY}"
trap - EXIT INT TERM

echo "Installed ${INSTALL_DIR}/${BINARY}"
"${INSTALL_DIR}/${BINARY}" version

case ":${PATH}:" in
  *":${INSTALL_DIR}:"*) ;;
  *)
    echo ""
    echo "Note: ${INSTALL_DIR} is not on your PATH. Add it with:"
    echo "  export PATH=\"${INSTALL_DIR}:\$PATH\""
    ;;
esac

echo ""
echo "Usage:"
echo "  ${BINARY} scrape                       # current session"
echo "  ${BINARY} scrape <walkthrough.html>    # session embedded in a state HTML"
echo "  ${BINARY} scrape --format json         # machine-readable output"
