# Hardware-Aware Placement

The host is heterogeneous: an RTX 3090 Ti (24,564 MiB, SM 8.6) and a GTX
1080 Ti (11,264 MiB, SM 6.1), with 64 GiB DDR4 and D: NVMe storage. The cards
are not interchangeable, and a nominal two-GPU configuration is not evidence
that tensor parallelism is beneficial.

## Default topology

Use independent queues. The 3090 Ti owns latency-sensitive managers, coding
agents, long-context requests, and high-batch work. The 1080 Ti is a helper
candidate for short drafts, routing, classifiers, and low-concurrency workers.
The router and tokenizer remain CPU work. DDR4 and NVMe are cold staging and
spill tiers, never an unconditional per-token path.

Pascal stays outside the CUDA 13, TensorRT-LLM, SGLang, and vLLM baseline. It
has now passed an isolated CUDA 12.4 llama.cpp probe using the explicit
llama.cpp device name `CUDA1`. The 3090 Ti is `CUDA0` in that binary; these
llama.cpp device names are distinct from the Windows `nvidia-smi` indices.
Mixed-GPU tensor parallelism is
blocked until PCIe transfer, synchronization, and quality/latency measurements
show a benefit over independent workers.

## Required measurements

Every placement trial records TTFT, decode rate, p95 latency, queue wait,
quality, peak VRAM, host RAM, GPU utilization, power, and completed tasks per
joule. Compare short-draft, routine-agent, long-context, and mixed-role traces.
The placement policy is in `config/hardware_aware_placement.yaml`.
