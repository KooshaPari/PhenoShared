# Verification — Cosign-signed release artifacts

This directory contains release artifacts signed with [cosign](https://docs.sigstore.dev/cosign/).

## How to verify a release

```bash
# Download the public key
curl -sLO https://raw.githubusercontent.com/KooshaPari/pheno-harness/main/cosign.pub

# Download release artifacts
TAG="v0.40-pheno-harness-summit"
gh release -R KooshaPari/pheno-harness download "$TAG" \
    --pattern "pheno-harness-${TAG}.tar.gz" \
    --pattern "pheno-harness-${TAG}.tar.gz.sig" \
    --pattern "pheno-harness-${TAG}.tar.gz.cert"

# Verify SHA256 first
sha256sum -c pheno-harness-${TAG}.tar.gz.sha256

# Verify cosign signature (requires `cosign` binary)
cosign verify-blob \
    --key cosign.pub \
    --signature pheno-harness-${TAG}.tar.gz.sig \
    --certificate pheno-harness-${TAG}.tar.gz.cert \
    --insecure-ignore-tlog \
    pheno-harness-${TAG}.tar.gz
```

Expected output: `Verified OK`

## Key rotation

The current key is **local-test-2023-09-02** — a local cosign key pair generated for OpenSSF Scorecard
Signed-Releases check compliance. For production use, regenerate via:

```bash
cosign generate-key-pair --output-key-prefix cosign
# Set COSIGN_PASSWORD via env var or interactive prompt
# Replace the public key in this file
```

## Why local (not keyless)?

Cosign keyless mode requires browser OIDC authentication via Sigstore Fulcio.
Since this signing pipeline is automated via Tailscale + OpenSSH from a CI host
without an interactive browser, we use a local key pair instead. Both methods
satisfy the OpenSSF Scorecard Signed-Releases check (4-10 depending on tlog upload).

For full keyless + Rekor transparency log, run interactively:
```bash
COSIGN_PASSWORD="" cosign sign-blob \
    --output-signature pheno-harness-${TAG}.tar.gz.sig \
    --output-certificate pheno-harness-${TAG}.tar.gz.cert \
    pheno-harness-${TAG}.tar.gz
# Then visit the device URL printed in the terminal
```