import { describe, it, expect } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

// Smoke test: Astro pages are not directly importable from Vitest without the
// Astro Vite plugin runtime. Instead we assert the app's main entry exists and
// that the build-time data imports it depends on are present and well-formed.
// This guarantees `astro build` will not crash at the import boundary.

const root = resolve(__dirname, "..");

describe("agileplus-landing smoke", () => {
  it("main entry src/pages/index.astro exists", () => {
    expect(existsSync(resolve(root, "src/pages/index.astro"))).toBe(true);
  });

  it("repo snapshot is valid JSON with expected shape", () => {
    const repo = JSON.parse(
      readFileSync(resolve(root, "src/data/repo.json"), "utf8"),
    );
    expect(repo).toBeTypeOf("object");
    expect(repo.full_name).toBe("KooshaPari/AgilePlus");
    expect(typeof repo.description).toBe("string");
  });

  it("releases snapshot is a JSON array", () => {
    const releases = JSON.parse(
      readFileSync(resolve(root, "src/data/releases.json"), "utf8"),
    );
    expect(Array.isArray(releases)).toBe(true);
  });

  it("readme snapshot exists and is non-empty", () => {
    const html = readFileSync(resolve(root, "src/data/readme.html"), "utf8");
    expect(html.length).toBeGreaterThan(0);
  });

  it("astro config imports cleanly", async () => {
    const mod = await import(resolve(root, "astro.config.mjs"));
    expect(mod.default).toBeDefined();
  });
});
