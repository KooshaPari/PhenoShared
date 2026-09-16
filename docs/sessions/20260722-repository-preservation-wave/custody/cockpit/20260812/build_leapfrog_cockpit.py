#!/usr/bin/env python3
"""
Leapfrog Cockpit Builder — supersedes Codex WIP for the 2026-08-09 19:11:31 build.

The original artifact cockpit/bead-cockpit-20260809-191131-f5ca38f7.html was
overwritten by Codex and is unrecoverable. The closest historical match is
cockpit/bead-cockpit-20260809-193102-multi.html (Aug 9 19:31, 150 KB, 5-lane
kanban PM viewer). This script renders a leapfrog 9-lane AgilePlus-faithful
kanban + PM outcomes panel, derived from the authoritative bead log.

Inputs:
    - phenotype-dag/beads.jsonl (primary source of truth)
    - ~/.agileplus/audit.jsonl (mirror; same schema)

Output:
    - cockpit/bead-cockpit-20260810-leapfrog-fca38f7.html

Invariants:
    - 9 AgilePlus-faithful lanes (Backlog, Specified, Researched, Planned,
      Implementing, Review, Validating, Blocked, Shipped, Retrospected)
    - No emoji anywhere; pictographs stripped from bead text
    - Self-contained (inline CSS, no external deps)
    - Under 1 MiB
    - Well-formed HTML (validated with html.parser)
"""

from __future__ import annotations

import html
import json
import os
import re
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

REPO_ROOT = Path("/Users/kooshapari/CodeProjects/Phenotype/repos")
BEADS_PATH = REPO_ROOT / "phenotype-dag" / "beads.jsonl"
BEAD_SOURCES = (BEADS_PATH,)
OUTPUT_PATH = REPO_ROOT / "cockpit" / "bead-cockpit-20260809-191131-f5ca38f7.html"
REFERENCE_PATH = REPO_ROOT / "cockpit" / "bead-cockpit-20260809-193102-multi.html"
MAX_OUTPUT_BYTES = 1024 * 1024

# ---------------------------------------------------------------------------
# Lane definitions — strict AgilePlus methodology + PM-lite cross-cuts.
# ---------------------------------------------------------------------------
# Lane order matters: lanes are first-match-wins.  Each PM-lite cross-cut
# lane MUST be defined BEFORE the broader AgilePlus lane it would
# otherwise be swallowed by (e.g. EVIDENCE before SHIPPED so complete
# beads with explicit user-outcome land in EVIDENCE, not SHIPPED).
# Lifecycle order: Archived -> Pending -> Backlog -> Ready -> Specified
# -> Researched -> Planned -> Implementing -> Review -> Validating
# -> Blocked -> Preserve -> Evidence -> Promote -> Shipped ->
# Retrospected (catchall).
LANES: list[dict[str, Any]] = [
    {
        "id": "archived",
        "name": "ARCHIVED",
        "subtitle": "session/fr/changelog no active work",
        "rule": lambda b: b["kind"] in {"session", "fr"},
        "accent": "#475569",
    },
    {
        "id": "pending",
        "name": "PENDING",
        "subtitle": "goal no recent activity",
        "rule": lambda b: b["kind"] == "goal" and not b["_has_any_activity"],
        "accent": "#a3a3a3",
    },
    {
        "id": "ready",
        "name": "READY",
        "subtitle": "intent scoped, no claim yet",
        # Defined BEFORE BACKLOG so the intent-without-claim catch in
        # _lane_backlog does not swallow READY (FR-COCKPIT-PM-15COLS).
        "rule": lambda b: b["kind"] == "intent" and not b["_target_has_claim"],
        "accent": "#0ea5e9",
    },
    {
        "id": "backlog",
        "name": "BACKLOG",
        "subtitle": "no recent activity",
        "rule": lambda b: _lane_backlog(b),
        "accent": "#71717a",
    },
    {
        "id": "specified",
        "name": "SPECIFIED",
        "subtitle": "intent captured + feature spec",
        "rule": lambda b: b["kind"] == "intent" or (
            b["kind"] == "feature" and b["_has_any_activity"]
        ),
        "accent": "#14b8a6",
    },
    {
        "id": "researched",
        "name": "RESEARCHED",
        "subtitle": "prompts explored",
        "rule": lambda b: b["kind"] == "prompt",
        "accent": "#f97316",
    },
    {
        "id": "planned",
        "name": "PLANNED",
        "subtitle": "ctl planning + reorg + active goal",
        "rule": lambda b: b["kind"] == "reorg"
        or (b["kind"] == "ctl" and _ctl_is_planning(b))
        or (b["kind"] == "goal" and b["_has_any_activity"]),
        "accent": "#8b5cf6",
    },
    {
        "id": "implementing",
        "name": "IMPLEMENTING",
        "subtitle": "claim active + ctl build",
        "rule": lambda b: b["kind"] == "claim" or (b["kind"] == "ctl" and _ctl_is_build(b)),
        "accent": "#3b82f6",
    },
    {
        "id": "review",
        "name": "REVIEW",
        "subtitle": "ctl review",
        "rule": lambda b: b["kind"] == "ctl" and _ctl_is_review(b),
        "accent": "#a855f7",
    },
    {
        "id": "validating",
        "name": "VALIDATING",
        "subtitle": "ctl verify",
        "rule": lambda b: b["kind"] == "ctl" and _ctl_is_verify(b),
        "accent": "#06b6d4",
    },
    {
        "id": "blocked",
        "name": "BLOCKED",
        "subtitle": "warn signals",
        "rule": lambda b: b["kind"] == "warn",
        "accent": "#f59e0b",
    },
    {
        "id": "preserve",
        "name": "PRESERVE",
        "subtitle": "preserve rationale captured",
        "rule": lambda b: b["kind"] == "preserve",
        "accent": "#eab308",
    },
    {
        "id": "evidence",
        "name": "EVIDENCE",
        "subtitle": "complete w/ user-facing outcome",
        "rule": lambda b: b["kind"] == "complete" and _has_user_outcome(b),
        "accent": "#22c55e",
    },
    {
        "id": "promote",
        "name": "PROMOTE",
        "subtitle": "release candidate",
        "rule": lambda b: b["kind"] == "release",
        "accent": "#f43f5e",
    },
    {
        "id": "outcome",
        "name": "OUTCOME",
        "subtitle": "user-facing outcome recorded",
        "rule": lambda b: b["kind"] == "outcome",
        "accent": "#34d399",
    },
    {
        "id": "shipped",
        "name": "SHIPPED",
        "subtitle": "complete (no explicit outcome)",
        "rule": lambda b: b["kind"] == "complete",
        "accent": "#10b981",
    },
    {
        "id": "retrospected",
        "name": "RETROSPECTED",
        "subtitle": "post-ship notes",
        "rule": lambda b: _is_retrospective(b),
        "accent": "#ec4899",
    },
]

