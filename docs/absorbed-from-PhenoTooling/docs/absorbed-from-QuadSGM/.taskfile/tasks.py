from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
IGNORED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".next",
    ".turbo",
    ".cache",
    "build",
    "coverage",
    "dist",
    "htmlcov",
    "node_modules",
    "out",
}


def visible(path: Path) -> bool:
    return not any(part in IGNORED_PARTS for part in path.relative_to(ROOT).parts)


def find(name: str) -> list[Path]:
    return sorted(path for path in ROOT.rglob(name) if visible(path))


def run(command: list[str], cwd: Path) -> None:
    rel = "." if cwd == ROOT else str(cwd.relative_to(ROOT))
    print(f"==> {rel}: {' '.join(command)}")
    subprocess.run(command, cwd=cwd, check=True)


def package_runner(cwd: Path) -> str:
    if (cwd / "bun.lock").exists() or (cwd / "bun.lockb").exists():
        return "bun"
    if (cwd / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (cwd / "yarn.lock").exists():
        return "yarn"
    return "npm"


def has_typescript_config(cwd: Path) -> bool:
    return any(cwd.glob("tsconfig*.json"))


def ensure_package_dependencies(cwd: Path, runner: str) -> None:
    install_commands = {
        "bun": ["bun", "install", "--frozen-lockfile"],
        "pnpm": ["pnpm", "install", "--frozen-lockfile"],
        "yarn": ["yarn", "install", "--frozen-lockfile"],
    }
    install = install_commands.get(runner)
    if install is None:
        if not (cwd / "package-lock.json").exists() and (cwd / "node_modules").exists():
            return
        install = (
            ["npm", "ci"]
            if (cwd / "package-lock.json").exists()
            else [
                "npm",
                "install",
                "--no-package-lock",
            ]
        )
    run(install, cwd)


def package_json() -> list[tuple[Path, dict]]:
    packages = []
    for manifest in find("package.json"):
        packages.append((manifest, json.loads(manifest.read_text())))
    return packages


def pyprojects() -> list[Path]:
    return find("pyproject.toml")


def nested_pyproject_dirs(cwd: Path) -> set[Path]:
    return {
        path.parent
        for path in cwd.rglob("pyproject.toml")
        if path.parent != cwd and visible(path)
    }


def python_test_targets(pyproject: Path) -> list[str]:
    cwd = pyproject.parent
    config = tomllib.loads(pyproject.read_text())
    paths = (
        config.get("tool", {})
        .get("pytest", {})
        .get("ini_options", {})
        .get("testpaths", [])
    )
    configured = [cwd / path for path in paths if (cwd / path).exists()]
    if configured:
        return [str(path.relative_to(cwd)) for path in configured]

    nested = nested_pyproject_dirs(cwd)
    tests = []
    for path in cwd.rglob("test_*.py"):
        if not visible(path):
            continue
        if any(other in path.parents for other in nested):
            continue
        tests.append(str(path.relative_to(cwd)))
    return sorted(tests)


def build() -> int:
    targets = 0

    for pyproject in pyprojects():
        targets += 1
        run(["uv", "build"], pyproject.parent)

    for manifest, data in package_json():
        scripts = data.get("scripts", {})
        script = (
            "build"
            if "build" in scripts
            else "docs:build"
            if "docs:build" in scripts
            else None
        )
        if script is None:
            continue

        targets += 1
        cwd = manifest.parent
        runner = package_runner(cwd)
        ensure_package_dependencies(cwd, runner)
        run([runner, "run", script], cwd)

    return targets


def test() -> int:
    targets = 0

    for pyproject in pyprojects():
        test_targets = python_test_targets(pyproject)
        if not test_targets:
            continue

        targets += 1
        run(["uv", "run", "--extra", "dev", "pytest", *test_targets], pyproject.parent)

    for manifest, data in package_json():
        script = data.get("scripts", {}).get("test")
        if not script or "no test specified" in script:
            continue

        targets += 1
        cwd = manifest.parent
        runner = package_runner(cwd)
        ensure_package_dependencies(cwd, runner)
        run([runner, "run", "test"], cwd)

    return targets


def lint() -> int:
    targets = 0

    for pyproject in pyprojects():
        targets += 1
        run(["uv", "run", "--extra", "dev", "ruff", "check", "."], pyproject.parent)
        run(
            ["uv", "run", "--extra", "dev", "ruff", "format", "--check", "."],
            pyproject.parent,
        )

    for manifest, data in package_json():
        scripts = data.get("scripts", {})
        cwd = manifest.parent

        if "typecheck" in scripts and has_typescript_config(cwd):
            script = "typecheck"
        elif "tsc" in scripts and has_typescript_config(cwd):
            script = "tsc"
        elif "eslint" in scripts:
            script = "eslint"
        elif "lint" in scripts:
            script = "lint"
        else:
            continue

        targets += 1
        runner = package_runner(cwd)
        ensure_package_dependencies(cwd, runner)
        run([runner, "run", script], cwd)

    return targets


def tracked_paths() -> set[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return {ROOT / path for path in result.stdout.split("\0") if path}


def clean() -> int:
    ignored = {".git", ".venv", "node_modules"}
    names = {
        ".cache",
        ".coverage",
        ".mypy_cache",
        ".next",
        ".pytest_cache",
        ".ruff_cache",
        ".turbo",
        "__pycache__",
        "build",
        "coverage",
        "coverage_html",
        "dist",
        "htmlcov",
        "out",
    }
    suffixes = (".egg-info", ".pyc", ".pyo", ".tsbuildinfo")
    tracked = tracked_paths()
    removed = 0

    def clean_visible(path: Path) -> bool:
        return not any(part in ignored for part in path.relative_to(ROOT).parts)

    def safe_to_remove(path: Path) -> bool:
        if path in tracked:
            return False
        if path.is_dir():
            return not any(item == path or path in item.parents for item in tracked)
        return True

    for path in sorted(ROOT.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if not clean_visible(path) or not path.exists():
            continue
        if path.name not in names and not path.name.endswith(suffixes):
            continue
        if not safe_to_remove(path):
            print(f"skipped tracked {path.relative_to(ROOT)}")
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()
        removed += 1
        print(f"removed {path.relative_to(ROOT)}")

    return removed


TASKS: dict[str, Callable[[], int]] = {
    "build": build,
    "test": test,
    "lint": lint,
    "clean": clean,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run repository Taskfile commands.")
    parser.add_argument("task", choices=TASKS)
    args = parser.parse_args()

    targets = TASKS[args.task]()
    if args.task != "clean" and targets == 0:
        raise SystemExit(f"No {args.task} targets detected.")


if __name__ == "__main__":
    main()
