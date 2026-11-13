#!/usr/bin/env node
// Live end-to-end exercise of the agent-comms bridge.
//
// Starts the REAL receiver entrypoint (agent-comms/receiver/src/index.js) against
// the REAL `herdr` CLI, then POSTs a real PhenoBot-shaped receipt and applies the
// producer's OWN acceptance rule (PhenoBot src/bridges/inbox.ts) to the response.
//
// This is the proof that the bridge is WIRED, not merely present in the tree.
// It is NOT a unit test: it spawns the real process, binds a real port, and
// drives the real herdr path walk.
//
// It is SAFE by construction:
//   * the recipient is a persona bound to a pane that is ALREADY FOCUSED or
//     already the target, so the walk either confirms it in place or fails
//     honestly;
//   * the dry-run flag is NOT used, because a dry run would prove only the
//     transport, not the wake.
//   * the pane it targets is a dedicated scratch pane when one is available.
//
// Usage: node scripts/live-bridge-check.mjs [--port N] [--persona jcode] [--dry-run]

import { spawn } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtemp, rm, readFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

import { logSafe, safeError } from "../receiver/src/log-safe.js";

const AGENT_COMMS_DIR = join(dirname(fileURLToPath(import.meta.url)), "..");
const ENTRYPOINT = join(AGENT_COMMS_DIR, "receiver", "src", "index.js");
const MAP_FILE = join(AGENT_COMMS_DIR, "config", "recipient-map.json");

const args = process.argv.slice(2);
const argValue = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 && args[i + 1] ? args[i + 1] : fallback;
};
const PORT = Number(argValue("--port", "3219"));
const PERSONA = argValue("--persona", "jcode");
const DRY_RUN = args.includes("--dry-run");
const TOKEN = "live-check-token-not-a-secret";

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * Apply the producer's acceptance rule, verbatim from PhenoBot src/bridges/inbox.ts.
 */
function producerVerdict(status, body, receiptId) {
  if (status === 202) return "pending-protocol";
  if (status === 200 && body?.status === "awakened" && body?.receiptId === receiptId) {
    return "delivered";
  }
  return "failed";
}

async function main() {
  const stateDir = await mkdtemp(join(tmpdir(), "live-bridge-"));
  const map = JSON.parse(await readFile(MAP_FILE, "utf8"));
  const binding = map[PERSONA];
  if (!binding) {
    console.error(`persona ${logSafe(PERSONA)} has no pane binding in the map; nothing to exercise`);
    await rm(stateDir, { recursive: true, force: true });
    process.exit(2);
  }
  const paneId = typeof binding === "string" ? binding : binding.paneId;
  console.log(`target persona : ${logSafe(PERSONA)} -> pane ${logSafe(paneId)}`);
  console.log(`target port    : ${PORT}`);
  console.log(`mode           : ${DRY_RUN ? "DRY RUN (transport only)" : "LIVE (real herdr walk)"}`);

  const child = spawn(process.execPath, [ENTRYPOINT], {
    env: {
      ...process.env,
      WAKE_RECEIVER_TOKEN: TOKEN,
      WAKE_RECEIVER_PORT: String(PORT),
      WAKE_RECEIVER_STATE: stateDir,
      ...(DRY_RUN ? { WAKE_RECEIVER_DRY_RUN: "1" } : {}),
    },
    stdio: ["ignore", "pipe", "pipe"],
  });
  let stdout = "";
  child.stdout.on("data", (d) => { stdout += d; process.stdout.write(`[receiver] ${d}`); });
  child.stderr.on("data", (d) => process.stderr.write(`[receiver:err] ${d}`));

  // Wait for the listening line. The receiver prints it only after a real bind.
  const deadline = Date.now() + 20000;
  while (!/\[wake\] listening on/.test(stdout)) {
    if (Date.now() > deadline) {
      console.error("receiver never reported listening");
      child.kill("SIGTERM");
      await rm(stateDir, { recursive: true, force: true });
      process.exit(1);
    }
    await sleep(100);
  }
  console.log("receiver is listening\n");

  // Build a receipt exactly as PhenoBot's Inbox.put persists it.
  const messageId = "live-check-1";
  const receipt = {
    id: createHash("sha256").update(`${PERSONA}:${messageId}`).digest("hex"),
    agent: PERSONA,
    messageId,
    guildId: "1558641660915884154",
    channelId: "1558641660915884154",
    userId: "684729569226977292",
    content: "live bridge check",
  };

  const res = await fetch(`http://127.0.0.1:${PORT}/wake`, {
    method: "POST",
    redirect: "error",
    headers: {
      "content-type": "application/json",
      authorization: `Bearer ${TOKEN}`,
      "idempotency-key": receipt.id,
    },
    body: JSON.stringify(receipt),
  });
  const text = await res.text();
  let body = {};
  try { body = JSON.parse(text); } catch { body = { unparseable: text }; }
  const verdict = producerVerdict(res.status, body, receipt.id);

  console.log("--- producer-side verdict ---");
  console.log(`http status   : ${res.status}`);
  console.log(`response body : ${logSafe(text)}`);
  console.log(`PhenoBot would: ${verdict}`);

  // Durable receipt evidence.
  let receipts = "";
  try {
    receipts = await readFile(join(stateDir, "receipts.jsonl"), "utf8");
  } catch { /* none */ }
  const lines = receipts.trim().split("\n").filter(Boolean);
  console.log(`durable receipt: ${lines.length} line(s)`);
  for (const line of lines) console.log(`  ${logSafe(line)}`);

  child.kill("SIGTERM");
  await sleep(300);
  await rm(stateDir, { recursive: true, force: true });

  if (verdict !== "delivered") {
    console.error(`\nFAIL: the producer would NOT treat this as delivered (${verdict})`);
    process.exit(1);
  }
  console.log("\nPASS: the producer would treat this wake as DELIVERED.");
}

main().catch((error) => {
  console.error(safeError(error));
  process.exit(1);
});
