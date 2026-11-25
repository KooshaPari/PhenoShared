# SOTA.md + docs/sota/

State-of-the-art documentation argues **this implementation is the best chosen option** against researched alternatives — not merely "we built X." SOTA is a living research record, not a one-time README boast.

**AgilePlus trace:** FR-GENESIS-006 (dimensional optimality documentation per repo)

Bootstrap: [`templates/genesis/SOTA.md`](../../templates/genesis/SOTA.md), [`templates/genesis/docs/sota/`](../../templates/genesis/docs/sota/)

## Root: `SOTA.md`

Executive summary for humans and agents. Must fit on one screen.

### Required content

1. **Last researched** date and **methods** (GitHub, papers, HN, vendor docs, dogfood)
2. **Executive summary table** — all dimensions
3. **Why optimal for our constraints** — ties to `intent.md` goals and `charter.md` scope
4. **Fork status** — yes/no + link to `fork-rationale.md`
5. **Evolution triggers** — when to re-open research
6. **Linkage** — charter, review, intent

### Executive summary table

| Dimension | Our choice | Confidence | Deep dive |
|-----------|------------|------------|-----------|
| Technical | … | high/med/low | [technical.md](docs/sota/technical.md) |
| DX | … | … | [dx.md](docs/sota/dx.md) |
| UX | … | … | [ux.md](docs/sota/ux.md) |
| AX (agent UX) | … | … | [ax.md](docs/sota/ax.md) |
| Security | … | … | [security.md](docs/sota/security.md) |
| Ops | … | … | [ops.md](docs/sota/ops.md) |
| Cost | … | … | [cost.md](docs/sota/cost.md) |

Master index: [alternatives.md](docs/sota/alternatives.md)

## Dimensional files (`docs/sota/`)

Each dimension file follows the same structure (see templates):

| File | Dimension |
|------|-----------|
| [technical.md](../../templates/genesis/docs/sota/technical.md) | Architecture, algorithms, performance, stack |
| [dx.md](../../templates/genesis/docs/sota/dx.md) | Developer experience, CLI, local dev loop |
| [ux.md](../../templates/genesis/docs/sota/ux.md) | End-user experience (N/A for infra-only repos) |
| [ax.md](../../templates/genesis/docs/sota/ax.md) | Agent experience — Cursor, forge, Codex, Claude |
| [security.md](../../templates/genesis/docs/sota/security.md) | Threat model, compliance, secret handling |
| [ops.md](../../templates/genesis/docs/sota/ops.md) | CI/CD, deploy, observe, maintain |
| [cost.md](../../templates/genesis/docs/sota/cost.md) | Infra, API, maintenance, duplicate governance cost |
| [alternatives.md](../../templates/genesis/docs/sota/alternatives.md) | Master comparison index across dimensions |
| [fork-rationale.md](../../templates/genesis/docs/sota/fork-rationale.md) | Required if fork; stub if not |

### Per-dimension structure

#### 1. Use case framing

What user/job story this dimension serves. Link to FR IDs if AgilePlus defines them.

#### 2. Requirements (weighted)

| Requirement | Weight |
|-------------|--------|
| … | must / should / nice |

Weights drive verdict — "must" failures reject alternatives.

#### 3. Alternatives considered

| Alternative | Type | Pros | Cons | Verdict |
|-------------|------|------|------|---------|
| Upstream X | OSS | … | … | rejected — reason |
| Vendor Y | closed | … | … | rejected — reason |
| **Our choice** | … | … | … | **chosen** |

Minimum **three** alternatives per dimension where applicable (OSS + commercial where relevant).

Sources: GitHub activity, issues, benchmarks, team experience, user discussions.

#### 4. Chosen strategy

What we implemented and why it wins **for our constraints** (charter scope + intent goals).

#### 5. Evolution triggers

When to re-open research (upstream ships feature, cost threshold, new agent tool).

## AX (agent experience) dimension

Unique to Phenotype org — document how **Cursor / forge / Codex / Claude** agents interact with this repo:

- Context files read order (charter → review → intent → SOTA)
- Skills and hooks (`.cursor/skills/`, forge-fanout)
- Session log locations for intent scrape
- Failure modes (branch wars, lockfile conflicts, scope creep) and mitigations
- Subagent → forge `-p` orchestration when applicable

## Fork repos: `docs/sota/fork-rationale.md`

Required when `fork: true` in charter or OKF. Replace template stub entirely.

1. **Upstream identity** — URL, version pinned, last sync commit/date
2. **Why fork** — blockers in upstream (governance, missing features, license, maintainer responsiveness)
3. **Why prefer this fork** — detailed comparison table vs upstream (not hand-waving)
4. **Evangelism / divergence policy** — what we upstream vs keep local; justify each divergence
5. **Merge-back criteria** — conditions under which fork could dissolve or rebase

Non-fork repos: keep short attestation pointing to this spec (see template).

## Research methods (document in SOTA.md)

Acceptable evidence:

- Public GitHub repos (stars, commit frequency, issue response time)
- Vendor documentation and pricing pages
- Academic papers and benchmarks (cite URL/DOI)
- HN, Reddit, Discord threads (link, date)
- Internal dogfood and incident postmortems

Unacceptable:

- "Industry best practice" without named alternative
- Verdict without rejection reason for runner-up

## Linkage and enforcement

| Artifact | Role |
|----------|------|
| `review.md` | Agents **Block** PRs violating documented SOTA without ADR |
| `charter.md` | Scope limits which alternatives are in-bounds |
| `intent.md` | User goals define what "optimal" means for this product |
| `okf/manifest.okf.yaml` | Indexes all dimension paths for agent retrieval |

PRs introducing new dependencies must update **security** + relevant dimension + row in **alternatives.md**.

## HexaKit genesis examples

Reference implementation (filled, not template placeholders):

- [`docs/sota/technical.md`](../sota/technical.md) — templates vs Cookiecutter/Copier/Backstage
- [`docs/sota/cost.md`](../sota/cost.md) — 9× Kit repos vs genesis + SDK split

## Related specs

- [STANDARD.md](STANDARD.md)
- [REVIEW_SPEC.md](REVIEW_SPEC.md) — SOTA alignment checks
- [OKF.md](OKF.md) — `dimensions` map
