#!/usr/bin/env python3
"""
Pheno-SDK Vendor Management System Automated local package vendoring with setup/cleanup
capabilities.
"""

import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class PackageInfo:
    """
    Package information for vendor management.
    """

    name: str
    version: str
    source: str
    files: list[str]
    checksum: str
    vendor_path: str


class VendorManager:
    """
    Manages vendored dependencies and package synchronization.
    """

    def __init__(self, vendor_dir: str = "vendor"):
        self.vendor_dir = Path(vendor_dir)
        self.lock_file = self.vendor_dir / "vendor.lock.json"
        self.metadata_file = self.vendor_dir / "metadata.json"
        self.packages: dict[str, PackageInfo] = {}

        # Ensure vendor directory exists
        self.vendor_dir.mkdir(exist_ok=True)

        # Load existing vendor configuration
        self._load_metadata()

    def _load_metadata(self):
        """
        Load vendor metadata from disk.
        """
        if self.lock_file.exists():
            try:
                with open(self.lock_file) as f:
                    data = json.load(f)
                    for name, info in data.items():
                        self.packages[name] = PackageInfo(**info)
            except (json.JSONDecodeError, ValueError):
                print(f"Warning: Could not parse vendor lock file {self.lock_file}")

        if self.metadata_file.exists():
            try:
                with open(self.metadata_file) as f:
                    self.metadata = json.load(f)
            except (json.JSONDecodeError, ValueError):
                self.metadata = {}
        else:
            self.metadata = {}

    def _save_metadata(self):
        """
        Save vendor metadata to disk.
        """
        # Save lock file
        lock_data = {
            name: {
                "name": pkg.name,
                "version": pkg.version,
                "source": pkg.source,
                "files": pkg.files,
                "checksum": pkg.checksum,
                "vendor_path": pkg.vendor_path,
            }
            for name, pkg in self.packages.items()
        }

        with open(self.lock_file, "w") as f:
            json.dump(lock_data, f, indent=2)

        # Save metadata
        with open(self.metadata_file, "w") as f:
            json.dump(self.metadata, f, indent=2)

    def add_package(
        self,
        package_name: str,
        *,
        version: str | None = None,
        source: str | None = None,
        files: list[str] | None = None,
        force: bool = False,
    ) -> bool:
        """
        Add a package to vendor directory.
        """
        if package_name in self.packages and not force:
            print(f"Package {package_name} already exists. Use --force to override.")
            return False

        # Get package information
        try:
            if not version:
                version = self._get_package_version(package_name)

            if not source:
                source = self._get_package_source(package_name, version)

            if not files:
                files = self._get_package_files(package_name)

            # Create package vendor directory
            pkg_vendor_dir = self.vendor_dir / package_name
            pkg_vendor_dir.mkdir(exist_ok=True)

            # Download and extract package
            if source.startswith("http"):
                self._download_and_extract(source, pkg_vendor_dir)
            else:
                # Copy from existing site-packages
                self._copy_from_site_packages(package_name, pkg_vendor_dir)

            # Generate checksum
            checksum = self._generate_checksum(pkg_vendor_dir)

            # Create package info
            pkg_info = PackageInfo(
                name=package_name,
                version=version,
                source=source,
                files=files,
                checksum=checksum,
                vendor_path=str(pkg_vendor_dir),
            )

            self.packages[package_name] = pkg_info

            # Create __init__.py files for proper Python imports
            self._create_init_files(pkg_vendor_dir)

            # Update metadata
            self.metadata[package_name] = {
                "added_at": str(Path.cwd()),
                "added_by": "vendor_manager",
                "purpose": "dependency vendoring",
            }

            self._save_metadata()

            print(f"✅ Added {package_name}@{version} to vendor directory")
            return True

        except Exception as e:
            print(f"❌ Failed to add package {package_name}: {e}")
            return False

    def remove_package(self, package_name: str, force: bool = False) -> bool:
        """
        Remove a package from vendor directory.
        """
        if package_name not in self.packages:
            print(f"Package {package_name} not found in vendor directory")
            return False

        try:
            pkg_info = self.packages[package_name]
            pkg_dir = Path(pkg_info.vendor_path)

            if pkg_dir.exists() and pkg_dir.is_dir():
                shutil.rmtree(pkg_dir)

            del self.packages[package_name]

            if package_name in self.metadata:
                del self.metadata[package_name]

            self._save_metadata()

            print(f"✅ Removed {package_name} from vendor directory")
            return True

        except Exception as e:
            print(f"❌ Failed to remove package {package_name}: {e}")
            return False

    def update_package(
        self,
        package_name: str,
        *,
        version: str | None = None,
        force: bool = False,
    ) -> bool:
        """
        Update a vendored package.
        """
        if package_name not in self.packages:
            print(f"Package {package_name} not found in vendor directory")
            return self.add_package(package_name, version=version, force=force)

        return self.add_package(package_name, version=version, force=True)

    def sync_packages(self) -> bool:
        """
        Synchronize all vendored packages with their sources.
        """
        success = True

        for package_name in self.packages:
            try:
                pkg_info = self.packages[package_name]
                current_checksum = self._generate_checksum(Path(pkg_info.vendor_path))

                if current_checksum != pkg_info.checksum:
                    print(f"🔄 Updating {package_name}...")
                    if not self.update_package(package_name, force=True):
                        success = False
                else:
                    print(f"✅ {package_name} is up to date")

            except Exception as e:
                print(f"❌ Failed to sync {package_name}: {e}")
                success = False

        return success

    def list_packages(self, detailed: bool = False) -> list[dict[str, Any]]:
        """
        List all vendored packages.
        """
        packages = []

        for name, pkg in self.packages.items():
            pkg_data = {
                "name": pkg.name,
                "version": pkg.version,
                "source": pkg.source,
                "files_count": len(pkg.files),
                "vendor_path": pkg.vendor_path,
            }

            if detailed:
                pkg_path = Path(pkg.vendor_path)
                if pkg_path.exists():
                    pkg_data.update(
                        {
                            "size_mb": self._get_directory_size(pkg_path) / (1024 * 1024),
                            "file_count": len(list(pkg_path.rglob("*"))),
                            "last_modified": (
                                os.path.getmtime(pkg_path) if pkg_path.exists() else None
                            ),
                            "checksum": pkg.checksum,
                        },
                    )

            packages.append(pkg_data)

        return packages

    def verify_packages(self) -> dict[str, dict[str, Any]]:
        """
        Verify all vendored packages.
        """
        results = {}

        for name, pkg in self.packages.items():
            pkg_path = Path(pkg.vendor_path)

            result = {
                "exists": pkg_path.exists(),
                "is_package": pkg_path.is_dir(),
                "checksum_valid": False,
                "files_present": 0,
                "files_missing": [],
            }

            if pkg_path.exists():
                # Check checksum
                current_checksum = self._generate_checksum(pkg_path)
                result["checksum_valid"] = current_checksum == pkg.checksum

                # Check files
                for file in pkg.files:
                    file_path = pkg_path / file
                    if file_path.exists():
                        result["files_present"] += 1
                    else:
                        result["files_missing"].append(file)

            results[name] = result

        return results

    def clean_vendor_dir(self, dry_run: bool = False) -> list[str]:
        """
        Clean up vendor directory.
        """
        removed = []

        # Remove directories not in lock file
        for item in self.vendor_dir.iterdir():
            if item.is_dir() and item.stem not in self.packages:
                if not dry_run:
                    shutil.rmtree(item)
                removed.append(str(item))

        # Clean metadata
        files_to_clean = []
        for file in self.lock_file.parent.glob("vendor.*"):
            if file != self.lock_file:
                files_to_clean.append(file)

        for file in files_to_clean:
            if not dry_run:
                file.unlink()
            removed.append(str(file))

        return removed

    def _get_package_version(self, package_name: str) -> str:
        """
        Get current version of an installed package.
        """
        try:
            import importlib.metadata

            return importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            # Fallback to pip command
            result = subprocess.run(
                ["pip", "show", package_name], check=False, capture_output=True, text=True
            )

            for line in result.stdout.split("\n"):
                if line.startswith("Version:"):
                    return line.split(":")[1].strip()

            raise ValueError(f"Could not determine version for {package_name}")

    def _get_package_source(self, package_name: str, version: str) -> str:
        """
        Get source URL for a package.
        """
        # Try PyPI API
        import urllib.request

        try:
            with urllib.request.urlopen(
                f"https://pypi.org/pypi/{package_name}/{version}/json",
            ) as response:
                data = json.loads(response.read().decode())
                return data["urls"][0]["url"]  # Get first URL (usually source distribution)
        except:
            # Fallback to constructing URL
            return f"https://pypi.org/simple/{package_name}/"

    def _get_package_files(self, package_name: str) -> list[str]:
        """
        Get list of files in a package.
        """
        try:
            import importlib.util

            spec = importlib.util.find_spec(package_name)
            if spec and spec.origin:
                pkg_dir = Path(spec.origin).parent
                return [str(f.relative_to(pkg_dir)) for f in pkg_dir.rglob("*.py") if f.is_file()]

            return []
        except:
            return []

    def _download_and_extract(self, source_url: str, target_dir: Path):
        """
        Download and extract package from URL.
        """
        import urllib.request

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            urllib.request.urlretrieve(source_url, tmp_file.name)

            # Extract archive
            if source_url.endswith(".tar.gz") or source_url.endswith(".tgz"):
                with tarfile.open(tmp_file.name, "r:gz") as tar:
                    tar.extractall(target_dir.parent)
            elif source_url.endswith(".zip"):
                with zipfile.ZipFile(tmp_file.name, "r") as zip_ref:
                    zip_ref.extractall(target_dir.parent)

            os.unlink(tmp_file.name)

    def _copy_from_site_packages(self, package_name: str, target_dir: Path):
        """
        Copy package from site-packages to vendor directory.
        """
        import importlib.util

        spec = importlib.util.find_spec(package_name)
        if spec and spec.origin:
            source_dir = Path(spec.origin).parent
            if source_dir.exists():
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                shutil.copytree(source_dir, target_dir)
            else:
                raise FileNotFoundError(f"Package {package_name} not found in site-packages")
        else:
            raise ImportError(f"Could not find {package_name} in site-packages")

    def _generate_checksum(self, directory: Path) -> str:
        """
        Generate checksum for directory contents.
        """
        import hashlib

        hash_md5 = hashlib.md5()

        for file_path in sorted(directory.rglob("*")):
            if file_path.is_file():
                with open(file_path, "rb") as f:
                    # Update with relative path and content
                    rel_path = file_path.relative_to(directory)
                    hash_md5.update(str(rel_path).encode("utf-8"))
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)

        return hash_md5.hexdigest()

    def _get_directory_size(self, directory: Path) -> int:
        """
        Get total size of directory in bytes.
        """
        total_size = 0
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    def _create_init_files(self, directory: Path):
        """
        Create __init__.py files for proper Python imports.
        """
        for dir_path in directory.rglob("*/"):
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                init_file.touch()


