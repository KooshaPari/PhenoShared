# Multi-Region Deployment — heliosCLI

> **Status:** Living document.
> **Owner:** heliosCLI distribution team.
> **Last reviewed:** 2026-08-20.

---

## Overview

heliosCLI is a **Rust-based CLI** distributed as a compiled binary across multiple platforms (macOS, Linux, Windows via WSL2) and package managers. Unlike a hosted service, the "multi-region deployment" challenge for heliosCLI centers on **distribution strategy** — ensuring fast, reliable, and globally accessible binary downloads, package registry availability, and localized documentation. This document covers the multi-platform distribution architecture, mirror/CDN strategy, npm registry mirrors, and documentation localization deployment.

---

## 1. Multi-Platform Distribution Strategy

### 1.1 Distribution Channels

| Channel | Platform | Update Mechanism | Priority |
|---------|----------|-----------------|----------|
| **GitHub Releases** | All platforms | Manual / CI-triggered | Primary |
| **crates.io** | All platforms (Rust source) | `cargo install helios-cli` | Primary |
| **Homebrew** | macOS + Linux | `brew install helios-cli` | High |
| **APT repository** | Debian/Ubuntu | `apt update && apt install helios-cli` | High |
| **npm** | All platforms (JS wrapper) | `npm install -g @helios/cli` | Medium |
| **DotSlash** | All platforms | Inline in repo | Medium |
| **Scoop** | Windows | `scoop install helios-cli` | Medium |
| **AUR** | Arch Linux | `yay -S helios-cli` | Low |

### 1.2 Binary Build Matrix

CI produces platform-specific binaries for every release:

| Target Triple | OS | ABI | Binary Name |
|--------------|-----|-----|-------------|
| `x86_64-unknown-linux-gnu` | Linux | glibc | `helios-cli-linux-amd64` |
| `x86_64-unknown-linux-musl` | Linux | musl | `helios-cli-linux-amd64-musl` |
| `aarch64-unknown-linux-gnu` | Linux ARM | glibc | `helios-cli-linux-arm64` |
| `x86_64-apple-darwin` | macOS Intel | — | `helios-cli-darwin-amd64` |
| `aarch64-apple-darwin` | macOS Apple Silicon | — | `helios-cli-darwin-arm64` |
| `x86_64-pc-windows-msvc` | Windows | MSVC | `helios-cli-windows-amd64.exe` |
| `x86_64-unknown-linux-gnu` | WSL2 | glibc | `helios-cli-wsl-amd64` |

### 1.3 Release Artifact Layout

```
releases/
└── v1.2.3/
    ├── manifest.json              # SHA-256 checksums + SLSA provenance
    ├── helios-cli-linux-amd64
    ├── helios-cli-linux-amd64.sha256
    ├── helios-cli-linux-amd64-musl
    ├── helios-cli-linux-amd64-musl.sha256
    ├── helios-cli-linux-arm64
    ├── helios-cli-linux-arm64.sha256
    ├── helios-cli-darwin-amd64
    ├── helios-cli-darwin-amd64.sha256
    ├── helios-cli-darwin-arm64
    ├── helios-cli-darwin-arm64.sha256
    ├── helios-cli-windows-amd64.exe
    ├── helios-cli-windows-amd64.exe.sha256
    ├── helios.wasm                  # Optional WASM extension
    └── codex                        # DotSlash file
```

---

## 2. Mirror/CDN for Binary Downloads

### 2.1 CDN Architecture

Binary downloads are served through a multi-layer CDN to ensure low latency globally:

```
┌─────────────┐     DNS (GeoIP routing)     ┌──────────────────┐
│  User/CI     │ ──────────────────────────> │  Nearest CDN PoP │
│  (download)  │ <── Binary response ──────── │  (Cloudflare)    │
└─────────────┘                              └──────────────────┘
                                                       │
                                              Origin pull (on miss)
                                                       │
                                              ┌──────────────────┐
                                              │  GitHub Releases  │
                                              │  (origin)         │
                                              └──────────────────┘
```

### 2.2 CDN Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| **CDN provider** | Cloudflare | Global anycast, 300+ PoPs |
| **Cache TTL (binaries)** | 7 days | Binaries are immutable once published |
| **Cache TTL (manifest)** | 5 minutes | Manifest must reflect latest checksums |
| **Stale-while-revalidate** | 24 hours | Serve stale binary while checking for updates |
| **Range requests** | Enabled | Support partial downloads for resume |
| **Brotli compression** | Enabled for text assets | Binary assets served uncompressed (already small) |

