"""corpus_guard.py — the write tripwires that protect the research-ledger corpus.

The guard exists because the corpus was destroyed once (2026-10-15) by a symlink
planted at its path. On 2026-11-10 it was found to be protecting nothing: every
path constant had drifted off the real corpus, so `guard_write_target` refused
writes to locations nobody used while the live 21 GiB corpus sat unguarded.

These tests pin the behaviour, not the current constant values:

  * the sealed archive is never writable, by any flag or environment;
  * retired corpus locations are refused, so the corpus cannot be split;
  * a missing or symlinked canonical path is refused;
  * the canonical corpus needs a deliberate opt-in, by flag or by environment;
  * anything else passes through untouched;
  * and the configured CANONICAL is a real regular file on this host, which is
    the tripwire that would have caught the original drift.

No test reads or writes the production corpus: every path here is under
tmp_path or monkeypatched.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Import the package from the repo root so this suite runs without installation.
_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from researchledger import corpus_guard  # noqa: E402


@pytest.fixture
def fake_corpus(tmp_path):
    """A file standing in for the canonical corpus."""
    p = tmp_path / "research_ledger.sqlite"
    p.write_bytes(b"SQLite format 3\x00" + b"\x00" * 64)
    return p


@pytest.fixture
def guard(fake_corpus, tmp_path, monkeypatch):
    """Point every guard constant at tmp_path so nothing real is touched."""

    def apply(canonical=fake_corpus, sealed=None, sealed_dir=None, retired=()):
        monkeypatch.setattr(corpus_guard, "CANONICAL", str(canonical))
        monkeypatch.setattr(
            corpus_guard,
            "SEALED_BACKUP",
            str(sealed or (tmp_path / "sealed.bak")),
        )
        # Keep the archive directory distinct from tmp_path itself, otherwise
        # every ordinary-path test would land inside the sealed tree.
        monkeypatch.setattr(
            corpus_guard,
            "SEALED_ARCHIVE_DIR",
            str(sealed_dir or (tmp_path / "sealed-archive")),
        )
        monkeypatch.setattr(
            corpus_guard, "RETIRED_CANONICALS", tuple(str(r) for r in retired)
        )
        monkeypatch.delenv(corpus_guard.ALLOW_ENV, raising=False)

    apply()
    return apply


# --------------------------------------------------------------------------
# The sealed archive: absolute, no override.
# --------------------------------------------------------------------------


def test_refuses_sealed_archive(guard, tmp_path):
    guard(sealed=tmp_path / "sealed.bak")
    with pytest.raises(SystemExit, match="sealed archive"):
        corpus_guard.guard_write_target(str(tmp_path / "sealed.bak"))


def test_sealed_archive_refused_even_with_flag_and_env(guard, tmp_path, monkeypatch):
    sealed = tmp_path / "sealed.bak"
    guard(sealed=sealed)
    monkeypatch.setenv(corpus_guard.ALLOW_ENV, "1")
    with pytest.raises(SystemExit, match="sealed archive"):
        corpus_guard.guard_write_target(str(sealed), allow_canonical=True)


def test_refuses_any_path_inside_sealed_archive_dir(guard, tmp_path):
    """A future dated backup must be protected without a code change.

    This is the 2026-11-10 drift class: protection keyed to one exact filename
    silently stops covering a file nobody updated the constant for.
    """
    archive = tmp_path / "sealed-archive"
    archive.mkdir()
    guard(sealed=archive / "current.bak", sealed_dir=archive)
    for name in ("next.bak", "research_ledger.sqlite.sealed-20270101", "nested/x"):
        with pytest.raises(SystemExit, match="sealed archive"):
            corpus_guard.guard_write_target(str(archive / name))


def test_sealed_dir_refused_even_with_flag_and_env(guard, tmp_path, monkeypatch):
    archive = tmp_path / "sealed-archive"
    archive.mkdir()
    guard(sealed=archive / "current.bak", sealed_dir=archive)
    monkeypatch.setenv(corpus_guard.ALLOW_ENV, "1")
    with pytest.raises(SystemExit, match="sealed archive"):
        corpus_guard.guard_write_target(
            str(archive / "future.bak"), allow_canonical=True
        )


def test_path_outside_sealed_dir_is_unaffected(guard, tmp_path):
    archive = tmp_path / "sealed-archive"
    archive.mkdir()
    guard(sealed=archive / "current.bak", sealed_dir=archive)
    sibling = tmp_path / "sealed-archive-not" / "work.db"
    assert corpus_guard.guard_write_target(str(sibling)).endswith("work.db")


# --------------------------------------------------------------------------
# Retired locations: writing there splits the corpus.
# --------------------------------------------------------------------------


def test_refuses_retired_location(guard, tmp_path):
    retired = tmp_path / "old" / "research_ledger.sqlite"
    guard(retired=[retired])
    with pytest.raises(SystemExit, match="RETIRED corpus location"):
        corpus_guard.guard_write_target(str(retired))


def test_retired_location_is_refused_even_with_optin(guard, tmp_path, monkeypatch):
    """A flag lets you write the *canonical* corpus, never a dead address."""
    retired = tmp_path / "old" / "research_ledger.sqlite"
    guard(retired=[retired])
    with pytest.raises(SystemExit, match="RETIRED corpus location"):
        corpus_guard.guard_write_target(str(retired), allow_canonical=True)
    monkeypatch.setenv(corpus_guard.ALLOW_ENV, "true")
    with pytest.raises(SystemExit, match="RETIRED corpus location"):
        corpus_guard.guard_write_target(str(retired))


# --------------------------------------------------------------------------
# Missing / symlinked canonical: the shape of the 2026-10-15 incident.
# --------------------------------------------------------------------------


def test_refuses_missing_canonical(guard, tmp_path):
    absent = tmp_path / "nope" / "research_ledger.sqlite"
    guard(canonical=absent)
    with pytest.raises(SystemExit, match="canonical corpus is missing"):
        corpus_guard.guard_write_target(str(absent))


def test_refuses_symlinked_canonical(guard, tmp_path):
    real = tmp_path / "real.sqlite"
    real.write_bytes(b"SQLite format 3\x00" + b"\x00" * 64)
    link = tmp_path / "link.sqlite"
    link.symlink_to(real)
    guard(canonical=link)
    with pytest.raises(SystemExit, match="SYMLINK"):
        corpus_guard.guard_write_target(str(link))


# --------------------------------------------------------------------------
# The canonical corpus needs a deliberate opt-in.
# --------------------------------------------------------------------------


def test_refuses_canonical_without_optin(guard, fake_corpus):
    with pytest.raises(SystemExit, match="without --allow-canonical"):
        corpus_guard.guard_write_target(str(fake_corpus))


def test_allows_canonical_with_flag(guard, fake_corpus):
    target = corpus_guard.guard_write_target(str(fake_corpus), allow_canonical=True)
    assert target == os.path.realpath(fake_corpus)


def test_allows_canonical_with_env(guard, fake_corpus, monkeypatch, capsys):
    monkeypatch.setenv(corpus_guard.ALLOW_ENV, "1")
    target = corpus_guard.guard_write_target(str(fake_corpus))
    assert target == os.path.realpath(fake_corpus)
    # Honouring the env opt-out must leave a trace, never be silent.
    assert corpus_guard.ALLOW_ENV in capsys.readouterr().err


@pytest.mark.parametrize("value", ["0", "false", "no", "", "off"])
def test_falsy_env_does_not_allow_canonical(guard, fake_corpus, monkeypatch, value):
    monkeypatch.setenv(corpus_guard.ALLOW_ENV, value)
    with pytest.raises(SystemExit, match="without --allow-canonical"):
        corpus_guard.guard_write_target(str(fake_corpus))


# --------------------------------------------------------------------------
# Everything else passes through.
# --------------------------------------------------------------------------


def test_ordinary_path_allowed(guard, tmp_path):
    staging = tmp_path / "staging.sqlite"
    assert corpus_guard.guard_write_target(str(staging)) == os.path.realpath(staging)


# --------------------------------------------------------------------------
# The anti-drift tripwire: the configured corpus must be real.
# --------------------------------------------------------------------------


def test_configured_canonical_exists_on_this_host():
    """Fails if CANONICAL drifts off the real corpus again.

    This is the check that was missing on 2026-11-10: CANONICAL pointed at a
    path that did not exist, so every guard decision was about a dead address.
    """
    if not os.path.exists(corpus_guard.CANONICAL):
        pytest.fail(
            f"CANONICAL does not exist: {corpus_guard.CANONICAL}\n"
            "The guard would be protecting nothing. Repoint it (or set "
            f"{corpus_guard.CANONICAL_ENV}) at the live corpus."
        )
    assert not os.path.islink(corpus_guard.CANONICAL), (
        f"CANONICAL is a symlink: {corpus_guard.CANONICAL}"
    )
    assert os.path.isfile(corpus_guard.CANONICAL)
    assert os.path.getsize(corpus_guard.CANONICAL) > 0
    corpus_guard.assert_corpus_sane()


def test_configured_sealed_backup_exists_on_this_host():
    """Fails if the last line of defence is missing or writable.

    On 2026-11-10 SEALED_BACKUP pointed at a path that had been repurposed, so
    the corpus had no archive at all and nothing said so.
    """
    sealed = corpus_guard.SEALED_BACKUP
    if not os.path.exists(sealed):
        pytest.fail(
            f"SEALED_BACKUP does not exist: {sealed}\n"
            "The corpus has no last line of defence. Take a sealed backup "
            f"(or set {corpus_guard.SEALED_ENV})."
        )
    assert not os.path.islink(sealed), f"SEALED_BACKUP is a symlink: {sealed}"
    assert os.path.isfile(sealed)
    assert os.path.getsize(sealed) > 0
    assert os.stat(sealed).st_mode & 0o222 == 0, (
        f"SEALED_BACKUP is writable: {sealed} "
        f"(mode {oct(os.stat(sealed).st_mode & 0o777)})"
    )
    assert corpus_guard._inside(sealed, corpus_guard.SEALED_ARCHIVE_DIR), (
        f"SEALED_BACKUP {sealed} is outside SEALED_ARCHIVE_DIR "
        f"{corpus_guard.SEALED_ARCHIVE_DIR}, so the directory guard would not "
        "cover it"
    )
    assert os.path.getsize(sealed) == os.path.getsize(corpus_guard.CANONICAL), (
        "sealed backup size differs from the live corpus\n"
        f"  corpus: {os.path.getsize(corpus_guard.CANONICAL):,}\n"
        f"  sealed: {os.path.getsize(sealed):,}"
    )
