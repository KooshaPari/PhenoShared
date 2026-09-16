# Qwen Stock MLX vs Pheno Metal Comparison Matrix

## Scope and interpretation

- Pheno Metal is not an end-to-end Qwen comparator: the available real-weights decode runs RMSNorm only; attention, MLP, and projection kernels are not wired into that decode path.
- Rows are marked **not comparable** until both sides execute the same full Qwen workload.
- Component validation evidence below is retained for correctness and implementation tracking only.

## Methodology

- Workload: `full Qwen logits forward [batch, context] -> [batch, context, vocab]`
- Stock MLX source: `mlx_lm model forward in an isolated subprocess per variant`
- Batches: `[1, 8]`; context tokens: `[1, 128]`
- Timed iterations: `3`; warmups: `1`
- Weights: the supplied mlx_lm model; no synthetic-weight timings are used for stock-MLX rows
- Timing boundary: wall clock around evaluated forwards after warmup, followed by mx.synchronize()

## Full-workload matrix

| Batch | Context | Stock MLX | Pheno Metal | Comparison |
| ---: | ---: | --- | --- | --- |
| 1 | 1 | completed; 12.17 ms/fwd; 82.2 tok/s | unsupported | not comparable |
| 1 | 128 | completed; 154.85 ms/fwd; 826.6 tok/s | unsupported | not comparable |
| 8 | 1 | completed; 33.13 ms/fwd; 241.5 tok/s | unsupported | not comparable |
| 8 | 128 | completed; 2221.66 ms/fwd; 460.9 tok/s | unsupported | not comparable |

## Pheno component-validation evidence (not an end-to-end comparison)

- Report: `/Users/<REDACTED>/CodeProjects/Phenotype/pheno-harness-compare/kernels/qwen3.5-0.8b/bench/results/validate_latest.json` (loaded)
- Metal available when report was written: `True`

| Component | Passed | Metal available | MLX ms | Metal ms | Notes |
| --- | --- | --- | ---: | ---: | --- |
| RMSNorm | True | True | 0.7835197448730469 | 2.4540328979492188 | max_diff=6.250e-02 |
| RoPE | True | True | 0.7739639282226562 | 1.7619132995605469 | max_diff=1.562e-02 |
| SwiGLU | True | True | 0.33832550048828125 | 11.266794204711914 | max_diff=6.250e-02 |
| sigmoid_gate | True | True | 0.4125213623046875 | 3.4439563751220703 | max_diff=3.125e-02 |
| attention_decode | True | True | 0.7288742065429688 | 15.272760391235352 | max_diff=5.352e-01 |
| causal_conv1d_step | True | False | 0.33588409423828125 | None |  |
| linear_attn_step | True | False | 0.5774784088134766 | None |  |
| gemv_decode | True | False | 0.6364822387695312 | None |  |
| gemm_bf16 | True | False | 1.0187149047851562 | None |  |
| fused_argmax | True | True | 24.9721622467041 | 20.051393508911133 | max_diff=5830  ref_tok=235686 metal_tok=229856 |
| decode_step_batched | True | True | 0.006875000508443918 | 0.8760830005485332 | status=0 L=24 H=1024 (batched vs per-op) check=stub_mode_dispatch_only |
| end_to_end | True | False | -1.0 | None | subprocess rc=0 |
