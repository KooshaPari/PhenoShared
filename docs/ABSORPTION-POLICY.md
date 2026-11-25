# Absorption policy

Standing rules for consolidating `KooshaPari` repositories into `PhenoShared`
(public code) and `PhenoRegistry` (private data). These come from the operator
and override earlier practice in this ledger. Where an earlier wave did
something different, these rules win from here on.

## 1. Never delete a fork

**Do not delete forks.** A mistake there is not easily reversed.

An earlier pass deleted eleven `zz-aa-dep-*` forks after preserving every ref.
That should not have happened. The preservation is real and complete - 2,950 refs
under `refs/preserved/` in the registry, verified name by name and sha by sha -
so all eleven are recoverable, but the repos should not have been removed in the
first place.

If a fork must be retired, **archive it** (`gh repo archive`) rather than delete.
Archiving keeps history, refs and the fork relationship, and is reversible with
`gh repo unarchive`.

Deleting a non-fork still requires the preconditions below.

## 2. Notify the owning agent before absorbing

Before a repository's content is moved, its owning agent must be told, so the
agent can move with it instead of continuing to work against a source that is
being drained.

Use the `herdr` API to identify the active agent working on that repository and
inform it that the content is moving to `PhenoShared` / `PhenoRegistry` and any
other applicable absorb target. This applies to **every** repository being
absorbed, not only the ones listed for a particular wave.

## 3. Safety bundle first

Before any destructive or irreversible step, the repository gets a bundle
pushed to the private registry (or to `PhenoShared` where the content is public).
The bundle is a safety net, not the integration.

## 4. Semantic integration, not a plop

Absorption means a real merge: the content is placed where it belongs, made
consistent with its destination, and checked. Copying a tree into `absorption/`
and calling it done is not absorption.

Forensic analysis for agent-driven commit regression or history rewrite issues
has already been done for the affected repositories, so the remaining work is
the proper semantic integration and merge.

## 5. Where things go

- Public code -> `PhenoShared`
- Private data, credentials, host addressing, exports -> `PhenoRegistry`
- A repository may legitimately need both.

## 6. Scope

Any repository not explicitly named in a given instruction, but still active, is
a **valid absorb target**. Exceptions are named explicitly per wave.

## 7. Permanent exceptions

- The recovery stores (`*-rb-archive-*`, `*-archive-<date>`, `*-archives-*`,
  `work-archive-*`, `exports-temp-archive-*`) stay. See
  [`RECOVERY-STORES.md`](absorption-ledger/RECOVERY-STORES.md) for why none of
  them is redundant.
- `argis-extensions`, `Substrate`, `Pine` - left as-is.
- `cmux` - see the open question recorded with the current wave.

## 8. Preconditions for deleting a non-fork

All of the following, checked in the same pass:

1. `scripts/verify_absorption.py <repo>` reports complete.
2. History preserved - bundle, or refs under `refs/preserved/`.
3. Issues, pull requests and comments exported to the registry.
4. The owning agent has been notified (rule 2).

`scripts/prepare_deletion.py` enforces 1-3. It never deletes anything itself.
