# AgilePlus usable surface: latest, peak, and regression

Status: EVIDENCE ONLY. No implementation decisions are made here beyond the surface ranking.

Scope: answer one question honestly. *If a traceability/autograder epic were to hand work to
AgilePlus, which AgilePlus would it hand work to, and what can that version actually be called
through?*

Every cell below cites a measured command or a read source. Anything not measured is UNKNOWN,
not inferred.

---

## 1. Version identity: which number is authoritative

Four version strings exist and they disagree. Only one is authoritative.

| Source | Value | Authoritative? | Evidence |
|---|---|---|---|
| `Cargo.toml` `[workspace.package] version` | `0.2.4` | **YES** | `Cargo.toml:30` at `8699676` |
| `VERSION` file | `0.1.2` | no, stale | `VERSION` at `8699676` |
| `CHANGELOG.md` top entry | `2026.08A.0` (2026-08-26) | no, trails tags | `CHANGELOG.md` at `8699676` |
| Installed binary | `agileplus 0.2.4` | agrees with workspace | `agileplus --version` |

Rule for all downstream agents: **read the version from `Cargo.toml` and cross-check `git tag`,
never from `VERSION` or `CHANGELOG.md`.** Both of the latter are behind in every revision inspected
so far, and an agent that trusts them will mis-date the tree.

Observed tag-to-commit mapping (`gh api repos/KooshaPari/AgilePlus/commits/<tag>`):

| Tag | Commit (12) | Date |
|---|---|---|
| `v2026.09.0` | `40d53e8c3d94` | 2026-08-22 |
| `v2026.08.1` | `103681b5fcda` | 2026-08-21 |
| `v0.2.4` | `920c7f31da11` | 2026-09-16 |

CalVer tags and SemVer tags do not order against each other. `v2026.09.0` sorts by name but is
*older* than `v0.2.4`. Do not use tag names to pick a revision.

## 2. Peak revision

**Peak = `main` tip, `8699676312dfcd787435221a7926a407af920fc6`, committed 2026-11-10T01:59:57Z.**

Measured with `gh api repos/KooshaPari/AgilePlus/commits/main --jq '.sha + " " + .committer.date'`.
That SHA is the tip, not a chosen older commit, so "latest" and "peak" coincide here. No
least-regressive older revision needs to be preferred on this evidence.

Note the asymmetry that makes "peak" non-obvious: `main` is 55 days *ahead* of the newest SemVer
tag (`v0.2.4`, 2026-09-16) while still reporting workspace version `0.2.4`. There is unreleased
work on main under a released version number. If a later audit finds a regression on main, the
fallback candidate is `920c7f31da11` (tag `v0.2.4`), whose workspace version is the same string.
That fallback is **UNKNOWN-untested**: no CLI or MCP run has been performed against `920c7f31da11`.

## 3. CLI surface at peak (measured)

Installed binary reports `0.2.4`, the same version string as peak. Directly measured in `/tmp/agp-test`:

| Verb | Result | Evidence |
|---|---|---|
| `specify --feature ... --from-file` | works, writes `docs/agileplus/<slug>/spec.md` | smoke test |
| `research --feature ...` | works, writes `kitty-specs/<slug>/research.md` | smoke test |
| `plan --feature ...` | works, generates work packages | smoke test |
| `list --json` | works | smoke test |
| `validate` | exit `1` on wrong feature state and on missing feature | smoke test |
| `dag topology` | returns `0 nodes` | smoke test |
| `dag pick` | requires `--agent` | smoke test |
| `mvp next-ready` | works | smoke test |

**Absent from the installed binary's CLI help: no `accept`, no `verify`, no `freeze` verb**
(measured: `agileplus --help | grep -i -E "accept|verify|freeze"` returned nothing).

Scope that claim honestly. It is a measurement of the **installed 0.2.4 binary**, not of a build
of `8699676`. Because `main` carries 55 days of unreleased commits since tag `v0.2.4`, a CLI verb
added in that window would not appear in the installed binary. **CLI exposure at exact peak is
UNKNOWN**; it becomes KNOWN only by building `8699676` and re-running the grep. Do not upgrade
this cell to PASS or FAIL on the installed-binary evidence alone.

What is established regardless: atomic acceptance exists in the peak *source* as a full vertical
slice (domain command, application services, SQLite transaction and receipt table, HTTP routes,
gRPC service, four test suites — enumerated file-by-file in
`~/CodeProjects/temp/proresearch-20261110/agile-parity.md`), and the one binary that can be run on
this host does not surface it as a command.

