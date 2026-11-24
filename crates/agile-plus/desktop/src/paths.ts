/**
 * Resolved filesystem locations for the desktop client. The repo root is
 * the selected spec-kit-style project — the directory containing
 * `kitty-specs/`, `docs/adr/`, `traces/`, etc.
 *
 * The app NEVER makes network calls. All paths point at local disk.
 */

import * as path from "node:path";
import * as os from "node:os";
import * as fs from "node:fs";

export interface AppPaths {
  /** Selected repo root, e.g. the AgilePlus checkout the user picked. */
  readonly repoRoot: string;
  /** `kitty-specs/<feature-id>/` — feature specs and acceptance. */
  readonly specsDir: string;
  /** `docs/adr/` — architecture decision records. */
  readonly adrDir: string;
  /** `traces/` — traceability worklogs and link tables. */
  readonly tracesDir: string;
  /** Local user data dir for the desktop app itself (cache, recent repos). */
  readonly userDataDir: string;
}

export const AppPaths = {
  /**
   * Resolve paths for a chosen repo root. The root is the only thing the
   * user selects; everything else is derived.
   */
  fromRepoRoot(repoRoot: string): AppPaths {
    const abs = path.resolve(repoRoot);
    if (!fs.existsSync(abs)) {
      throw new Error(`Repo root does not exist: ${abs}`);
    }
    const userDataDir = path.join(
      os.homedir(),
      ".agileplus",
      "desktop"
    );
    fs.mkdirSync(userDataDir, { recursive: true });
    return Object.freeze({
      repoRoot: abs,
      specsDir: path.join(abs, "kitty-specs"),
      adrDir: path.join(abs, "docs", "adr"),
      tracesDir: path.join(abs, "traces"),
      userDataDir,
    });
  },

  /** Default to the current working directory. */
  fromCwd(cwd: string): AppPaths {
    return AppPaths.fromRepoRoot(cwd);
  },
} as const;
