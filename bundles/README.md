# Git bundles

Full-history bundles of repositories preserved into PhenoShared, as distinct from
`absorption/`, which holds absorbed working trees.

A bundle is not an absorbed tree, and putting one under `absorption/<repo>/` makes
`verify_absorption.py` treat that directory as an incomplete absorption of the
whole repository. `absorption/HeliosLite/` did exactly that and reported
`1560 of 1560 missing` until it moved here.

Each bundle is verified by cloning it back and comparing the full ref map against
the source, not by trusting the file size.

| Bundle | Refs | Namespaces | Commits | Size |
|---|---:|---|---:|---:|
| `HeliosLite.bundle` | 1,061 | heads 303, tags 414, pull 339, keep 2, sources 3 | 4,955 | 96.0 MiB |

The same history is also held privately in `PhenoRegistry` under
`repos/<repo>/history/`, and as namespace-complete refs under
`refs/preserved/<repo>/`. Three copies is deliberate: this one is the copy that
lives with the code, the registry is the backup, and the refs are the form an
agent can fetch and work with directly.
