Build Sweep 2026-05-04
Summary
- Passed: 13
- Failed: 3
- Skipped: 4
- Timed Out: 0

Detailed Results
| Repo | Tool | Status | Error Summary |
| --- | --- | --- | --- |
| AgilePlus | N/A | SKIP | No recognized build manifest |
| AgilePlus-wtrees | N/A | SKIP | No recognized build manifest |
| agileplus-agents | cargo check | PASS | - |
| heliosApp | npm run build | PASS | - |
| helios-cli | cargo check | PASS | - |
| helios-router | cargo check | PASS | - |
| BytePort | cargo check | PASS | - |
| thegent | npx vitest run | FAIL | npm error code EOVERRIDE<br>npm error Override for esbuild@^0.28.0 conflicts with direct dependency<br>npm error A complete log of this run can be found in: /Users/<REDACTED>/.npm/_logs/2026-05-05T07_47_50_499Z-debug-0.log |
| thegent-dispatch | cargo check | PASS | - |
| HexaKit | cargo check | PASS | - |
| phenoShared | cargo check | PASS | - |
| AuthKit | N/A | SKIP | No recognized build manifest |
| Tokn | cargo check | PASS | - |
| Sidekick | cargo check | PASS | - |
| GDK | cargo check | PASS | - |
| Parpoura | npx vitest run | FAIL |        \| ^<br>      4\|<br><br>⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[3/3]⎯<br> |
| Configra | cargo check | PASS | - |
| HeliosLab | cargo check | PASS | - |
| PhenoDevOps | cargo check | FAIL |    \|                no `blake3_hash` in `hash`<br><br>Some errors have detailed explanations: E0432, E0583.<br>For more information about an error, try `rustc --explain E0432`.<br>error: could not compile `phenodevops` (lib) due to 4 previous errors |
| kitty-specs | N/A | SKIP | No recognized build manifest |
