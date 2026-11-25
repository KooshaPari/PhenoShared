# ResearchLedger Release Candidate P1 Safety Design

## Scope

This is the first remediation slice for the ResearchLedger A+ release candidate. It covers only defects that can cause unconsented retrieval, server-side request forgery, incorrect reranker verification, empty successful captures, weak production CSP checks, or acceptance of an incorrectly signed macOS app. Hosted CI workflow changes are intentionally a separate follow-up because they require their own approval and evidence cycle.

## Design

### Reference fetching

Reference jobs remain queued only after an explicit consent decision. Dequeue scans pending jobs in deterministic id order until it has found the requested count of currently allowed jobs, so a revoked job cannot starve later eligible jobs. The worker rechecks consent after it claims a job and immediately before network activity; a revoked job is marked blocked and never fetched.

URL policy rejects non-public literal addresses, including IPv4-mapped IPv6, carrier-grade NAT, documentation/reserved, multicast, and broadcast ranges. Hostname resolution remains a preflight policy check; the implementation must not claim it eliminates DNS rebinding until the HTTP client is pinned to the validated addresses. The release scorecard must record that residual limitation explicitly if address pinning is not implemented in this slice.

### Capture, reranker, CSP, and macOS release checks

Capture sessions assert a non-empty result before serialization and close their browser context with `finally`. Each reranker endpoint candidate receives a request body formed for that candidate's engine, so fallback across MLX/TEI does not send an incompatible protocol. Production CSP validation rejects wildcard, loopback/localhost, and WebSocket development sources rather than one hard-coded Vite URL.

The macOS release verifier requires the actual Developer ID authority to contain the configured signing identity and requires a secure signing timestamp, in addition to the existing hardened-runtime and entitlement checks. These are pre-notarization gates; they do not represent signing or notarization evidence.

## Verification

- Unit tests prove pending-job scanning passes a later consented job after revoked jobs and prove a revoked claimed job cannot be fetched.
- URL unit tests cover mapped IPv6 and the non-routable IPv4 ranges handled by policy.
- Node tests prove empty captures reject and close their context, candidate reranker bodies follow each candidate engine, and CSP rejects localhost/WebSocket variants.
- Release-script tests prove the preflight rejects an authority mismatch and a missing timestamp without calling notarization.
- Full Rust and Bun suites must pass before the next snapshot/PR update.

## Non-goals

- No LinkedIn browser crawling, cookie/profile extraction, or CAPTCHA work.
- No claim that hostname preflight alone prevents DNS rebinding.
- No release, signing, notarization, or authenticated GitHub-import completion claim.
