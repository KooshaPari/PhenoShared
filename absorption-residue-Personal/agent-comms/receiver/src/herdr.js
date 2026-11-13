// The real wake: wake a recipient's mapped Herdr pane, and prove it or fail honestly.
//
// Ported from the proven reference implementation
// (harness-ops-bridge agent-comms receiver) and adapted to a recipient -> pane mapping.
// Verified against the live herdr CLI on 2026-10-17:
//
//   herdr pane focus --direction <left|right|up|down> [--pane <ID>]
//   herdr tab focus <TAB_ID>
//   herdr workspace focus <WORKSPACE_ID>
//   herdr pane list      -> {"result":{"panes":[{pane_id, tab_id, workspace_id, focused, ...}]}}
//   herdr pane edges --pane <ID> -> {"result":{"edges":{"left,right,up,down,layout:{panes:[{pane_id,rect,focused}]}}}}
//   herdr pane neighbor --pane <ID> --direction <D> -> {"result":{"neighbor":{"neighbor_pane_id":...}}}
//
// There is NO absolute "focus pane <ID>" verb, so reaching a pane is a path walk:
// focus its workspace, focus its tab, then step to it from the focused pane.
//
// FOCUS EVIDENCE (corrected 2026-10-18). Which source may back a "the target is focused"
// claim:
//   herdr pane get <ID>    AUTHORITATIVE for that pane. Reads that pane's own `focused` flag.
//   herdr pane list        AUTHORITATIVE machine-wide. Enumerates EVERY pane in EVERY
//                          workspace/tab with a per-pane `focused` flag; exactly one is true.
//   herdr pane edges --current   NOT authoritative for a focus CLAIM. It reports the ATTACHED
//                          UI tab, not programmatic focus.
//   herdr pane current     NOT authoritative; reports a different pane than the focused one.
//
// `--current` survives only as a FALLBACK geometry seed, used when the per-pane sources
// cannot name a single focused pane. It is never a focus claim. Every "focused" claim is
// gated on `pane get <target>`, cross-checked against `pane list`. If either disagrees, or
// reports nothing, the wake fails honestly.
//
// MODULE SPLIT. This file holds only the wake POLICY. Process transport is `herdr-cli.js`,
// and pane lookup/geometry is `herdr-panes.js`.

import { InvalidCliArgument, assertHerdrId, isValidHerdrId } from "./cli-args.js";
import { HerdrNotReachable, result, runHerdr } from "./herdr-cli.js";
import { focusedPaneIdFromList, paneIsFocused, selectPane, stepToward } from "./herdr-panes.js";

export { HerdrNotReachable, runHerdr };

/** Depth ceiling for the path walk. Bounds a cycle in herdr's geometry. */
const MAX_DEPTH = 48;

/**
 * A waker either wakes the pane (return true / target id) or reports honestly why not.
 * @typedef {(recipient: string, receipt: Record<string, any>) => Promise<{woke: boolean, detail: string, paneId?: string}>} Waker
 */

/**
 * Build the waker. `recipientMap` maps a recipient local part to a Herdr pane binding
 * (`{paneId, label?, agent?}`). A recipient with no entry can never be woken, and says so
 * instead of faking it.
 *
 * `runner` defaults to the real `herdr` CLI. Tests inject an in-memory fake so they exercise
 * the verification logic deterministically without spawning a process per herdr call.
 *
 * @param {{recipientMap: Record<string, {paneId?: string, label?: string, agent?: string}>, runner?: (args: string[]) => Promise<any>}} options
 * @returns {Waker}
 */
export function createHerdrWaker({ recipientMap, runner = runHerdr }) {
  /**
   * @param {string} recipient
   * @param {Record<string, any>} receipt
   */
  return async function wakeViaHerdr(recipient, receipt) {
    try {
      return await wakeUnchecked(recipient, recipientMap, runner);
    } catch (error) {
      if (error instanceof InvalidCliArgument) {
        // A handle we cannot vouch for means we cannot know WHICH pane the operator
        // meant. Refusing is the only honest answer, and it matches the module invariant:
        // never report a wake that was not independently confirmed.
        return { woke: false, detail: error.message };
      }
      throw error;
    }
  };
}

/**
 * The wake itself. Every value that becomes an argv token is asserted on the way in.
 *
 * @param {string} recipient
 * @param {Record<string, {paneId?: string, label?: string, agent?: string}>} recipientMap
 * @param {(args: string[]) => Promise<any>} runner
 * @returns {Promise<{woke: boolean, detail: string, paneId?: string}>}
 */
