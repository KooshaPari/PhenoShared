export const type = "herdr_session";
export const label = "herdr pane session";
export const models = [
  { id: "jcode", label: "jcode pane" },
  { id: "codex", label: "Codex pane" },
  { id: "forgecode", label: "ForgeCode pane" },
];
export const agentConfigurationDoc = `# herdr_session configuration
Use when: a role maps to an already-running agent harness (jcode, codex, forgecode) in a herdr pane. Paperclip never launches or kills the harness.
Don't use when: you need Paperclip to spawn the process (use a *_local adapter) or an HTTP agent.
Config: host ("mac"|"desk", key into adapter hosts map), pane (herdr pane id like "w1:p2"), harness ("jcode"|"codex"|"forgecode"),
allowedPanes (string[], REQUIRED; pane must be listed), idleTimeoutSeconds (default 600), captureLines (default 200),
auditLog (path, default ./herdr-session-audit.jsonl). Transport is ssh to the host alias; no passthrough, only: pane run, pane read, agent wait.
No secrets in config. Result text is a heuristic scrape of the pane tail and is marked "extracted: heuristic".
`;
export { createServerAdapter } from "./server/index.js";
