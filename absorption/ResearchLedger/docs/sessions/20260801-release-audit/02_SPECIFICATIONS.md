# Specifications and ARUs

## Acceptance criteria

- Imported source has stable ID, canonical path, content hash, source URI, and provenance.
- Re-import is idempotent and repairs provenance without duplicating documents.
- Browser resources in source and packaged app are identical.
- A+ is withheld until reference fetching, structured distillation, retrieval hardening,
  and authenticated installed-app smoke are evidenced.

## Assumptions, risks, uncertainties

- Assume Tauri + SQLite + Markdown remains the local-first boundary.
- Risk: provider DOM changes can break capture; mitigate with fixtures and bounded selectors.
- Risk: hosted models leak private research; default to local providers and explicit opt-in.
- Uncertainty: LinkedIn account capture has not been run in this release pass.
