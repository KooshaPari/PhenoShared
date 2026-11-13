// Tests for herdr CLI argument validation.
//
// THE BUG THESE GUARD. `execFile` is spawned without a shell, so these values cannot
// start a shell command. They CAN still be read by herdr as FLAGS. A pane id of
// `--json` in the recipient map, or in the JSON `herdr pane list` emits, would be
// handed straight through to argv and change what the command means, so the waker
// would walk toward whatever the flag selected instead of toward a pane.
//
// The rule the fix encodes: a herdr handle is an opaque, machine-generated token. It
// must start alphanumeric, so it can never be mistaken for an option. Anything else is
// refused rather than escaped or repaired, because "repair" is how these bugs return.

import { test, describe } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import {
  HERDR_DIRECTIONS,
  InvalidCliArgument,
  MAX_HERDR_ID_LENGTH,
  assertHerdrDirection,
  assertHerdrId,
  isValidHerdrDirection,
  isValidHerdrId,
  sanitizePaneEntry,
} from "../src/cli-args.js";
import { createHerdrWaker } from "../src/herdr.js";

describe("herdr handle validation", () => {
  test("accepts the real id shapes herdr emits", () => {
    for (const id of ["w7:p1Q", "w8:pN", "wA:p8", "wF:p1", "w7", "w7:t1", "p0", "a_b.c-d:e"]) {
      assert.equal(isValidHerdrId(id), true, `${id} is a real handle shape`);
    }
  });

  test("refuses anything a CLI would read as a flag", () => {
    // The whole point of the leading-alphanumeric rule: none of these may be argv.
    for (const id of ["--json", "-h", "--pane", "-", "--", " -x", "--dir=/tmp"]) {
      assert.equal(isValidHerdrId(id), false, `${JSON.stringify(id)} must not reach argv`);
    }
  });

  test("refuses whitespace, control characters, and shell metacharacters", () => {
    for (const id of [
      "w7 p1",
      "w7:p1\nevil",
      "w7:p1\tx",
      "w7:p1;rm",
      "w7:p1`id`",
      "w7:p1$(id)",
      "w7:p1|cat",
      "w7:p1&",
      "w7:p1\n",
      "",
    ]) {
      assert.equal(isValidHerdrId(id), false, `${JSON.stringify(id)} must not reach argv`);
    }
  });

  test("refuses non-strings and absurd lengths", () => {
    for (const value of [undefined, null, 0, 42, {}, [], true, Symbol("w7:p1")]) {
      assert.equal(isValidHerdrId(value), false, `${String(value)} must not reach argv`);
    }
    assert.equal(isValidHerdrId("w".repeat(MAX_HERDR_ID_LENGTH)), true);
    assert.equal(isValidHerdrId("w".repeat(MAX_HERDR_ID_LENGTH + 1)), false);
  });

  test("assertHerdrId returns the value unchanged, so it composes inline", () => {
    assert.equal(assertHerdrId("pane id", "w7:p1Q"), "w7:p1Q");
    assert.throws(() => assertHerdrId("tab id", "--json"), (error) => {
      assert.ok(error instanceof InvalidCliArgument);
      assert.equal(error.kind, "tab id");
      return true;
    });
  });

  test("only the four real directions are accepted", () => {
    for (const direction of HERDR_DIRECTIONS) {
      assert.equal(isValidHerdrDirection(direction), true);
      assert.equal(assertHerdrDirection(direction), direction);
    }
    for (const bad of ["up-left", "UP", "", "--up", undefined, 1]) {
      assert.equal(isValidHerdrDirection(bad), false, `${String(bad)} is not a direction`);
    }
    assert.throws(() => assertHerdrDirection("sideways"), InvalidCliArgument);
  });
});

