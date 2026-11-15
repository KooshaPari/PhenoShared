#!/usr/bin/env python3
"""
Deployment Readiness Checker Comprehensive pre-deployment validation and health checks.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any


class CheckStatus(Enum):
    """
    Check result status.
    """

    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"
    ERROR = "error"


class CheckPriority(Enum):
    """
    Check priority levels.
    """

    CRITICAL = "critical"  # Must pass for deployment
    HIGH = "high"  # Should pass for production
    MEDIUM = "medium"  # Nice to have
    LOW = "low"  # Optional


@dataclass
class CheckResult:
    """
    Result of a single readiness check.
    """

    name: str
    status: CheckStatus
    priority: CheckPriority
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to dictionary.
        """
        return {
            "name": self.name,
            "status": self.status.value,
            "priority": self.priority.value,
            "message": self.message,
            "details": self.details,
            "duration": self.duration,
            "timestamp": self.timestamp.isoformat(),
        }


class ReadinessChecker:
    """
    Main deployment readiness checker.
    """

    def __init__(self, project_dir: str = None):
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.logger = logging.getLogger(__name__)

        # Register checks
        self._check_registry = {}
        self._register_default_checks()

    def _register_default_checks(self):
        """
        Register all default readiness checks.
        """
        checks = [
            self.check_code_quality,
            self.check_tests_status,
            self.check_security_vulnerabilities,
            self.check_dependencies,
            self.check_configuration,
            self.check_database_health,
            self.check_environment_variables,
            self.check_build_artifacts,
            self.check_deployment_configuration,
            self.check_performance_benchmarks,
            self.check_compatibility,
            self.check_resource_limits,
            self.check_backup_status,
            self.check_monitoring_setup,
        ]

        for check in checks:
            self.register_check(check.__name__, check)

    def register_check(self, name: str, check_func: Callable) -> None:
        """
        Register a custom check.
        """
        self._check_registry[name] = check_func

    def run_all_checks(
        self,
        priorities: list[CheckPriority] = None,
        parallel: bool = True,
    ) -> list[CheckResult]:
        """
        Run all readiness checks.
        """
        if not priorities:
            priorities = [CheckPriority.CRITICAL, CheckPriority.HIGH]

        # Filter checks by priority
        checks_to_run = []
        for name, check_func in self._check_registry.items():
            # Determine check priority (can be hardcoded in check function)
            priority = getattr(check_func, "priority", CheckPriority.MEDIUM)
            if priority in priorities:
                checks_to_run.append((name, check_func, priority))

        if not parallel:
            return self._run_checks_sequential(checks_to_run)
        return self._run_checks_parallel(checks_to_run)

    def run_check(self, check_name: str) -> CheckResult | None:
        """
        Run a single check.
        """
        if check_name not in self._check_registry:
            return None

        check_func = self._check_registry[check_name]
        start_time = time.time()

        try:
            result = check_func()
            if isinstance(result, CheckResult):
                return result
            return CheckResult(
                name=check_name,
                status=CheckStatus.FAILED,
                priority=getattr(check_func, "priority", CheckPriority.MEDIUM),
                message="Check returned invalid result",
            )
        except Exception as e:
            duration = time.time() - start_time
            return CheckResult(
                name=check_name,
                status=CheckStatus.ERROR,
                priority=getattr(check_func, "priority", CheckPriority.MEDIUM),
                message=f"Check failed with error: {e}",
                duration=duration,
            )

    def _run_checks_sequential(self, checks: list[tuple]) -> list[CheckResult]:
        """
        Run checks sequentially.
        """
        results = []

        for check_name, check_func, priority in checks:
            start_time = time.time()

            try:
                result = check_func()
                if isinstance(result, CheckResult):
                    result.duration = time.time() - start_time
                    results.append(result)
                else:
                    results.append(
                        CheckResult(
                            name=check_name,
                            status=CheckStatus.FAILED,
                            priority=priority,
                            message="Check returned invalid result",
                            duration=time.time() - start_time,
                        ),
                    )

            except Exception as e:
                results.append(
                    CheckResult(
                        name=check_name,
                        status=CheckStatus.ERROR,
                        priority=priority,
                        message=f"Check failed: {e}",
                        duration=time.time() - start_time,
                    ),
                )

        return results

    async def _run_checks_parallel(self, checks: list[tuple]) -> list[CheckResult]:
        """
        Run checks in parallel.
        """

        async def run_single_check(check_name: str, check_func: Callable, priority: CheckPriority):
            start_time = time.time()

            try:
                result = check_func()
                if isinstance(result, CheckResult):
                    result.duration = time.time() - start_time
                    return result
                return CheckResult(
                    name=check_name,
                    status=CheckStatus.FAILED,
                    priority=priority,
                    message="Check returned invalid result",
                    duration=time.time() - start_time,
                )

            except Exception as e:
                return CheckResult(
                    name=check_name,
                    status=CheckStatus.ERROR,
                    priority=priority,
                    message=f"Check failed: {e}",
                    duration=time.time() - start_time,
                )

        # Run all checks concurrently
        tasks = []
        for check_name, check_func, priority in checks:
            if asyncio.iscoroutinefunction(check_func):
                task = run_single_check(check_name, check_func, priority)
                tasks.append(task)
            else:
                # Run sync checks in executor
                task = asyncio.get_event_loop().run_in_executor(
                    None,
                    run_single_check,
                    check_name,
                    check_func,
                    priority,
                )
                tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and convert to CheckResults
        processed_results = []
        for result in results:
            if isinstance(result, CheckResult):
                processed_results.append(result)
            elif isinstance(result, Exception):
                processed_results.append(
                    CheckResult(
                        name="Parallel execution error",
                        status=CheckStatus.ERROR,
                        priority=CheckPriority.HIGH,
                        message=f"Parallel execution failed: {result}",
                    ),
                )

        return processed_results

    def generate_report(self, results: list[CheckResult], format: str = "json") -> str:
        """
        Generate deployment readiness report.
        """
        total_checks = len(results)
        passed = sum(1 for r in results if r.status == CheckStatus.PASSED)
        failed = sum(1 for r in results if r.status == CheckStatus.FAILED)
        warnings = sum(1 for r in results if r.status == CheckStatus.WARNING)

        summary = {
            "total_checks": total_checks,
            "passed": passed,
            "failed": failed,
            "warnings": warnings,
            "readiness_score": (passed / total_checks * 100) if total_checks > 0 else 0,
            "can_deploy": all(
                r.status in [CheckStatus.PASSED, CheckStatus.WARNING]
                for r in results
                if r.priority == CheckPriority.CRITICAL
            ),
            "timestamp": datetime.now().isoformat(),
            "checks": [r.to_dict() for r in results],
        }

        if format == "json":
            return json.dumps(summary, indent=2)
        if format == "markdown":
            return self._generate_markdown_report(summary)
        return str(summary)

    def _generate_markdown_report(self, summary: dict[str, Any]) -> str:
        """
        Generate markdown report.
        """
        report = f"""# Deployment Readiness Report

Generated: {summary["timestamp"]}

## Summary

- **Total Checks**: {summary["total_checks"]}
- **Passed**: {summary["passed"]}
- **Failed**: {summary["failed"]}
- **Warnings**: {summary["warnings"]}
- **Readiness Score**: {summary["readiness_score"]:.1f}%
- **Can Deploy**: {"✅ Yes" if summary["can_deploy"] else "❌ No"}

## Check Results

"""

        # Group by status
        by_status = {}
        for check in summary["checks"]:
            status = check["status"]
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(check)

        # Render results
        status_emoji = {
            "passed": "✅",
            "failed": "❌",
            "warning": "⚠️",
            "error": "🚨",
            "skipped": "⏭️",
        }

        for status in ["failed", "warning", "passed", "skipped", "error"]:
            if status in by_status:
                report += f"### {status.title()}\n\n"
                for check in by_status[status]:
                    emoji = status_emoji.get(status, "❓")
                    priority_badge = check["priority"].upper()
                    report += f"{emoji} **{check['name']}** `{priority_badge}`\n"
                    report += f"- Message: {check['message']}\n"
                    if check["details"]:
                        report += f"- Details: {json.dumps(check['details'], indent=2)}\n"
                    report += f"- Duration: {check['duration']:.2f}s\n\n"

        return report

    # Individual check implementations
    @staticmethod
    def check_code_quality() -> CheckResult:
        """
        Check code quality metrics.
        """
        try:
            # Run ruff check
            ruff_result = subprocess.run(
                ["ruff", "check", "--output-format=json", "."],
                check=False,
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )

            # Run mypy
            mypy_result = subprocess.run(
                ["mypy", "--show-error-codes", "."],
                check=False,
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )

            ruff_issues = len(json.loads(ruff_result.stdout)) if ruff_result.stdout else 0
            mypy_errors = mypy_result.returncode

            if ruff_issues == 0 and mypy_errors == 0:
                return CheckResult(
                    name="code_quality",
                    status=CheckStatus.PASSED,
                    priority=CheckPriority.HIGH,
                    message="Code quality checks passed",
                    details={"ruff_issues": ruff_issues, "mypy_errors": mypy_errors},
                )
            return CheckResult(
                name="code_quality",
                status=CheckStatus.WARNING if ruff_issues < 10 else CheckStatus.FAILED,
                priority=CheckPriority.HIGH,
                message=f"Found {ruff_issues} ruff issues and {mypy_errors} mypy errors",
                details={"ruff_issues": ruff_issues, "mypy_errors": mypy_errors},
            )

        except Exception as e:
            return CheckResult(
                name="code_quality",
                status=CheckStatus.ERROR,
                priority=CheckPriority.HIGH,
                message=f"Code quality check failed: {e}",
            )

    @staticmethod
    def check_tests_status() -> CheckResult:
        """
        Check if tests are passing.
        """
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--tb=no", "-q"],
                check=False,
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )

            if result.returncode == 0:
                return CheckResult(
                    name="tests_status",
                    status=CheckStatus.PASSED,
                    priority=CheckPriority.CRITICAL,
                    message="All tests are passing",
                )
            return CheckResult(
                name="tests_status",
                status=CheckStatus.FAILED,
                priority=CheckPriority.CRITICAL,
                message="Tests are failing",
                details={"return_code": result.returncode, "stderr": result.stderr},
            )

        except Exception as e:
            return CheckResult(
                name="tests_status",
                status=CheckStatus.ERROR,
                priority=CheckPriority.CRITICAL,
                message=f"Test status check failed: {e}",
            )

    @staticmethod
    def check_security_vulnerabilities() -> CheckResult:
        """
        Check for security vulnerabilities.
        """
        try:
            # Run safety check
            safety_result = subprocess.run(
                ["safety", "check", "--json"],
                check=False,
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )

            if safety_result.returncode == 0:
                vulnerabilities = []
            else:
                try:
                    data = json.loads(safety_result.stdout)
                    vulnerabilities = data.get("vulnerabilities", [])
                except:
                    vulnerabilities = [{"error": safety_result.stdout}]

            vuln_count = len(vulnerabilities)

            if vuln_count == 0:
                return CheckResult(
                    name="security_vulnerabilities",
                    status=CheckStatus.PASSED,
                    priority=CheckPriority.HIGH,
                    message="No security vulnerabilities found",
                )
            return CheckResult(
                name="security_vulnerabilities",
                status=CheckStatus.FAILED if vuln_count > 5 else CheckStatus.WARNING,
                priority=CheckPriority.HIGH,
                message=f"Found {vuln_count} security vulnerabilities",
                details={"vulnerabilities": vulnerabilities},
            )

        except Exception as e:
            return CheckResult(
                name="security_vulnerabilities",
                status=CheckStatus.ERROR,
                priority=CheckPriority.HIGH,
                message=f"Security check failed: {e}",
            )

    @staticmethod
    def check_dependencies() -> CheckResult:
        """
        Check dependency status.
        """
        try:
            # Check if requirements files exist
            requirements_files = []
            for req_file in ["requirements.txt", "requirements-dev.txt", "pyproject.toml"]:
                if Path(req_file).exists():
                    requirements_files.append(req_file)

            # Check if dependencies are installable
            install_result = subprocess.run(
                ["pip", "check"],
                check=False,
                capture_output=True,
                text=True,
                cwd=Path.cwd(),
            )

            if install_result.returncode == 0 and requirements_files:
                return CheckResult(
                    name="dependencies",
                    status=CheckStatus.PASSED,
                    priority=CheckPriority.HIGH,
                    message="Dependencies are valid",
                    details={"requirements_files": requirements_files},
                )
            return CheckResult(
                name="dependencies",
                status=CheckStatus.FAILED,
                priority=CheckPriority.HIGH,
                message=f"Dependency issues: {install_result.stdout if install_result.stdout else 'No requirements files found'}",
                details={
                    "requirements_files": requirements_files,
                    "stderr": install_result.stderr,
                },
            )

        except Exception as e:
            return CheckResult(
                name="dependencies",
                status=CheckStatus.ERROR,
                priority=CheckPriority.HIGH,
                message=f"Dependency check failed: {e}",
            )

    @staticmethod
    def check_configuration() -> CheckResult:
        """
        Check deployment configuration.
        """
        try:
            config_files = []
            required_configs = []

            # Check for various config files
            for config in [
                "vercel.json",
                ".vercel/project.json",
                "docker-compose.yml",
                "Dockerfile",
            ]:
                if Path(config).exists():
                    config_files.append(config)
                elif config in ["vercel.json", ".vercel/project.json"]:
                    required_configs.append(config)

            # Check environment files
            env_files = []
            for env_file in [".env", ".env.preview", ".env.production"]:
                if Path(env_file).exists():
                    env_files.append(env_file)

            if required_configs and not config_files:
                return CheckResult(
                    name="configuration",
                    status=CheckStatus.FAILED,
                    priority=CheckPriority.HIGH,
                    message=f"Missing required configuration: {', '.join(required_configs)}",
                    details={
                        "missing": required_configs,
                        "existing": config_files,
                        "env_files": env_files,
                    },
                )
            return CheckResult(
                name="configuration",
                status=CheckStatus.PASSED,
                priority=CheckPriority.HIGH,
                message="Configuration files are present",
                details={"config_files": config_files, "env_files": env_files},
            )

        except Exception as e:
            return CheckResult(
                name="configuration",
                status=CheckStatus.ERROR,
                priority=CheckPriority.HIGH,
                message=f"Configuration check failed: {e}",
            )

    @staticmethod
    def check_build_artifacts() -> CheckResult:
        """
        Check build artifacts.
        """
        try:
            dist_dir = Path("dist")
            build_dir = Path("build")

            dist_exists = dist_dir.exists() and any(dist_dir.iterdir())
            build_exists = build_dir.exists() and any(build_dir.iterdir())

            if dist_exists or build_exists:
                # Check if artifacts are recent (within last hour)
                now = time.time()
                recent_artifacts = False

                for artifact_dir in [dist_dir, build_dir]:
                    if artifact_dir.exists():
                        for item in artifact_dir.iterdir():
                            item_age = now - item.stat().st_mtime
                            if item_age < 3600:  # 1 hour
                                recent_artifacts = True
                                break

                status = CheckStatus.PASSED if recent_artifacts else CheckStatus.WARNING
                message = f"Build artifacts found, {'recent' if recent_artifacts else 'stale'}"

                return CheckResult(
                    name="build_artifacts",
                    status=status,
                    priority=CheckPriority.MEDIUM,
                    message=message,
                    details={
                        "dist_exists": dist_exists,
                        "build_exists": build_exists,
                        "recent_artifacts": recent_artifacts,
                    },
                )
            return CheckResult(
                name="build_artifacts",
                status=CheckStatus.WARNING,
                priority=CheckPriority.MEDIUM,
                message="No build artifacts found - run 'make build' first",
                details={"dist_exists": False, "build_exists": False},
            )

        except Exception as e:
            return CheckResult(
                name="build_artifacts",
                status=CheckStatus.ERROR,
                priority=CheckPriority.MEDIUM,
                message=f"Build artifacts check failed: {e}",
            )

    @staticmethod
    def check_environment_variables() -> CheckResult:
        """
        Check required environment variables.
        """
        try:
            required_vars = ["NODE_ENV", "DATABASE_URL"]

            missing_vars = []
            present_vars = {}

            for var in required_vars:
                if os.getenv(var):
                    present_vars[var] = "✓"
                else:
                    missing_vars.append(var)

            # Check optional but recommended vars
            optional_vars = ["API_BASE_URL", "REDIS_URL", "SENTRY_DSN"]

            for var in optional_vars:
                if os.getenv(var):
                    present_vars[var] = "✓"

            if missing_vars:
                return CheckResult(
                    name="environment_variables",
                    status=CheckStatus.FAILED,
                    priority=CheckPriority.CRITICAL,
                    message=f"Missing required environment variables: {', '.join(missing_vars)}",
                    details={"missing": missing_vars, "present": list(present_vars.keys())},
                )
            return CheckResult(
                name="environment_variables",
                status=CheckStatus.PASSED,
                priority=CheckPriority.CRITICAL,
                message="All required environment variables are set",
                details={"present": list(present_vars.keys())},
            )

        except Exception as e:
            return CheckResult(
                name="environment_variables",
                status=CheckStatus.ERROR,
                priority=CheckPriority.CRITICAL,
                message=f"Environment check failed: {e}",
            )

    @staticmethod
    def check_database_health() -> CheckResult:
        """
        Check database connectivity and health.
        """
        try:
            db_url = os.getenv("DATABASE_URL")
            if not db_url:
                return CheckResult(
                    name="database_health",
                    status=CheckStatus.WARNING,
                    priority=CheckPriority.HIGH,
                    message="DATABASE_URL not set - skipping database health check",
                )

            # Simple database connectivity test
            try:
                import psycopg2

                conn = psycopg2.connect(db_url, connect_timeout=5)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                conn.close()

                return CheckResult(
                    name="database_health",
                    status=CheckStatus.PASSED,
                    priority=CheckPriority.HIGH,
                    message="Database connection successful",
                )

            except Exception as db_e:
                return CheckResult(
                    name="database_health",
                    status=CheckStatus.FAILED,
                    priority=CheckPriority.HIGH,
                    message=f"Database connection failed: {db_e}",
                    details={"error": str(db_e)},
                )

        except Exception as e:
            return CheckResult(
                name="database_health",
                status=CheckStatus.ERROR,
                priority=CheckPriority.HIGH,
                message=f"Database health check failed: {e}",
            )

    @staticmethod
    def check_deployment_configuration() -> CheckResult:
        """
        Check deployment-specific configuration.
        """
        try:
            vercel_config = Path("vercel.json")
            project_config = Path(".vercel/project.json")

            if not vercel_config.exists():
                return CheckResult(
                    name="deployment_configuration",
                    status=CheckStatus.WARNING,
                    priority=CheckPriority.HIGH,
                    message="vercel.json not found - using default deployment config",
                )

            # Parse and validate vercel config
            try:
                with open(vercel_config) as f:
                    config = json.load(f)

                required_fields = ["version", "builds"]
                missing_fields = [field for field in required_fields if field not in config]

                if missing_fields:
                    return CheckResult(
                        name="deployment_configuration",
                        status=CheckStatus.FAILED,
                        priority=CheckPriority.HIGH,
                        message=f"Missing deployment config fields: {', '.join(missing_fields)}",
                        details={"missing_fields": missing_fields, "config": config},
                    )
                return CheckResult(
                    name="deployment_configuration",
                    status=CheckStatus.PASSED,
                    priority=CheckPriority.HIGH,
                    message="Deployment configuration is valid",
                    details={"config_fields": list(config.keys())},
                )

            except json.JSONDecodeError as e:
                return CheckResult(
                    name="deployment_configuration",
                    status=CheckStatus.FAILED,
                    priority=CheckPriority.HIGH,
                    message=f"Invalid JSON in deployment config: {e}",
                )

        except Exception as e:
            return CheckResult(
                name="deployment_configuration",
                status=CheckStatus.ERROR,
                priority=CheckPriority.HIGH,
                message=f"Deployment configuration check failed: {e}",
            )

    @staticmethod
    def check_performance_benchmarks() -> CheckResult:
        """
        Check if performance benchmarks are passing.
        """
        try:
            benchmark_file = Path("reports/benchmarks.json")

            if not benchmark_file.exists():
                return CheckResult(
                    name="performance_benchmarks",
                    status=CheckStatus.WARNING,
                    priority=CheckPriority.MEDIUM,
                    message="No benchmark results found - run 'make benchmark'",
                )

            with open(benchmark_file) as f:
                benchmarks = json.load(f)

            # Check if benchmarks have regressions
            issues = []
            for benchmark_name, benchmark_data in benchmarks.items():
                if "min" in benchmark_data and "max" in benchmark_data:
                    # Check for performance regressions (simple heuristic)
                    if benchmark_data["max"] > benchmark_data["min"] * 2:
                        issues.append(f"{benchmark_name}: high variance")

            if issues:
                return CheckResult(
                    name="performance_benchmarks",
                    status=CheckStatus.WARNING,
                    priority=CheckPriority.MEDIUM,
                    message=f"Performance issues detected: {', '.join(issues)}",
                    details={"issues": issues, "benchmark_count": len(benchmarks)},
                )
            return CheckResult(
                name="performance_benchmarks",
                status=CheckStatus.PASSED,
                priority=CheckPriority.MEDIUM,
                message="Performance benchmarks are healthy",
                details={"benchmark_count": len(benchmarks)},
            )

        except Exception as e:
            return CheckResult(
                name="performance_benchmarks",
                status=CheckStatus.ERROR,
                priority=CheckPriority.MEDIUM,
                message=f"Performance benchmark check failed: {e}",
            )

    @staticmethod
    def check_compatibility() -> CheckResult:
        """
        Check version compatibility.
        """
        try:
            # Check Python version
            python_version = sys.version_info
            if python_version < (3, 11):
                return CheckResult(
                    name="compatibility",
                    status=CheckStatus.FAILED,
                    priority=CheckPriority.HIGH,
                    message=f"Python {python_version.major}.{python_version.minor} is not supported (requires 3.11+)",
                    details={"python_version": f"{python_version.major}.{python_version.minor}"},
                )

            # Check key dependencies
            try:
                import rich
                import typer

                return CheckResult(
                    name="compatibility",
                    status=CheckStatus.PASSED,
                    priority=CheckPriority.HIGH,
                    message="Dependencies are compatible",
                    details={"python_version": f"{python_version.major}.{python_version.minor}"},
                )
            except ImportError as e:
                return CheckResult(
                    name="compatibility",
                    status=CheckStatus.FAILED,
                    priority=CheckPriority.HIGH,
                    message=f"Missing critical dependency: {e}",
                    details={"python_version": f"{python_version.major}.{python_version.minor}"},
                )

        except Exception as e:
            return CheckResult(
                name="compatibility",
                status=CheckStatus.ERROR,
                priority=CheckPriority.HIGH,
                message=f"Compatibility check failed: {e}",
            )

    @staticmethod
    def check_resource_limits() -> CheckResult:
        """
        Check resource limits and requirements.
        """
        try:
            warnings = []

            # Check disk space (simple check)
            current_dir = Path.cwd()
            stat = os.statvfs(current_dir)
            free_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)

            if free_gb < 1:  # Less than 1GB free
                warnings.append(f"Low disk space: {free_gb:.1f}GB free")

            # Check code size (simplified LOC check)
            try:
                from scripts.count_loc import count_lines

                loc_info = count_lines()
                if loc_info.get("total_loc", 0) > 10000:
                    warnings.append(f"Large codebase: {loc_info['total_loc']} LOC")
            except:
                pass

            if warnings:
                return CheckResult(
                    name="resource_limits",
                    status=CheckStatus.WARNING,
                    priority=CheckPriority.MEDIUM,
                    message=f"Resource warnings: {', '.join(warnings)}",
                    details={"warnings": warnings, "free_disk_gb": free_gb},
                )
            return CheckResult(
                name="resource_limits",
                status=CheckStatus.PASSED,
                priority=CheckPriority.MEDIUM,
                message="Resource limits are acceptable",
                details={"free_disk_gb": free_gb},
            )

        except Exception as e:
            return CheckResult(
                name="resource_limits",
                status=CheckStatus.ERROR,
                priority=CheckPriority.MEDIUM,
                message=f"Resource limits check failed: {e}",
            )

    @staticmethod
    def check_backup_status() -> CheckResult:
        """
        Check backup systems.
        """
        try:
            # Simple backup check - look for backup directories or files
            backup_dirs = [
                d
                for d in Path.cwd().iterdir()
                if d.is_dir() and ("backup" in d.name.lower() or "bak" in d.name.lower())
            ]

            if not backup_dirs:
                return CheckResult(
                    name="backup_status",
                    status=CheckStatus.WARNING,
                    priority=CheckPriority.LOW,
                    message="No backup directories found",
                )
            return CheckResult(
                name="backup_status",
                status=CheckStatus.PASSED,
                priority=CheckPriority.LOW,
                message=f"Found {len(backup_dirs)} backup directories",
                details={"backup_dirs": [d.name for d in backup_dirs]},
            )

        except Exception as e:
            return CheckResult(
                name="backup_status",
                status=CheckStatus.ERROR,
                priority=CheckPriority.LOW,
                message=f"Backup status check failed: {e}",
            )

    @staticmethod
    def check_monitoring_setup() -> CheckResult:
        """
        Check monitoring configuration.
        """
        try:
            monitoring_files = []

            # Check for monitoring configurations
            for monitor_file in ["datadog.yaml", "prometheus.yml", "grafana.json", ".newrelic"]:
                if Path(monitor_file).exists():
                    monitoring_files.append(monitor_file)

            # Check for health endpoints
            health_files = []
            for pattern in ["*health*", "*monitor*"]:
                health_files.extend(Path.cwd().glob(pattern))

            return CheckResult(
                name="monitoring_setup",
                status=CheckStatus.PASSED if monitoring_files else CheckStatus.WARNING,
                priority=CheckPriority.LOW,
                message=f"Monitoring {'configured' if monitoring_files else 'not configured'}",
                details={
                    "monitoring_files": monitoring_files,
                    "health_files": [f.name for f in health_files],
                },
            )

        except Exception as e:
            return CheckResult(
                name="monitoring_setup",
                status=CheckStatus.ERROR,
                priority=CheckPriority.LOW,
                message=f"Monitoring setup check failed: {e}",
            )


# Set priorities for each check
ReadinessChecker.check_code_quality.priority = CheckPriority.HIGH
ReadinessChecker.check_tests_status.priority = CheckPriority.CRITICAL
ReadinessChecker.check_security_vulnerabilities.priority = CheckPriority.HIGH
ReadinessChecker.check_dependencies.priority = CheckPriority.HIGH
ReadinessChecker.check_configuration.priority = CheckPriority.HIGH
ReadinessChecker.check_database_health.priority = CheckPriority.HIGH
ReadinessChecker.check_environment_variables.priority = CheckPriority.CRITICAL
ReadinessChecker.check_build_artifacts.priority = CheckPriority.MEDIUM
ReadinessChecker.check_deployment_configuration.priority = CheckPriority.HIGH
ReadinessChecker.check_performance_benchmarks.priority = CheckPriority.MEDIUM
ReadinessChecker.check_compatibility.priority = CheckPriority.HIGH
ReadinessChecker.check_resource_limits.priority = CheckPriority.MEDIUM
ReadinessChecker.check_backup_status.priority = CheckPriority.LOW
ReadinessChecker.check_monitoring_setup.priority = CheckPriority.LOW
