import pytest
from pathlib import Path
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

# Test LinkResult
class TestLinkResult:
    def test_valid_result_creation(self):
        result = LinkResult(
            url="https://example.com",
            file_path=Path("/docs/readme.md"),
            line_number=1,
            status_code=200,
            is_valid=True,
        )
        assert result.url == "https://example.com"
        assert result.file_path == Path("/docs/readme.md")
        assert result.line_number == 1
        assert result.status_code == 200
        assert result.is_valid is True
        assert result.error is None

    def test_result_with_error(self):
        result = LinkResult(
            url="https://broken.example.com",
            file_path=Path("/docs/readme.md"),
            line_number=1,
            status_code=404,
            is_valid=False,
            error="Not Found",
        )
        assert result.is_valid is False
        assert result.error == "Not Found"

    def test_invalid_result(self):
        result = LinkResult(
            url="https://example.com",
            file_path=Path("/docs/readme.md"),
            line_number=1,
            status_code=500,
            is_valid=False,
        )
        assert result.is_valid is False

# Test is_placeholder_url
class TestPlaceholderDetection:
    def test_placeholder_detection(self):
        assert is_placeholder_url("https://example.com") is False
        assert is_placeholder_url("https://example.com/path") is False
        assert is_placeholder_url("https://example.com/path?q=1") is False
        for ph in KNOWN_PLACEHOLDERS:
            assert is_placeholder_url(ph) is True

    def test_custom_placeholder_detection(self):
        custom = ["https://custom.example.com/placeholder", "https://another.example.com/todo"]
        for url in custom:
            assert is_placeholder_url(url, custom_placeholders=custom) is True
        assert is_placeholder_url("https://real.example.com/page", custom_placeholders=custom) is False

# Test extract_links_from_file
class TestExtractLinks:
    def test_extract_links_from_file(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n\n[link](https://example.com)\n\nAnother [link2](https://example2.com) here.\n")
        links = extract_links_from_file(test_file)
        assert len(links) == 2
        assert links[0] == (3, "https://example.com")
        assert links[1] == (5, "https://example2.com")

    def test_extract_links_no_links(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n\nNo links here.\n")
        links = extract_links_from_file(test_file)
        assert links == []

    def test_extract_links_empty_file(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("")
        links = extract_links_from_file(test_file)
        assert links == []

    def test_extract_links_with_placeholders(self, tmp_path):
        test_file = tmp_path / "test.md"
        test_file.write_text("# Test\n\n[placeholder](https://placeholder.example.com)\n\n[real](https://real.example.com)\n")
        links = extract_links_from_file(test_file)
        assert len(links) == 2
        assert links[0] == (3, "https://placeholder.example.com")
        assert links[1] == (5, "https://real.example.com")

# Test collect_all_links
class TestCollectAllLinks:
    def test_collect_from_multiple_files(self, tmp_path):
        file1 = tmp_path / "file1.md"
        file1.write_text("[link1](https://example.com)\n")
        file2 = tmp_path / "file2.md"
        file2.write_text("[link2](https://example2.com)\n")
        result = collect_all_links([file1, file2])
        assert len(result) == 2
        assert result[0] == (file1, 1, "https://example.com")
        assert result[1] == (file2, 1, "https://example2.com")

    def test_collect_with_placeholders(self, tmp_path):
        file1 = tmp_path / "file1.md"
        file1.write_text("[placeholder](https://placeholder.example.com)\n")
        result = collect_all_links([file1])
        assert len(result) == 1
        assert result[0] == (file1, 1, "https://placeholder.example.com")

    def test_collect_skips_directories(self, tmp_path):
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        file1 = tmp_path / "file1.md"
        file1.write_text("[link1](https://example.com)\n")
        result = collect_all_links([file1, subdir])
        assert len(result) == 1
        assert result[0] == (file1, 1, "https://example.com")

# Test check_link
class TestCheckLink:
    def test_check_link_success(self, tmp_path):
        result = check_link(
            url="https://example.com",
            file_path=tmp_path / "test.md",
            line_number=1,
        )
        assert isinstance(result, LinkResult)
        assert result.url == "https://example.com"
        assert result.line_number == 1
        assert result.file_path == tmp_path / "test.md"

    def test_check_link_with_timeout(self, tmp_path):
        result = check_link(
            url="https://example.com",
            file_path=tmp_path / "test.md",
            line_number=1,
            timeout=1,
        )
        assert isinstance(result, LinkResult)

# Test check_links_concurrent
class TestCheckLinksConcurrent:
    def test_check_multiple_links(self, tmp_path):
        links = [
            (tmp_path / "test1.md", 1, "https://example.com"),
            (tmp_path / "test2.md", 2, "https://example2.com"),
        ]
        results = check_links_concurrent(links)
        assert len(results) == 2
        for result in results:
            assert isinstance(result, LinkResult)

    def test_empty_links(self):
        results = check_links_concurrent([])
        assert results == []

    def test_placeholder_links(self, tmp_path):
        links = [
            (tmp_path / "test1.md", 1, "https://placeholder.example.com"),
        ]
        results = check_links_concurrent(links)
        assert len(results) == 1
        assert results[0].is_valid is True
        assert results[0].status_code == 0

# Test print_report
class TestPrintReport:
    def test_print_report_with_results(self, capsys):
        results = [
            LinkResult(
                url="https://example.com",
                file_path=Path("/docs/readme.md"),
                line_number=1,
                status_code=200,
                is_valid=True,
            ),
            LinkResult(
                url="https://broken.example.com",
                file_path=Path("/docs/readme.md"),
                line_number=2,
                status_code=404,
                is_valid=False,
                error="Not Found",
            ),
        ]
        print_report(results)
        captured = capsys.readouterr()
        assert "https://example.com" in captured.out
        assert "https://broken.example.com" in captured.out
        assert "Not Found" in captured.out

    def test_print_report_empty(self, capsys):
        print_report([])
        captured = capsys.readouterr()
        assert "No links" in captured.out or captured.out == "" or "links" in captured.out.lower()

# Test KNOWN_PLACEHOLDERS
class TestKnownPlaceholders:
    def test_known_placeholders_not_empty(self):
        assert len(KNOWN_PLACEHOLDERS) > 0
        assert isinstance(KNOWN_PLACEHOLDERS, list)
        assert all(isinstance(url, str) for url in KNOWN_PLACEHOLDERS)

    def test_known_placeholders_are_urls(self):
        for url in KNOWN_PLACEHOLDERS:
            assert url.startswith("http://") or url.startswith("https://")
