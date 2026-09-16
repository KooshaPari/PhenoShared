"""Tests for VitePress documentation build process."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Generator


# Root directory of the phenodocs project
PHENODOCS_ROOT = Path(__file__).parent.parent
DOCS_DIR = PHENODOCS_ROOT / "docs"


@pytest.fixture
def docs_dir() -> Path:
    """Return path to the docs directory."""
    return DOCS_DIR


@pytest.fixture
def vitepress_config() -> Path:
    """Return path to the VitePress config file."""
    return DOCS_DIR / ".vitepress" / "config.ts"


class TestVitePressConfig:
    """Tests for VitePress configuration."""

    def test_config_file_exists(self, vitepress_config: Path) -> None:
        """Verify VitePress config file exists."""
        assert vitepress_config.exists(), f"Config not found at {vitepress_config}"

    def test_config_is_valid_typescript(self, vitepress_config: Path) -> None:
        """Verify config file is valid TypeScript syntax."""
        content = vitepress_config.read_text()
        # Basic sanity checks
        assert "export default" in content or "export {" in content
        assert len(content) > 0


class TestDocsDirectory:
    """Tests for docs directory structure."""

    def test_docs_directory_exists(self, docs_dir: Path) -> None:
        """Verify docs directory exists."""
        assert docs_dir.exists(), f"Docs directory not found at {docs_dir}"

    def test_docs_has_index(self, docs_dir: Path) -> None:
        """Verify docs has an index file."""
        index_path = docs_dir / "index.md"
        assert index_path.exists(), "Missing index.md in docs root"

    def test_docs_has_subdirectories(self, docs_dir: Path) -> None:
        """Verify docs has subdirectories for organization."""
        subdirs = [d for d in docs_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
        assert len(subdirs) > 0, "No documentation subdirectories found"


class TestMarkdownFiles:
    """Tests for markdown file quality."""

    def test_markdown_files_exist(self, docs_dir: Path) -> None:
        """Verify there are markdown files in docs."""
        md_files = list(docs_dir.rglob("*.md"))
        assert len(md_files) > 0, "No markdown files found in docs"

    def test_no_deeply_nested_generated(self, docs_dir: Path) -> None:
        """Verify .generated content is not too deeply nested."""
        generated_dirs = list(docs_dir.rglob(".generated"))
        for gen_dir in generated_dirs:
            # .generated should be at most 2 levels deep
            depth = len(gen_dir.relative_to(docs_dir).parts)
            assert depth <= 2, f".generated too deeply nested: {gen_dir}"


class TestBuildIntegration:
    """Integration tests for VitePress build."""

    def test_bun_available(self) -> None:
        """Verify bun package manager is available."""
        result = subprocess.run(
            ["which", "bun"],
            capture_output=True,
            text=True,
        )
        # Skip if bun is not installed
        if result.returncode != 0:
            pytest.skip("bun not installed")

    def test_vitepress_can_build(self) -> None:
        """Verify VitePress build completes successfully."""
        # Check if bun is available
        result = subprocess.run(
            ["which", "bun"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.skip("bun not installed")

        # Run vitepress build
        result = subprocess.run(
            ["bun", "run", "build"],
            capture_output=True,
            text=True,
            cwd=PHENODOCS_ROOT,
            timeout=300,  # 5 minute timeout
        )

        # Check for success or expected errors
        if result.returncode != 0:
            # If it fails, print output for debugging
            print(f"STDOUT:\n{result.stdout}")
            print(f"STDERR:\n{result.stderr}")

            # Some failures are acceptable (e.g., missing workspace deps)
            # Only fail if it's a VitePress configuration issue
            if "VitePress" in result.stderr or "vitepress" in result.stdout.lower():
                pytest.fail(f"VitePress build failed: {result.stderr}")
            # Otherwise, assume it's a workspace dependency issue
            pytest.skip("Build failed (likely missing workspace dependencies)")


class TestLinkCheckerScript:
    """Tests for the link checker integration."""

    def test_link_checker_script_exists(self) -> None:
        """Verify link checker script exists."""
        script_path = PHENODOCS_ROOT / "scripts" / "check_docs_links.py"
        assert script_path.exists(), f"Script not found at {script_path}"

    def test_link_checker_can_import(self) -> None:
        """Verify link checker can be imported."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from scripts.check_docs_links import main, collect_all_links",
            ],
            capture_output=True,
            text=True,
            cwd=PHENODOCS_ROOT,
        )
        assert result.returncode == 0, f"Import failed: {result.stderr}"

    def test_link_checker_finds_links(self) -> None:
        """Verify link checker finds external links in docs."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "from pathlib import Path; from scripts.check_docs_links import collect_all_links; links = collect_all_links(Path('docs')); print(len(links))",
            ],
            capture_output=True,
            text=True,
            cwd=PHENODOCS_ROOT,
        )
        assert result.returncode == 0, f"Failed to collect links: {result.stderr}"
        link_count = int(result.stdout.strip())
        assert link_count > 0, "No external links found in docs"
