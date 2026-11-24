# ADR 0002: Treat mobile presence as outside current scope

- Status: Accepted
- Date: 2026-07-13
- Decision owners: SessionLedger maintainers
- Related: `audit/SCORECARD.md`, `docs/adr/0001-desktop-companion-scope.md`, `docs/ops/distribution.md`

## Context

SessionLedger is currently scoped as a desktop-plus-daemon product:

1. `sl-daemon`, which watches, compiles, stores, and serves session data.
2. `sl-viewer`, a user-launched desktop viewer for inspecting that data.

The SCORECARD tracks mobile presence as a soft goal, not as a hard release
requirement. That soft-goal line currently records the absence of a mobile
decision as missing evidence; it does not imply an accepted iOS, Android, or
mobile-web delivery requirement.

A native mobile app would add a separate product surface with packaging,
distribution, authentication, sync, device storage, privacy, notification,
offline, and support requirements. Those commitments are not part of the
current desktop viewer and daemon scope. A responsive web viewer may still be
useful for narrow inspection workflows, but it is optional stretch work rather
than the definition of mobile presence for this release line.

## Decision

Mobile presence is **Soft / Not Applicable** for the current SessionLedger
product scope. SessionLedger will not ship or score itself against a native
iOS or Android app in the current daemon-plus-desktop-viewer release line.

The only mobile-adjacent work considered in scope is best-effort responsive
behavior for the web/viewer experience when that can be done without creating a
separate mobile application, mobile packaging channel, or mobile support
contract.

## Consequences

- Release and packaging evidence remains focused on the desktop viewer,
  daemon, and documented installer scaffolds.
- Missing App Store, Play Store, PWA, push notification, and mobile offline
  evidence is intentional product scope, not a release blocker.
- Responsive layout improvements may be accepted as usability enhancements, but
  they do not change SessionLedger into a mobile product.
- Future mobile work must be proposed as a new product surface with its own
  security, sync, distribution, and support plan.

## Reconsider when

Revisit this decision only when mobile access becomes a committed product
requirement, supported by user need and an implementation plan for at least:

- authentication and authorization from mobile devices,
- data sync or server-backed access semantics,
- mobile storage and privacy expectations,
- app distribution and update operations, and
- support ownership for mobile-specific failures.
