/**
 * Spawns the local `agileplus` CLI for project management state
 * transitions (specify, status, wp advance, etc.). The CLI is the
 * canonical state machine; the desktop client is a thin wrapper.
 *
 * No network. The CLI runs against the same local repo the bridge
 * reads from.
 */

import { spawn } from "node:child_process";
import type { AppPaths } from "./paths";

export interface CliResult {
  code: number;
  stdout: string;
  stderr: string;
}

export class CLI {
  constructor(
    private readonly paths: AppPaths,
    /** Override the binary path; defaults to `agileplus` on PATH. */
    private readonly bin: string = "agileplus",
  ) {}

  /** Run `agileplus <args>` in the selected repo root. */
  run(args: readonly string[]): Promise<CliResult> {
    return new Promise((resolve, reject) => {
      const child = spawn(this.bin, [...args], {
        cwd: this.paths.repoRoot,
        env: process.env,
        stdio: ["ignore", "pipe", "pipe"],
      });
      let stdout = "";
      let stderr = "";
      child.stdout.on("data", (b: Buffer) => (stdout += b.toString()));
      child.stderr.on("data", (b: Buffer) => (stderr += b.toString()));
      child.on("error", reject);
      child.on("close", (code) => resolve({ code: code ?? -1, stdout, stderr }));
    });
  }

  /** `agileplus status <feature-id> --wp <wp-id> --state <state>` */
  advanceWp(featureId: string, wpId: string, state: string): Promise<CliResult> {
    return this.run(["status", featureId, "--wp", wpId, "--state", state]);
  }
}
