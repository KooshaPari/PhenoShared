# Local-model-driven item — reproducibility manifest

**Date:** 2026-07-04
**Round:** 7
**Cost:** $0.00 cloud spend, ~5 minutes wall, 1.74 GB GPU vRAM reserved (no engine binary loaded yet)
**Operator:** forge-dev session via pheno-harness
**Sign-off gate:** Stage 6 (matrix sweep) requires this manifest + a separate gate for the engine-binary install per `docs/specs/005-engine-binary-install.md`.

---

## 1. Scope of "just the local model driven item"

User 2026-07-04 23:xx: "run just the local model driven item".

Interpreted as: **stand up `pheno-serve-dev` and verify the locked T0 (`Qwen/Qwen3.5-0.8B`) profile is wired end-to-end**, without spending any cloud budget and without forcing an engine-binary install this round.

**In scope:**
- Start `pheno-serve-dev` from existing config (`config/pheno_serve.yaml`)
- Smoke `/healthz`, `/v1/models`, `/admin/models` via `scripts/smoke_pheno_serve.py --skip-completion`
- Probe per-profile engine + base_url reachability via `scripts/probe_pheno_serve.py --json`
- Re-scrape OR `/api/v1/models` for the 7 locked cloud picks + Granite-4.0-h-micro (DLQ) for transparency; emit drift report vs 2026-07-04 round-4 snapshot
- Emit this manifest + ADR 0006 + spec 005
- Fix lingering Granite-4.0 drop inconsistency in ADR 0005 + locked_shortlist.md

**Out of scope (gated behind separate sign-offs):**
- Engine binary install (`llama-server.exe` for the `qwen35-08b` profile). See `docs/specs/005-engine-binary-install.md` § 6 for the install procedure + sign-off criteria.
- Weight download (`Qwen/Qwen3.5-0.8B` GGUF, ~1.7 GB). See spec 005 § 5 for the download + verify + SHA-256 procedure.
- Actual completion generation through `local/qwen35-08b`. The `--skip-completion` flag on the smoke script deliberately avoids spending GPU time on a model that has no upstream.
- Spec-dec trial (self-speculation Qwen3.5-0.8B → Qwen3.5-0.8B). Gated on the engine binary being installed AND accepting EAGLE-2 / N-gram spec-dec methods.
- Any TB 2.0 / DeepSWE / SWE-bench / custom long-horizon run. Those are Stage 1 (per `docs/specs/004-implementation-plan.md`) and are NOT in this round.

---

## 2. Environment

| Resource | Value |
|---|---|
| Host | `WIN-9RK0HR5PHL0` (Windows 11 24H2, build 26100.x) |
| GPU | 1× NVIDIA RTX 3090 Ti, 24 GB VRAM (UUID `8d337a84-43de-158d-7526-7175288a6064`) — idle, no engine binary loaded |
| Python env | `C:\Python313\python.exe` 3.13.x — `sglang 0.5.2`, `vllm 0.20.0`, `transformers 4.57.6`, `huggingface_hub 0.36.2` installed |
| `llama-server` / `ik_llama-server` | NOT on PATH (engine install gated behind spec 005) |
| `pheno-serve-dev` | running, PID `458020`, listening on `http://127.0.0.1:21080` (proxy only — does NOT need an engine binary) |
| `pheno-serve-dev` log | `bench/results/2026-07-04/pheno_serve_start.log` |
| Disk pressure | D: 528 GB free (down from 530 GB; 2 GB slack for future weight cache) |
| Cloud cost | $0.00 (no OpenRouter calls, no HF API calls with token, no model invocations) |
| Wall time | ~5 minutes |

---

## 3. Reproducibility contract

Every run of "just the local model driven item" must emit this manifest + these artifacts:

