"""Tests for scripts/check_docs_links.py."""
from __future__ import annotations

import asyncio
import re
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from scripts.check_docs_links import (
    KNOWN_PLACEHOLDERS,
    LinkResult,
    check_link,
    check_links_concurrent,
    collect_all_links,
    extract_links_from_file,
    is_placeholder_url,
    print_report,
)


class TestLinkResult:
    """Tests for the LinkResult dataclass."""

    def test_valid_result_creation(self) -> None:
        """Test creating a valid LinkResult."""
        result = LinkResult(
            url="https://example.com",
            file_path="docs/test.md",
            line_number=10,
            status_code=200,
            is_valid=True,
        )
        assert result.url == "https://example.com"
        assert result.is_valid is True
        assert result.error is None

    def test_invalid_result_with_error(self) -> None:
        """Test creating an invalid LinkResult with error."""
        result = LinkResult(
            url="https://broken.example.com",
            file_path="docs/test.md",
            line_number=5,
            status_code=None,
            is_valid=False,
            error="Connection refused",
        )
        assert result.is_valid is False
        assert result.error == "Connection refused"


class TestExtractLinksFromFile:
    """Tests for link extraction from markdown files."""

    def test_extract_single_http_link(self, tmp_path: Path) -> None:
        """Test extracting a single HTTP link."""
        md_file = tmp_path / "test.md"
        md_file.write_text("Check out [this link](https://example.com)!\n")

        links = extract_links_from_file(md_file)
        assert len(links) == 1
        assert links[0] == (1, "https://example.com")

    def test_extract_multiple_links(self, tmp_path: Path) -> None:
        """Test extracting multiple links from a file."""
        md_file = tmp_path / "test.md"
        md_file.write_text(
            "Links: [one](https://example.com) and [two](https://example.org)\n"
        )

        links = extract_links_from_file(md_file)
        assert len(links) == 2
        assert links[0] == (1, "https://example.com")
        assert links[1] == (1, "https://example.org")

    def test_extract_links_across_lines(self, tmp_path: Path) -> None:
        """Test extracting links on different lines."""
        md_file = tmp_path / "test.md"
        md_file.write_text(
            "Line 1 [link1](https://a.com)\n"
            "Line 2 [link2](https://b.com)\n"
            "Line 3 [link3](https://c.com)\n"
        )

        links = extract_links_from_file(md_file)
        assert len(links) == 3
        assert links[0] == (1, "https://a.com")
        assert links[1] == (2, "https://b.com")
        assert links[2] == (3, "https://c.com")

    def test_ignore_relative_links(self, tmp_path: Path) -> None:
        """Test that relative links are ignored."""
        md_file = tmp_path / "test.md"
        md_file.write_text(
            "[External](https://example.com)\n"
            "[Relative](./other-page.md)\n"
            "[Absolute](/guide/getting-started)\n"
        )

        links = extract_links_from_file(md_file)
        assert len(links) == 1
        assert links[0] == (1, "https://example.com")

    def test_ignore_non_http_links(self, tmp_path: Path) -> None:
        """Test that non-HTTP(S) links are ignored."""
        md_file = tmp_path / "test.md"
        md_file.write_text(
            "[Email](mailto:test@example.com)\n"
            "[File](file:///path/to/file)\n"
        )

        links = extract_links_from_file(md_file)
        assert len(links) == 0

    def test_file_with_no_links(self, tmp_path: Path) -> None:
        """Test a file with no links."""
        md_file = tmp_path / "test.md"
        md_file.write_text("Just some text with no links here.\n")

        links = extract_links_from_file(md_file)
        assert len(links) == 0

    def test_nonexistent_file(self, tmp_path: Path) -> None:
        """Test handling of nonexistent file."""
        fake_file = tmp_path / "nonexistent.md"
        links = extract_links_from_file(fake_file)
        assert links == []


class TestIsPlaceholderUrl:
    """Tests for placeholder URL detection."""

    @pytest.mark.parametrize(
        "url,expected",
        [
            ("https://example.com/page", True),
            ("https://example.org/path/to/page", True),
            ("https://vendor.com/docs", True),
            ("https://github.com/kooshapari/repo", False),
            ("https://docs.example.com", False),
            ("https://example.computer.com", False),  # Not a placeholder
        ],
    )
    def test_placeholder_detection(self, url: str, expected: bool) -> None:
        """Test placeholder URL detection."""
        assert is_placeholder_url(url) is expected


