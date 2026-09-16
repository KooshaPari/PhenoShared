---
source_file: ChatGPT-Software Project Traceability Tools.md
sha256: 3fd6a6eff105da8efda33fa5c3f20b8f2c2e0b5942315dbc1d3fbf48f7f83725
topics: [agents, traceability, evidence-registry, spec-links, audit]
related_okf:
  - agents/coding-agents-intent-graphs.md
  - agents/feature-graph-system-design.md
evidence_class: L
status: stub — N10 priority, needs full distillation
---

# Software Project Traceability Tools

**Source:** `ChatGPT-Software Project Traceability Tools.md` (41 KB, 2026-06-14) — class **L**.

Traceability is the ability to walk **intent → spec → code → test → eval → evidence** without manual grep. The corpus surveys tools that bind claims to artifacts via **evidence classes** (L=local corpus, P=primary source) and hash-only registries — exactly the `config/evidence_registry.yaml` + `local_corpus` pattern in pheno-harness (`pheno/evidence/adapters/local_corpus.py`, `corpus_manifest.json`).

## Key insights (stub — full distillation pending N10)

- **Hash-only store:** never persist raw corpus paths in git; cite `local://sha256/<digest>` so evidence survives moves/renames — implemented in `evidence_registry.yaml`.
- **Claim tagging:** every OKF page marks claims `[L]` until primary-source confirmation promotes to `[P]`; unverified ChatGPT assertions stay **L**.
- **Spec-ADR link:** traceability enables "hidden claims → ADR" (Forward DAG N17) — pick 3 highest-leverage `[L]` claims lacking an ADR and spec them (`docs/adr/ADR-ECO-xxx.md`).
- **Tooling:** `scripts/evidence_registry.py plan --sources local_corpus` re-scans `D:/koosh/Downloads/ChatGPT-*.md` and updates `corpus_manifest.json` mtimes/sha256.
- **Pheno-harness links:** `docs/okf/INDEX.md` taxonomy, `plans/2026-07-14-usch-heterogeneous-inference-v1/EVALUATOR_CONTRACT.md`, `config/heterogeneous_tournament.yaml` (corpus forbidden on mobile workers).

## Next (N10)

- Extract full `[L]` claims with `local://sha256/3fd6a6eff...` citations into `docs/okf/agents/software-project-traceability.claims.md`.
- Cross-link to `evidence-links.md` per category (verification loop).
- After 10 N10 pages land, pick 3 for N17 ADR synthesis (with `synthesis/03-moe` / `06-hardware`).

**Evidence:** `local://sha256/3fd6a6eff105da8efda33fa5c3f20b8f2c2e0b5942315dbc1d3fbf48f7f83725` (class **L**).
