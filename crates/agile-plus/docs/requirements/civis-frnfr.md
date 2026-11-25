# Civis — FR/NFR Catalog

Version 1.0 · 2026-06-09 · Generated from `civis-game/agileplus-specs/civ-001..civ-013/meta.json` and `civis-game/FUNCTIONAL_REQUIREMENTS.md`.

This catalog traces the Civis PRD initiative epics E1–E8: each `### FR-...` block below carries an explicit Status cell and a Traceability cell pointing at its source spec_id and most relevant crate.

---

## Epic E1: Core Simulation Engine

### FR-CORE-001 — Fixed-Timestep Tick Loop

| Field | Value |
|---|---|
| **ID** | FR-CORE-001 |
| **Title** | Fixed-Timestep Tick Loop |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-001; crates/engine |

---

### FR-CORE-002 — ECS Entity Model

| Field | Value |
|---|---|
| **ID** | FR-CORE-002 |
| **Title** | ECS Entity Model |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-001; crates/engine |

---

### FR-CORE-003 — Deterministic Transition Phase

| Field | Value |
|---|---|
| **ID** | FR-CORE-003 |
| **Title** | Deterministic Transition Phase |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-001; crates/engine |

---

### FR-CORE-004 — Stochastic Event Phase with Seeded RNG

| Field | Value |
|---|---|
| **ID** | FR-CORE-004 |
| **Title** | Stochastic Event Phase with Seeded RNG |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-001; crates/engine |

---

### FR-CORE-005 — Policy Evaluation Phase

| Field | Value |
|---|---|
| **ID** | FR-CORE-005 |
| **Title** | Policy Evaluation Phase |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-001; crates/engine |

---

### FR-CORE-006 — Multi-Client Command Queue

| Field | Value |
|---|---|
| **ID** | FR-CORE-006 |
| **Title** | Multi-Client Command Queue |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-001; crates/engine |

---

### FR-CORE-007 — Tick Budget Enforcement

| Field | Value |
|---|---|
| **ID** | FR-CORE-007 |
| **Title** | Tick Budget Enforcement |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-001; crates/engine |

---

## Epic E2: Economy, Actors, Building, Climate, Genetics, Culture

### FR-ECON-001 — Production System

| Field | Value |
|---|---|
| **ID** | FR-ECON-001 |
| **Title** | Production System |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-002; crates/economy |

---

### FR-ECON-002 — Joule Energy Conservation

| Field | Value |
|---|---|
| **ID** | FR-ECON-002 |
| **Title** | Joule Energy Conservation |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-002; crates/economy |

---

### FR-ECON-003 — Market Clearing

| Field | Value |
|---|---|
| **ID** | FR-ECON-003 |
| **Title** | Market Clearing |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-002; crates/economy |

---

### FR-ECON-004 — Taxation and Budget System

| Field | Value |
|---|---|
| **ID** | FR-ECON-004 |
| **Title** | Taxation and Budget System |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-002; crates/economy |

---

### FR-ECON-005 — Allocation Algorithm

| Field | Value |
|---|---|
| **ID** | FR-ECON-005 |
| **Title** | Allocation Algorithm |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-002; crates/economy |

---

### FR-METRICS-001 — Metrics Struct

| Field | Value |
|---|---|
| **ID** | FR-METRICS-001 |
| **Title** | Metrics Struct |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-002; crates/engine/src/metrics.rs |

---

### FR-METRICS-002 — Metrics Computation

| Field | Value |
|---|---|
| **ID** | FR-METRICS-002 |
| **Title** | Metrics Computation |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-002; crates/engine/src/metrics.rs |

---

### FR-METRICS-003 — Fixed-Point Determinism for Metrics

| Field | Value |
|---|---|
| **ID** | FR-METRICS-003 |
| **Title** | Fixed-Point Determinism for Metrics |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-002; crates/engine/src/lib.rs |

---

### FR-CIV-ACTOR-001 — Citizen Lifecycle Core

| Field | Value |
|---|---|
| **ID** | FR-CIV-ACTOR-001 |
| **Title** | Citizen Lifecycle Core |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-003; crates/agents |

---

### FR-CIV-ACTOR-002 — Citizen State Machine

| Field | Value |
|---|---|
| **ID** | FR-CIV-ACTOR-002 |
| **Title** | Citizen State Machine |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-003; crates/agents |

---

### FR-CIV-SOCIAL-001 — Social Relationships

| Field | Value |
|---|---|
| **ID** | FR-CIV-SOCIAL-001 |
| **Title** | Social Relationships |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-003; crates/agents |

---

### FR-CIV-SOCIAL-002 — Emergent Social Clusters

| Field | Value |
|---|---|
| **ID** | FR-CIV-SOCIAL-002 |
| **Title** | Emergent Social Clusters |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-003; crates/agents |

---

### FR-CIV-BUILD-001 — Building Tiers

| Field | Value |
|---|---|
| **ID** | FR-CIV-BUILD-001 |
| **Title** | Building Tiers |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-004; crates/build |

---

### FR-CIV-BUILD-002 — Production Chains

