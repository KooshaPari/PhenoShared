# Implementation Strategy

Use a deletion-only cleanup for the dead asset set in `frontend/web/src/assets/css/`. Avoid touching `app.css` or Storybook CSS because those files are actively imported and already small.
