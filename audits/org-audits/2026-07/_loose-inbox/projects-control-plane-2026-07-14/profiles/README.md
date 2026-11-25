# Phench Profiles

Profiles are named environment overlays applied at run time.

Each file should capture one operational envelope.

Convention:
- `default` should remain minimal and stable.
- branch-specific profiles can be added per target.
- keep secrets out of repo files; use runtime secret injection.