## 4. MCP surface at peak (measured by source enumeration)

`PhenoShared/python/src/agileplus_mcp` contains exactly **22** `@mcp.tool` decorators:

```
agileplus_check_governance_gate   agileplus_elicit_clarify    agileplus_plan
agileplus_elicit_feature          agileplus_get_audit_trail   agileplus_queue_add
agileplus_queue_import            agileplus_queue_list        agileplus_queue_pop
agileplus_queue_show              agileplus_implement         agileplus_research
agileplus_retrospective           agileplus_sample_governance_check
agileplus_sample_retrospective    agileplus_sample_triage     agileplus_ship
agileplus_specify                 agileplus_status            agileplus_stream_status
agileplus_validate                agileplus_verify_audit_chain
```

Two facts follow.

1. **`elicit` already exists.** `agileplus_elicit_feature` and `agileplus_elicit_clarify` are real
   tools. Any new design that "adds interactive requirement refinement to AgilePlus" duplicates
   shipped capability. The gap is not *elicitation*; it is *freezing* what elicitation produced.
2. **No acceptance tool exists.** None of the 22 exposes accept-feature or read-receipt. An
   autograder cannot reach AgilePlus atomic acceptance through MCP at peak.

**Deployment status is UNKNOWN, not working.** Every tool is a proxy: the package ships
`grpc_client.py`, `grpc_backlog.py`, `grpc_errors.py`, `grpc_serialization.py`, `grpc_streaming.py`
and expects a gRPC backend on `localhost:50051`. No separate gRPC server binary has been identified
as installed. Import also fails in the absorbed tree because `fastmcp` is absent there. Source
presence is therefore not evidence of a runnable MCP surface; a real tool-loop call is required
before claiming it works.

The absorbed copy at `PhenoShared/crates/agile-plus/python/src/agileplus_mcp` is further degraded:
it has no `tools/` subpackage and only 5 tool definitions in `server.py`.

## 5. Regression: absorbed copy vs peak

| Dimension | Peak (`8699676`, workspace 0.2.4) | Absorbed `crates/agile-plus` (workspace 0.2.1) |
|---|---|---|
| Migrations | through `030_atomic_acceptance.sql` | `017` (split crates) / `026` (snapshot) |
| Atomic acceptance | present, 15 files | ABSENT (no rename, no re-home, 0 identifier hits) |
| `agileplus-application` crate | present | absent at top level |
| MCP package | 22 tools in `PhenoShared/python/...` | 5 tools, no `tools/` |
| Traceability integration test | 13,388 B | 384 lines (older revision, same file) |

Cause is **snapshot age, not dropped files**. The migration ceiling proves the absorbed snapshot
predates the introduction of migration 030, so a diff-only audit that concludes "absorption
dropped nine files" is wrong. Recorded in `agile-parity.md` §4.1 and §"No missing absorption incident".

## 6. What this settles for the epic

- **Canonical AgilePlus for integration: `main` @ `8699676`, workspace `0.2.4`.** Not the absorbed
  copy, not a CalVer tag.
- **Callable today over CLI:** specify, research, plan, list, validate, dag, mvp.
- **Callable today over MCP:** 22 named tools — *if* a gRPC backend is running, which is UNKNOWN.
- **Not callable at all at peak:** acceptance, receipts, freeze. These are the seams a
  traceability/autograder epic must own or must surface, and owning them does not duplicate
  shipped AgilePlus behaviour.
- **Already shipped, must not be rebuilt:** feature lifecycle, spec artifacts, work packages,
  governance gate, audit chain, queue, retrospective, and *elicit*.

## 7. Reproduce

```bash
gh api repos/KooshaPari/AgilePlus/commits/main --jq '.sha + " " + .commit.committer.date'
gh api "repos/KooshaPari/AgilePlus/contents/Cargo.toml?ref=8699676312dfcd787435221a7926a407af920fc6" \
  --jq '.content' | base64 -d | sed -n '29,31p'
agileplus --version
agileplus --help | grep -i -E "accept|verify|freeze"   # expect no match
grep -rn "@mcp.tool" ~/CodeProjects/Phenotype/repos/PhenoShared/python/src/agileplus_mcp | wc -l  # expect 22
```
