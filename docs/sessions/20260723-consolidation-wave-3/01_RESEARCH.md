# Research

The cloud-gap scan covered 37 top-level local Git repositories. High-priority local-ahead candidates
are OmniRoute, AgilePlus, Civis, PhenoObservability, SessionLedger, forgecode, phenotype-tooling,
portage, and thegent. Dirty checkouts were not cleaned or reset.

| Repository | Evidence | Action |
|---|---|---|
| Civis | local main 56 ahead/3 behind; 9 dirty workflows; gitleaks clean | namespaced push completed |
| OmniRoute | 65 local heads; 23 local-only commits; gitleaks clean | 65 namespaced refs pushed |
| AgilePlus | dirty route diff + untracked 3.2 MB payload; 1 stash; 2076 local commits | Airlock snapshot; hold push |
| PhenoObservability | local ahead history and dirty signal | preserve before audit |
| SessionLedger | local ahead history and dirty signal | preserve before audit |

Canonical owners remain governed by `BOUNDARY_OWNERS.md`; preservation is not absorption.

