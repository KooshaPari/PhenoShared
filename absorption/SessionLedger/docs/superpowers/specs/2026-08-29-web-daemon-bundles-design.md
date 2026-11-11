# Web viewer daemon-backed bundles

## Problem

The `sl-viewer` WASM target selects `DataSource::Mock` unconditionally. As a
result, its Bundles tab renders embedded demo sessions even when a reachable
local `sl-daemon` is serving real OKF documents at `GET /api/bundles`. This
breaks the documented local daemon-to-viewer journey for the web target.

## Decision

Add a daemon-backed bundle loader for the WASM build. It will request the
already documented `GET /api/bundles` endpoint at `SL_DAEMON_URL` (or the
existing loopback default), parse the returned OKF documents, and project each
document into the existing `Session` model used by all viewer tabs.

Desktop behavior remains unchanged: it continues to use native corpus
discovery unless a pre-existing desktop data-source option selects another
source. Mock data remains available only for explicit demo and visual-fixture
paths.

## Data flow

```text
JSONL -> sl-daemon -> OKF files -> GET /api/bundles -> WASM loader
                                                       |
                                                       v
                                                 Vec<Session>
                                                       |
                                                       v
                                           existing Bundles / History UI
```

The loader must tolerate additive OKF fields and reject malformed documents
with a plain-language error. An empty successful response is an empty state,
not a mock-data fallback. Network or decode failures are surfaced through the
existing retryable discovery error state.

## Scope

- Add an API response type and pure OKF-to-`Session` projection helper.
- Add a WASM async loader using the viewer's current HTTP dependency.
- Select this loader for non-fixture WASM builds.
- Add focused parser/projection tests and a fixture-backed browser assertion
  that the rendered bundle identifiers originate from the daemon.

## Explicit non-goals

- No public deployment or non-loopback daemon exposure.
- No change to desktop corpus discovery defaults.
- No web replay SSE implementation; the current desktop-only replay boundary
  remains documented separately.
- No API contract change in `sl-daemon`.

## Acceptance evidence

1. A WASM build with a local daemon returns and renders known fixture IDs
   `fuzz-a` and `fuzz-b`, not the embedded demo IDs.
2. A malformed daemon response produces a retryable error rather than stale
   mock content.
3. Existing desktop corpus-loader tests and workspace quality gates remain
   green.
