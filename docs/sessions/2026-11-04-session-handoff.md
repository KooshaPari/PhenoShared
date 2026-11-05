# Session handoff — 2026-11-04 (PST)

Coordinator session: `session_hamster_1793231882338_6acad471b77d6cf7`
Written: 2026-11-05T00:01Z (16:01 PST). Deadline agreed with operator: 16:20 PST.

## 1. Intent chain (what was actually asked, in order)

| # | Request | Status |
|---|---|---|
| 1 | Give agents a way to scrape the **full prompt timeline** out of the state HTMLs they produce (`.../lane-walkthrough.html`), using **JCode and Codex harness data only**, with the session id auto-derived, so agents can then curate/label rather than reconstruct. Test on the session itself. | delivered |
| 2 | "lets use go" — ship that scraper as a Go CLI, not a Python one-off | delivered |
| 3 | Repair `phenoShared` itself (macros crate, substrate repointing, licence/dependency hygiene, IAC tests, coverage workflow, Go module table, docs) | delivered, one gate red |
| 4 | Fix the root Tarpaulin coverage gate that had been failing on every commit | fixed locally, **CI not yet re-run** |
| 5 | This request: full state of every repo + intent owned, finish what is safe before 16:20 PST, then fan out | in progress |

## 2. Delivered artifacts (verified in git)