| Field | Value |
|---|---|
| **ID** | FR-CIV-BUILD-002 |
| **Title** | Production Chains |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-004; crates/build |

---

### FR-CIV-BUILD-003 — Building Upgrade Paths

| Field | Value |
|---|---|
| **ID** | FR-CIV-BUILD-003 |
| **Title** | Building Upgrade Paths |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-004; crates/build |

---

### FR-CIV-CLIMATE-001 — Seasonal Climate Cycle

| Field | Value |
|---|---|
| **ID** | FR-CIV-CLIMATE-001 |
| **Title** | Seasonal Climate Cycle |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-005; crates/planet |

---

### FR-CIV-CLIMATE-002 — Disaster Events

| Field | Value |
|---|---|
| **ID** | FR-CIV-CLIMATE-002 |
| **Title** | Disaster Events |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-005; crates/planet |

---

### FR-CIV-CLIMATE-003 — Climate Effects on Production

| Field | Value |
|---|---|
| **ID** | FR-CIV-CLIMATE-003 |
| **Title** | Climate Effects on Production |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-005; crates/planet |

---

### FR-CIV-BIO-001 — Genome Model

| Field | Value |
|---|---|
| **ID** | FR-CIV-BIO-001 |
| **Title** | Genome Model |
| **Priority** | SHOULD |
| **Status** | SHIPPED |
| **Traceability** | civ-008; crates/genetics |

---

### FR-CIV-BIO-002 — Trait Inheritance

| Field | Value |
|---|---|
| **ID** | FR-CIV-BIO-002 |
| **Title** | Trait Inheritance |
| **Priority** | SHOULD |
| **Status** | SHIPPED |
| **Traceability** | civ-008; crates/genetics |

---

### FR-CIV-BIO-003 — Species Divergence

| Field | Value |
|---|---|
| **ID** | FR-CIV-BIO-003 |
| **Title** | Species Divergence |
| **Priority** | SHOULD |
| **Status** | SHIPPED |
| **Traceability** | civ-008; crates/species |

---

### FR-CIV-CULT-001 — Culture Vector Model

| Field | Value |
|---|---|
| **ID** | FR-CIV-CULT-001 |
| **Title** | Culture Vector Model |
| **Priority** | SHOULD |
| **Status** | SHIPPED |
| **Traceability** | civ-009; crates/agents |

---

### FR-CIV-CULT-002 — Ideology Diffusion

| Field | Value |
|---|---|
| **ID** | FR-CIV-CULT-002 |
| **Title** | Ideology Diffusion |
| **Priority** | SHOULD |
| **Status** | SHIPPED |
| **Traceability** | civ-009; crates/agents |

---

### FR-CIV-CULT-003 — Cultural Drift Over Generations

| Field | Value |
|---|---|
| **ID** | FR-CIV-CULT-003 |
| **Title** | Cultural Drift Over Generations |
| **Priority** | SHOULD |
| **Status** | SHIPPED |
| **Traceability** | civ-009; crates/agents |

---

## Epic E3: Multi-Client Protocol

### FR-PROTO-001 — RFC 6455 WebSocket Server

| Field | Value |
|---|---|
| **ID** | FR-PROTO-001 |
| **Title** | RFC 6455 WebSocket Server |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-010; crates/protocol-3d |

---

### FR-PROTO-002 — JSON-RPC 2.0 Message Dispatcher

| Field | Value |
|---|---|
| **ID** | FR-PROTO-002 |
| **Title** | JSON-RPC 2.0 Message Dispatcher |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-010; crates/protocol-3d |

---

### FR-PROTO-003 — Client Handshake and Bootstrap

| Field | Value |
|---|---|
| **ID** | FR-PROTO-003 |
| **Title** | Client Handshake and Bootstrap |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-010; crates/protocol-3d |

---

### FR-PROTO-004 — Binary Frame Protocol

| Field | Value |
|---|---|
| **ID** | FR-PROTO-004 |
| **Title** | Binary Frame Protocol |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-010; crates/protocol-3d |

---

### FR-PROTO-005 — Snapshot Filtering by Region and Type

| Field | Value |
|---|---|
| **ID** | FR-PROTO-005 |
| **Title** | Snapshot Filtering by Region and Type |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-010; crates/protocol-3d |

---

### FR-CLIENT-003 — Client Role Authorization Enforcement

| Field | Value |
|---|---|
| **ID** | FR-CLIENT-003 |
| **Title** | Client Role Authorization Enforcement |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-010; crates/protocol-3d |

---

## Epic E4: Deep Combat, Diplomacy, Laws, and Government

### FR-CIV-WAR-001 — War Goals

| Field | Value |
|---|---|
| **ID** | FR-CIV-WAR-001 |
| **Title** | War Goals |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-006; crates/tactics |

---

### FR-CIV-WAR-002 — Combat Resolution

| Field | Value |
|---|---|
| **ID** | FR-CIV-WAR-002 |
| **Title** | Combat Resolution |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-006; crates/tactics |

---

### FR-CIV-WAR-003 — Casualties and Attrition

| Field | Value |
|---|---|
| **ID** | FR-CIV-WAR-003 |
| **Title** | Casualties and Attrition |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-006; crates/tactics |

