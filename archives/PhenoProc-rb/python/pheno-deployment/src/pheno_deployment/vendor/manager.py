"""
High level vendoring manager.
"""

from __future__ import annotations

import shutil
import sys
import time
from pathlib import Path
from typing import TYPE_CHECKING

from .config import DEFAULT_VENDOR_DIR, PACKAGE_MAPPINGS
from .discovery import detect_used_packages, resolve_pheno_sdk_root, scan_packages
from .fs import copy_package, handle_kinfra
from .validation import test_imports, validate_vendored
from .writers import (
    create_sitecustomize,
    generate_manifest,
    generate_prod_requirements,
    write_vendor_init,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from .models import PackageInfo


class PhenoVendor:
    """
    Vendoring manager for pheno-sdk packages.
    """

    def __init__(
        self,
        project_root: Path | None = None,
        pheno_sdk_root: Path | None = None,
        vendor_dir: str = DEFAULT_VENDOR_DIR,
    ):
        self.project_root = Path(project_root or Path.cwd()).resolve()
        self.pheno_sdk_root = resolve_pheno_sdk_root(self.project_root, pheno_sdk_root)
        self.vendor_dir = self.project_root / vendor_dir
        self.packages: dict[str, PackageInfo] = scan_packages(self.pheno_sdk_root, PACKAGE_MAPPINGS)

    def _selected_packages(self, packages: list[str] | None, auto_detect: bool) -> set[str]:
        if packages is not None:
            return set(packages)
        if auto_detect:
            return detect_used_packages(self.project_root, self.packages)
        return {
            name for name, info in self.packages.items() if info.is_available and info.has_setup
        }

    def vendor_packages(
        self,
        packages: list[str] | None = None,
        auto_detect: bool = True,
        clean: bool = True,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> tuple[dict[str, bool], dict[str, float]]:
        """
        Vendor the requested packages into the vendor directory.
        """
        results: dict[str, bool] = {}
        timings: dict[str, float] = {}

        packages_to_vendor = self._selected_packages(packages, auto_detect)

        if clean and self.vendor_dir.exists():
            shutil.rmtree(self.vendor_dir)

        write_vendor_init(self.vendor_dir)

        total = len(packages_to_vendor)
        for idx, module_name in enumerate(sorted(packages_to_vendor), 1):
            start_time = time.time()
            if progress_callback:
                progress_callback(module_name, idx, total)

            pkg_info = self.packages.get(module_name)
            if not pkg_info or not pkg_info.is_available or not pkg_info.has_setup:
                results[module_name] = False
                timings[module_name] = time.time() - start_time
                continue

            try:
                copy_package(pkg_info, self.vendor_dir)
                results[module_name] = True
            except Exception as exc:
                print(f"Failed to vendor {module_name}: {exc}")
                results[module_name] = False

            timings[module_name] = time.time() - start_time

        handle_kinfra(self.pheno_sdk_root, self.vendor_dir)

        return results, timings

    def generate_prod_requirements(self, output_file: Path | None = None) -> Path:
        """
        Generate production requirements file.
        """
        return generate_prod_requirements(self.project_root, output_file)

    def create_sitecustomize(self) -> Path:
        """
        Create sitecustomize.py that points to the vendor directory.
        """
        return create_sitecustomize(self.project_root, self.vendor_dir.name)

    def generate_manifest(self) -> Path:
        """
        Generate a manifest of vendored packages.
        """
        return generate_manifest(self.vendor_dir, self.pheno_sdk_root)

    def validate_vendored(self, packages: list[str] | None = None) -> dict[str, tuple[bool, str]]:
        """
        Validate vendored packages.
        """
        return validate_vendored(self.vendor_dir, packages)

    def test_imports(self, packages: list[str] | None = None) -> dict[str, tuple[bool, str]]:
        """
        Attempt to import vendored packages.
        """
        original_path = list(sys.path)
        try:
            vendor_str = str(self.vendor_dir)
            if vendor_str not in sys.path:
                sys.path.insert(0, vendor_str)
            return test_imports(self.vendor_dir, packages)
        finally:
            sys.path[:] = original_path

    def clean(self) -> bool:
        """
        Remove the vendor directory.
        """
        if self.vendor_dir.exists():
            shutil.rmtree(self.vendor_dir)
            return True
        return False

    def vendor_all(
        self,
        auto_detect: bool = True,
        validate: bool = True,
        progress_callback: Callable[[str, int, int], None] | None = None,
    ) -> tuple[bool, dict[str, float]]:
        """
        Complete vendoring workflow.
        """
        timings: dict[str, float] = {}
        overall_start = time.time()

        print(f"Vendoring pheno-sdk packages to {self.vendor_dir}")
        print(f"Source: {self.pheno_sdk_root}")
        print()

        start = time.time()
        results, package_timings = self.vendor_packages(
            auto_detect=auto_detect,
            progress_callback=progress_callback,
        )
        timings["vendoring"] = time.time() - start
        timings.update(package_timings)

        successful = sum(1 for success in results.values() if success)
        print(f"Vendored {successful}/{len(results)} packages")

        print("\nGenerating production files...")
        start = time.time()
        self.generate_prod_requirements()
        timings["requirements"] = time.time() - start
        print("  Created requirements-prod.txt")

        start = time.time()
        self.create_sitecustomize()
        timings["sitecustomize"] = time.time() - start
        print("  Created sitecustomize.py")

        start = time.time()
        self.generate_manifest()
        timings["manifest"] = time.time() - start
        print("  Created VENDOR_MANIFEST.txt")

        if validate:
            print("\nValidating vendored packages...")
            start = time.time()
            validation_results = self.validate_vendored()
            timings["validation"] = time.time() - start

            for pkg_name, (success, message) in validation_results.items():
                status = "✓" if success else "✗"
                print(f"  {status} {pkg_name}: {message}")

            all_valid = all(success for success, _ in validation_results.values())
            timings["total"] = time.time() - overall_start

            if all_valid:
                print("\n✓ All packages validated successfully!")
                return True, timings

            print("\n✗ Some packages failed validation")
            return False, timings

        timings["total"] = time.time() - overall_start
        return successful > 0, timings


__all__ = ["PhenoVendor"]
