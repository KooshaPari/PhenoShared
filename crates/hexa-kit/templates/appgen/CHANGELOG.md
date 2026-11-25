# Changelog

All notable changes to this project will be documented in this file.

## 🐛 Bug Fixes
- Fix: package.json to reduce vulnerabilities (#20)

The following vulnerabilities are fixed with an upgrade:
- https://snyk.io/vuln/SNYK-JS-ESLINT-15102420
- https://snyk.io/vuln/SNYK-JS-INFLIGHT-6095116

Co-authored-by: snyk-bot <snyk-bot@snyk.io> (`fbea853`)
## 📚 Documentation
- Docs(worklog): initialize first-entry bootstrap (`ebaa0b0`)
- Docs(wave-4): scaffold FUNCTIONAL_REQUIREMENTS.md with 6 stubs (`9256992`)
- Docs(fr): scaffold FUNCTIONAL_REQUIREMENTS.md with 3 FR stubs (`6bfa7fb`)
- Docs: mark as archived personal project - STRICTLY DO NOT DELETE NOR UNARCHIVE (`7984581`)
- Docs: add README/SPEC/PLAN (`761b4d6`)
## 🔨 Other
- Chore(ci): adopt phenotype-tooling workflows (wave-2) (`5b60b73`)
- Test(ts): wire vitest runner for smoke test (`47d5ba6`)
- Test(smoke): seed minimal smoke test — proves harness works (`ee235ab`)
- Chore(governance): adopt standard CLAUDE.md + AGENTS.md + worklog (`07eef40`)
- Chore: add AgilePlus scaffolding (`826f686`)
- Ci(legacy-enforcement): add legacy tooling anti-pattern gate (WARN mode)

Adds legacy-tooling-gate.yml monitoring per CLAUDE.md Technology Adoption Philosophy.

Refs: phenotype/repos/tooling/legacy-enforcement/ (`63467fe`)
