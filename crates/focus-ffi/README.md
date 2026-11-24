# focus-ffi

UniFFI export surface for FocalPoint core. Exposes the mascot state machine plus rules/rewards/penalties/policy/audit/sync sub-APIs to Swift (via UniFFI) and Kotlin (via UniFFI-Kotlin/JNI) using a single UDL (Uniffi Definition Language).

## Purpose

Bridges Rust core to native platforms (iOS, Android) without requiring native implementations of domain logic. All business rules, state machines, and sync orchestration live in Rust; native layers call through FFI for state mutations and queries.

## Key Types

- Exported wrapper types for `MascotMachine`, `RewardWallet`, `PenaltyState`, `EnforcementPolicy`, `Rule`, `AuditChain`
- FFI result types that map Rust errors to native exceptions
- Object handles for long-lived objects (state machines, stores)

## Entry Points

- UDL file (`focalpoint.udl`) — defines all exported types and methods
- Generated scaffolding at build time via `uniffi_build`
- Swift: import `FocalPointFFI` framework; Kotlin: import `com.focalpoint.ffi` package

## Functional Requirements

- Cross-platform state machine exposure
- Error translation (Rust → Swift/Kotlin)
- Thread-safe reference handling via UniFFI

## Consumers

- iOS app (Swift bindings from generated scaffolding)
- Android app (Kotlin bindings from generated scaffolding)
- `focus-mcp-server` (uses same Rust APIs for testing)
