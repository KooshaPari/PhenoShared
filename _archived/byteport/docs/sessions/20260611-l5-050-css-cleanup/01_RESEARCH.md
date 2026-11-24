# Research

## Repo findings

- `frontend/web/src/routes/+layout.svelte` imports `../app.css`.
- `frontend/web/src/routes/home/+layout.svelte` imports `../../app.css`.
- Storybook imports only `button.css`, `header.css`, and `page.css` from their paired story components.
- Repo-wide search found no imports or path references to files in `frontend/web/src/assets/css/`.

## Evidence

- `rg -n "app.css|button.css|header.css|page.css|dark.css|light.css|dark-mc.css|light-mc.css|dark-hc.css|light-hc.css" frontend/web -S`
- `rg -n "src/assets/css|assets/css|light-hc.css|dark-hc.css|light-mc.css|dark-mc.css|light.css|dark.css|md-sys-color-" . -S`

## Decision

Treat the six theme asset CSS files as dead code and remove them. They are not imported by the app, Storybook, or any repo-level document or script.
