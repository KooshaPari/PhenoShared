#!/usr/bin/env bash
# pheno release builder -- local CI replacement
# Builds all binaries, packages, generates SBOMs, and creates a GitHub release.
# Run from the pheno repo root: bash scripts/release.sh v0.2.0
set -euo pipefail

VERSION="${1:?Usage: $0 <version> (e.g., v0.2.0)}"
VERSION="${VERSION#v}"  # strip leading v for filenames

REPO="<REDACTED>/zz-pheno"
BINS=(agileplus phenoctl configra-ops pheno-agents-md)
TARGETS=(
  "x86_64-unknown-linux-gnu"
  "aarch64-unknown-linux-gnu"
  "x86_64-apple-darwin"
  "aarch64-apple-darwin"
)
RELEASE_DIR="release-assets"
HOST_TARGET=$(rustup show active-toolchain | head -1; rustc -vV | grep host | awk '{print $2}')

echo "=== pheno release builder ==="
echo "Version: ${VERSION}"
echo "Host target: ${HOST_TARGET}"
echo ""

# 1. Build for host target
echo "--- Building for ${HOST_TARGET} ---"
for bin in "${BINS[@]}"; do
  echo "  Building ${bin}..."
  cargo build --release --bin "${bin}" 2>&1 | tail -1
done

# 2. Package host target
echo "--- Packaging ${HOST_TARGET} ---"
STAGING="${RELEASE_DIR}/pheno-${VERSION}-${HOST_TARGET}"
mkdir -p "${STAGING}"
for bin in "${BINS[@]}"; do
  cp "target/release/${bin}" "${STAGING}/" 2>/dev/null || echo "  WARN: ${bin} not found"
done
echo "${VERSION}" > "${STAGING}/VERSION"
cp LICENSE "${STAGING}/" 2>/dev/null || true
cp README.md "${STAGING}/" 2>/dev/null || true
tar czf "${STAGING}.tar.gz" -C "${RELEASE_DIR}" "pheno-${VERSION}-${HOST_TARGET}"
echo "  Created ${STAGING}.tar.gz"

# 3. Generate SBOMs if tools available
echo "--- SBOMs ---"
mkdir -p "${RELEASE_DIR}/sbom"
if command -v cargo-cyclonedx &>/dev/null; then
  echo "  Generating CycloneDX..."
  cargo cyclonedx --format json --output-dir "${RELEASE_DIR}/sbom" 2>/dev/null || true
else
  echo "  SKIP: cargo-cyclonedx not installed"
fi
if command -v syft &>/dev/null; then
  echo "  Generating SPDX..."
  syft . -o "spdx-json=${RELEASE_DIR}/sbom/syft-spdx.json" \
    --exclude './target/**' --exclude './docs/**' --exclude './.git/**' 2>/dev/null || true
else
  echo "  SKIP: syft not installed"
fi

# 4. Generate install scripts
echo "--- Install scripts ---"
cat > "${RELEASE_DIR}/install.sh" << 'INSTALL_SH'
#!/usr/bin/env bash
set -euo pipefail
REPO="<REDACTED>/zz-pheno"
VERSION="${PHENO_VERSION:-latest}"
INSTALL_DIR="${PHENO_INSTALL_DIR:-$HOME/.pheno/bin}"
detect_platform() {
  os="$(uname -s)"; arch="$(uname -m)"
  case "$os" in Linux*) os="unknown-linux-gnu" ;; Darwin*) os="apple-darwin" ;; MINGW*|MSYS*) os="pc-windows-msvc" ;; *) echo "Unsupported: $os" >&2; exit 1 ;; esac
  case "$arch" in x86_64|amd64) arch="x86_64" ;; aarch64|arm64) arch="aarch64" ;; *) echo "Unsupported: $arch" >&2; exit 1 ;; esac
  echo "${arch}-${os}"
}
get_version() {
  [ "$VERSION" = "latest" ] && curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" | grep '"tag_name"' | head -1 | cut -d'"' -f4 || echo "v${VERSION}"
}
main() {
  target="$(detect_platform)"; version="$(get_version)"; version_num="${version#v}"
  echo "Installing pheno ${version} for ${target}..."
  tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
  curl -fsSL "https://github.com/${REPO}/releases/download/${version}/pheno-${version_num}-${target}.tar.gz" -o "$tmp/pheno.tar.gz"
  tar xzf "$tmp/pheno.tar.gz" -C "$tmp"
  mkdir -p "$INSTALL_DIR"
  cp "$tmp"/pheno-*/agileplus "$tmp"/pheno-*/phenoctl "$tmp"/pheno-*/configra-ops "$tmp"/pheno-*/pheno-agents-md "$INSTALL_DIR/" 2>/dev/null
  chmod +x "$INSTALL_DIR"/*
  echo "Installed to $INSTALL_DIR -- add to PATH: export PATH=\"\$HOME/.pheno/bin:\$PATH\""
}
main "$@"
INSTALL_SH
chmod +x "${RELEASE_DIR}/install.sh"
echo "  Created install.sh"

# 5. Show what's ready
echo ""
echo "=== Release assets ready ==="
ls -lh "${RELEASE_DIR}/"*.tar.gz "${RELEASE_DIR}/sbom/"* "${RELEASE_DIR}/install.sh" 2>/dev/null
echo ""
echo "To publish: gh release create v${VERSION} ${RELEASE_DIR}/pheno-${VERSION}-*.tar.gz ${RELEASE_DIR}/sbom/* ${RELEASE_DIR}/install.sh --title \"v${VERSION}\" --generate-notes"
