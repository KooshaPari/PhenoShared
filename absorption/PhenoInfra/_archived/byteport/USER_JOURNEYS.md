# BytePort — USER_JOURNEYS.md

This file traces the three core user-facing flows of BytePort from the
outside in: who is doing what, which surface they touch, and which
functional requirement and code path they exercise. It complements
`FUNCTIONAL_REQUIREMENTS.md` (the "what") and `PLAN.md` (the "when") by
answering "who, in what order, against which components."

Each journey lists:

- **Actor** — the user role that initiates the flow.
- **Trigger** — the event that starts it.
- **Steps** — the concrete sequence of touchpoints, in order.
- **Surface(s)** — UI/CLI/API components the actor sees.
- **Traces To** — functional requirement IDs from `FUNCTIONAL_REQUIREMENTS.md`.
- **Code Path** — the modules that must respond for the journey to succeed.
- **Failure Visibility** — how a broken step surfaces to the actor.

Journey numbering matches the FR prefixes so the two documents cross-link
one-to-one: J1 ↔ FR-MANIFEST / FR-DEPLOY, J2 ↔ FR-DEPLOY (status), J3 ↔
FR-PORTFOLIO.

---

## J1 — Founder Deploys a Project from a Manifest

The first-time flow. A developer (the "founder") authors a single NVMS
manifest at the root of their application repo and runs the BytePort
deploy command. BytePort reads the manifest, validates it strictly,
provisions the AWS resources declared in it, pulls the source from the
referenced Git repo at the specified ref, and surfaces live endpoint
URLs for each service.

- **Actor:** Founder (developer; authenticated via PASETO; sole owner of
  the project record).
- **Trigger:** `byteport deploy` (CLI) **or** `POST /api/deploy` from the
  SvelteKit dashboard, both driven by an `odin.nvms` manifest at the
  repo root.
- **Steps:**
  1. Founder runs `byteport deploy` (or clicks "Deploy" in the web UI).
  2. CLI/UI submits the manifest + project metadata to the Go backend.
  3. Backend validates the manifest against the NVMS schema; on any
     schema error the run aborts with stderr message + non-zero exit
     (FR-MANIFEST-002, FR-CLI-003).
  4. Backend persists a `Project` row via GORM, owner-scoped to the
     caller's UUID.
  5. Backend signs a short-lived NVMS token (PASETO) and POSTs the
     project to the local `nvms` service at `http://localhost:3000/deploy`
     with the token in an `Authorization` cookie.
  6. `nvms` clones the source repo at the manifest-specified branch/ref
     (FR-DEPLOY-004), provisions AWS infra (EC2 / ECS / Lambda per
     manifest), and returns per-service status (FR-DEPLOY-006).
  7. Backend records the resulting `Instance` rows with live endpoints
     and returns them to the caller.
  8. CLI prints the live endpoint URLs to stdout (FR-DEPLOY-005); the
     web UI renders them in the project's status card.
- **Surfaces:** `byteport` CLI; SvelteKit `Deploy` page; Go routes
  `DeployProject`; Go `nvms` service.
- **Traces To:** FR-MANIFEST-001, FR-MANIFEST-002, FR-MANIFEST-003,
  FR-MANIFEST-004, FR-DEPLOY-001, FR-DEPLOY-003, FR-DEPLOY-004,
  FR-DEPLOY-005, FR-DEPLOY-006, FR-CLI-001, FR-CLI-003, FR-CLI-004.
- **Code Path:** `backend/byteport/routes/deployment.go` →
  `backend/byteport/models/projects.go` (GORM save) →
  `backend/byteport/lib/crypto.go` (PASETO token) →
  `backend/nvms` (deploy handler) → AWS SDK calls.
- **Failure Visibility:** Manifest parse/validation errors print to
  stderr and exit non-zero (FR-CLI-003). AWS credential absence fails
  loudly at the SDK client init, not silently. Failed service
  provisions are reported per-service in the response (FR-DEPLOY-006)
  rather than collapsing the whole deploy into a single error.

---

## J2 — Founder Checks Deployment Status

The recurring flow. A founder has already deployed (J1) and wants to
know "is my project live, and what are the endpoints right now?" This
flow exercises the read paths only — no provisioning, no LLM, no
deploy.

- **Actor:** Founder (authenticated; owner-scoped).
- **Trigger:** `byteport status` (CLI) **or** opening the project page
  in the SvelteKit dashboard, **or** `GET /api/projects/:id/instances`.
- **Steps:**
  1. Founder runs `byteport status <project>` or navigates to the
     project's status page in the web UI.
  2. Backend authenticates the request (PASETO middleware) and loads
     the caller's `User` record.
  3. Backend queries `Project` rows where `owner = caller.UUID` and
     runs each through `AfterFind` to hydrate related fields.
  4. For each project, backend queries the `Instance` table for live
     endpoints associated with that project/owner.
  5. Backend returns the per-service status and endpoint URLs.
  6. CLI prints a per-service health + endpoint table
     (FR-CLI-002, FR-DEPLOY-006). The web UI renders the same data as
     status cards on the project page.
