# Authenticated Flow — Real Runtime Evidence

**Run:** 2026-09-18 20:15 PDT · Binary built from `backend/byteport` (module `byteport`), CGO_ENABLED=1 with Xcode SDK.
**Environment:** scratch port 8099, scratch sqlite (`byteport-e2e.db`), no shared state with 8081.
**Caveat:** this covers the canonical backend only. The unused `/api/v1` module in `backend/` was NOT exercised.

## Method

Server started with `nohup`, confirmed listening on `0.0.0.0:8099` via GIN log. All probes via `curl` with a cookie jar. Signup creates a user; the session cookie from signup is reused for every authenticated route.

## Results

| # | Probe | Status | Verbatim body (truncated) | Class |
|---|---|---|---|---|
| 1 | `OPTIONS /signup` (preflight) | 204 | — | clean |
| 2 | `POST /signup` | 201 | `{"uuid":"9f6c20d3-…","name":"E2E Test",…}` | clean; password NOT echoed back (good) |
| 3 | `GET /authenticate` + session | 200 | `{"User":{…},"message":"Success"}` | clean; cookie session works |
| 4 | `GET /projects` + session | 200 | `[]` | clean; empty list for new user |
| 5 | `GET /instances` + session | 200 | `[]` | clean; empty list for new user |
| 6 | `GET /link` + session | 500 | `{"error":"Failed to decrypt client id"}` | env dependency |
| 7 | `GET /user/:id/creds` + session | 500 | `{"details":"no provider entry for \"openai\"","error":"Failed to decrypt OAI"}` | env dependency |
| 8 | `POST /deploy` invalid body | 500 | `{"error":"Failed to deploy project: Post \"http://localhost:8443/v1/deploy\": dial tcp [::1]:8443: connect: connection refused"}` | proxy + validation gap — **FIXED**, see [DEPLOY-AUTHORIZATION.md](DEPLOY-AUTHORIZATION.md) |

## Findings

**Clean (4/8).** CORS preflight, signup, cookie-authenticated `/authenticate`, and the per-user list routes all work with real requests. The password field is correctly zeroed in signup responses.

**Environment dependencies (2/8, routes 6-7).** `/link` and `/user/:id/creds` return 500 because the scratch sqlite has no stored OAuth client or LLM provider entries. These routes decrypt configured credentials; with none configured, failure is the designed behavior. Not proven broken, not proven correct — they need a configured environment to test.

**Validation gap (1/8, route 8) — FIXED.** A `POST /deploy` with `{"invalid":true}` was NOT rejected by local validation. It passed through and the handler attempted to proxy to `http://localhost:8443/v1/deploy` (the BFF/WorkOS module), which was not running. Two implications:

1. The deploy route has no up-front request validation, or its schema accepts this shape.
2. The deploy flow hard-depends on a second service on 8443. Any deploy attempt without it fails with connection refused.

Both were addressed in `DEPLOY-AUTHORIZATION.md` (same folder). Reading the handler while
fixing implication 1 also showed that the owner and the project identifiers were taken
from the request body, and that `POST /terminate` did not check ownership at all. The fix
rejects an incomplete body with 400 before any outbound call, derives identity from the
session, and scopes terminate to the owner. Implication 2 is unchanged by design: the
sandbox service is a real dependency, not a bug.

**Cross-check with prior coverage.** `docs/sessions/20260919-endpoint-coverage/COVERAGE.md` recorded unauthenticated status codes only. This report adds the authenticated flow it could not reach.

## Status

- Visual state: UNKNOWN (no screenshots taken; none permitted).
- Server killed after evidence collection; scratch db and log left in `$JCODE_SCRATCH_DIR`.

tx-agent: jcode
tx-task: G9 authenticated flows
tx-validated: go-build,curl-e2e
