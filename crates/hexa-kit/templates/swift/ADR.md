# ADR — template-lang-swift

## ADR-001: Swift Version
**Status:** Accepted
**Context:** Swift version selection impacts available features and platform support.
**Decision:** Target Swift 5.9+ for all generated projects. Support iOS 16+ and macOS 13+.
**Rationale:** Swift 5.9 adds macro support and improved concurrency.

## ADR-002: Package Manager
**Status:** Accepted
**Context:** SPM, CocoaPods, and Carthage all support Swift.
**Decision:** Use Swift Package Manager (SPM) as primary. CocoaPods for UI libraries only.
**Rationale:** SPM is now native; better IDE integration, faster builds.

## ADR-003: Concurrency
**Status:** Accepted
**Context:** Swift has async/await and actors.
**Decision:** Use Swift Concurrency throughout. Actors for shared state. AsyncSequence for streams.
**Rationale:** Modern Swift concurrency is type-safe and prevents data races.

## ADR-004: Error Handling
**Status:** Accepted
**Context:** Swift has throw/catch and Result type.
**Decision:** Use throws for synchronous errors. Result<T> for completion handlers. Never force unwrap.
**Rationale:** Explicit error handling prevents crashes; Result composes better.

## ADR-005: Dependency Injection
**Status:** Accepted
**Context:** Multiple DI patterns exist for Swift.
**Decision:** Use initializer injection with protocols. Environment objects for SwiftUI.
**Rationale:** Protocol-based DI enables testing; no runtime magic.

## ADR-006: Architecture
**Status:** Accepted
**Context:** MVVM, MVC, and VIPER all exist.
**Decision:** MVVM with Coordinators for navigation. Observable for state management.
**Rationale:** MVVM is simple, testable, and scales well.
