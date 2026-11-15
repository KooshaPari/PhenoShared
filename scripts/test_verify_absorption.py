"""Offline regression coverage for absorption root validation."""

import subprocess
import sys
from pathlib import Path


def test_missing_root_fails_before_remote_lookup(tmp_path):
    script = Path(__file__).with_name("verify_absorption.py").resolve()
    relative_root = Path("does/not/exist") / tmp_path.name
    result = subprocess.run(
        [sys.executable, str(script), "host-ops", "--root", str(relative_root)],
        cwd=tmp_path,
        env={"PATH": ""},
        capture_output=True,
        text=True,
    )

    assert not (script.parent.parent / relative_root).exists()
    assert result.returncode == 2
    assert str(script.parent.parent / relative_root) in result.stderr
    assert "directory does not exist" in result.stderr
    assert "OK" not in result.stdout
