# Live Discord qualification evidence

Exact PhenoShared source a8b41cae73f07d5aa4737d29411f285fd358f1b4; remote Linux native CLI, no MCP/tray. One synthetic item only. See assessment-receipt.json for selected predicates, limits and unknowns. qualification-summary.json points to preserved archived/locked live thread. native-commands.json contains actual sanitized native CLI arguments/results. state-*.json are actual Discord REST GET responses for that canary, with signed CDN query strings removed. artifact-manifest.json records original remote and published hashes. Native credentials were never copied.

focused/Cargo.toml resolves inherited dependency declarations to an isolated build manifest pointing at exact archived source; focused/Cargo.lock records actual fresh compatible resolution. This is not root-workspace lock parity or a full default-feature build. build.log retains real build output.

Initial CDN download with default Python User-Agent got403; a bounded explicit-User-Agent retry downloaded both original/workflow attachments and compared exact bytes/fields. Native close then verified all controls disabled and archived=true/locked=true; no DELETE. Human click, Gateway ownership and original harness permission acceptance remain NOT_RUN/UNKNOWN.