`cmd/promptscrape` — Go/Cobra CLI, subcommands `install`, `uninstall`, `update`, `scrape`, `version`; curl install scripts + docs; landings `bb0c181a`, `ef98d1fd`, `ed3f8bfa` (#588).

- JCode source of truth: `<sid>.json` authoritative, merged with `.journal.jsonl`.
- Codex source of truth: sqlite index + `rollout-*.jsonl`, real prompts filtered by `content_item_kind == "user.text"`.
- Finding that shaped the design: the HTML artifacts never contain prompts, so the timeline must be re-derived from harness storage; the HTML is only the index of which session to scrape.

Verified this round with the cached toolchain:

```
GOTOOLCHAIN=go1.26.10 GODEBUG=netdns=cgo go build ./...   # ok
go test ./...                                             # extract 0.232s, resolve 0.696s
```

## 3. Coverage gate (the live defect)

Root `coverage-root` job fails with `Error: Timed out waiting for test response` on
`crates/sharecli/tests/fr007_proc_pid_watch.rs`.

Root cause: `tarpaulin.toml` had `timeout = 180`. cargo-tarpaulin deserialises that field with
`humantime_serde` (`config/mod.rs:98` in 0.37.5), so a bare integer fails TOML deserialisation,
tarpaulin discards the **whole** config file, and the built-in 60s default applies. That default is
a per-test-binary budget, and the three watch tests each dwelt 30s.

Two commits fix it:

- `cc6dceed` — watcher capture helper: strict newline-terminated NDJSON records (a truncated tail is
  a failure, not a log line), bounded `stop_and_reap` using `try_wait` instead of a raw `ESRCH`
  constant, honest detached-reader reporting, and the three watch cases now run concurrently
  (30s wall clock instead of 90s) with no `#[serial]`.
- `58d51bd3` — `timeout = "180s"`, with the deserialisation evidence recorded in the file.

`cargo test -p sharecli --test fr007_proc_pid_watch` → 9 passed / 0 failed, ~30.06s, twice.

Pushing that fix surfaced a second, latent defect in the same file: `features = "all"`. It had been
inert while the config was discarded, and the moment the file parsed again tarpaulin forwarded it to
cargo, which aborted with `none of the selected packages contains this feature: all` — every crate
in the workspace lacks a feature by that name. Fixed in `1f01b931` by removing the key; default
features are what the gate always measured in practice.

Sequence, for the record: run 41394778746 failed on the 60s test timeout → run 41943272699 failed
at `cargo metadata` on `features = "all"` (config now being honoured) → run 41943965243 got past
metadata and into the coverage run itself.

**Not verified:** the coverage gate itself. It needs Linux (`cargo-tarpaulin` has no macOS
backend) and the local Colima/Docker daemon is down, so there is no container to run it in.

## 4. Repo state (read-only census by a subagent; ahead/behind vs last-known remote refs, no fetch)

| Repo | Dirty | Divergence | Note |
|---|---|---|---|
| phenoShared | 1 (this doc) | **ahead 2** | the two coverage commits above, unpushed |
| OmniRoute | 54 | `feat/release-line-gap-recovery` ahead 43 | 2 unpushed branches |
| melosviz | 17 | `feat/production-delivery-extensions` ahead 44; `main` behind 25 | |
| pheno | 27 | `integrate-20261102` ahead 4 / behind 6; `main` ahead 8 | |
| phenotype-registry | 8 | `fix/restore-setup-bun-hosted` ahead 3 | branch changed by a concurrent process mid-audit |
| phenotype-fabric | 0 | 5 unpushed | |
| Tracera | 31 | `main` ahead 2 / behind 219 | 10 worktrees |
| jcode | — | ~47 unpushed branches | 38 worktrees, 6 dirty |
| phenoAI | 1 | `main` ahead 2 / behind 317 | |
| wt-byteport-tauri | 2 untracked | behind 4 | |
| KooshaPari-public-sync | 211 | — | |
| koosha-phenotype | 0 | — | clean |
| PhenoTooling | — | unborn repo | 30,498 staged files, zero commits |

Session footprint: 44 hamster sessions (33 closed, 6 active, 5 crashed), 259 nested child sessions.
Scratch worktrees holding earlier hamster work are deleted.

## 5. What is left, in priority order

1. **Push `phenoShared` (2 commits) and watch the coverage run.** This is the only way to convert
   the local fix into a green gate. Requires operator authorisation for the push.
2. **Coverage verification** if a Docker/Colima daemon can be started, or let CI do it (cheaper).
3. **PhenoTooling** has 30,498 staged files and zero commits — an unborn repo is a data-loss risk;
   it needs a decision (commit, or discard) rather than more staging.
4. **Stale branches**: ~47 in jcode, 43-ahead OmniRoute feature branch, melosviz 44 ahead. All
   need a human call on whether to push or drop; `git branch -D` is policy-blocked for me.
5. **Behind-main repos** (phenoAI behind 317, Tracera behind 219, melosviz behind 25) drift further
   every day; rebasing them is a separate, larger job than this window allowed.
6. Open decisions that are not code: legal/RUSTSEC dependency dispositions, and the saturated CI
   queue observed earlier.

## 6. CI census at `cd8c0d1c` (nothing above is CI-validated yet)

Main branch protection has **no required status checks**, so every failure below is invisible at
merge time. That is the real defect; the individual red jobs are symptoms.

| Gate | Run | Failure |
|---|---|---|
| Coverage Gate (Tier-2) | 41394778746 | root tarpaulin killed at 60s on `fr007_proc_pid_watch` — addressed by `cc6dceed` + `58d51bd3` |
| cargo-deny (push) | 41394778751 | advisories: `webpki-roots` RUSTSEC, yanked `chacha20 0.10.1` in `iac/Cargo.lock` |
| Dependency Audit | 41505842523 | licences: `winfsp-sys` GPL-3.0 (product/legal call) |
| Security | 41545065359 | `lru 0.12.5` RUSTSEC-2026-0002/0253, `crypto-bigint` RUSTSEC-2026-0387; Gitleaks backlog ~1453 lines |
| Trufflehog | 41394778729 | workflow bug: `BASE == HEAD` on push to main |
| Trunk Check | 41394778716 | pinned `trunk-io/trunk-action` SHA no longer resolves |
| OpenSSF Scorecard | 41394778682 | pinned `github/codeql-action` SHA no longer resolves |
| Quality Ratchet | 41394778689 | `npm ci` hits `EUNSUPPORTEDPROTOCOL` on `workspace:*` — repo is bun/pnpm |
| Nightly CVP | 41839290304 | 27 landing errors / 37 sites (workflow demands `src/pages/index.astro`, only 11 have it); docs-3 placeholder `SUP-<...>` at `docs/atlas/portfolio/topic-proposals.json` index 29 |

Also open: 11 PRs, 25 local branches (several `[gone]`), sibling worktree `PhenoShared-d1-nontq`
dirty (7 files) and 154 behind, IAC `fail-under` still 10, 21 branches awaiting `-D` approval,
89 workflows in the fan-out.

## 7. Where the coverage gate actually stands (run 41951143548)

The third run got all the way through the suite: **646 test binaries reported `ok`, zero failures**,
and the whole workspace ran inside the armed 180s budget instead of being killed at 60s. The
`fr007_proc_pid_watch` cases no longer time out; the golden snapshots match because the help width is
now pinned.

It still fails, on the last step, for a reason that is a policy question rather than a defect:

```
37.54% coverage, 36295/96696 lines covered
Coverage is below the failure threshold 37.54% < 71.00%
```

The 71% figure comes from ADR-040, whose tier model names `nanovms-core`, `nvms-ffi`,
`pheno-config` and `pheno-compose-driver`. **Three of those four crates no longer exist** in the
repointed workspace, so no tier definition is being applied: `--workspace` simply averages ~200
crates, including UI/gfx crates with no tests at all (`src/voxel/*`, `src/water/*`) and fake harness
binaries under `tools/`. A whole-workspace number can never express a per-tier threshold.

Measured for context: `crates/sharecli` 58.5%, `phenotype-gfx` 73.9% (but counted as 0 for its
voxel/water modules elsewhere), `fabric-graph` 88.4%, `traceability-core` 80.9%,
`sharecli-fleet` 86.6%, `phenotype-config` 83.3%.

Two honest options, both one commit:

- **Ratchet the floor.** Set `--fail-under` to the measured value and require it never decrease.
  Cheap, unblocks immediately, but the job keeps a name that claims 71%.
- **Restore the tier model.** Define the lib/framework package list that ADR-040 actually means,
  gate those crates at 71%/70% with `--packages`, and let the rest be measured but not gated.
  Faithful to the ADR, requires choosing the crate list (the old names are gone).

The threshold is the owner's call; I did not lower a quality gate unilaterally.

## 8. Environment blockers observed this session

- `cargo-tarpaulin` is Linux-only; macOS host has no backend.
- Colima/Docker socket absent (`~/.colima/default/docker.sock`), so no local Linux container.
- `proxy.golang.org` resets connections over IPv6 on this host; `GODEBUG=netdns=cgo` fixes it.
  `go.mod` requests 1.26.0 and the download is flaky, but 1.26.9/1.26.10 are already cached in
  `~/go/pkg/mod/golang.org/` — pin `GOTOOLCHAIN=go1.26.10` to build offline.
