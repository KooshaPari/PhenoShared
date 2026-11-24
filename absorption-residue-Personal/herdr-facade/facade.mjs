#!/usr/bin/env node
// herdr-facade MVP. Authored by Instinct. Zero dependencies (Node 20+).
// Loopback-only HTTP API in front of the herdr CLI, meant to sit behind Tailscale Serve.
// Reads: any pane. Writes: only panes in workspaces whose label matches FACADE_WRITE_SCOPE.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { execFile } from "node:child_process";

const CFG = {
  host: "127.0.0.1", // never configurable: refuse anything else
  port: Number(process.env.FACADE_PORT || 8787),
  trustedUser: process.env.FACADE_TRUSTED_USER || "",
  herdr: process.env.FACADE_HERDR_BIN || "herdr",
  writeScope: new RegExp(process.env.FACADE_WRITE_SCOPE || "^instinct\\b", "i"),
  auditFile: process.env.FACADE_AUDIT_FILE || path.join(process.env.LOCALAPPDATA || process.env.HOME || ".", "herdr-facade", "audit.jsonl"),
  maxPanesPerSpace: 9, // 3x3 per-space limit; beyond that the caller should open a new space
  maxText: 4000,
  writesPerMinute: 30,
};
if (!CFG.trustedUser) { console.error("FACADE_TRUSTED_USER is required (Tailscale login, e.g. you@gmail.com)"); process.exit(2); }
fs.mkdirSync(path.dirname(CFG.auditFile), { recursive: true });

function audit(rec) { // append-only JSONL; never rewritten
  fs.appendFileSync(CFG.auditFile, JSON.stringify({ ts: new Date().toISOString(), ...rec }) + "\n");
}
const run = (args) => new Promise((res, rej) =>
  execFile(CFG.herdr, args, { timeout: 15000, windowsHide: true, maxBuffer: 8 << 20 }, (e, out, err) =>
    e ? rej(new Error((err || e.message).toString().slice(0, 300))) : res(out)));
const herdrJson = async (args) => JSON.parse(await run(args));

// Adapter interface: list() -> panes[], read(id), sendText(id, text), sendKeys(id, keys).
// herdr is the primary, durable adapter. See README for the jcode adapter plan (desk jcode
// sessions run outside herdr because jcode+herdr+Windows breaks input).
const herdrAdapter = {
  name: "herdr",
  async workspaces() { return (await herdrJson(["workspace", "list"])).result.workspaces; },
  async panes() { return (await herdrJson(["pane", "list"])).result.panes ?? []; },
  async read(id) { return await run(["pane", "read", id]); },
  async sendText(id, text) { await run(["pane", "send-text", id, text]); },
  async sendKeys(id, keys) { await run(["pane", "send-keys", id, ...keys]); },
};

function who(req) {
  const u = req.headers["tailscale-user-login"];
  return typeof u === "string" && u === CFG.trustedUser ? u : null;
}
const stamps = [];
function rateOk() {
  const now = Date.now();
  while (stamps.length && now - stamps[0] > 60000) stamps.shift();
  if (stamps.length >= CFG.writesPerMinute) return false;
  stamps.push(now); return true;
}
async function inWriteScope(paneId) {
  const wsId = paneId.split(":")[0];
  const ws = (await herdrAdapter.workspaces()).find((w) => w.workspace_id === wsId);
  return ws && CFG.writeScope.test(ws.label) ? ws : null;
}
const send = (res, code, body) => {
  res.writeHead(code, { "content-type": "application/json", "cache-control": "no-store" });
  res.end(JSON.stringify(body));
};
const body = (req) => new Promise((ok, no) => {
  let b = ""; req.on("data", (c) => { b += c; if (b.length > 16384) { no(new Error("too large")); req.destroy(); } });
  req.on("end", () => { try { ok(b ? JSON.parse(b) : {}); } catch (e) { no(e); } });
});
const PANE = /^w\w+:p\w+$/;

const server = http.createServer(async (req, res) => {
  const user = who(req);
  const url = new URL(req.url, "http://x");
  const base = { method: req.method, path: url.pathname, user };
  if (!user) { audit({ ...base, outcome: "denied-identity" }); return send(res, 403, { error: "identity not trusted" }); }
  try {
    if (req.method === "GET" && url.pathname === "/healthz") return send(res, 200, { ok: true, adapters: ["herdr"] });
    if (req.method === "GET" && url.pathname === "/v1/workspaces") {
      const ws = await herdrAdapter.workspaces();
      return send(res, 200, { workspaces: ws.map((w) => ({ ...w, writable: CFG.writeScope.test(w.label), full: w.pane_count >= CFG.maxPanesPerSpace })) });
    }
    if (req.method === "GET" && url.pathname === "/v1/panes") return send(res, 200, { panes: await herdrAdapter.panes() });
    let m = url.pathname.match(/^\/v1\/panes\/([^/]+)\/(read|text|keys)$/);
    if (m && PANE.test(m[1])) {
      const [, id, op] = m;
      if (op === "read" && req.method === "GET") {
        audit({ ...base, pane: id, outcome: "read" });
        return send(res, 200, { pane: id, text: await herdrAdapter.read(id) });
      }
      if (req.method === "POST" && (op === "text" || op === "keys")) {
        const ws = await inWriteScope(id);
        if (!ws) { audit({ ...base, pane: id, outcome: "denied-scope" }); return send(res, 403, { error: "pane is outside the write scope" }); }
        if (!rateOk()) { audit({ ...base, pane: id, outcome: "rate-limited" }); return send(res, 429, { error: "slow down" }); }
        const b = await body(req);
        if (op === "text") {
          if (typeof b.text !== "string" || !b.text || b.text.length > CFG.maxText) return send(res, 400, { error: "text required, max " + CFG.maxText });
          audit({ ...base, pane: id, workspace: ws.label, outcome: "write-text", bytes: b.text.length, preview: b.text.slice(0, 80) });
          await herdrAdapter.sendText(id, b.text);
        } else {
          if (!Array.isArray(b.keys) || !b.keys.length || b.keys.length > 20 || !b.keys.every((k) => typeof k === "string" && k.length < 24)) return send(res, 400, { error: "keys[] required" });
          audit({ ...base, pane: id, workspace: ws.label, outcome: "write-keys", keys: b.keys });
          await herdrAdapter.sendKeys(id, b.keys);
        }
        return send(res, 200, { ok: true });
      }
    }
    audit({ ...base, outcome: "not-found" });
    return send(res, 404, { error: "not found" });
  } catch (e) {
    audit({ ...base, outcome: "error", error: String(e.message).slice(0, 200) });
    return send(res, 500, { error: "adapter error" });
  }
});
server.listen(CFG.port, CFG.host, () => console.log(`herdr-facade on http://${CFG.host}:${CFG.port}, audit ${CFG.auditFile}`));