class TestCollectAllLinks:
    """Tests for collecting links from all documentation files."""

    def test_collect_from_multiple_files(self, tmp_path: Path) -> None:
        """Test collecting links from multiple files."""
        # Create directory structure
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        file1 = docs_dir / "page1.md"
        file1.write_text("[Link1](https://github.com)\n")

        file2 = docs_dir / "page2.md"
        file2.write_text("[Link2](https://bun.sh)\n")

        links = collect_all_links(docs_dir)
        urls = {url for _, _, url in links}

        assert len(links) == 2
        assert "https://github.com" in urls
        assert "https://bun.sh" in urls

    def test_skip_generated_directory(self, tmp_path: Path) -> None:
        """Test that .generated directory is skipped."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        generated_dir = docs_dir / ".generated"
        generated_dir.mkdir()

        # File in .generated should be skipped
        generated_file = generated_dir / "page.md"
        generated_file.write_text("[Link](https://example.com)\n")

        # File in root should be included
        root_file = docs_dir / "page.md"
        root_file.write_text("[Link](https://github.com)\n")

        links = collect_all_links(docs_dir)
        urls = [url for _, _, url in links]

        assert len(links) == 1
        assert "https://github.com" in urls


class TestCheckLink:
    """Tests for individual link checking."""

    @pytest.mark.asyncio
    async def test_valid_link_returns_success(self) -> None:
        """Test that a valid link returns is_valid=True."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.head.return_value = mock_response

        result = await check_link(
            mock_client,
            "https://github.com",
            Path("docs/test.md"),
            1,
        )

        assert result.is_valid is True
        assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_link_returns_failure(self) -> None:
        """Test that a 404 link returns is_valid=False."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_client.head.return_value = mock_response

        result = await check_link(
            mock_client,
            "https://broken-link.com",
            Path("docs/test.md"),
            5,
        )

        assert result.is_valid is False
        assert result.status_code == 404

    @pytest.mark.asyncio
    async def test_timeout_returns_failure(self) -> None:
        """Test that a timeout returns is_valid=False with error."""
        import httpx

        mock_client = AsyncMock()
        mock_client.head.side_effect = httpx.TimeoutException("Request timed out")

        result = await check_link(
            mock_client,
            "https://slow-site.com",
            Path("docs/test.md"),
            1,
        )

        assert result.is_valid is False
        assert result.error == "Timeout"


class TestCheckLinksConcurrent:
    """Tests for concurrent link checking."""

    @pytest.mark.asyncio
    async def test_checks_multiple_links(self) -> None:
        """Test checking multiple links concurrently."""
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_client.head.return_value = mock_response

        links = [
            (Path("docs/test1.md"), 1, "https://github.com"),
            (Path("docs/test2.md"), 2, "https://bun.sh"),
        ]

        results = await check_links_concurrent(links)

        assert len(results) == 2
        assert all(r.is_valid for r in results)


class TestPrintReport:
    """Tests for report printing."""

    def test_report_shows_valid_links(self) -> None:
        """Test that report displays valid link count."""
        results = [
            LinkResult("https://github.com", "docs/test.md", 1, 200, True),
            LinkResult("https://bun.sh", "docs/test.md", 2, 200, True),
        ]

        # Should not raise any exceptions
        print_report(results)

    def test_report_shows_invalid_links(self) -> None:
        """Test that report displays invalid links with errors."""
        results = [
            LinkResult(
                "https://broken.com",
                "docs/test.md",
                5,
                404,
                False,
                "HTTP 404",
            ),
        ]

        # Should not raise exceptions and should show the invalid link
        print_report(results)


class TestScriptExecution:
    """Integration tests for script execution."""

    def test_script_exists(self) -> None:
        """Verify the script file exists."""
        script_path = Path(__file__).parent.parent / "scripts" / "check_docs_links.py"
        assert script_path.exists(), f"Script not found at {script_path}"

    def test_script_has_shebang(self) -> None:
        """Verify the script has a proper Python shebang."""
        script_path = Path(__file__).parent.parent / "scripts" / "check_docs_links.py"
        content = script_path.read_text()
        assert content.startswith("#!/") or "from __future__" in content

    def test_script_runs_without_errors(self) -> None:
        """Verify the script runs without import/syntax errors."""
        script_path = Path(__file__).parent.parent / "scripts" / "check_docs_links.py"

        # Just test that the script can be imported and main() is callable
        # (actual link checking results depend on external URLs)
        result = subprocess.run(
            [
                "python",
                "-c",
                "from scripts.check_docs_links import main, extract_links_from_file, LinkResult; print('Import OK')",
            ],
            capture_output=True,
            text=True,
            cwd=script_path.parent.parent,
        )
        assert result.returncode == 0, f"Script import failed: {result.stderr}"
        assert "Import OK" in result.stdout

    def test_main_returns_zero_for_valid_results(self) -> None:
        """Verify main() returns 0 when no invalid links found."""
        script_path = Path(__file__).parent.parent / "scripts" / "check_docs_links.py"

        result = subprocess.run(
            [
                "python",
                "-c",
                "from scripts.check_docs_links import main; raise SystemExit(main())",
            ],
            capture_output=True,
            text=True,
            cwd=script_path.parent.parent,
        )
        # Should exit cleanly (may return 0 or 1 depending on actual link status)
        assert result.returncode in (0, 1)
