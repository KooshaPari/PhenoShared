# Hermetic testing policy

> Hermetic = a test that requires no network, no MLX, no harbor, no
> docker, and no host-side state mutation. Pure-Python unit tests.

## Why a hermetic subset

Some tests assume optional external tooling (Apple Silicon + `mlx`,
`harbor_cli`, docker daemon, network endpoints). These are skipped
locally when the tooling is absent but break on a clean CI runner
that doesn't have it.

The hermetic subset is the **floor** of tests that pass on any Python
≥ 3.13 install with the project's dev dependencies. It is the right
gate for a quick smoke check:

```sh
bash scripts/run_hermetic_tests.sh
```

## Marker

The marker is registered in `pyproject.toml` (`[tool.pytest.ini_options]`
→ `markers`) as `hermetic`. Apply it per-test:

```python
import pytest

@pytest.mark.hermetic
def test_pure_unit_x(): ...
```

Or per-module:

```python
pytestmark = pytest.mark.hermetic
```

## What counts as hermetic

A test is hermetic iff it satisfies **all** of:

1. No `import mlx` (or any sub-module of it).
2. No `import harbor_cli` (or any sub-module).
3. No subprocess call that requires docker, harbor, or any non-stdlib
   binary on PATH.
4. No outbound network request (`httpx`, `requests`, `urllib.request`,
   `aiohttp`, `socket.create_connection`).
5. No filesystem write outside `tmp_path` / `pytest`'s basetemp.
6. No environment-variable reads other than `PATH`, `HOME`, `TMPDIR`,
   `PYTHONPATH`.

## What does NOT count as hermetic

| Pattern | Why |
|---------|-----|
| `@pytest.mark.skipif(not _has_mlx())` | Required MLX |
| `@pytest.mark.skipif(not _has_harbor())` | Required harbor |
| `@pytest.mark.skipif(not _has_docker())` | Required docker |
| `httpx.get(...)` | Network |
| `subprocess.run(["docker", ...])` | Docker CLI |
| `harbor_cli.run(...)` | Harbor CLI |

These are correctly excluded from the hermetic subset and should
remain under `@pytest.mark.hermetic` exclusion.

## Running

| Mode | Command | Purpose |
|------|---------|---------|
| Default | `bash scripts/run_hermetic_tests.sh` | Run subset |
| Full | `bash scripts/run_hermetic_tests.sh --full` | Run all (no marker filter) |
| Collect-only | `bash scripts/run_hermetic_tests.sh --collect` | List selected tests |

## Adding new hermetic tests

When writing a new unit test, ask:

> "Does this test need anything outside this Python process + the
> repo's source tree?"

If no, add `@pytest.mark.hermetic` (or `pytestmark = pytest.mark.hermetic`
at module top). The hermetic subset is curated, not auto-derived.

## Policy

The hermetic subset is **required** to pass before merging any change
to a test file. The full suite may skip tests that require external
tooling (these skip reasons are visible in `pytest -v` output).
