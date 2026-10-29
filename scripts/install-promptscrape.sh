#!/usr/bin/env sh
set -e

# promptscrape installer
# Usage: curl -fsSL https://raw.githubusercontent.com/phenotype/phenoShared/main/scripts/install-promptscrape.sh | sh
# Or: curl -fsSL ... | sh -s -- --version v0.1.0

REPO="phenotype/phenoShared"
BINARY="promptscrape"
INSTALL_DIR="${INSTALL_DIR:-$HOME/.local/bin}"

# Parse args
VERSION="latest"
for arg in "$@"; do
  case $arg in
    --version=*) VERSION="${arg#*=}" ;;
    --dir=*) INSTALL_DIR="${arg#*=}" ;;
  esac
done

# Detect OS and arch
OS=$(uname -s | tr '[:upper:]' '[:lower:]')
ARCH=$(uname -m)
case "$ARCH" in
  x86_64) ARCH="amd64" ;;
  aarch64|arm64) ARCH="arm64" ;;
  *) echo "Unsupported arch: $ARCH"; exit 1 ;;
esac

case "$OS" in
  darwin) OS="darwin" ;;
  linux) OS="linux" ;;
  *) echo "Unsupported OS: $OS"; exit 1 ;;
esac

mkdir -p "$INSTALL_DIR"

if [ "$VERSION" = "latest" ]; then
  URL="https://github.com/${REPO}/releases/latest/download/${BINARY}-${OS}-${ARCH}"
else
  URL="https://github.com/${REPO}/releases/download/${VERSION}/${BINARY}-${OS}-${ARCH}"
fi

echo "Downloading ${BINARY} from ${URL}..."
curl -fsSL "$URL" -o "${INSTALL_DIR}/${BINARY}"
chmod +x "${INSTALL_DIR}/${BINARY}"

echo "Installed to ${INSTALL_DIR}/${BINARY}"
echo ""
echo "Make sure ${INSTALL_DIR} is in your PATH:"
echo "  export PATH=\"${INSTALL_DIR}:\$PATH\""
echo ""
echo "Usage:"
echo "  promptscrape scrape <html-file>"
echo "  promptscrape scrape --session <session-id>"
echo "  promptscrape scrape  # current session"
