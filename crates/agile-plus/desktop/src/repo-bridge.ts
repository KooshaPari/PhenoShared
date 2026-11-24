/**
 * Thin abstraction over the local repo. Reads and writes the spec-kit
 * style artifacts: specs under `kitty-specs/`, ADRs under `docs/adr/`,
 * traces under `traces/`, and acceptance files alongside each spec.
 *
 * This is the OFFLINE-FIRST boundary. No network, no remote storage, no
 * RPC — just the filesystem of the selected repo.
 */

import * as fs from "node:fs/promises";
import * as path from "node:path";
import type { AppPaths } from "./paths";

export interface SpecSummary {
  id: string;
  title: string;
  state: string;
  path: string;
}

export interface AdrSummary {
  id: string;
  title: string;
  status: string;
  path: string;
}

export interface TraceEntry {
  id: string;
  kind: string;
  path: string;
}

export class RepoBridge {
  constructor(private readonly paths: AppPaths) {}

  /** All spec feature directories under `kitty-specs/`. */
  async listSpecs(): Promise<SpecSummary[]> {
    return this.listDirs(this.paths.specsDir, (id, dir) => {
      const specFile = path.join(dir, "spec.md");
      return {
        id,
        title: id,
        state: "draft",
        path: specFile,
      };
    });
  }

  /** All ADRs under `docs/adr/`. */
  async listAdrs(): Promise<AdrSummary[]> {
    return this.listFiles(this.paths.adrDir, /\.md$/i, (file) => {
      const base = path.basename(file, ".md");
      return {
        id: base,
        title: base,
        status: "unknown",
        path: file,
      };
    });
  }

  /** All worklogs/trace files under `traces/`. */
  async listTraces(): Promise<TraceEntry[]> {
    return this.listFiles(this.paths.tracesDir, /\.jsonl?$|\.md$/i, (file) => {
      const base = path.basename(file);
      return {
        id: base,
        kind: base.endsWith(".jsonl") ? "jsonl" : "md",
        path: file,
      };
    });
  }

  /** Read a text file relative to the repo root. */
  async readText(relPath: string): Promise<string> {
    const abs = this.abs(relPath);
    return fs.readFile(abs, "utf8");
  }

  /** Write a text file relative to the repo root. */
  async writeText(relPath: string, body: string): Promise<void> {
    const abs = this.abs(relPath);
    await fs.mkdir(path.dirname(abs), { recursive: true });
    await fs.writeFile(abs, body, "utf8");
  }

  private abs(relPath: string): string {
    const abs = path.resolve(this.paths.repoRoot, relPath);
    if (!abs.startsWith(this.paths.repoRoot)) {
      throw new Error(`Path escapes repo root: ${relPath}`);
    }
    return abs;
  }

  private async listDirs(
    root: string,
    map: (id: string, dir: string) => SpecSummary,
  ): Promise<SpecSummary[]> {
    try {
      const entries = await fs.readdir(root, { withFileTypes: true });
      const out: SpecSummary[] = [];
      for (const e of entries) {
        if (!e.isDirectory()) continue;
        if (e.name.startsWith(".")) continue;
        out.push(map(e.name, path.join(root, e.name)));
      }
      return out.sort((a, b) => a.id.localeCompare(b.id));
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code === "ENOENT") return [];
      throw err;
    }
  }

  private async listFiles(
    root: string,
    re: RegExp,
    map: (file: string) => AdrSummary | TraceEntry,
  ): Promise<(AdrSummary | TraceEntry)[]> {
    try {
      const entries = await fs.readdir(root, { withFileTypes: true });
      const out: (AdrSummary | TraceEntry)[] = [];
      for (const e of entries) {
        if (!e.isFile()) continue;
        if (!re.test(e.name)) continue;
        out.push(map(path.join(root, e.name)));
      }
      return out.sort((a, b) => a.id.localeCompare(b.id));
    } catch (err) {
      if ((err as NodeJS.ErrnoException).code === "ENOENT") return [];
      throw err;
    }
  }
}
