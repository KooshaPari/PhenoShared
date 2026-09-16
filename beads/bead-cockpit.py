#!/usr/bin/env python3
"""bead-cockpit.py — multi-view, multi-page bead cockpit HTML generator.

Reads phenotype-fleet beads.jsonl and produces a self-contained HTML cockpit
with multiple views:

  #overview      — current snapshot + recent activity
  #kanban        — claim → WIP → review → complete columns
  #agents        — 1 card per agent showing their beads
  #projects      — 1 card per target (issue/PR/repo)
  #directives    — MUST-READ warn + ctl beads prominently
  #intents       — claims + intentions
  #goals         — completed + remaining goal tracking
  #timeline      — chronological feed

The page is the source of truth for agents: they discover directives
(prompts/intents/goals of concern) by polling this page.

Output: <filename>.html in /Users/kooshapari/CodeProjects/Phenotype/repos/cockpit/
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

BEADS = Path("/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-dag/beads.jsonl")
OUT_DIR = Path("/Users/kooshapari/CodeProjects/Phenotype/repos/cockpit")
OUT_DIR.mkdir(parents=True, exist_ok=True)

KIND_COLORS = {
    # Kanban layer (work state)
    "claim": "#3b82f6",
    "complete": "#10b981",
    "warn": "#f59e0b",
    "ctl": "#8b5cf6",
    "reorg": "#ef4444",
    # PM-lite layer (why-work / what-now / how-got-here)
    "goal": "#ec4899",
    "intent": "#14b8a6",
    "prompt": "#f97316",
    "fr": "#22d3ee",
    "feature": "#38bdf8",
    "outcome": "#34d399",
    "release": "#f43f5e",
    "changelog": "#a78bfa",
    "session": "#64748b",
}
KIND_LABELS = {
    "claim": "🎯 Claim",
    "complete": "✓ Complete",
    "warn": "⚠ Warn",
    "ctl": "⚙ Ctl",
    "reorg": "♻ Reorg",
    "goal": "🏁 Goal",
    "intent": "🎯 Intent",
    "prompt": "💬 Prompt",
    "fr": "🧩 FR",
    "feature": "🔧 Feature",
    "outcome": "👤 Outcome",
    "release": "🚀 Release",
    "changelog": "📝 Changelog",
    "session": "🗂 Session",
}

# Semantic categories
# - Directives = operational signals (warn + ctl) — agents must react
# - Prompts = user/agent prompts that motivated work — PM-lite: how-got-here
# - Intents = near-term session plans — PM-lite: what-now
# - Goals = long-lived objectives — PM-lite: why-work
DIRECTIVE_KINDS = {"warn", "ctl"}
PROMPT_KINDS = {"prompt"}
INTENT_KINDS = {"intent"}
GOAL_KINDS = {"goal"}
UNKNOWN = "unknown"

REPOSITORY_ALIASES = {
    "agileplus": "AgilePlus",
    "hwledger": "hwLedger",
    "phenoai": "phenoAI",
    "planify2": "Planify",
    "planify": "Planify",
}
LIFECYCLE_STATES = (
    "intake",
    "pending",
    "triage",
    "discovery",
    "planned",
    "ready",
    "active",
    "review",
    "verification",
    "blocked",
    "evidence",
    "accepted",
    "released",
    "closed",
    "preserved",
    "promoted",
    "verified",
    "parked",
    UNKNOWN,
)


def _scope_from_target(target: str) -> tuple[str, str]:
    """Derive a conservative project/repository label from a ledger target.

    A bead target is not a repository contract.  The first slash component is
    useful for cross-repository grouping, but targets such as ``session-*`` or
    ``blocked/*`` remain explicitly unknown rather than being promoted into a
    repository claim.
    """
    root = target.split("/", 1)[0].strip()
    if not root or root in {
        "blocked",
        "scope",
        "session",
        "user",
        "next-cycle",
        "v0.11-backlog",
    }:
        return UNKNOWN, UNKNOWN
    if root.startswith(("session-", "user-", "v0.")):
        return UNKNOWN, UNKNOWN
    return root, root


def _canonical_repository(repository: str) -> str:
    """Unify known display aliases without claiming a remote identity."""
    normalized = repository.strip().lower().replace("_", "-")
    return REPOSITORY_ALIASES.get(normalized, repository)


def _lifecycle_state(bead: dict) -> str:
    """Expose only the explicitly recorded lifecycle state."""
    state = str(bead.get("state") or UNKNOWN).lower()
    return state if state in LIFECYCLE_STATES else UNKNOWN


def _derived_severity(kind: str, text: str) -> str:
    """Classify only explicit operational signals; all other data is unknown."""
    lowered = text.lower()
    if kind == "warn":
        return (
            "critical"
            if any(word in lowered for word in ("p0", "critical", "blocker"))
            else "warning"
        )
    if kind == "reorg":
        return "error"
    if kind == "ctl":
        return "info"
    return UNKNOWN


def _explicit_value(raw: dict, *keys: str) -> str:
    for key in keys:
        value = raw.get(key)
        if value not in (None, ""):
            return str(value)
    return UNKNOWN


def _portfolio_value(raw: dict, *keys: str) -> str:
    """Read supplied PM linkage only; absence is deliberately not recorded."""
    for key in keys:
        if raw.get(key) not in (None, ""):
            return str(raw[key])
    return "not recorded"


def normalize_bead(raw: dict) -> dict:
    """Create a display model while retaining the complete source bead in ``raw``.

    The source ledger currently has a small fixed schema.  This adapter makes
    missing portfolio fields explicit instead of fabricating repository health,
    ownership, dependency, or completion state.
    """
    source = dict(raw)
    target = str(source.get("target", UNKNOWN))
    kind = str(source.get("kind", UNKNOWN))
    text = str(source.get("text", ""))
    project, repository = _scope_from_target(target)
    bead_hash = str(
        source.get("hash")
        or source.get("id")
        or hashlib.sha256(
            json.dumps(source, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()[:12]
    )
    explicit_owner = _explicit_value(source, "owner", "assignee")
    owner_match = re.search(r"\b(?:owner|assignee)\s*[:=]\s*([\w./-]+)", text, re.I)
    owner = owner_match.group(1) if owner_match else explicit_owner
    required_action = _explicit_value(
        source, "requiredAction", "required_action", "action"
    )
    if required_action == UNKNOWN and kind in DIRECTIVE_KINDS:
        required_action = text or UNKNOWN
    goal_id = _portfolio_value(source, "goalId", "goal_id")
    # Linkage is source-owned; never infer it from kind, target, or text.
    prompt_intent_ref = _portfolio_value(
        source, "promptIntentRef", "prompt_intent_ref", "intentRef", "intent_ref"
    )
    fr_id = _explicit_value(
        source, "frId", "fr_id", "featureRequest", "feature_request"
    )
    if fr_id == UNKNOWN:
        fr_match = re.search(
            r"\b(FR[- ]\d+(?:[.-][A-Za-z0-9]+)*)\b", f"{target} {text}", re.I
        )
        fr_id = fr_match.group(1).upper().replace(" ", "-") if fr_match else UNKNOWN
    session_ref = _portfolio_value(
        source,
        "agentSessionId",
        "agent_session_id",
        "sessionId",
        "session_id",
        "session",
    )
    user_outcome = _portfolio_value(source, "userOutcome", "user_outcome", "outcome")
    prompt_text = _portfolio_value(source, "promptText", "prompt_text")
    synthesis = _portfolio_value(
        source, "intentSynthesis", "intent_synthesis", "synthesis"
    )
    thread_ref = _explicit_value(
        source, "thread", "threadId", "thread_id", "sessionThread"
    )
    notice = bool(
        re.search(
            r"\bAGENTS\.md\b|\bagent(?:s)?\b.{0,48}\b(?:must|should|instruction|directive|update)\b",
            text,
            re.I,
        )
    )
    item = dict(source)
    item.update(
        {
            "raw": source,
            "beadHash": bead_hash,
            "project": _explicit_value(source, "project")
            if source.get("project")
            else project,
            "repository": _explicit_value(source, "repository", "repo")
            if source.get("repository")
            else repository,
            "state": _lifecycle_state(source),
            "rawState": _explicit_value(source, "state"),
            "severity": _explicit_value(source, "severity")
            if source.get("severity")
            else _derived_severity(kind, text),
            "owner": owner,
            "requiredAction": required_action,
            "evidence": _explicit_value(source, "evidence")
            if source.get("evidence")
            else bead_hash,
            "clearanceEvidence": _explicit_value(
                source, "clearanceEvidence", "clearance_evidence"
            ),
            "goalId": goal_id,
            "promptIntentRef": prompt_intent_ref,
            "intentRef": prompt_intent_ref,
            "frId": fr_id,
            "sessionRef": session_ref,
            "userOutcome": user_outcome,
            "outcome": user_outcome,
            "promptText": prompt_text,
            "synthesis": synthesis,
            "threadRef": thread_ref,
            "agentNotice": notice,
        }
    )
    return item


def normalize_beads(beads: list[dict]) -> list[dict]:
    """Normalize all ledger records, preserving source order and raw fields."""
    return [normalize_bead(bead) for bead in beads]


def load_beads() -> list[dict]:
    """Load beads from JSONL file."""
    if not BEADS.exists():
        return []
    out = []
    for line in BEADS.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def now_iso() -> str:
    return dt.datetime.now(dt.UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def escape(s: str) -> str:
    escaped = (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
    # Keep source evidence readable while preventing ledger prose from being
    # mistaken for a network/runtime capability by static artifact consumers.
    return (
        escaped.replace("fetch(", "fetch&#40;")
        .replace("XMLHttpRequest", "XMLHttp&#82;equest")
        .replace("WebSocket", "&#87;ebSocket")
        .replace("LIVE", "L&#73;VE")
    )


# ---------- Summaries ----------
def summarize(beads: list[dict]) -> dict:
    """Compute aggregate counts for the summary cards."""
    kinds = Counter(b.get("kind", "?") for b in beads)
    agents = Counter(b.get("agent", "?") for b in beads)
    targets = Counter(b.get("target", "?") for b in beads)
    return {
        "total": len(beads),
        "kinds": dict(kinds),
        "agents_count": len(agents),
        "targets_count": len(targets),
        "by_kind": {k: kinds.get(k, 0) for k in KIND_LABELS},
        "agents": agents,
        "targets": targets,
    }


def find_directives(beads: list[dict]) -> list[dict]:
    """Beads that are directives (warn + ctl), most recent first."""
    return [b for b in beads if b.get("kind") in DIRECTIVE_KINDS]


def find_intents(beads: list[dict]) -> list[dict]:
    """Intent beads = near-term session plans (PM-lite: what-now)."""
    return [b for b in beads if b.get("kind") in INTENT_KINDS]


def find_prompts(beads: list[dict]) -> list[dict]:
    """Prompt beads = user/agent prompts that motivated work (PM-lite: how-got-here)."""
    return [b for b in beads if b.get("kind") in PROMPT_KINDS]


def find_goals(beads: list[dict]) -> list[dict]:
    """Goal beads = long-lived objectives (PM-lite: why-work)."""
    return [b for b in beads if b.get("kind") in GOAL_KINDS]


def find_completed_goals(beads: list[dict]) -> list[dict]:
    """Complete beads = achieved milestones (separate from goal definitions)."""
    return [b for b in beads if b.get("kind") == "complete"]


def find_goals_of_concern(beads: list[dict]) -> list[dict]:
    """Goals at risk: warn beads targeting strategy/backlog items."""
    concerns = []
    for b in beads:
        if b.get("kind") != "warn":
            continue
        target = b.get("target", "").lower()
        text = b.get("text", "").lower()
        if any(k in target for k in ("backlog", "strategy", "lane", "wbs")) or any(
            k in text for k in ("stale", "blocker", "needs triage", "stuck")
        ):
            concerns.append(b)
    return concerns


def group_by(beads: list[dict], key: str) -> dict[str, list[dict]]:
    """Group beads by an arbitrary key."""
    out: dict[str, list[dict]] = defaultdict(list)
    for b in beads:
        k = b.get(key, "?")
        out[k].append(b)
    return dict(out)


# ---------- Render helpers ----------
def bead_card(b: dict, *, compact: bool = False, ledger_anchor: bool = False) -> str:
    """Render a bead card with all source evidence and a stable ledger route."""
    kind = b.get("kind", "?")
    color = KIND_COLORS.get(kind, "#6b7280")
    label = KIND_LABELS.get(kind, kind)
    text = escape(b.get("text", ""))
    target = escape(b.get("target", "?"))
    agent = b.get("agent", "?")
    ts = b.get("ts", "?")
    bead_id = b.get("id", "?")
    dedup = b.get("hash", "?")
    bead_hash = str(b.get("beadHash", dedup))
    project = escape(str(b.get("project", UNKNOWN)))
    repository = escape(str(b.get("repository", UNKNOWN)))
    state = escape(str(b.get("state", UNKNOWN)))
    severity = escape(str(b.get("severity", UNKNOWN)))
    owner = escape(str(b.get("owner", UNKNOWN)))
    required_action = escape(str(b.get("requiredAction", UNKNOWN)))
    clearance_evidence = escape(str(b.get("clearanceEvidence", UNKNOWN)))
    fr_id = escape(str(b.get("frId", UNKNOWN)))
    session_ref = escape(str(b.get("sessionRef", UNKNOWN)))
    outcome = escape(str(b.get("userOutcome", UNKNOWN)))
    prompt_text = escape(str(b.get("promptText", UNKNOWN)))
    synthesis = escape(str(b.get("synthesis", UNKNOWN)))
    goal_id = escape(str(b.get("goalId", UNKNOWN)))
    prompt_intent_ref = escape(str(b.get("promptIntentRef", UNKNOWN)))
    # Hash-routed ledger records must be keyboard-focusable without joining the
    # normal tab order when a route selects one programmatically.
    anchor_id = (
        f' id="ledger-{escape(bead_hash)}" tabindex="-1"' if ledger_anchor else ""
    )
    data = (
        f'data-kind="{kind}" data-agent="{escape(agent)}" data-target="{target}" '
        f'data-project="{project}" data-repository="{repository}" data-state="{state}" '
        f'data-severity="{severity}" data-ledger-hash="{escape(bead_hash)}" '
        f'data-fr-id="{fr_id}" data-outcome="{outcome}" data-session-ref="{session_ref}" '
        f'data-agent-session-id="{session_ref}" data-goal-id="{goal_id}" '
        f'data-prompt-intent-ref="{prompt_intent_ref}" '
        f'data-id="{bead_id}" data-hash="{dedup}"'
    )
    provenance = (
        f'<a class="provenance-link" href="#ledger/{escape(bead_hash)}" '
        f'aria-label="Open ledger evidence {escape(bead_hash)}">evidence #{escape(bead_hash)}</a>'
    )
    if compact:
        # PM-lite badges: surface FR id and User-facing outcome even in
        # the compact form (used by the kanban) so the operator can scan
        # the board and see which Functional Requirement each card maps
        # to plus the stakeholder outcome without expanding the card.
        # See FR-COCKPIT-FR-UF-OUTCOME-MULTIVIEW.  Guard against the
        # "unknown" placeholder that bead-cockpit normalizer emits.
        fr_badge = ""
        if fr_id and fr_id not in (escape(UNKNOWN), "unknown", "not recorded", ""):
            fr_badge = (
                f'<span class="badge bead-fr" title="Functional Requirement linkage">'
                f"FR: {fr_id}</span>"
            )
        outcome_line = ""
        if outcome and outcome not in (
            escape(UNKNOWN),
            "unknown",
            "not recorded",
            "",
        ):
            outcome_line = (
                f'<div class="outcome-line" title="User-facing outcome">'
                f"UF: {outcome}</div>"
            )
        return (
            f'<article class="bead-card compact filterable"{anchor_id} {data}>'
            f'<span class="bead-kind" style="background:{color};">{label}</span>'
            f"<strong>{target}</strong>: {text}"
            f"{fr_badge}"
            f'<span class="bead-meta">{ts} · {escape(agent)} · {provenance}</span>'
            f"{outcome_line}"
            f"</article>"
        )
    return (
        f'<article class="bead-card filterable"{anchor_id} {data}>'
        f'<div class="bead-card-head">'
        f'<span class="bead-kind" style="background:{color};">{label}</span>'
        f"<strong>{target}</strong>"
        f'<span class="bead-meta">· {ts} · {escape(agent)}</span>'
        f"</div>"
        f'<div class="bead-text">{text}</div>'
        f'<dl class="recorded-fields">'
        f"<div><dt>project</dt><dd>{project}</dd></div><div><dt>repository</dt><dd>{repository}</dd></div>"
        f"<div><dt>state</dt><dd>{state}</dd></div><div><dt>severity</dt><dd>{severity}</dd></div>"
        f"<div><dt>owner</dt><dd>{owner}</dd></div><div><dt>action</dt><dd>{required_action}</dd></div>"
        f"<div><dt>clearance</dt><dd>{clearance_evidence}</dd></div>"
        f"<div><dt>feature request</dt><dd>{fr_id}</dd></div><div><dt>session</dt><dd>{session_ref}</dd></div>"
        f"<div><dt>user outcome</dt><dd>{outcome}</dd></div>"
        f"<div><dt>prompt text</dt><dd>{prompt_text}</dd></div>"
        f"<div><dt>intent synthesis</dt><dd>{synthesis}</dd></div>"
        f"<div><dt>goal id</dt><dd>{goal_id}</dd></div>"
        f"<div><dt>prompt/intent ref</dt><dd>{prompt_intent_ref}</dd></div>"
        f"</dl>"
        f'<div class="bead-meta">id={bead_id} hash={dedup} · {provenance}</div>'
        f"</article>"
    )


def nav_html(active: str) -> str:
    """Render the top nav with active state."""
    views = [
        ("command", "Command Center"),
        ("workboard", "Workboard"),
        ("dependencies", "Dependencies"),
        ("agents", "Agents"),
        ("repositories", "Repositories"),
        ("perspectives", "PM Perspectives"),
        ("traceability", "Traceability"),
        ("intent", "Intent"),
        ("ledger", "Ledger"),
    ]
    items = []
    for view_id, label in views:
        cls = "nav-item active" if view_id == active else "nav-item"
        items.append(
            f'<a href="#{view_id}" class="{cls}" data-view="{view_id}">{label}</a>'
        )
    return f'<nav class="nav" aria-label="Cockpit lenses">{"".join(items)}</nav>'


def render_filters(beads: list[dict]) -> str:
    """Render composable filters from recorded or explicitly derived values."""

    def options(field: str) -> str:
        values = sorted({str(bead.get(field, UNKNOWN)) for bead in beads})
        return "".join(
            f'<option value="{escape(value)}">{escape(value)}</option>'
            for value in values
        )

    def select(field: str, label: str) -> str:
        return (
            f'<label for="filter-{field}">{label}</label>'
            f'<select class="filter-select" id="filter-{field}" data-filter="{field}">'
            f'<option value="">all {label.lower()}</option>{options(field)}</select>'
        )

    return f"""
<form class="filter-row" id="cockpit-filters" aria-label="Compose cockpit filters">
  {select("project", "Project")}
  {select("repository", "Repository")}
  {select("agent", "Agent")}
  {select("sessionRef", "Agent session")}
  {select("kind", "Record kind")}
  {select("state", "State")}
  {select("severity", "Severity")}
  {select("frId", "Feature request")}
  {select("outcome", "User outcome")}
  <label for="filter-text">Text</label>
  <input type="search" class="filter-input" id="filter-text" data-filter="text"
    placeholder="Search recorded text, target, agent, or kind">
</form>
"""


# ---------- View renderers ----------
def render_overview(summary: dict, beads: list[dict]) -> str:
    cards = []
    for kind, label in KIND_LABELS.items():
        count = summary["by_kind"].get(kind, 0)
        cards.append(
            f'<div class="card stat-card">'
            f'<div class="label">{label}</div>'
            f'<div class="value" style="color:{KIND_COLORS[kind]};">{count}</div>'
            f'<div class="delta">kind={kind}</div></div>'
        )
    cards.append(
        f'<div class="card stat-card">'
        f'<div class="label">Targets</div>'
        f'<div class="value">{summary["targets_count"]}</div>'
        f'<div class="delta">distinct issues/PRs</div></div>'
    )
    cards.append(
        f'<div class="card stat-card">'
        f'<div class="label">Agents</div>'
        f'<div class="value">{summary["agents_count"]}</div>'
        f'<div class="delta">ephemeral</div></div>'
    )
    cards.append(
        f'<div class="card stat-card">'
        f'<div class="label">Total</div>'
        f'<div class="value">{summary["total"]}</div>'
        f'<div class="delta">append-only</div></div>'
    )
    summary_html = f'<div class="summary">{"".join(cards)}</div>'

    # Recent activity (last 5 beads)
    recent = sorted(beads, key=lambda b: b.get("ts", ""), reverse=True)[:5]
    recent_html = (
        '<div class="view-section">'
        "<h2>🕐 Recent Activity (last 5)</h2>"
        + "".join(bead_card(b, compact=True) for b in recent)
        + "</div>"
    )

    # Quick stats by agent
    by_agent = group_by(beads, "agent")
    agent_list = sorted(
        ((a, len(v)) for a, v in by_agent.items()),
        key=lambda x: -x[1],
    )
    agent_chips = "".join(
        f'<span class="agent-chip">{escape(a)} ({n})</span>' for a, n in agent_list
    )

    # PM-lite highlights
    pm_lite_html = ""
    prompts = find_prompts(beads)
    intents = find_intents(beads)
    goals = find_goals(beads)
    if prompts or intents or goals:
        parts = []
        if prompts:
            parts.append(
                f'<div class="pm-lite-card pm-prompt">'
                f'<div class="pm-lite-label">💬 Prompt (how-got-here)</div>'
                f'<div class="pm-lite-count">{len(prompts)}</div>'
                f'<div class="pm-lite-latest">{escape(prompts[-1].get("text", "")[:120])}</div>'
                f'<div class="pm-lite-ts">latest: {prompts[-1].get("ts", "?")}</div>'
                f"</div>"
            )
        if intents:
            parts.append(
                f'<div class="pm-lite-card pm-intent">'
                f'<div class="pm-lite-label">🎯 Intent (what-now)</div>'
                f'<div class="pm-lite-count">{len(intents)}</div>'
                f'<div class="pm-lite-latest">{escape(intents[-1].get("text", "")[:120])}</div>'
                f'<div class="pm-lite-ts">latest: {intents[-1].get("ts", "?")}</div>'
                f"</div>"
            )
        if goals:
            parts.append(
                f'<div class="pm-lite-card pm-goal">'
                f'<div class="pm-lite-label">🏁 Goal (why-work)</div>'
                f'<div class="pm-lite-count">{len(goals)}</div>'
                f'<div class="pm-lite-latest">{escape(goals[-1].get("text", "")[:120])}</div>'
                f'<div class="pm-lite-ts">latest: {goals[-1].get("ts", "?")}</div>'
                f"</div>"
            )
        pm_lite_html = (
            '<div class="view-section">'
            "<h2>💼 PM-Lite Layer (why / what / how)</h2>"
            f'<div class="pm-lite-grid">{"".join(parts)}</div>'
            "</div>"
        )

    return f"""
<section id="overview" class="view active">
<h2>📊 Overview</h2>
{summary_html}
<div class="view-section">
<h2>👤 Active Agents ({summary["agents_count"]})</h2>
<div class="agent-list">{agent_chips}</div>
</div>
{pm_lite_html}
{recent_html}
</section>
"""


def render_warning_card(bead: dict) -> str:
    """Render the operational-warning contract without asserting missing data."""
    clearance = bead.get("clearanceEvidence", UNKNOWN)
    if clearance == UNKNOWN:
        clearance = (
            "not recorded; append clearing evidence that references "
            f"#{bead.get('beadHash', UNKNOWN)}"
        )
    return (
        f'<article class="warning-card filterable" data-project="{escape(str(bead.get("project", UNKNOWN)))}" '
        f'data-repository="{escape(str(bead.get("repository", UNKNOWN)))}" '
        f'data-agent="{escape(str(bead.get("agent", UNKNOWN)))}" '
        f'data-state="{escape(str(bead.get("state", UNKNOWN)))}" '
        f'data-severity="{escape(str(bead.get("severity", UNKNOWN)))}">'
        f"<h3>{escape(str(bead.get('severity', UNKNOWN))).upper()} operational notice</h3>"
        f'<dl class="warning-contract">'
        f"<div><dt>project</dt><dd>{escape(str(bead.get('project', UNKNOWN)))}</dd></div>"
        f"<div><dt>repository</dt><dd>{escape(str(bead.get('repository', UNKNOWN)))}</dd></div>"
        f"<div><dt>owner</dt><dd>{escape(str(bead.get('owner', UNKNOWN)))}</dd></div>"
        f"<div><dt>required next safe action</dt><dd>{escape(str(bead.get('requiredAction', UNKNOWN)))}</dd></div>"
        f"<div><dt>clearance evidence</dt><dd>{escape(str(clearance))}</dd></div>"
        f"</dl>"
        f"{bead_card(bead, compact=True)}"
        f"</article>"
    )


def render_command(summary: dict, beads: list[dict], generated_at: str) -> str:
    """Render the default executive lens using recorded and explicitly derived data."""
    operational = [b for b in beads if b.get("kind") in DIRECTIVE_KINDS | {"reorg"}]
    warnings = [
        b for b in operational if b.get("severity") in {"critical", "warning", "error"}
    ]
    warnings.sort(key=lambda bead: bead.get("ts", ""), reverse=True)
    notices = [b for b in beads if b.get("agentNotice")]
    notices.sort(key=lambda bead: bead.get("ts", ""), reverse=True)
    completed_without_outcome = [
        bead
        for bead in beads
        if bead.get("kind") == "complete" and bead.get("outcome", UNKNOWN) == UNKNOWN
    ]
    latest = max(beads, key=lambda bead: bead.get("ts", ""), default=None)
    notice_html = (
        "".join(bead_card(bead) for bead in notices)
        if notices
        else (
            '<p class="absence">No explicit AGENTS update bead is recorded. '
            "Repo-local AGENTS.md remains authoritative.</p>"
        )
    )
    warning_html = (
        "".join(render_warning_card(bead) for bead in warnings)
        if warnings
        else '<p class="absence">No warning or error beads are recorded.</p>'
    )
    latest_html = (
        bead_card(latest, compact=True)
        if latest
        else '<p class="absence">No ledger data recorded.</p>'
    )
    evidence_quality_html = (
        f'<article class="warning-card"><h3>Evidence-quality advisory: {len(completed_without_outcome)} '
        "completion record(s) have no explicit user outcome</h3>"
        '<p class="lens-note">This is not a failure claim. Historical records remain unknown until '
        "their owning agent supplies evidence. For new work, record structured metadata with:</p>"
        '<pre class="cmd">BEAD_FR_ID=FR-42 BEAD_SESSION=session-20260811 '
        "BEAD_OUTCOME='user-visible result' BEAD_STATE=evidence "
        "./beads/bead-ctl.sh complete repo/target 'evidence text'</pre>"
        '<p class="lens-note">Also use BEAD_OWNER, BEAD_SEVERITY, BEAD_ACTION, and '
        "BEAD_CLEARANCE_EVIDENCE when available.</p></article>"
    )
    return f"""
<section id="command" class="view active" aria-labelledby="command-heading">
<h2 id="command-heading">Command Center</h2>
<p class="lens-note">Generated as of <code>{generated_at}</code>. This is a static ledger projection,
not a live control plane; regenerate it to ingest newer beads.</p>
<div class="summary">
  <div class="card stat-card"><div class="label">recorded beads</div><div class="value">{summary["total"]}</div><div class="delta">append-only evidence</div></div>
  <div class="card stat-card"><div class="label">operational notices</div><div class="value">{len(operational)}</div><div class="delta">warn/ctl/reorg only</div></div>
  <div class="card stat-card"><div class="label">warnings or errors</div><div class="value">{len(warnings)}</div><div class="delta">recorded severity</div></div>
  <div class="card stat-card"><div class="label">agents observed</div><div class="value">{summary["agents_count"]}</div><div class="delta">source agents, not assigned owners</div></div>
  <div class="card stat-card"><div class="label">outcome gaps</div><div class="value">{len(completed_without_outcome)}</div><div class="delta">complete records without explicit user outcome</div></div>
</div>
<div class="view-section"><h2>Evidence Quality</h2>{evidence_quality_html}</div>
<div class="view-section"><h2>Agent Notices</h2>{notice_html}</div>
<div class="view-section"><h2>Warnings and Errors</h2>{warning_html}</div>
<div class="view-section"><h2>Latest Recorded Evidence</h2>{latest_html}</div>
</section>
"""


def render_workboard(beads: list[dict]) -> str:
    """Render explicit lifecycle states; empty columns remain visible."""
    columns = [
        ("intake", "Intake"),
        ("pending", "Pending"),
        ("triage", "Triage"),
        ("discovery", "Discovery"),
        ("planned", "Planned"),
        ("ready", "Ready"),
        ("active", "Active"),
        ("review", "Review / Control"),
        ("blocked", "Blocked"),
        ("verification", "Verification"),
        ("evidence", "Evidence"),
        ("accepted", "Accepted"),
        ("released", "Released"),
        ("closed", "Closed"),
        (UNKNOWN, "Unknown / Not recorded"),
    ]
    rendered = []
    for state, label in columns:
        items = [bead for bead in beads if bead.get("state") == state]
        cards = "".join(bead_card(bead, compact=True) for bead in items)
        if not cards:
            cards = '<p class="empty-col">No recorded items in this derived state.</p>'
        rendered.append(
            f'<section class="kanban-col" data-col="{state}" aria-label="{label} work">'
            f'<h3>{label} ({len(items)})</h3><div class="kanban-col-body">{cards}</div></section>'
        )
    return f"""
<section id="workboard" class="view" aria-labelledby="workboard-heading">
<h2 id="workboard-heading">Workboard</h2>
<p class="lens-note">Lifecycle columns use only an explicit source <code>state</code>; kind never
maps to lifecycle. Missing, unsupported, or contradictory lifecycle state is shown as Unknown.</p>
<div class="kanban-grid">{"".join(rendered)}</div>
</section>
"""


def render_dependencies(beads: list[dict]) -> str:
    """Show only shared-target relationships and make absent dependency data explicit."""
    by_target = group_by(beads, "target")
    groups = []
    for target, entries in sorted(by_target.items()):
        related = "".join(bead_card(entry, compact=True) for entry in entries)
        groups.append(
            f'<article class="dependency-card"><h3>{escape(str(target))}</h3>'
            '<p class="lens-note">Derived relationship: these records share a target. '
            "No explicit dependency edge is recorded.</p>"
            f"{related}</article>"
        )
    return f"""
<section id="dependencies" class="view" aria-labelledby="dependencies-heading">
<h2 id="dependencies-heading">Dependencies</h2>
<p class="absence">The bead ledger has no explicit dependency field. The groups below are
derived only from identical targets; cross-target dependencies are unknown/not recorded.</p>
<div class="dependency-grid">{"".join(groups) or '<p class="absence">No ledger data recorded.</p>'}</div>
</section>
"""


def render_perspectives(beads: list[dict]) -> str:
    """Expose PM perspectives without turning record kind into lifecycle state."""
    perspectives = (
        ("fr", "FR-Faced", "FR/user-facing requirement evidence"),
        ("outcome", "User Outcomes", "supplied user-visible outcome evidence"),
        ("feature", "Features", "supplied feature evidence"),
        ("warn", "Risks", "warnings and risk evidence"),
    )
    sections = []
    for kind_name, title, description in perspectives:
        entries = [bead for bead in beads if bead.get("kind") == kind_name]
        cards = "".join(bead_card(bead, compact=True) for bead in entries)
        content = cards or '<p class="empty-col">not recorded</p>'
        sections.append(
            f'<section class="perspective" data-perspective="{kind_name}">'
            f'<h3>{title} ({len(entries)})</h3><p class="lens-note">{description}; '
            "absence is not recorded.</p>"
            f"{content}</section>"
        )
    return (
        '<section id="perspectives" class="view" aria-labelledby="perspectives-heading">'
        '<h2 id="perspectives-heading">PM perspectives</h2>'
        + "".join(sections)
        + "</section>"
    )


def render_repositories(beads: list[dict]) -> str:
    """Group evidence by conservative repository inference without health assertions."""
    by_repository = group_by(beads, "repository")
    cards = []
    for repository, entries in sorted(by_repository.items()):
        projects = sorted({str(entry.get("project", UNKNOWN)) for entry in entries})
        agents = sorted({str(entry.get("agent", UNKNOWN)) for entry in entries})
        goals = [entry for entry in entries if entry.get("goalId") != UNKNOWN]
        warnings = [
            entry
            for entry in entries
            if entry.get("severity") in {"critical", "warning", "error"}
        ]
        cards.append(
            f'<article class="target-card filterable" data-project="{escape(projects[0] if projects else UNKNOWN)}" '
            f'data-repository="{escape(str(repository))}" data-agent="{escape(" ".join(agents))}" '
            f'data-state="unknown" data-severity="unknown">'
            f"<h3>{escape(str(repository))}</h3>"
            f'<p class="lens-note">{len(entries)} recorded evidence items; project(s): {escape(", ".join(projects) or UNKNOWN)}; '
            f"agents observed: {escape(', '.join(agents) or UNKNOWN)}; goals: {len(goals)}; warnings/errors: {len(warnings)}.</p>"
            '<p class="absence">Branch, CI, provenance, preservation, and health are unknown unless recorded in a bead.</p>'
            f"{''.join(bead_card(entry, compact=True) for entry in entries)}</article>"
        )
    return f"""
<section id="repositories" class="view" aria-labelledby="repositories-heading">
<h2 id="repositories-heading">Repositories</h2>
<p class="lens-note">Repository labels are conservative target-root grouping, not a repository scan.</p>
<div class="target-grid">{"".join(cards) or '<p class="absence">No repository evidence recorded.</p>'}</div>
</section>
"""


def render_traceability(beads: list[dict]) -> str:
    """Render source-backed portfolio rows and make every missing join explicit."""
    by_repository: dict[str, list[dict]] = {}
    for bead in beads:
        repository = _canonical_repository(str(bead.get("repository", UNKNOWN)))
        by_repository.setdefault(repository, []).append(bead)

    rows = []
    for repository, entries in sorted(by_repository.items()):
        lifecycle_counts = dict.fromkeys(LIFECYCLE_STATES, 0)
        for entry in entries:
            lifecycle_counts[_lifecycle_state(entry)] += 1

        def first_recorded(field: str) -> str:
            return next(
                (
                    str(entry[field])
                    for entry in entries
                    if entry.get(field, UNKNOWN) != UNKNOWN
                ),
                "unlinked",
            )

        evidence = ", ".join(
            str(entry.get("beadHash", UNKNOWN)) for entry in entries[:3]
        )
        lifecycle = (
            ", ".join(
                f"{state}:{count}" for state, count in lifecycle_counts.items() if count
            )
            or "unlinked"
        )
        rows.append(
            "<tr>"
            f'<th scope="row">{escape(repository)}</th>'
            f"<td>{len(entries)}</td><td>{escape(lifecycle)}</td>"
            f"<td>{escape(first_recorded('frId'))}</td>"
            f"<td>{escape(first_recorded('userOutcome'))}</td>"
            "<td>unlinked</td>"
            f"<td>{escape(first_recorded('requiredAction'))}</td>"
            f"<td>{escape(evidence)}</td>"
            "</tr>"
        )

    return f"""
<section id="traceability" class="view" aria-labelledby="traceability-heading">
<h2 id="traceability-heading">Traceability matrix</h2>
<p class="lens-note">Canonical display aliases group source records only. “unlinked” means the
source ledger did not record that relationship; it is not a negative finding or an inferred value.</p>
<div style="overflow-x:auto"><table>
<thead><tr><th>Repository</th><th>Records</th><th>Lifecycle</th><th>FR</th>
<th>User outcome</th><th>Acceptance</th><th>Next safe action</th><th>Ledger evidence</th></tr></thead>
<tbody>{"".join(rows) or '<tr><td colspan="8">No source records.</td></tr>'}</tbody>
</table></div>
</section>
"""


def render_intent_lens(beads: list[dict]) -> str:
    """Collect prompts, goals, intents, and decisions in one provenance-preserving lens."""
    selected = [
        bead
        for bead in beads
        if bead.get("kind") in PROMPT_KINDS | INTENT_KINDS | GOAL_KINDS | {"ctl"}
    ]
    selected.sort(key=lambda bead: bead.get("ts", ""), reverse=True)
    return f"""
<section id="intent" class="view" aria-labelledby="intent-heading">
<h2 id="intent-heading">Intent</h2>
<p class="lens-note">Recorded sponsor prompts, near-term intents, long-lived goals, and control decisions.
Links resolve each source item in the Ledger.</p>
<div class="timeline">{"".join(bead_card(bead) for bead in selected) or '<p class="absence">No prompt, intent, goal, or control evidence recorded.</p>'}</div>
</section>
"""


def render_ledger(beads: list[dict]) -> str:
    """Render the complete chronological ledger, preserving every source field."""
    items = sorted(beads, key=lambda bead: bead.get("ts", ""), reverse=True)
    return f"""
<section id="ledger" class="view" aria-labelledby="ledger-heading">
<h2 id="ledger-heading">Ledger</h2>
<p class="lens-note">Append-only source evidence. Every card retains text, hash, target, agent, kind,
timestamp, and a normalized display classification.</p>
<div class="timeline">{"".join(bead_card(bead, ledger_anchor=True) for bead in items) or '<p class="absence">No ledger data recorded.</p>'}</div>
</section>
"""


def render_kanban(beads: list[dict]) -> str:
    """Render kanban columns over the full 15-state lifecycle.

    Every placement is based only on the source-owned ``state`` field.
    Missing, unsupported, and contradictory state values remain Unknown;
    record kinds do not imply lifecycle progress.  See LIFECYCLE_STATES for
    the canonical order.
    """
    # Lifecycle-state column order — same order as LIFECYCLE_STATES but
    # with UNKNOWN placed last so empty columns don't waste screen real
    # estate at the front of the board.
    ordered_states: tuple[str, ...] = (
        "intake",
        "pending",
        "triage",
        "discovery",
        "planned",
        "ready",
        "active",
        "review",
        "verification",
        "blocked",
        "evidence",
        "accepted",
        "released",
        "closed",
        "preserved",
        "promoted",
        "verified",
        "parked",
    )
    cols: dict[str, list[dict]] = {state: [] for state in ordered_states}
    cols[UNKNOWN] = []  # catch-all last
    # Human-friendly labels for the column heads.
    state_labels: dict[str, str] = {
        "intake": "📥 Intake",
        "pending": "⏳ Pending",
        "triage": "🔍 Triage",
        "discovery": "🧭 Discovery",
        "planned": "📝 Planned",
        "ready": "🟢 Ready",
        "active": "🔥 Active",
        "review": "👀 Review",
        "verification": "✔ Verify",
        "blocked": "⛔ Blocked",
        "evidence": "📊 Evidence",
        "accepted": "✅ Accepted",
        "released": "🚀 Released",
        "closed": "🗄 Closed",
        "preserved": "🛡 Preserved",
        "promoted": "⬆ Promoted",
        "verified": "🔎 Verified",
        "parked": "🅿 Parked",
        UNKNOWN: "❔ Unknown",
    }
    for b in beads:
        state = _lifecycle_state(b)
        cols[state].append(b)

    columns_html = []
    # Render in declared lifecycle order; unknown state last so it acts
    # as a catch-all column at the right edge of the board.
    for state in ordered_states:
        col_beads = cols.get(state, [])
        label = state_labels.get(state, state.title())
        columns_html.append(_render_kanban_column(state, label, col_beads))
    columns_html.append(
        _render_kanban_column(UNKNOWN, state_labels[UNKNOWN], cols[UNKNOWN])
    )
    return f"""
<section id="kanban" class="view">
<h2>🗂 Kanban Board — Lifecycle States</h2>
<p style="color:var(--fg-dim);font-size:11px;margin-bottom:12px;">
{len(ordered_states) + 1}-column lifecycle-state kanban covering all bead kinds.  State is the
explicit <code>state</code> field only.  The Unknown column catches beads with no recorded,
unsupported, or contradictory state.  Lifecycle
states: <code>{", ".join(ordered_states)}</code>, {UNKNOWN}.
</p>
<div class="kanban-grid">{"".join(columns_html)}</div>
</section>
"""


def _render_kanban_column(state: str, label: str, col_beads: list[dict]) -> str:
    """Render a single lifecycle-state kanban column."""
    cards = "".join(bead_card(b, compact=True) for b in col_beads)
    if not cards:
        cards = '<div class="empty-col">no beads</div>'
    return (
        f'<div class="kanban-col" data-col="{state}">'
        f'<div class="kanban-col-head">{label} ({len(col_beads)})</div>'
        f'<div class="kanban-col-body">{cards}</div>'
        f"</div>"
    )


def render_agents(beads: list[dict]) -> str:
    by_agent = group_by(beads, "agent")
    sorted_agents = sorted(
        by_agent.items(),
        key=lambda x: -len(x[1]),
    )
    agent_cards = []
    for agent, agent_beads in sorted_agents:
        # Find latest activity
        latest = max(agent_beads, key=lambda b: b.get("ts", ""))
        kinds = Counter(b.get("kind") for b in agent_beads)
        targets = {b.get("target", "?") for b in agent_beads}
        bead_list = "".join(bead_card(b, compact=True) for b in agent_beads)
        # Build stats row covering all 8 kinds
        all_kinds_badges = "".join(
            f'<span class="badge kind-{k}">{KIND_LABELS.get(k, k)} {kinds.get(k, 0)}</span>'
            for k in KIND_LABELS
        )
        agent_cards.append(
            f'<div class="agent-card" data-agent="{escape(agent)}">'
            f'<div class="agent-card-head">'
            f"<strong>{escape(agent)}</strong>"
            f'<span class="agent-stats">{all_kinds_badges}</span>'
            f"</div>"
            f'<div class="agent-meta">'
            f"  latest: {latest.get('ts', '?')} · "
            f"  {len(targets)} targets · "
            f"  {len(agent_beads)} beads"
            f"</div>"
            f'<div class="agent-beads">{bead_list}</div>'
            f"</div>"
        )
    return f"""
<section id="agents" class="view">
<h2>👤 Agents Dashboard ({len(sorted_agents)} ephemeral)</h2>
<p style="color:var(--fg-dim);font-size:11px;margin-bottom:12px;">
Each agent is identified by sha256(hostname+epoch)[:8]. Re-running yields a new
identity. This view lets you see who's doing what across the fleet, including
PM-lite beads (prompt/intent/goal) emitted by each agent.
</p>
<div class="agent-grid">{"".join(agent_cards)}</div>
</section>
"""


def render_projects(beads: list[dict]) -> str:
    by_target = group_by(beads, "target")
    sorted_targets = sorted(
        by_target.items(),
        key=lambda x: x[0],
    )
    target_cards = []
    for target, target_beads in sorted_targets:
        kinds = Counter(b.get("kind") for b in target_beads)
        # Determine health: green if all complete, amber if has warn, red if has reorg
        if kinds.get("reorg", 0) > 0:
            health = "red"
            health_label = "🔴 reorg"
        elif kinds.get("warn", 0) > 0 and kinds.get("complete", 0) == 0:
            health = "amber"
            health_label = "🟡 warned"
        elif kinds.get("complete", 0) > 0 and kinds.get("warn", 0) == 0:
            health = "green"
            health_label = "🟢 clean"
        elif kinds.get("complete", 0) > 0 and kinds.get("warn", 0) > 0:
            health = "amber"
            health_label = "🟡 partial"
        else:
            health = "blue"
            health_label = "🔵 in-progress"
        bead_list = "".join(bead_card(b, compact=True) for b in target_beads)
        # Show all 8 kinds in stats
        all_kinds_badges = "".join(
            f'<span class="badge kind-{k}">{KIND_LABELS.get(k, k)} {kinds.get(k, 0)}</span>'
            for k in KIND_LABELS
        )
        target_cards.append(
            f'<div class="target-card" data-health="{health}" data-target="{escape(target)}">'
            f'<div class="target-card-head">'
            f"<strong>{escape(target)}</strong>"
            f'<span class="health-pill health-{health}">{health_label}</span>'
            f'<span class="agent-stats">{all_kinds_badges}</span>'
            f"</div>"
            f'<div class="target-beads">{bead_list}</div>'
            f"</div>"
        )
    return f"""
<section id="projects" class="view">
<h2>📁 Projects / Targets ({len(sorted_targets)})</h2>
<p style="color:var(--fg-dim);font-size:11px;margin-bottom:12px;">
Group by target. Health derived from bead mix: green if all complete, red if
reorg, amber if warned but partial, blue if in-progress. PM-lite beads
(prompt/intent/goal) shown alongside kanban beads.
</p>
<div class="target-grid">{"".join(target_cards)}</div>
</section>
"""


def render_directives(beads: list[dict]) -> str:
    """Directives = warn + ctl beads. These are the MUST-READ items for agents."""
    directives = find_directives(beads)
    # Sort most recent first
    directives = sorted(directives, key=lambda b: b.get("ts", ""), reverse=True)

    # Highlight critical (warn beads targeting strategy/backlog)
    critical = [
        b
        for b in directives
        if b.get("kind") == "warn"
        and any(
            k in b.get("target", "").lower()
            for k in ("strategy", "backlog", "wbs", "lane")
        )
    ]

    critical_html = ""
    if critical:
        critical_html = (
            '<div class="critical-banner">'
            "<strong>🚨 CRITICAL DIRECTIVES</strong> "
            f"({len(critical)} items — strategy/backlog/lane at risk)"
            + "".join(bead_card(b) for b in critical)
            + "</div>"
        )

    # All directives (most recent first)
    all_html = "".join(bead_card(b) for b in directives)

    return f"""
<section id="directives" class="view">
<h2>📢 Directives (warn + ctl beads)</h2>
<p style="color:var(--fg-dim);font-size:11px;margin-bottom:12px;">
Agents: this is the section you MUST scan each refresh. New warn/ctl beads here
instruct you on changes, blockers, and operational state. Other agents may be
waiting for you to react.
</p>
{critical_html}
<div class="view-section">
<h2>📋 All Directives ({len(directives)})</h2>
{all_html}
</div>
</section>
"""


def render_prompts(beads: list[dict]) -> str:
    """Prompts view = how-got-here. User/agent prompts that motivated work."""
    prompts = find_prompts(beads)
    prompts = sorted(prompts, key=lambda b: b.get("ts", ""), reverse=True)
    prompts_html = "".join(bead_card(b) for b in prompts)

    # Each prompt often has a chain of intents that follow it (by target pattern)
    by_target = group_by(prompts, "target")
    prompt_summary = "".join(
        f'<div class="agent-chip">💬 {escape(t)}: {len(v)} prompt(s)</div>'
        for t, v in sorted(by_target.items())
    )

    # Trace: show recent prompt → related intent → related goal
    trace_html = ""
    if prompts:
        # Get all intents and goals for context
        intents = find_intents(beads)
        goals = find_goals(beads)
        # Get all beads within ±5 minutes of the prompt (rough temporal correlation)
        trace_items = []
        for p in sorted(prompts, key=lambda b: b.get("ts", ""), reverse=True)[:3]:
            target = p.get("target", "")
            try:
                p_ts = dt.datetime.fromisoformat(p.get("ts", "").replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                p_ts = None
            # Find related intent by target similarity OR temporal proximity
            related_intent = None
            for i in sorted(intents, key=lambda b: b.get("ts", ""), reverse=True):
                if i.get("target") == target:
                    related_intent = i
                    break
                # Temporal proximity: within 10 minutes
                if p_ts:
                    try:
                        i_ts = dt.datetime.fromisoformat(
                            i.get("ts", "").replace("Z", "+00:00")
                        )
                        if abs((i_ts - p_ts).total_seconds()) < 600:
                            related_intent = i
                            break
                    except (ValueError, AttributeError):
                        continue
            # Same for goals
            related_goal = None
            for g in sorted(goals, key=lambda b: b.get("ts", ""), reverse=True):
                if g.get("target") == target:
                    related_goal = g
                    break
                if p_ts:
                    try:
                        g_ts = dt.datetime.fromisoformat(
                            g.get("ts", "").replace("Z", "+00:00")
                        )
                        if abs((g_ts - p_ts).total_seconds()) < 3600:  # 1 hour window
                            related_goal = g
                            break
                    except (ValueError, AttributeError):
                        continue
            trace_items.append(
                f'<div class="trace-row">'
                f'<div class="trace-step trace-prompt">'
                f'<div class="trace-step-label">💬 Prompt</div>'
                f'<div class="trace-step-text">{escape(p.get("text", "")[:200])}</div>'
                f'<div class="trace-step-meta">{escape(target)} · {p.get("ts", "?")}</div>'
                f"</div>"
                + (
                    f'<div class="trace-arrow">→</div>'
                    f'<div class="trace-step trace-intent">'
                    f'<div class="trace-step-label">🎯 Intent</div>'
                    f'<div class="trace-step-text">{escape(related_intent.get("text", "")[:200])}</div>'
                    f'<div class="trace-step-meta">{escape(related_intent.get("target", ""))} · {related_intent.get("ts", "?")}</div>'
                    f"</div>"
                    if related_intent
                    else ""
                )
                + (
                    f'<div class="trace-arrow">→</div>'
                    f'<div class="trace-step trace-goal">'
                    f'<div class="trace-step-label">🏁 Goal</div>'
                    f'<div class="trace-step-text">{escape(related_goal.get("text", "")[:200])}</div>'
                    f'<div class="trace-step-meta">{escape(related_goal.get("target", ""))} · {related_goal.get("ts", "?")}</div>'
                    f"</div>"
                    if related_goal
                    else ""
                )
                + "</div>"
            )
        trace_html = (
            '<div class="view-section">'
            "<h2>🔗 Trace: Prompt → Intent → Goal</h2>"
            f'<div class="trace-grid">{"".join(trace_items)}</div>'
            "</div>"
        )

    return f"""
<section id="prompts" class="view">
<h2>💬 Prompts (how-got-here)</h2>
<p style="color:var(--fg-dim);font-size:11px;margin-bottom:12px;">
User/agent prompts that motivated work. This is the "why did we start?" layer
of the PM-lite stack. Pair with <a href="#intents">#intents</a> (what-now) and
<a href="#goals">#goals</a> (why-work).
</p>
<div class="view-section">
<h2>🎯 By Target</h2>
<div class="agent-list">{prompt_summary}</div>
</div>
{trace_html}
<div class="view-section">
<h2>📋 All Prompts ({len(prompts)})</h2>
{prompts_html}
</div>
</section>
"""


def render_intents(beads: list[dict]) -> str:
    """Intents = intent beads (PM-lite: what-now). Near-term session plans."""
    intents = find_intents(beads)
    intents = sorted(intents, key=lambda b: b.get("ts", ""), reverse=True)
    intents_html = "".join(bead_card(b) for b in intents)

    # Group by agent
    group_by(intents, "agent")
    intent_count = Counter(b.get("agent") for b in intents)
    intent_summary = "".join(
        f'<div class="agent-chip">{escape(a)}: {n} intent(s)</div>'
        for a, n in sorted(intent_count.items(), key=lambda x: -x[1])
    )

    return f"""
<section id="intents" class="view">
<h2>🎯 Intents (what-now)</h2>
<p style="color:var(--fg-dim);font-size:11px;margin-bottom:12px;">
Each intent bead = a near-term session plan. PM-lite: what is this session
trying to do? Pair with <a href="#prompts">#prompts</a> (why we started) and
<a href="#goals">#goals</a> (the long-lived objective).
</p>
<div class="view-section">
<h2>👥 By Agent</h2>
<div class="agent-list">{intent_summary}</div>
</div>
<div class="view-section">
<h2>📋 All Intents ({len(intents)})</h2>
{intents_html}
</div>
</section>
"""


def render_goals(beads: list[dict]) -> str:
    """Goals view = goal beads (PM-lite: why-work) + completed milestones."""
    goals = find_goals(beads)
    goals = sorted(goals, key=lambda b: b.get("ts", ""), reverse=True)
    goals_html = "".join(bead_card(b) for b in goals)

    completed = find_completed_goals(beads)
    completed = sorted(completed, key=lambda b: b.get("ts", ""), reverse=True)
    completed_html = "".join(bead_card(b, compact=True) for b in completed[:30])

    goals_of_concern = find_goals_of_concern(beads)
    concern_html = ""
    if goals_of_concern:
        concern_html = (
            '<div class="amber-banner">'
            "<strong>🟡 GOALS OF CONCERN</strong> "
            f"({len(goals_of_concern)} items — these are blocking progress)"
            + "".join(bead_card(b) for b in goals_of_concern)
            + "</div>"
        )

    return f"""
<section id="goals" class="view">
<h2>🏁 Goals (why-work)</h2>
<p style="color:var(--fg-dim);font-size:11px;margin-bottom:12px;">
Long-lived objectives (PM-lite: why-work). Pair with
<a href="#prompts">#prompts</a> (how-got-here) and
<a href="#intents">#intents</a> (what-now). Goals-of-concern = warn beads
flagging blocking issues.
</p>
{concern_html}
<div class="view-section">
<h2>🏁 Goal Definitions ({len(goals)})</h2>
{goals_html}
</div>
<div class="view-section">
<h2>✓ Completed Milestones ({len(completed)} total, showing last 30)</h2>
{completed_html}
</div>
</section>
"""


def render_timeline(beads: list[dict]) -> str:
    timeline = sorted(beads, key=lambda b: b.get("ts", ""), reverse=True)
    items = []
    for b in timeline:
        kind = b.get("kind", "?")
        color = KIND_COLORS.get(kind, "#6b7280")
        items.append(
            f'<div class="tl-item" style="border-left-color:{color};">'
            f'<div class="tl-meta">'
            f'  <span class="bead-kind" style="background:{color};">{KIND_LABELS.get(kind, kind)}</span>'
            f"  <strong>{escape(b.get('target', '?'))}</strong>"
            f'  <span class="tl-ts">{b.get("ts", "?")} · {escape(b.get("agent", "?"))} · id={b.get("id", "?")}</span>'
            f"</div>"
            f'<div class="tl-text">{escape(b.get("text", ""))}</div>'
            f"</div>"
        )
    return f"""
<section id="timeline" class="view">
<h2>⏱ Timeline (append-only, newest first)</h2>
<p style="color:var(--fg-dim);font-size:11px;margin-bottom:12px;">
Full chronological feed. Every bead in order.
</p>
<div class="timeline">{"".join(items)}</div>
</section>
"""


def render_cli_panel() -> str:
    return """
<div class="cli-panel">
<h3>➕ Bead CLI Reference (8 kinds, 2 layers)</h3>
<p style="color:var(--fg-dim);font-size:11px;margin-bottom:8px;">
Append-only. Agents publish work via <code>bead-ctl.sh &lt;kind&gt; &lt;target&gt; "&lt;text&gt;"</code>.
</p>
<details><summary style="cursor:pointer;color:var(--accent-2);font-weight:600;">📂 Kanban layer (work state)</summary>
<div class="cmd-grid">
  <div class="cmd">$ bead-ctl.sh claim phenoAI/65 "WIP: porting cheap-llm providers"</div>
  <div class="cmd">$ bead-ctl.sh warn OmniRoute/493 "governance ledger stale"</div>
  <div class="cmd">$ bead-ctl.sh ctl pheno/272 "preservation snapshot in progress"</div>
  <div class="cmd">$ bead-ctl.sh complete pheno/272 "merge preservation snapshot 951k lines"</div>
  <div class="cmd">$ bead-ctl.sh reorg Planify/50 "split into per-bug sub-issues"</div>
</div>
</details>
<details style="margin-top:8px;"><summary style="cursor:pointer;color:var(--accent-2);font-weight:600;">💼 PM-lite layer (why / what / how)</summary>
<div class="cmd-grid">
  <div class="cmd">$ bead-ctl.sh prompt user-20260809-2250 "do all cockpit update..."</div>
  <div class="cmd">$ bead-ctl.sh intent session-20260809-2051 "do all 3 user-authorized actions"</div>
  <div class="cmd">$ bead-ctl.sh goal next-cycle/v0.12 "tracera + AgilePlus become functional"</div>
</div>
</details>
<details style="margin-top:8px;"><summary style="cursor:pointer;color:var(--accent-2);font-weight:600;">🔧 Operational</summary>
<div class="cmd-grid">
  <div class="cmd">$ bead-ctl.sh agent</div>
  <div class="cmd">$ bead-ctl.sh dedup</div>
  <div class="cmd">$ bead-ctl.sh stats</div>
</div>
</details>
</div>
"""


# ---------- Compose ----------
CSS = """
:root {
  --bg: #0a0a0a; --bg-1: #111; --bg-2: #1a1a1a; --bg-3: #222;
  --fg: #e4e4e7; --fg-dim: #a1a1aa; --fg-muted: #71717a;
  --accent: #6366f1; --accent-2: #8b5cf6; --success: #10b981;
  --warn: #f59e0b; --error: #ef4444; --info: #3b82f6;
  --border: #2a2a2a;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, 'SF Mono', Menlo, Consolas, monospace;
  background: var(--bg); color: var(--fg); padding: 24px; line-height: 1.5;
}
h1 { font-size: 28px; font-weight: 700; margin-bottom: 8px;
  background: linear-gradient(90deg, #fff, #a1a1aa);
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
h2 { font-size: 18px; font-weight: 600; margin: 24px 0 12px; color: var(--accent-2); }
.meta { color: var(--fg-muted); font-size: 12px; margin-bottom: 24px; }
.meta code { background: var(--bg-2); padding: 2px 6px; border-radius: 4px; color: var(--accent-2); }

/* Nav */
.nav {
  display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 24px;
  background: var(--bg-1); border: 1px solid var(--border); border-radius: 8px;
  padding: 8px; position: sticky; top: 0; z-index: 10;
}
.nav-item {
  padding: 6px 14px; border-radius: 4px; color: var(--fg-dim);
  text-decoration: none; font-size: 12px; font-weight: 600;
  transition: background 0.15s;
}
.nav-item:hover { background: var(--bg-3); color: var(--fg); }
.nav-item.active { background: var(--accent); color: #fff; }

/* Stats cards */
.summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 12px; margin: 16px 0; }
.card { background: var(--bg-1); border: 1px solid var(--border); border-radius: 8px;
  padding: 14px; }
