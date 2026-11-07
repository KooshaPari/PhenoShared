# ResearchLedger in PhenoShared

**Migration state:** historical research recovered on a draft branch; not yet the completed, running ResearchLedger product.

ResearchLedger is the logical local-first provenance, retrieval, source, and claims product. This directory currently contains a **verified historical Wave 5 research fallback**, not the full latest corpus or the Tauri application.

## Start here

- [Recovery and ownership gates](2026-10-12-recovery-and-boundaries.md) — exact lineage constraints, authorization, missing source, and pass/fail requirements.
- [Historical campaign overview](historical-wave5/docs/corpora/emergent-garden/README.md) — original research intent and document graph.
- [Wave 5 source review](historical-wave5/docs/corpora/emergent-garden/research/WAVE-5-SOURCE-REVIEW.md) — directly reviewed methods including OMNI-EPIC.
- [Wave 5 lineage](historical-wave5/docs/corpora/emergent-garden/research/WAVE-5-LINEAGE-AND-TRANSFER.md) — distinct repo identities, Git ancestry, and limited negative findings.
- [Wave 3 comments and corrections](historical-wave5/docs/corpora/emergent-garden/research/WAVE-3-COMMENTS-AND-SYNTHESIS.md) — interpretive findings from historical commenter evidence; not live current comment counts.
- [Evidence admission and bounded tests](historical-wave5/scripts/research/assess_research_evidence.py) — machine-checking script, not proof that papers or agents were reproduced.
- [Preservation manifest](historical-wave5/PRESERVATION-MANIFEST.json) — all 47 retained files with original hashes.

## Scope and source integrity

The 47 files were restored byte-for-byte from a verified Wave 5 handoff. These files intentionally remain nested under `historical-wave5/`: their older relative references and repository assumptions need semantic review before promoting to canonical live paths. **Do not run historical collectors against current credentials as if their stored September 5 data are fresh.**

The later September 9 source revision `8822aa14baef2a964288076645edcc493c338688` is referenced by older coordination documents but not currently accessible through the original or successor GitHub repositories. Recover from a verified Git object, local worktree, bundle or backup before overriding any of these files.

The private full-comment archive's historical CMS inputs are not a public corpus. A public-comment API count, a third-party transcript mirror, model-generated video analysis and creator-authorized exact captions are **different evidence classes**.

## Components and source of truth

- **PhenoShared:** designated shared provenance/research engine and historical research migration destination, pending owner-reviewed implementation.
- **PhenoApps:** separate imported desktop shell under [PR #166](https://github.com/KooshaPari/PhenoApps/pull/166); open and unmerged as last checked.
- **Private local vault:** raw and restricted source materials and credentials. Never copy these into public Git.
- **Tracera:** downstream trace/evidence projection, not a second research corpus.
- **PhenoRegistry/AgilePlus:** fleet boundary and work tracking; feature ID 3 is CLI-verified `specified`, but full MCP/governance acceptance remains unverified.
- **Benchora successor:** current experiment ownership unresolved. The finite-state reference does not prove optimal real multi-agent topology.

## Execution gates

[Hosted offline historical validation](https://github.com/KooshaPari/PhenoShared/actions/runs/38469882345) passed 70 research tests and the runnable recovery tests; it did not exercise current YouTube credentials or a deployed application.

The [manual census workflow](../../.github/workflows/researchledger-youtube-census-manual.yml) is designed to be available from a reviewed default-branch revision. A successful current API refresh still requires a destination-scoped `YOUTUBE_API_KEY`, a completed check, an explicit retention plan, and current data reconciliation. No live refresh has been verified from this PhenoShared recovery PR.

Full completion further requires recovery/disposition of later work, PhenoApps/PhenoShared integration and UI/run tests, actual agent experiment, resolved fleet projections, relevant CI review, and deliberate merges/releases. Absence of evidence is **not** a pass.
