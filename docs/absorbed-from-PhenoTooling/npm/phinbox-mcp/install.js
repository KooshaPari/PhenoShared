#!/usr/bin/env node

/**
 * postinstall for @kooshapari/phinbox-mcp
 *
 * Tries the platform-specific optionalDependency first.
 * Falls back to downloading from GitHub Releases.
 */

const fs = require("fs");
const path = require("path");
const { execSync } = require("child_process");

const BIN_DIR = path.join(__dirname, "bin");
const PLATFORMS = {
  "darwin-arm64": { pkg: "@kooshapari/phinbox-mcp-darwin-arm64", target: "aarch64-apple-darwin" },
  "darwin-x64": { pkg: "@kooshapari/phinbox-mcp-darwin-x64", target: "x86_64-apple-darwin" },
  "linux-x64": { pkg: "@kooshapari/phinbox-mcp-linux-x64", target: "x86_64-unknown-linux-gnu" },
  "linux-arm64": { pkg: "@kooshapari/phinbox-mcp-linux-arm64", target: "aarch64-unknown-linux-gnu" },
  "win32-x64": { pkg: "@kooshapari/phinbox-mcp-win32-x64", target: "x86_64-pc-windows-msvc" },
};

function getPlatformKey() { return `${process.platform}-${process.arch}`; }
function getBinExt() { return process.platform === "win32" ? ".exe" : ""; }

async function tryPlatformPackage() {
  const key = getPlatformKey();
  const config = PLATFORMS[key];
  if (!config) return false;

  try {
    const pkgDir = require.resolve(config.pkg);
    const srcDir = path.dirname(pkgDir);
    fs.mkdirSync(BIN_DIR, { recursive: true });
    for (const name of ["phinbox", "phinbox-mcp"]) {
      const ext = getBinExt();
      const src = path.join(srcDir, `${name}${ext}`);
      const dest = path.join(BIN_DIR, `${name}${ext}`);
      if (fs.existsSync(src)) { fs.copyFileSync(src, dest); fs.chmodSync(dest, 0o755); }
    }
    return true;
  } catch { return false; }
}

async function downloadFromGitHub() {
  const key = getPlatformKey();
  const config = PLATFORMS[key];
  if (!config) {
    console.error(`[phinbox-mcp] unsupported platform: ${key}`);
    console.error("[phinbox-mcp] install manually: https://github.com/Kooshapari/phenotype-tooling/releases");
    process.exit(0);
  }

  const pkg = require(path.join(__dirname, "package.json"));
  const version = pkg.version;
  const tag = `phinbox-v${version}`;
  const isWin = process.platform === "win32";
  const ext = isWin ? "zip" : "tar.gz";
  const archive = `phinbox-${version}-${config.target}.${ext}`;
  const url = `https://github.com/Kooshapari/phenotype-tooling/releases/download/${tag}/${archive}`;

  console.log(`[phinbox-mcp] downloading ${archive} ...`);
  fs.mkdirSync(BIN_DIR, { recursive: true });

  const tmpDir = path.join(__dirname, ".tmp-install");
  fs.mkdirSync(tmpDir, { recursive: true });

  try {
    execSync(`curl -fSL --progress-bar "${url}" -o "${path.join(tmpDir, archive)}"`, { stdio: "inherit" });
    if (isWin) {
      execSync(`powershell -Command "Expand-Archive -Path '${path.join(tmpDir, archive)}' -DestinationPath '${BIN_DIR}' -Force"`, { stdio: "inherit" });
    } else {
      execSync(`tar -xzf "${path.join(tmpDir, archive)}" -C "${BIN_DIR}"`, { stdio: "inherit" });
    }
    for (const name of ["phinbox", "phinbox-mcp"]) {
      const p = path.join(BIN_DIR, name);
      if (fs.existsSync(p)) fs.chmodSync(p, 0o755);
    }
  } catch (err) {
    console.error(`[phinbox-mcp] download failed: ${err.message}`);
    console.error("[phinbox-mcp] install from https://github.com/Kooshapari/phenotype-tooling/releases");
  } finally {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  }
}

async function main() {
  fs.mkdirSync(BIN_DIR, { recursive: true });
  const found = await tryPlatformPackage();
  if (!found) await downloadFromGitHub();
  console.log("[phinbox-mcp] done. Run 'phinbox --help' or 'phinbox-mcp --help'.");
}

main().catch(() => process.exit(0));
