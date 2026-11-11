import type { AdapterEnvironmentTestContext, AdapterEnvironmentTestResult } from "@paperclipai/adapter-utils";
import { runHerdr, isValidPane } from "./herdr-client.js";

export async function testEnvironment(ctx: AdapterEnvironmentTestContext): Promise<AdapterEnvironmentTestResult> {
  const checks: { level: "info" | "warn" | "error"; message: string; hint?: string; code: string }[] = [];
  const c = ctx.config as Record<string, unknown>;
  const alias = ((c.hosts ?? {}) as Record<string, string>)[String(c.host ?? "")];
  const pane = String(c.pane ?? "");
  const allowed = Array.isArray(c.allowedPanes) ? c.allowedPanes.map(String) : [];
  if (!alias) checks.push({ level: "error", message: "host not in hosts map", code: "bad_host" });
  if (!isValidPane(pane)) checks.push({ level: "error", message: "pane id invalid", code: "bad_pane" });
  else if (!allowed.includes(pane)) checks.push({ level: "error", message: "pane not in allowedPanes", code: "scope" });
  if (alias && isValidPane(pane)) {
    const t0 = Date.now();
    const r = await runHerdr(alias, { sub: "pane read", pane, extra: ["--source", "recent", "--lines", "1"], timeoutMs: 15_000 });
    if (r.code === 0) checks.push({ level: "info", message: `ssh+herdr ok, pane readable (${Date.now() - t0} ms)`, code: "ok" });
    else {
      const denied = /Access is denied|os error 5/i.test(r.stderr);
      checks.push({ level: "error", message: `herdr not reachable: ${r.stderr.slice(0, 160)}`,
        hint: denied ? "Integrity-level mismatch: SSH session must match the live herdr server (High vs Medium)" : undefined, code: "herdr_unreachable" });
    }
  }
  return { adapterType: ctx.adapterType, status: checks.some((x) => x.level === "error") ? "fail" : "pass", checks, testedAt: new Date().toISOString() } as AdapterEnvironmentTestResult;
}
