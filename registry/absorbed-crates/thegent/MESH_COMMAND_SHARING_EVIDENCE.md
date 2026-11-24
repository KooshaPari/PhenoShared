# thegent Mesh Command-Sharing Evidence

## Scope

This entry records implementation evidence for the two mesh commits below. It
does not change or reinterpret any manifest-preservation references.

| Commit | Change | Status |
|---|---|---|
| `2b3cb89d8` | Adds command-sharing contracts (`Command`, query validation, mesh events, queue port) and contract tests | implemented |
| `a1609033f` | Routes the CLI through `CommandShareService`, adds service coverage, and extends the boundary-drift check | implemented |

## Focused verification

The focused lane passes with plugin autoload disabled and the repository
configuration boundary limited to `tests/`:

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest --confcutdir=tests -q \
  tests/mesh/test_command_share_contracts.py \
  tests/mesh/test_command_share_service.py \
  tests/test_sharecli_boundary_drift_check.py
```

Result: **16 passed** in 2.03s. The two commits contribute **14 new tests**
(five contract tests, one service test, and eight boundary-drift tests); the
remaining two are pre-existing service coverage in the same focused files.

```sh
ruff check \
  src/thegent/mesh/cli.py \
  src/thegent/mesh/command_share.py \
  src/thegent/mesh/contracts.py \
  tests/mesh/test_command_share_contracts.py \
  tests/mesh/test_command_share_service.py \
  tests/test_sharecli_boundary_drift_check.py
```

Result: **clean**. Ruff reports only that deprecated/removed rule names in the
repository configuration (`E999`, `ANN101`, `ANN102`) are ignored; no lint
violations occur in the touched implementation or tests.

## Environment caveat

The ordinary `pytest` entrypoint is currently blocked before collection on the
host Python 3.13 environment. The repository `conftest.py` declares
`pytest_ignore_collect(path: pathlib.Path, ...)`, while the installed pytest
hook specification no longer exposes `path`, producing a `PluginValidationError`.
This is an environment/tooling compatibility issue, not a failure of the
focused mesh tests. Re-run the broader suite after aligning pytest and the
repository hook signature; do not claim full-suite parity from the focused
result.

## Remaining integration coverage

- Add a real CLI integration test that exercises the command-share service from
  argument parsing through queue/lock/event persistence.
- Add a cross-process or subprocess test proving queue reclaim and result-path
  confinement across worker boundaries.
- Add a consumer test for the intended registry/dispatch boundary once the
  receiving runtime is selected; current evidence proves only the thegent mesh
  producer contracts and boundary drift guard.
- Re-run the complete suite in a compatible Python/pytest environment and
  capture the result alongside this entry.

