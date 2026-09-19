# Desktop handoff prompt

Copy everything inside the fence into your desktop agent. It is written to be
self-contained: host, what to read, what to own, and how to prove it.

Replace `kooshas-laptop` with the tailnet name of the machine holding the
working copy if it differs.

```text
CONTEXT
You are picking up half of a two-machine effort on PhenoShared, a container
repository (50+ absorbed repos) at github.com/KooshaPari/PhenoShared.
Another agent works the other half on the same machine you are about to SSH
into. You will never edit its files: the split is by path prefix and is
listed under "YOUR HALF" below.

STEP 1 — SSH in
  ssh kooshas-laptop          # tailnet; key already authorised
  cd ~/CodeProjects/Phenotype/repos/PhenoShared

STEP 2 — Read what is NOT in git first
The most recent analysis is in the working tree, and some of it may not be
pushed yet. Before you pull, capture the local-only state:

  git status --short                       # uncommitted work by the other agent
  git log --oneline -15                    # what landed recently
  ls ~/.jcode/scratch/                     # all audit harnesses and repros
  ls ~/CodeProjects/Phenotype/repos/       # other phenotype-* checkouts (relics)

Then pull:
  git fetch origin && git rebase origin/main    # or merge; do not force anything

STEP 3 — Read these five artifacts before touching code
  docs/plan/LONG-TERM-WBS.md              # the plan; your epics are E5 and E8
  docs/audits/GIT-HISTORY-INTEGRITY.md    # what the git history actually is
  docs/audits/IDENTITY-CLAIMS.md          # what the repo claims vs reality
  docs/audits/PII-SWEEP-DAMAGE.md         # collateral damage from the redaction sweep
  docs/absorption/ABSORPTION-LINEAGE.md   # source repo -> destination mapping
  docs/atlas/INVENTORY.md, FILES.md, HYGIENE.md   # generated inventory

If any of those do not exist yet, the other machine is still generating them.
Proceed with whichever exist and say which were missing.

STEP 4 — YOUR HALF
Epic E5 (hygiene at scale) and E8 (product-domain triage) from the WBS.

You own exactly these paths. Do not edit anything else:
  crates/focus-*  crates/fabric-*  crates/agileplus*  crates/eyetracker-*
  crates/sharecli-*  crates/substrate-*  crates/connector-*  crates/eidolon-*
  crates/playcua-*  crates/port-*  crates/driver-*  crates/engine-*
  agileplus/  sites/  servers/  python/  unity/  bench/  agents/  registry/

The other machine owns, and you must not touch:
  docs/  audits/  absorption/  .github/  scripts/  Cargo.toml  Cargo.lock
  rustfmt.toml  clippy.toml  crates/phinbox/**

E5 tasks: work the file-size breach list (hard limit 500 lines, target 350),
rename test files that violate the naming rule (no _v2/_new/_old/_final/
_temp/_backup/_draft/_complete, no test_*_unit, no arbitrary numbering), list
the three archive trees for consolidation, and fix documents whose H1 names a
different project while living in this repo (the identity audit found 39).

E8 tasks: for EACH absorbed family in your half, answer three questions and
record the answers: does it build, does it test, does it have a home? Then
recommend keep / absorb / split / delete. ~16 tasks per family; the count is
the point, do not sample.

STEP 5 — HOW TO VERIFY (non-negotiable)
This repo's defining failure mode is "a mechanism was built, never worked,
and nothing detected it". Four examples: clippy.toml made every clippy run
exit 101; rustfmt.toml uses 19 nightly-only options while CI runs stable so
`cargo fmt --check` cannot pass; the tray-native feature never compiled; and
a commit titled "Add unit tests for DurationExt" committed 3,757 zero-byte
files.

So for every change:
  - run it, do not reason about it
  - if you add a regression test, revert your fix and confirm the test FAILS,
    then restore the fix and confirm it passes
  - report the exact command and its real output, not a summary
  - if you cannot verify something, say "unverified" — never imply otherwise

STEP 6 — REPORT
Per family or file cluster: what you found, what you changed, the command
that proves it, and anything you deliberately left alone with the reason.
Flag anything that looks like it contradicts docs/audits/GIT-HISTORY-INTEGRITY.md
or docs/audits/IDENTITY-CLAIMS.md.

CONSTRAINTS
  - Do not rewrite git history. No force-push, no rebase of published
    branches, no filter-repo, no reset --hard. The 694-commit ledger is
    shared and cited by SHA in the audit documents.
  - Do not squash other people's work into your commits.
  - Commit in small, message-scoped units. Never mix a reformat with a logic
    change.
  - If you need a decision (e.g. which archive tree to keep), ask rather than
    guess, and keep working on something else meanwhile.
```

## Notes for the human

- The split is by path prefix specifically so the two machines cannot conflict
  in git. If you would rather split by *theme* than by path, the only
  alternative that stays conflict-free is: one machine does gates/provenance
  (E1–E4, E6, E7, E9) and the other does all product domains (E8) plus
  hygiene (E5) — which is what the prompt says.
- E1 (gates) is on this machine deliberately: until `make check` can run,
  nothing either machine merges is actually verified.
- If the desktop is the box with 64 GB / 2 GPUs and 5.5 TB, it is the better
  host for the workspace-wide `cargo build/test/clippy --workspace` runs in
  E2, which are the expensive ones. Swap E2 to the desktop if you prefer.
