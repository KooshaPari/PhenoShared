// Entrypoint. Tokens are read from the environment and are never logged, never written to
// disk, and never baked into a URL.
//
//   WAKE_RECEIVER_TOKEN      (required) bearer token the sender must present
//   WAKE_RECEIVER_PORT       (optional, default 3211) loopback port
//   WAKE_RECEIVER_STATE      (optional, default ./state/receipts) durable receipt root
//   WAKE_RECEIVER_DRY_RUN    "1" to prove transport without moving panes
//   WAKE_RECEIVER_MAX_PER_MINUTE  accepted wake attempts per minute (default 30; 0 disables)
//   WAKE_RECEIVER_MAP_JSON   inline JSON recipient -> pane map (test/local override)
//   WAKE_RECEIVER_MAP_FILE   path to a recipient -> pane map JSON file (else default)
//
// The recipient -> pane mapping is the ONLY thing that decides which pane a message wakes.
// This runtime does not provision DNS, email addresses, provider routes, aliases, or
// credentials; it consumes a mapping the operator edits.
//
// ONE PROCESS PER STATE DIR. The durable index is file-backed but the dedupe decision is
// made in memory (see the header of `server.js` and the class doc of `store.js`). There is
// no lock file, so a second receiver over the same WAKE_RECEIVER_STATE would race the first
// and could wake the same pane twice. Never run two.
//
//   node agent-comms/receiver/src/index.js                     start the receiver
//   node agent-comms/receiver/src/index.js resolve <id> <outcome>
//                                                              record an operator decision
//                                                              for an uncertain receipt

import { realpathSync, existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { createReceiver, createWakeServer } from "./server.js";
import { ReceiptStore, SeenStore } from "./store.js";
import { createHerdrWaker, noopWaker } from "./herdr.js";
import { parseRecipientMap } from "./mapping.js";
import { parseResolveArgs } from "./cli-args.js";

const DEFAULT_MAP_FILE = fileURLToPath(new URL("../../config/recipient-map.json", import.meta.url));
const DEFAULT_STATE_DIR = fileURLToPath(new URL("../state/receipts/", import.meta.url));

/**
 * Load the recipient -> pane map from env (inline JSON or a file) or the shipped default.
 * @param {NodeJS.ProcessEnv} env
 * @returns {Record<string, {paneId?: string, label?: string, agent?: string}>}
 */
export function loadRecipientMap(env) {
  if (env.WAKE_RECEIVER_MAP_JSON) {
    return parseRecipientMap(JSON.parse(env.WAKE_RECEIVER_MAP_JSON));
  }
  const file = env.WAKE_RECEIVER_MAP_FILE ?? DEFAULT_MAP_FILE;
  if (!existsSync(file)) {
    throw new Error(`recipient map file not found: ${file}`);
  }
  return parseRecipientMap(JSON.parse(readFileSync(file, "utf8")));
}

/**
 * Parse config from the environment. Throws on any invalid input; a thrown error is the
 * only honest way to say "this process must not run".
 *
 * @param {NodeJS.ProcessEnv} env
 */
export function readConfig(env) {
  const token = env.WAKE_RECEIVER_TOKEN;
  if (!token) throw new Error("WAKE_RECEIVER_TOKEN is required");

  const port = Number(env.WAKE_RECEIVER_PORT ?? "3211");
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error("WAKE_RECEIVER_PORT must be an integer 1-65535");
  }

  const dryRun = env.WAKE_RECEIVER_DRY_RUN === "1";
  const maxPerMinute = Number(env.WAKE_RECEIVER_MAX_PER_MINUTE ?? "30");
  if (!Number.isInteger(maxPerMinute) || maxPerMinute < 0) {
    throw new Error("WAKE_RECEIVER_MAX_PER_MINUTE must be an integer >= 0");
  }
  const stateDir = env.WAKE_RECEIVER_STATE ?? DEFAULT_STATE_DIR;
  const recipientMap = loadRecipientMap(env);

  return { token, port, dryRun, maxPerMinute, stateDir, recipientMap };
}

/**
 * Record an operator decision for a receipt that is stuck at `pending`.
 *
 * WHY A COMMAND AND NOT A HAND EDIT. Appending to `seen.jsonl` by hand works, but it is easy
 * to get wrong in ways this receiver cannot forgive: a missing newline splices onto the
 * previous record, a mistyped id silently resolves nothing, and a `status` of `pending`
 * re-creates the unknown state the operator was trying to clear. This command validates the
 * id and the outcome, refuses an id the index has never seen, and appends through the same
 * fsyncing writer the receiver uses.
 *
 * The running receiver keeps its own in-memory snapshot, so it sees the new decision only
 * after a restart. That is deliberate: a live process must not silently swap the answer it
 * is about to write.
 *
 * @param {NodeJS.ProcessEnv} env
 * @param {string[]} argv arguments after the `resolve` subcommand
 * @returns {{receiptId: string, previous: string, status: string}}
 */
