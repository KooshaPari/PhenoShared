# audit-v38 Scorecard — SessionLedger

**Repo:** KooshaPari/SessionLedger
**Date:** 2026-07-17
**Repo-type profile:** CLI+daemon + desktop (sl-daemon + sl-viewer)
**Auditor:** cursor-w37-reaudit
**Commit audited:** 9845a70 (origin/main / Wave-37 closure #303-#307)

> Rubric SSOT: phenotype-org-audits/audit-v38

## Category Scores

| Cluster | Category | Pillars | Score (sum/max) | Pct | Grade | Notes |
|---------|----------|---------|:---------------:|:---:|:-----:|-------|
| C00 | Architecture + Module | L0-L9 | 29/30 | 97% | A | see audit/.lane-c00 |
| C01 | CI, DX, Observability | L10-L19 | 29/30 | 97% | A | see audit/.lane-c01 |
| C02 | Error handling, API, Governance | L20-L29 | 29/30 | 97% | A | see audit/.lane-c02 |
| C03 | Agent Readiness | L30 | 36/36 | 100% | A | see audit/.lane-c03 |
| C04 | Security | L31-L40 | 27/30 | 90% | A | see audit/.lane-c04 |
| C05 | Observability (deep) | L41-L50 | 30/30 | 100% | A | see audit/.lane-c05 |
| C06 | Supply Chain | L51-L60 | 30/30 | 100% | A | see audit/.lane-c06 |
| C07 | DX, QEng, Portability | L61-L70 | 29/30 | 97% | A | see audit/.lane-c07 |
| C08 | Eval Coverage | L71-L80 | 29/30 | 97% | A | see audit/.lane-c08 |
| C09 | Accessibility + UX | L81-L95 | 45/45 | 100% | A | see audit/.lane-c09 |
| C10 | Visual Identity | L96-L107 | 36/36 | 100% | A | see audit/.lane-c10 |
| C11 | Packaging + Distribution | L108-L122 | 41/45 | 91% | A | see audit/.lane-c11 |

## Overall

**Weighted overall score:** 97% · **Overall grade:** A

(Raw rubric total across all 12 clusters. Sum 390 / 402.)

## Wave-37 Delta

| Cluster | Before | After | Raw delta | Evidence-backed movement |
|---------|:------:|:-----:|:---------:|--------------------------|
| C06 | 29/30 | 30/30 | +1 | Source provenance policy SSOT + SelfCheck (#305); L59 2→3 |
| **Overall** | **389/402 (97% A)** | **390/402 (97% A)** | **+1** | Conservative; one pillar only |

## Headline Findings

- **Strongest:** C03/C05/C06/C09/C10 (100% A); C00/C01/C02/C07/C08 (97% A)
- **Weakest:** C04 (90% A); C11 Packaging (91% A)
- **Wave-36 → Wave-37:** 97% A (389/402) → 97% A (390/402), +1 raw point
- **Held (no score):** #303 blocking shuttle permutation (C00 L7 already pillar max); #304 blocking Miri permutation (C00 L7 already pillar max); #306 reusable hermetic workflow provenance (C06 L53 already pillar max); #307 maintainer 2FA policy SSOT (C04 L36 org enforcement NOT_VERIFIABLE_IN_REPO)
- **Remaining unpaid:** human org 2FA attestation (C04 L36), full protected-environment SLSA Build L3 (C06 L53 residual), live branch-protection signed-commits attestation (C06 L59 residual), Authenticode/notarization (C11 L112), live brew/winget publish, live Alertmanager webhooks, production Pyroscope profiling push, TSan + daemon-graph permutation ports (C00 L7), default-on jemalloc, multi-tenant / auto-ETL PII redaction (C02 L24), in-tree KMS/envelope encryption (C02 L22), Fluent/ICU multi-locale (C01 L16), hard rootless/no-net CI (C04 L40 residual), USE process gauges (C05)

## N/A / soft goals

- Harbor/agent-eval: docs/EVAL_SCOPE.md
- Tray/menubar auto-update: docs/adr/0001-desktop-companion-scope.md
- Mobile presence: docs/adr/0002-mobile-presence.md
- Platform Authenticode/notarization: deferred per docs/adr/0003-platform-code-signing.md
- Serverless/edge deploy: explicit N/A per docs/adr/0005-no-serverless-edge.md
- MCP host provenance: explicit N/A per docs/adr/0006-no-mcp-server.md
