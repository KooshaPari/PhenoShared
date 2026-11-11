import type { AdapterSessionCodec } from "@paperclipai/adapter-utils";
import { isValidPane } from "./herdr-client.js";

const HARNESS = new Set(["jcode", "codex", "forgecode"]);

export const sessionCodec: AdapterSessionCodec = {
  deserialize(raw) {
    if (typeof raw !== "object" || raw === null) return null;
    const r = raw as Record<string, unknown>;
    if (typeof r.host !== "string" || typeof r.pane !== "string" || typeof r.harness !== "string") return null;
    if (!isValidPane(r.pane) || !HARNESS.has(r.harness)) return null;
    return { host: r.host, pane: r.pane, harness: r.harness };
  },
  serialize(params) {
    return params ? { host: String(params.host), pane: String(params.pane), harness: String(params.harness) } : null;
  },
  getDisplayId(params) {
    return params ? `${params.host}:${params.pane} (${params.harness})` : null;
  },
};