export function resolveReceipt(env = process.env, argv = []) {
  const { receiptId, status } = parseResolveArgs(argv);
  const stateDir = env.WAKE_RECEIVER_STATE ?? DEFAULT_STATE_DIR;
  const file = join(stateDir, "seen.jsonl");
  // Never create the directory or the file here: a mistyped WAKE_RECEIVER_STATE must not
  // leave an empty index behind, because an empty index reads as "nothing was ever
  // attempted" and re-opens every receipt for replay.
  if (!existsSync(file)) {
    throw new Error(`no seen index at ${file}; start the receiver once, or fix WAKE_RECEIVER_STATE`);
  }
  const seen = new SeenStore(stateDir);
  const { previous, entry } = seen.resolve(receiptId, status);
  return { receiptId, previous: previous.status, status: entry.status };
}

/**
 * Select the waker for a config. Dry-run selects a no-op so no pane is ever moved; live
 * selects the real path walk. `runner` is injectable for tests.
 *
 * @param {{dryRun: boolean, recipientMap: Record<string, any>}} config
 * @param {(args: string[]) => Promise<any>} [runner]
 */
export function buildWaker(config, runner) {
  if (config.dryRun) return noopWaker;
  return createHerdrWaker({ recipientMap: config.recipientMap, runner });
}

/**
 * @param {NodeJS.ProcessEnv} [env]
 * @param {(args: string[]) => Promise<any>} [runner]
 */
export function main(env = process.env, runner) {
  const config = readConfig(env);
  const store = new ReceiptStore(config.stateDir);
  const seen = new SeenStore(config.stateDir);
  const waker = buildWaker(config, runner);
  const handler = createReceiver({
    store,
    seen,
    waker,
    token: config.token,
    maxPerMinute: config.maxPerMinute,
    // Log receipt identity only. The token is never passed to the logger.
    logger: {
      info: (msg, meta) => console.log(`[wake] ${msg}`, meta ?? {}),
      warn: (msg, meta) => console.warn(`[wake] ${msg}`, meta ?? {}),
    },
  });

  const server = createWakeServer(handler, { port: config.port, host: "127.0.0.1" });
  // A failed bind (EADDRINUSE, EACCES) raises an async 'error', not a throw. Without this
  // the process would print nothing and exit 0, and a supervisor would read that clean exit
  // as "healthy" while no receiver exists. Fail loudly and non-zero instead.
  server.on("error", (error) => {
    console.error(`[wake] could not bind http://127.0.0.1:${config.port}: ${/** @type {Error} */ (error).message}`);
    process.exit(1);
  });
  server.on("listening", () => {
    const address = server.address();
    const port = typeof address === "object" && address ? address.port : config.port;
    console.log(`[wake] listening on http://127.0.0.1:${port}/wake (loopback only)`);
    console.log(`[wake] durable receipts: ${config.stateDir}`);
    console.log(`[wake] mode: ${config.dryRun ? "DRY RUN (no pane is ever raised)" : "live herdr wake"}`);
    console.log(`[wake] bound recipients: ${Object.keys(config.recipientMap).join(", ") || "(none)"}`);
    // Tell the operator which env var points the sender here. No secrets in output.
    console.log(`[wake] senders call POST /wake with Authorization: Bearer $WAKE_RECEIVER_TOKEN`);
  });
  return server;
}

// Only auto-start when executed directly, so tests can import without binding a port.
//
// This MUST compare resolved realpaths. `import.meta.url` is the resolved realpath of
// this module; `process.argv[1]` is the path AS TYPED. Comparing them directly fails
// whenever the two differ -- a symlinked parent directory, a symlinked launch path, a
// launcher that resolves paths (npx, bun wrappers, some launchd ProgramArguments forms).
// That failure is silent and fatal: main() never runs, the process prints nothing, exits
// 0, and binds no port, so there is no wake path at all.
function isEntrypoint() {
  const invoked = process.argv[1];
  if (!invoked) return false;
  try {
    return realpathSync(invoked) === fileURLToPath(import.meta.url);
  } catch {
    return false;
  }
}

if (isEntrypoint()) {
  try {
    if (process.argv[2] === "resolve") {
      const result = resolveReceipt(process.env, process.argv.slice(3));
      console.log(
        `[wake] resolved ${result.receiptId}: ${result.previous} -> ${result.status}`,
      );
      console.log("[wake] restart the receiver so it reloads the index");
    } else {
      main();
    }
  } catch (error) {
    const prefix = process.argv[2] === "resolve" ? "resolve failed" : "startup failed";
    console.error(`[wake] ${prefix}: ${/** @type {Error} */ (error).message}`);
    process.exit(1);
  }
}