describe("pane entries from herdr are sanitized, not repaired", () => {
  test("a malformed pane_id drops the whole entry", () => {
    assert.equal(sanitizePaneEntry({ pane_id: "--json" }), undefined);
    assert.equal(sanitizePaneEntry({}), undefined);
    assert.equal(sanitizePaneEntry(null), undefined);
  });

  test("a malformed workspace or tab id is omitted rather than trusted", () => {
    const clean = sanitizePaneEntry({ pane_id: "w7:p1Q", workspace_id: "w7", tab_id: "w7:t1" });
    assert.deepEqual(clean, { paneId: "w7:p1Q", workspaceId: "w7", tabId: "w7:t1" });

    const partial = sanitizePaneEntry({ pane_id: "w7:p1Q", workspace_id: "--x", tab_id: "w7:t1" });
    assert.deepEqual(partial, { paneId: "w7:p1Q", tabId: "w7:t1" });
    assert.equal("workspaceId" in partial, false);
  });
});

describe("a hostile handle can never reach argv", () => {
  /** Records every argv the waker builds, so the test can assert on the literal tokens. */
  function spyRunner(paneDoc, { getResult } = {}) {
    const seen = [];
    const runner = async (args) => {
      seen.push([...args]);
      if (args[0] === "pane" && args[1] === "list") return paneDoc;
      if (args[0] === "pane" && args[1] === "get") return { result: getResult };
      return { result: {} };
    };
    return { runner, seen };
  }

  test("a pane list whose ids are flag-shaped produces an honest failure", async () => {
    // herdr here reports a pane named `--json` and claims it is focused.
    const { runner, seen } = spyRunner({
      result: {
        panes: [{ pane_id: "--json", workspace_id: "--ws", tab_id: "--tab", focused: true }],
      },
    });

    const waker = createHerdrWaker({ recipientMap: { civis: { paneId: "--json" } }, runner });
    const result = await waker("civis", {});

    assert.equal(result.woke, false, "a flag-shaped handle must never report a wake");
    assert.equal(result.paneId, undefined);
    // The list call is the ONLY thing that may run: the bad ids never reach argv.
    assert.deepEqual(seen, [["pane", "list"]]);
    for (const args of seen) {
      for (const token of args) {
        assert.doesNotMatch(token, /^--/, `${token} was passed as a flag-shaped token`);
      }
    }
  });

  test("a focus seed that turns out to be flag-shaped fails the walk honestly", async () => {
    // `pane list` names a legitimate target, and `pane get` confirms it is NOT focused --
    // so the walk really starts. The machine-wide focused entry -- the value that seeds
    // the walk -- is hostile, and without sanitizing it would be handed to
    // `pane edges --pane --move` as a flag.
    const { runner, seen } = spyRunner(
      {
        result: {
          panes: [
            { pane_id: "--move", workspace_id: "w7", tab_id: "w7:t1", focused: true },
            { pane_id: "w7:p1Q", workspace_id: "w7", tab_id: "w7:t1", focused: false },
          ],
        },
      },
      { getResult: { pane: { pane_id: "w7:p1Q", focused: false } } },
    );

    const waker = createHerdrWaker({ recipientMap: { civis: { paneId: "w7:p1Q" } }, runner });
    const result = await waker("civis", {});

    assert.equal(result.woke, false, "the walk must not claim a wake from a hostile seed");
    assert.equal(result.paneId, undefined);
    assert.ok(seen.length > 1, "the walk should have started before failing");
    for (const args of seen) {
      assert.equal(
        args.includes("--move"),
        false,
        `a flag-shaped focus seed reached argv: ${JSON.stringify(args)}`,
      );
    }
  });
});

describe("the shipped recipient map stays inside the allowlist", () => {
  test("every configured pane id validates", async () => {
    // Guards the operator's own editable file: a typo there should fail loudly here
    // rather than turning into an unexplained "no pane matched" at 3am.
    const file = fileURLToPath(new URL("../../config/recipient-map.json", import.meta.url));
    const map = JSON.parse(await readFile(file, "utf8"));

    const checked = [];
    for (const [key, value] of Object.entries(map)) {
      if (key.startsWith("_")) continue;
      const paneId = typeof value === "string" ? value : value?.paneId;
      if (typeof paneId !== "string") continue;
      checked.push(paneId);
      assert.equal(
        isValidHerdrId(paneId),
        true,
        `recipient-map.json binds ${key} to ${JSON.stringify(paneId)}, which is not a safe handle`,
      );
    }
    assert.ok(checked.length > 0, "the shipped map should configure at least one recipient");
  });
});
