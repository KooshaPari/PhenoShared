# Recursive applets and hexagonal boundaries

## Applet contract

Each applet declares identity/version, provided/required capabilities, commands/queries/events/streams, owned state, permission scopes, lifecycle/health, resource/timing assumptions, supported surfaces, child composition and version/feature negotiation. A composite may expose a smaller contract upward while preserving its children's ownership and trust boundaries.

A pure package can be an applet. A UI feature can be an applet. A background service can be an applet. These do not all need daemon startup, network serialization or hot unload. Repository independence is earned by consumer/release/security/licensing/governance boundaries—not recursive aesthetics.

## Invariants

Domain logic depends on domain-facing ports, not specific GUI/provider/database SDKs. Adapters obey the same observable contract, including errors, cancellation, timing and ownership. Replaceability tests must demonstrate the boundary; directory names alone are insufficient. Do not create adapters for stable internal functions when there is no useful boundary to protect.

Optional children negotiate capabilities explicitly. Unsupported, disabled, unavailable, incompatible and forbidden are different states. Parent health composes actual required child readiness; it cannot mark a required backend healthy merely because it produced a mock record. Children quiesce before unmount/upgrade, and parent cancellation has defined propagation and unresolved-operation handling.

## Resource and locality lowering

For same-process hot paths, prefer direct calls and qualified shared ownership. Shared-memory/IPC paths require appropriate lifecycle and security. Network placement requires marshalling, retry, consistency and deadline contracts. Wasm Component Model or other ABI technology is optional after concrete qualification. Do not impose a universal RPC layer on every internal edge.

## Federation test

Compose two applets independently, then as a product. Remove an optional capability and verify graceful behavior. Remove a required capability and verify explicit non-readiness. Test version mismatch, cancellation, restart, permission reduction and the actual public UI/CLI/API surface. A composition diagram is not acceptance evidence.

## Consumer-driven boundaries

Apply [ecosystem-first evolution](ECOSYSTEM-FIRST-EVOLUTION.md). Derive shared applet contracts from actual and committed consumers; make plausible future seams cheap rather than inventing speculative services. Reuse owned contracts and adapters where appropriate. A composite remains independently useful and does not make every child depend on unrelated siblings or the entire platform. Contract evolution names affected consumers, required tests and migration ownership.