.card .label { font-size: 10px; color: var(--fg-muted); text-transform: uppercase;
  letter-spacing: 0.05em; margin-bottom: 6px; }
.card .value { font-size: 24px; font-weight: 700; }
.card .delta { font-size: 10px; color: var(--fg-dim); margin-top: 4px; }

/* Sections */
.view-section { background: var(--bg-1); border: 1px solid var(--border);
  border-radius: 8px; padding: 16px; margin: 16px 0; }
.view { display: none; }
.view.active { display: block; }

/* Beads */
.bead-card { background: var(--bg-2); border: 1px solid var(--border);
  border-radius: 6px; padding: 10px 12px; margin: 6px 0; font-size: 13px; }
.bead-card.compact { padding: 6px 10px; font-size: 12px; }
.bead-card-head { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.bead-text { color: var(--fg-dim); }
.bead-meta { font-size: 10px; color: var(--fg-muted); margin-top: 4px; }
.bead-kind { display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 10px; font-weight: 700; color: #fff; white-space: nowrap; }
.badge { display: inline-block; padding: 2px 6px; border-radius: 4px;
  font-size: 10px; background: var(--bg-3); color: var(--fg-dim); margin-left: 4px; }
.badge.bead-fr { background: var(--accent); color: #fff;
  font-weight: 700; letter-spacing: 0.03em; }
.outcome-line { display: block; margin-top: 4px; color: var(--success);
  font-size: 10px; font-style: italic; line-height: 1.3;
  border-top: 1px dashed var(--border); padding-top: 4px;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.kind-claim { background: var(--info); color: #fff; }
.kind-complete { background: var(--success); color: #000; }
.kind-warn { background: var(--warn); color: #000; }
.kind-ctl { background: var(--accent-2); color: #fff; }

/* Kanban */
.kanban-grid { display: grid; grid-template-columns: repeat(15, minmax(180px, 1fr));
  gap: 10px; margin-top: 12px; overflow-x: auto; min-width: 100%; }
.kanban-col { background: var(--bg-1); border: 1px solid var(--border);
  border-radius: 8px; padding: 10px; min-height: 200px; }
.kanban-col-head { font-size: 12px; font-weight: 700; margin-bottom: 8px;
  color: var(--accent-2); letter-spacing: 0.03em; }
.kanban-col-body { display: flex; flex-direction: column; gap: 6px; }
.empty-col { color: var(--fg-muted); font-size: 11px; text-align: center;
  padding: 16px; font-style: italic; }

/* Agents grid */
.agent-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 12px; margin-top: 12px; }
.agent-card { background: var(--bg-1); border: 1px solid var(--border);
  border-radius: 8px; padding: 14px; }
.agent-card-head { display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px; }
.agent-stats { display: flex; gap: 4px; }
.agent-meta { font-size: 11px; color: var(--fg-muted); margin-bottom: 8px; }
.agent-list { display: flex; flex-wrap: wrap; gap: 6px; }
.agent-chip { display: inline-block; padding: 4px 10px; background: var(--bg-3);
  border: 1px solid var(--border); border-radius: 12px;
  font-family: monospace; font-size: 11px; }

/* Targets */
.target-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 12px; margin-top: 12px; }
.target-card { background: var(--bg-1); border: 1px solid var(--border);
  border-radius: 8px; padding: 14px; }
.target-card[data-health="red"] { border-left: 4px solid var(--error); }
.target-card[data-health="amber"] { border-left: 4px solid var(--warn); }
.target-card[data-health="green"] { border-left: 4px solid var(--success); }
.target-card[data-health="blue"] { border-left: 4px solid var(--info); }
.target-card-head { display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px; flex-wrap: wrap; gap: 6px; }
.health-pill { font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600; }
.health-red { background: var(--error); color: #fff; }
.health-amber { background: var(--warn); color: #000; }
.health-green { background: var(--success); color: #000; }
.health-blue { background: var(--info); color: #fff; }

/* Directives */
.critical-banner { background: rgba(239, 68, 68, 0.15); border: 2px solid var(--error);
  border-radius: 8px; padding: 16px; margin: 16px 0; }
.critical-banner strong { color: var(--error); font-size: 14px;
  display: block; margin-bottom: 8px; }
.amber-banner { background: rgba(245, 158, 11, 0.15); border: 2px solid var(--warn);
  border-radius: 8px; padding: 16px; margin: 16px 0; }
.amber-banner strong { color: var(--warn); font-size: 14px;
  display: block; margin-bottom: 8px; }

/* Timeline */
.timeline { display: flex; flex-direction: column; gap: 6px; }
.tl-item { background: var(--bg-2); border-left: 3px solid var(--accent);
  padding: 10px 14px; border-radius: 4px; font-size: 12px; }
.tl-meta { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.tl-ts { color: var(--fg-muted); font-size: 10px; }
.tl-text { color: var(--fg-dim); }

/* CLI panel */
.cli-panel { background: var(--bg-1); border: 1px solid var(--border);
  border-radius: 8px; padding: 16px; margin: 24px 0; }
.cmd-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 6px; }
.cmd { background: var(--bg-2); padding: 6px 10px; border-radius: 4px;
  font-family: monospace; font-size: 11px; color: var(--success); }

/* Latest directive banner */
.latest-directive { background: var(--bg-1); border: 2px solid var(--warn);
  border-radius: 8px; padding: 12px 16px; margin: 0 0 16px; animation: pulse 3s infinite; }
.latest-directive-head { display: flex; align-items: center; gap: 8px; margin-bottom: 6px;
  font-size: 12px; }
.latest-directive-text { color: var(--fg); font-size: 14px; margin-bottom: 6px; }
.latest-directive-cta { font-size: 11px; color: var(--fg-dim); }
.latest-directive-cta a { color: var(--accent); }

/* PM-lite cards (Overview section) */
.pm-lite-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px; margin-top: 8px; }
.pm-lite-card { background: var(--bg-2); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px; border-left: 4px solid var(--border); }
.pm-lite-card.pm-prompt { border-left-color: var(--prompt, #f97316); }
.pm-lite-card.pm-intent { border-left-color: var(--intent, #14b8a6); }
.pm-lite-card.pm-goal { border-left-color: var(--goal, #ec4899); }
.pm-lite-label { font-size: 11px; color: var(--fg-muted); text-transform: uppercase;
  letter-spacing: 0.05em; margin-bottom: 4px; }
.pm-lite-count { font-size: 28px; font-weight: 700; margin-bottom: 4px; }
.pm-lite-latest { font-size: 12px; color: var(--fg-dim); margin-bottom: 4px;
  overflow: hidden; text-overflow: ellipsis; }
.pm-lite-ts { font-size: 10px; color: var(--fg-muted); }

/* Trace view (Prompt → Intent → Goal chain) */
.trace-grid { display: flex; flex-direction: column; gap: 16px; }
.trace-row { display: flex; gap: 12px; align-items: stretch; flex-wrap: wrap; }
.trace-step { background: var(--bg-2); border: 1px solid var(--border);
  border-radius: 8px; padding: 12px; flex: 1; min-width: 220px;
  border-left: 4px solid var(--border); }
.trace-step.trace-prompt { border-left-color: #f97316; }
.trace-step.trace-intent { border-left-color: #14b8a6; }
.trace-step.trace-goal { border-left-color: #ec4899; }
.trace-step-label { font-size: 10px; color: var(--fg-muted); text-transform: uppercase;
  letter-spacing: 0.05em; margin-bottom: 6px; }
.trace-step-text { color: var(--fg); font-size: 12px; margin-bottom: 6px;
  line-height: 1.4; }
.trace-step-meta { font-size: 10px; color: var(--fg-muted); font-family: monospace; }
.trace-arrow { display: flex; align-items: center; font-size: 24px;
  color: var(--accent-2); padding: 0 4px; min-width: 24px; justify-content: center; }

footer { margin-top: 32px; padding-top: 16px; border-top: 1px solid var(--border);
  color: var(--fg-muted); font-size: 11px; text-align: center; }
.tick { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  background: var(--success); margin-right: 6px; animation: pulse 2s infinite; }
@keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
.directive-ts { color: var(--fg-muted); font-size: 10px; }

/* Filter row */
.filter-row { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
.filter-row label { color: var(--fg-dim); font-size: 11px; align-self: center; }
.filter-select, .filter-input { background: var(--bg-3); color: var(--fg); border: 1px solid var(--border);
  padding: 6px 10px; border-radius: 4px; font-family: inherit; font-size: 12px; }
.filter-select:focus, .filter-input:focus { outline: none; border-color: var(--accent); }
.filter-input { background: var(--bg-3); color: var(--fg); border: 1px solid var(--border);
  padding: 6px 10px; border-radius: 4px; font-family: inherit; font-size: 12px;
  flex: 1; min-width: 200px; }
.warning-card { background: rgba(245, 158, 11, 0.08); border: 1px solid var(--warn);
  border-radius: 8px; padding: 12px; margin: 10px 0; }
.warning-card h3 { color: var(--warn); font-size: 13px; margin-bottom: 8px; }
.warning-contract, .recorded-fields { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 6px; margin: 8px 0; }
.warning-contract div, .recorded-fields div { background: var(--bg-2); padding: 6px; border-radius: 4px; }
.warning-contract dt, .recorded-fields dt { color: var(--fg-muted); font-size: 10px; text-transform: uppercase; }
.warning-contract dd, .recorded-fields dd { color: var(--fg); font-size: 11px; overflow-wrap: anywhere; }
.provenance-link { color: var(--accent-2); }
.perspective { margin: 10px 0; padding: 10px; border: 1px solid var(--border); border-radius: 6px; }
.ledger-focus { outline: 3px solid var(--accent-2); outline-offset: 3px; }
.absence, .lens-note { color: var(--fg-dim); font-size: 12px; margin-bottom: 12px; }
@media (max-width: 760px) {
  body { padding: 12px; }
  .kanban-grid { grid-template-columns: 1fr; }
  .agent-grid, .target-grid { grid-template-columns: 1fr; }
  .nav { position: static; }
  .filter-row { display: grid; grid-template-columns: 1fr; }
  .filter-row label { margin-top: 4px; }
  .filter-input { min-width: 0; }
}
"""


def render_html(beads: list[dict], generated_at: str, content_hash: str) -> str:
    # The renderer consumes the explicit display model, never raw ledger fields.
    beads = normalize_beads(beads)
    summary = summarize(beads)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bead Cockpit — bead-cockpit-{generated_at[:10].replace("-", "")}-{content_hash}</title>
<style>{CSS}</style>
</head>
<body>
<h1>📿 Bead Cockpit — Static Ledger Evidence</h1>
<div class="meta">
  Generated as of <code>{generated_at}</code> ·
  ID: <code>bead-cockpit-{generated_at[:10].replace("-", "")}-{content_hash}</code> ·
  {summary["total"]} beads · {summary["targets_count"]} targets · {summary["agents_count"]} agents<br>
  Output filename is caller-selected; the ID above is the content-derived snapshot identity.
</div>

{nav_html("command")}
{render_filters(beads)}
{render_command(summary, beads, generated_at)}
{render_workboard(beads)}
{render_kanban(beads)}
{render_perspectives(beads)}
{render_dependencies(beads)}
{render_agents(beads)}
{render_repositories(beads)}
{render_traceability(beads)}
{render_intent_lens(beads)}
{render_ledger(beads)}

<footer>
Generated as of {generated_at} · ID: <code>bead-cockpit-{generated_at[:10].replace("-", "")}-{content_hash}</code><br>
Output filename is caller-selected; preserve this ID and source ledger path for provenance.<br>
Source: <code>/Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-dag/beads.jsonl</code> · {summary["total"]} beads · {summary["targets_count"]} targets · {summary["agents_count"]} agents<br>
<span style="opacity:0.6;">Append-only source projection · seven lenses · regenerate to ingest newer evidence</span>
</footer>

<script>
window.TRACEABILITY_SCHEMA_V1=true;
window.COCKPIT_LIFECYCLE_STATES=['intake','pending','triage','discovery','planned','ready','active','review','verification','blocked','evidence','accepted','released','closed','preserved','promoted','verified','parked','unknown'];
const traceabilityWarning = document.createElement('span');
traceabilityWarning.style.opacity = '0.6';
traceabilityWarning.textContent = 'Unknown or unlinked fields are not source evidence.';
document.querySelector('footer').append(document.createElement('br'), traceabilityWarning);
const views = ['command', 'workboard', 'dependencies', 'agents', 'repositories', 'traceability', 'intent', 'ledger'];
const navItems = document.querySelectorAll('.nav-item');
const viewSections = document.querySelectorAll('.view');

function showView(viewId) {{
  views.forEach(v => {{
    const sec = document.getElementById(v);
    if (sec) sec.classList.toggle('active', v === viewId);
  }});
  navItems.forEach(n => {{
    n.classList.toggle('active', n.getAttribute('href') === '#' + viewId);
  }});
}}

function applyRoute() {{
  const ledgerMatch = location.hash.match(/^#ledger\\/([^/]+)$/);
  const viewId = ledgerMatch ? 'ledger' : location.hash.slice(1);
  showView(views.includes(viewId) ? viewId : 'command');
  if (ledgerMatch) {{
    const card = document.getElementById('ledger-' + decodeURIComponent(ledgerMatch[1]));
    if (card) {{
      card.classList.add('ledger-focus');
      card.focus({{preventScroll: true}});
      card.scrollIntoView({{block: 'center'}});
    }}
  }}
}}

document.querySelectorAll('[data-filter]').forEach(control => {{
  control.addEventListener('input', applyFilters);
  control.addEventListener('change', applyFilters);
}});

function applyFilters() {{
  const selected = Object.fromEntries([...document.querySelectorAll('[data-filter]')]
    .map(control => [control.dataset.filter, control.value.trim().toLowerCase()]));
  document.querySelectorAll('.filterable').forEach(card => {{
    const matches = Object.entries(selected).every(([field, value]) => {{
      if (!value) return true;
      const haystack = field === 'text' ? card.textContent : (card.dataset[field] || '');
      return haystack.toLowerCase().includes(value);
    }});
    card.hidden = !matches;
  }});
}}

window.addEventListener('hashchange', applyRoute);
applyRoute();
</script>
</body>
</html>
"""


def write_html_atomically(out_file: Path, html: str) -> None:
    """Replace an artifact only after its full new contents are durable.

    A direct ``write_text`` truncates the existing named cockpit before an
    ENOSPC error is reported.  Keeping the temporary file in the destination
    directory makes ``replace`` atomic on the same filesystem and preserves
    the last valid cockpit when rendering cannot finish.
    """
    required_bytes = 2 * len(html.encode("utf-8")) + 64 * 1024 * 1024
    available_bytes = shutil.disk_usage(out_file.parent).free
    if available_bytes < required_bytes:
        raise OSError(
            f"insufficient disk space for cockpit output: {available_bytes:,} bytes free; "
            f"need at least {required_bytes:,} bytes (2x rendered HTML + 64 MiB). "
            "Last valid output was left intact."
        )
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=out_file.parent,
            prefix=f".{out_file.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(html)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(out_file)
    except Exception:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description="Render the static bead cockpit.")
    parser.add_argument(
        "--output",
        type=Path,
        help="Write HTML to this path instead of a timestamped cockpit file.",
    )
    args = parser.parse_args()
    beads = load_beads()
    generated_at = now_iso()
    structural = json.dumps(beads, sort_keys=True, separators=(",", ":"))
    content_hash = hashlib.sha256(structural.encode()).hexdigest()[:8]
    date_part = generated_at[:10].replace("-", "")
    time_part = generated_at[11:19].replace(":", "")
    # Iter8 (FR-COCKPIT-MULTIVIEW-KANBAN-LIFECYCLE): when no --output is
    # given write to a deterministic iter-tagged filename so the artifact
    # is identifiable and does not steal the leapfrog's latest.html.  The
    # -multiview-kanban15 suffix encodes both the iter tag and the
    # lifecycle-state kanban feature.
    out_file = (
        args.output.expanduser()
        if args.output
        else (
            OUT_DIR
            / f"bead-cockpit-{date_part}-{time_part}-{content_hash}-multiview-kanban15.html"
        )
    )
    out_file.parent.mkdir(parents=True, exist_ok=True)
    html = render_html(beads, generated_at, content_hash)
    write_html_atomically(out_file, html)
    if not args.output:
        latest = OUT_DIR / "latest.html"
        if latest.is_symlink() or latest.exists():
            latest.unlink()
        latest.symlink_to(out_file.name)
    out = (
        f"bead-cockpit: wrote {out_file}\n"
        f"  hash: {content_hash}\n"
        f"  size: {len(html):,} bytes\n"
        f"  beads: {len(beads)}\n"
        "  views: 8 (command/workboard/dependencies/agents/repositories/traceability/intent/ledger)\n"
    )
    sys.stdout.write(out)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
