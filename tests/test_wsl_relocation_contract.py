import unittest
from pathlib import Path


class WslRelocationContractTests(unittest.TestCase):
    def test_script_has_explicit_destructive_gate_and_volume_allowlist(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "scripts" / "relocate_wsl_distro.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("ConfirmUnregister", text)
        self.assertIn('@("D:", "E:")', text)
        self.assertIn("wsl --export", text)
        self.assertIn("wsl --unregister", text)


if __name__ == "__main__":
    unittest.main()
