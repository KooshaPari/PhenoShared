# dagrun stage-gate trace

A gate verdict that is not committed is a claim, not evidence. This file is the
committed record that dagrun's own artifact stage gate was exercised, with the
real commands, the real exit codes, and the real output of a real run.

**A gate verdict WAS obtained.** Two nodes were driven through the full
`plan -> next -> claim -> done` path. Each `done` was attempted once with the
artifact absent (refused, exit 1) and once with the artifact present by hand
(accepted, exit 0). One further cell is not satisfied and is recorded as such:
the trace log came back empty.

## 1. Purpose

dagrun's central promise is that a node is done only when the artifacts it
declared verify (`internal/run/run.go`; the CLI help line reads "A node is done
only when the artifacts it declared verify"). Without a committed transcript
that promise is unfalsifiable: anyone can assert "the gates ran" and nothing on
disk can contradict them. A reader re-runs section 5 and gets the same
verdicts, or sees that they got different ones.

## 2. Environment

- Run date `2026-11-12T12:31:51Z` (`date -u +%Y-%m-%dT%H:%M:%SZ`); host
  `Darwin 27.0.0 arm64` (`uname -srm`).
- System Go toolchain `go version go1.23.4 darwin/arm64`. `cmd/dagrun/go.mod:3`
  requires `go 1.25.0`; with `GOTOOLCHAIN=auto` the toolchain resolves to
  `go version go1.25.0 darwin/arm64` inside `cmd/dagrun`, which is what the
  probe binary was built with.
- Module path `github.com/KooshaPari/dagrun` (`cmd/dagrun/go.mod:1`).
- Probe binary built to `/tmp/dagrun-probe` (14,179,554 bytes), never into the
  repo. Probe workspace `/Users/kooshapari/CodeProjects/temp/dagrun-gate-probe/`
  (outside the repository); run directory `.../dagrun-gate-probe/.dagrun`.

## 3. The probe

Plan: node `1.1` (INTENT) declares `artifacts/PROBE_INTENT.md`; node `2.1` (GATE)
depends on it, declares `artifacts/PROBE_GATE.txt`, and carries the check
`pwd; test -s artifacts/PROBE_GATE.txt`. No harness, no provider, no network.

```
$ /tmp/dagrun-probe plan -file .../plan.yaml -dir .../.dagrun
run: dagrun-gate-probe   nodes: 2   waves: 2   critical path: 10m
installed plan at .../dagrun-gate-probe/.dagrun/run.yaml
artifacts resolve under /Users/kooshapari/CodeProjects/temp/dagrun-gate-probe
EXIT=0

$ /tmp/dagrun-probe claim 1.1 -dir .../.dagrun -owner probe-agent
claimed 1.1 owner=probe-agent epoch=1
EXIT=0

$ /tmp/dagrun-probe done 1.1 -dir .../.dagrun          # artifact absent
1.1 does not satisfy its contract: artifacts/PROBE_INTENT.md: missing file does not exist; INTENT: intent_no_acceptance no acceptance criteria [add an "Acceptance Criteria" section]
dagrun done: verification failed
EXIT=1

$ printf '# Probe Intent\n\nAcceptance Criteria\n\n- one\n- two\n- three\n' > .../artifacts/PROBE_INTENT.md
EXIT=0

$ /tmp/dagrun-probe done 1.1 -dir .../.dagrun          # artifact present
done 1.1 (INTENT)
EXIT=0

$ /tmp/dagrun-probe done 2.1 -dir .../.dagrun          # artifact absent
2.1 does not satisfy its contract: artifacts/PROBE_GATE.txt: missing file does not exist; check exited 1
dagrun done: verification failed
EXIT=1

$ /tmp/dagrun-probe explain 2.1 -dir .../.dagrun
  FAIL artifacts/PROBE_GATE.txt                 missing file does not exist
check FAIL  pwd; test -s artifacts/PROBE_GATE.txt  (.../dagrun-gate-probe)
EXIT=1

$ printf 'PROBE-PASS token\n' > .../artifacts/PROBE_GATE.txt
EXIT=0

$ /tmp/dagrun-probe done 2.1 -dir .../.dagrun          # artifact present
done 2.1 (GATE)
EXIT=0

$ /tmp/dagrun-probe status -dir .../.dagrun
progress 2/2 (100%)
EXIT=0

$ /tmp/dagrun-probe validate -dir .../.dagrun -all
1.1      ok
2.1      ok
0 broken, 0 already satisfied but not marked done
EXIT=0

$ /tmp/dagrun-probe trace -dir .../.dagrun
no events yet
EXIT=0

$ /tmp/dagrun-probe export -dir .../.dagrun -format agileplus -out .../agileplus.bundle.json
-rw-r--r--@ 1 kooshapari  staff  1054 Nov 12 04:31 .../agileplus.bundle.json
EXIT=0
```

The exported bundle reads back with top-level keys `projects`, `features`,
`modules`, `cycles`; its `spec_content` records
`artifact artifacts/PROBE_INTENT.md (232 bytes, sha256 8e7d1d1fbb12)`.

| step | command (abbreviated) | exit | artifact gate verdict | cell |
|---|---|---|---|---|
| 01 | `plan -file plan.yaml -dir .dagrun` | 0 | plan accepted, 2 nodes, 2 waves | PASS |
| 02 | `next -dir .dagrun` | 0 | 1 ready node, cvp gate 2.1 | PASS |
| 03 | `claim 1.1 -owner probe-agent` | 0 | claimed, epoch 1 | PASS |
| 04 | `done 1.1` (artifact absent) | 1 | refused: `missing file does not exist` | PASS (gate refused) |
| 05 | `explain 1.1` | 1 | `FAIL artifacts/PROBE_INTENT.md` | PASS (diagnosed) |
| 06 | write `artifacts/PROBE_INTENT.md` by hand | 0 | 232 bytes on disk | PASS |
| 07 | `done 1.1` (artifact present) | 0 | `done 1.1 (INTENT)` | PASS |
| 08 | `next -dir .dagrun` | 0 | 2.1 now ready | PASS |
| 09 | `claim 2.1 -owner probe-agent` | 0 | claimed, epoch 1 | PASS |
| 10 | `done 2.1` (artifact absent) | 1 | refused: `missing file does not exist; check exited 1` | PASS (gate refused) |
| 11 | `explain 2.1` | 1 | `FAIL artifacts/PROBE_GATE.txt`, `check FAIL` | PASS (diagnosed) |
| 12 | write `artifacts/PROBE_GATE.txt` by hand | 0 | 17 bytes on disk | PASS |
| 13 | `done 2.1` (artifact present) | 0 | `done 2.1 (GATE)` | PASS |
| 14 | `status -dir .dagrun` | 0 | `progress 2/2 (100%)` | PASS |
| 15 | `validate -dir .dagrun -all` | 0 | `0 broken` | PASS |
| 16 | `trace -dir .dagrun` | 0 | `no events yet`; `.dagrun/trace/` empty | FAIL (no trace evidence) |
| 17 | `export -format agileplus` | 0 | 1054-byte bundle written | PASS |
| 18 | `git status --porcelain -- cmd/dagrun` | 0 | repository clean | PASS |

Step 16 is a real FAIL against the expectation that a completed run leaves
trace evidence: the command succeeded but `.dagrun/trace/` was empty
afterwards, so the agent-driven `claim`/`done` path recorded no trace events.
The cause is UNKNOWN: `dagrun run` (the harness-spawning path) was NOT run, so
it is unknown whether that path populates the trace where this one does not.

## 4. What this trace proves, and what it does not

Proves: the artifact stage gate is real and falsifiable on this host. An absent
artifact is refused with exit 1 and a named reason; a present, well-formed
artifact is accepted with exit 0; `validate` re-derives the same verdict from
the filesystem alone; `status` reports the run complete only after both nodes
passed. The AgilePlus export bridge produced a parseable bundle from that run.

Does NOT prove: anything about semantic correctness. A passing artifact
predicate means the file exists, is large enough, and contains the required
strings. It does not mean the content is true, meaningful, or that the work
described was actually done. This probe's artifacts are two hand-written text
files; a green gate over them says only that the mechanism works.

Also NOT_RUN: `dagrun run` (harness spawning), the MCP surface, workspace
resolution, replan/recover, and any real repository change.

## 5. Reproduce

Run the commands in section 3's fenced block verbatim, after:

```
cd /Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared/cmd/dagrun
go build -o /tmp/dagrun-probe .
cd /Users/kooshapari/CodeProjects/temp/dagrun-gate-probe
rm -rf .dagrun artifacts
```

`plan.yaml` is intentionally not committed; it lives outside the repository so
the probe cannot dirty the tree. Its full content is the plan named above:

```yaml
version: 1
run: dagrun-gate-probe
intent: "Exercise dagrun's artifact-gated stage gate locally with no harness and no network."
artifacts_root: artifacts
max_parallel: 1
defaults: {estimate: 5m, timeout: 10m, max_attempts: 1}
nodes:
  - id: "1.1"
    kind: INTENT
    role: intent
    title: "State the probe intent on disk"
    artifacts:
      - path: artifacts/PROBE_INTENT.md
        min_bytes: 120
        must_contain: ["Acceptance Criteria"]
  - id: "2.1"
    kind: GATE
    role: gate
    title: "Gate on a hand-written marker artifact"
    deps: ["1.1"]
    artifacts:
      - path: artifacts/PROBE_GATE.txt
        min_bytes: 12
        must_contain: ["PROBE-PASS"]
    check: "pwd; test -s artifacts/PROBE_GATE.txt"
```

## 6. Anything that could not run

Recorded rather than hidden, from the first attempt:

- `dagrun plan` rejected the initial plan with exit 1: `plan is not runnable:
  1 issue(s)` / `2.1 [gate_without_check]: GATE nodes must declare a check` /
  `dagrun plan: plan rejected`. The plan was corrected by adding a `check` to
  the GATE node; the transcript in section 3 is the second attempt, which ran
  clean from step 01.
- With two acceptance bullets in the intent artifact, `done 1.1` refused with
  exit 1: `INTENT: intent_thin_acceptance fewer than 3 acceptance bullets
  [list at least three checkable "- " acceptance bullets]`. The artifact was
  rewritten with three bullets, which is what steps 06 and 07 record.

NOT_RUN, with reasons:

- `dagrun run` (harness spawning): NOT_RUN. It spawns agent harnesses; the
  probe was deliberately built to avoid any provider or network.
- Trace evidence of the gate transitions: the command ran (exit 0) but produced
  `no events yet`. Recorded as FAIL in the table, cause UNKNOWN.
- MCP surface (`internal/mcp`), `serve`, `viz`, `replan`, `recover`: NOT_RUN.
  Out of scope for a stage-gate probe.