---

### FR-CIV-WAR-004 — War Exhaustion

| Field | Value |
|---|---|
| **ID** | FR-CIV-WAR-004 |
| **Title** | War Exhaustion |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-006; crates/tactics |

---

### FR-CIV-DIPLO-001 — Bounded War Goals and Defender Evaluation

| Field | Value |
|---|---|
| **ID** | FR-CIV-DIPLO-001 |
| **Title** | Bounded War Goals and Defender Evaluation |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-007; crates/laws |

---

### FR-CIV-DIPLO-002 — Treaties and Trust Ledger

| Field | Value |
|---|---|
| **ID** | FR-CIV-DIPLO-002 |
| **Title** | Treaties and Trust Ledger |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-007; crates/laws |

---

### FR-CIV-DIPLO-003 — Negotiation and Reservation Utility

| Field | Value |
|---|---|
| **ID** | FR-CIV-DIPLO-003 |
| **Title** | Negotiation and Reservation Utility |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-007; crates/laws |

---

### FR-CIV-GOV-001 — Government Forms

| Field | Value |
|---|---|
| **ID** | FR-CIV-GOV-001 |
| **Title** | Government Forms |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-007; crates/laws |

---

### FR-CIV-GOV-002 — Law and Policy Enactment

| Field | Value |
|---|---|
| **ID** | FR-CIV-GOV-002 |
| **Title** | Law and Policy Enactment |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-007; crates/laws |

---

## Epic E5: Research API and Scenario System

### FR-API-001 — Scenario YAML Format and Validation

| Field | Value |
|---|---|
| **ID** | FR-API-001 |
| **Title** | Scenario YAML Format and Validation |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-013; crates/research |

---

### FR-API-002 — Python Scenario Runner

| Field | Value |
|---|---|
| **ID** | FR-API-002 |
| **Title** | Python Scenario Runner |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-013; crates/research |

---

### FR-API-003 — Policy Parameter Override

| Field | Value |
|---|---|
| **ID** | FR-API-003 |
| **Title** | Policy Parameter Override |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-013; crates/research |

---

### FR-API-004 — Data Export for Analysis

| Field | Value |
|---|---|
| **ID** | FR-API-004 |
| **Title** | Data Export for Analysis |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-013; crates/research |

---

### FR-REPLAY-001 — Civreplay Export Format

| Field | Value |
|---|---|
| **ID** | FR-REPLAY-001 |
| **Title** | Civreplay Export Format |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-013; crates/engine |

---

### FR-REPLAY-002 — Bit-Identical Determinism Verification

| Field | Value |
|---|---|
| **ID** | FR-REPLAY-002 |
| **Title** | Bit-Identical Determinism Verification |
| **Priority** | SHALL |
| **Status** | PLANNED |
| **Traceability** | civ-013; crates/engine |

---

## Epic E7: Bevy Primary Client

### FR-CLIENT-001 — Bevy Reference Client

| Field | Value |
|---|---|
| **ID** | FR-CLIENT-001 |
| **Title** | Bevy Reference Client |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-011; clients/bevy-ref |

---

### FR-CIV-HUD-001 — RTS HUD Frame

| Field | Value |
|---|---|
| **ID** | FR-CIV-HUD-001 |
| **Title** | RTS HUD Frame |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-011; clients/bevy-ref |

---

### FR-CIV-HUD-002 — Minimap and World View

| Field | Value |
|---|---|
| **ID** | FR-CIV-HUD-002 |
| **Title** | Minimap and World View |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-011; clients/bevy-ref |

---

### FR-CIV-HUD-003 — Entity Inspector Panel

| Field | Value |
|---|---|
| **ID** | FR-CIV-HUD-003 |
| **Title** | Entity Inspector Panel |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-011; clients/bevy-ref |

---

### FR-CIV-HUD-004 — Brush and Build Tools

| Field | Value |
|---|---|
| **ID** | FR-CIV-HUD-004 |
| **Title** | Brush and Build Tools |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-011; clients/bevy-ref |

---

### FR-CIV-HUD-005 — Time Controls and Speed

| Field | Value |
|---|---|
| **ID** | FR-CIV-HUD-005 |
| **Title** | Time Controls and Speed |
| **Priority** | SHALL |
| **Status** | SHIPPED |
| **Traceability** | civ-011; clients/bevy-ref |

---

## Epic E8: Godot Secondary Client

### FR-CIV-CLIENT-GODOT-001 — Godot Client Connection

| Field | Value |
|---|---|
| **ID** | FR-CIV-CLIENT-GODOT-001 |
| **Title** | Godot Client Connection |
| **Priority** | SHOULD |
| **Status** | PLANNED |
| **Traceability** | civ-012; clients/godot |

---

### FR-CIV-CLIENT-GODOT-002 — Godot Strategic View

| Field | Value |
|---|---|
| **ID** | FR-CIV-CLIENT-GODOT-002 |
| **Title** | Godot Strategic View |
| **Priority** | SHOULD |
| **Status** | PLANNED |
| **Traceability** | civ-012; clients/godot |

---
