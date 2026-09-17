# Fork rationale — {{PROJECT_NAME}}

## Fork status

**Is fork:** {{yes|no}}

---

## If `no` (default for genesis-scaffolded repos)

This repository is **not a fork** of upstream open source. No upstream divergence analysis is required.

If charter or OKF later marks `fork: true`, replace this entire file per [HexaKit docs/genesis/SOTA_SPEC.md](https://github.com/KooshaPari/HexaKit/blob/main/docs/genesis/SOTA_SPEC.md).

---

## If `yes` — complete all sections below

### 1. Upstream identity

| Field | Value |
|-------|-------|
| Upstream URL | {{UPSTREAM_URL}} |
| Version / commit pinned | {{VERSION_OR_SHA}} |
| Last sync date | {{DATE}} |
| License (upstream) | {{LICENSE}} |
| License (this fork) | {{LICENSE}} |

### 2. Why fork (blockers in upstream)

| Blocker | Detail | Upstream issue/PR |
|---------|--------|-------------------|
| {{BLOCKER_1}} | {{DETAIL}} | {{LINK}} |
| Governance / maintainer responsiveness | … | … |
| Missing feature required by intent | … | … |
| License incompatibility | … | … |

Cite [intent.md](../../../intent.md) goals that upstream cannot satisfy.

### 3. Why prefer this fork over upstream

| Criterion | Upstream | This fork | Winner |
|-----------|----------|-----------|--------|
| Feature {{X}} | … | … | fork |
| Governance / merge latency | … | … | … |
| Security patch cadence | … | … | … |
| Phenotype integration (AX, OKF, review) | … | … | fork |
| Community / ecosystem size | … | … | upstream |

**Summary:** {{ONE_PARAGRAPH — no hand-waving; user discussions and issue links}}

### 4. Evangelism and divergence policy

| Change type | Policy | Justification |
|-------------|--------|---------------|
| Bugfix applicable upstream | Open PR upstream first | reduce drift |
| Phenotype-specific integration | Keep in fork | out of upstream scope |
| {{DIVERGENCE}} | {{POLICY}} | {{JUSTIFICATION}} |

### 5. Merge-back criteria

Fork could dissolve or rebase when:

- [ ] Upstream merges blockers {{LIST}}
- [ ] Divergence count below {{N}} files / {{M}} LOC
- [ ] Intent goals achievable on upstream without charter conflict
- [ ] Security and cost dimensions favor upstream per [cost.md](cost.md)

Until then, update [alternatives.md](alternatives.md) fork row on each major divergence.
