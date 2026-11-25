// Regression tests for the pane-scoped focus verification, ported from the proven reference
// implementation and adapted to a recipient -> pane map.
//
// THE BUG THESE GUARD
// A waker must decide "is the target pane focused?" from a PANE-SCOPED source
// (`herdr pane get <target>`, cross-checked against `herdr pane list`). `pane edges --current`
// reflects the ATTACHED UI tab, not programmatic focus, so it can never back a focus claim.
// `edges.<dir>` booleans are untrustworthy too: every direction is probed with
// `pane neighbor`, and the walk must be seeded from the machine-wide focused pane.
//
// DETERMINISM. These tests inject an in-memory `runner`; they spawn no process, bind no port,
// and touch no real pane.

import { test, describe } from "node:test";
import assert from "node:assert/strict";

import { createHerdrWaker } from "../src/herdr.js";

/**
 * In-memory stand-in for the herdr CLI that models the real binary's asymmetry:
 * `pane get` and `pane list` are per-pane and authoritative, while `pane edges --current`
 * reports the ATTACHED tab regardless of where programmatic focus actually is.
 *
 * @param {Record<string, {workspaceId: string, tabId: string, label?: string, focused?: boolean}>} panes
 * @param {{attached?: string, focusedPaneId?: string, overridePaneGet?: Record<string, boolean>, omitFocusFlag?: boolean}} options
 */
function fakeRunner(panes, { attached, focusedPaneId, overridePaneGet = {}, omitFocusFlag = false } = {}) {
  /** @type {string[][]} */
  const calls = [];

  const tabPanes = (tabId) =>
    Object.entries(panes)
      .filter(([, p]) => p.tabId === tabId)
      .map(([pane_id]) => ({
        pane_id,
        focused: pane_id === focusedPaneId,
        rect: { x: 0, y: 0, width: 80, height: 24 },
      }));

  /** @type {(args: string[]) => Promise<any>} */
  const runner = async (args) => {
    calls.push([...args]);

    // pane get <ID> -- PER-PANE, authoritative.
    if (args[0] === "pane" && args[1] === "get") {
      const id = args[2];
      const p = panes[id];
      if (!p) return { result: { pane: { pane_id: id } } };
      const focused = id in overridePaneGet ? overridePaneGet[id] : p.focused === true;
      const pane = { pane_id: id, workspace_id: p.workspaceId, tab_id: p.tabId, label: p.label };
      // `omitFocusFlag` models a herdr that reports the pane but no focus verdict at all,
      // which is different from reporting `focused: false`.
      if (!omitFocusFlag) pane.focused = focused;
      return { result: { pane } };
    }

    // pane list -- MACHINE-WIDE, per-pane flags, NOT tab-scoped.
    if (args[0] === "pane" && args[1] === "list") {
      return {
        result: {
          panes: Object.entries(panes).map(([pane_id, p]) => ({
            pane_id,
            workspace_id: p.workspaceId,
            tab_id: p.tabId,
            label: p.label,
            focused: p.focused === true,
          })),
        },
      };
    }

    // pane edges --current / --pane -- geometry. `--current` is ATTACHED-TAB-SCOPED.
    if (args[0] === "pane" && args[1] === "edges") {
      if (args.includes("--current")) {
        return {
          result: {
            edges: {
              pane_id: focusedPaneId,
              layout: { focused_pane_id: focusedPaneId, panes: tabPanes(attached) },
            },
          },
        };
      }
      const id = args[args.indexOf("--pane") + 1];
      const p = panes[id];
      return {
        result: {
          edges: {
            pane_id: id,
            layout: { focused_pane_id: focusedPaneId, panes: tabPanes(p ? p.tabId : attached) },
          },
        },
      };
    }

    // workspace focus / tab focus -- accepted, and deliberately NOT treated as evidence.
    if ((args[0] === "workspace" || args[0] === "tab") && args[1] === "focus") {
      return { result: { focused: true } };
    }

    return { result: {} };
  };

  return { runner, calls };
}

