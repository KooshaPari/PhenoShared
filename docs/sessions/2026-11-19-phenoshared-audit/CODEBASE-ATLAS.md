# PhenoShared — Codebase Atlas

**Measured:** 2026-11-19, at `f06c3cc7f` (2026-11-17T15:33:13-08:00), branch `main`.
**Method:** read-only `git` plus batch-safe line counting over the tracked tree. Every figure is
labelled with how it was obtained: *verified* means the author re-ran it directly, *lane* means it
comes from the parallel atlas measurement and carries its method. Anything unmeasured is
`UNKNOWN` with the blocker named.

---

## 1. What this repository is

PhenoShared is a **polyglot container SDK workspace**: one repository holding separately
importable units in four languages, a very large documentation set, and the accumulated remains of
many absorbed sibling projects. It is not one product with one build. It is a distribution surface
whose units are meant to be consumed individually.

That intent is the operator's own framing and it governs the reshape recommendations:

> "a harmonious decentralized CONTAINER SDK so you dont hae to imkport the entire bulky item.
> and in some cases just not possible to have it be one item"

The measurements below show how far the present tree is from that shape.

---

## 2. Size

| Metric | Value | Source |
|---|---|---|
| Tracked files | 55,898 | verified, `git ls-files \| wc -l` |
| Working tree on disk | 5.2 G | verified, `du -sh .` |
| — `target/` | 2.7 G | verified (untracked build residue) |
| — `node_modules/` | 515 M | verified (untracked) |
| Code lines, all languages | **6,228,356** | lane |
| Docs and config lines | 3,296,977 | lane (markdown 2.0 M, json 1.08 M) |

Tracked content is roughly 2 G of the 5.2 G; the rest is local build residue that a fresh clone
never receives.

---

## 3. Language mix

Line counts obtained by concatenating every tracked file of the extension into a single `wc -l`
stream. This matters: `xargs wc -l | tail -1` returns **only the final xargs batch** and understates
a 11,466-file language by an order of magnitude. The earlier draft of this document made exactly
that error and reported Rust at 365,543 instead of 3,158,866.

| Language | Lines | Share of code | Source |
|---|---|---|---|
| Rust | 3,158,866 | 50.7% | verified |
| Python | 1,244,093 | 20.0% | verified |
| Go | 594,188 | 9.5% | verified |
| TypeScript | 460,069 | 7.4% | verified |
| TSX | 252,517 | 4.1% | verified |
| JavaScript | 87,860 | 1.4% | verified |
| Swift | 89,687 | 1.4% | lane |
| HTML / Shell | 71,293 / 71,185 | 1.1% / 1.1% | lane |
| Six-language verified subtotal | 5,797,593 | | |

**Attribution caveat, and it is a large one:** the lane measured **2.86 M code lines as
absorbed or vendored** — `docs/absorbed-from-PhenoTooling` alone is 1.46 M and
`apps/zz-ref-Helios*` is 1.40 M — leaving roughly **3.4 M first-party lines**. Go being smaller
than Rust is therefore a first-party fact, while much of the TypeScript and Python mass is
inherited.

---

## 4. Build topology

| Surface | Count | Source |
|---|---|---|
| Root manifests | 3 | verified (`Cargo.toml`, `package.json`, `pyproject.toml`) |
| Cargo workspace members | **292 packages**, from 287 member-list entries | verified, `cargo metadata --no-deps`; entries by `tomllib` |
| `crates/*/Cargo.toml` files | 510 | verified |
| Nested sub-workspaces | 26 | lane (`Cmdra`, `agile-plus`, `gateway`, …) |
| `go.mod` files / `go.work` | 47 / **0** | verified |
| `[[bin]]` declarations | 126 | lane |
| Python projects | 87 | lane |
| Node packages | root VitePress + 8 `packages/*` | lane |
| CI workflows | 81 | verified |
| Dockerfiles | 80 exact-name / 81 case-insensitive substring | verified on both hosts; the two methods differ by one file |

Four findings carry the structural story:

1. **The root manifest defines no package.** `[package]` is absent from the root `Cargo.toml`
   (verified), so a root `src/` can never compile. The repository is a workspace and nothing else.
2. **Nested sub-workspaces are invisible to the root build.** 26 cargo sub-workspaces do not
   participate in `cargo build --workspace` at the root. Code that exists, builds in isolation, and
   never appears in a root build is the definition of a container relationship that was never
   formalised.
3. **47 Go modules with no `go.work`.** Verified. Go is present as 47 independent module roots, so
   there is no single Go build either.
4. **Absorbed residue is a build member.** The member list includes `absorption-residue-Agentora/…`,
   so absorb-program leftovers participate in the workspace graph.