async function wakeUnchecked(recipient, recipientMap, runner) {
  const binding = recipientMap[recipient];
  if (!binding) {
    return { woke: false, detail: `no herdr pane bound to recipient ${recipient}` };
  }

  const listDoc = await runner(["pane", "list"]);
  const target = selectPane(listDoc, binding);
  if (!target) {
    return { woke: false, detail: `no herdr pane matched recipient ${recipient}` };
  }

  // 1. Focus the owning workspace so the tab/pane walk operates on the right screen.
  //    NOTE: herdr's `workspace focus` is not idempotent-stable (observed 2026-10-17:
  //    three consecutive calls to the same id landed on different workspaces), so it is
  //    treated as a nudge, never as evidence. Every focus claim below is re-read from a
  //    per-pane source.
  if (target.workspace_id) {
    await runner(["workspace", "focus", assertHerdrId("workspace id", target.workspace_id)]);
  }
  // 2. Focus the owning tab.
  if (target.tab_id) {
    await runner(["tab", "focus", assertHerdrId("tab id", target.tab_id)]);
  }

  // 3. Ask a PANE-SCOPED source whether the TARGET pane is focused. `pane get <target>`
  //    reads that pane's own `focused` flag, so it answers the question directly and is
  //    not scoped to the attached UI tab.
  const startFocus = await paneIsFocused(target.pane_id, runner);
  if (startFocus === undefined) {
    return { woke: false, detail: `herdr reported no focus state for pane ${target.pane_id}` };
  }
  if (startFocus) {
    // Independent confirmation: the machine-wide focused pane must also be the target.
    const focusedId = await focusedPaneIdFromList(runner);
    if (focusedId !== target.pane_id) {
      return {
        woke: false,
        detail:
          `pane get reports ${target.pane_id} focused but pane list reports ` +
          `${focusedId ?? "no single focused pane"}`,
      };
    }
    return { woke: true, detail: `pane ${target.pane_id} already focused`, paneId: target.pane_id };
  }

  // 4. Seed the walk from the MACHINE-WIDE focused pane, not from `pane edges --current`.
  //    `--current` remains only as a fallback when the per-pane sources cannot name a
  //    single focused pane. That is a best-effort geometry seed, never a focus claim.
  let current = await focusedPaneIdFromList(runner);
  if (!current) {
    const currentDoc = await runner(["pane", "edges", "--current"]);
    const fallback = result(currentDoc).edges?.layout?.focused_pane_id;
    // Same rule as the per-pane source: an id we cannot vouch for is not a seed. Treating
    // it as "unknown" keeps the two seed paths consistent -- both end in the honest
    // "could not determine" failure rather than walking from a handle we cannot trust.
    current = isValidHerdrId(fallback) ? fallback : undefined;
  }
  if (!current) {
    return { woke: false, detail: `could not determine the focused pane to walk from` };
  }
  if (current === target.pane_id) {
    // The seed already landed on the target; confirm per-pane before claiming.
    const confirmed = await paneIsFocused(target.pane_id, runner);
    if (confirmed === true) {
      return { woke: true, detail: `pane ${target.pane_id} already focused`, paneId: target.pane_id };
    }
    return {
      woke: false,
      detail: `pane ${target.pane_id} reported as the focused pane but pane get does not confirm`,
    };
  }

  // 5. Walk to it. `pane focus` returns {focus:{changed,focused_pane_id,layout}}, so each
  //    step's outcome comes from herdr itself rather than a second, racy query.
  for (let depth = 0; depth < MAX_DEPTH; depth++) {
    // `edgesResult` is {edges:{...},type}; the geometry lives under .edges.
    const edgesResult = result(await runner(["pane", "edges", "--pane", assertHerdrId("pane id", current)]));
    const layout = edgesResult.edges.layout;
    const targetRect = layout.panes.find((p) => p.pane_id === target.pane_id);
    if (!targetRect) {
      // Target is not in this layout (closed or moved); report honestly.
      return { woke: false, detail: `pane ${target.pane_id} not present in focused layout` };
    }

    const direction = await stepToward(edgesResult, current, targetRect, runner);
    if (!direction) {
      return { woke: false, detail: `no navigation path from ${current} to ${target.pane_id}` };
    }

    const focusDoc = await runner(["pane", "focus", "--pane", current, "--direction", direction]);
    const focus = result(focusDoc).focus;
    if (!focus || !focus.focused_pane_id) {
      return { woke: false, detail: `step ${direction} from ${current} focused nothing` };
    }
    if (focus.focused_pane_id === target.pane_id) {
      // Second gate: the step's own return says it landed on the target, but that is
      // herdr echoing the request. Confirm with an independent per-pane read before
      // claiming the wake, so a mis-scoped or stale layout cannot forge a success.
      const confirmed = await paneIsFocused(target.pane_id, runner);
      if (confirmed !== true) {
        return {
          woke: false,
          detail:
            `pane focus reported ${target.pane_id} but pane get reports ` +
            `${confirmed === undefined ? "no focus state" : "not focused"}`,
        };
      }
      return { woke: true, detail: `focused ${target.pane_id} in ${depth + 1} step(s)`, paneId: target.pane_id };
    }
    // Not there yet: keep walking toward the target. The next seed becomes argv on the
    // following iteration, so it is held to the same handle rule.
    current = assertHerdrId("pane id", focus.focused_pane_id);
  }
  return { woke: false, detail: `exceeded max depth ${MAX_DEPTH} without focusing ${target.pane_id}` };
}

/**
 * A waker that never wakes anything. Used in `--dry-run` so the transport can be proven
 * without moving the operator's panes.
 * @type {Waker}
 */
export const noopWaker = async (recipient) => ({
  woke: false,
  detail: `dry-run: no wake performed for ${recipient}`,
});
