#!/usr/bin/env python3
"""Stage checked historical research from a verified ZIP; never auto-publish expired API data."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zipfile

ALLOWED = ("docs/corpora/emergent-garden/", "docs/superpowers/plans/", "scripts/research/")
BLOCKED = ("/data/", "/validation/", "/.github/", "/private/", "/comments/")
EXTRA = {"BUNDLE-MANIFEST.json", "SOURCE.json", "README.md", "RESEARCHLEDGER-AGENTS.md"}
EXPECTED_ZIP_SHA256 = "5197f26bd5ba82abffd2d03354174352f5cf06efee1ea99f33e201d589aa99c3"
SECRET_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_-]{35}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
)

def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def safe(path: str) -> bool:
    p = PurePosixPath(path)
    return bool(path and not path.startswith("/") and p.as_posix() == path
                and ".." not in p.parts and "." not in p.parts
                and "\\" not in path and "\x00" not in path)

def chosen(path: str) -> bool:
    return (path.startswith(ALLOWED) and path not in EXTRA
            and not any(seg in "/" + path for seg in BLOCKED)
            and path.endswith((".md", ".py", ".yaml", ".yml", ".txt")))

def verify_zip(bundle: zipfile.ZipFile) -> dict[str, bytes]:
    names = bundle.namelist()
    if len(names) != len(set(names)):
        raise ValueError("DUPLICATE_ARCHIVE_MEMBER")
    for info in bundle.infolist():
        if not safe(info.filename) or info.is_dir():
            raise ValueError("INVALID_MEMBER_NAME")
        if (info.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError("SYMLINK_MEMBER")
        if info.file_size > 2_000_000:
            raise ValueError("OVERSIZED_MEMBER")
    if "BUNDLE-MANIFEST.json" not in names:
        raise ValueError("MISSING_MANIFEST")
    manifest = json.loads(bundle.read("BUNDLE-MANIFEST.json"))
    records = manifest.get("files")
    if not isinstance(records, list) or len(records) < 20:
        raise ValueError("INVALID_MANIFEST")
    expected = {r["path"]: r for r in records}
    if len(expected) != len(records) or set(expected) != set(names) - {"BUNDLE-MANIFEST.json"}:
        raise ValueError("MANIFEST_MISMATCH")
    data = {}
    for path, row in expected.items():
        content = bundle.read(path)
        if row.get("bytes") != len(content) or row.get("sha256") != sha(content):
            raise ValueError("HASH_MISMATCH " + path)
        data[path] = content
    return data

def stage(archive: Path, destination: Path, expected_sha256=EXPECTED_ZIP_SHA256) -> dict:
    archive_hash = sha(archive.read_bytes())
    if expected_sha256 and archive_hash != expected_sha256:
        raise ValueError("ARCHIVE_HASH_MISMATCH")
    with zipfile.ZipFile(archive) as bundle:
        contents = verify_zip(bundle)
    included, excluded = [], []
    if destination.is_symlink():
        raise ValueError("DESTINATION_SYMLINK")
    # Verify the destination itself and every existing child component.
    # A ZIP can be safe while a staging directory contains a malicious symlink.
    resolved_root = destination.resolve(strict=False)
    # Check all collisions and secret patterns before writing a single file.
    for path, content in contents.items():
        if not chosen(path):
            excluded.append(path)
            continue
        decoded = content.decode("utf-8")
        if any(pattern.search(decoded) for pattern in SECRET_PATTERNS):
            raise ValueError("POTENTIAL_CREDENTIAL " + path)
        target = destination / path
        component = target
        while component != destination:
            if component.is_symlink():
                raise ValueError("DESTINATION_PATH_SYMLINK " + path)
            component = component.parent
        if not target.resolve(strict=False).is_relative_to(resolved_root):
            raise ValueError("DESTINATION_PATH_ESCAPE " + path)
        if target.exists() and target.read_bytes() != content:
            raise ValueError("DIFFERENT_CONTENT_COLLISION " + path)
        included.append((path, content))
    for path, content in included:
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    result = {
        "schema": "researchledger-recovery-v1",
        "archive_sha256": archive_hash,
        "verified_archive_members": len(contents),
        "staged_files": len(included),
        "excluded_files": len(excluded),
        "staged": [{"path": path, "bytes": len(content), "sha256": sha(content)}
                   for path, content in included],
        "excluded_paths": excluded,
        "status": "STAGED_NOT_PUBLISHED_OR_MERGED",
        "scope": "Historical Wave 5 fallback; not the later September 9 source head",
        "api_data_policy": "Refresh or delete expired YouTube Data API data; do not publish stale September raw metadata."
    }
    receipt = destination / "RECOVERY-RECEIPT.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    parser.add_argument("--expected-sha256", default=EXPECTED_ZIP_SHA256)
    args = parser.parse_args()
    result = stage(args.archive, args.destination, args.expected_sha256)
    print(json.dumps({key: result[key] for key in
        ("archive_sha256", "verified_archive_members", "staged_files", "excluded_files", "status")}, indent=2))

if __name__ == "__main__":
    main()