**Member-count reconciliation.** Five figures circulate and only two of them are true statements
about members.

| Figure | What it actually counts | Method |
|---|---|---|
| 292 | workspace packages | `cargo metadata --no-deps` on 2026-11-19 |
| 291 | workspace packages | same command on 2026-11-12 |
| **287** | literal entries in the `members` array | `tomllib`, and independently a worker's parse |
| 288 | nothing: an off-by-one from my own first pass | quote-counting a `sed` range |
| 240 | nothing: the `sed` range terminated early | `sed -n '/members = \[/,/\]/p' | grep -c '"'` |

The entries expand to 292 packages because many are globs, and `exclude` removes four paths.
Only `cargo metadata` is authoritative: **a count of literal entries is not a count of members**,
and neither is a count of quoted lines. My earlier 288 was wrong and the worker who said 287 was
right; the disagreement is recorded here rather than quietly corrected, because the method that
produced 288 also produced 240 on a different host and either number would have read as measured
fact.

Three root manifests means three dependency graphs that drift independently. A Rust consumer never
learns about the npm unit, and neither learns about the Python unit.

---

## 5. Tracked mass by top-level directory

| Directory | Tracked files | Size | Role |
|---|---|---|---|
| `crates/` | 14,219 | 265 M | Rust workspace units |
| `docs/` | 11,919 | 309 M | documentation plus rendered site source |
| `apps/` | 9,617 | 140 M | TS/JS/Python applications |
| `absorption/` | 6,583 | 68 M | absorbed sibling projects (§7) |
| `audits/` | 1,750 | 40 M | audit artifacts |
| `agents/` | 1,533 | 29 M | agent definitions and harness material |
| `agileplus/` | 1,106 | — | absorbed AgilePlus material |
| `libs/` | 816 | 14 M | shared libraries |
| `_archived/` | 632 | — | retired material, still reachable |
| `sites/` | 603 | — | documentation sites |
| `scripts/` `bench/` `servers/` `python/` | 431 / 391 / 386 / 314 | — | tooling and services |

Documentation is 21% of tracked files and markdown alone is about a third of all tracked lines.
That ratio is coherent for a docs-first SDK and is also why the repository reads as a corpus.

---

## 6. History shape (summary; detail in the dossier)

| Metric | Value |
|---|---|
| First commit on `main` | `043003e9a`, 2026-03-17, "Initial commit: workspace setup" |
| Root commits across all refs | **21** — the repository is a union of unrelated histories |
| Oldest object anywhere | `56319267b`, 2026-02-23, absorbed `tokenledger` |
| Commits on `main` / all refs | 1,457 / 5,610 |
| Refs total | 1,415 = 181 local + 162 `origin` + 205 `_sweep` + 841 `triage/pr` + 25 tags |
| Authors | KooshaPari 2,164 · Koosha Paridehpour 1,271 · Mergify 646 · dependabot 631 · Forge 291 · jcode 237 |

The `_sweep` and `triage` namespaces are automation memory, not product branches, and they
outnumber real branches about 6 to 1.

---

## 7. Structural confusion, named

Each was confirmed by inspection rather than inferred.

1. **`absorption/` holds plain copies.** 6,583 files, 11.8% of the tree, no nested `.git` anywhere.
   Provenance is a per-directory `PROVENANCE.md` convention, and three absorbed directories have none.
2. **Tracked bloat that is not source.** Verified line counts: `.patch` files hold **1,500,120**
   lines, `.o` objects 213,148, `.bundle` 418,787, plus `.rlib` and a checked-in `zig-cache`. Roughly
   2.1 M tracked lines are build output or patch archives.
3. **`_archived/` is live.** 632 tracked files still referenced in places. "Archived" describes
   intent, not state.
4. **Duplicated trees.** Several absorbed projects exist twice, under `absorption/…` and under
   `docs/absorbed-from-…`, with byte-identical content.
5. **Generated output is committed.** A rendered documentation build sits in `.vitepress/dist/`,
   tracked, so a source search for "dossier" returns compiled JavaScript.
6. **Agent state was committed.** `state/` held process-inventory dumps, session-resume files and
   codex transcripts. Removed from the tip in `f06c3cc7f`, still in history. See dossier §5.

---

## 8. Governed artifacts that already exist, and that are stale

The repository already contains an **atlas package** at `docs/atlas/` — roughly 250 tracked files:
`PRD.md`, `HLD.md`, `LLD.md`, `ALD.md`, `SPECIFICATION.md`, 13 ADRs, 11 spec directories, 37 product
dossiers, schemas, examples, and its own `qa/` doctrine. It is a governed package with
`MANIFEST.json` (257 payload files with sha256), `SHA256SUMS`, `INDEX.md` and a validator at
`docs/atlas/scripts/validate_package.py` that `cvp-nightly.yml` runs in CI.

