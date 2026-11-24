# cmux Lane Audit — 2026-10-17

**Auditor:** audit subagent (Swarm)
**Repo audited:** `KooshaPari/cmux` (public)
**Audit date:** 2026-10-17T22:28Z–22:40Z
**Mode:** read-only. No deletions, no pushes, no PRs/issues opened, no build started.

---

## Identity

| Field | Value | Source |
|---|---|---|
| Repo | `KooshaPari/cmux` | `gh repo view` |
| Description | "Open source Ghostty-based macOS terminal with vertical tabs and notifications for AI coding agents. Built for multitasking, organization, and programmability." | `gh repo view` |
| Is a fork | **Yes** | `gh repo view --json isFork` → `true` |
| **Direct parent** | **`manaflow-ai/cmux`** (NOT `ghostty-org/ghostty` directly) | `gh repo view --json parent` → `{"login":"manaflow-ai","name":"cmux"}` |
| Parent is itself a fork | No — `manaflow-ai/cmux` reports `parent: none`, `source: none`. cmux is its own upstream root. | `gh api repos/manaflow-ai/cmux` |
| Grandparent | None. `gh api repos/manaflow-ai/cmux/parent` → `404 Not Found`. | `gh api` |
| Ghostty relationship | Indirect, via a **submodule**: cmux consumes `manaflow-ai/ghostty` as a pinned GhosttyKit submodule (`docs/ghostty-fork.md`, pin `abd40f6e4`). cmux is a Ghostty-*based* terminal app, not a Ghostty fork in the git-ancestry sense. | `docs/ghostty-fork.md` |
| Created | 2026-09-16T23:03:12Z | `gh repo view` |
| Last push | 2026-09-20T09:01:07Z | `gh repo view` |
| Default branch | `main` | `gh repo view` |
| Archived | No (`isArchived: false`) | `gh repo view` |
| Disk usage | 1,997,062 KB (~1.9 GB) | `gh repo view` |
| Homepage | https://cmux.com | `gh repo view` |
| Fork/parent scale | parent `manaflow-ai/cmux` = 28,230 stars, pushed 2026-10-17T22:11Z (i.e. **active today**) | `gh api repos/manaflow-ai/cmux` |

**Correction to the task brief.** The mission assumed "cmux is Koosha's Ghostty fork." It is not a fork of `ghostty-org/ghostty`. It is a fork of `manaflow-ai/cmux`, a third-party commercial macOS terminal app (28.2k stars) that itself embeds a Ghostty fork as a submodule. This matters for the verdict: Koosha forked a fast-moving commercial upstream, not a stable OSS foundation.

---

## Activity + staleness

**Weeks since last push: 3.9 weeks (27 days)**, as of 2026-10-17.

Last 10 commits on `main`:

| SHA | Date (local) | Author | Subject |
|---|---|---|---|
| `c041c443ba` | 2026-09-20 02:01:06 -0700 | Koosha Paridehpour | `chore(deps): enable Dependabot via minimal config` |
| `5228f1f8cc` | 2026-09-16 15:48:03 -0700 | Austin Wang | Merge PR #12799 from manaflow-ai/issue-12745-cloud-surface-ownership |
| `c5a666ad40` | 2026-09-16 15:41:20 -0700 | austinpower1258 | Merge origin/main into issue-12745-cloud-surface-ownership |
| `956104e08b` | 2026-09-16 15:34:44 -0700 | austinpower1258 | fix: explain local workspace workaround for cloud drops |
| `64a665af88` | 2026-09-16 15:20:39 -0700 | Abdulaziz Albahar | Fix delayed build labels in iOS computer picker (#12786) |
| `0c7ccb4c02` | 2026-09-16 15:11:01 -0700 | Abdulaziz Albahar | Fix iOS crash on duplicate WebSocket ping completion (#12787) |
| `5994f5e333` | 2026-09-16 12:17:05 -0700 | Abdulaziz Albahar | Rename Tailscale Pairing to Mobile Pairing |
| `57b0073134` | 2026-09-16 11:08:01 -0700 | Lawrence Chen | Add monthly Max pricing and gate the Go starter plan (#12415) |
| `78f4c82504` | 2026-09-16 09:42:07 -0700 | Lawrence Chen | web: simplify the settings gear in the account dropdown (#12708) |
| `8c53ab55d2` | 2026-09-16 05:36:21 -0700 | Lawrence Chen | Fix cmux-tui build: use the crate-root child term re-export (#12774) |

**Only 1 of the last 10 commits is Koosha's.** The other 9 are upstream `manaflow-ai` contributors, all landing on 2026-09-16 (the fork date, +1 day).

**Lifetime contribution: exactly one commit, in the repo's entire history.**

```
$ git rev-list --count 5228f1f8cced4687fc672086acf091ea68aad6ae..main
1
$ git log --oneline 5228f1f8cc..main
c041c443ba chore(deps): enable Dependabot via minimal config
```

That single commit adds `.github/dependabot.yml` with a weekly **npm** schedule at the repo root — not a Dependabot config matching cmux's actual stack (a Swift/Xcode app with a Ghostty submodule, Python tests under `tests_v2/`, Go bindings under `cmux-tui/bindings/`). The `docs/` tree also contains `cloud-cmux-tui-daemon.md` and CI-runner docs referencing Go/Python ecosystems. So the sole local change is not only the only local change, it appears to target the wrong language.

---

## Divergence

Measured via GitHub compare API (local `git fetch` of a `--filter=blob:none` clone was cancelled at 7 min — the partial clone had to refetch blobs on demand; the API gives the same answer without the transfer).

```
$ gh api repos/KooshaPari/cmux/compare/main...manaflow-ai:main
{ "status": "diverged", "ahead_by": 1, "behind_by": 6143,
  "merge_base": "5228f1f8cced4687fc672086acf091ea68aad6ae" }
```

| Metric | Value |
|---|---|
| Ahead of parent | **1** commit (`c041c443ba`) |
| Behind parent | **6143** commits |
| Merge base | `5228f1f8cc` (2026-09-16T15:48:03Z) |
| Status | `diverged` |

Interpretation: the fork was cut on 2026-09-16, Koosha added a single Dependabot commit on 2026-09-20, and the parent has since landed **6143 commits**. The 27-day gap is not dormancy of the project he was building — it is a fork that was created and then never worked in again, while a very high-velocity upstream moved on by three and a half months of work.

For scale, parent activity in the last few hours alone (2026-10-17): `6d7cbc157 fix(cloud): New Display opens the new display again (#21294)` at 22:11Z, plus `use stable daemon error categories (#18673)`, `Fix Cloud VM computer-use MCP setup (#20818)`, `Fix Codex restore identity and recovery (#21178)`. PR numbers above 21,000.

---

## PR / issue census

| Query | Result |
|---|---|
| `gh pr list --state all` | **1 PR total, MERGED.** `#1 chore(deps): enable Dependabot via minimal config`, branch `chore/enable-dependabot`, created 2026-09-20T05:18:12Z, updated 2026-09-20T09:01:07Z, author `KooshaPari`. |
| `gh issue list --state all` | `the 'KooshaPari/cmux' repository has disabled issues` — issues are disabled on this fork. |
| Open PRs | **Zero.** No stale CI, no failing CI, nothing pending review. |
| `open_issues_count` (API) | 0 |
| `forks_count` / `subscribers_count` | 0 / 0 |
| Branches | Many long-lived `agent/*` and `add-*` upstream branches exist on the fork (inherited from the network), but none are Koosha-created and none have open PRs. |

**No open PR with stale or failing CI exists.** The PR backlog is empty, not neglected.

---

## CI and releases

```
$ gh run list --repo KooshaPari/cmux --limit 8
[ success  2026-09-20T05:12:57Z  main  "Graph Update: go_modules in /cmux-tui/..." (dynamic) ]
[ success  2026-09-20T05:12:57Z  main  "Graph Update: pip in /cmux-tui/..."       (dynamic) ]
```

| Field | Value |
|---|---|
| Total CI runs ever on the fork | **2**, both `event: dynamic`, both `conclusion: success` |
| Workflows defined | Exactly one: `Dependency Graph` at `dynamic/dependabot/update-graph`, `state: active` |
| Build/test/release workflow | **None.** No `build.yml`, no `test.yml`, no `release.yml` on this fork. (Upstream has these in `docs/`/`.github/`; fork CI is effectively unconfigured.) |
| Releases on the fork | **None.** `gh release list` returns empty. |
| Usable macOS artifacts from the fork | **None.** No `.dmg`/`.app` published by `KooshaPari/cmux`. The only macOS download path in the README points at the **parent**: `https://github.com/manaflow-ai/cmux/releases/latest/download/cmux-macos.dmg`. |

Note the asymmetry: the fork enabled Dependabot (which needs the Dependency Graph workflow to be useful), but Dependabot has produced **zero PRs**, and there is no CI to catch anything. The two green runs are the Dependabot graph updates firing once after config landed, not evidence of a maintained pipeline.

---

## Purpose vs herdr / Khostty

### What cmux is

From `README.md` (read via GitHub API) and `PROJECTS.md`:

> "A Ghostty-based macOS terminal with vertical tabs and notifications for AI coding agents"

Its differentiators, per its own README feature table:
- **Notification rings** — panes get a blue ring and tabs light up when a coding agent needs attention
- **Notification panel** — aggregate pending notifications, jump to most recent unread
- **In-app browser** — split a browser alongside the terminal, scriptable API ported from `vercel-labs/agent-browser`
- **Vertical + horizontal tabs** — sidebar shows git branch, linked PR status/number, cwd, listening ports, latest notification text
- **`cmux ssh user@remote`** — creates a workspace for a remote machine; `--command` runs an initial command; browser panes route through the remote network
- **`cmux claude-teams`** — runs Claude Code teammate mode; teammates spawn as native splits with sidebar metadata and notifications, "No tmux required"
- Agent hooks, agent session tracking, agent-hooks/agent-session-tracking docs, `cmux-tui` daemon, Codex agent detection

### Local install evidence

```
$ which cmux                    → (not found)
$ ls -d /Applications/cmux*     → No such file or directory
$ ls -d /Applications/*hostty*  → /Applications/Ghostty.app
$ brew list --cask | grep cmux|ghostty → ghostty
```

**cmux is not installed on this machine.** Ghostty is. That is the strongest single signal in this audit: Koosha forked cmux, enabled Dependabot, and then never ran it.

### Ties to herdr / Khostty

```
$ gh api search/code q="herdr   repo:KooshaPari/cmux"   → total_count 0
$ gh api search/code q="khostty repo:KooshaPari/cmux"   → total_count 0
$ gh api search/code q="Khostty repo:KooshaPari/cmux"   → total_count 0
```

**Zero references to herdr and zero to Khostty anywhere in the fork.** The README, PROJECTS.md, and docs/ are entirely upstream manaflow-ai text with no Koosha-side integration work. There is no documented coupling between cmux and the rest of his agent access+comms plane. Whatever the intent was, it was never expressed in the repo.

### Same purpose as herdr, or different?

**DIFFERENT — but only partly overlapping.**

| | cmux | herdr | Khostty |
|---|---|---|---|
| Layer | **GUI application** (macOS .app, Swift/AppKit, SwiftUI sidebar) | **TUI / CLI** pane multiplexer driven by coding agents | **Terminal emulator** (Ghostty fork, Windows) |
| Pane multiplexing | Yes (Bonsplit splits, vendored) | Yes — this is its core function | Yes (tmux-style splits) |
| Agent attention signalling | Notification rings + notification panel + menu-bar extra | Agent status, `herdr agent prompt`, `?` status, herdr-cockpit | Not its focus |
| In-app browser / scriptable agent API | Yes (`cmux-browser`, `cmux claude-teams`, agent hooks) | Not in this shape | No |
| Remote/SSH workspaces | `cmux ssh` first-class | Not the focus | No |
| Runs where | macOS desktop GUI | macOS, cross-harness | Windows desktop |

cmux overlaps herdr on **pane multiplexing only**. cmux's actual distinct value is *macOS-native GUI agent attention management*: a visible, clickable place where a swarm of background agents (Claude Code, Codex, cmux-tui) signals "I need you," plus an in-app browser and SSH workspaces. herdr multiplexes panes and moves prompts between them; it does not present a macOS-native notification surface with rings and a sidebar indexed by PR status and listening ports. Conversely, cmux has no fleet-control, cross-harness dispatch, or orchestration semantics — no swarm, no pane-as-agent-address model, no `herdr-cockpit` equivalent.

So: **cmux is the "attention inbox" leg; herdr is the "control plane" leg.** They are complementary in concept, overlapping only in the pane-multiplexing primitive. The complementary story is real — but it is currently a story about a *downloaded upstream app*, not about anything Koosha built, because the fork contains no work.

Khostty (Windows Ghostty) is orthogonal on both axes: different OS, and a plain terminal emulator rather than an agent-aware workspace surface.

---

## Verdict

# ABANDONED-ARCHIVE-ONLY

The fork carries exactly **one** commit — an `npm`-scoped Dependabot config that matches neither the repo's language nor its submodule layout — produced 27 days ago, with **zero** code, docs, or configuration changes of any kind, **zero** follow-up PRs, **zero** CI beyond a one-shot Dependabot graph update, **zero** releases, **zero** references to herdr or Khostty, and **zero evidence of ever being installed on this machine**. Against a parent that has landed 6,143 commits in the interim and shipped commits within hours of this audit, this is not a work-in-progress with a quiet week — it is a fork created and abandoned within four days, and a perishable artifact thereafter.

The distinguishing evidence that pushes this past DORMANT-BUT-INTENDED: dormancy implies a paused plan. Here there is nothing a plan could resume from. The single commit is inert, the app was never run, and the app is not installable from this fork at all (no releases; the README's `.dmg` points at the parent). Reviving it would mean re-syncing 6,143 commits and re-establishing an integration intent that was never written down.

## Recommended action

**Archive-label only** (`gh repo edit KooshaPari/cmux --add-topic archived-lane` or an equivalent non-destructive marker; the repo is already `isArchived: false`, so flipping that flag is the stronger option and is non-destructive). Do not delete. Do not revive. Do not merge purpose into herdr — cmux's complementary value (macOS-native agent attention surface) is real but is already fully served by upstream `manaflow-ai/cmux`, which Koosha can consume as an ordinary installed app; a fork is not the vehicle. Note this verdict is a judgment call on intent: if Koosha later claims an intended cmux lane, the cheapest revival path is deleting the local Dependabot commit's dependency and consuming upstream's release artifact rather than tracking a 6,143-commit-behind fork.

---

## Provenance / audit integrity

- **No local checkout existed** under `~/CodeProjects/Phenotype/repos/` (searched `~/CodeProjects` to depth 4 and 6 for `cmux*`; only `khostty` and `khostty-wtrees` matched terminal-related names). Herdr lives at `~/CodeProjects/herdr-pr/herdr`.
- **Cloned** to a new path `/Users/kooshapari/CodeProjects/Phenotype/repos/cmux-audit-20261017/` via `git clone --filter=blob:none --no-checkout https://github.com/KooshaPari/cmux.git`. No existing checkout was overwritten or modified.
- **No Ghostty build was started.**
- **No deletions:** no `rm`, no `git clean`, no `git reset --hard`, no branch/remote deletion, no force push, no archive action taken.
- **No pushes, no PRs, no GitHub issues** were created against any repository, fork or upstream.
- **No production source was modified.** Only new file written: this document.
- One remote was added to the audit clone (`upstream` → `manaflow-ai/cmux`) to read divergence; the fetch was cancelled at 7 minutes because the `--filter=blob:none` clone had to refetch blobs on demand. Divergence was obtained from the GitHub compare API instead and cross-checks with the local `git rev-list --count` (1 fork-only commit).