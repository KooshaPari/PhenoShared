/** @vitest-environment node */

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) => fs.readFileSync(path.join(repoRoot, relativePath), "utf8");
const bannedLinkedInSurfaces = [
  ["capture", "_linkedin_browser"].join(""),
  ["open", "_linkedin_signin"].join(""),
  ["import", "_linkedin_capture"].join(""),
  ["import", "_linkedin_html"].join(""),
  ["linkedin", ":capture"].join(""),
];

describe("consented provider boundary", () => {
  it("ships no invokable LinkedIn browser/profile capture surface", () => {
    const surfaces = [
      read("src/App.tsx"),
      read("apps/desktop/src-tauri/src/lib.rs"),
      read("apps/desktop/src-tauri/tauri.conf.json"),
      read("package.json"),
    ];

    for (const source of surfaces) {
      for (const banned of bannedLinkedInSurfaces) expect(source).not.toContain(banned);
    }
    expect(fs.existsSync(path.join(repoRoot, "scripts/linkedin_capture.mjs"))).toBe(false);
    expect(fs.existsSync(path.join(repoRoot, "scripts/linkedin_signin.mjs"))).toBe(false);
  });

  it("keeps the shipped shared browser helper provider-neutral", () => {
    const sharedBrowserHelper = read("scripts/_capture_common.mjs");

    expect(sharedBrowserHelper).not.toMatch(/linkedin/i);
  });

  it("keeps GitHub credentials behind the Rust import boundary", () => {
    const app = read("src/App.tsx");
    const backend = read("apps/desktop/src-tauri/src/lib.rs");

    expect(app).toContain("import_github_from_gh");
    expect(app).not.toContain(["github", "_token_from_gh"].join(""));
    expect(app).not.toContain("GitHub token");
    expect(backend).toContain("import_github_from_gh");
    expect(backend).not.toContain(["github", "_token_from_gh"].join(""));
    expect(backend).not.toContain(["github", "_device_poll"].join(""));
  });
});
