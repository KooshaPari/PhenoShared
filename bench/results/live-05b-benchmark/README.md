# Live Benchmark: Qwen2.5-0.5B-Instruct-4bit (MLX)

**Date:** 2026-07-23  
**Model:** `mlx-community/Qwen2.5-0.5B-Instruct-4bit`  
**Framework:** MLX 0.31.2 / mlx-lm 0.31.2  
**Platform:** macOS aarch64 (Apple Silicon)  
**Precision:** 4-bit quantized  
**Method:** Direct `mlx_lm.generate()` (server had threading bug, see notes)

---

## Results

| Cell | Prompt | Latency | Tokens | tok/s | Response (truncated) |
|------|--------|---------|--------|-------|----------------------|
| 1 | What is 2+2? | 1959 ms | 30 | 15.3 | The answer is 4. 2+2 = 4... |
| 2 | Capital of France? | 878 ms | 30 | 34.2 | The capital of France is... |
| 3 | Write a Python hello world | 1363 ms | 30 | 22.0 | program that prints "Hello, World!"... |
| 4 | Explain recursion in one sentence | 1710 ms | 30 | 17.5 | Recursion is a method of solving problems... |
| 5 | What year was Python created? | 1572 ms | 30 | 19.1 | Python was first developed in 1980... |
| 6 | Convert 100 Celsius to Fahrenheit | 1407 ms | 30 | 21.3 | To convert 100 degrees Celsius... |
| 7 | Name 3 prime numbers | 1878 ms | 30 | 16.0 | three prime numbers... |
| 8 | What is a linked list? | 1051 ms | 30 | 28.5 | A linked list is a linear list... |
| 9 | Write a SQL SELECT statement | 1063 ms | 30 | 28.2 | to select the top 5 most popular books... |
| 10 | What does API stand for? | 1091 ms | 30 | 27.5 | API stands for Application Programming Interface... |

---

## Summary

| Metric | Value |
|--------|-------|
| Cells | 10 |
| Total tokens | 300 |
| Avg latency | 1397 ms |
| Avg throughput | 23.0 tok/s |
| Min latency | 878 ms (Cell 2) |
| Max latency | 1959 ms (Cell 1) |
| Min tok/s | 15.3 (Cell 1) |
| Max tok/s | 34.2 (Cell 2) |

---

## Notes

- **Server issue:** `mlx_lm.server` crashed with `RuntimeError: There is no Stream(gpu, 0) in current thread` on generation. This is a known threading bug in mlx-lm 0.31.x. The benchmark ran via direct `mlx_lm.generate()` instead.
- **Cell 1 was slowest:** First inference includes model warmup (prompt cache initialization). Subsequent cells were faster.
- **All prompts returned 30 tokens** (max_tokens cap) — responses were coherent and on-topic.
- Results saved to `results.json` in this directory.
