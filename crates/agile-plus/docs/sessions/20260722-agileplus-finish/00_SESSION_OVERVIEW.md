# AgilePlus Finish Session Overview

## Goal

Finish AgilePlus as the trusted control plane before dogfooding full consumption,
usage, observability, and compliance journeys project by project. The first consumer
sequence is Tracera, then Grapheon after repository recovery.

## Decision

Control-plane first. No consumer rollout may substitute mocked, in-memory, or
undeliverable evidence for a working runtime, durable data, streamed events, stored
artifacts, and immutable compliance evidence.

## Baseline

This documentation branch begins at `a086185b586835a342395c422ffe1bbc71e30e2e`
(`fix(domain): declare optional keychain feature (#923)`). It contains only session
documentation; implementation work must begin in separate, focused worktrees.

## Exit criteria

1. A clean build produces runnable API and MCP deliverables, rather than proto stubs.
2. One resolved runtime configuration drives launcher, compose, API, gRPC, MCP, and
   health probes without port collisions.
3. Credentials and API keys never persist plaintext: use the OS keychain when
   available, otherwise an encrypted, fail-closed AES-256-GCM/Argon2id file store.
4. Events, artifacts, stream cursors, usage, traces, and governance decisions are
   durable, queryable, and attributable to one project/feature/work-package run.
5. Tracera passes the complete consumer journey; Grapheon passes it after merge-conflict
   recovery; each later project uses the same evidence pack and gate sequence.

## Non-goals

This session does not change product code, start shared services, or claim a rollout
has passed. It specifies the implementation and validation required to make those
claims valid.

## Snapshot policy

An Airlock snapshot preserves committed `HEAD` only. Every meaningful edit batch must
therefore be committed before its snapshot is requested; a snapshot is not evidence that
uncommitted changes were preserved.
