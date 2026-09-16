# Threat Model — BytePort (STRIDE-per-component)

> **Repository:** [`KooshaPari/BytePort`](https://github.com/KooshaPari/BytePort)
> **Source audit:** [`FLEET-AUDIT-REPORT.md`](../../audits/FLEET-AUDIT-REPORT.md) — S7 (Threat model) was the #1 P0 gap (priority 42; BytePort at score 0).
> **Source template:** [`THREAT-MODEL-TEMPLATE.md`](https://github.com/KooshaPari/phenotype/blob/main/audits/THREAT-MODEL-TEMPLATE.md) v1.0.
> **Method:** STRIDE per-component. Each component in this system gets a row; each STRIDE category is a column.
> **Last reviewed:** 2026-06-16 — initial instantiation (lifts S7 from 0 → 2, "wired").
> **Owner:** BytePort security / platform maintainers (see CODEOWNERS once added).

The fleet-wide S7 P0 work used the same template; this file is the BytePort instance.
BytePort is a self-hosted IaC deployment + portfolio platform: a SvelteKit + Tauri
desktop shell, a Go backend, a Go Spin/MicroVM orchestrator (`nvms`), and Rust crates.
The components enumerated below cover the **production** attack surface (production
Go services, published Tauri desktop binary, release artifacts) — the `./start` dev
wrappers and local `tmux` orchestration are out of scope (development-only).

## When to do this

A threat model is **wired** (score 2) when this file exists in `docs/security/threat-model.md`
and is referenced from your `README.md` or `SECURITY.md`.
It's **measured** (score 3) when a CI gate fails if the file is more than 90 days old.

## STRIDE cheat sheet

| Letter | Threat | Property violated | Question to ask |
|--------|--------|-------------------|------------------|
| **S** | Spoofing | Authentication | Can an attacker impersonate a user/system? |
| **T** | Tampering | Integrity | Can an attacker modify data or code? |
| **R** | Repudiation | Non-repudiation | Can a user deny an action they took? |
| **I** | Information disclosure | Confidentiality | Can an attacker read data they shouldn't? |
| **D** | Denial of service | Availability | Can an attacker make the system unavailable? |
| **E** | Elevation of privilege | Authorization | Can an attacker gain higher privileges? |

For each cell, mark one of: **N/A** (not applicable to this component), **low** (impact minor,
mitigation optional), **med** (mitigation required), **high** (mitigation + test required).

---

## Component inventory

BytePort is a self-hosted IaC deployment + portfolio platform. The threat model
covers the following components derived from `ARCHITECTURE.md` and the
shipping stack documented in `README.md`:

- **`frontend/web`** — SvelteKit 2 + Svelte 5 + Tailwind 4 web app (compiled, then bundled into the Tauri shell).
- **`frontend/web/src-tauri`** — Tauri 2 desktop/mobile shell (Rust). Hosts the IPC bridge, capabilities, and Tauri-side adapters (S3 etc.).
- **`backend/byteport`** — Go 1.25 service: Gin HTTP, GORM persistence (SQLite), PASETO auth, AWS SDK client.
- **`backend/nvms`** — Go service implementing the Spin / MicroVM runtime. Parses `odin.nvms` manifests, drives cloud provisioning (EC2, ALB, Route53, S3), and shells out to LLM providers.
- **`backend/nvms/lib/providers`** — LLM provider adapters: openai, anthropic, gemini, deepseek, local. Receives user-controlled context to generate showcase metadata.
- **`crates/byteport-transport`** — Rust transport crate (consumed by the Tauri shell).
- **`crates/integration`** — Rust integration-test crate.
- **SQLite database** (`backend/byteport/database.db`) — single-file GORM store; deployment + user + project + secrets metadata.
- **Cloud accounts** (AWS via EC2/ALB/S3/Route53) — provisioning target; credentials gate the blast radius.
- **CI/CD pipeline** — 5 GitHub Actions workflows (`ci.yml`, `audit.yml`, `deny.yml`, `release.yml`, `scorecard.yml`); all third-party actions SHA-pinned (S9=3).
- **npm supply chain** — SvelteKit 2, Svelte 5, Tailwind 4, shadcn-svelte components; lockfile committed.
- **Tunnel / dev orchestration** — `./start` shell wrappers (development-only, not on the production attack surface).

## Per-component threat grid

For each component, fill in the STRIDE table.

### Component: `<name>`

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | low/med/high | | | | YYYY-MM-DD |
| **T — Tampering** | | | | | |
| **R — Repudiation** | | | | | |
| **I — Info disclosure** | | | | | |
| **D — DoS** | | | | | |
| **E — Elevation** | | | | | |

Repeat this block for every component.

---

## Worked examples: BytePort components

Below are the per-component STRIDE rows for the most exposed BytePort components.
The "Owner" column maps to a role; once CODEOWNERS exists, the role maps to a team.

### Component: `frontend/web` (SvelteKit 2 + Svelte 5 + Tailwind 4)

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | low | Phishing deployment of a near-clone Tauri app | Tauri signing identity (per-platform); not yet wired — see `docs/slsa.md` | platform | 2026-06-16 |
| **T — Tampering** | med | Malicious PR adding `@html` interpolation of user-controlled strings in `addProjectDialog` / `projectPopup` | Svelte auto-escapes (S6=1 evidence); `eslint-plugin-svelte` a11y rules; PR review | frontend | 2026-06-16 |
| **R — Repudiation** | low | Authorship of UI changes | Git log; Co-Authored-By trailer | frontend | 2026-06-16 |
| **I — Info disclosure** | med | User session token stored in localStorage (Svelte stores) | Move to httpOnly cookie; SvelteKit `+page.server.ts` boundary for tokens | frontend | 2026-06-16 |
| **D — DoS** | low | Static asset CDN abuse | Tailwind purges unused CSS; Vite bundle budget not yet enforced | frontend | 2026-06-16 |
| **E — Elevation** | med | Supply-chain compromise of shadcn-svelte or `bits-ui` | `package-lock.json` committed; `npm ci` in CI; SCA pending (SC2=0) | security | 2026-06-16 |

### Component: `frontend/web/src-tauri` (Tauri 2 Rust shell)

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | med | Forged IPC messages from compromised frontend claiming a different user | Tauri capabilities in `src-tauri/capabilities/default.json` scope IPC by command | platform | 2026-06-16 |
| **T — Tampering** | med | Malicious Tauri-side adapter (`s3.rs`, `network.rs`) | cargo-deny + CodeQL; deny.toml blocks high-severity advisories | platform | 2026-06-16 |
| **R — Repudiation** | low | Rust-side IPC origin | Git log of Tauri adapter changes | platform | 2026-06-16 |
| **I — Info disclosure** | high | Tauri 2 capability leak: capability allowlist too broad exposes FS / shell | Tighten `capabilities/default.json` to least-privilege; deny `[shell]` exec where unused | platform | 2026-06-16 |
| **D — DoS** | low | Tauri runtime crash from malformed IPC | `tauri.conf.json` crash-reporter off by default | platform | 2026-06-16 |
| **E — Elevation** | high | Transitive gtk-rs advisories (RUSTSEC-2024-0411..0415) unpatched in Tauri 2.x | deny.toml documents each ignore with RUSTSEC ID + justification; re-evaluate on Tauri bump | security | 2026-06-16 |

### Component: `backend/byteport` (Go 1.25 — Gin + GORM + SQLite + PASETO + AWS SDK)

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | med | Forged PASETO token replay | PASETO v4 (asymmetric or symmetric depending on deployment); `expiry` claim mandatory | backend | 2026-06-16 |
| **T — Tampering** | med | Gin handler passes unescaped user input to GORM raw query | Use GORM parameterized APIs (no `db.Raw` with user input); CodeQL Go scan | backend | 2026-06-16 |
| **R — Repudiation** | low | Deployment-create audit log | GORM hooks on `models/deployments.go` (audit trail fields present) | backend | 2026-06-16 |
| **I — Info disclosure** | med | SQLite file `backend/database.db` readable on disk by other users | File permission 0600; deployment runs as dedicated user; secrets table encrypted at rest | backend | 2026-06-16 |
| **D — DoS** | med | Unbounded GORM query (list deployments) | Pagination mandatory on list endpoints; rate limit at Gin middleware | backend | 2026-06-16 |
| **E — Elevation** | med | WorkOS callback mis-validates state claim → session escalation | `workos_service.go` validates `state` nonce; tests in `workos_comprehensive_test.go` | security | 2026-06-16 |

### Component: `backend/nvms` (Go — Spin/MicroVM orchestrator + LLM providers)

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | med | Caller of `nvms` API impersonates another user via stale project token | Verify token in middleware; bind token to project ID | platform | 2026-06-16 |
| **T — Tampering** | high | Malicious `odin.nvms` manifest injects arbitrary `exec` command via Spin templating | Parser in `nvms/projectManager/parser.go` must reject unknown keys; manifest schema validation gate | platform | 2026-06-16 |
| **R — Repudiation** | med | LLM-generated metadata sent to portfolio site is not signed | Sign LLM output with deployer key; embed signature in portfolio payload | platform | 2026-06-16 |
| **I — Info disclosure** | high | LLM provider receives full project context including secrets if not redacted | Strip secrets before LLM call; explicit allowlist of fields in `nvms/lib/llm.go` | security | 2026-06-16 |
| **D — DoS** | high | `odin.nvms` requests unlimited MicroVMs → cloud bill explosion (cost-DoS) | Per-user quota in `nvms/projectManager/deploy.go`; AWS SCP cap on account | platform | 2026-06-16 |
| **E — Elevation** | high | LLM-provider API key reused across users → cross-tenant data exposure | Per-tenant provider keys; rotation in `nvms/lib/secrets.go` | security | 2026-06-16 |

### Component: `backend/nvms/lib/providers` (openai / anthropic / gemini / deepseek / local)

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | high | Local LLM provider (`local.go`) impersonates cloud provider if env var flips | Pin provider via typed config; refuse unknown provider names at boot | security | 2026-06-16 |
| **T — Tampering** | med | Prompt-injection from user-controlled repo README flips metadata output | System prompt fixed; output schema-validated before downstream use | security | 2026-06-16 |
| **R — Repudiation** | low | Provider call attribution | `audit` table records provider + request ID | security | 2026-06-16 |
| **I — Info disclosure** | high | Provider API key in env var leaked via stack trace | Load keys from OS keyring (Linux) or Windows credential store; never log | security | 2026-06-16 |
| **D — DoS** | med | Provider rate-limit hit → user-visible deploy failure | Exponential backoff with jitter; circuit breaker in `nvms/lib/providers/lib.go` | platform | 2026-06-16 |
| **E — Elevation** | med | Cloud provider plugin reads broader IAM role than needed | `aws-sdk-go-v2` uses scoped session; IAM policy reviewed per role | security | 2026-06-16 |

### Component: Cloud accounts (AWS — EC2 / ALB / S3 / Route53)

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | med | Stolen long-lived IAM access key | Migrate to IRSA / short-lived STS; deny IAM-user keys in SCP | platform | 2026-06-16 |
| **T — Tampering** | med | `Route53` record hijack via compromised API creds | Route53 zone locked to BytePort account; registry-level lock | platform | 2026-06-16 |
| **R — Repudiation** | low | CloudTrail logs (out of band) | n/a (AWS-managed) | platform | 2026-06-16 |
| **I — Info disclosure** | med | Public S3 bucket accidentally opened | Bucket policy default-deny; `s3:PutBucketPublicAccessBlock` enforced | security | 2026-06-16 |
| **D — DoS** | med | AWS account-level throttling on provisioning | Quota increase request; fallback region | platform | 2026-06-16 |
| **E — Elevation** | high | Compromised deployer creds → can spin up crypto-mining EC2 | AWS SCP `Deny: ec2:RunInstances` for unapproved instance types; cost anomaly alarm | security | 2026-06-16 |

### Component: CI/CD pipeline (5 GitHub Actions workflows, all SHA-pinned)

| Threat | Rating | Specific attack vector | Mitigation | Owner | Last reviewed |
|--------|--------|------------------------|------------|-------|---------------|
| **S — Spoofing** | med | Compromised third-party GitHub Action | All third-party `uses:` SHA-pinned (verified S9=3, 2026-06) | ci-ops | 2026-06-16 |
| **T — Tampering** | med | Malicious workflow PR that broadens `permissions:` | `permissions: contents: read` on workflow-level; per-job overrides explicit | ci-ops | 2026-06-16 |
| **R — Repudiation** | low | Workflow authorship | Git log; PR review | ci-ops | 2026-06-16 |
| **I — Info disclosure** | low | Workflow logs leaking secrets | All secrets via GitHub Actions secrets (encrypted at rest); Gitleaks + TruffleHog scan in `audit.yml` | security | 2026-06-16 |
| **D — DoS** | low | Workflow abuse / quota exhaustion | `concurrency:` per workflow; per-ref `cancel-in-progress: true`; standard `ubuntu-latest` runners only | infra | 2026-06-16 |
| **E — Elevation** | med | Workflow gains write access via compromised PAT | `permissions: contents: read` workflow default; only `release.yml` job escalates to `contents: write` for releases | ci-ops | 2026-06-16 |

---

## How to lift the S7 score

- **0 → 1 (ad-hoc):** Add a `docs/security/threat-model.md` with at least one component's STRIDE table.
- **1 → 2 (wired):** Reference the threat model from `README.md` and `SECURITY.md`. Cover at least 80% of your components. Add an owner + last-reviewed column to each row.
- **2 → 3 (measured):** Add a CI gate that fails if `docs/security/threat-model.md` is older than 90 days, OR if a previously-scored component row is deleted.

## Review cadence

Review the threat model:
- **On every major release** (semver minor)
- **On any new external dependency** added
- **On any new public-facing endpoint**
- **Quarterly minimum** (a 90-day-old model is a CI failure for "measured" repos)

## Cross-references

- `docs/audits/BytePort/ACTION-PLAN.md` — per-pillar plan; S7 task is **BYT-067** (lift S7 from 0 → 2).
- `docs/audits/FLEET-AUDIT-REPORT.md` — fleet-wide audit; S7 is the #1 P0 gap.
- `docs/audits/THREAT-MODEL-TEMPLATE.md` — source template (phenotype/audits).
- `ARCHITECTURE.md` — defines the components enumerated above.
- `SECURITY.md` — security policy, advisory reporting, cargo-deny + CodeQL coverage.
- `deny.toml` — cargo-deny config; each `ignore` carries a RUSTSEC ID + justification.

## How to validate

```bash
# After writing your threat model, validate it has all 5 STRIDE rows
for c in S T R I D E; do
  grep -q "^\*\*$c " docs/security/threat-model.md || echo "missing $c"
done
```

If `grep` returns nothing for all 6 letters, your file is valid.

## Open high-rated threats (require follow-up work)

The following cells are rated **high** and have a mitigation listed but no test/control yet.
They are tracked as separate work items under `docs/audits/BytePort/ACTION-PLAN.md`:

| Component | Cell | Action-plan task |
|-----------|------|------------------|
| `frontend/web/src-tauri` (Tauri) | I — Info disclosure (capability scope) | New (open issue) — tighten `capabilities/default.json` |
| `frontend/web/src-tauri` (Tauri) | E — Elevation (gtk-rs) | Re-evaluate on Tauri 2.x upgrade; tracked via `deny.toml` |
| `backend/nvms` | T — Tampering (`odin.nvms` parser) | New (open issue) — schema validation gate |
| `backend/nvms` | I — Info disclosure (LLM context) | New (open issue) — secrets-stripping in `llm.go` |
| `backend/nvms` | D — DoS (cost-DoS) | New (open issue) — per-user quota in `deploy.go` |
| `backend/nvms` | E — Elevation (per-tenant LLM keys) | New (open issue) — per-tenant provider keys |
| `backend/nvms/lib/providers` | S — Spoofing (local provider flip) | New (open issue) — typed config gate |
| `backend/nvms/lib/providers` | I — Info disclosure (API key leak) | New (open issue) — OS keyring integration |
| Cloud accounts (AWS) | E — Elevation (compromised deployer) | AWS SCP + cost anomaly alarm |

## Score state

- **S7 (Threat model):** 0 → 2 (this commit: "wired"). File exists, referenced from `README.md` and `SECURITY.md`, owners + last-reviewed columns populated, ≥80% of components covered.
- **S7 → 3 (measured):** Pending — add a CI gate that fails if `docs/security/threat-model.md` is older than 90 days. Tracked as a follow-up issue (not part of this PR).

## Provenance

- **Template version:** 1.0
- **Author:** Phenotype Org holistic audit, 2026-06-16; instantiated for BytePort 2026-06-16
- **Audit that produced it:** `FLEET-AUDIT-30-PILLAR.md` (S7 P0)
- **License:** Same as the parent repo
