# Absorption manifest moved

The absorption manifest for this repo lives at
[`docs/absorbed-from-zz-zz-agentcheck-PhenoTooling/ABSORPTION.md`](./absorbed-from-zz-zz-agentcheck-PhenoTooling/ABSORPTION.md).

The directory is named after the repository's **actual** name. The repo was
renamed from `KooshaPari/PhenoTooling` to `KooshaPari/zz-zz-agentcheck-PhenoTooling`
during the `zz-zz-agentcheck-*` quarantine pass; the old name still redirects.

`bin/repo-delete-gate.sh` derives the manifest path from the repository name, so
the manifest has to sit under the real name for gate (a) to pass.
