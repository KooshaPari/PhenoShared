import { describe, it, expect } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import { resolve } from "node:path";

const root = resolve(__dirname, "..");

describe("projects-landing smoke", () => {
  it("main entry src/pages/index.astro exists", () => {
    expect(existsSync(resolve(root, "src/pages/index.astro"))).toBe(true);
  });

  it("repos.json data snapshot exists and is valid JSON array", () => {
    const data = JSON.parse(
      readFileSync(resolve(root, "data/repos.json"), "utf8"),
    );
    expect(Array.isArray(data)).toBe(true);
    if (data.length > 0) {
      expect(data[0]).toHaveProperty("name");
      expect(data[0]).toHaveProperty("url");
    }
  });
});
