# SETUP_STEPS.md

Run these commands to initialize the repository locally and publish to GitHub. The scaffold agent does NOT run these — the sandbox denies public-repo creation (per #67 lesson).

```
cd /Users/kooshapari/CodeProjects/Phenotype/repos/phenotype-infra
git init -b main
git add .
git commit -m "feat: initial phenotype-infra scaffold — 9 ADRs, 4 specs, 10 runbooks, IaC stubs"
gh repo create KooshaPari/phenotype-infra --public --source . --push
```

After the repo is live:

- Verify the license is detected correctly on GitHub (both MIT and Apache-2.0 should show).
- Enable branch protection on `main` (PR required, no force push).
- Configure required Vaultwarden-sourced secrets as GitHub Actions secrets (see `docs/specs/credential-inventory.md`).
- Subscribe Dependabot (already configured in `.github/dependabot.yml`).
