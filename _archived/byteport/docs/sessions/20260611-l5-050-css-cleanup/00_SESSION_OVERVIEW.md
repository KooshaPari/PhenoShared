# L5-050 CSS Cleanup

## Goal

Remove unused CSS from the frontend worktree without changing active app or Storybook behavior.

## Scope

- Audit frontend stylesheet references.
- Remove dead CSS assets with no import or runtime usage.
- Validate the frontend still passes its local checks.

## Outcome

- Removed six unused theme asset stylesheets from `frontend/web/src/assets/css/`.
- Left active application and Storybook styles unchanged.
