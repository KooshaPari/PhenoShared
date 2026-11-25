import subprocess
import sys
from importlib import import_module
from pathlib import Path

import tomllib


def test_harness_entrypoint_is_importable():
    # Traces to: FR-HELIOS-IO-006 (installable harness entrypoint).
    module = import_module("harness.scripts.run_harness")
    assert callable(module.main)
    assert callable(module.run_runner)


def test_harness_declares_schema_validation_dependencies():
    # Traces to: FR-HELIOS-SCHEMA-001 (schema validation dependencies).
    project = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())
    dependencies = set(project["project"]["dependencies"])
    assert any(dependency.startswith("jsonschema") for dependency in dependencies)
    assert any(dependency.startswith("fastjsonschema") for dependency in dependencies)


def test_harness_wheel_includes_the_legacy_runner() -> None:
    # Traces to: FR-HELIOS-IO-006 (functional installed entrypoint).
    project = tomllib.loads((Path(__file__).resolve().parents[1] / "pyproject.toml").read_text())
    force_include = project["tool"]["hatch"]["build"]["targets"]["wheel"]["force-include"]
    assert force_include["scripts/run-harness.py"] == "harness/_legacy_runner.py"
    assert (
        force_include["schemas/benchmark_run.schema.json"]
        == "harness/schemas/benchmark_run.schema.json"
    )


def test_entrypoint_resolves_a_real_legacy_runner() -> None:
    # Traces to: FR-HELIOS-IO-006 (source and wheel runner resolution).
    module = import_module("harness.scripts.run_harness")
    path = module._legacy_script_path()

    assert path.is_file()
    assert path.name in {"run-harness.py", "_legacy_runner.py"}


def test_repository_root_package_exposes_lazy_exports() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from harness import L1Cache, TeammateRegistry; "
            "assert L1Cache.__name__ == 'L1Cache'; "
            "assert TeammateRegistry.__name__ == 'TeammateRegistry'",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
