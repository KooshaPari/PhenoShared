#!/usr/bin/env node
/**
 * Prepare an electron-builder staging directory from an existing electrobun
 * build output. The electrobun build emits:
 *   build/dev-<platform>-<arch>/<AppName>-dev/
 *     ├── bin/<launcher>      (native launcher binary)
 *     ├── Info.plist
 *     ├── lib/                (CEF / runtime libs)
 *     └── Resources/
 *         └── app/            (Bun-side code, scripts, views, assets)
 *
 * electron-builder expects a directory layout where the *root* is what the OS
 * installer wraps. For a Windows NSIS target, that root is the dir containing
 * the .exe + Resources. We stage a known layout so electron-builder can wrap it.
 */
import { existsSync, mkdirSync, cpSync, rmSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { platform, arch } from "node:process";

const projectRoot = resolve(import.meta.dirname, "..");
const buildDir = join(projectRoot, "build");
const stageDir = join(projectRoot, "stage");

const plat = platform === "win32" ? "win" : platform === "darwin" ? "mac" : "linux";
const archName = arch === "x64" ? "x64" : arch === "arm64" ? "arm64" : arch;
const subdir = `dev-${plat}-${archName}`;

const srcDir = join(buildDir, subdir);
if (!existsSync(srcDir)) {
  console.error(`[prepare-bundle] electrobun build output not found at ${srcDir}.`);
  console.error(`[prepare-bundle] Run \`bun run build\` first.`);
  process.exit(1);
}

const candidates = readdirSync(srcDir).filter((n) => n.endsWith("-dev"));
if (candidates.length === 0) {
  console.error(`[prepare-bundle] no *-dev artifact dir under ${srcDir}.`);
  process.exit(1);
}
const appDir = join(srcDir, candidates[0]);

// Wipe and recreate stage dir.
if (existsSync(stageDir)) rmSync(stageDir, { recursive: true, force: true });
mkdirSync(stageDir, { recursive: true });

// Copy the entire electrobun build artifact (binary + Resources + libs + plist).
cpSync(appDir, stageDir, { recursive: true });

// electron-builder on Windows expects the launcher binary named after productName.
// It uses package.json `name` to look up <staging>/<productName>.exe. Our
// launcher is literally `launcher.exe`, so we also stage a renamed copy.
const productName = "AgilePlus";
const launcherSrc = join(stageDir, "bin", "launcher.exe");
if (existsSync(launcherSrc)) {
  cpSync(launcherSrc, join(stageDir, `${productName}.exe`));
}

console.log(`[prepare-bundle] staged ${appDir} -> ${stageDir}`);
