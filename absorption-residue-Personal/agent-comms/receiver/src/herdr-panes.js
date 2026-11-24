// Pane sources and pane geometry: everything that asks herdr "which panes exist, which
// one is focused, and which way is the target" -- with no opinion about whether a wake
// should be reported. That decision lives in `herdr.js`.
//
// Every handle read here is checked before it can become an argv token; see `cli-args.js`.

import { assertHerdrDirection, assertHerdrId, isValidHerdrId } from "./cli-args.js";
import { result } from "./herdr-cli.js";

/** @typedef {"left"|"right"|"up"|"down"} Direction */

/**
 * Drop any pane whose handle could not be safely passed back to the CLI. A malformed
 * `pane_id` is removed from consideration rather than repaired, so the waker ends up
 * reporting "no pane matched" instead of navigating toward a handle we cannot vouch for.
 *
 * @param {any[]} panes
 * @returns {any[]}
 */
export function safePanes(panes) {
  return panes.filter((p) => p && typeof p === "object" && isValidHerdrId(p.pane_id));
}

/**
 * Find the pane bound to a recipient, preferring an explicit `paneId` and otherwise
 * falling back to `label` then `agent`. Deterministic tie-break on pane_id so repeated
 * wakes for the same recipient always target the same pane.
 *
 * @param {any} listDoc
 * @param {{paneId?: string, label?: string, agent?: string}} binding
 * @returns {any}
 */
export function selectPane(listDoc, binding) {
  const panes = safePanes(result(listDoc).panes ?? []);
  // An explicit pane binding is authoritative when that pane is present in the listing.
  if (binding.paneId) {
    const exact = panes.find((p) => p.pane_id === binding.paneId);
    if (exact) return exact;
  }
  const byLabel = binding.label ? panes.filter((p) => p.label === binding.label) : [];
  const pool = byLabel.length > 0 ? byLabel : panes.filter((p) => binding.agent && p.agent === binding.agent);
  if (pool.length === 0) return undefined;
  return [...pool].sort((a, b) => String(a.pane_id).localeCompare(String(b.pane_id)))[0];
}

/**
 * Read a pane's OWN `focused` boolean. This is the ONLY sound focus verdict for a specific
 * pane: `herdr pane get <ID>` looks that pane up directly, so it cannot be scoped to some
 * other tab the way `pane edges --current` is.
 *
 * @param {string} paneId
 * @param {(args: string[]) => Promise<any>} runner
 * @returns {Promise<boolean | undefined>} undefined when herdr did not report the flag.
 */
export async function paneIsFocused(paneId, runner) {
  // The handle came out of herdr's own JSON. Validate before it re-enters argv: herdr
  // parses that argv, so an unvalidated value could be read as a flag.
  assertHerdrId("pane id", paneId);
  const pane = result(await runner(["pane", "get", paneId])).pane;
  if (!pane || typeof pane.focused !== "boolean") return undefined;
  return pane.focused;
}

/**
 * The id of the single focused pane, read from `herdr pane list`. `pane list` enumerates
 * every pane across every workspace and tab with a per-pane `focused` flag, so exactly one
 * entry is focused machine-wide. Returns undefined when that is not unambiguous (zero or
 * more than one), because a focus claim we cannot pin down is not a focus claim.
 *
 * @param {(args: string[]) => Promise<any>} runner
 * @returns {Promise<string | undefined>}
 */
export async function focusedPaneIdFromList(runner) {
  const panes = safePanes(result(await runner(["pane", "list"])).panes ?? []);
  const focused = panes.filter((/** @type {any} */ p) => p?.focused === true);
  if (focused.length !== 1) return undefined;
  const focusedId = focused[0].pane_id;
  // Unambiguous is not yet trustworthy: confirm the id is safe before it becomes a seed.
  return isValidHerdrId(focusedId) ? focusedId : undefined;
}

/**
 * One step toward `target`, from `from`. Returns undefined when there is no such neighbor.
 *
 * `edgesResult` is the unwrapped `result()` of `herdr pane edges --pane <from>`, which is
 * `{edges:{down,layout,left,pane_id,right,up}, type}`. The geometry lives under `.edges`.
 *
 * @param {any} edgesResult  unwrapped edges RESULT (one level below the top-level envelope)
 * @param {string} from
 * @param {any} target  layout entry `{pane_id, rect}` for the destination
 * @param {(args: string[]) => Promise<any>} runner
 * @returns {Promise<string | undefined>}
 */
export async function stepToward(edgesResult, from, target, runner) {
  // Both endpoints become argv (`pane neighbor --pane <from>`, and the layout lookup for
  // the target), so neither may be anything other than a plain handle.
  assertHerdrId("pane id", from);
  assertHerdrId("pane id", target.pane_id);
  const edges = edgesResult.edges;
  const t = target.rect;
  const f = edges.layout.panes.find((p) => p.pane_id === from)?.rect;
  if (!f) return undefined;

  // Prefer the axis with the larger center distance so we do not crawl along the long edge.
  const horizontal = Math.abs(t.x + t.width / 2 - (f.x + f.width / 2));
  const vertical = Math.abs(t.y + t.height / 2 - (f.y + f.height / 2));
  const order = /** @type {Direction[]} */ (
    horizontal >= vertical ? ["left", "right", "up", "down"] : ["up", "down", "left", "right"]
  );

  // Ask herdr which pane actually lies in each direction. The `edges.<dir>` booleans are
  // NOT trustworthy (observed 2026-10-17: edges.right was false while `pane neighbor
  // --direction right` correctly returned the pane to the right), so every direction is
  // probed and an empty probe simply means "no pane that way".
  /** @type {Array<{direction: Direction, id: string, rect: any}>} */
  const reachable = [];
  for (const direction of order) {
    const neighborDoc = await runner(["pane", "neighbor", "--pane", from, "--direction", direction]);
    const neighbor = result(neighborDoc).neighbor;
    if (!neighbor || !neighbor.neighbor_pane_id) continue;
    // The neighbour id is recorded for evidence and can become the next seed, so it is
    // held to the same rule as any other handle.
    if (!isValidHerdrId(neighbor.neighbor_pane_id)) continue;
    const rect = neighbor.layout?.panes?.find((p) => p.pane_id === neighbor.neighbor_pane_id)?.rect;
    reachable.push({ direction, id: neighbor.neighbor_pane_id, rect });
    if (neighbor.neighbor_pane_id === target.pane_id) return direction;
  }

  // Take the step that most reduces the center distance. This converges in one step for an
  // immediate neighbor and never walks away from the target.
  const cx = (r) => r.x + r.width / 2;
  const cy = (r) => r.y + r.height / 2;
  let best;
  let bestScore = Infinity;
  for (const option of reachable) {
    if (!option.rect) continue;
    const score =
      Math.abs(cx(option.rect) - cx(t)) + Math.abs(cy(option.rect) - cy(t));
    if (score < bestScore) {
      bestScore = score;
      best = option;
    }
  }
  // Nothing moves us closer, so there is genuinely no path along this direction set.
  if (!best) return undefined;
  return assertHerdrDirection(best.direction);
}
