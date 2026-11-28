"""refresh-sealed-archive.sh — the freshness comparison must work on both hosts.

The tool compares the live corpus mtime against the newest sealed copy. That
comparison used `stat -f '%m %z'`, which is BSD spelling: on a Linux node GNU
stat reads `-f` as `--file-system` and prints a filesystem report, so the two
"mtimes" compared as garbage and a stale seal could read as current. It also
hashed with `shasum`, a perl utility a minimal Linux install need not carry.

These tests pin the behaviour, not the implementation: every case is driven
through ARCHIVE_CORPUS / ARCHIVE_SEAL_DIR, so nothing touches a real corpus.

  * no sealed copy -> REFRESH_NEEDED, with the live size and a real epoch mtime;
  * sealed copy newer than the corpus -> UP_TO_DATE;
  * sealed copy older than the corpus -> REFRESH_NEEDED naming both sides;
  * the platform spellings that broke it are gone from the source.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOL = REPO_ROOT / "tools" / "refresh-sealed-archive.sh"


def _run(corpus: Path, seal_dir: Path) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env["ARCHIVE_CORPUS"] = str(corpus)
    env["ARCHIVE_SEAL_DIR"] = str(seal_dir)
    return subprocess.run(
        ["bash", str(TOOL), "--check"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
        check=False,
    )


def test_no_sealed_copy_reports_real_size_and_epoch(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.sqlite"
    corpus.write_bytes(b"0123456789")
    result = _run(corpus, tmp_path / "seal")

    assert "REFRESH_NEEDED: no sealed copy exists" in result.stdout
    # A BSD stat under GNU stat prints a filesystem report here, not these.
    assert "10 bytes" in result.stdout
    mtime = result.stdout.split("mtime ", 1)[1].split(")", 1)[0]
    assert mtime.isdigit() and int(mtime) > 1_500_000_000


def test_seal_newer_than_corpus_is_up_to_date(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.sqlite"
    corpus.write_bytes(b"0123456789")
    seal_dir = tmp_path / "seal"
    seal_dir.mkdir()
    seal = seal_dir / "research_ledger.sqlite.sealed-20260101"
    seal.write_bytes(b"sealed")
    os.utime(seal, (1_893_456_000, 1_893_456_000))  # 2030-01-01

    result = _run(corpus, seal_dir)

    assert result.returncode == 0
    assert "UP_TO_DATE" in result.stdout


def test_seal_older_than_corpus_needs_refresh(tmp_path: Path) -> None:
    corpus = tmp_path / "corpus.sqlite"
    corpus.write_bytes(b"0123456789")
    seal_dir = tmp_path / "seal"
    seal_dir.mkdir()
    seal = seal_dir / "research_ledger.sqlite.sealed-20260101"
    seal.write_bytes(b"sealed")
    os.utime(seal, (1_577_836_800, 1_577_836_800))  # 2020-01-01

    result = _run(corpus, seal_dir)

    assert result.returncode == 1
    assert "the live corpus was written after the sealed copy" in result.stdout
    assert "sealed mtime 1577836800 size 6" in result.stdout


def test_stat_and_hash_are_platform_selected() -> None:
    source = TOOL.read_text()

    # The unguarded original: a bare BSD spelling used on every host.
    assert "corpus_stat() { stat -f" not in source
    assert "stat -f%z" not in source
    # Both platforms remain reachable: GNU first, BSD as the fallback.
    assert "stat -c '%Y %s'" in source
    assert "stat -f '%m %z'" in source
    assert "command -v sha256sum" in source
