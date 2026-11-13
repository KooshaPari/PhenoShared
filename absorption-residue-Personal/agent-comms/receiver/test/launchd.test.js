// The launchd supervisor tests.
//
// The receiver is only RUNNING if something supervises it. These tests check the
// two properties that matter, and that a past incident proved matter:
//
//   1. The installer REFUSES to install a job whose entrypoint does not exist.
//      The previous bridge incarnation pointed at a wiped /private/tmp path and
//      launchd crash-looped 4414 times before anyone noticed. The installer is
//      the thing that must prevent that, so it is the thing that must be tested.
//   2. The rendered plist PARSES. A plist that does not parse is a job that
//      silently never runs -- the worst possible outcome, because it looks
//      installed.
//
// These tests are read-only with respect to the machine: they render into a temp
// directory and never call `launchctl`.

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { mkdtemp, readFile, rm, writeFile, chmod } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";

const exec = promisify(execFile);

// This test file lives at agent-comms/receiver/test/, so the launchd dir is two
// levels up: agent-comms/launchd.
const AGENT_COMMS_DIR = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const LAUNCHD_DIR = join(AGENT_COMMS_DIR, "launchd");
const INSTALL_SH = join(LAUNCHD_DIR, "install.sh");
const PLIST_TEMPLATE = join(LAUNCHD_DIR, "com.example.agent-comms-wake.plist");

/**
 * Render the plist template the way install.sh does.
 * @param {Record<string, string>} vars
 */
async function render(vars) {
  let text = await readFile(PLIST_TEMPLATE, "utf8");
  for (const [key, value] of Object.entries(vars)) {
    text = text.replaceAll(`__${key}__`, value);
  }
  return text;
}

describe("the launchd supervisor", () => {
  test("the plist template has no unsubstituted placeholder after rendering", async () => {
    const text = await render({
      NODE: "/opt/homebrew/bin/node",
      REPO: "/tmp/repo",
      ENV: "/tmp/env",
      LOG_DIR: "/tmp/log",
      HOME: "/tmp/home",
      USER: "tester",
    });
    assert.ok(!text.includes("__"), `unsubstituted placeholder remains:\n${text}`);
  });

  test("the rendered plist parses on every platform, not just macOS", async (t) => {
    const dir = await mkdtemp(join(tmpdir(), "wake-plist-"));
    t.after(() => rm(dir, { recursive: true, force: true }));
    const file = join(dir, "job.plist");
    await writeFile(
      file,
      await render({
        NODE: "/opt/homebrew/bin/node",
        REPO: "/tmp/repo",
        ENV: "/tmp/env",
        LOG_DIR: "/tmp/log",
        HOME: "/tmp/home",
        USER: "tester",
      }),
    );

    const keys = await parsePlistKeys(file);

    // Parsing is necessary but not sufficient: a plist can be well-formed XML and
    // still be a job that never runs. These four keys are what make it a job.
    const required = ["EnvironmentVariables", "KeepAlive", "Label", "ProgramArguments"];
    for (const key of required) {
      assert.ok(keys.includes(key), `parsed plist is missing <${key}>; got: ${keys.join(", ")}`);
    }
  });

  test("a malformed plist is rejected, so the parse assertion actually bites", async (t) => {
    // Without this the parse test would still pass if the parser chain silently
    // degraded into a no-op that reported whatever keys it liked.
    const dir = await mkdtemp(join(tmpdir(), "wake-plist-bad-"));
    t.after(() => rm(dir, { recursive: true, force: true }));
    const file = join(dir, "job.plist");

    const good = await render({
      NODE: "/opt/homebrew/bin/node",
      REPO: "/tmp/repo",
      ENV: "/tmp/env",
      LOG_DIR: "/tmp/log",
      HOME: "/tmp/home",
      USER: "tester",
    });

    // Drop the closing tag: unclosed XML, exactly the silent-never-runs failure
    // this suite exists to catch.
    await writeFile(file, good.replace("</plist>", ""));

    await assert.rejects(parsePlistKeys(file), /does not parse/);
  });

  test("the plist never contains a credential", async () => {
    const text = await readFile(PLIST_TEMPLATE, "utf8");
    // The bearer token belongs in the env file, never in a committed plist.
    // Match an ASSIGNMENT with a value, not a prose mention in a comment.
    assert.ok(!/WAKE_RECEIVER_TOKEN\s*=\s*\S/.test(text), "the plist must not assign a token");
    assert.ok(!/Bearer\s+[A-Za-z0-9_-]{12,}/i.test(text), "the plist must not contain a bearer token value");
  });

  test("the plist execs node so SIGTERM reaches it", async () => {
    const text = await readFile(PLIST_TEMPLATE, "utf8");
    // Without `exec` the zsh wrapper catches the signal and node never sees it,
    // so the process never exits and launchd keeps a zombie.
    assert.match(text, /exec __NODE__/);
  });

  test("the plist parks on a clean exit instead of respawn-storming", async () => {
    const text = await readFile(PLIST_TEMPLATE, "utf8");
    assert.match(text, /<key>SuccessfulExit<\/key>\s*<false\/>/);
    assert.match(text, /<key>ThrottleInterval<\/key>/);
  });

  test("the installer refuses to install when the entrypoint is missing", async (t) => {
    // A fake HOME so the installer cannot touch the real ~/Library/LaunchAgents.
    const home = await mkdtemp(join(tmpdir(), "wake-home-"));
    t.after(() => rm(home, { recursive: true, force: true }));

    // The installer resolves its own entrypoint relative to its own location, so
    // a copy of the launchd dir with NO sibling receiver/ gives a missing entry.
    const fakeLaunchd = join(home, "agent-comms", "launchd");
    await mkdirp(fakeLaunchd);
    await writeFile(join(fakeLaunchd, "install.sh"), await readFile(INSTALL_SH));
    await writeFile(
      join(fakeLaunchd, "com.example.agent-comms-wake.plist"),
      await readFile(PLIST_TEMPLATE),
    );
    await chmod(join(fakeLaunchd, "install.sh"), 0o755);

    let failed = false;
    let stderr = "";
    try {
      await exec("bash", [join(fakeLaunchd, "install.sh"), "install"], {
        env: { ...process.env, HOME: home },
      });
    } catch (error) {
      failed = true;
      stderr = String(error.stderr ?? "");
    }
    assert.ok(failed, "the installer must fail when the entrypoint is missing");
    assert.match(stderr, /entrypoint not found/);
    assert.ok(
      !(await readFile(join(home, "Library", "LaunchAgents", "com.example.agent-comms-wake.plist"), "utf8").catch(() => null)),
      "no plist may be installed when the entrypoint is missing",
    );
  });
});

