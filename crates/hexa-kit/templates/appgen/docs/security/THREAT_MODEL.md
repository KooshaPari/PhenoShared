---
title: "Threat Model"
version: 0.1.0
lastUpdated: 2026-06-16
---

# Threat Model

> **Source of truth:** AppGen (Personal project template for rapid app prototyping)
> **Scope:** Scaffolding templates, generated source files, CLI bootstrap, CI/CD, distribution

## Assets

1. **Scaffolding templates (`templates/`)** — File/directory templates that get copied into new projects. If mutable, an attacker can ship a template that drops a backdoor into every project scaffolded from it.
2. **Generated source files** — Output of `appgen new <name>`. If mutable in transit, an attacker can inject code at generation time.
3. **CLI binary** — Distributed via cargo install. Supply-chain risk: a malicious release substitutes the legitimate binary.
4. **Configuration templates (`templates/.appgen.yml`)** — Default config for new projects. If mutable, can set insecure defaults.
5. **Local dev environment** — Where AppGen runs. Reads `$HOME/.config/appgen/`, `$HOME/.cargo/`, `$HOME/.gitconfig/`. Exfiltration risk if AppGen is malicious.

## Threats (STRIDE)

| Category | Threat | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| **Spoofing** | An attacker publishes a `AppGen` fork under a similar name (e.g., `appgen-cli` vs `AppGen`) and downstream consumers fetch the wrong binary. | Low | Critical | Releases are signed (cosign, keyless). README documents the canonical install command. |
| **Tampering** | A scaffolding template is modified in a release to drop a backdoor into every project generated from it. | Low | Critical | All templates are content-addressed by SHA-256. The release script verifies the template hash matches the registered hash. Templates are reviewed in PRs before merge. |
| **Repudiation** | A contributor pushes a template change and later denies it. | Low | Medium | All commits are signed (gitsign, keyless). Releases are tagged. The git history is the audit trail. |
| **Information Disclosure** | A scaffolding template inadvertently includes a sensitive file (e.g., a `.env` with a test API key). | Medium | Medium | The `appgen new` command has a `redact-output` filter that masks known secret patterns. CI runs `gitleaks` on every PR. The README documents the canonical "no-secrets in templates" rule. |
| **Denial of Service** | A maliciously-named template file (e.g., a 1GB `Cargo.lock` template) causes `appgen new` to OOM. | Medium | Low | The generator enforces `max-file-size=10MB` per template. Files over the limit are skipped with a warning. |
| **Elevation of Privilege** | A scaffolding template uses Jinja2 `{% include %}` with a path the user controls, leading to arbitrary file read. | Low | High | The template engine uses a sandboxed loader that only reads from the bundled `templates/` directory. External paths are not allowed. |

## Residual Risk and Revision Cadence

The most material residual risk is **template compromise** — a malicious change to a single template affects every project scaffolded from it. The strongest available mitigation is the SHA-256 content-addressed template + the review process, but this assumes the review is rigorous. The next highest residual is **CLI binary compromise** — if the upstream release channel is compromised, every consumer of AppGen is affected. This threat model should be revised quarterly (February, May, August, November) or whenever a new template is added, a new generator option is introduced, or the distribution channel changes. The revision trigger is any PR that adds a new template, modifies the template engine, or adds a new CLI flag.
