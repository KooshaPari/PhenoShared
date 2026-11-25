# Pheno Stack Layer Contract

This document pins the owned-fork names and runtime boundaries for the
ForgeCode/OmniRoute/Pheno stack.

## Layer Order

From agent UI outward to raw inference inward:

1. `forge-dev`
   - Owned ForgeCode fork and CLI/bin identity.
   - Runs the coding agent, tool loop, shell/file edits, and benchmark agents.
   - Should talk to `omniroute-dev` by default through an OpenAI-compatible API.
   - May call a lower layer directly only for controlled eval cells where router
     behavior would hide the thing being measured.

2. `omniroute-dev`
   - Owned OmniRoute fork and outer router identity.
   - Presents the stable OpenAI-compatible endpoint used by Forge, Harbor, Codex,
     Claude-code adapters, and eval drivers.
   - Owns provider blending, quota routing, direct-provider fallback, subscription
     lane policy, and request-level accounting.
   - Does not own low-level serving-engine lifecycle.

3. `PhenoLM`
   - LLM policy, eval, trace, reward, and self-improvement layer.
   - Replaces the old `pheno-specs` split as the living spec/control plane.
   - Owns model/lane policy, trace-derived evalsets, RLVR-AF scoring, promotion
     gates, and benchmark reports.
   - Lives in this repo unless intentionally extracted later.

4. `pheno-serve-dev`
   - Missing inner inference/router/server layer to create.
   - Owns local serving engines and their OpenAI-compatible endpoints:
     SGLang, vLLM, TensorRT-LLM, llama.cpp, MLX, and future CUDA/kernel paths.
   - Reports TTFT, ITL, tokens/sec, queue wait, KV/prefix cache hit rate, VRAM,
     CPU/RAM/disk/network, engine errors, and crash/restart events.
   - Is below OmniRoute and above concrete engine processes.

5. Engine layer
   - Concrete runtimes: SGLang, vLLM, TensorRT-LLM, llama.cpp, MLX.
   - This layer is benchmarked and profiled, not used as the policy source.

6. `bifrost`
   - Inner model/runtime substrate when present.
   - Treated as a backend capability below `pheno-serve-dev`, not as the
     external router.

## Default Call Path

```text
forge-dev / Harbor / Codex eval
  -> omniroute-dev OpenAI-compatible endpoint
  -> PhenoLM policy and eval hooks
  -> pheno-serve-dev local engine endpoint or remote provider endpoint
  -> SGLang/vLLM/TensorRT-LLM/llama.cpp/MLX/Bifrost
```

## Direct-Call Exceptions

Direct calls are allowed only when the eval cell is explicitly measuring the
lower layer:

- `forge-dev -> pheno-serve-dev` for serving-engine parity and harness-overhead
  isolation.
- `PhenoLM -> provider` for direct OpenRouter/Ling baseline cells.
- `PhenoLM -> engine` for cache/speculative-decoding experiments where
  OmniRoute grouping would confound the measurement.

Every direct-call eval must log:

- reason
- bypassed layer
- model id
- engine id
- route id
- commit hash
- hardware profile
- secret source name, never secret value

## Naming Rules

- `*-dev` names are the owned fork/bin/path identities even when a local folder
  currently uses another name.
- Docs and configs should refer to `forge-dev` and `omniroute-dev` for future
  work, while compatibility scripts may keep existing paths until renamed.
- `PhenoLM` is the preferred name for the old `pheno-specs` concept.
- Do not delete or detach the `agileplus-specs` submodule until its remote
  content is fetched and imported or explicitly archived.