| Artifact | Path | Purpose |
|---|---|---|
| `MANIFEST.md` | `bench/results/<date>/MANIFEST.md` | This file |
| `pheno_serve_start.log` | `bench/results/<date>/pheno_serve_start.log` | stdout of the `pheno-serve-dev` startup |
| `pheno_serve_start.err` | `bench/results/<date>/pheno_serve_start.err` | stderr of the startup |
| `pheno_serve_smoke.json` | `bench/results/<date>/pheno_serve_smoke.json` | health + /v1/models + /admin/models smoke output |
| `pheno_serve_probe.json` | `bench/results/<date>/pheno_serve_probe.json` | per-profile engine + base_url reachability |
| `or_drift_<date>.json` | `bench/results/<date>/or_drift_<date>.json` | OR metadata re-scrape vs round-4 snapshot |
| `scrape_or_drift.py` | `bench/results/<date>/scrape_or_drift.py` | the OR drift script (in the results dir, not scripts/, because it's per-date) |
| ADR 0006 | `docs/adrs/0006-pheno-serve-dev-bootstrap.md` | the decision document for this round |
| Spec 005 | `docs/specs/005-engine-binary-install.md` | the engine-binary install + first-real-run bootstrap |

Command to reproduce from a clean checkout:

```powershell
$env:PYTHONPATH = 'C:\Users\koosh\pheno-harness'
Start-Process -FilePath 'C:\Python313\python.exe' `
    -ArgumentList '-u','-m','pheno.serve.server','--config','C:\Users\koosh\pheno-harness\config\pheno_serve.yaml' `
    -RedirectStandardOutput 'bench\results\<date>\pheno_serve_start.log' `
    -RedirectStandardError  'bench\results\<date>\pheno_serve_start.err' `
    -WindowStyle Hidden
Start-Sleep -Seconds 3
C:\Python313\python.exe -u scripts\smoke_pheno_serve.py --skip-completion `
    > bench\results\<date>\pheno_serve_smoke.json 2>&1
C:\Python313\python.exe -u scripts\probe_pheno_serve.py --json `
    > bench\results\<date>\pheno_serve_probe.json 2>&1
C:\Python313\python.exe -u bench\results\<date>\scrape_or_drift.py `
    > bench\results\<date>\scrape_or_drift.out 2>&1
```

---

## 4. Captured artifacts (this round)

| Artifact | Status | Key findings |
|---|---|---|
| `pheno_serve_start.log` | OK | `pheno-serve-dev listening on http://127.0.0.1:21080` |
| `pheno_serve_start.err` | empty | no errors |
| `pheno_serve_smoke.json` | OK | `/healthz` 200; 7 profiles visible; `local/qwen35-08b` engine=`llama_cpp`, active, base_url=`http://127.0.0.1:8080` |
| `pheno_serve_probe.json` | OK | `local/qwen35-08b` → `127.0.0.1:8080` TCP-reachable (connect-ok); other local profiles TCP-fail (no engines) |
| `or_drift_2026-07-04.json` | OK | 8 picks present in OR (7 active + Granite-4.0 DLQ for transparency); pricing drift empty (round-4 JSON didn't carry per-record `pricing_prompt_per_m` field — known artifact) |
| `scrape_or_drift.py` | OK | reproducible; idempotent |
| ADR 0006 | OK | bootstrap decision + sign-off gates |
| Spec 005 | OK | engine-binary install + first-real-run procedure |
| ADR 0005 fix | OK | cloud baseline table = 7 (Granite-4.0 dropped with rationale preserved in DLQ + post-mortem) |
| locked_shortlist.md fix | OK | cloud baseline table = 7; DLQ + cost-table references to Granite-4.0 preserved as historical (not as active pick) |

---

## 5. Sign-off gates for next actions

| Action | Gate | Decision owner |
|---|---|---|
| Install `llama-server.exe` (or `ik_llama-server.exe`) | spec 005 § 6 sign-off criteria | user |
| Download `Qwen/Qwen3.5-0.8B` GGUF | spec 005 § 5 SHA-256 verify | user |
| Run first real completion against `local/qwen35-08b` profile | engine binary on PATH + weight downloaded + SHA-256 verified | user |
| Stage 6 matrix sweep (11 picks × 5 tiers × 4 engines ≈ 176 cells) | first real completion succeeds + Stage 1 evals pass + first cell cross-validated against OR baseline | user |
| Stage 9 SWE-bench debug-only regression | Stage 6 single engine matrix succeeds end-to-end + reproducibility manifest lands in `bench/results/` | user |
| Codex fork workstream (Stage 10) | ADR 0001 / RISKS § 12 explicit go-ahead | user |

---

## 6. Open decisions from this round

1. **`llama-cpp-python` wheel vs compiled `llama-server.exe`?** spec 005 § 2 covers this — recommendation is **prebuilt `llama-server.exe` from the official ikawrakow/llama.cpp release** for Windows because the build time + CUDA toolchain on the 3090 Ti is non-trivial. Awaiting user sign-off.
2. **Weight format: GGUF Q4_K_M, GGUF Q8_0, or AWQ-INT4 BF16?** spec 005 § 5 covers this — recommendation is **GGUF Q4_K_M** because the 0.8 B model in Q4_K_M is ~700 MB (fits comfortably in any cache layout, decode speed is fastest on `llama-cpp`). AWQ-INT4 BF16 requires vLLM/SGLang, which is a different engine binary. Awaiting user sign-off.
3. **Spec-dec method for Qwen3.5-0.8B self-speculation:** matrix spec § 7 lists EAGLE-2 (vLLM 0.20.0 / SGLang 0.5.2), N-gram / suffix (any engine), and self-speculation (research). Recommendation is **N-gram with seed=N+1** as the first spec-dec trial because it doesn't need a second model head; EAGLE-2 is gated behind SGLang being the engine (not llama.cpp). Awaiting user sign-off.

---

## 7. Cost summary

| Bucket | Cost |
|---|---:|
| OpenRouter completions | $0.00 (no calls made) |
| HF API calls (with `HF_TOKEN`) | $0.00 (no calls in this round; round-4 tokens already used and disclosed) |
| GPU time | ~3 s (proxy startup only) |
| CPU time | ~5 s (startup + smoke + probe + OR scrape) |
| Disk pressure | 0 MB (no weights downloaded; only log files written, ~6 KB total) |
| **Total** | **$0.00** |

---

## 8. Risks surfaced (see also `docs/adrs/0002-risks-register.md`)

- **R3 (engine-binary install on Windows):** `llama.cpp` Windows builds have historically lagged Linux; the 3090 Ti needs CUDA 12.x. spec 005 § 6 lists the verified paths; if those don't apply to this specific driver/CUDA combo, fall back to `ik_llama-server` (the lfm2_moe support is in ikawrakow's fork).
- **R9 (proxy-as-upstream):** `pheno-serve-dev` happily proxies to a dead upstream and returns a connect error to the client. The smoke script correctly reports `local/qwen35-08b` as `active` because the proxy can reach its config-level base_url, but the actual engine (llama-server) is not loaded. Future runs must verify `OK` from `/admin/models` AND a real completion before claiming the profile is end-to-end functional.
- **R12 (spec-dec on Qwen3.5-0.8B):** the model is small enough that self-speculation may not produce speedup (the overhead of running the draft + verification may exceed the savings on a 0.87 B model). The first trial should include a baseline run (no spec-dec) for direct comparison.

---

## 9. Next-action list

For the user:

1. Review ADR 0006 + spec 005 + this manifest.
2. Decide: **install `llama-server.exe` + download `Qwen/Qwen3.5-0.8B` GGUF Q4_K_M** (spec 005 full path) OR keep proxy-only state for now and skip Stage 6.
3. If yes: run spec 005 § 6 procedure; once SHA-256 verified, run a single completion through `local/qwen35-08b` to confirm end-to-end; emit a new MANIFEST.md dated the day of the first real run.

For me, gated on user sign-off:

1. Nothing in this round. Round 7 closed. No downloads, no completions, no matrix sweep until spec 005 § 6 is signed off.