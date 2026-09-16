# charter.md specification

`charter.md` locks **scope** and **governance** for a repository. It is the contract between humans, maintainers, and automated agents. On conflict with informal README claims, **charter wins**.

**AgilePlus trace:** FR-GENESIS-003 (scope attestation per repo)

Bootstrap template: [`templates/genesis/charter.md`](../../templates/genesis/charter.md)

## Required sections

### 1. Identity

| Field | Required | Notes |
|-------|----------|-------|
| Repository name | yes | Display title at H1 |
| Org | yes | Typically `<REDACTED>` |
| Lifecycle | yes | `active` \| `archived` \| `genesis-template` |
| One-line mission | yes | Single sentence, user-facing |
| **Boundary class** | yes | See table below |
| Genesis template version | recommended | e.g. `HexaKit templates/genesis/ v1.0.0` |

**Boundary classes**

| Class | Meaning | Example repos |
|-------|---------|---------------|
| `genesis` | Scaffolding, templates, bootstrap docs only | HexaKit |
| `sdk-domain` | Shared libraries (auth, telemetry, MCP) | `phenotype-rust-sdk` (planned) |
| `application` | End-user product logic | Agentora, phenodocs |
| `tooling` | CI wrappers, devtools, linters | phenotype-tooling, KodeVibe |
| `personal-protected` | Solo-owner; relaxed review per org policy | varies |

### 2. Scope

#### In scope

- Bullet list of what this repo **owns**
- Include **FR IDs** where AgilePlus specs define requirements (e.g. `FR-GENESIS-001`)
- Be explicit about template paths, CLI commands, or crate names when applicable

**HexaKit example (genesis class):**

- In: `templates/*`, `hexakit genesis init`, OKF genesis docs, pattern compliance schema stubs
- In: `scripts/extract-intent-prompts.py`, `scripts/scaffold-smoke.sh`
- Out: domain SDK packages, runtime linters, application business logic

#### Out of scope

- Table format preferred: **Boundary** | **Owner repo**
- Link sibling repos that own excluded boundaries
- Prevents agents from "helpfully" adding domain crates to genesis trees

### 3. Governance linkage (mandatory)

`charter.md` must link all genesis artifacts:

| Artifact | Path | Role |
|----------|------|------|
| Intent | `intent.md` | Why we exist; user goals |
| Review | `review.md` | Kilo Code Stand — automated PR contract |
| SOTA | `SOTA.md` | Optimality claims vs alternatives |
| OKF | `okf/manifest.okf.yaml` | Machine-readable index |

Also link to HexaKit spec when bootstrapped from genesis:

```markdown
Specs: [HexaKit docs/genesis/STANDARD.md](https://github.com/<REDACTED>/HexaKit/blob/main/docs/genesis/STANDARD.md)
```

### 4. Decision rights

Document:

| Action | Authority |
|--------|-----------|
| Merge to `main` | maintainer + N reviewers (branch protection) |
| Agent-authored PR | Allowed per `review.md` tiers |
| Scope expansion | Charter amendment + `docs/intent/synthesis.md` update |
| Fork divergence | Requires `docs/sota/fork-rationale.md` |

**Agent autonomy level (0–3)** — define in charter, enforce in `review.md`:

| Level | Meaning |
|-------|---------|
| 0 | Agents may not push; human-only |
| 1 | Agents may open PRs; human merge required |
| 2 | Agents may merge doc-only PRs if CI green |
| 3 | Agents may merge per Kilo Code Stand if all Block rules pass |

Reference: [`review.md#agent-roster`](../../templates/genesis/review.md)

### 5. Dependencies on other boundaries

- Genesis template version pin (`{{HEXAKIT_TEMPLATE_REF}}`)
- SDK imports allowed / forbidden
- Fleet chokepoints — consumers that must repoint if this repo moves or archives
- External services (SonarCloud, GitHub Actions reusable workflows)

### 6. Archive / delete policy

- Absorption target repo if retired
- **100% boundary coverage** requirement before delete (no orphaned capabilities)
- Update `phenotype-registry` and OKF manifest on archive

### 7. Fork clause (if applicable)

If repo is a fork (`fork: true` in OKF or charter metadata):

- Pointer to [`docs/sota/fork-rationale.md`](../../templates/genesis/docs/sota/fork-rationale.md)
- Upstream URL and last sync date
- Merge-back criteria

If not a fork, state explicitly: **Not a fork** — see template `fork-rationale.md` stub.

## Standard charter footer

Every charter ends with:

```markdown
## Changelog
| Date | Change | Author |
|------|--------|--------|

## Attestation
This charter supersedes informal README scope claims. On conflict, charter wins.
```

## Review agent checks

Automated PR agents (Kilo Code Stand) must verify:

1. Changed code/files remain within **In scope**
2. New dependencies appear in relevant `docs/sota/*` dimension
3. Scope expansion PRs include charter amendment section
4. Governance links in charter still resolve (no broken paths)

## Bootstrap checklist

1. Copy `templates/genesis/charter.md`
2. Replace `{{PROJECT_NAME}}`, `{{BOUNDARY_CLASS}}`, `{{MAINTAINER}}`, placeholders
3. Fill in/out scope tables with real sibling repo names
4. Set agent autonomy level consistent with branch protection
5. Add initial changelog row
6. Update `okf/manifest.okf.yaml` `project` block to match

## Related specs

- [STANDARD.md](STANDARD.md)
- [REVIEW_SPEC.md](REVIEW_SPEC.md)
- [SOTA_SPEC.md](SOTA_SPEC.md) — fork rationale
