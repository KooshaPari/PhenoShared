"""Dependency Analysis Module.

Analyzes pyproject.toml, setup.py, and requirements.txt files
to create comprehensive dependency graphs.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

# Try to use stdlib tomllib (Python 3.11+), else fall back to toml if installed
try:  # Python 3.11+
    import tomllib as toml_lib  # type: ignore[attr-defined]
except Exception:
    try:
        import toml as toml_lib  # type: ignore[no-redef]
    except Exception:
        toml_lib = None  # Graceful degradation if no TOML parser is available


class DependencyAnalyzer:
    """Analyzes dependencies across all pheno-sdk kits."""

    def __init__(self, root_path: Path):
        self.root_path = Path(root_path)
        self.dependencies: dict[str, dict[str, str]] = defaultdict(dict)
        self.kit_info: dict[str, dict[str, Any]] = {}
        self.all_deps = Counter()
        self.dev_deps = Counter()
        self.optional_deps: dict[str, Counter] = defaultdict(Counter)

    def analyze_all(self) -> dict[str, Any]:
        """Run complete dependency analysis."""
        self.find_and_analyze_packages()
        return {
            "summary": self.generate_summary(),
            "kit_dependencies": dict(self.dependencies),
            "kit_info": self.kit_info,
            "consolidation_groups": self.suggest_consolidation_groups(),
            "unified_dependencies": self.create_unified_dependencies(),
        }

    def find_and_analyze_packages(self) -> None:
        """Find all packaging files and analyze them."""
        packaging_files: list[Path] = []

        # Find all packaging files
        for pattern in ["**/pyproject.toml", "**/setup.py", "**/requirements*.txt"]:
            packaging_files.extend(self.root_path.glob(pattern))

        # Group by kit directory
        kit_files: dict[Path, list[Path]] = defaultdict(list)
        for file_path in packaging_files:
            # Find the kit directory (first parent with a hyphenated name or kit suffix)
            kit_dir = self._find_kit_directory(file_path)
            if kit_dir:
                kit_files[kit_dir].append(file_path)

        # Analyze each kit's dependencies
        for kit_dir, files in kit_files.items():
            kit_name = kit_dir.name
            if kit_name not in self.kit_info:
                self.kit_info[kit_name] = {
                    "path": str(kit_dir),
                    "packaging_files": [],
                    "dependencies": {},
                    "dev_dependencies": {},
                    "optional_dependencies": {},
                }

            for file_path in files:
                self.kit_info[kit_name]["packaging_files"].append(str(file_path))
                self._analyze_file(kit_name, file_path)

    def _find_kit_directory(self, file_path: Path) -> Path | None:
        """Find the kit directory for a packaging file."""
        parts = file_path.parts
        sdk_index = -1

        # Find the pheno-sdk directory
        for i, part in enumerate(parts):
            if "pheno-sdk" in part:
                sdk_index = i
                break

        if sdk_index == -1:
            return None

        # Look for kit directories after pheno-sdk
        for i in range(sdk_index + 1, len(parts)):
            part = parts[i]
            if (
                "-kit" in part
                or "kit" in part.lower()
                or part
                in [
                    "pydevkit",
                    "authkit-client",
                    "KInfra",
                    "pheno_cli",
                    "process-monitor-sdk",
                    "mcp-infra-sdk",
                    "mcp-QA",
                    "mcp-sdk-kit",
                ]
            ):
                return Path(*parts[: i + 1])

        return None

    def _analyze_file(self, kit_name: str, file_path: Path) -> None:
        """Analyze a single packaging file."""
        if file_path.name == "pyproject.toml":
            self._analyze_pyproject(kit_name, file_path)
        elif file_path.name == "setup.py":
            self._analyze_setup_py(kit_name, file_path)
        elif "requirements" in file_path.name:
            self._analyze_requirements(kit_name, file_path)

    def _analyze_pyproject(  # noqa: PLR0912, PLR0915
        self, kit_name: str, file_path: Path
    ) -> None:
        """Analyze pyproject.toml file."""
        try:
            data: dict[str, Any] = {}
            if toml_lib is not None:
                # Use available TOML parser
                mode = (
                    "rb" if (hasattr(toml_lib, "loads") and toml_lib.__name__ == "tomllib") else "r"
                )
                with open(file_path, mode) as f:
                    if mode == "rb":
                        data = toml_lib.load(f)  # type: ignore[arg-type]
                    else:
                        data = toml_lib.load(f)  # type: ignore[assignment]
            else:
                # Minimal fallback: regex parse dependencies from pyproject
                text = Path(file_path).read_text()
                data = {}
                # Attempt to capture simple dependencies list under [project]
                proj_match = re.search(r"\[project\](.*?)\n\[", text, re.DOTALL)
                if proj_match:
                    proj_block = proj_match.group(1)
                    deps_match = re.search(
                        r"dependencies\s*=\s*\[(.*?)\]",
                        proj_block,
                        re.DOTALL,
                    )
                    if deps_match:
                        deps_block = deps_match.group(1)
                        deps_list = re.findall(r"['\"]([^'\"]+)['\"]", deps_block)
                        data["project"] = {"dependencies": deps_list}
                # Optional dependencies minimal parse
                opt_blocks = re.findall(
                    r"\[project\.optional-dependencies\](.*?)\n\[",
                    text,
                    re.DOTALL,
                )
                if opt_blocks:
                    # Very naive parser: group = [ ... ] on single lines
                    opt_data: dict[str, Any] = {}
                    for block in opt_blocks:
                        for line in block.splitlines():
                            m = re.match(r"\s*([A-Za-z0-9_-]+)\s*=\s*\[(.*?)\]", line)
                            if m:
                                group = m.group(1)
                                deps_block = m.group(2)
                                deps_list = re.findall(
                                    r"['\"]([^'\"]+)['\"]",
                                    deps_block,
                                )
                                opt_data[group] = deps_list
                    if opt_data:
                        data.setdefault("project", {})["optional-dependencies"] = opt_data

            project = data.get("project", {})

            # Main dependencies
            deps = project.get("dependencies", [])
            for dep in deps:
                dep_name = self._parse_dependency(dep)
                if dep_name:
                    self.dependencies[kit_name][dep_name] = dep
                    self.all_deps[dep_name] += 1

            # Optional dependencies
            optional = project.get("optional-dependencies", {})
            for group, group_deps in optional.items():
                for dep in group_deps:
                    dep_name = self._parse_dependency(dep)
                    if dep_name:
                        if "optional_dependencies" not in self.kit_info[kit_name]:
                            self.kit_info[kit_name]["optional_dependencies"] = {}
                        if group not in self.kit_info[kit_name]["optional_dependencies"]:
                            self.kit_info[kit_name]["optional_dependencies"][group] = {}

                        self.kit_info[kit_name]["optional_dependencies"][group][dep_name] = dep
                        self.optional_deps[group][dep_name] += 1

            # Build system dependencies
            build_system = data.get("build-system", {})
            build_deps = build_system.get("requires", [])
            for dep in build_deps:
                dep_name = self._parse_dependency(dep)
                if dep_name:
                    self.dev_deps[dep_name] += 1

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def _analyze_setup_py(self, kit_name: str, file_path: Path) -> None:
        """Analyze setup.py file (simplified - just scan for common patterns)."""
        try:
            with open(file_path) as f:
                content = f.read()

            # Look for install_requires pattern
            install_requires_match = re.search(
                r"install_requires\s*=\s*\[(.*?)\]",
                content,
                re.DOTALL,
            )
            if install_requires_match:
                deps_str = install_requires_match.group(1)
                deps = re.findall(r'["\']([^"\']+)["\']', deps_str)

                for dep in deps:
                    dep_name = self._parse_dependency(dep)
                    if dep_name:
                        self.dependencies[kit_name][dep_name] = dep
                        self.all_deps[dep_name] += 1

            # Look for extras_require pattern
            extras_match = re.search(
                r"extras_require\s*=\s*\{(.*?)\}",
                content,
                re.DOTALL,
            )
            if extras_match:
                extras_str = extras_match.group(1)
                # This is a simplified parser - could be improved
                for line in extras_str.split("\n"):
                    if ":" in line and "[" in line:
                        group_match = re.search(
                            r'["\']([^"\']+)["\']:\s*\[(.*?)\]',
                            line,
                        )
                        if group_match:
                            group = group_match.group(1)
                            deps_str = group_match.group(2)
                            deps = re.findall(r'["\']([^"\']+)["\']', deps_str)

                            for dep in deps:
                                dep_name = self._parse_dependency(dep)
                                if dep_name:
                                    if "optional_dependencies" not in self.kit_info[kit_name]:
                                        self.kit_info[kit_name]["optional_dependencies"] = {}
                                    if (
                                        group
                                        not in self.kit_info[kit_name]["optional_dependencies"]
                                    ):
                                        self.kit_info[kit_name]["optional_dependencies"][group] = {}

                                    self.kit_info[kit_name]["optional_dependencies"][group][
                                        dep_name
                                    ] = dep
                                    self.optional_deps[group][dep_name] += 1

        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def _analyze_requirements(self, kit_name: str, file_path: Path) -> None:
        """Analyze requirements.txt file."""
        try:
            with open(file_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        dep_name = self._parse_dependency(line)
                        if dep_name:
                            # Determine if it's a dev dependency based on file name
                            if "dev" in file_path.name.lower() or "test" in file_path.name.lower():
                                self.dev_deps[dep_name] += 1
                                if "dev_dependencies" not in self.kit_info[kit_name]:
                                    self.kit_info[kit_name]["dev_dependencies"] = {}
                                self.kit_info[kit_name]["dev_dependencies"][dep_name] = line
                            else:
                                self.dependencies[kit_name][dep_name] = line
                                self.all_deps[dep_name] += 1
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")

    def _parse_dependency(self, dep_spec: str) -> str | None:
        """Parse dependency specification to extract package name."""
        if not dep_spec or dep_spec.startswith("#"):
            return None

        # Remove common prefixes
        dep_spec = dep_spec.strip()

        # Handle various formats: pkg>=1.0, pkg==1.0, pkg[extra], etc.
        match = re.match(r"^([a-zA-Z0-9_-]+)", dep_spec)
        if match:
            return match.group(1).lower()

        return None

    def generate_summary(self) -> dict[str, Any]:
        """Generate summary statistics."""
        return {
            "total_kits": len(self.kit_info),
            "total_unique_dependencies": len(self.all_deps),
            "total_dev_dependencies": len(self.dev_deps),
            "most_common_dependencies": self.all_deps.most_common(20),
            "most_common_dev_dependencies": self.dev_deps.most_common(10),
            "kits_by_dependency_count": sorted(
                [(kit, len(deps)) for kit, deps in self.dependencies.items()],
                key=lambda x: x[1],
                reverse=True,
            ),
        }

    def suggest_consolidation_groups(self) -> dict[str, list[str]]:
        """Suggest dependency groupings for consolidation."""
        groups: dict[str, list[str]] = {
            "core": [],
            "data": [],
            "web": [],
            "infra": [],
            "ai": [],
            "ui": [],
            "dev": [],
        }

        # Common patterns for each group
        patterns = {
            "core": [
                "pydantic",
                "cattrs",
                "dependency-injector",
                "typing",
                "dataclasses",
            ],
            "data": [
                "asyncpg",
                "supabase",
                "redis",
                "sqlite",
                "psycopg",
                "sqlalchemy",
                "weaviate",
                "chromadb",
                "pinecone",
            ],
            "web": [
                "fastapi",
                "aiohttp",
                "uvicorn",
                "websockets",
                "grpcio",
                "starlette",
                "httpx",
                "requests",
            ],
            "infra": ["opentelemetry", "prometheus", "boto3", "azure", "google-cloud"],
            "ai": [
                "openai",
                "anthropic",
                "langchain",
                "transformers",
                "torch",
                "tensorflow",
            ],
            "ui": ["textual", "rich", "typer", "click", "curses"],
            "dev": ["pytest", "coverage", "ruff", "black", "mypy", "isort"],
        }

        # Categorize dependencies
        for dep_name, count in self.all_deps.items():
            categorized = False
            for group, keywords in patterns.items():
                if any(keyword in dep_name.lower() for keyword in keywords):
                    groups[group].append(f"{dep_name} (used by {count} kits)")
                    categorized = True
                    break

            if not categorized and count >= 3:  # Popular uncategorized dependencies
                groups["core"].append(f"{dep_name} (used by {count} kits)")

        return groups

    def create_unified_dependencies(self) -> dict[str, list[str]]:
        """Create unified dependency specification for consolidated package."""
        # Group dependencies by category
        unified: dict[str, list[str]] = {
            "core": [],
            "data": [],
            "web": [],
            "infra": [],
            "ai": [],
            "ui": [],
            "dev": [],
        }

        # Map dependencies to groups (simplified)
        dep_mapping = {
            "pydantic": "core",
            "aiohttp": "core",
            "structlog": "core",
            "asyncpg": "data",
            "supabase": "data",
            "redis": "data",
            "fastapi": "web",
            "uvicorn": "web",
            "websockets": "web",
            "opentelemetry-api": "infra",
            "prometheus-client": "infra",
            "boto3": "infra",
            "textual": "ui",
            "rich": "ui",
            "typer": "ui",
            "pytest": "dev",
            "coverage": "dev",
            "ruff": "dev",
        }

        # Categorize all dependencies
        for dep_name, count in self.all_deps.items():
            group = dep_mapping.get(dep_name, "core" if count >= 3 else None)
            if group:
                # Find the most common version spec for this dependency
                version_specs: list[str] = []
                for kit_deps in self.dependencies.values():
                    if dep_name in kit_deps:
                        version_specs.append(kit_deps[dep_name])

                # Use the most specific version if available
                if version_specs:
                    unified[group].append(max(version_specs, key=len))
                else:
                    unified[group].append(dep_name)

        return unified


def analyze_dependencies(root_path: Path) -> dict[str, Any]:
    """Analyze dependencies in the given path."""
    analyzer = DependencyAnalyzer(root_path)
    return analyzer.analyze_all()


def render_mermaid(analysis: dict[str, Any], min_count: int = 3) -> str:
    """Render dependency analysis as Mermaid diagram."""
    kit_deps: dict[str, dict[str, str]] = analysis.get("kit_dependencies", {})
    # Compute counts from summary
    most_common: list[tuple[str, int]] = analysis.get("summary", {}).get(
        "most_common_dependencies", []
    )
    top_deps = [dep for dep, cnt in most_common if cnt >= min_count]

    # Build edge list kit -> dep if kit uses dep in top_deps
    edges: list[tuple[str, str]] = []
    kits: list[str] = sorted(kit_deps.keys())

    for kit, deps in kit_deps.items():
        for dep in deps:
            if dep in top_deps:
                edges.append((kit, dep))

    def sanitize(name: str) -> str:
        return name.lower().replace("-", "_").replace(" ", "_").replace("/", "_")

    # Build Mermaid content
    lines: list[str] = []
    lines.append("# Dependency Graph (Mermaid)")
    lines.append("")
    lines.append(
        "This graph shows kit-to-dependency relationships for dependencies "
        f"used by at least {min_count} kits."
    )
    lines.append("")
    lines.append("```mermaid")
    lines.append("graph LR")
    lines.append("  %% Kits")
    lines.append("  subgraph Kits")
    for kit in kits:
        lines.append(f'    kit_{sanitize(kit)}["{kit}"]')
    lines.append("  end")
    lines.append("  %% Dependencies (top)")
    lines.append(f"  subgraph Deps_>={min_count}")
    for dep in top_deps:
        lines.append(f'    dep_{sanitize(dep)}["{dep}"]')
    lines.append("  end")
    lines.append("  %% Edges")
    for kit, dep in edges:
        lines.append(f"  kit_{sanitize(kit)} --> dep_{sanitize(dep)}")
    lines.append("```")

    return "\n".join(lines)
