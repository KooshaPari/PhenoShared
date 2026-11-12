# dagrun stage-gate probe — measured 2026-11-12

A gate verdict that is not committed is a claim, not evidence. This file records the
exact commands, exit codes, and observed output of one real probe of dagrun's
artifact stage gate. Scope: the agent-driven path only (`plan` → `next` → `claim`
→ `done` → `validate` → `status` → `trace`), with no LLM, no provider, no network.

## 1. Environment

| item | observed value |
|---|---|
| Run timestamp | `2026-11-12T12:31:51Z` (`date -u +%Y-%m-%dT%H:%M:%SZ`) |
| Host | `Darwin 27.0.0 arm64` (`uname -srm`) |
| System Go toolchain | `go version go1.23.4 darwin/arm64` |
| Module | `github.com/KooshaPari/dagrun` (`cmd/dagrun/go.mod:1`); Go directive `cmd/dagrun/go.mod:3` → `go 1.25.0`, resolved by `GOTOOLCHAIN=auto` to `go version go1.25.0 darwin/arm64` inside `cmd/dagrun`, the toolchain the probe binary was built with |
| Probe binary | `/tmp/dagrun-probe`, 14,179,554 bytes, built outside the repository |
| Probe workspace | `/Users/kooshapari/CodeProjects/temp/dagrun-gate-probe/`; run dir `.../dagrun-gate-probe/.dagrun`; `git status --porcelain -- cmd/dagrun` empty (clean) |

Plan under test: node `1.1` (INTENT) declares `artifacts/PROBE_INTENT.md` (`min_bytes: 120`,
`must_contain: ["Acceptance Criteria"]`); node `2.1` (GATE) depends on it, declares
`artifacts/PROBE_GATE.txt` (`min_bytes: 12`, `must_contain: ["PROBE-PASS"]`), check `pwd; test -s artifacts/PROBE_GATE.txt`.

## 2. Transcript

```
Commands in order, with the exit code observed for each. `...` = `/Users/kooshapari/CodeProjects/temp/dagrun-gate-probe`.
$ cd .../cmd/dagrun && go build -o /tmp/dagrun-probe .   # EXIT=0 (GOTOOLCHAIN=auto -> go1.25.0)
$ /tmp/dagrun-probe plan -file .../plan.yaml -dir .../.dagrun                    # EXIT=0
run: dagrun-gate-probe   nodes: 2   waves: 2   critical path: 10m
installed plan at .../dagrun-gate-probe/.dagrun/run.yaml
$ /tmp/dagrun-probe next -dir .../.dagrun                    # EXIT=0 (1 ready node, cvp gate 2.1)
$ /tmp/dagrun-probe claim 1.1 -dir .../.dagrun -owner probe-agent                # EXIT=0
claimed 1.1 owner=probe-agent epoch=1
$ /tmp/dagrun-probe done 1.1 -dir .../.dagrun          # artifact absent
1.1 does not satisfy its contract: artifacts/PROBE_INTENT.md: missing file does not exist; INTENT: intent_no_acceptance no acceptance criteria [add an "Acceptance Criteria" section]
dagrun done: verification failed
EXIT=1
$ printf '# Probe Intent\n\nAcceptance Criteria\n\n- one\n- two\n- three\n' > .../artifacts/PROBE_INTENT.md   # EXIT=0
$ /tmp/dagrun-probe done 1.1 -dir .../.dagrun          # artifact present
done 1.1 (INTENT)
EXIT=0
$ /tmp/dagrun-probe claim 2.1 -dir .../.dagrun -owner probe-agent                # EXIT=0
claimed 2.1 owner=probe-agent epoch=1
$ /tmp/dagrun-probe done 2.1 -dir .../.dagrun          # artifact absent
2.1 does not satisfy its contract: artifacts/PROBE_GATE.txt: missing file does not exist; check exited 1
dagrun done: verification failed
EXIT=1
$ printf 'PROBE-PASS token\n' > .../artifacts/PROBE_GATE.txt                       # EXIT=0
$ /tmp/dagrun-probe done 2.1 -dir .../.dagrun          # artifact present
done 2.1 (GATE)
EXIT=0
$ /tmp/dagrun-probe validate -dir .../.dagrun -all
1.1      ok
2.1      ok
0 broken, 0 already satisfied but not marked done
EXIT=0
$ /tmp/dagrun-probe status -dir .../.dagrun
progress 2/2 (100%)
EXIT=0
$ /tmp/dagrun-probe trace -dir .../.dagrun
no events yet
EXIT=0
$ ls -A .../.dagrun/trace/
EXIT=0            # no output: the trace directory is empty
```

