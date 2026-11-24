import os
import json
import subprocess
from typing import List, Dict, Any, Set
from rich.console import Console

console = Console()

class DependencyResolver:
    def __init__(self, root_path: str):
        self.root_path = root_path
        self._resolved_cache: Set[str] = set()

    def resolve_python(self) -> List[Dict[str, Any]]:
        """Resolve Python dependencies from multiple sources."""
        deps = []
        
        # Try different Python dependency file formats
        python_files = [
            ("requirements.txt", self._parse_requirements),
            ("pyproject.toml", self._parse_pyproject),
            ("setup.py", self._parse_setup_py),
            ("Pipfile", self._parse_pipfile),
        ]
        
        for filename, parser in python_files:
            filepath = os.path.join(self.root_path, filename)
            if os.path.exists(filepath):
                parsed = parser(filepath)
                for dep in parsed:
                    if dep['name'] not in self._resolved_cache:
                        deps.append(dep)
                        self._resolved_cache.add(dep['name'])
        
        return deps

    def resolve_npm(self) -> List[Dict[str, Any]]:
        """Resolve NPM/Yarn dependencies."""
        deps = []
        
        # Check for package.json
        package_json = os.path.join(self.root_path, "package.json")
        if os.path.exists(package_json):
            with open(package_json, "r") as f:
                try:
                    package_data = json.load(f)
                    
                    # Dependencies
                    for name, version in package_data.get("dependencies", {}).items():
                        if name not in self._resolved_cache:
                            deps.append({
                                "name": name,
                                "version": version,
                                "type": "npm",
                                "source": "npm",
                                "dev": False
                            })
                            self._resolved_cache.add(name)
                    
                    # Dev Dependencies
                    for name, version in package_data.get("devDependencies", {}).items():
                        if name not in self._resolved_cache:
                            deps.append({
                                "name": name,
                                "version": version,
                                "type": "npm",
                                "source": "npm",
                                "dev": True
                            })
                            self._resolved_cache.add(name)
                except json.JSONDecodeError:
                    console.print(f"[yellow]Warning: Invalid JSON in {package_json}")
        
        return deps

    def _parse_requirements(self, filepath: str) -> List[Dict[str, Any]]:
        """Parse requirements.txt file."""
        deps = []
        try:
            with open(filepath, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        # Handle various formats: pkg, pkg==1.0, pkg>=1.0, etc.
                        pkg_name = line.split(">=")[0].split("==")[0].split("<")[0].split(">")[0].split("~=")[0].strip()
                        deps.append({
                            "name": pkg_name,
                            "spec": line,
                            "type": "python",
                            "source": "pypi"
                        })
        except Exception as e:
            console.print(f"[red]Error parsing {filepath}: {e}")
        return deps

    def _parse_pyproject(self, filepath: str) -> List[Dict[str, Any]]:
        """Parse pyproject.toml file."""
        # Simplified: would need tomli in production
        # For now, return empty
        return []

    def _parse_setup_py(self, filepath: str) -> List[Dict[str, Any]]:
        """Parse setup.py file."""
        # Complex: would need AST parsing
        # For now, return empty
        return []

    def _parse_pipfile(self, filepath: str) -> List[Dict[str, Any]]:
        """Parse Pipfile (pipenv)."""
        # Simplified: would need toml parser
        # For now, return empty
        return []

    def get_all_dependencies(self) -> List[Dict[str, Any]]:
        """Resolve all dependencies across all package managers."""
        return self.resolve_python() + self.resolve_npm()

    def get_dependency_metadata(self, package_name: str, package_type: str) -> Dict[str, Any]:
        """Get detailed metadata for a specific package."""
        # Placeholder for package registry lookups (PyPI, npm)
        return {
            "name": package_name,
            "type": package_type,
            "metadata_fetched": False
        }
