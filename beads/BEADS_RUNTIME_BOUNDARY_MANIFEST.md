# Beads runtime boundary preservation manifest

## Purpose

This commit preserves the runnable Beads source boundary found as loose
workspace files on 2026-08-14. It is preservation evidence only: it does not
claim merge readiness, installed-runtime proof, ledger migration, or release.

## Provenance

- Loose source directory: `/Users/<REDACTED>/CodeProjects/Phenotype/repos/beads`
- Governed parent: `<REDACTED>/pheno-harness`
- Parent base: `21a4e4353bd16132214384ce1377a5455a9a6ef9`
- Preservation branch: `chore/preserve-beads-runtime-boundary-20260814`

## Included source hashes (SHA-256)

| Path | SHA-256 |
|---|---|
| `beads/bead-ctl.sh` | `8d10df3793324878fdd8306ef9d351f84a14ed0c2e519aead20768ef537a2f05` |
| `beads/agileplus_adapter.py` | `1c7f2ceb379700f7ebfc50b4d4b6aca80cd8ade4e49f9c5cb683ecedd20a2797` |
| `beads/refresh-agileplus-token.sh` | `b25dff74ed5a4893bdf5f62c30f1167792216dd67140778fae36630010f161c5` |
| `beads/bead-cockpit.py` | `1120b70c65475f3d1f7af7bbaae03a070dea2f8f768301a9414f73a80d8af26a` |
| `beads/tests/test_agileplus_adapter.py` | `077a9ac4f673ad38176b1070d04cbacc9adf94d18839bdc7470fbf599eb2961b` |
| `beads/tests/test_cockpit_traceability.py` | `c9b52a080f152a81fa6b26d2ddeb1a4270a8ca5cdeb66c80bea259e06095d2cb` |

## Explicit exclusions

- External canonical ledger reference only:
  `/Users/<REDACTED>/CodeProjects/Phenotype/repos/phenotype-dag/beads.jsonl`
  (known SHA-256 prefix `675db341`). Ledger contents were not read, copied,
  staged, or committed.
- `~/.agileplus/config.json` and all tokens are excluded.
- `.beads.lock` is generated runtime state and is excluded.

## Verification and follow-up boundary

Python compilation and the cockpit traceability contract verify the preserved
source files. The adapter's copied unit test is intentionally not interpreted
as package integration proof: pheno-harness already has a package directory
named `beads/agileplus_adapter/`, which shadows the loose single-file module.
Resolving that namespace boundary and restoring the external ledger/configured
endpoint are separate, reviewable integration and dogfood gates.
