---
source_file: ChatGPT-GPU Rentals Safety Review.md
sha256: db67d55b180a30d4283f7fe3e040c2fe3bea4afa933d0a15359deb1ed292ab4e
topics: [hardware, gpu-rentals, safety, deployment, vast-ai]
related_okf:
  - hardware/machine-comparison-for-ai.md
  - hardware/model-improvements-under-500.md
  - docs/adr/ADR-008-Multi-Platform-Deployment.md
evidence_class: L
status: stub — N10 in-order
---

# GPU Rentals Safety Review

**Source:** `ChatGPT-GPU Rentals Safety Review.md` (43 KB) — class **L**.

GPU rentals (Vast.ai, RunPod) reviewed on **safety + cost + data-exfiltration** — the corpus flags `host.containers.internal:9102` scrape exposure, vault `LANGFUSE_*` vs `.env` leakage, and `podman :7777` blast radius. The review is the same `infra/circuitbreaker` + `config/secrets` + `risky_action_gate.yaml` gate that `pheno-harness` uses for `start_dual_gpu_stack.ps1`.

## Key insight

- Rentals win on `$` but lose on **traceability** — `evidence/dual_gpu/host_manifest.yaml` 7-day tail + `platform/federation/out/cells-*.json` ignored pattern is safety, not cost, and is `R6` `canonicalize.py` + `harbor_result_to_cells.py` before `seed_langfuse`.

**Evidence:** `local://sha256/db67d55b180a30d4283f7fe3e040c2fe3bea4afa933d0a15359deb1ed292ab4e`