### 2.3 Mirror Endpoints

| Mirror | URL | Region | Fallback |
|--------|-----|--------|----------|
| **Primary** | `https://releases.helios-cli.dev` | Global (CDN) | GitHub Releases |
| **GitHub** | `https://github.com/KooshaPari/heliosCLI/releases` | US | — |
| **Gitee** | `https://gitee.com/kooshapari/helios-cli/releases` | China | GitHub |
| **Academic** | `https://mirror.example.edu/helios-cli` | Various | Primary |

### 2.4 Download Resilience

The install script (`install.sh` / `install.ps1`) implements **multi-source fallback**:

1. Try the primary CDN endpoint.
2. If unreachable (timeout 10 s), try GitHub Releases directly.
3. If GitHub is unreachable, try the regional mirror (Gitee for China, academic mirrors for universities).
4. If all mirrors fail, print a manual download URL and exit with a descriptive error.

```bash
# Install script retry logic (simplified)
for mirror in "$PRIMARY_URL" "$GITHUB_URL" "$REGIONAL_MIRROR"; do
  if curl -fsSL --connect-timeout 10 "$mirror/$VERSION/$BINARY" -o "$OUTPUT"; then
    break
  fi
done
```

---

## 3. Regional npm Registry Mirrors

### 3.1 npm Distribution

heliosCLI is published to npm as `@helios/cli` for developers who prefer the JavaScript ecosystem for toolchain management.

| Registry | URL | Region | Sync Interval |
|----------|-----|--------|---------------|
| **npmjs.com** | `https://registry.npmjs.org/@helios/cli` | Global | — (origin) |
| **npmmirror (China)** | `https://registry.npmmirror.com/@helios/cli` | China | Every 10 min |
| **Verdaccio (self-hosted)** | `https://npm.helios-cli.dev` | US/EU | Every 5 min |

### 3.2 npm Mirror Strategy

- **npmmirror** is the recommended mirror for developers in China, where npmjs.com connectivity can be unreliable.
- The `@helios/cli` package wraps the native binary download — it detects the platform, downloads the appropriate binary from the CDN, and symlinks it into the npm bin directory.
- The package includes a **preinstall script** that validates the CDN endpoint before downloading. If the default CDN is unreachable, it falls back to the npm registry's own CDN.

### 3.3 Registry Failover Configuration

Users in restricted network environments can configure their `.npmrc`:

```ini
# Default (global)
@helios:registry=https://registry.npmjs.org/

# China (recommended for CN developers)
@helios:registry=https://registry.npmmirror.com/

# Corporate (behind firewall, use Verdaccio mirror)
@helios:registry=https://npm.internal.example.com/
```

---

## 4. Documentation Localization Deployment

### 4.1 Supported Locales

| Locale | Language | Status | Maintainers |
|--------|----------|--------|-------------|
| `en` | English | Active | Core team |
| `zh-CN` | Chinese (Simplified) | Active | Community |
| `zh-TW` | Chinese (Traditional) | Active | Community |
| `fa` | Persian (Farsi) | Active | Community |
| `fa-Latn` | Persian (Latin script) | Experimental | Community |
| `ja` | Japanese | Planned | — |
| `ko` | Korean | Planned | — |
| `pt-BR` | Portuguese (Brazil) | Planned | — |

### 4.2 Localization File Structure

Localized documentation lives in the `docs/` directory alongside the English source:

```
docs/
├── zh-CN/                   # Chinese (Simplified)
│   ├── README.md
│   ├── install.md
│   ├── getting-started.md
│   └── ...
├── zh-TW/                   # Chinese (Traditional)
│   ├── README.md
│   ├── install.md
│   └── ...
├── fa/                      # Persian (Arabic script)
│   ├── README.md
│   └── ...
├── fa-Latn/                 # Persian (Latin script)
│   ├── README.md
│   └── ...
└── (English source files at top level)
```

### 4.3 Documentation Build Pipeline

