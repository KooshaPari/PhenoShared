"""Unit tests for the BytePort toolchain convergence doctor.

These tests run against the live BytePort repo at C:/Users/koosh/BytePort
and verify the doctor's invariants without requiring `mise` itself to be
installed (the doctor is mise-output-only).
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCTOR_PATH = REPO_ROOT / "scripts" / "doctor.py"


class DoctorSmokeTests(unittest.TestCase):
    """Doctor CLI surface + cross-file consistency invariants."""

    def test_doctor_exits_zero(self) -> None:
        """The doctor should exit 0 when the live BytePort repo is healthy."""
        result = subprocess.run(
            [sys.executable, str(DOCTOR_PATH)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=REPO_ROOT,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"doctor failed:\nstdout={result.stdout}\nstderr={result.stderr}",
        )
        # The doctor should mention at least one toolchain pin (mise.toml is
        # always present in the live repo).
        self.assertIn("Taskfile:", result.stdout)

    def test_mise_toml_and_cargo_toml_consistent(self) -> None:
        """If both pins are present, they must agree on Rust version."""
        mise_text = (REPO_ROOT / "mise.toml").read_text(encoding="utf-8")
        cargo_text = (REPO_ROOT / "Cargo.toml").read_text(encoding="utf-8")
        import re

        m_mise = re.search(r'RUST_VERSION\s*=\s*"(\d+\.\d+\.\d+)"', mise_text)
        m_cargo = re.search(r'rust-version\s*=\s*"(\d+\.\d+(?:\.\d+)?)"', cargo_text)
        if m_mise and m_cargo:
            self.assertEqual(
                m_mise.group(1),
                m_cargo.group(1),
                "RUST_VERSION mismatch between mise.toml and Cargo.toml",
            )

    def test_taskfile_yaml_parses(self) -> None:
        """Taskfile.yml must be a valid YAML doc with at least one top-level target."""
        try:
            import yaml  # type: ignore
        except ImportError:
            self.skipTest("PyYAML not installed")
        data = yaml.safe_load((REPO_ROOT / "Taskfile.yml").read_text(encoding="utf-8"))
        self.assertIsInstance(data, dict)
        self.assertIn("tasks", data)
        self.assertGreaterEqual(len(data["tasks"]), 5)


if __name__ == "__main__":
    unittest.main()
