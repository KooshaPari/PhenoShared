# Known Issues

| Issue | Impact | Mitigation |
|---|---|---|
| Seven remote repositories have no refs | Cloud capture may be incomplete | Search local clones/worktrees before archive |
| AgilePlus canonical checkout contains runtime/build dirt | Unsafe integration surface | Use isolated worktrees only |
| OMLX `tmp/main` is not represented | One history line remains at risk | Import missing ref before archive proposal |
| `omniroute-rust` has 13 crates | Parent cannot be chosen per repository name | Run crate-level boundary audit |
| `thegent-sharecli` dedupe is incomplete | Possible unique behavior | Compare with `thegent-cli-share` and `sharecli` |
| phenoVessel head is not reachable in PhenoPlugins | Absorption claim is unproven | Preserve tag/release and prove parity |
| Cockpit bead ledger, renderer, and HTML are non-Git | Source history can drift without durable refs | Preserve time-stamped hashes; no move, `git init`, or replacement before boundary decision |
| Cockpit source bytes changed after the 06:53 snapshot | Snapshot hash must not be presented as live-current | Retain both observations and require atomic writer/renderer migration |
| `~/.agileplus/cockpit.ndjson` is stale | It can mislead operators into treating old scores as source data | Classify it as non-source historical telemetry |
| AgilePlus and Tracera roles are not cut over | Operational and consumer boundaries remain unproven | Keep AgilePlus successor and Tracera consumer status as blocked DAG gates |
