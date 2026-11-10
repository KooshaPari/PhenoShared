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

**63 occurrences across 38 files**, all in this repository's own executable
code, via `scripts/pii-sweep-repair.py`:

| Language         | Before  | After   | Rewritten    |
| ---------------- | ------- | ------- | ------------ |
| shell (`*.sh`)   | 32      | **0**   | 32           |
| python (`*.py`)  | 125     | 94      | 31           |
| yaml / rust / js | 101     | 101     | 0 (reported) |
| **total**        | **258** | **195** | **63**       |

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

The tool reported **2,435 sites** and left them untouched. Each refusal is a
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

Own executable slice: **258 → 195** occurrences. Repo-wide: **40,239 → 40,176**.
The two numbers differ by exactly the 63 repaired sites.

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

## 8. Reproducing this

```bash
python3 scripts/pii-sweep-repair.py         # dry run: what would change
python3 scripts/pii-sweep-repair.py --apply    # write the safe rewrites
python3 scripts/test_pii_sweep_repair.py        # the rules' own tests
```