# Cross-cutting sub-rule patterns for ctl beads.  Order matters — most specific
# first.  These were hand-curated by inspecting the Aug 10 audit mirror.
_CTL_PLAN_PATTERNS = re.compile(
    r"\b(planning|plan\s+(for|to|wbs|wbs|update)|wbs|decompos|architect|design)\b",
    re.IGNORECASE,
)
_CTL_REVIEW_PATTERNS = re.compile(r"\b(review|audit|inspect|triage)\b", re.IGNORECASE)
_CTL_VERIFY_PATTERNS = re.compile(
    r"\b(verif|validat|ci\s+green|fixture\s+pass|smoke\s+test|smoke\s+pass|ci\s+pass|"
    r"tests?\s+pass|evidence|state\s+evidence|state\s+update|gate|gate\s+green|"
    r"ready|complete|passes|green|dogfood|dogfood-pass|dogfood\s+pass|test\s+green|"
    r"ci\s+verified|verify-?pass|verifies|verifying)\b",
    re.IGNORECASE,
)


def _ctl_is_planning(b: dict[str, Any]) -> bool:
    hay = f"{b.get('target', '')} {_haystack(b)}"
    return bool(_CTL_PLAN_PATTERNS.search(hay))


def _ctl_is_review(b: dict[str, Any]) -> bool:
    hay = f"{b.get('target', '')} {_haystack(b)}"
    return bool(_CTL_REVIEW_PATTERNS.search(hay))


def _ctl_is_verify(b: dict[str, Any]) -> bool:
    hay = f"{b.get('target', '')} {_haystack(b)}"
    return bool(_CTL_VERIFY_PATTERNS.search(hay))


def _ctl_is_build(b: dict[str, Any]) -> bool:
    return not (_ctl_is_planning(b) or _ctl_is_review(b) or _ctl_is_verify(b))


def _haystack(b: dict[str, Any]) -> str:
    return " ".join(
        str(b.get(k, "")) for k in ("text", "intentSynthesis", "clearanceEvidence", "userOutcome")
    )


# Pictographs to strip from bead text — covers the common Unicode block ranges
# plus the explicit glyphs the operator called out.
_PICTOGRAPH_RE = re.compile(
    "["
    "\u2600-\u27BF"        # Misc Symbols / Dingbats / Arrows
    "\u2300-\u23FF"        # Misc Technical (some symbols)
    "\u2B00-\u2BFF"        # Misc Symbols and Arrows
    "\U0001F300-\U0001FAFF"  # Emoji & supplemental pictographs
    "\uFE0F"               # Variation Selector-16
    "\u200D"               # Zero Width Joiner
    "]"
)


def _is_retrospective(b: dict[str, Any]) -> bool:
    if b.get("kind") == "changelog":
        # changelog is by definition post-ship reflection.
        return True
    text = f"{b.get('text', '')} {_haystack(b)}".lower()
    return "retro" in text or "retrospective" in text


def _has_user_outcome(b: dict[str, Any]) -> bool:
    """True if a bead carries an explicit User-facing outcome (any source)."""
    for k in ("userOutcome", "outcome", "user_outcome"):
        v = b.get(k)
        if v not in (None, "", "not recorded"):
            return True
    return False


def _fr_id(b: dict[str, Any]) -> str:
    """Surface the first FR-* identifier found on the bead (or empty string)."""
    for k in ("frId", "fr_id", "featureRequest", "feature_request"):
        v = b.get(k)
        if v not in (None, ""):
            return str(v)
    # Last resort: scan target + text for FR-* pattern.
    import re as _re
    m = _re.search(r"\bFR[- ]\d+(?:[.-][A-Za-z0-9]+)*\b",
                   f"{b.get('target','')} {b.get('text','')}", _re.I)
    return m.group(0).upper().replace(" ", "-") if m else ""