## 3. Step table

| step | command | exit | observed verdict | cell |
|---|---|---|---|---|
| 01 | `plan -file plan.yaml -dir .dagrun` | 0 | plan accepted: 2 nodes, 2 waves | PASS |
| 02 | `next -dir .dagrun` | 0 | 1 ready node, cvp gate 2.1 | PASS |
| 03 | `claim 1.1 -owner probe-agent` | 0 | claimed, epoch 1 | PASS |
| 04 | `done 1.1` (artifact absent) | 1 | refused: `missing file does not exist` | PASS |
| 05 | write `artifacts/PROBE_INTENT.md` by hand | 0 | 232 bytes on disk | PASS |
| 06 | `done 1.1` (artifact present) | 0 | `done 1.1 (INTENT)` | PASS |
| 07 | `claim 2.1 -owner probe-agent` | 0 | claimed, epoch 1 | PASS |
| 08 | `done 2.1` (artifact absent) | 1 | refused: `missing file does not exist; check exited 1` | PASS |
| 09 | write `artifacts/PROBE_GATE.txt` by hand | 0 | 17 bytes on disk | PASS |
| 10 | `done 2.1` (artifact present) | 0 | `done 2.1 (GATE)` | PASS |
| 11 | `validate -dir .dagrun -all` | 0 | `0 broken` | PASS |
| 12 | `status -dir .dagrun` | 0 | `progress 2/2 (100%)` | PASS |
| 13 | `trace -dir .dagrun` | 0 | `no events yet`; `.dagrun/trace/` empty | FAIL |
| 14 | `dagrun run` (orchestrator path) | — | not exercised by this probe | NOT_RUN |

## 4. Finding

1. **The artifact gate is correct and the negative control held.** Each `done` was
   attempted once with the artifact absent and once with it present. Absent: exit 1,
   naming the missing path (`missing file does not exist`) and, for node `2.1`, the
   failing check (`check exited 1`). Present: exit 0 and `done <node> (<KIND>)`.
   `validate` re-derived the same verdict from the filesystem alone (`0 broken`), and
   `status` reported `progress 2/2 (100%)` only after both nodes had passed.
2. **The agent-driven path records no trace events.** `dagrun trace` exited 0 but printed
   `no events yet`, and `.dagrun/trace/` was empty afterwards, even though both nodes had
   been claimed and completed. A command exiting 0 is not evidence of a record.

## 5. What this does NOT prove

- It does **not** prove the orchestrator-driven `dagrun run` path is untraceable: that path
  was **NOT_RUN**, and whether `run` populates the trace where `next`/`claim`/`done` do not is UNKNOWN.
- It does **not** speak to the semantic correctness of an artifact that satisfies a predicate:
  a green gate means the file exists, is large enough, and contains the required strings.
  Both artifacts are hand-written text files: green means the mechanism works, not that the work was done.
- It does **not** cover the MCP surface, `serve`, `viz`, `replan`, `recover`, or
  any real repository change.
- The cause of the empty trace is UNKNOWN from the probe alone; `../../TRACEABILITY.md` section 7 explains it from the source, not from this run.

## 6. Reproduce

```
cd /Users/kooshapari/CodeProjects/Phenotype/repos/PhenoShared/cmd/dagrun
go build -o /tmp/dagrun-probe .
cd /Users/kooshapari/CodeProjects/temp/dagrun-gate-probe
rm -rf .dagrun artifacts
```

The plan file is deliberately not committed (it lives outside the repository so the probe
cannot dirty the tree); its full content is in closed PR #955, `cmd/dagrun/TRACEABILITY.md`
section 5. Re-running section 2 verbatim should reproduce the same verdicts, or show it did not.
