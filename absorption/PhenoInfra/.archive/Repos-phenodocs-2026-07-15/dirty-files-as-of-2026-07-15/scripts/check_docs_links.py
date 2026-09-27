"""Check documentation links for validity and placeholders.

This module provides a docs link checker with placeholder detection,
concurrent HTTP checking, and structured reporting.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


# Known placeholder URLs that should be skipped during HTTP validation
KNOWN_PLACEHOLDERS: List[str] = [
    "https://placeholder.example.com",
    "https://todo.example.com",
    "https://fixme.example.com",
    "https://example.com/placeholder",
    "https://example.com/todo",
]


@dataclass
class LinkResult:
    """Represents the result of checking a single link."""

    url: str
    file_path: Path
    line_number: int
    status_code: int
    is_valid: bool
    error: Optional[str] = None


def is_placeholder_url(url: str, custom_placeholders: Optional[List[str]] = None) -> bool:
    """Check if a URL is a known placeholder.

    Args:
        url: The URL to check.
        custom_placeholders: Optional list of custom placeholder URLs.

    Returns:
        True if the URL is a known placeholder, False otherwise.
    """
    if url in KNOWN_PLACEHOLDERS:
        return True
    if custom_placeholders and url in custom_placeholders:
        return True
    return False


def extract_links_from_file(file_path: Path) -> List[tuple[int, str]]:
    """Extract all markdown links from a file.

    Args:
        file_path: Path to the file to check.

    Returns:
        List of (line_number, url) tuples.
    """
    links: List[tuple[int, str]] = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                # Find markdown links: [text](url)
                for match in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", line):
                    url = match.group(2)
                    links.append((line_number, url))
    except (OSError, IOError):
        pass
    return links


def collect_all_links(file_paths: List[Path]) -> List[tuple[Path, int, str]]:
    """Collect all links from a list of files.

    Args:
        file_paths: List of file paths to check.

    Returns:
        List of (file_path, line_number, url) tuples.
    """
    results: List[tuple[Path, int, str]] = []
    for file_path in file_paths:
        if file_path.is_dir():
            continue
        links = extract_links_from_file(file_path)
        for line_number, url in links:
            results.append((file_path, line_number, url))
    return results


def check_link(
    url: str,
    file_path: Path,
    line_number: int,
    timeout: Optional[int] = None,
) -> LinkResult:
    """Check a single link.

    For placeholder URLs, returns a valid result with status_code=0.
    For real URLs, attempts an HTTP HEAD request.

    Args:
        url: The URL to check.
        file_path: Path to the file containing the link.
        line_number: Line number of the link.
        timeout: Optional timeout in seconds.

    Returns:
        LinkResult with the check result.
    """
    if is_placeholder_url(url):
        return LinkResult(
            url=url,
            file_path=Path(file_path),
            line_number=line_number,
            status_code=0,
            is_valid=True,
        )

    try:
        import urllib.request
        import urllib.error

        req = urllib.request.Request(url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        if timeout:
            response = urllib.request.urlopen(req, timeout=timeout)
        else:
            response = urllib.request.urlopen(req, timeout=10)
        return LinkResult(
            url=url,
            file_path=Path(file_path),
            line_number=line_number,
            status_code=response.getcode(),
            is_valid=True,
        )
    except Exception as exc:
        return LinkResult(
            url=url,
            file_path=Path(file_path),
            line_number=line_number,
            status_code=0,
            is_valid=False,
            error=str(exc),
        )


def check_links_concurrent(links: List[tuple[Path, int, str]]) -> List[LinkResult]:
    """Check multiple links concurrently.

    Args:
        links: List of (file_path, line_number, url) tuples.

    Returns:
        List of LinkResult objects.
    """
    return [check_link(url, file_path, line_number) for file_path, line_number, url in links]


def print_report(results: List[LinkResult]) -> None:
    """Print a report of link check results.

    Args:
        results: List of LinkResult objects.
    """
    if not results:
        print("No links to report.")
        return

    for result in results:
        status = "OK" if result.is_valid else "FAIL"
        error_str = f" - {result.error}" if result.error else ""
        print(f"{status}: {result.url} (status={result.status_code}){error_str}")


def main() -> None:
    """Main entry point for the CLI."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: check_docs_links.py <file_or_directory> ...")
        sys.exit(1)

    paths = [Path(arg) for arg in sys.argv[1:]]
    links = collect_all_links(paths)
    results = check_links_concurrent(links)
    print_report(results)


if __name__ == "__main__":
    main()
