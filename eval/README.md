# Pheno RLVR Eval Suite

End-to-end evaluation for harness × modelNet experiments on **3090 Ti only**.

## Pillars

| Pillar | Metrics |
|--------|---------|
| **Token burn** | input/output/cache, duplicate context, compiler savings |
| **Accuracy** | verifier pass, Harbor TB success, patch/test rates |
| **Speed** | p50/p95 latency, tok/s, accepted steps/sec |
| **Cost** | $/accepted step, monthly spend vs $200 ideal / $400 max |
| **Motion** | forward / stagnate / regress + ROI per token |
| **Quality** | escalation correctness, compiler reduction, DPO fidelity |
| **Safety** | risky-action gate pass rate, bypass attempts |

Config: `config/eval_pillars.yaml`, `config/budget_targets.yaml`

## Quick start

```powershell
cd C:\Users\koosh\pheno-harness
pip install -r requirements.txt

# Full suite: collect traces → wastage → pillars → budget
python scripts/run_eval_suite.py --small-grid

# Individual steps
python scripts/collect_traces.py
python scripts/analyze_wastage.py
python scripts/run_playground.py --small-grid --verify
```

## Harbor + Terminal Bench

Harbor **0.6.1** installed. TB **2.1** not in registry yet — use **`terminal-bench@2.0`** (89 tasks).

```powershell
.\harbor\run_tbench_local.ps1          # oracle sanity (1 task)
.\harbor\run_tbench_local.ps1 -Full   # full dataset (slow)
```

See `eval/HARBOR.md` for Docker troubleshooting.

## RLVR Playground

Combinatorial matrix: harness × modelNet × routing × decode × train_mode.

```powershell
python scripts/run_playground.py --small-grid     # 2×2 smoke
python scripts/run_playground.py --count-only       # 1440 filtered experiments
```

Training modes (3090 Ti): `qlora_role`, `lora_repair`, `sft_traces`, `pretrain_sub1b`  
Decode experiments: `speculative_06b`, `dflash_qwen4b`, `dflash_granite8`, `eagle3_baseline`, plus stubs (`dflash_stub`, `bitnet_stub`, `ternary_stub`, `double_speculative_stub`, `diffusion_dllm_stub`)

Full decode matrix: `config/decode_acceleration_matrix.yaml` — DFlash, SSD, diffusion dLLM research, PolyKV, LatentMAS cross-links.

```powershell
python scripts/decode_prepare.py list
python scripts/decode_prepare.py check --target codescout-4b --method dflash
```

## Trace sources (5+)

1. OmniRoute SQLite
2. Forge (`~/forge/.forge_history`)
3. Codex / agent-runner jobs
4. Claude Code sessions
5. Cursor agent transcripts + Factory Droid

Mac sync via Tailscale: `scripts/sync_traces_tailscale.ps1`

## Budget targets

- Baseline: **$570/mo** → ideal **<$200**, max **<$400**
- Codex cut: 50% bill = 4× usage efficiency
- Sunset: MiniMax + Firepass Kimi only for paid cloud routine

Results: `eval/results/wastage_latest.json`, `budget_latest.json`
