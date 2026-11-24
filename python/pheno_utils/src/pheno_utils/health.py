"""Health Check Module.

Health monitoring and validation for projects.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class HealthResult:
    """Result of a health check."""

    passed: bool
    name: str
    message: str
    details: dict[str, Any] | None = None


@dataclass
class HealthReport:
    """Complete health report."""

    project: str
    checks: list[HealthResult]

    @property
    def passed_count(self) -> int:
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)

    @property
    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "passed": self.all_passed,
            "passed_count": self.passed_count,
            "failed_count": self.failed_count,
            "checks": [asdict(c) for c in self.checks],
        }


def check_imports(project_root: Path) -> HealthResult:
    """Check for circular or broken imports."""
    # This is a simplified check - real implementation would use import analysis
    src_dir = project_root / "src"
    if not src_dir.exists():
        return HealthResult(
            passed=True,
            name="imports",
            message="No src directory to check",
        )

    broken = []
    for py_file in src_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8", errors="ignore")
        # Simple check for import errors
        if "import error" in content.lower() or "importerror" in content.lower():
            broken.append(str(py_file.relative_to(project_root)))

    if broken:
        return HealthResult(
            passed=False,
            name="imports",
            message=f"Found {len(broken)} files with potential import issues",
            details={"files": broken[:10]},
        )

    return HealthResult(
        passed=True,
        name="imports",
        message="No obvious import issues found",
    )


def check_structure(project_root: Path) -> HealthResult:
    """Check project structure conventions."""
    expected_dirs = ["src", "tests", "docs"]
    missing = []

    for d in expected_dirs:
        if not (project_root / d).exists():
            missing.append(d)

    if missing:
        return HealthResult(
            passed=False,
            name="structure",
            message=f"Missing expected directories: {', '.join(missing)}",
            details={"missing": missing},
        )

    return HealthResult(
        passed=True,
        name="structure",
        message="Project structure follows conventions",
    )


def check_config_files(project_root: Path) -> HealthResult:
    """Check for required configuration files."""
    required = ["pyproject.toml", "README.md"]
    optional = [".gitignore", "LICENSE"]

    missing_required = [f for f in required if not (project_root / f).exists()]
    missing_optional = [f for f in optional if not (project_root / f).exists()]

    if missing_required:
        return HealthResult(
            passed=False,
            name="config",
            message=f"Missing required files: {', '.join(missing_required)}",
            details={"missing_required": missing_required},
        )

    details = {}
    if missing_optional:
        details["missing_optional"] = missing_optional

    return HealthResult(
        passed=True,
        name="config",
        message="Required configuration files present",
        details=details or None,
    )


def run_health_checks(
    project_root: Path,
    checks: list[str] | None = None,
) -> HealthReport:
    """Run health checks on a project."""
    all_checks = {
        "imports": check_imports,
        "structure": check_structure,
        "config": check_config_files,
    }

    checks_to_run = checks if checks else list(all_checks.keys())
    results = []

    for check_name in checks_to_run:
        if check_name in all_checks:
            try:
                result = all_checks[check_name](project_root)
                results.append(result)
            except Exception as e:
                results.append(
                    HealthResult(
                        passed=False,
                        name=check_name,
                        message=f"Check failed with error: {e}",
                    )
                )

    return HealthReport(
        project=str(project_root.name),
        checks=results,
    )


def format_health_report(report: HealthReport) -> str:
    """Format health report for display."""
    lines = [
        f"Health Report: {report.project}",
        "=" * 40,
        f"Passed: {report.passed_count}",
        f"Failed: {report.failed_count}",
        "",
    ]

    for check in report.checks:
        status = "✅" if check.passed else "❌"
        lines.append(f"{status} {check.name}: {check.message}")
        if check.details:
            for key, value in check.details.items():
                if isinstance(value, list):
                    lines.append(f"   {key}:")
                    for item in value:
                        lines.append(f"     - {item}")
                else:
                    lines.append(f"   {key}: {value}")

    return "\n".join(lines)
