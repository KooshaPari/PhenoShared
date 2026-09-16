# Research

## Verified repository paths

- `scripts/start_dual_gpu_stack.ps1` is the dual-runtime launcher.
- `scripts/run_perf_suite.py` is the honest OpenAI-compatible real endpoint
  harness; it requires model alias `local/qwen35-08b`.
- `scripts/validate_desktop_evidence.py` validates the evidence envelope,
  contract hash, source commit, run metadata, and exact gate set.

## Verified desktop facts

- Host: `KOOSHAPARI-DESK`, Windows + WSL2 FedoraLinux-44.
- GTX 1080 Ti is the helper; RTX 3090 Ti is the primary.
- vLLM uses `CUDA_VISIBLE_DEVICES=1` and logical `cuda:0` for the 3090.
- Windows llama.cpp uses `CUDA_VISIBLE_DEVICES=1` and logical `CUDA0` for the
  1080 under the captured reversed enumeration.
- User-owned LFM2.5 vLLM remains on port `19000`; it must not be stopped or
  used as Qwen3.5 evidence.