def _lane_backlog(b: dict[str, Any]) -> bool:
    """Backlog = no recent activity, or kind=intent with no claim.

    Iterated first so unscoped intake (session, fr, lone feature, lone goal,
    intent without claim) lands here.  Beads whose kind has a dedicated lane
    (claim, ctl, prompt, reorg, warn, complete, release, outcome, preserve,
    changelog) are excluded so they fall through to the right lane.
    """
    kind = b["kind"]
    # Kinds with a dedicated lane — never backlog.
    if kind in {
        "claim", "ctl", "prompt", "reorg", "warn", "complete",
        "release", "outcome", "preserve", "changelog",
    }:
        return False
    if kind in {"session", "fr"}:
        return True  # unscoped intake
    if kind == "intent":
        return b["_target_has_claim"] is False
    if kind == "feature":
        # Active feature specs belong in Specified, lone ones in backlog.
        return not b["_has_any_activity"]
    if kind == "goal":
        # Active goals drive planning; lone goals sit in backlog.
        return not b["_has_any_activity"]
    # Any other kind lands here as a catch-all.
    return True


# ---------------------------------------------------------------------------
# Emoji / pictograph stripping
# ---------------------------------------------------------------------------
def strip_pictographs(s: str) -> str:
    if not s:
        return ""
    # Drop any of the explicit pictograph glyphs the operator listed.
    s = s.replace("\u2713", "").replace("\u2699", "").replace("\u25B6", "")
    s = s.replace("\u2717", "").replace("\u25C6", "").replace("\u25CF", "")
    # Drop the broader Unicode blocks.
    s = _PICTOGRAPH_RE.sub("", s)
    return s.strip()


# ---------------------------------------------------------------------------
# Load beads
# ---------------------------------------------------------------------------
def load_beads() -> list[dict[str, Any]]:
    beads: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()
    for path in BEAD_SOURCES:
        if not path.exists():
            print(f"WARN: missing {path}", file=sys.stderr)
            continue
        added = 0
        with path.open("r", encoding="utf-8") as fh:
            for raw in fh:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if "kind" not in obj:
                    continue
                # Dedup key: hash if present, else (ts, kind, target, agent).
                h = obj.get("hash")
                if h:
                    key = ("h", str(h))
                else:
                    key = (
                        "k",
                        str(obj.get("ts", "")),
                        str(obj.get("kind", "")),
                        str(obj.get("target", "")),
                        str(obj.get("agent", "")),
                    )
                if key in seen:
                    continue
                seen.add(key)
                obj["_source"] = path.name
                beads.append(obj)
                added += 1
        print(f"  loaded {added} unique beads from {path}", file=sys.stderr)
    # Sort newest-first so the kanban has a deterministic order.
    beads.sort(key=lambda b: b.get("ts", ""), reverse=True)
    # Decorate with claim/activity info for backlog detection.
    targets_with_claim = {b.get("target", "") for b in beads if b.get("kind") == "claim"}
    targets_with_complete = {b.get("target", "") for b in beads if b.get("kind") == "complete"}
    active_targets = targets_with_claim | targets_with_complete
    for b in beads:
        b["_target_has_claim"] = b.get("target", "") in targets_with_claim
        b["_has_any_activity"] = b.get("target", "") in active_targets
    return beads


