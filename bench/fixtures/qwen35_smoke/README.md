# 16-task Harbor-compatible smoke fixture for Qwen3.5-0.8B

This fixture is designed to exercise the local model end-to-end through `pheno-serve-dev` without paying the cost of TB 2.0 / DeepSWE. It is intentionally tiny (~16 tasks, 1 KB JSONL) so a full sweep costs < 60 s on SGLang + < 60 s on vLLM.

## Tasks

The fixture file is `tasks.jsonl` (one JSON object per line). Each task has:

| Field | Description |
|---|---|
| `task_id` | Stable unique id; `smoke-NNN` |
| `kind` | One of `sanity_check`, `json_shape`, `code_read`, `tool_call`, `reasoning`, `multi_turn`, `code_write`, `spec_dec_target`, `n_gram_target`, `mtp_target`, `eagle_target` |
| `prompt` | The prompt fed to the model via `/v1/chat/completions` |
| `expected` | A substring that must appear in the response (for `assert` mode) or a structural cue (for streaming-mode) |
| `max_tokens` | Hard cap on output length (kept small for fast smoke) |
| `temperature` | All tasks are `0` for determinism |

## Why these 16 tasks

The fixture covers the surface area that a real Harbor task hits, but in < 1 KB:

- **Sanity checks (3):** verify the model can produce a literal expected string — basic engine alive
- **JSON shape (1):** verify the engine emits valid JSON when asked
- **Code read (3):** verify the model can read repo files (the primary Harbor task mode)
- **Tool-call-ish (1):** verify the model can produce a structured enumeration
- **Reasoning (2):** basic math + latency math
- **Multi-turn (1):** verify conversation history works
- **Code write (1):** verify the model can produce a code one-liner
- **Spec-dec target (4):** four kinds of spec-dec-targetable prompts (free-form, n-gram continuation, list-generation, acronym) — these are the ones used in round 9's spec-dec trial design

## What it does NOT do

- Does not test tool calling (Harbor's primary mode). That's a deeper fixture for a later round.
- Does not test long context. Qwen3.5-0.8B supports long context but this fixture stays short.
- Does not test code execution or Docker sandboxing. Those are Harbor-side.

## How to run

```bash
set PYTHONPATH=C:\Users\koosh\pheno-harness
C:\Python313\python.exe -u scripts\perf_probe.py ^
    --base-url http://127.0.0.1:21080 ^
    --model local/qwen35-08b ^
    --fixture bench/fixtures/qwen35_smoke/tasks.jsonl ^
    --output bench/results/2026-07-04/local_qwen35_08b_probe/sglang_batch1.json
```

Repeat with `--batch-size 4` for the batch-4 probe, and with `--engine vllm` (or the vllm-mirror profile) for the cross-check.

## Reproducibility contract

Every run must emit:

- `sglang_batch1.json` — TTFT + tokens/sec per task (5 fields each)
- `sglang_batch4.json` — same at batch=4
- `vllm_batch1.json` — cross-check
- `vllm_batch4.json` — cross-check
- `summary.json` — aggregate stats per engine × batch
- `spec_dec_eagle.json`, `spec_dec_mtp.json`, `spec_dec_ngram.json` — spec-dec trial outputs