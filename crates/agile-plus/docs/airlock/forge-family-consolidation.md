## STATUS: ✅ SPONSOR ACK 2026-07-29 — G4 ACK (import only, no squash)

**Sponsor decision (2026-07-29 transcript):**
> *"g3a g4 ok g5 no only squash lattr as you consume into foremr g4 no g7 no NEVER squas parent repos with deep improtnat histories. only a cosnumed REPO AND ONLY AS A NEW MAIN BRANCH WHILE YOU KEEP ONE FULL HISTOIRY OR OTHER FULL HIST RBANCEHS PRESENT"*

**Decoded:**
- **G4: ACK** — `pheno-forge-smoke` and `pheno-forge-plugins` may be imported into `forgecode` on **NEW feature branches** (no squash, no force-push).
- After import, the **consumed** repos (`pheno-forge-smoke`, `pheno-forge-plugins`) may be squashed per `SQUASH_POLICY.md` — but ONLY as a new branch, with full history retained.
- `forgecode` itself is a **parent repo** (fork of `antinomyhq/forgecode`) → NEVER squashed.
- `MCPForge` is a **parent repo** (fork of `isaacphi/mcp-language-server`) → NEVER squashed.
- `phenoForge` is a distinct project → NOT consumed by `forgecode`.

### G4 Execution Plan (Pending per-phase ACK)

| Phase | Action | Target Branch | Reversible? |
|---|---|---|---|
| 1 | Shallow clone `pheno-forge-smoke` to `/tmp/imports/pheno-forge-smoke` | n/a (clone) | yes (rm dir) |
| 2 | Shallow clone `pheno-forge-plugins` to `/tmp/imports/pheno-forge-plugins` | n/a (clone) | yes (rm dir) |
| 3 | Identify smoke commits unique to its branches | n/a | yes |
| 4 | Identify plugins commits unique to its branches | n/a | yes |
| 5 | In `/repos/forgecode`, create `feat/import-pheno-forge-smoke-2026-07-29` off `main` | new local branch | yes |
| 6 | Cherry-pick smoke commits into `crates/pheno-forge-smoke/` | new branch only | yes |
| 7 | Create `feat/import-pheno-forge-plugins-2026-07-29` off `main` | new local branch | yes |
| 8 | Cherry-pick plugins commits into `crates/pheno-forge-plugins/` | new branch only | yes |
| 9 | Push both feature branches to `origin` (no force-push) | remote refs | yes |
| 10 | `forgecode/main` is **NEVER** touched, **NEVER** force-pushed | n/a | n/a |
| 11 | After import verified, optionally squash `pheno-forge-smoke` and `pheno-forge-plugins` to a new branch (consumed-repo policy) | new branch on consumed repos | yes |

**No force-push. No `forgecode` squash. No MCPForge squash. No phenoForge mutation.**

---

## STATUS HISTORY

- 2026-07-28 — Audit completed; 4 sub-repos identified; G4 proposed.
- 2026-07-29 — Sponsor ACK: G4 confirmed; SQUASH_POLICY.md adopted; forgecode is `parent`, never squashed; consumed-repo squash path defined.

## NEXT STEP — AWAITING PHASE 1 ACK

Reply with one of:
- `G4 Phase 1+2`: shallow clone smoke + plugins to `/tmp/imports/` (read-only-ish; creates local dirs)
- `G4 all phases`: execute all 11 phases sequentially, pausing before each push and before each consumed-repo squash
- `hold`: pause here