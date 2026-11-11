import { appendFileSync } from "node:fs";
import { createHash } from "node:crypto";
import type { AdapterExecutionContext, AdapterExecutionResult } from "@paperclipai/adapter-utils";
import { renderPaperclipWakePrompt } from "@paperclipai/adapter-utils/server-utils";
import { runHerdr, isValidPane } from "./herdr-client.js";
import { extractResult } from "./extract.js";

function fail(msg: string, code: string, clearSession = false): AdapterExecutionResult {
  return { exitCode: 1, signal: null, timedOut: false, errorMessage: msg, errorCode: code, clearSession } as AdapterExecutionResult;
}

export async function execute(ctx: AdapterExecutionContext): Promise<AdapterExecutionResult> {
  const { config, agent, context, onLog } = ctx;
  const host = String(config.host ?? "");
  const pane = String(config.pane ?? "");
  const harness = String(config.harness ?? "");
  const allowed = Array.isArray(config.allowedPanes) ? config.allowedPanes.map(String) : [];
  const hosts = (config.hosts ?? {}) as Record<string, string>; // adapter-level host -> ssh alias map
  const alias = hosts[host];
  const idleSec = Number(config.idleTimeoutSeconds ?? 600);
  const lines = Number(config.captureLines ?? 200);
  const audit = String(config.auditLog ?? "./herdr-session-audit.jsonl");

  if (!alias || !isValidPane(pane)) return fail("bad host/pane config", "bad_config");
  if (!allowed.includes(pane)) return fail(`pane ${pane} not in allowedPanes`, "scope_violation"); // rejected before send

  // wake prompt: pass through the helper, never the raw object
  const prompt = renderPaperclipWakePrompt((context as Record<string, unknown>).paperclipWake) || "Continue your work.";

  // preflight: pane exists
  const pre = await runHerdr(alias, { sub: "pane read", pane, extra: ["--source", "recent", "--lines", "1"], timeoutMs: 15_000 });
  if (pre.code !== 0) return fail(`pane unreachable: ${pre.stderr.slice(0, 200)}`, "pane_missing", true);

  appendFileSync(audit, JSON.stringify({ ts: new Date().toISOString(), runId: ctx.runId, role: agent.name, host, pane, harness,
    promptSha256: createHash("sha256").update(prompt).digest("hex") }) + "\n");

  const sent = await runHerdr(alias, { sub: "pane run", pane, extra: [prompt], timeoutMs: 15_000 });
  if (sent.code !== 0) return fail(`send failed: ${sent.stderr.slice(0, 200)}`, "send_failed");

  // wait for idle semantic state; pane is left running on timeout (his session)
  const waited = await runHerdr(alias, { sub: "agent wait", pane, extra: ["--until", "done"], timeoutMs: idleSec * 1000 });
  const read = await runHerdr(alias, { sub: "pane read", pane, extra: ["--source", "recent", "--lines", String(lines)], timeoutMs: 20_000 });
  const { text, method } = extractResult(read.stdout, prompt);
  onLog("stdout", text + "\n");

  return {
    exitCode: waited.timedOut ? null : 0, signal: null, timedOut: waited.timedOut,
    errorMessage: waited.timedOut ? "idle timeout; pane left running" : null,
    sessionParams: { host, pane, harness },
    sessionDisplayId: `${host}:${pane} (${harness})`,
    resultJson: { text, extracted: method },
  } as AdapterExecutionResult;
}