def main():
    """
    CLI entry point for vendor manager.
    """
    import argparse

    parser = argparse.ArgumentParser(description="Pheno-SDK Vendor Management")
    parser.add_argument(
        "command",
        choices=["add", "remove", "update", "sync", "list", "verify", "clean", "setup"],
        help="Command to execute",
    )
    parser.add_argument("package", nargs="?", help="Package name")
    parser.add_argument("--version", help="Package version")
    parser.add_argument("--source", help="Package source URL")
    parser.add_argument("--force", action="store_true", help="Force operation")
    parser.add_argument("--detailed", action="store_true", help="Show detailed information")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't make changes)")
    parser.add_argument("--vendor-dir", default="vendor", help="Vendor directory")

    args = parser.parse_args()

    vendor_manager = VendorManager(args.vendor_dir)

    if args.command == "setup":
        print("🚀 Setting up vendor system...")
        vendor_manager.vendor_dir.mkdir(exist_ok=True)
        print("✅ Vendor system ready")

    elif args.command == "add" and args.package:
        success = vendor_manager.add_package(
            args.package,
            version=args.version,
            source=args.source,
            force=args.force,
        )
        sys.exit(0 if success else 1)

    elif args.command == "remove" and args.package:
        success = vendor_manager.remove_package(args.package, args.force)
        sys.exit(0 if success else 1)

    elif args.command == "update" and args.package:
        success = vendor_manager.update_package(
            args.package,
            version=args.version,
            force=args.force,
        )
        sys.exit(0 if success else 1)

    elif args.command == "sync":
        success = vendor_manager.sync_packages()
        sys.exit(0 if success else 1)

    elif args.command == "list":
        packages = vendor_manager.list_packages(detailed=args.detailed)

        if packages:
            print("\n📦 Vendored Packages:")
            for pkg in packages:
                if args.detailed:
                    print(f"  • {pkg['name']}@{pkg['version']}")
                    print(f"    Source: {pkg['source']}")
                    print(f"    Size: {pkg.get('size_mb', 0):.1f} MB")
                    print(f"    Files: {pkg.get('file_count', 0)}")
                    print(f"    Path: {pkg['vendor_path']}")
                    print()
                else:
                    print(f"  • {pkg['name']}@{pkg['version']}")
        else:
            print("No vendored packages found")

    elif args.command == "verify":
        results = vendor_manager.verify_packages()

        print("\n🔍 Package Verification:")
        for name, result in results.items():
            status = "✅ OK" if result["exists"] and result["checksum_valid"] else "❌ Issues"
            print(f"  • {name}: {status}")

            if result.get("files_missing"):
                print(f"    Missing files: {', '.join(result['files_missing'])}")

    elif args.command == "clean":
        removed = vendor_manager.clean_vendor_dir(dry_run=args.dry_run)

        if removed:
            print(f"\n{'Would remove' if args.dry_run else 'Removed'} {len(removed)} items:")
            for item in removed:
                print(f"  • {item}")
        else:
            print("No items to clean")


if __name__ == "__main__":
    main()