```
┌──────────────┐    Extract     ┌──────────────┐    Translate    ┌──────────────┐
│  English     │ ──────────────> │  i18n strings │ ──────────────> │  Translated  │
│  source docs │                │  (JSON/POT)   │                │  strings     │
└──────────────┘                └──────────────┘                └──────┬───────┘
                                                                      │
                                                             ┌────────▼────────┐
                                                             │  Build localized │
                                                             │  docs per locale │
                                                             └────────┬────────┘
                                                                      │
                                                    ┌─────────────────┼─────────────────┐
                                                    │                 │                 │
                                              ┌─────▼─────┐   ┌──────▼──────┐   ┌─────▼─────┐
                                              │  /en/      │   │  /zh-CN/   │   │  /fa/     │
                                              │  docs      │   │  docs      │   │  docs    │
                                              └─────┬─────┘   └──────┬──────┘   └─────┬─────┘
                                                    │                 │                 │
                                                    └─────────────────┼─────────────────┘
                                                                      │
                                                             ┌────────▼────────┐
                                                             │  Deploy to CDN  │
                                                             │  (per-locale    │
                                                             │   subdomains)   │
                                                             └─────────────────┘
```

### 4.4 Locale-Specific Deployment

| Locale | URL | CDN Config |
|--------|-----|------------|
| English | `https://docs.helios-cli.dev/` | Default (global) |
| Chinese (Simplified) | `https://docs.helios-cli.dev/zh-CN/` | npmmirror edge for CN |
| Chinese (Traditional) | `https://docs.helios-cli.dev/zh-TW/` | Default (global) |
| Persian | `https://docs.helios-cli.dev/fa/` | Default (global) |

### 4.5 Locale-Aware Redirect

The documentation site detects the user's browser `Accept-Language` header and redirects to the appropriate locale:

```
Accept-Language: zh-CN,zh;q=0.9 → Redirect to /zh-CN/
Accept-Language: fa,fa-IR;q=0.9 → Redirect to /fa/
Accept-Language: en-US,en;q=0.9 → Stay on / (English default)
```

This redirect is handled at the CDN edge (Cloudflare Workers) to avoid any server-side processing.

### 4.6 Translation Workflow

1. **Source updates** are committed to English docs in `docs/*.md`.
2. **CI bot** detects changes and creates translation tracking issues for each active locale.
3. **Community translators** submit PRs against locale-specific directories (e.g., `docs/zh-CN/install.md`).
4. **CI validates** that all translated files have the same heading structure as the English source (structural lint).
5. **On merge**, the docs build pipeline regenerates the localized site and deploys to CDN.

### 4.7 Translation Freshness

Each translated file carries a YAML front-matter header:

```yaml
---
locale: zh-CN
source: install.md
source_commit: abc1234
translated_commit: def5678
last_updated: 2026-08-15
staleness_threshold: 30 days
---
```

A weekly CI job checks all translated files against their source commit. If the source has changed more than `staleness_threshold` days ago and the translation has not been updated, the file is flagged with a "This translation may be outdated" banner.

---

## 5. Global Distribution Monitoring

### 5.1 Download Health Metrics

| Metric | Measurement | Alert Threshold |
|--------|-------------|-----------------|
| **Download success rate** | Per CDN PoP, 5-min window | < 99.5 % |
| **Download latency (p95)** | Per region, 5-min window | > 30 s for binary < 10 MB |
| **Mirror sync lag** | Per registry mirror, 10-min window | > 30 min |
| **Documentation availability** | Per locale, 1-min check | Any locale down > 5 min |

### 5.2 Synthetic Monitoring

A CI job runs every 6 hours that:

1. Downloads the latest release binary from each CDN endpoint (primary, GitHub, Gitee).
2. Verifies SHA-256 checksum matches the manifest.
3. Executes `helios-cli --version` on the downloaded binary.
4. Checks each documentation locale's homepage returns HTTP 200.
5. Publishes results to a health dashboard.

---

## 6. Future Considerations

- **Package manager signing:** Add GPG signatures for APT and Homebrew casks to prevent supply chain attacks.
- **Binary delta updates:** Implement delta/patch downloads (e.g., bsdiff) to reduce update download size from ~10 MB to ~500 KB.
- **Regional build mirrors:** For extremely latency-sensitive CI pipelines, offer self-hosted build mirrors that cache compiled dependencies per region.
- **Additional locales:** Expand to Japanese, Korean, and Portuguese (Brazil) based on community contribution.
- **Offline documentation:** Ship a `helios-cli docs offline` command that bundles all locales into a local browsable archive.

---

## Related Documents

- [Install Guide](install.md) — Platform-specific installation instructions.
- [SLA/SLO](SLA-SLO.md) — Service level targets.
- [Incident Response](incident-response.md) — Runbook for distribution incidents.
- [Contributing](contributing.md) — How to contribute translations and documentation.
- [Changelog](CHANGELOG.md) — Release history.
