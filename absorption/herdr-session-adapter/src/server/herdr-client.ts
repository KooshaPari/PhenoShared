import { spawn } from "node:child_process";

// Fixed allowlist of herdr subcommands. No free shell passthrough.
// Source for these commands: https://herdr.dev/docs/socket-api/ (pane run, pane read, agent wait).
const ALLOWED = new Set(["pane run", "pane read", "agent wait"]);
const PANE_RE = /^[A-Za-z0-9_:-]{1,32}$/;

export function isValidPane(p: string): boolean {
  return PANE_RE.test(p);
}

function shq(s: string): string {
  return `'${s.replaceAll("'", `'\\''`)}'`; // POSIX shells (mac zsh). Windows desk shell NOT supported in v1.
}

export interface HerdrCall { sub: "pane run" | "pane read" | "agent wait"; pane: string; extra: string[]; timeoutMs: number }

export function runHerdr(sshAlias: string, call: HerdrCall): Promise<{ code: number | null; stdout: string; stderr: string; timedOut: boolean }> {
  if (!ALLOWED.has(call.sub)) throw new Error("herdr subcommand not allowed");
  if (!isValidPane(call.pane)) throw new Error("invalid pane id");
  const remote = ["herdr", ...call.sub.split(" "), shq(call.pane), ...call.extra.map(shq)].join(" ");
  return new Promise((resolve) => {
    const p = spawn("ssh", ["-o", "BatchMode=yes", "-o", "ConnectTimeout=10", sshAlias, remote], { stdio: ["ignore", "pipe", "pipe"] });
    let stdout = "", stderr = "", timedOut = false;
    const t = setTimeout(() => { timedOut = true; p.kill("SIGTERM"); setTimeout(() => p.kill("SIGKILL"), 5000); }, call.timeoutMs);
    p.stdout.on("data", (d) => (stdout += d));
    p.stderr.on("data", (d) => (stderr += d));
    p.on("close", (code) => { clearTimeout(t); resolve({ code, stdout, stderr, timedOut }); });
    p.on("error", (e) => { clearTimeout(t); resolve({ code: null, stdout, stderr: String(e), timedOut }); });
  });
}