/**
 * Extend a fake herdr runner with a WORKING geometry walk.
 *
 * Real herdr answers `pane focus` by moving machine-wide focus, and `pane get` / `pane
 * list` then report the new state. Without modelling that, the walk path can only ever
 * be tested in its failure modes. This wrapper makes `pane focus` actually land, and
 * flips the per-pane `focused` flags to match -- so a test can assert that the waker
 * takes the success path AND that its independent confirmation is what authorised it.
 *
 * @param {{runner: (args: string[]) => Promise<any>, calls: string[][]}} base
 * @param {{
 *   panes: Record<string, any>, seedId: string, targetId: string, neighborId: string,
 *   confirmFocusOnLanding?: boolean,
 * }} config
 */
function withWalkSimulation({ runner, calls }, { panes, seedId, targetId, neighborId, confirmFocusOnLanding = true }) {
  let landed = false;

  const entry = (id) => {
    const p = panes[id];
    return { pane_id: id, workspace_id: p.workspaceId, tab_id: p.tabId, label: p.label };
  };

  return async (args) => {
    if (args[0] === "pane" && args[1] === "neighbor") {
      calls.push([...args]);
      return {
        result: {
          neighbor: {
            neighbor_pane_id: neighborId,
            layout: { panes: [{ pane_id: neighborId, rect: { x: 80, y: 0, width: 80, height: 24 } }] },
          },
        },
      };
    }
    if (args[0] === "pane" && args[1] === "focus") {
      calls.push([...args]);
      landed = true;
      return { result: { focus: { changed: true, focused_pane_id: targetId } } };
    }
    if (args[0] === "pane" && args[1] === "list") {
      calls.push([...args]);
      return {
        result: {
          panes: Object.keys(panes).map((id) => ({
            ...entry(id),
            focused: landed ? id === targetId : id === seedId,
          })),
        },
      };
    }
    if (args[0] === "pane" && args[1] === "get") {
      calls.push([...args]);
      const focused = confirmFocusOnLanding && landed && args[2] === targetId;
      return { result: { pane: { ...entry(args[2]), focused } } };
    }
    return runner(args);
  };
}

/** @param {any} runner @param {{paneId?: string, label?: string, agent?: string}} [binding] */
function wakerFor(runner, binding = { paneId: "wD:p2" }) {
  return createHerdrWaker({ recipientMap: { civis: binding }, runner });
}

/** @param {string[][]} calls */
function invoked(calls) {
  return calls.map((c) => c.join(" "));
}

