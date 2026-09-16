# Known issues

## Evidence status

Host availability and helper-run details below are historical observations, not
current promotion evidence. The canonical lane remains `planning_only`, and the
canonical evidence validator is valid but blocked at 5/7 promotion gates. No
desktop launch or evaluation is authorized from these observations alone.

- Tailscale/OpenSSH routing recovered during this session. The active SSH
  tunnel reaches a Qwen3.5 Pascal helper on WSL port `19001` through local
  `127.0.0.1:19002`.
- The user-owned LFM2.5 vLLM process occupies port `19000` on the 3090.
- The Pascal helper rejects `stream=true`; its earlier streaming artifact is
  retained as a failed diagnostic and is not evidence.
- A non-streaming harness evaluation now passes (warmup 0 errors, 3/3
  requests successful), with total-latency measurement explicitly labeled as
  a proxy. WSL `nvidia-smi` lists helper PIDs under both UUIDs, but both
  supervisors report `CUDA_VISIBLE_DEVICES=0` and memory deltas isolate the
  load to the GTX 1080 Ti; per-process UUID attribution is a WSL caveat.
- A second non-destructive helper on port `19002` used the same explicit
  mapping and produced another 3/3 harness pass. Its host resource sampler
  had zero samples because macOS `psutil` raised `host_statistics64`.
- Primary repeatability remains deferred because the user-owned LFM2.5
  process occupies port `19000`.
- The desktop is currently reachable again. Read-only endpoint probes found
  Qwen3.5 on Windows llama.cpp `127.0.0.1:8080` and the WSL Pascal helper on
  `127.0.0.1:19001`; the 3090-owned Windows endpoint remains LFM2.5 on
  `127.0.0.1:8081`, so this does not satisfy primary Qwen3.5 evidence.
- A fresh read-only `nvidia-smi` probe reports roughly 441 MiB free on the
  GTX 1080 Ti and 2.4 GiB free on the RTX 3090 Ti. The launcher now requires
  4096 MiB free on both physical devices before attempting either worker,
  preventing a launch from contending with active user-owned workloads.
- The direct stack launcher is reserved and authority-blocked before it can
  use a caller-supplied window, start a process, or contact an endpoint. A
  future owner-issued authority must bind the window, contract digest,
  preflight digest, runtime/endpoint, issuance, and expiry.
- A standalone `scripts/run_desktop_agentic_fixture.py` provides an
  OpenAI-compatible single-tool envelope shape (`get_runtime_status`) and is
  dry-run by default. Under the current policy it rejects execution before an
  endpoint probe; a window alone is never authorization. It remains neither
  Harbor task-success evidence nor promotion evidence until an authorized
  Terminal-Bench run is captured.
- At the latest desktop probe, `nvidia-smi -L` exposed only the RTX 3090 Ti;
  the GTX 1080 Ti was absent and ports `8000`, `8080`, `8081`, `8082`, `19000`,
  and `19001` did not return model metadata. The dual-GPU lane therefore fails
  closed until the helper device and both authorized endpoints are restored.
- Current evidence is valid but promotion status is intentionally `blocked`.
- The Harbor runner is reserved and authority-blocked before it can write a
  sidecar, contact an endpoint, inspect Docker, or invoke Harbor. It must stay
  blocked until an owner-issued authority contract and verifier are approved;
  it no longer self-issues a sidecar from a caller-supplied window.
