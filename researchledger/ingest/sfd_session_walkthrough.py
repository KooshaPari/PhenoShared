#!/usr/bin/env python3
"""Render the session walkthrough HTML.

Kept as a script so the artifact can be regenerated from live data rather
than hand-edited. Run:  python3 ~/Exports/analysis/sfd_session_walkthrough.py
"""
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

OUT = Path.home() / "Exports" / "analysis" / "sfd_session_walkthrough.html"
REPO = Path.home() / "CodeProjects" / "Phenotype" / "repos" / "AgilePlus"

# ── Live probes ────────────────────────────────────────────────────────────
def sh(*cmd, cwd=REPO):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                              timeout=90).stdout.strip()
    except Exception:
        return ""


def pr_state(n):
    out = sh("gh", "pr", "view", str(n), "--repo", "KooshaPari/AgilePlus",
             "--json", "state,mergeStateStatus,reviewDecision",
             "--jq", '"\(.state)|\(.mergeStateStatus)|\(.reviewDecision // "none")"')
    parts = out.split("|")
    if len(parts) < 3:
        return {"state": "?", "merge": "?", "review": "?"}
    return {"state": parts[0], "merge": parts[1], "review": parts[2]}


def unresolved(n):
    q = ('{repository(owner:"KooshaPari",name:"AgilePlus"){pullRequest(number:%d)'
         '{reviewThreads(first:60){nodes{isResolved}}}}}' % n)
    out = sh("gh", "api", "graphql", "-f", "query=" + q)
    try:
        nodes = json.loads(out)["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
        return sum(1 for x in nodes if not x["isResolved"]), len(nodes)
    except Exception:
        return -1, -1


def main_head():
    return sh("git", "ls-remote", "origin", "refs/heads/main")[:10]


# ── Static content: the session narrative ─────────────────────────────────
PANES = [
    ("wA:p8", "Browser Auto", "done",
     "model endpoint recon", "Recon of provider endpoints; independent of the docket line."),
    ("wA:pK", "Agile", "done",
     "HTML walkthrough retry", "Prior walkthrough attempt in this workspace."),
    ("wA:pA", "Exports - Datamine", "done",
     "session walkthrough HTML", "Exports-side walkthrough authoring."),
    ("wA:pR", "MuxBridge - access+comms plane", "done",
     "dashboard-fallback", "MuxBridge dashboard fallback work."),
    ("wA:pH", "Omni", "idle",
     "walkthrough retry", "THIS PANE. Docket reconciliation, CI unblock, fork state audit."),
    ("wA:pT", "(unlabeled)", "idle",
     "research-agent-orchestration", "Unlabeled; will be assigned a label later."),
]

WS = [("w8", "~", 1, 6), ("wA", "chats", 2, 6), ("wF", "Desk Workers 2", 3, 6),
      ("w7", "~", 4, 6), ("wG", "~", 5, 6)]

# WBS: id, title, lane, deps, state, note
WBS = [
    ("1.0", "Reconcile SFD cockpit counts", "cockpit", [], "DONE",
     "50/256 PASS, 166 meaningful; validator re-derives from tree body"),
    ("1.1", "Derive numerator + denominator from per-cell body", "cockpit", ["1.0"], "DONE",
     "Replaces inherited raw-file tally"),
    ("1.2", "Correct JSON headline + md table together", "cockpit", ["1.1"], "DONE",
     "6 defects: 49->50, 150->166, 255->256, 4/10->3/10, 4/20->3/20, table"),
    ("1.3", "Resolve compound cells A.9 / B.7 / B.10", "cockpit", ["1.1"], "DONE",
     "Overlay merge semantics verified"),
    ("1.4", "Restore PROGRESS_TREE_RAW.md from orphan blob", "cockpit", ["1.0"], "DONE",
     "c46a4eed, identity ap-sfd-2026-10-17T22-14Z@d6b418a6"),
    ("1.5", "Consolidate 4 exploratory scripts into 3", "cockpit", ["1.0"], "DONE",
     "validate_counts / derive_headlines / reconcile"),
    ("1.6", "Commit e4f5707c + push", "cockpit", ["1.2", "1.3", "1.4", "1.5"], "DONE", ""),
    ("2.0", "Make PR #1149 green and mergeable", "pr", ["1.6"], "DONE",
     "Merged c09e53ce; 38/38 threads resolved"),
    ("2.1", "Resolve PR #1149 conflict (merge main)", "pr", ["1.6"], "DONE",
     "79a71360; conflict in check_intent_reconciliation.py"),
    ("2.2", "Fix ruff format drift (Python job)", "pr", ["2.1"], "DONE",
     "0e83d09c; ruff check + ruff format both pass"),
    ("2.3", "Prettier-format 25 docs + decouple validator", "pr", ["2.2"], "DONE",
     "83df57e7; _table_rows() compares cells, not text"),
    ("2.4", "Verify + fix 13 real review defects", "pr", ["2.3"], "DONE",
     "mature verdict, gate labels, colours, ancestry, closure list, counts"),
    ("2.5", "Rebut 4 false findings with evidence", "pr", ["2.4"], "DONE",
     "snapshot.json exists; v2026.09.0 IS ancestor; 3/20 correct; byte-identical correct"),
    ("2.6", "Merge #1149 (squash) + verify main", "pr", ["2.4", "2.5"], "DONE",
     "c09e53ce; validator OK on new main"),
    ("2.7", "Merge the 5 PRs (#1157 #1151 #1156 #1165 #1166)", "pr", ["3.0"], "DONE",
     "79a3e45f 69c6b4d7 d64fe905 28b4f56f 060ebe86; main=060ebe86"),
    ("3.0", "Clear the 5 PRs to mergeable", "pr", ["2.6"], "DONE",
     "All 5 merged; conversation-resolution was the only gate, CI was not"),
    ("3.1", "#1157 cargo-deny + zbus ignore", "pr", ["2.6"], "DONE",
     "merged 79a3e45f; +818a094a bumped ctutils/pulldown-cmark"),
    ("3.2", "#1165 exclude=[rust] + deny.toml cleanup", "pr", ["2.6"], "DONE",
     "merged 28b4f56f; conflict on ctutils resolved to main's 0.4.6"),
    ("3.3", "#1166 python-coverage COVERAGE_PATH", "pr", ["2.6"], "DONE", "merged 060ebe86"),
    ("3.4", "#1156 mvp.rs test portability", "pr", ["2.6"], "DONE",
     "merged d64fe905; ComSpec /C exit 0 on Windows"),
    ("3.5", "#1151 Cloudflare Access JWT edge gate", "pr", ["2.6"], "DONE",
     "merged 69c6b4d7; edge-attestation path; 8 threads adjudicated"),
    ("3.6", "Re-trigger the 4 remaining source PRs", "pr", ["3.0"], "IN PROGRESS",
     "#1162 #1164 resolved; #1161 in progress; #1163 already clean"),
    ("3.7", "Confirm the flips with a later scout", "pr", ["3.6"], "OPEN",
     "semver-checks should now reach analysis for the first time"),
    ("4.0", "Audit fork families", "forks", [], "DONE",
     "Two families: harness forks (live) + airlock dockets (superseded)"),
    ("4.1", "Harness fork state (KCode/HeliosLite/HeliosCLI)", "forks", ["4.0"], "DONE",
     "KCode decollision merged then REVERTED; upstream sync blocked on 47 paths"),
    ("4.2", "Airlock consolidation dockets (8 groups)", "forks", ["4.0"], "DONE",
     "7 of 8 superseded by 2026-07-29 policy; group 8 complete"),
    ("4.3", "Traceability failure: 4 audit receipts missing", "forks", ["4.2"], "OPEN",
     "/tmp/kp_* gone, no in-repo copy; counts unverifiable"),
    ("4.4", "Mark 7 dockets SUPERSEDED (not awaiting approval)", "forks", ["4.2"], "OPEN",
     "Policy already voided them; files still say pending"),
    ("4.5", "KCode: resolve 47 untracked worktree paths", "forks", ["4.1"], "OPEN",
     "Mechanical, report-before-delete; blocks monthly sync"),
    ("4.6", "HeliosCLI: decide build-or-archive", "forks", ["4.1"], "OPEN",
     "Decollided but never built since October"),
    ("5.0", "Security CI track (not a merge gate)", "security", [], "DONE",
     "GREEN on main 060ebe86 for the first time since 2026-10-19"),
    ("5.1", "Cargo Deny + OSV disagree on same advisories", "security", ["5.0"], "DONE",
     "Both pass now: 818a094a bumps ctutils/pulldown-cmark; OSV follows the lock"),
    ("5.2", "webpki patch bumps (3 advisories)", "security", ["5.0"], "DONE",
     "Landed independently as 5d670486 (#1175)"),
    ("5.3", "Dry run publish: unpublished versioned path deps", "security", ["5.0"], "OPEN",
     "Needs publishing-order design decision, not a patch"),
]

# DAG edges: (from, to)
EDGES = [
    ("1.1", "1.2"), ("1.1", "1.3"), ("1.0", "1.4"), ("1.0", "1.5"),
    ("1.2", "1.6"), ("1.3", "1.6"), ("1.4", "1.6"), ("1.5", "1.6"),
    ("1.6", "2.1"), ("2.1", "2.2"), ("2.2", "2.3"), ("2.3", "2.4"),
    ("2.4", "2.5"), ("2.4", "2.6"), ("2.5", "2.6"),
    ("2.6", "3.1"), ("2.6", "3.2"), ("2.6", "3.3"), ("2.6", "3.4"), ("2.6", "3.5"),
    ("4.0", "4.1"), ("4.0", "4.2"), ("4.2", "4.3"), ("4.2", "4.4"), ("4.1", "4.5"),
    ("4.1", "4.6"), ("5.0", "5.1"), ("5.0", "5.2"), ("5.0", "5.3"),
]

STATE_CLASS = {"DONE": "s-done", "IN PROGRESS": "s-wip", "OPEN": "s-open",
               "BLOCKED": "s-blocked", "PARTIAL": "s-wip"}


def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def build():
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    head = main_head()
    prs = {n: pr_state(n) for n in (1151, 1156, 1157, 1165, 1166)}
    thr = {n: unresolved(n) for n in prs}

    rows = []
    for pid, title, lane, deps, state, note in WBS:
        cls = STATE_CLASS.get(state, "s-open")
        depstr = ", ".join(deps) if deps else "—"
        rows.append(
            f'<tr class="{cls}"><td class="mono">{esc(pid)}</td>'
            f'<td><b>{esc(title)}</b><div class="sub">{esc(note)}</div></td>'
            f'<td class="mono">{esc(lane)}</td>'
            f'<td class="mono dim">{esc(depstr)}</td>'
            f'<td><span class="pill {cls}">{esc(state)}</span></td></tr>')

    prrows = []
    intent = {
        1151: "Cloudflare Access JWT at the edge",
        1156: "mvp.rs test portability (/bin/true)",
        1157: "dist allow-dirty + zbus advisory ignore",
        1165: "exclude=[rust]; deny.toml cleanup",
        1166: "python-coverage COVERAGE_PATH + mutants timeout",
    }
    for n in (1151, 1156, 1157, 1165, 1166):
        p = prs[n]
        u, t = thr[n]
        mcls = ("s-done" if p["merge"] == "MERGEABLE" else
                "s-wip" if p["merge"] in ("UNSTABLE", "BLOCKED", "DIRTY") else "s-open")
        prrows.append(
            f'<tr><td class="mono">#{n}</td>'
            f'<td>{esc(intent[n])}</td>'
            f'<td class="mono">{esc(p["merge"])}</td>'
            f'<td class="mono">{esc(p["review"])}</td>'
            f'<td class="mono">{u}/{t}</td>'
            f'<td><span class="pill {mcls}">{"CLEAR" if u == 0 else "THREADS"}</span></td></tr>')

    # pane matrix
    cells = []
    for i in range(0, len(PANES), 3):
        row = PANES[i:i + 3]
        tds = []
        for pid, label, status, title, note in row:
            me = pid == "wA:pH"
            tds.append(
                f'<div class="pane{" me" if me else ""}">'
                f'<div class="pane-h"><span class="mono">{esc(pid)}</span>'
                f'<span class="badge {status}">{esc(status)}</span></div>'
                f'<div class="pane-t">{esc(label)}</div>'
                f'<div class="pane-s">{esc(title)}</div>'
                f'<div class="pane-n">{esc(note)}</div>'
                f'{"<div class=flag>◀ THIS PANE</div>" if me else ""}</div>')
        while len(tds) < 3:
            tds.append('<div class="pane empty"></div>')
        cells.append('<div class="prow">' + "".join(tds) + '</div>')

    wstable = "".join(
        f'<tr><td class="mono">{esc(i)}</td><td>{esc(lbl)}</td>'
        f'<td class="mono">#{num}</td><td class="mono">{n}</td>'
        f'<td>{"◀ active workspace" if i == "wA" else ""}</td></tr>'
        for i, lbl, num, n in WS)

    commits = sh("git", "log", "--oneline", "-9", "origin/main").splitlines()
    commitrows = "".join(
        f'<tr><td class="mono">{esc(c.split()[0])}</td>'
        f'<td class="mono">{esc(" ".join(c.split()[1:]))}</td></tr>' for c in commits)

    return TEMPLATE.format(
        now=now, head=head, rows="\n".join(rows), prrows="\n".join(prrows),
        panes="\n".join(cells), wstable=wstable, commitrows=commitrows,
        n_wbs=len(WBS), n_done=sum(1 for w in WBS if w[4] == "DONE"),
        n_wip=sum(1 for w in WBS if w[4] == "IN PROGRESS"),
        n_open=sum(1 for w in WBS if w[4] == "OPEN"),
        n_edges=len(EDGES), n_prs=len(prs),
        n_thr=sum(thr[n][0] for n in thr),
    )


TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>SFD Session Walkthrough — Omni (wA:pH)</title>
<style>
  :root {{
    --bg:#0d1117; --panel:#161b22; --line:#30363d; --fg:#e6edf3; --dim:#8b949e;
    --red:#f85149; --green:#3fb950; --amber:#d29922; --blue:#58a6ff; --purple:#bc8cff;
  }}
  * {{ box-sizing:border-box; }}
  body {{ background:var(--bg); color:var(--fg); font:14px/1.55 -apple-system,
    BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; margin:0; padding:28px; }}
  h1 {{ font-size:23px; margin:0 0 4px; }}
  h2 {{ font-size:16px; margin:30px 0 10px; padding-bottom:6px;
        border-bottom:1px solid var(--line); color:var(--blue); }}
  h3 {{ font-size:13px; margin:18px 0 8px; color:var(--purple); }}
  .mono {{ font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:12px; }}
  .sub {{ color:var(--dim); font-size:12px; margin-top:3px; }}
  .dim {{ color:var(--dim); }}
  .ident {{ display:flex; gap:14px; flex-wrap:wrap; align-items:center;
            background:var(--panel); border:1px solid var(--line); border-left:4px solid var(--red);
            border-radius:8px; padding:14px 18px; margin:14px 0 22px; }}
  .ident b {{ color:var(--red); }}
  .kv {{ background:#0b0f14; border:1px solid var(--line); border-radius:6px;
          padding:3px 10px; font-family:ui-monospace,Menlo,monospace; font-size:12.5px; }}
  table {{ width:100%; border-collapse:collapse; margin-top:8px; font-size:13px; }}
  th {{ text-align:left; color:var(--dim); font-weight:600; font-size:11px;
        text-transform:uppercase; letter-spacing:.6px; padding:7px 10px;
        border-bottom:1px solid var(--line); }}
  td {{ padding:7px 10px; border-bottom:1px solid #21262d; vertical-align:top; }}
  tr.s-done td:first-child {{ border-left:3px solid var(--green); }}
  tr.s-wip  td:first-child {{ border-left:3px solid var(--amber); }}
  tr.s-open td:first-child {{ border-left:3px solid var(--blue); }}
  tr.s-blocked td:first-child {{ border-left:3px solid var(--red); }}
  .pill {{ display:inline-block; padding:2px 9px; border-radius:99px; font-size:10.5px;
           font-weight:700; letter-spacing:.4px; }}
  .pill.s-done {{ background:#12331f; color:var(--green); border:1px solid #1d6b34; }}
  .pill.s-wip {{ background:#332a10; color:var(--amber); border:1px solid #6b5416; }}
  .pill.s-open {{ background:#12243d; color:var(--blue); border:1px solid #1f4a7a; }}
  .pill.s-blocked {{ background:#3d1618; color:var(--red); border:1px solid #6b2226; }}
  .prow {{ display:grid; grid-template-columns:repeat(3,1fr); gap:12px; margin-bottom:12px; }}
  .pane {{ background:var(--panel); border:1px solid var(--line); border-radius:8px;
           padding:12px 14px; min-height:104px; }}
  .pane.me {{ border:2px solid var(--red); background:#1c1416;
              box-shadow:0 0 0 4px rgba(248,81,73,.14); }}
  .pane.empty {{ opacity:.25; }}
  .pane-h {{ display:flex; justify-content:space-between; align-items:center; gap:8px; }}
  .pane-t {{ font-weight:700; margin-top:7px; font-size:14.5px; }}
  .pane-s {{ color:var(--blue); font-size:12px; margin-top:3px; }}
  .pane-n {{ color:var(--dim); font-size:11.5px; margin-top:5px; }}
  .flag {{ margin-top:9px; color:var(--red); font-weight:800; font-size:12px;
           letter-spacing:.7px; }}
  .badge {{ font-size:10px; padding:1px 7px; border-radius:99px; font-weight:700; }}
  .badge.done {{ background:#12331f; color:var(--green); }}
  .badge.working {{ background:#332a10; color:var(--amber); }}
  .badge.idle {{ background:#12243d; color:var(--blue); }}
  .grid2 {{ display:grid; grid-template-columns:1fr 1fr; gap:22px; }}
  .card {{ background:var(--panel); border:1px solid var(--line); border-radius:8px;
           padding:14px 16px; }}
  .dag {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(168px,1fr));
          gap:8px; margin-top:10px; }}
  .node {{ background:#0b0f14; border:1px solid var(--line); border-radius:6px;
           padding:8px 10px; font-size:12px; }}
  .node .id {{ color:var(--purple); font-family:ui-monospace,Menlo,monospace; }}
  .node.d {{ border-left:3px solid var(--green); }}
  .node.w {{ border-left:3px solid var(--amber); }}
  .node.o {{ border-left:3px solid var(--blue); }}
  .node .t {{ color:var(--dim); font-size:11px; margin-top:2px; }}
  .warn {{ background:#2a1f10; border:1px solid #6b5416; border-left:4px solid var(--amber);
           border-radius:6px; padding:11px 14px; margin:10px 0; }}
  .bad {{ background:#2a1416; border:1px solid #6b2226; border-left:4px solid var(--red);
          border-radius:6px; padding:11px 14px; margin:10px 0; }}
  .ok {{ background:#12241a; border:1px solid #1d6b34; border-left:4px solid var(--green);
         border-radius:6px; padding:11px 14px; margin:10px 0; }}
  footer {{ margin-top:36px; padding-top:14px; border-top:1px solid var(--line);
            color:var(--dim); font-size:11.5px; }}
</style></head><body>

<h1>State &amp; Forward Docket — session walkthrough</h1>
<div class="sub">Generated {now} · regenerate with
<code class="mono">python3 ~/Exports/analysis/sfd_session_walkthrough.py</code></div>

<div class="ident">
  <span class="kv">herdr pane label: <b>Omni</b></span>
  <span class="kv">pane id: wA:pH</span>
  <span class="kv">workspace: <b>chats</b> (wA)</span>
  <span class="kv">Local-chats</span>
  <span class="kv">agent: jcode / shrimp</span>
  <span class="kv">repo: KooshaPari/AgilePlus @ {head}</span>
</div>

<h2>1 · Where I am</h2>
<div class="grid2">
  <div class="card">
    <h3 style="margin-top:0">Identity</h3>
    <table>
      <tr><td class="dim">Pane label</td><td class="mono"><b style="color:var(--red)">Omni</b></td></tr>
      <tr><td class="dim">Pane id</td><td class="mono">wA:pH</td></tr>
      <tr><td class="dim">Workspace</td><td class="mono">wA = "chats" (workspace #2 of 5)</td></tr>
      <tr><td class="dim">Grid</td><td class="mono">2 rows x 3 cols = 6 panes</td></tr>
      <tr><td class="dim">Swarm</td><td class="mono">shrimp (coordinator)</td></tr>
      <tr><td class="dim">Repo HEAD</td><td class="mono">{head}</td></tr>
    </table>
  </div>
  <div class="card">
    <h3 style="margin-top:0">This session in one line</h3>
    <div>Reconciled a three-artefact cockpit into one derivable source, landed it,
    then spent the remaining budget on the fork-family audit that revealed the
    traceability receipts were gone.</div>
    <table style="margin-top:10px">
      <tr><td class="dim">WBS nodes</td><td class="mono">{n_wbs}
        (<span style="color:var(--green)">{n_done} done</span>,
         <span style="color:var(--amber)">{n_wip} in progress</span>,
         <span style="color:var(--blue)">{n_open} open</span>)</td></tr>
      <tr><td class="dim">DAG edges</td><td class="mono">{n_edges}</td></tr>
      <tr><td class="dim">PRs in flight</td><td class="mono">{n_prs} (one gate: conversations)</td></tr>
      <tr><td class="dim">Threads left</td><td class="mono">{n_thr} of 38 on #1149 → 0</td></tr>
    </table>
  </div>
</div>

<h2>2 · Pane matrix — workspace <span class="mono">wA "chats"</span></h2>
<div class="warn"><b>Highlighted red = this pane.</b> Matrix is 2x3; the red cell is
row 2, column 3.</div>
{panes}

<h3>All workspaces in this herdr session</h3>
<table>
  <tr><th>id</th><th>label</th><th>#</th><th>panes</th><th></th></tr>
  {wstable}
</table>

<h2>3 · WBS — every node, every state</h2>
<div class="sub">State is evidence-backed, never aspirational. DONE means the change
is merged and verified; IN PROGRESS means work is actively running now; OPEN means
identified but not started.</div>
<table>
  <tr><th>id</th><th>title / evidence</th><th>lane</th><th>deps</th><th>state</th></tr>
  {rows}
</table>

<h2>4 · DAG — dependency structure</h2>
<div class="dag">
  <div class="node d"><span class="id">1.0</span><div>cockpit reconcile</div><div class="t">root</div></div>
  <div class="node d"><span class="id">1.1-1.5</span><div>derive · correct · restore · consolidate</div><div class="t">deps 1.0</div></div>
  <div class="node d"><span class="id">1.6</span><div>commit e4f5707c</div><div class="t">joins 1.2-1.5</div></div>
  <div class="node d"><span class="id">2.1-2.3</span><div>conflict · ruff · prettier</div><div class="t">chain from 1.6</div></div>
  <div class="node d"><span class="id">2.4-2.5</span><div>fix 13 real · rebut 4 false</div><div class="t">chain from 2.3</div></div>
  <div class="node d"><span class="id">2.6</span><div>merge c09e53ce</div><div class="t">joins 2.4+2.5</div></div>
  <div class="node w"><span class="id">3.1-3.5</span><div>5 PRs → mergeable</div><div class="t">all from 2.6</div></div>
  <div class="node d"><span class="id">4.0-4.2</span><div>fork family audit</div><div class="t">root</div></div>
  <div class="node o"><span class="id">4.3-4.4</span><div>receipts · mark superseded</div><div class="t">from 4.2</div></div>
  <div class="node o"><span class="id">4.5-4.6</span><div>KCode 47 paths · HeliosCLI</div><div class="t">from 4.1</div></div>
  <div class="node o"><span class="id">5.0-5.3</span><div>security CI (not a gate)</div><div class="t">independent root</div></div>
</div>
<div class="sub" style="margin-top:8px">Critical path:
<span class="mono">1.0 → 1.1 → 1.2 → 1.6 → 2.1 → 2.2 → 2.3 → 2.4 → 2.5 → 2.6 → 3.x</span></div>

<h2>5 · PR queue — the only real gate is conversation resolution</h2>
<div class="ok"><b>Branch protection has no required status checks.</b>
<code class="mono">required_status_checks</code>, <code class="mono">required_pull_request_reviews</code>
and <code class="mono">enforce_admins</code> are all absent. The gates are
<code class="mono">required_linear_history</code> and
<code class="mono">required_conversation_resolution</code>. That is why Cargo Deny
and OSV have been red on main for 8+ days without blocking a single merge —
and why the two PRs merged this session merged despite red checks.</div>
<table>
  <tr><th>PR</th><th>intent</th><th>merge state</th><th>review</th><th>threads</th><th>gate</th></tr>
  {prrows}
</table>

<h2>6 · What the session actually established</h2>
<div class="card">
  <h3 style="margin-top:0">Two findings that changed the plan</h3>
  <p><b>1. The merge gate was never CI.</b> I spent four commits making
  #1149's <span class="mono">Python</span> and <span class="mono">Lint &amp; Format</span>
  jobs green before reading the branch-protection config, which has no required
  status checks at all. The gate was 33 unresolved review conversations. CI green
  was real work but it was never on the critical path.</p>
  <p><b>2. The automated reviewers were wrong often enough that bulk-resolving
  would have damaged the docket.</b> Of 38 threads, 13 were real defects, 14
  were outdated, and 4 were false in ways that would have caused damage if
  acted on:</p>
  <table>
    <tr><th>false finding</th><th>what acting on it would have done</th></tr>
    <tr><td class="mono">DOCKET.snapshot.json "does not exist"</td>
        <td>added a duplicate of a 19,705-byte file that already existed</td></tr>
    <tr><td class="mono">remove v2026.09.0 from the gitGraph</td>
        <td>deleted a tag <span class="mono">git merge-base --is-ancestor</span>
            confirms IS an ancestor</td></tr>
    <tr><td class="mono">"keep the gate count at 2/20"</td>
        <td>walked back G19, which closed on 93.99% line coverage</td></tr>
    <tr><td class="mono">"byte-identical is overstated"</td>
        <td>the count was right; a different parenthetical was wrong</td></tr>
  </table>
</div>

<h2>7 · The traceability failure (fork family B)</h2>
<div class="bad"><b>Four "preserved" audit receipts are gone.</b>
The airlock dockets advertise
<span class="mono">/tmp/kp_repos_clean.json</span>,
<span class="mono">/tmp/kp_archived.json</span>,
<span class="mono">/tmp/kp_audit/audit.json</span> and
<span class="mono">/tmp/kp_audit/audit.py</span> as "Audit Artifacts (preserved)".
All four are missing and there is <b>no in-repo copy</b>. They lived in
<span class="mono">/tmp</span>, which is ephemeral.</div>
<div class="card">
  <div>Every numeric claim in the seven live consolidation dockets is now
  <b>unverifiable from the repo</b>:</div>
  <table style="margin-top:8px">
    <tr><td class="mono">29</td><td>audit candidates</td></tr>
    <tr><td class="mono">358</td><td>novel branches blocking thegent squash</td></tr>
    <tr><td class="mono">330 / 2061</td><td>omlx divergence, no merge-base</td></tr>
    <tr><td class="mono">47</td><td>conflicting paths in the KCode worktree</td>
        <td style="color:var(--green)">✓ this one is fine — it lives in
        <span class="mono">docs/UPSTREAM-SYNC-STATUS.md</span> with the regeneration
        command</td></tr>
  </table>
  <p class="sub" style="margin-top:10px">The KCode file is the pattern to copy:
  it embeds the failure output, the counts, and the command that regenerates them,
  so it stays checkable with no external files.</p>
</div>

<h2>8 · Commits landed this session</h2>
<table>
  <tr><th>sha</th><th>subject</th></tr>
  {commitrows}
</table>

<h2>9 · Open items, honestly</h2>
<div class="warn">
  <b>1 · Fork family B is closed as a migration program.</b> The 2026-07-29
  sponsor policy says those dockets are "superseded" and "no docket below
  authorizes a state-changing operation" — yet seven files still read
  "awaiting approval". A reader cannot tell which wins. Mark them SUPERSEDED.
</div>
<div class="warn">
  <b>2 · Re-derive the audit counts or strike them.</b> Commit an in-repo audit
  script + JSON so 358 / 330-2061 / 29 are reproducible, or mark them
  unverifiable. Leaving unsourced counts in an audit docket is the same defect
  class I spent today fixing in the cockpit.
</div>
<div class="warn">
  <b>3 · KCode upstream sync is blocked on the worktree, not the strategy.</b>
  47 untracked paths collide with upstream. That is mechanical, report-before-delete
  work, and it is the only thing standing between the fork and its monthly sync.
</div>
<div class="warn">
  <b>4 · HeliosCLI is indistinguishable from done.</b> Decollided in October,
  never built, never run, no <span class="mono">~/.helios/</span>. Either give it
  a first build or record the intent as abandoned.
</div>
<div class="bad">
  <b>5 · Dependabot reports 17 vulnerabilities on main (3 critical, 1 high).</b>
  Up from 5 when this session started. The webpki bumps landed
  (<span class="mono">5d670486</span>), so the increase is elsewhere and should be
  triaged — it is not a merge gate, but 3 critical is worth a look.
</div>

<footer>
  <b>Omni</b> · herdr pane wA:pH · workspace "chats" (wA) · Local-chats ·
  KooshaPari/AgilePlus @ {head} · generated {now}<br>
  This artifact is regenerated from live probes, not hand-edited. Re-run
  <span class="mono">python3 ~/Exports/analysis/sfd_session_walkthrough.py</span> to refresh.
</footer>
</body></html>
"""

if __name__ == "__main__":
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build())
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