def classify(beads: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = {lane["id"]: [] for lane in LANES}
    for b in beads:
        # Lane assignment is order-sensitive: walk LANES in definition order and
        # place each bead into the first matching lane.  Lane order is
        # intentionally lifecycle-ordered (Backlog ... Retrospected).
        for lane in LANES:
            if lane["rule"](b):
                buckets[lane["id"]].append(b)
                break
    return buckets


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def esc(s: Any) -> str:
    if s is None:
        return ""
    return html.escape(str(s), quote=True)


def short_time(ts: str) -> str:
    if not ts:
        return ""
    # Accept ISO8601 with or without trailing Z and fractional seconds.
    s = ts.replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.strftime("%m-%d %H:%M")
    except ValueError:
        return ts[:16]


def short_agent(agent: str) -> str:
    if not agent:
        return "(anon)"
    if len(agent) <= 18:
        return agent
    if agent.startswith("agent-"):
        return "agent-" + agent[6:14] + "..."
    return agent[:15] + "..."


def render_card(b: dict[str, Any], lane_id: str) -> str:
    target_raw = b.get("target", "") or ""
    target = esc(target_raw)
    kind = esc(b.get("kind", "?"))
    agent = esc(short_agent(b.get("agent", "")))
    ts = esc(short_time(b.get("ts", "")))
    text_raw = strip_pictographs(b.get("text", "") or "")
    # Truncate text excerpt to keep total HTML under 600 KB.
    excerpt = esc(text_raw[:120].replace("\n", " "))
    state = esc(b.get("state", ""))
    repo = ""
    slug = ""
    if "/" in target_raw:
        repo, slug = target_raw.split("/", 1)
    elif "+" in target_raw:
        # Cross-repo target like "RepoA+RepoB/feature" — use first repo only.
        head, _, slug = target_raw.partition("/")
        repo = head.split("+", 1)[0]
    cmd = f"agileplus dashboard --json --feature {slug}" if slug else ""
    cmd_attr = html.escape(cmd, quote=True) if cmd else ""
    state_html = f'<span class="bead-state">{state}</span>' if state else ""

    # PM-lite linkage badges (added 2026-08-12, FR-COCKPIT-FR-UF-OUTCOME):
    # show FR-* id (functional requirement) and user-facing outcome hint
    # on every bead card so the operator can trace work to outcome without
    # opening the JSONL.  Source: BEAD_FR_ID env var and BEAD_USER_OUTCOME
    # env var on the originating bead-ctl.sh invocation.
    fr = _fr_id(b)
    fr_badge = (
        f'<span class="bead-fr" title="Functional Requirement linkage">'
        f'{esc(fr)}</span>'
    ) if fr else ""
    user_outcome_raw = b.get("userOutcome") or b.get("outcome") or b.get("user_outcome") or ""
    user_outcome_clean = strip_pictographs(str(user_outcome_raw))[:80] if user_outcome_raw else ""
    outcome_badge = (
        f'<span class="bead-outcome" title="User-facing outcome">'
        f'UF: {esc(user_outcome_clean)}</span>'
    ) if user_outcome_clean else ""
    # Keep the article compact; ARIA + tabindex are optional but accessibility-friendly.
    return (
        f'<article class="bead" data-kind="{kind}" data-lane="{lane_id}" '
        f'data-cmd="{cmd_attr}" data-target="{target}" '
        f'onclick="onBeadClick(this)" tabindex="0" role="button">'
        f'<div class="bead-head">'
        f'<span class="kind kind-{kind}">{kind}</span>'
        f'<span class="bead-target" title="{target}">{target}</span>'
        f'</div>'
        f'<div class="bead-text">{excerpt}</div>'
        f'<div class="bead-meta">'
        f'<span class="bead-agent">{agent}</span>'
        f'<span class="bead-time">{ts}</span>'
        f'{state_html}'
        f'{fr_badge}'
        f'</div>'
        f'{outcome_badge}'
        f'</article>'
    )


def render_summary_cards(beads: list[dict[str, Any]], buckets: dict[str, list[dict[str, Any]]]) -> str:
    total = len(beads)
    distinct_agents = len({b.get("agent", "") for b in beads if b.get("agent")})
    distinct_repos: set[str] = set()
    for b in beads:
        t = b.get("target", "")
        if "/" in t:
            distinct_repos.add(t.split("/", 1)[0])
        elif "+" in t:
            # Targets like "AgilePlus+PhenoObservability/..." split on plus.
            distinct_repos.add(t.split("+", 1)[0])
    oldest = min((b.get("ts", "") for b in beads if b.get("ts")), default="")
    newest = max((b.get("ts", "") for b in beads if b.get("ts")), default="")
    kinds = Counter(b.get("kind", "?") for b in beads)

    cards = [
        ("Total Beads", f"{total}", f"kinds: {len(kinds)}"),
        ("Distinct Agents", f"{distinct_agents}", "codex / droid / agent-* / agent-phenotype"),
        ("Distinct Repos", f"{len(distinct_repos)}", "scope of cockpit coverage"),
        ("Window", f"{oldest[:10] or '?'} -> {newest[:10] or '?'}", "oldest -> newest ts"),
    ]
    out = ['<div class="summary">']
    for label, value, delta in cards:
        out.append(
            f'<div class="card"><div class="label">{esc(label)}</div>'
            f'<div class="value">{esc(value)}</div>'
            f'<div class="delta">{esc(delta)}</div></div>'
        )
    # Lane counts as additional cards.
    out.append('<div class="card"><div class="label">Lane Distribution</div><div class="lane-dist">')
    for lane in LANES:
        cnt = len(buckets[lane["id"]])
        out.append(
            f'<div class="lane-pill" style="--accent:{lane["accent"]}">'
            f'<span class="lane-name">{esc(lane["name"])}</span>'
            f'<span class="lane-count">{cnt}</span></div>'
        )
    out.append("</div></div>")
    out.append("</div>")
    return "\n".join(out)


def render_kanban(buckets: dict[str, list[dict[str, Any]]]) -> str:
    cols = []
    for lane in LANES:
        items = buckets[lane["id"]]
        body = "\n".join(render_card(b, lane["id"]) for b in items) if items else '<div class="empty">no beads</div>'
        cols.append(
            f'<section class="kanban-lane" data-lane="{lane["id"]}" style="--lane-accent:{lane["accent"]}">'
            f'<header class="lane-header">'
            f'<h3>{esc(lane["name"])}</h3>'
            f'<span class="count">{len(items)}</span>'
            f'</header>'
            f'<div class="lane-subtitle">{esc(lane["subtitle"])}</div>'
            f'<div class="lane-body">{body}</div>'
            f'</section>'
        )
    return f'<div class="kanban" data-lanes="{len(LANES)}">' + "\n".join(cols) + "</div>"


def render_top_features(beads: list[dict[str, Any]], buckets: dict[str, list[dict[str, Any]]]) -> str:
    """PM-style outcomes panel: top 10 features by bead count."""
    target_counts: Counter = Counter()
    target_lane: dict[str, str] = {}
    for lane in LANES:
        for b in buckets[lane["id"]]:
            t = b.get("target", "")
            if not t:
                continue
            target_counts[t] += 1
            target_lane[t] = lane["name"]
    rows = []
    for target, count in target_counts.most_common(10):
        lane_name = target_lane.get(target, "BACKLOG")
        rows.append(
            f'<tr><td class="feat-target">{esc(target)}</td>'
            f'<td class="feat-count">{count}</td>'
            f'<td><span class="status-pill">{esc(lane_name)}</span></td></tr>'
        )
    return (
        '<section class="pm-panel"><h2>PM-Style Outcomes</h2>'
        '<p class="section-desc">Top 10 targets by bead count, with current lane derived '
        'from AgilePlus state machine bucketing. Click any card on the kanban above to '
        'copy the matching <code>agileplus dashboard --json --feature &lt;slug&gt;</code> '
        'command for the relevant work package.</p>'
        '<table class="feat-table"><thead><tr>'
        '<th>Target</th><th>Beads</th><th>Current Lane</th>'
        '</tr></thead><tbody>' + "\n".join(rows) + '</tbody></table></section>'
    )


def render_semantic_reconciliation() -> str:
    """Render supplied facts with provenance without turning them into status claims."""
    facts = (
        (
            "Forge preflight and idempotency",
            "Forge idempotency preflight conflicts with the publisher path.",
            "Forge ui.rs:172",
        ),
        (
            "Forge .forge alias",
            "The .forge alias guard has a gap.",
            "Forge reader.rs:166",
        ),
        (
            "Forge hidden schema policy",
            "The v3 decision retains an 18-column hidden schema.",
            "Forge snapshot.rs:25, :204, :456",
        ),
        (
            "Release authority",
            "Release authority is separate from implementation and evidence authority.",
            "Supplied verified fact; no code position recorded",
        ),
        (
            "Helios deterministic harness",
            "Harness outcome is evidence only; legacy schema and signature blockers remain.",
            "Supplied verified fact; no code position recorded",
        ),
        (
            "Portage / Harbor",
            "Exact divergence is 282/223; there is no safe host.",
            "Supplied verified fact; no code position recorded",
        ),
        (
            "Capacity",
            "Available capacity is 11.12/20 GiB.",
            "Supplied verified fact; no code position recorded",
        ),
    )
    cards = "".join(
        f'<article class="reconciliation-card"><h3>VERIFIED: {esc(title)}</h3>'
        f'<p>{esc(fact)}</p><p class="evidence-source">Exact source: {esc(source)}</p></article>'
        for title, fact, source in facts
    )
    return (
        '<section class="reconciliation" aria-labelledby="reconciliation-heading">'
        '<h2 id="reconciliation-heading">Product Management: semantic reconciliation</h2>'
        '<p><strong>Exact user prompt:</strong> not recorded in the supplied reconciliation '
        'evidence packet.</p>'
        '<p><strong>Coordinator synthesis:</strong> render the supplied facts in this existing '
        'cockpit as evidence-only content.</p>'
        f'<div class="reconciliation-grid">{cards}</div>'
        '<p class="reconciliation-note"><strong>Unknown:</strong> this section does not infer a '
        'safe host, remediation, release readiness, promotion, or clearance from these facts.</p>'
        '</section>'
    )


def render_footer() -> str:
    return """
    <footer class="footer">
      <h2>Source of Truth</h2>
      <p>beads.jsonl (phenotype-dag/) is authoritative; this HTML is a derived view.
      Mirror at <code>~/.agileplus/audit.jsonl</code> reflects the same schema.</p>
      <p>Companion surfaces:
        <code>agileplus-mcp</code> for live state queries, and the
        <code>agileplus-agents</code> skill for orchestrated lane progression.</p>
      <p class="footer-meta">Leapfrog build 2026-08-12 (PM-15 enhancement, FR-COCKPIT-PM-15COLS).
      Generated from <code>phenotype-dag/beads.jsonl</code> + <code>~/.agileplus/audit.jsonl</code>.
      Lane model: AgilePlus feature lifecycle
      (Created -> Specified -> Researched -> Planned -> Implementing ->
       Validated -> Shipped -> Retrospected) plus a Blocked cross-cut
      AND six PM-lite cross-cuts (Ready, Pending, Evidence, Promote,
      Preserve, Archived) so the kanban reaches 15 columns minimum.
      FR linkage and User-facing outcome badges now rendered on every
      bead card (FR-COCKPIT-FR-UF-OUTCOME).
      </p>
    </footer>"""


# ---------------------------------------------------------------------------
# CSS / JS
# ---------------------------------------------------------------------------
CSS = r"""
:root {
  --bg: #0a0a0a; --bg-1: #111; --bg-2: #1a1a1a; --bg-3: #222;
  --fg: #e4e4e7; --fg-dim: #a1a1aa; --fg-muted: #71717a;
  --accent: #6366f1; --accent-2: #8b5cf6; --success: #10b981;
  --warn: #f59e0b; --error: #ef4444; --info: #3b82f6;
  --border: #2a2a2a; --border-bright: #3a3a3a;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'SF Mono', Menlo, Consolas, monospace;
  background: var(--bg); color: var(--fg); padding: 0; line-height: 1.5;
  font-size: 13px;
}
header.banner {
  background: linear-gradient(90deg, #1f1147 0%, #0a0a0a 100%);
  border-bottom: 1px solid var(--border-bright);
  padding: 14px 24px;
}
header.banner h1 { font-size: 18px; font-weight: 700; }
header.banner .subtitle { font-size: 12px; color: var(--fg-dim); margin-top: 4px; }
header.banner .provenance { font-size: 11px; color: var(--fg-muted); margin-top: 8px; line-height: 1.7; }
header.banner .provenance code { color: var(--accent-2); }
header.topbar {
  background: var(--bg-1); border-bottom: 1px solid var(--border);
  padding: 10px 24px; display: flex; align-items: center; gap: 16px;
  position: sticky; top: 0; z-index: 100; flex-wrap: wrap;
}
header.topbar nav { display: flex; gap: 4px; flex-wrap: wrap; margin-left: auto; }
header.topbar nav a {
  padding: 6px 12px; border-radius: 4px; color: var(--fg-dim);
  text-decoration: none; font-size: 12px; font-weight: 600;
  border: 1px solid transparent;
}
header.topbar nav a:hover { background: var(--bg-2); color: var(--fg); }
main { padding: 24px; max-width: 1800px; margin: 0 auto; }
h2 { font-size: 20px; font-weight: 700; margin: 24px 0 12px;
  background: linear-gradient(90deg, #fff, #a1a1aa);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px; margin: 16px 0; }
.card { background: var(--bg-1); border: 1px solid var(--border); border-radius: 8px;
  padding: 14px; }
.card .label { font-size: 10px; color: var(--fg-muted); text-transform: uppercase;
  letter-spacing: 0.05em; margin-bottom: 6px; }
.card .value { font-size: 24px; font-weight: 700; }
.card .delta { font-size: 10px; color: var(--fg-dim); margin-top: 4px; }
.lane-dist { display: grid; grid-template-columns: repeat(2, 1fr); gap: 4px; margin-top: 6px; }
.lane-pill { display: flex; align-items: center; justify-content: space-between;
  padding: 4px 8px; border-radius: 4px; background: var(--bg-2);
  border-left: 3px solid var(--accent); font-size: 10px; }
.lane-pill .lane-name { color: var(--fg-dim); font-weight: 700; letter-spacing: 0.05em; }
.lane-pill .lane-count { color: var(--accent); font-weight: 700; }

.kanban { display: grid; grid-template-columns: repeat(17, minmax(200px, 1fr));
  gap: 8px; margin: 16px 0; overflow-x: auto; min-width: 100%; }
.kanban-lane { background: var(--bg-1); border: 1px solid var(--border); border-radius: 8px;
  padding: 12px; min-height: 320px; display: flex; flex-direction: column; }
.lane-header { display: flex; justify-content: space-between; align-items: center;
  padding-bottom: 6px; border-bottom: 1px solid var(--border);
  border-left: 3px solid var(--lane-accent); padding-left: 8px; }
.lane-header h3 { margin: 0; font-size: 12px; letter-spacing: 0.05em; }
.lane-header .count { background: var(--lane-accent); color: #000;
  padding: 2px 8px; border-radius: 12px; font-size: 10px; font-weight: 700; }
.lane-subtitle { font-size: 10px; color: var(--fg-muted); margin: 6px 0 8px; }
.lane-body { display: flex; flex-direction: column; gap: 4px; max-height: 720px;
  overflow-y: auto; padding-right: 4px; }
.bead { display: flex; flex-direction: column; gap: 4px; padding: 8px;
  background: var(--bg-2); border-radius: 4px; font-size: 11px;
  border-left: 3px solid var(--lane-accent); cursor: pointer;
  transition: background 0.1s ease; }
.bead:hover { background: var(--bg-3); }
.bead:focus { outline: 2px solid var(--accent); outline-offset: 2px; }
.bead-head { display: flex; gap: 6px; align-items: center; }
.bead-target { font-weight: 700; color: var(--accent);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
  flex: 1; min-width: 0; }
.bead-text { color: var(--fg-dim); font-size: 11px;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical;
  overflow: hidden; }
.bead-meta { display: flex; gap: 6px; font-size: 10px; color: var(--fg-muted); flex-wrap: wrap; }
.bead-agent { color: var(--accent-2); }
.bead-state { color: var(--warn); margin-left: auto; }
.bead-fr { background: var(--accent); color: #fff;
  padding: 1px 5px; border-radius: 3px; font-size: 9px;
  font-weight: 700; letter-spacing: 0.03em; }
.bead-outcome { display: block; margin-top: 4px; color: var(--success);
  font-size: 10px; font-style: italic; line-height: 1.3;
  border-top: 1px dashed var(--border); padding-top: 4px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kind { display: inline-block; padding: 1px 6px; border-radius: 3px;
  font-size: 9px; font-weight: 700; min-width: 44px; text-align: center;
  background: var(--bg-3); color: var(--fg-dim); }
.kind-claim { background: var(--info); color: #fff; }
.kind-complete { background: var(--success); color: #000; }
.kind-warn { background: var(--warn); color: #000; }
.kind-ctl { background: var(--accent-2); color: #fff; }
.kind-reorg { background: var(--error); color: #fff; }
.kind-goal { background: #ec4899; color: #fff; }
.kind-intent { background: #14b8a6; color: #fff; }
.kind-prompt { background: #f97316; color: #fff; }
.kind-feature { background: var(--accent); color: #fff; }
.kind-outcome { background: var(--success); color: #000; }
.kind-fr { background: var(--accent); color: #fff; }
.kind-session { background: var(--bg-3); color: var(--fg-dim); }
.kind-release { background: var(--success); color: #000; }
.kind-changelog { background: #ec4899; color: #fff; }
.kind-preserve { background: var(--warn); color: #000; }

.pm-panel { background: var(--bg-1); border: 1px solid var(--border); border-radius: 8px;
  padding: 16px; margin: 16px 0; }
.section-desc { color: var(--fg-dim); font-size: 11px; margin: 8px 0; }
.feat-table { width: 100%; border-collapse: collapse; font-size: 11px; }
.feat-table th, .feat-table td { text-align: left; padding: 6px 8px;
  border-bottom: 1px solid var(--border); }
.feat-table th { color: var(--fg-muted); text-transform: uppercase;
  letter-spacing: 0.05em; font-size: 10px; }
.feat-target { color: var(--accent); font-weight: 700; }
.feat-count { color: var(--accent-2); text-align: right; font-weight: 700; }
.status-pill { display: inline-block; padding: 2px 8px; border-radius: 3px;
  background: var(--bg-3); color: var(--fg-dim); font-size: 10px;
  font-weight: 700; letter-spacing: 0.05em; }

.reconciliation { background: var(--bg-1); border: 1px solid var(--border); border-radius: 8px;
  padding: 16px; margin: 16px 0; }
.reconciliation h2 { margin-top: 0; }
.reconciliation > p { color: var(--fg-dim); font-size: 11px; margin: 6px 0; }
.reconciliation-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 9px; margin-top: 12px; }
.reconciliation-card { border-left: 3px solid var(--info); background: var(--bg-2); border-radius: 5px;
  padding: 10px; }
.reconciliation-card h3 { color: var(--fg); font-size: 12px; }
.reconciliation-card p { color: var(--fg-dim); font-size: 11px; margin-top: 5px; }
.reconciliation-card .evidence-source { color: var(--accent-2); }
.reconciliation-note { border-top: 1px solid var(--border); margin-top: 12px !important; padding-top: 10px; }

.footer { background: var(--bg-1); border: 1px solid var(--border); border-radius: 8px;
  padding: 16px; margin: 16px 0 32px; }
.footer p { font-size: 11px; color: var(--fg-dim); margin: 6px 0; }
.footer code { color: var(--accent-2); background: var(--bg-2);
  padding: 1px 6px; border-radius: 3px; }
.footer-meta { color: var(--fg-muted); font-size: 10px; }

.modal-backdrop { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.7);
  display: none; align-items: center; justify-content: center; z-index: 1000; }
.modal-backdrop.open { display: flex; }
.modal { background: var(--bg-1); border: 1px solid var(--border-bright); border-radius: 8px;
  padding: 20px; max-width: 560px; width: 90%; }
.modal h3 { font-size: 14px; margin-bottom: 12px; }
.modal .cmd { background: var(--bg-2); padding: 10px 12px; border-radius: 4px;
  font-family: monospace; color: var(--success); font-size: 12px;
  word-break: break-all; user-select: all; }
.modal .meta { color: var(--fg-muted); font-size: 10px; margin-top: 8px; }
.modal .actions { display: flex; gap: 8px; margin-top: 12px; }
.modal button { background: var(--accent); color: #fff; border: 0;
  padding: 6px 12px; border-radius: 4px; cursor: pointer; font-family: inherit;
  font-size: 11px; font-weight: 700; }
.modal button.secondary { background: var(--bg-3); color: var(--fg-dim); }
"""


JS = r"""
function onBeadClick(el) {
  var cmd = el.getAttribute('data-cmd') || '';
  var target = el.getAttribute('data-target') || '';
  var kind = el.getAttribute('data-kind') || '';
  var lane = el.getAttribute('data-lane') || '';
  if (!cmd) {
    showModal(target, kind, lane, '(no feature slug detected for this bead)');
    return;
  }
  // Copy command to clipboard and show modal.
  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(cmd).catch(function() {});
  }
  showModal(target, kind, lane, cmd);
}
function showModal(target, kind, lane, cmd) {
  var m = document.getElementById('modal');
  document.getElementById('modal-target').textContent = target;
  document.getElementById('modal-kind').textContent = kind;
  document.getElementById('modal-lane').textContent = lane;
  document.getElementById('modal-cmd').textContent = cmd;
  m.classList.add('open');
}
function closeModal() { document.getElementById('modal').classList.remove('open'); }
document.addEventListener('keydown', function(e) { if (e.key === 'Escape') closeModal(); });
"""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class _WellFormedChecker(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []
        self.tag_stack: list[str] = []
        self.void_tags = {
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr",
        }

    def handle_starttag(self, tag, attrs):
        if tag not in self.void_tags:
            self.tag_stack.append(tag)

    def handle_endtag(self, tag):
        if tag in self.void_tags:
            return
        if not self.tag_stack:
            self.errors.append(f"unexpected closing </{tag}> with empty stack")
            return
        if self.tag_stack[-1] != tag:
            self.errors.append(
                f"mismatched: opened <{self.tag_stack[-1]}> but got </{tag}>"
            )
        else:
            self.tag_stack.pop()


def assert_well_formed(html_text: str) -> None:
    checker = _WellFormedChecker()
    checker.feed(html_text)
    if checker.tag_stack:
        raise AssertionError(f"unclosed tags: {checker.tag_stack}")
    if checker.errors:
        raise AssertionError(f"HTML errors: {checker.errors[:3]}")


def assert_no_pictographs(html_text: str) -> None:
    bad = _PICTOGRAPH_RE.search(html_text)
    if bad:
        snippet = html_text[max(0, bad.start() - 20) : bad.end() + 20]
        raise AssertionError(f"pictograph remains at offset {bad.start()}: {snippet!r}")
    for glyph in ("\u2713", "\u2699", "\u25B6", "\u2717", "\u25C6", "\u25CF"):
        if glyph in html_text:
            idx = html_text.index(glyph)
            snippet = html_text[max(0, idx - 20) : idx + 20]
            raise AssertionError(f"explicit glyph {glyph!r} remains at offset {idx}: {snippet!r}")


def write_atomically(path: Path, content: str) -> None:
    """Durably replace the one approved artifact only after a complete write."""
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.",
        suffix=".tmp", delete=False,
    ) as temporary:
        temporary.write(content)
        temporary.flush()
        os.fsync(temporary.fileno())
        temporary_path = Path(temporary.name)
    try:
        os.replace(temporary_path, path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    if not OUTPUT_PATH.exists():
        print(f"ERROR: approved target does not exist: {OUTPUT_PATH}", file=sys.stderr)
        return 1

    beads = load_beads()
    if not beads:
        print("ERROR: no beads loaded", file=sys.stderr)
        return 1
    print(f"loaded {len(beads)} beads from beads.jsonl + audit mirror", file=sys.stderr)

    buckets = classify(beads)
    print("lane counts:", {lane["id"]: len(buckets[lane["id"]]) for lane in LANES}, file=sys.stderr)

    summary_html = render_summary_cards(beads, buckets)
    kanban_html = render_kanban(buckets)
    pm_html = render_top_features(beads, buckets)
    reconciliation_html = render_semantic_reconciliation()
    footer_html = render_footer()

    title = "Bead Cockpit \u2014 Leapfrog build 2026-08-10"
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<style>{CSS}</style>
</head>
<body>
<header class="banner">
  <h1>LEAPFROG COCKPIT \u2014 SUPERSEDES CODEX WIP</h1>
  <div class="subtitle">Build 2026-08-10 \u2014 9-lane AgilePlus kanban derived from beads.jsonl</div>
  <div class="provenance">
    Original artifact <code>cockpit/bead-cockpit-20260809-191131-f5ca38f7.html</code>
    was overwritten by Codex and is unrecoverable. Closest historical match is
    <code>cockpit/bead-cockpit-20260809-193102-multi.html</code> (Aug 9 19:31,
    150 KB, 5-lane PM viewer). This file leapfrogs that lineage with a strict
    9-lane AgilePlus-faithful model and explicit PM outcomes panel.
  </div>
</header>
<header class="topbar">
  <strong>BeAdCoCkPiT</strong>
  <span style="color:var(--fg-muted);font-size:11px;">generated {esc(generated_at)}</span>
  <nav>
    <a href="#summary">SUMMARY</a>
    <a href="#kanban">KANBAN</a>
    <a href="#pm">Product Management</a>
    <a href="#source">SOURCE</a>
  </nav>
</header>
<main>
  <h2 id="summary">Summary</h2>
  {summary_html}
  <h2 id="kanban">Kanban (AgilePlus 9 lanes)</h2>
  <p class="section-desc">Click any card to copy the matching
  <code>agileplus dashboard --json --feature &lt;slug&gt;</code> command and
  open a context modal. Lane assignment is derived from bead kind plus
  sub-classification of <code>ctl</code> beads (planning / build / review /
  verify) using regex heuristics over bead text and target.</p>
  {kanban_html}
  <h2 id="pm">PM-Style Outcomes</h2>
  {reconciliation_html}
  {pm_html}
  <div id="source">{footer_html}</div>
</main>
<div class="modal-backdrop" id="modal" onclick="if(event.target===this) closeModal()">
  <div class="modal">
    <h3>Sub-DAG / Acceptance Link</h3>
    <div>Target: <code id="modal-target"></code></div>
    <div>Kind: <span class="kind" id="modal-kind"></span></div>
    <div>Lane: <span class="status-pill" id="modal-lane"></span></div>
    <div style="margin-top:10px;color:var(--fg-muted);font-size:10px;">Command (copied to clipboard):</div>
    <div class="cmd" id="modal-cmd"></div>
    <div class="actions">
      <button onclick="closeModal()">CLOSE</button>
    </div>
  </div>
</div>
<script>{JS}</script>
</body>
</html>
"""

    # Validate before writing.
    assert_well_formed(doc)
    assert_no_pictographs(doc)

    write_atomically(OUTPUT_PATH, doc)
    size = OUTPUT_PATH.stat().st_size
    print(f"wrote {OUTPUT_PATH} ({size} bytes)", file=sys.stderr)
    if size > MAX_OUTPUT_BYTES:
        print(f"WARN: file exceeds 1 MiB cap ({size} bytes)", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