/**
 * Real plist parsers, tried in order.
 *
 * `plutil` is the native macOS validator but does not exist on Linux, so the
 * self-hosted CI runner died with `spawn plutil ENOENT` before any assertion
 * ran. `plistlib` is part of the Python 3 standard library and parses the same
 * format, so the parse is asserted on every platform instead of being skipped
 * where the job actually runs.
 *
 * Each entry returns the rendered plist serialized as JSON.
 * @type {{name: string, run: (file: string) => Promise<{stdout: string}}[]}[]}
 */
const PLIST_PARSERS = [
  {
    name: "plutil",
    run: (file) => exec("plutil", ["-convert", "json", "-o", "-", file]),
  },
  {
    name: "python3 plistlib",
    run: (file) =>
      exec("python3", [
        "-c",
        "import json,plistlib,sys;print(json.dumps(plistlib.load(open(sys.argv[1],'rb')),default=str))",
        file,
      ]),
  },
];

/**
 * Parse the plist with the first parser that is actually installed and return
 * its sorted top-level keys.
 *
 * A parser that is missing falls through to the next one, but a parser that is
 * installed and REJECTS the file is a real failure: falling through there would
 * let a broken plist pass on whichever parser happens to be more lenient.
 * @param {string} file
 * @returns {Promise<string[]>}
 */
async function parsePlistKeys(file) {
  /** @type {string[]} */
  const rejections = [];
  /** @type {string[]} */
  const missing = [];

  for (const parser of PLIST_PARSERS) {
    try {
      const { stdout } = await parser.run(file);
      const parsed = JSON.parse(stdout);
      return Object.keys(parsed).sort();
    } catch (error) {
      const code = /** @type {NodeJS.ErrnoException} */ (error).code;
      if (code === "ENOENT") {
        missing.push(parser.name);
        continue;
      }
      rejections.push(`${parser.name}: ${String(error.stderr ?? error.message).trim()}`);
    }
  }

  assert.fail(
    rejections.length
      ? `the rendered plist does not parse:\n  ${rejections.join("\n  ")}`
      : `no plist parser available (not installed: ${missing.join(", ")})`,
  );
}

/** mkdir -p, portably enough for a test helper. */
async function mkdirp(dir) {
  const { mkdir } = await import("node:fs/promises");
  await mkdir(dir, { recursive: true });
}
