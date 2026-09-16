# Known Issues

- AgilePlus has a modified route file and untracked `PhenoObservability/` payload; it must be
  reconciled before publication.
- OmniRoute local `main` diverges substantially from remote (`1 ahead / 4943 behind`); it was not
  merged or reset. Namespaced heads preserve the evidence.
- `omniroute-wtrees` retains an unresolved historical dirty-orphan signal.
- Existing repository gitleaks configuration contains invalid regex-style allowlist entries; clean
  `/dev/null` configuration was used for evidence scans.
- The repository-wide ecosystem validator still reports unrelated metadata drift and an unreachable
  `dispatch-mcp` entry.
- Forgecode’s configured `origin` is `tailcallhq/forgecode`; the local Airlock push was denied.
  The snapshot was preserved to KooshaPari’s `fork` namespace, with no force-push or remote rewrite.
