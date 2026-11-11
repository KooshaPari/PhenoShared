# OKF — Worked Examples

> **Companion to:** [`OKF-SPEC.md`](./OKF-SPEC.md) (v1.0).
> **Audience:** engineers building or verifying OKF parsers, plus reviewers
> who want to sanity-check a SessionLedger output against the spec.
> **Convention:** every example in this document is **valid OKF v1.0** and
> passes the conformance corpus tests under
> [`conformance/`](./conformance/) (see that directory's README).

---

## Table of Contents

1. [How to read these examples](#1-how-to-read-these-examples)
2. [Auth-fix session (4-keyframe, single intent)](#2-auth-fix-session-4-keyframe-single-intent)
3. [Billing integration (multi-intent, multi-criteria)](#3-billing-integration-multi-intent-multi-criteria)
4. [ARM CI runner (no constraints, sparse contract)](#4-arm-ci-runner-no-constraints-sparse-contract)
5. [Minimal session (empty acceptance, no contract)](#5-minimal-session-empty-acceptance-no-contract)
6. [Multi-intent session (2 intents in one OKF)](#6-multi-intent-session-2-intents-in-one-okf)
7. [Rejected / invalid examples (what NOT to emit)](#7-rejected--invalid-examples-what-not-to-emit)
8. [Where to find live examples in the wild](#8-where-to-find-live-examples-in-the-wild)

---

## 1. How to read these examples

Each example has:

- **Source** — a one-paragraph description of the originating session.
- **Input** — the messages the user and assistant exchanged (truncated).
- **Expected OKF** — the v1.0 document SessionLedger SHOULD emit.
- **Conformance check** — which file under `conformance/` covers this shape
  and how to run the check.

All examples share these non-negotiable shape rules (from the spec):

- Top-level `okf: "1.0"` (no patch component).
- Top-level `source_id` matching the SessionLedger session id.
- Top-level `provenance` with at least `corpus` and `source_id`.
- Every entity has a unique `id`, a `type`, a `label`, and an optional
  `properties` blob.
- Every relation's `source` and `target` ids exist in `entities[]`.

---

## 2. Auth-fix session (4-keyframe, single intent)

**Source:** a developer fixing a login-timeout regression in the auth
service. The session lasted 5 user turns and ended with "looks good, ship it".

**Input messages** (truncated):

```text
USER: The login session keeps expiring after 5 minutes, we need to fix this.
ASSISTANT: Let me trace the auth middleware to find where the TTL is set.
ASSISTANT: Found it — the session TTL is hardcoded to 300s in src/auth/session.rs.
USER: Increase it to 1800s and make sure MFA is preserved.
ASSISTANT: Done. TTL bumped, all existing auth tests pass.
USER: Looks good, tests pass. Ship it.
```

**Expected OKF:**

```json
{
  "okf": "1.0",
  "source_id": "forge-session-001",
  "entities": [
    {
      "id": "intent-0",
      "type": "intent",
      "label": "Fix login timeout regression after auth refactor",
      "properties": { "user_turn_count": 5 }
    },
    {
      "id": "acceptance-0",
      "type": "acceptance",
      "label": "all existing auth tests pass",
      "properties": null
    },
    {
      "id": "acceptance-1",
      "type": "acceptance",
      "label": "session expiry extends beyond 30 min",
      "properties": null
    },
    {
      "id": "acceptance-2",
      "type": "acceptance",
      "label": "user story AC-417 verified",
      "properties": null
    },
    {
      "id": "constraint-0",
      "type": "constraint",
      "label": "must not touch password reset flow",
      "properties": null
    },
    {
      "id": "constraint-1",
      "type": "constraint",
      "label": "must preserve MFA",
      "properties": null
    },
    {
      "id": "resource-0",
      "type": "resource",
      "label": "working-directory",
      "properties": { "cwd": "/home/dev/auth-service" }
    },
    {
      "id": "state-0",
      "type": "state",
      "label": "session-title",
      "properties": { "title": "Login timeout fix" }
    },
    {
      "id": "criteria-0",
      "type": "criteria",
      "label": "existing auth tests pass",
      "properties": {
        "skipped_by": ["existing auth tests pass"],
        "watch_files": ["src/auth/session.rs"]
      }
    },
    {
      "id": "gate-0",
      "type": "gate",
      "label": "resume-gate",
      "properties": {
        "ready": true,
        "scope_sized": true,
        "user_turns": 5
      }
    }
  ],
  "relations": [
    {
      "source": "intent-0",
      "target": "acceptance-0",
      "type": "verified_by",
      "provenance": { "corpus": "forge", "source_id": "forge-session-001" }
    },
    {
      "source": "intent-0",
      "target": "acceptance-1",
      "type": "verified_by",
      "provenance": { "corpus": "forge", "source_id": "forge-session-001" }
    },
    {
      "source": "intent-0",
      "target": "acceptance-2",
      "type": "verified_by",
      "provenance": { "corpus": "forge", "source_id": "forge-session-001" }
    },
    {
      "source": "intent-0",
      "target": "constraint-0",
      "type": "bounded_by",
      "provenance": { "corpus": "forge", "source_id": "forge-session-001" }
    },
    {
      "source": "intent-0",
      "target": "constraint-1",
      "type": "bounded_by",
      "provenance": { "corpus": "forge", "source_id": "forge-session-001" }
    },
    {
      "source": "intent-0",
      "target": "criteria-0",
      "type": "requires",
      "provenance": { "corpus": "forge", "source_id": "forge-session-001" }
    },
    {
      "source": "intent-0",
      "target": "gate-0",
      "type": "asserts",
      "provenance": { "corpus": "forge", "source_id": "forge-session-001" }
    }
  ],
  "provenance": { "corpus": "forge", "source_id": "forge-session-001" }
}
```

**Conformance check:** see
[`conformance/fixtures/auth-fix-session-001.okf.json`](./conformance/fixtures/auth-fix-session-001.okf.json).

```sh
cargo test -p session-ledger --features okf-conformance -- conformance::auth_fix
```

---

## 3. Billing integration (multi-intent, multi-criteria)

**Source:** a 12-turn session about adding usage-based billing to the API
proxy layer. The session covers Stripe integration, rate-limit headers, and
a billing dashboard.

**Input messages** (truncated):

```text
USER: We need usage-based billing in the API proxy layer.
ASSISTANT: I'll design the middleware pipeline — rate limiter + counter.
USER: Integrate Stripe for payments but no credit card required for dev tier.
ASSISTANT: Stripe integration done. Dev tier exempted.
USER: Make sure rate limit headers reflect remaining quota.
ASSISTANT: Headers added. Billing dashboard renders for admins.
USER: Approved, ship it.
```

**Expected OKF:**

```json
{
  "okf": "1.0",
  "source_id": "codex-session-003",
  "entities": [
    {
      "id": "intent-0",
      "type": "intent",
      "label": "Add usage-based billing to the API proxy layer",
      "properties": { "user_turn_count": 12 }
    },
    {
      "id": "acceptance-0",
      "type": "acceptance",
      "label": "stripe integration complete",
      "properties": null
    },
    {
      "id": "acceptance-1",
      "type": "acceptance",
      "label": "rate limit headers reflect remaining quota",
      "properties": null
    },
    {
      "id": "acceptance-2",
      "type": "acceptance",
      "label": "billing dashboard renders for admin users",
      "properties": null
    },
    {
      "id": "constraint-0",
      "type": "constraint",
      "label": "no credit card required for dev tier",
      "properties": null
    },
    {
      "id": "constraint-1",
      "type": "constraint",
      "label": "must log all billing events",
      "properties": null
    },
    {
      "id": "resource-0",
      "type": "resource",
      "label": "working-directory",
      "properties": { "cwd": "/home/dev/api-gateway" }
    },
    {
      "id": "state-0",
      "type": "state",
      "label": "session-title",
      "properties": { "title": "Usage billing" }
    },
    {
      "id": "criteria-0",
      "type": "criteria",
      "label": "existing billing tests pass",
      "properties": {
        "skipped_by": ["existing billing tests pass"],
        "watch_files": ["src/middleware/usage.rs", "src/billing/"]
      }
    },
    {
      "id": "gate-0",
      "type": "gate",
      "label": "resume-gate",
      "properties": {
        "ready": true,
        "scope_sized": true,
        "user_turns": 12
      }
    }
  ],
  "relations": [
    {
      "source": "intent-0",
      "target": "acceptance-0",
      "type": "verified_by",
      "provenance": { "corpus": "codex", "source_id": "codex-session-003" }
    },
    {
      "source": "intent-0",
      "target": "acceptance-1",
      "type": "verified_by",
      "provenance": { "corpus": "codex", "source_id": "codex-session-003" }
    },
    {
      "source": "intent-0",
      "target": "acceptance-2",
      "type": "verified_by",
      "provenance": { "corpus": "codex", "source_id": "codex-session-003" }
    },
    {
      "source": "intent-0",
      "target": "constraint-0",
      "type": "bounded_by",
      "provenance": { "corpus": "codex", "source_id": "codex-session-003" }
    },
    {
      "source": "intent-0",
      "target": "constraint-1",
      "type": "bounded_by",
      "provenance": { "corpus": "codex", "source_id": "codex-session-003" }
    },
    {
      "source": "intent-0",
      "target": "criteria-0",
      "type": "requires",
      "provenance": { "corpus": "codex", "source_id": "codex-session-003" }
    },
    {
      "source": "intent-0",
      "target": "gate-0",
      "type": "asserts",
      "provenance": { "corpus": "codex", "source_id": "codex-session-003" }
    }
  ],
  "provenance": { "corpus": "codex", "source_id": "codex-session-003" }
}
```

**Conformance check:** see
[`conformance/fixtures/billing-session-003.okf.json`](./conformance/fixtures/billing-session-003.okf.json).

---

## 4. ARM CI runner (no constraints, sparse contract)

**Source:** a short 3-turn session about adding ARM builds to a CI pipeline.
The user emphasized "do not modify the existing x86_64 workflow matrix" but
did not state explicit acceptance signals.

**Input messages** (truncated):

```text
USER: Can we add ARM builds to the CI pipeline?
ASSISTANT: I'll set up a self-hosted ARM runner via GitHub Actions.
USER: Make sure x86_64 builds are unaffected and runner is ephemeral.
ASSISTANT: Done. ARM artifacts now publish to GHCR. Build time under 10 min.
USER: All good, thanks.
```

**Expected OKF:**

```json
{
  "okf": "1.0",
  "source_id": "claude-session-007",
  "entities": [
    {
      "id": "intent-0",
      "type": "intent",
      "label": "Update CI pipeline to use self-hosted runner for ARM builds",
      "properties": { "user_turn_count": 3 }
    },
    {
      "id": "acceptance-0",
      "type": "acceptance",
      "label": "ARM artifacts publish to GHCR",
      "properties": null
    },
    {
      "id": "acceptance-1",
      "type": "acceptance",
      "label": "build time under 15 min",
      "properties": null
    },
    {
      "id": "acceptance-2",
      "type": "acceptance",
      "label": "x86_64 builds unaffected",
      "properties": null
    },
    {
      "id": "constraint-0",
      "type": "constraint",
      "label": "do not modify existing x86_64 workflow matrix",
      "properties": null
    },
    {
      "id": "constraint-1",
      "type": "constraint",
      "label": "runner must be ephemeral",
      "properties": null
    },
    {
      "id": "resource-0",
      "type": "resource",
      "label": "working-directory",
      "properties": { "cwd": "/home/dev/infra" }
    },
    {
      "id": "state-0",
      "type": "state",
      "label": "session-title",
      "properties": { "title": "ARM CI runner" }
    },
    {
      "id": "gate-0",
      "type": "gate",
      "label": "resume-gate",
      "properties": {
        "ready": true,
        "scope_sized": true,
        "user_turns": 3
      }
    }
  ],
  "relations": [
    {
      "source": "intent-0",
      "target": "acceptance-0",
      "type": "verified_by",
      "provenance": {
        "corpus": "claude-code",
        "source_id": "claude-session-007"
      }
    },
    {
      "source": "intent-0",
      "target": "acceptance-1",
      "type": "verified_by",
      "provenance": {
        "corpus": "claude-code",
        "source_id": "claude-session-007"
      }
    },
    {
      "source": "intent-0",
      "target": "acceptance-2",
      "type": "verified_by",
      "provenance": {
        "corpus": "claude-code",
        "source_id": "claude-session-007"
      }
    },
    {
      "source": "intent-0",
      "target": "constraint-0",
      "type": "bounded_by",
      "provenance": {
        "corpus": "claude-code",
        "source_id": "claude-session-007"
      }
    },
    {
      "source": "intent-0",
      "target": "constraint-1",
      "type": "bounded_by",
      "provenance": {
        "corpus": "claude-code",
        "source_id": "claude-session-007"
      }
    },
    {
      "source": "intent-0",
      "target": "gate-0",
      "type": "asserts",
      "provenance": {
        "corpus": "claude-code",
        "source_id": "claude-session-007"
      }
    }
  ],
  "provenance": { "corpus": "claude-code", "source_id": "claude-session-007" }
}
```

**Notes vs. the other examples:**

- **No `criteria` entity** — this session had no contract bundle, so the
  compiler correctly omits it. Consumers MUST NOT assume one exists.
- The `relations` array has no `requires` edge as a result.

**Conformance check:** see
[`conformance/fixtures/arm-ci-runner-007.okf.json`](./conformance/fixtures/arm-ci-runner-007.okf.json).

---

## 5. Minimal session (empty acceptance, no contract)

**Source:** a brand-new user opens the app, types one sentence, and quits.
The intent extractor can pull a goal from the single user turn, but no
acceptance signals or constraints surface.

**Input messages:**

```text
USER: I want to add dark mode to my dashboard.
```

**Expected OKF:**

```json
{
  "okf": "1.0",
  "source_id": "forge-minimal-042",
  "entities": [
    {
      "id": "intent-0",
      "type": "intent",
      "label": "add dark mode to my dashboard",
      "properties": { "user_turn_count": 1 }
    }
  ],
  "provenance": { "corpus": "forge", "source_id": "forge-minimal-042" }
}
```

**Notes:**

- `relations` is **omitted entirely** (per §5: omitted when empty).
- Only one entity (the intent). No acceptance, no constraint, no context,
  no contract, no gate.
- Consumers MUST tolerate documents with exactly one entity.

**Conformance check:** see
[`conformance/fixtures/minimal-session-042.okf.json`](./conformance/fixtures/minimal-session-042.okf.json).

---

## 6. Multi-intent session (2 intents in one OKF)

**Source:** a session where the user switches topics mid-conversation. The
heuristic intent extractor identifies two distinct goals. SessionLedger v1.x
does NOT split multi-intent sessions into multiple OKF documents; the
entire session is one OKF with multiple `intent` entities.

**Input messages** (truncated):

```text
USER: Fix the login timeout AND update the auth docs while you're at it.
ASSISTANT: OK. Login TTL bumped, docs updated.
USER: Tests pass, ship it.
```

**Expected OKF:**

```json
{
  "okf": "1.0",
  "source_id": "forge-multi-088",
  "entities": [
    {
      "id": "intent-0",
      "type": "intent",
      "label": "Fix the login timeout",
      "properties": { "user_turn_count": 1 }
    },
    {
      "id": "intent-1",
      "type": "intent",
      "label": "Update the auth docs",
      "properties": { "user_turn_count": 1 }
    },
    {
      "id": "acceptance-0",
      "type": "acceptance",
      "label": "Tests pass",
      "properties": null
    },
    {
      "id": "constraint-0",
      "type": "constraint",
      "label": "do not change public API",
      "properties": null
    }
  ],
  "relations": [
    {
      "source": "intent-0",
      "target": "acceptance-0",
      "type": "verified_by",
      "provenance": { "corpus": "forge", "source_id": "forge-multi-088" }
    },
    {
      "source": "intent-1",
      "target": "constraint-0",
      "type": "bounded_by",
      "provenance": { "corpus": "forge", "source_id": "forge-multi-088" }
    }
  ],
  "provenance": { "corpus": "forge", "source_id": "forge-multi-088" }
}
```

**Notes:**

- Two `intent` entities, each with their own satellite acceptance / constraint.
- Consumers MUST NOT assume exactly one intent per document.
- Future OKF v1.x versions MAY add cross-intent edges; v1.0 only allows the
  five canonical relation types listed in §5.2 of the spec.

**Conformance check:** see
[`conformance/fixtures/multi-intent-088.okf.json`](./conformance/fixtures/multi-intent-088.okf.json).

---

## 7. Rejected / invalid examples (what NOT to emit)

These shapes MUST NOT be produced by an OKF v1.0 producer. They are listed
here so reviewers can spot them quickly.

### 7.1 Wrong version string

```json
{ "okf": "1", "source_id": "x" }
```

`okf` MUST be `"<major>.<minor>"` (two dot-separated numbers). `"1"` is
rejected.

### 7.2 Relation with unknown source

```json
{
  "okf": "1.0",
  "source_id": "x",
  "entities": [
    { "id": "intent-0", "type": "intent", "label": "foo", "properties": null }
  ],
  "relations": [
    {
      "source": "ghost",
      "target": "intent-0",
      "type": "verified_by",
      "provenance": { "corpus": "forge", "source_id": "x" }
    }
  ],
  "provenance": { "corpus": "forge", "source_id": "x" }
}
```

`source: "ghost"` does not exist in `entities[]`. Reject.

### 7.3 Unknown entity type

```json
{
  "okf": "1.0",
  "source_id": "x",
  "entities": [
    {
      "id": "foo-0",
      "type": "unknown_type",
      "label": "foo",
      "properties": null
    }
  ],
  "provenance": { "corpus": "forge", "source_id": "x" }
}
```

`type: "unknown_type"` is not in the v1.0 entity-type table. A consumer
SHOULD flag this as a warning; a strict conformance harness rejects it.

### 7.4 Relation referencing a target with mismatched provenance

```json
{
  "relations": [
    {
      "source": "intent-0",
      "target": "acceptance-0",
      "type": "verified_by",
      "provenance": { "corpus": "codex", "source_id": "WRONG_SESSION" }
    }
  ]
}
```

The relation's `provenance.source_id` MUST equal the document's
`source_id` in v1.0 (per §6.3 — relation provenance is cloned from the
document). Future versions may add per-relation provenance fields, but in
v1.0 a mismatch is a conformance error.

### 7.5 Patch component

```json
{ "okf": "1.0.1", ... }
```

There is no patch component in OKF versions. Reject.

---

## 8. Where to find live examples in the wild

- **sl-daemon output** — `sl-daemon serve --once` writes
  `<source_id>.okf.json` into the configured `--out` directory. Any session
  you have lying around becomes a real OKF sample.
- **Conformance corpus** — [`conformance/fixtures/`](./conformance/fixtures/)
  contains the canonical, hand-vetted examples used by the conformance test
  suite. These are the SAME documents shown above (sections 2-6), committed
  to the repo as fixtures so consumers can run them through their own
  parsers and diff the output.
- **sl-viewer demo** — `cargo run -p sl-viewer` ships with three mock
  bundles that compile to OKF-equivalent shapes internally (the viewer uses
  `ContinuationBundle`, not OKF, but the shape is the same). Useful for
  end-to-end demos without needing real agent sessions.

---

_End of OKF Worked Examples._
