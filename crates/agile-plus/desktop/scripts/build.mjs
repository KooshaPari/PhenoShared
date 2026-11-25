#!/usr/bin/env node
/**
 * Build entrypoint for the AgilePlus desktop client.
 *
 * Step-1: this is a thin wrapper that just invokes `electrobun build`.
 * End-state native shells will have per-platform build scripts
 * (cargo for WinUI-rs, xcodebuild for SwiftUI, meson/cmake for
 * Linux-native). This file is intentionally simple.
 */

import { spawnSync } from "node:child_process";

const result = spawnSync("npx", ["electrobun", "build"], {
  stdio: "inherit",
  shell: process.platform === "win32",
});

process.exit(result.status ?? 1);
