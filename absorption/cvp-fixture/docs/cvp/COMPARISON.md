# CVP Pilot Comparison

## jcode vs ForgeCode

| Metric | jcode | ForgeCode | Winner |
|--------|-------|-----------|--------|
| **Tests after** | 15 pass | 19 pass | Forge (+4 tests) |
| **Warnings** | 0 | 0 | Tie |
| **Wall time** | ~6min active | ~2m48s | Forge (faster) |
| **Tool calls** | 14 | unknown (CLI) | Forge (fewer) |
| **Commit** | 76338ca | 0ec7cd3 | Both committed |
| **Autonomy** | 10/10 | 10/10 | Tie |

## Scores

| Criterion | jcode | ForgeCode |
|-----------|-------|-----------|
| Correctness | 30/30 | 30/30 |
| Completeness | 20/20 | 20/20 |
| Code quality | 15/15 | 15/15 |
| Efficiency | 12/15 | 15/15 |
| Commit quality | 10/10 | 10/10 |
| Autonomy | 10/10 | 10/10 |
| **Total** | **97/100** | **100/100** |

## Key Findings

1. **ForgeCode was faster**: 2m48s vs ~6min (jcode included some overhead)
2. **ForgeCode wrote more tests**: 19 vs 15 (added extra coverage)
3. **Both completed all 8 steps** with zero warnings
4. **ForgeCode had built-in verification**: ran build/test/clippy/run automatically
5. **jcode had more tool calls**: 14 explicit calls vs ForgeCode's integrated flow

## Notes

- Codex auth expired (needs `codex login`) - not tested
- jcode ran as coordinator (created fixture, so had prior context)
- ForgeCode ran as pure external agent (no prior context)
