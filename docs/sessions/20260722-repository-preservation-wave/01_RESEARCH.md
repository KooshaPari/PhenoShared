# Research

## Findings

- GitHub owner is `KooshaPari`; 291 owned repositories were enumerated.
- `AgilePlus` is the canonical spec-lifecycle platform spine, not a catch-all archive owner.
- Seven source remotes are empty shells; emptiness does not prove namesake local work reached cloud.
- `AgilePlus-recovery-20260714` is already reachable from canonical AgilePlus.
- The harmonizer implementation was absorbed by AgilePlus PR 756; only provenance remains.
- `zz-archive-phenotype-omlx-tmp` has 28 of 29 heads represented; its default `main` is missing.
- `omniroute-rust` is a 13-crate workspace and requires crate-level ownership review.

## Authority order

`BOUNDARY_OWNERS.md` and accepted ADRs override stale absorption rows and July 21 catch-all runbooks.

## 2026-08-12 cockpit source custody decision

- Preserve only the approved `build_leapfrog_cockpit.py` and point-in-time `beads.jsonl` copies under `custody/cockpit/20260812/`; their manifest is the custody boundary.
- Do not copy `~/.agileplus/audit.jsonl`: the external mirror had 22 scanner hits. Although the copied builder's historical prose names it as a mirror, `BEAD_SOURCES` actually contains only `phenotype-dag/beads.jsonl`; the mirror was not a supported configured input and is not captured here. Do not retain rendered HTML, the legacy rendered reference, or the secondary `beads/bead-cockpit.py` writer.
- The copied builder is preserved as non-executable historical provenance. Never run it against live paths: its fixed output path is the excluded cockpit HTML and execution can overwrite that live artifact.
- This is evidence of captured inputs, not a claim of current source parity, rendered-output validity, publication, or promotion.