describe("recipient -> pane resolution and pane-scoped focus verification", () => {
  test("a mapped recipient resolves to its pane and the walk reaches it", async () => {
    // The target is NOT the focused pane, so a real geometry walk is required.
    const panes = {
      "wA:p0": { workspaceId: "wA", tabId: "wA:t1", label: "SEED", focused: true },
      "wA:p1": { workspaceId: "wA", tabId: "wA:t1", label: "LEFT" },
      "wA:p2": { workspaceId: "wA", tabId: "wA:t1", label: "TARGET" },
    };
    const { runner, calls } = fakeRunner(panes, { attached: "wA:t1", focusedPaneId: "wA:p0" });
    const wrapped = withWalkSimulation({ runner, calls }, {
      panes,
      seedId: "wA:p0",
      targetId: "wA:p2",
      neighborId: "wA:p2",
    });

    const result = await wakerFor(wrapped, { paneId: "wA:p2" })("civis", {});

    assert.equal(result.woke, true, `walk to the mapped pane should succeed: ${result.detail}`);
    assert.equal(result.paneId, "wA:p2");
    const callList = invoked(calls);
    assert.ok(
      callList.some((c) => c.startsWith("pane get wA:p2")),
      `the walk must confirm via a per-pane read; calls:\n${callList.join("\n")}`,
    );
    assert.ok(
      callList.includes("pane focus --pane wA:p0 --direction right") ||
        callList.some((c) => c.startsWith("pane focus --pane wA:p0 --direction")),
      `the walk must actually step from the seed; calls:\n${callList.join("\n")}`,
    );
  });

  test("a recipient with NO mapping reports an honest failure and never claims a wake", async () => {
    const panes = { "w7:p1Q": { workspaceId: "w7", tabId: "w7:t1", label: "OTHER", focused: true } };
    const { runner, calls } = fakeRunner(panes, { attached: "w7:t1", focusedPaneId: "w7:p1Q" });

    const waker = createHerdrWaker({ recipientMap: {}, runner });
    const result = await waker("nobody", {});

    assert.equal(result.woke, false);
    assert.match(result.detail, /no herdr pane bound/);
    assert.equal(calls.length, 0, "an unmapped recipient must not even read the pane list");
  });

  test("a mapping whose pane is absent from pane list never claims a wake", async () => {
    const panes = { "w7:p1Q": { workspaceId: "w7", tabId: "w7:t1", label: "OTHER", focused: true } };
    const { runner } = fakeRunner(panes, { attached: "w7:t1", focusedPaneId: "w7:p1Q" });

    const result = await wakerFor(runner, { paneId: "wX:p9", label: "NO-SUCH-LABEL" })("civis", {});
    assert.equal(result.woke, false);
    assert.match(result.detail, /no herdr pane matched/);
  });

  test("MISMATCH is a failure: pane get says focused, pane list names a different pane", async () => {
    // `pane get <target>` reports focused=true (a stale read) while `pane list` names some
    // OTHER pane as the machine-wide focus. Taking either at face value would forge a wake.
    const panes = {
      "w7:p1Q": { workspaceId: "w7", tabId: "w7:t1", label: "OTHER", focused: true },
      "wD:p2": { workspaceId: "wD", tabId: "wD:t1", label: "TARGET" },
    };
    const { runner } = fakeRunner(panes, {
      attached: "w7:t1",
      focusedPaneId: "w7:p1Q",
      overridePaneGet: { "wD:p2": true },
    });

    const result = await wakerFor(runner)("civis", {});
    assert.equal(result.woke, false, `stale per-pane read must not forge a wake: ${result.detail}`);
    assert.match(result.detail, /pane list reports/);
  });

  test("AMBIGUITY is a failure: two panes report focused, so neither can be claimed", async () => {
    const panes = {
      "w7:p1Q": { workspaceId: "w7", tabId: "w7:t1", label: "OTHER", focused: true },
      "wD:p2": { workspaceId: "wD", tabId: "wD:t1", label: "TARGET", focused: true },
    };
    const { runner } = fakeRunner(panes, { attached: "w7:t1", focusedPaneId: "w7:p1Q" });

    const result = await wakerFor(runner)("civis", {});
    assert.equal(result.woke, false, `ambiguous focus must not claim a wake: ${result.detail}`);
    assert.match(result.detail, /no single focused pane/);
  });

  test("a target that is NOT reachable from the focused layout never claims a wake", async () => {
    // The target lives in a different tab than the focused pane, so the seed's layout does
    // not contain it. The honest failure must be returned, not a fabricated success.
    const panes = {
      "w7:p1Q": { workspaceId: "w7", tabId: "w7:t1", label: "OTHER", focused: true },
      "wD:p2": { workspaceId: "wD", tabId: "wD:t1", label: "TARGET" },
    };
    const { runner } = fakeRunner(panes, { attached: "w7:t1", focusedPaneId: "w7:p1Q" });

    const result = await wakerFor(runner)("civis", {});
    assert.equal(result.woke, false, `must not claim a wake: ${result.detail}`);
    assert.match(result.detail, /not present in focused layout|no navigation path|no focus state/);
  });

  test("a missing focus flag is a failure, not an optimistic success", async () => {
    const panes = { "w7:p1Q": { workspaceId: "w7", tabId: "w7:t1", label: "TARGET" } };
    const { runner } = fakeRunner(panes, {
      attached: "w7:t1",
      focusedPaneId: "w7:p1Q",
      omitFocusFlag: true,
    });

    const result = await wakerFor(runner, { paneId: "w7:p1Q" })("civis", {});
    assert.equal(result.woke, false);
    assert.match(result.detail, /no focus state/);
  });

  test("the walk seeds from the machine-wide focused pane, not the attached tab", async () => {
    // The attached tab is w7:t1 (whose panes know nothing of wA), while the genuinely focused
    // pane is wA:p1 in the target's own tab. A pane-scoped seed must walk successfully and
    // must never go looking in the attached tab.
    const panes = {
      "w7:p1Q": { workspaceId: "w7", tabId: "w7:t1", label: "MUX" },
      "wA:p1": { workspaceId: "wA", tabId: "wA:t1", label: "LEFT", focused: true },
      "wA:p2": { workspaceId: "wA", tabId: "wA:t1", label: "TARGET" },
    };
    const { runner, calls } = fakeRunner(panes, {
      attached: "w7:t1",
      focusedPaneId: "wA:p1",
    });
    const wrapped = withWalkSimulation({ runner, calls }, {
      panes,
      seedId: "wA:p1",
      targetId: "wA:p2",
      neighborId: "wA:p2",
    });

    const result = await wakerFor(wrapped, { paneId: "wA:p2" })("civis", {});

    assert.equal(
      result.woke,
      true,
      `the walk must follow the genuinely focused pane into the target's tab: ${result.detail}`,
    );
    const callList = invoked(calls);
    assert.equal(
      callList.includes("pane edges --pane w7:p1Q"),
      false,
      `the walk must not be seeded from the attached tab's pane; calls:\n${callList.join("\n")}`,
    );
  });

  test("the walk refuses when pane focus claims success but pane get disagrees", async () => {
    const panes = {
      "wA:p1": { workspaceId: "wA", tabId: "wA:t1", label: "LEFT", focused: true },
      "wA:p2": { workspaceId: "wA", tabId: "wA:t1", label: "TARGET" },
    };
    const { runner, calls } = fakeRunner(panes, {
      attached: "wA:t1",
      focusedPaneId: "wA:p1",
    });
    // `pane focus` LIES: it claims to have landed on the target. The independent
    // `pane get` read must veto it, so the simulator is told NOT to confirm the landing.
    const wrapped = withWalkSimulation({ runner, calls }, {
      panes,
      seedId: "wA:p1",
      targetId: "wA:p2",
      neighborId: "wA:p2",
      confirmFocusOnLanding: false,
    });

    const result = await wakerFor(wrapped, { paneId: "wA:p2" })("civis", {});
    assert.equal(result.woke, false, `unconfirmed walk must not claim a wake: ${result.detail}`);
    assert.match(result.detail, /pane get reports/);
  });

  test("a hostile geometry seed is refused rather than walked from", async () => {
    // No pane reports focused, so the per-pane source cannot name a seed and the walk
    // falls back to `pane edges --current`. If that geometry fallback is handed a
    // flag-shaped id, walking from it would send `--json` into argv as an OPTION.
    const panes = { "wD:p2": { workspaceId: "wD", tabId: "wD:t1", label: "TARGET" } };
    const { runner, calls } = fakeRunner(panes, { attached: "wD:t1", focusedPaneId: "--json" });

    const result = await wakerFor(runner)("civis", {});

    assert.equal(result.woke, false, `a flag-shaped seed must not be walked from: ${result.detail}`);
    assert.match(result.detail, /could not determine the focused pane/);
    const callList = invoked(calls);
    assert.ok(
      !callList.some((c) => c.includes("--pane --json")),
      `the hostile seed must never reach argv; calls:\n${callList.join("\n")}`,
    );
  });

  test("an already-focused mapped pane is a real wake confirmed by both per-pane sources", async () => {
    const panes = {
      "w7:p1Q": { workspaceId: "w7", tabId: "w7:t1", label: "MUX" },
      "wD:p2": { workspaceId: "wD", tabId: "wD:t1", label: "TARGET", focused: true },
    };
    const { runner, calls } = fakeRunner(panes, {
      attached: "w7:t1",
      focusedPaneId: "wD:p2",
    });

    const result = await wakerFor(runner)("civis", {});
    assert.equal(result.woke, true, result.detail);
    assert.match(result.detail, /already focused/);
    const callList = invoked(calls);
    assert.ok(callList.includes("pane get wD:p2"), "must read the target's own focus state");
    assert.ok(callList.includes("pane list"), "must cross-check the machine-wide source");
  });
});
