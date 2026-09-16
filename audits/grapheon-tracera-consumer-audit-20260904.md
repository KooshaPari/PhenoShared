# Grapheon -> Tracera Consumer Audit

**Captured:** 2026-09-04T07:34Z  
**Scope:** current local trees for `Tracera`, `phenotype-registry`, `phenotype-tooling`, `pheno`, and `AgilePlus`  
**Policy:** read-only consumer classification; no source, remote, or runtime mutation

## Method

```text
rg -n -i --hidden --glob '!.git/**' --glob '!docs/**' --glob '!*.md' \
  --glob '!*.jsonl' --glob '!target/**' --glob '!node_modules/**' \
  'KooshaPari/Grapheon|github.com/.*/Grapheon|grapheon.pheno|GRAPHEON_API|TRACERA_API' \
  pheno phenotype-registry phenotype-go-sdk phenotype-python-sdk \
  phenotype-tooling AgilePlus Tracera
```

## Results

| Surface | Finding | Classification | Action |
|---|---|---|---|
| `Tracera/frontend/apps/web/vite.config.mjs:416-418` | Mentions the Rust Grapheon service only to keep it separate from the canonical Tracera gateway; target is `VITE_API_URL` or `127.0.0.1:18000` | Intentional safety boundary | No repoint required |
| `Tracera/scripts/validate-oracle-ports.py:9` and `validate-oracle-compose.py` | Reserves host port 8080 for Grapheon | Intentional collision guard | Preserve invariant |
| `Tracera/docs/sessions/20260722-rich-dashboard-recovery/capability-manifest.json:5` | Records `origin/legacy/grapheon-wip-final-2026-07-17` | Historical snapshot metadata | Do not rewrite historical evidence |
| `phenotype-registry/projects/Grapheon.json` and DSPI-16 | Live identity now points to `KooshaPari/zz-archive-grapheon`; obsolete `pheno` target cleared in commit `0ce5cd12` | Reconciled canonical governance | No further repoint |
| `phenotype-registry/registry/audit-absorption-justification/refresh-cohort-20260726.json` | Records the pre-rename `KooshaPari/Grapheon` remote | Historical audit snapshot | Preserve unchanged; superseded by live DSPI-16 |
| Runtime URL/repository search | No active consumer URL or package import targeting `KooshaPari/Grapheon` was found | No live stale consumer identified | End-to-end usage remains unproven |

## Gate conclusion

The repository-identity repoint is verified for the canonical registry record,
and no active runtime consumer still targets the pre-retirement repository name.
This report does **not** prove Tracera consumption, observability, compliance,
or dogfood behavior; those remain `UNKNOWN` pending a real current-main run and
captured artifacts. It also does not prove the required dual-cloud backup and
independent restore.