Two facts follow, and both matter to anyone adding documentation here:

1. **Its generated artifacts are stale.** `codebase/INVENTORY.md` was last committed **2026-11-07**,
   before the November absorption waves; `codebase/HYGIENE.md` is from **2026-09-20**; `MANIFEST.json`
   from **2026-09-16**. The inventory reports 29,049 tracked files and 1,095,486 Rust lines against
   today's 55,898 files and 3,158,866 Rust lines — it describes about half the present tree. It also
   reports 81 root workspace members where `cargo metadata` now reports 292; the file predates the
   waves, so the gap is expected, but the file must be regenerated rather than quoted.
2. **The validator constrains anything placed inside the package.** It walks `docs/atlas/**/*.md`,
   requires every relative markdown link to resolve inside the package, and asserts that no file
   under it is empty or a symlink. Audit output therefore belongs in `docs/sessions/` (as this
   document does), not inside a checksum-governed package.

The existing `docs/atlas/codebase/` inventory also defines its terms more carefully than a `wc -l`
run can: logical LOC (newline bytes plus one for a missing trailing newline), ownership by deepest
tracked `Cargo.toml`, and test counts by declaration syntax per language. Where this document and
that package disagree, prefer the package once it has been regenerated.

---

## 9. What a consumer can actually import today

| Unit | Separately consumable? | Blocker |
|---|---|---|
| `crates/*` | Partly | 292-package root graph; 26 nested sub-workspaces are outside it; no per-crate release cadence observed |
| `apps/*` | No | consumes sibling paths, not published packages |
| `libs/*` | `UNKNOWN` | no per-package publish workflow examined |
| Go modules | In principle | 47 module roots, no `go.work`, no tags observed per module |
| Python projects | `UNKNOWN` | 87 projects, no index/publication evidence examined |
| Docs site | Yes | self-contained VitePress build |
| Absorbed trees | No | unpackaged source copies |

That table is the gap: today the container is **one repository**, not a set of containers.

---

## 10. Re-measurement recipe

```bash
# batch-safe line counting (never xargs wc -l | tail -1)
git ls-files -z -- '*.rs' | xargs -0 cat | wc -l

cargo metadata --no-deps --format-version 1 | python3 -c \
  'import json,sys; print(len(json.load(sys.stdin)["workspace_members"]))'

git ls-files | wc -l                                  # tracked files
git for-each-ref --format='%(refname)' | wc -l        # refs
git rev-list --max-parents=0 --all | wc -l            # root commits
git ls-files -- '*go.mod' | wc -l                     # module roots
du -sh target node_modules 2>/dev/null                # local residue
```

Any figure here that a later reader cannot reproduce is a defect in this document and should be
corrected rather than trusted.

---

## 11. Cross-host verification (desk, 2026-11-19)

Every figure above was re-derived on a second machine from a fresh clone, not from the working tree.
Host: `ssh desk` -> WSL2 Fedora, 4 cores, cargo 1.100.0, 815 GB free. Clone landed on
`f06c3cc7fdf61d75e8aa9f8d0feade068760d308`, the same commit the Mac worktree was read at, so the
comparison is like-for-like rather than across time.

| Figure | Mac | Desk | Agree |
|---|---|---|---|
| Tracked files | 55,898 | 55,898 | yes |
| Rust LOC | 3,158,866 | 3,158,866 | yes |
| Python LOC | 1,244,093 | 1,244,093 | yes |
| Go LOC | 594,188 | 594,188 | yes |
| TS LOC | 460,069 | 460,069 | yes |
| TSX LOC | 252,517 | 252,517 | yes |
| JS LOC | 87,860 | 87,860 | yes |
| `go.mod` / `go.work` | 47 / 0 | 47 / 0 | yes |
| CI workflows | 81 | 81 | yes |
| Workspace packages | 292 | 292 | yes |
| Files with `<REDACTED>` under `docs/atlas` | 13 | 13 | yes |
| `members` entries | 288 (wrong) | 240 (wrong) | **no** |
| `members` entries, `tomllib` | n/a | **287** | resolved |

Two new figures the desk produced that the Mac pass had not measured: **2,007,094 lines of
Markdown** and **1,082,522 lines of JSON** are tracked. The repository's prose and generated data
outweigh its Rust source in line count, which matters for the reshape: a container SDK has to ship
documentation and schema, and here those are already the larger half of the tree.

The single disagreement was a counting method, not a repository fact, and it is left in the table
with both wrong values visible. A reconciliation that only shows the winning number is how 288 would
have survived into a third document.
