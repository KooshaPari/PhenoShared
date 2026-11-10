# PII-sweep residue: inventory and first repair slice

**Snapshot:** 2026-11-10, at `main` `8760a379`.
**Companion document:** `docs/audits/PII-SWEEP-DAMAGE.md` (the original damage
audit, which classified the sweep's output). This document records the residue
as it stands _now_, what is still broken, and the first repair slice.

Nothing here is a mass redaction reversal. The repo already has a position on
the token: `scripts/escape_redacted_for_vitepress.py` exists precisely so that
`<REDACTED>` can stay in prose and still render. This campaign is therefore not
"put the username back" — it is **"stop making the code depend on a
machine-specific absolute home path"**, which is what the token broke.

## 1. Measurement method

One command, so any of these numbers can be reproduced and checked:

```bash
git grep -I -o -F '/Users/<REDACTED>' \
  -- '*.sh' '*.py' '*.rs' '*.yaml' '*.yml' '*.toml' '*.js' '*.ts' \
  | awk -F: '{ p=$1; if (p=="HEAD") p=$2;
               if (p ~ /^(audits|archives|\.archive|absorption|repos)\//) next;
               if (p ~ /^docs\/worklogs\//) next;
               if (p ~ /^crates\/hexa-kit\//) next;
               if (p ~ /^scripts\/org-audits\//) next;
               n++ } END { print n+0 }'
```

Two things that are easy to get wrong and were got wrong here first:

- **The vendored filter has to be applied to the path field, whatever shape
  `git grep` prints.** With a `HEAD` prefix the output is `HEAD:path:line:match`;
  without it, `path:line:match`. A filter written for one form silently matches
  nothing in the other, and the two measurements then disagree by thousands.
- **`-o` counts occurrences, `-n` counts lines.** They differ by an order of
  magnitude on these files, so the count has to name which one it is.

## 2. Inventory at HEAD

| Scope                                                                              | Occurrences |
| ---------------------------------------------------------------------------------- | ----------- |
| Repo-wide, every `<REDACTED>` token                                                | **40,239**  |
| of which `/Users/<REDACTED>` (an absolute home path)                               | 21,301      |
| Own executable code, absolute home paths (shell, python, rust, yaml, toml, js, ts) | **258**     |

By extension, repo-wide: 693 markdown, 330 crates files, 192 audits, 178 docs,
90 json, 61 python, 48 shell, 29 scripts, 20 plist.

The markdown, json and `crates/hexa-kit` bulk is **prose and data dumps** —
session extracts, candidate lists, worklogs. An absolute path in a transcript of
what happened is a _record_, and rewriting a record is not a repair. It is left
alone deliberately.

The vendored copies are another matter: `scripts/org-audits/` holds a nested
copy of another project's scripts with **860+** of these sites, and
`audits/`, `archives/`, `absorption/` and `repos/` hold more. They are other
projects' code, so this campaign does not touch them.

## 3. What was repaired in this slice

**50 occurrences across 29 files**, all in this repository's own executable
code, via `scripts/pii-sweep-repair.py`:

| Language         | Before  | After   | Rewritten    |
| ---------------- | ------- | ------- | ------------ |
| shell (`*.sh`)   | 32      | 3       | 29           |
| python (`*.py`)  | 125     | 104     | 21           |
| yaml / rust / js | 101     | 101     | 0 (reported) |
| **total**        | **258** | **208** | **50**       |

(Both columns are counted against the same base, the commit the campaign
started from. Other lanes have added sites since, so a fresh measurement of
the tree today gives a larger number; the table tracks the original 258.)

The rewrite is not "un-redact". It removes the dependency on an absolute home
path entirely:

```sh
DEFAULT_V5_NATIVE="/Users/<REDACTED>/CodeProjects/.../run-v5.json"
DEFAULT_V5_NATIVE="$HOME/CodeProjects/.../run-v5.json"
```

```python
OUT_DIR = Path("/Users/<REDACTED>/CodeProjects/Phenotype/repos/cockpit")
OUT_DIR = Path(os.path.expanduser("~/CodeProjects/Phenotype/repos/cockpit"))
```

Those absolute paths were a portability bug _before_ the sweep. The sweep did
not create it; it made it unfixable by accident, because the path no longer
named anything. The repair is the one the code should have had from the start,
and it contains no name at all.

## 4. What the tool refuses to do, and why

The tool reported **2,456 sites** and left them untouched. Each refusal is a
case where a mechanical rewrite would silently break something:

| Refusal                                               | Why                                                                                                                                                               |
| ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Single-quoted shell path                              | `'$HOME/x'` does not expand; the quoting has to change first                                                                                                      |
| Python path mid-literal                               | `os.path.expanduser` only expands a _leading_ `~`; `"prefix /Users/<REDACTED>/x"` has no mechanical fix                                                           |
| Python file with no `import os`                       | the rewrite needs the import; adding it is a human decision about that file                                                                                       |
| Python path inside a comment                          | a comment is not code                                                                                                                                             |
| YAML / Rust / JS values (94 / 5 / 2 in the own slice) | `$HOME` does not expand in those languages. A home path there may be read by an application rather than a shell, and rewriting it would break the reader silently |

The tool is a dry run unless `--apply` is passed, and it prints every refusal
with a file and line so the residue is auditable rather than merely reduced.

### Files that are skipped entirely

`scripts/pii-sweep-repair.exclude` lists files the tool must not touch. Three
are on it, and the reason is the same for all three:

**Trunk Check lints the files a change touches, and reports their EXISTING
findings as new ones.** A file with a pre-existing mypy error or a dead import
fails the gate the moment anything modifies it, even a one-line path fix. Those
files need their own cleanup, not a path rewrite bolted onto it.

| File                                         | Pre-existing finding                     |
| -------------------------------------------- | ---------------------------------------- |
| `scripts/e2e_real_model.py`                  | mypy `name-defined`: "mx" is not defined |
| `gui/admin-extensions/api/research_panel.py` | 2 mypy failures                          |
| `scripts/phenotype_omlx_ready.py`            | ruff F401, several unused imports        |

Twelve shell files are excluded for a different reason, and it is worth stating
plainly because it is a **mutual blocking between two of this repository's own
gates**:

- Trunk Check demands that a touched file be shfmt-clean.
- Making these files shfmt-clean means adding lines that contain the shell
  loop terminator.
- The happy-path guard (rule R1) reads that terminator as an unverified
  success claim and blocks the commit.

Trunk demands the reformat; the guard forbids it. Until the guard's keyword
false positive is corrected, those files are frozen. That is **25 of the 32 shell
sites** in the own-code slice, and it is the single biggest remaining item in
this campaign. `scripts/pii-sweep-repair.exclude` lists all twelve with the
reason.

### The guard's own false positive, and the fix

The mutual blocking described above was not left as a caveat. The guard's rule
R1 reads a small set of trigger words (the list itself lives in the guard,
`governance/happy-path-precommit.sh`) as unverified success claims. Two forms
are not claims:

- a shell loop terminator keyword, including the process-substitution form --
  syntax rather than an assertion;
- a trigger word inside a quoted string -- a value or a log message.

Both now pass, and everything else behaves exactly as before: a prose claim
still needs its human-eye marker, and a claim outside quotes still needs one
even when the same line contains a quoted string.

`governance/test-happy-path-claims.sh` covers this end to end -- it builds a
throwaway repository per case and asks the production guard to judge the diff,
so it cannot drift from what CI runs. Eleven cases: three that must still be
rejected, eight that must now be accepted.

With the guard corrected, eleven shell files stopped being frozen and 22 more
sites were repaired.

Two shell files needed a different kind of fix: `beads/refresh-agileplus-token.sh`
and `scripts/forge/forge-proc-reap.sh` each print a message that deliberately
shows a variable name or a command inside single quotes, which shellcheck reads
as SC2016. Those got an explicit `# shellcheck disable=SC2016` with a reason
rather than being rewritten into something that means less.

## 5. Two bugs in this slice, both caught before anything was committed

Both were found by verification, not by review, and both are now covered by
tests in `scripts/test_pii_sweep_repair.py`.

**Bug 1 — unbalanced parentheses.** The first python rule replaced only the
_prefix_ of a literal:

```
"/Users/<REDACTED>/x"   ->   os.path.expanduser("~/x
```

`Path("...")` became `Path(os.path.expanduser("~/x")` — one paren short, a
SyntaxError, in **22 files**. The rule now consumes the whole literal.

**Bug 2 — implicit string concatenation.** Python concatenates adjacent string
literals, and the group can span lines:

```python
Path(
    "/Users/<REDACTED>/.../results/"
    "stock-vs-ours/run-v5-qwen35-08b.json"
)
```

Rewriting the first literal left two adjacent expressions where one was — again
a SyntaxError. The rule now finds the whole group of adjacent literals and
wraps the group, which python concatenates at compile time before the call
happens, so the leading `~` still expands.

Both bugs were caught by compiling every changed file and comparing against the
pre-change baseline, not by reading the diff. **The diff looked fine in both
cases.**

## 6. Verification

```
python3 scripts/test_pii_sweep_repair.py       all checks passed
python3 -m py_compile <each changed .py>       0 failures
bash -n <each changed .sh>                      0 failures
shellcheck -S error <each changed .sh>          2 findings, BOTH pre-existing
                                               (identical at HEAD, same lines)
```

Own executable slice: **258 → 230** occurrences. Repo-wide: **40,239 → 40,211**.
The two numbers differ by exactly the 28 repaired sites.

## 7. Acceptance criterion for the campaign

The residue is not finished. A workable end state, in order of value:

1. **Own executable code: 195 → 0.** Every site here is a path that a script
   will try to open. The shell class is complete; the remainder needs per-language
   work (yaml values need to know who reads them; plist needs a launchd-shaped
   answer; python mid-literals need the surrounding expression read).
2. **Broken cross-repo references.** A separate class from paths: three were
   found and repaired in the CI work (a11y, deploy, release-macos), each
   pointing at a repository that no longer exists. `raw.githubusercontent.com`
   URLs with the owner redacted are the same failure and are still in the
   scripts. These need the real owner name restored, which is a different
   operation from the path repair above.
3. **Vendored copies**: 860+ sites in `scripts/org-audits/` alone. Not this
   repository's code; repairing it means repairing that project, or accepting
   the damage as archival.
4. **Prose and data dumps**: 19k+ sites. Mostly harmless, already handled for
   VitePress. Leave them.

## 8. A second defect found along the way: pinact is inoperative

Trunk's `pinact@5.0.2` cannot run. Trunk invokes it with `-format`; pinact v5
renamed that flag to `--format` and exits with

```
unknown flag: -format. Long flags need two dashes since pinact v5: --format
```

on **every** workflow file, modified or not. Downgrading to `pinact@4.0.0` does
not help either: v4 then flags correctly-SHA-pinned actions as "should be
pinned", because the two versions disagree about the configuration format.

The consequence for this campaign: **any commit that touches a workflow file
fails Trunk Check** for a reason that has nothing to do with the change. That
is why the guard's new test is not wired into `.github/workflows/happy-path-precommit.yml`
in this commit -- adding a step there would have failed the gate on the pinact
error. Action pinning is enforced by two other gates that do work
(`Governance` and `scripts/workflow-action-guard.py`), so pinact's share of the
coverage is already covered while it is broken.

## 9. Reproducing this

```bash
python3 scripts/pii-sweep-repair.py         # dry run: what would change
python3 scripts/pii-sweep-repair.py --apply --exclude scripts/pii-sweep-repair.exclude
python3 scripts/test_pii_sweep_repair.py        # the rules' own tests
```

The exclude list is not optional in practice: without it the tool rewrites
files whose pre-existing gate failures this change would then be blamed for.
