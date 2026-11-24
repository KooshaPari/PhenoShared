# Day 3 — HW Mesh Agent Bus Crate + Wiring

Scaffold the `hw-mesh-agent-bus` crate (ADR 0009) and wire a smoke-test RPC between oci-primary (planner) and home-mac (builder).

**Estimated wall-clock:** ~2 hours.

## Prerequisites

- ADR 0009 accepted (or advanced beyond stub).
- Rust toolchain on oci-primary and home-mac.
- Tailscale healthy; mesh hostnames resolve via MagicDNS.

## Step 1 — Create crate skeleton

New repo: `phenotype-hw-mesh` (create separately via `gh repo create KooshaPari/phenotype-hw-mesh --public`). Layout:

```
crates/
  hw-mesh-agent-bus/        # lib: tonic gRPC client + server helpers
  hw-mesh-planner/           # bin: runs on oci-primary
  hw-mesh-builder/           # bin: runs on home-mac
proto/
  mesh.proto                 # PlanRequest, BuildDispatch, HealthPing, ResultSink
```

## Step 2 — Proto definition (sketch)

```proto
syntax = "proto3";
package mesh.v1;
service Mesh {
  rpc HealthPing(HealthPingRequest) returns (HealthPingResponse);
  rpc DispatchBuild(BuildDispatchRequest) returns (BuildDispatchResponse);
}
message HealthPingRequest { string from = 1; }
message HealthPingResponse { string from = 1; int64 uptime_secs = 2; }
message BuildDispatchRequest { string repo = 1; string commit = 2; repeated string targets = 3; }
message BuildDispatchResponse { string dispatch_id = 1; }
```

## Step 3 — Deploy builder on home-mac

- `cargo build --release -p hw-mesh-builder` on home-mac.
- launchd plist similar to `com.phenotype.woodpecker-agent.plist`; binds to `:50051` on the Tailscale interface only.

## Step 4 — Deploy planner on oci-primary

- `cargo build --release -p hw-mesh-planner` — cross-compile with `cross` for `aarch64-unknown-linux-gnu`.
- systemd unit `hw-mesh-planner.service`.

## Step 5 — Smoke test

From oci-primary:

```
curl -s http://localhost:50051/... # gRPC over Tailscale to home-mac; use grpcurl
grpcurl -plaintext home-mac:50051 mesh.v1.Mesh/HealthPing
```

Expect a response from `home-mac` with its uptime.

## Rollback

- Stop planner/builder services.
- Destroy the `phenotype-hw-mesh` repo (or mark archived).
- Revert ADR 0009 to Proposed.

> **Status:** Phase-2 feature; expect churn on the proto as we use it.
