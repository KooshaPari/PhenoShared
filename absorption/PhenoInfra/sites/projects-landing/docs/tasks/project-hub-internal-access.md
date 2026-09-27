# Project Hub Internal Access Task

## Status

In progress.

## Requirement

When `projects.kooshapari.com` is opened from a device on the Phenotype org network,
Tailscale, MagicDNS, or a local development host, the hub should reveal additional
internal options for local development portals and operational views. The public
internet view should not expose those links by default.

## Acceptance Criteria

- The hub uses the GMK Arch teal root color (`#7ebab5`) as the primary accent.
- Public users see the normal project catalog without internal links.
- Devices on trusted local contexts (`localhost`, `127.0.0.1`, `.local`, `.ts.net`,
  `.tailnet`, or `100.64.0.0/10`) see local portal links.
- A local operator can force the internal panel for testing with
  `?internal=1` or `localStorage.setItem("phenotype_internal", "1")`.
- Links must point only to local or tailnet destinations and must not embed secrets.
- Vercel remains the canonical production deployment for `projects.kooshapari.com`.
- GitHub Pages has a complete build and deploy workflow as a governance mirror.

## Follow-Up Work

- Add an authenticated internal status endpoint when the hub gets a server-side edge
  layer. Static browser heuristics cannot prove Tailscale membership without a probe.
- Replace localhost defaults with canonical tailnet service names when they are
  standardized in `phenotype-infra`.
- Add visual regression coverage for the public and internal panel states.
