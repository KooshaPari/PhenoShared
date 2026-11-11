# AgilePlus bootstrap

`agileplus.db` is generated local state and is intentionally ignored by Git.
Recreate it from the repository root with:

```powershell
.\agileplus\seed.ps1
```

The released seeder currently installs its bundled requirement catalogs. It
does not import `docs/functional_requirements.md` or create a SessionLedger
project. See [`docs/ops/AGILEPLUS.md`](../docs/ops/AGILEPLUS.md) for the
SessionLedger mapping, listing workflow, and optional GitHub sync.
