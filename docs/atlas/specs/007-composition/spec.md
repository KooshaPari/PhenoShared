# SPEC-07 — Hexagonal applets and federation

Status: proposed program contract; no engine transition or product verification claimed.

## REQ-07-01 Explicit applet manifest

Declare capabilities, state, ports, permissions, lifecycle, resources and children.

Acceptance: An unnamed shared mutable state fails boundary review.

## REQ-07-02 Dependency direction

Keep domain rules independent of concrete UI/provider/storage implementations.

Acceptance: Architecture tests detect forbidden dependency direction.

## REQ-07-03 Behavioral substitutability

Qualify adapters against errors, timing, data and cancellation contracts.

Acceptance: Type compatibility alone cannot certify an adapter.

## REQ-07-04 Recursive composition

Allow composites to expose applet contracts without copying child authority.

Acceptance: Composed state ownership remains consistent across nesting.

## REQ-07-05 Optional capability semantics

Differentiate disabled, unsupported, unavailable, forbidden and incompatible.

Acceptance: Required missing backend is non-ready rather than mock healthy.

## REQ-07-06 Locality-aware lowering

Use direct/local paths unless isolation/placement cost justifies boundaries.

Acceptance: A proposed RPC/microservice split records overhead and benefit.

## REQ-07-07 No forced repo split

Applet identity does not itself create a repository or release requirement.

Acceptance: New repo requires independent boundary/approval beyond a module name.

## REQ-07-08 Lifecycle composition

Specify startup, readiness, quiescence, cancellation, unmount and recovery.

Acceptance: Parent shutdown does not leave unowned children or duplicate operations.

## Scope discipline

Apply the actual subject support/role contract. Preserve richer existing source formats and authority. Generated spec bundles do not certify native AgilePlus compatibility; inspect the installed engine/schema first. Unknowns and failures remain explicit.
