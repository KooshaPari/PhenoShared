/** @vitest-environment node */

import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { expect, it } from "vitest";
import { verifyCspConfig } from "./verify_csp.mjs";

const scriptsDirectory = path.dirname(fileURLToPath(import.meta.url));

it("keeps production CSP limited to Tauri assets and IPC", () => {
  const output = execFileSync(process.execPath, ["verify_csp.mjs"], {
    cwd: scriptsDirectory,
    encoding: "utf8",
  });

  expect(output).toContain("CSP verification passed");
});

it("rejects production development and wildcard CSP sources", () => {
  const config = JSON.parse(fs.readFileSync(
    path.join(scriptsDirectory, "../apps/desktop/src-tauri/tauri.conf.json"),
    "utf8",
  ));
  const sources = config.app.security.csp["connect-src"];
  sources.push("http://localhost:5173", "ws://localhost:5173", "wss://localhost:5173", "*");

  const errors = verifyCspConfig(config);

  expect(errors).toEqual(expect.arrayContaining([
    expect.stringContaining("http://localhost:5173"),
    expect.stringContaining("ws://localhost:5173"),
    expect.stringContaining("wss://localhost:5173"),
    expect.stringContaining("*"),
  ]));
});

it("rejects bracketed IPv6 loopback development origins in production CSP", () => {
  const config = JSON.parse(fs.readFileSync(
    path.join(scriptsDirectory, "../apps/desktop/src-tauri/tauri.conf.json"),
    "utf8",
  ));
  config.app.security.csp["connect-src"].push("http://[::1]:5173");

  expect(verifyCspConfig(config)).toEqual(expect.arrayContaining([
    expect.stringContaining("http://[::1]:5173"),
  ]));
});