- **Surfaces:** `byteport status` CLI; SvelteKit project page; Go
  routes `GetProjects`, `GetInstances`.
- **Traces To:** FR-DEPLOY-002, FR-DEPLOY-005, FR-DEPLOY-006,
  FR-CLI-002.
- **Code Path:** `backend/byteport/routes/projects.go` →
  `backend/byteport/models/projects.go` (`AfterFind`) →
  `backend/byteport/routes/instances.go` →
  `backend/byteport/models/instances.go`. Frontend: `frontend/web/src`
  status components.
- **Failure Visibility:** A project with no instances renders an
  explicit "no deployments yet" empty state, not a 500. Auth failures
  return 401 with a clear message. Stale endpoints (instance row
  present but AWS resource gone) are flagged with a `stale: true` flag
  rather than silently dropped.

---

## J3 — Portfolio Site Renders a Deployed Project

The showcase flow. A visitor (anonymous or authenticated viewer) lands
on the BytePort portfolio site and browses the founder's deployed
projects. BytePort renders a per-project page from a generated template
that includes the live endpoint, an interactive widget for the
deployed app, and an LLM-assisted description.

- **Actor:** Visitor (typically unauthenticated; reads the public
  portfolio). May also be the founder previewing their own card.
- **Trigger:** Navigating to a portfolio project page
  (`/p/:projectSlug`) in the SvelteKit frontend, or hitting the
  portfolio render endpoint directly.
- **Steps:**
  1. Visitor opens the portfolio URL.
  2. SvelteKit route loads the project's `Project` and `Instance`
     rows from the Go backend.
  3. Backend reads the generated template for the project from
     `frontend/web/src` (or template store), which already includes
     the live endpoint URL embedded at generation time
     (FR-PORTFOLIO-002).
  4. The template renders an interactive widget — currently a Svelte
     component that proxies live API calls to the deployed service
     (FR-PORTFOLIO-003).
  5. The description block is the LLM-generated copy produced when the
     project was first deployed (FR-PORTFOLIO-004). The LLM backend
     is pluggable: OpenAI in prod, LLaMA in self-hosted
     (FR-PORTFOLIO-005).
  6. Visitor interacts with the widget; the widget proxies requests
     to the live endpoint. Errors from the proxied service surface in
     the widget UI, not as a 500 on the portfolio page itself.
- **Surfaces:** SvelteKit portfolio routes; Go routes serving project
  template + instance data; LLM backend (OpenAI / LLaMA).
- **Traces To:** FR-PORTFOLIO-001, FR-PORTFOLIO-002, FR-PORTFOLIO-003,
  FR-PORTFOLIO-004, FR-PORTFOLIO-005.
- **Code Path:** `frontend/web/src/routes/p/[slug]/+page.svelte` →
  `backend/byteport/routes/projects.go` (template + instance lookup)
  → `backend/byteport/lib/llm.go` (template text generation, pluggable
  backend) → live endpoint via widget proxy.
- **Failure Visibility:** A missing LLM backend fails loudly at deploy
  time (J1), not silently at render time. A dead live endpoint renders
  an explicit "endpoint unreachable" badge in the widget, with the
  last-known good status preserved so the page never goes blank. Stale
  templates fall back to the plain endpoint-card layout rather than
  rendering nothing.

---

## Cross-Journey Notes

- **Auth boundary:** J1 and J2 require an authenticated owner; J3 is
  publicly readable but read-only. The PASETO middleware enforces this
  in `backend/byteport/lib/crypto.go` and is reused across routes.
- **Single source of truth:** Both J2 (status) and J3 (portfolio) read
  from the same `Instance` table populated by J1 (deploy). There is no
  separate "portfolio state" — a deploy that succeeds in J1
  automatically appears in J2 and J3.
- **No silent degradation:** All three journeys rely on FR-CLI-003's
  loud-failure contract. A deploy, status check, or portfolio render
  that cannot complete returns an explicit error to the actor, with
  enough context (which step, which resource) to act on.

## Journey → FR → Test Traceability

| Journey | FR IDs | Existing test trace | Notes |
|---------|--------|---------------------|-------|
| J1 founder deploy | FR-MANIFEST-001..004, FR-DEPLOY-001/003/004/005/006, FR-CLI-001/003/004 | `tests/smoke_test.rs` (harness, FR-ORG-AUDIT-2026-04-001); `backend/byteport/smoke_test.go` (harness, FR-CI-FLOOR) | No journey-specific test yet; smoke tests only prove the harness. |
| J2 status check | FR-DEPLOY-002/005/006, FR-CLI-002 | Same smoke tests | No journey-specific test yet. |
| J3 portfolio render | FR-PORTFOLIO-001..005 | Same smoke tests | No journey-specific test yet; LLM and widget paths are uncovered. |

The smoke tests above are harness-floor tests, not journey tests —
they are deliberately not re-tagged with journey IDs to avoid claiming
coverage the harness tests do not provide. Adding per-journey tests
is a follow-up; they would need fixture-backed GORM setup, an
AWS-mock layer, and a stubbed LLM backend, which is out of scope for
this minimal change.
